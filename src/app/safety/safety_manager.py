"""
종합 안전 관리자
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from src.app.events import get_event_bus
from src.app.safety.backup_manager import IBackupManager
from src.app.safety.confirmation_manager import IConfirmationManager
from src.app.safety.interruption_manager import IInterruptionManager
from src.app.safety_events import (
    SafetyAlertEvent,
    SafetyModeChangedEvent,
    SafetyStatusUpdateEvent,
    TestModeOperationEvent,
)


class SafetyMode:
    """안전 모드"""

    NORMAL = "normal"  # 일반 모드
    SAFE = "safe"  # 안전 모드 (모든 작업에 확인 필요)
    TEST = "test"  # 테스트 모드 (실제 파일 수정 안함)
    SIMULATION = "simulation"  # 시뮬레이션 모드 (결과만 보여줌)
    EMERGENCY = "emergency"  # 비상 모드 (최소한의 작업만 허용)


@dataclass
class SafetyConfiguration:
    """안전 설정"""

    # 기본 모드
    default_mode: str = SafetyMode.NORMAL

    # 백업 설정
    backup_enabled: bool = True
    backup_before_operations: bool = True
    backup_strategy: str = "copy"

    # 확인 설정
    confirmation_required: bool = True
    auto_confirm_low_risk: bool = True
    confirmation_timeout_seconds: float = 30.0

    # 중단 설정
    can_interrupt: bool = True
    graceful_shutdown_timeout: float = 10.0
    force_interrupt_after_timeout: bool = True

    # 테스트 모드 설정
    test_mode_enabled: bool = False
    simulation_mode_enabled: bool = False

    # 위험도 임계값
    low_risk_threshold: int = 10  # 파일 수
    medium_risk_threshold: int = 100  # 파일 수
    high_risk_threshold: int = 1000  # 파일 수


@dataclass
class SafetyStatus:
    """안전 상태"""

    current_mode: str = SafetyMode.NORMAL
    backup_enabled: bool = True
    confirmation_required: bool = True
    can_interrupt: bool = True
    risk_level: str = "low"
    safety_score: float = 100.0  # 0-100
    warnings: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    # 모드별 상태
    is_test_mode: bool = False
    is_simulation_mode: bool = False
    can_modify_files: bool = True


class ISafetyManager(Protocol):
    """안전 관리자 인터페이스"""

    def get_safety_status(self) -> SafetyStatus:
        """안전 상태 조회"""
        ...

    def change_safety_mode(self, new_mode: str) -> bool:
        """안전 모드 변경"""
        ...

    def is_operation_safe(self, operation_type: str, affected_files: list[Path]) -> bool:
        """작업 안전성 확인"""
        ...

    def request_safe_operation(
        self, operation_type: str, affected_files: list[Path], operation_callback: Callable
    ) -> bool:
        """안전한 작업 실행 요청"""
        ...

    def get_safety_recommendations(self) -> list[str]:
        """안전 권장사항 조회"""
        ...


class SafetyManager:
    """종합 안전 관리자"""

    def __init__(self, config: SafetyConfiguration | None = None):
        self.config = config or SafetyConfiguration()
        self.event_bus = get_event_bus()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 현재 안전 상태
        self._current_mode = self.config.default_mode
        self._safety_status = SafetyStatus(
            current_mode=self._current_mode,
            backup_enabled=self.config.backup_enabled,
            confirmation_required=self.config.confirmation_required,
            can_interrupt=self.config.can_interrupt,
        )

        # 하위 매니저들
        self._backup_manager: IBackupManager | None = None
        self._confirmation_manager: IConfirmationManager | None = None
        self._interruption_manager: IInterruptionManager | None = None

        # 안전 점수 계산을 위한 통계
        self._operation_history: list[dict[str, Any]] = []
        self._risk_incidents: list[dict[str, Any]] = []

        # 모드별 제한사항
        self._mode_restrictions = {
            SafetyMode.NORMAL: {
                "can_modify_files": True,
                "requires_confirmation": False,
                "backup_required": False,
            },
            SafetyMode.SAFE: {
                "can_modify_files": True,
                "requires_confirmation": True,
                "backup_required": True,
            },
            SafetyMode.TEST: {
                "can_modify_files": False,
                "requires_confirmation": False,
                "backup_required": False,
            },
            SafetyMode.SIMULATION: {
                "can_modify_files": False,
                "requires_confirmation": False,
                "backup_required": False,
            },
            SafetyMode.EMERGENCY: {
                "can_modify_files": False,
                "requires_confirmation": True,
                "backup_required": True,
            },
        }

        # 안전 점수 계산 가중치
        self._safety_weights = {
            "successful_operation": 1.0,
            "failed_operation": -2.0,
            "backup_created": 0.5,
            "confirmation_given": 0.3,
            "risk_incident": -5.0,
            "mode_change": 0.0,
        }

        self.logger.info(f"안전 관리자 초기화됨 (모드: {self._current_mode})")

    def set_backup_manager(self, backup_manager: IBackupManager) -> None:
        """백업 매니저 설정"""
        self._backup_manager = backup_manager
        self.logger.info("백업 매니저 설정됨")

    def set_confirmation_manager(self, confirmation_manager: IConfirmationManager) -> None:
        """확인 매니저 설정"""
        self._confirmation_manager = confirmation_manager
        self.logger.info("확인 매니저 설정됨")

    def set_interruption_manager(self, interruption_manager: IInterruptionManager) -> None:
        """중단 매니저 설정"""
        self._interruption_manager = interruption_manager
        self.logger.info("중단 매니저 설정됨")

    def get_safety_status(self) -> SafetyStatus:
        """안전 상태 조회"""
        # 상태 업데이트
        self._update_safety_status()
        return self._safety_status

    def change_safety_mode(self, new_mode: str) -> bool:
        """안전 모드 변경"""
        if new_mode not in self._mode_restrictions:
            self.logger.error(f"알 수 없는 안전 모드: {new_mode}")
            return False

        if new_mode == self._current_mode:
            return True

        previous_mode = self._current_mode
        self._current_mode = new_mode

        # 모드별 제한사항 적용
        restrictions = self._mode_restrictions[new_mode]
        self._safety_status.can_modify_files = restrictions["can_modify_files"]
        self._safety_status.confirmation_required = restrictions["requires_confirmation"]

        # 테스트/시뮬레이션 모드 확인
        self._safety_status.is_test_mode = new_mode == SafetyMode.TEST
        self._safety_status.is_simulation_mode = new_mode == SafetyMode.SIMULATION

        # 모드 변경 이벤트 발행
        self.event_bus.publish(
            SafetyModeChangedEvent(
                previous_mode=previous_mode,
                new_mode=new_mode,
                mode_description=self._get_mode_description(new_mode),
                is_test_mode=self._safety_status.is_test_mode,
                is_simulation_mode=self._safety_status.is_simulation_mode,
                can_modify_files=self._safety_status.can_modify_files,
            )
        )

        self.logger.info(f"안전 모드 변경: {previous_mode} -> {new_mode}")
        return True

    def _get_mode_description(self, mode: str) -> str:
        """모드 설명 반환"""
        descriptions = {
            SafetyMode.NORMAL: "일반 모드 - 기본 안전 설정으로 파일 작업 가능",
            SafetyMode.SAFE: "안전 모드 - 모든 작업에 확인 및 백업 필요",
            SafetyMode.TEST: "테스트 모드 - 실제 파일 수정 없이 작업 시뮬레이션",
            SafetyMode.SIMULATION: "시뮬레이션 모드 - 작업 결과만 미리보기",
            SafetyMode.EMERGENCY: "비상 모드 - 최소한의 안전한 작업만 허용",
        }
        return descriptions.get(mode, "알 수 없는 모드")

    def is_operation_safe(self, operation_type: str, affected_files: list[Path]) -> bool:
        """작업 안전성 확인"""
        # 현재 모드에서 파일 수정 가능 여부 확인
        if not self._safety_status.can_modify_files:
            self.logger.warning(f"현재 모드({self._current_mode})에서 파일 수정 불가")
            return False

        # 위험도 평가
        risk_level = self._assess_operation_risk(operation_type, affected_files)

        # 위험도에 따른 안전성 판단
        if risk_level == "high":
            # 높은 위험도는 항상 확인 필요
            return self._safety_status.confirmation_required
        if risk_level == "medium":
            # 중간 위험도는 안전 모드에서만 확인 필요
            return (
                self._current_mode != SafetyMode.SAFE or self._safety_status.confirmation_required
            )
        # 낮은 위험도는 항상 안전
        return True

    def _assess_operation_risk(self, operation_type: str, affected_files: list[Path]) -> str:
        """작업 위험도 평가"""
        if not affected_files:
            return "low"

        file_count = len(affected_files)

        # 파일 수 기반 위험도
        if file_count <= self.config.low_risk_threshold:
            base_risk = "low"
        elif file_count <= self.config.medium_risk_threshold:
            base_risk = "medium"
        else:
            base_risk = "high"

        # 작업 유형별 위험도 조정
        operation_risk_multipliers = {
            "file_move": 1.0,
            "file_copy": 0.8,
            "file_delete": 2.0,
            "file_rename": 0.5,
            "batch_operation": 1.5,
        }

        multiplier = operation_risk_multipliers.get(operation_type, 1.0)

        # 최종 위험도 결정
        if base_risk == "low" and multiplier <= 1.0:
            return "low"
        if base_risk == "high" or multiplier >= 1.5:
            return "high"
        return "medium"

    def request_safe_operation(
        self, operation_type: str, affected_files: list[Path], operation_callback: Callable
    ) -> bool:
        """안전한 작업 실행 요청"""
        # 테스트 모드에서의 처리
        if self._safety_status.is_test_mode:
            return self._handle_test_mode_operation(
                operation_type, affected_files, operation_callback
            )

        # 시뮬레이션 모드에서의 처리
        if self._safety_status.is_simulation_mode:
            return self._handle_simulation_mode_operation(
                operation_type, affected_files, operation_callback
            )

        # 작업 안전성 확인
        if not self.is_operation_safe(operation_type, affected_files):
            self.logger.warning(f"작업 {operation_type}이 안전하지 않음")
            return False

        # 백업 생성
        if self._should_create_backup(operation_type, affected_files) and not self._create_backup(
            affected_files
        ):
            self.logger.error("백업 생성 실패로 작업 중단")
            return False

        # 확인 필요 여부 확인
        if self._requires_confirmation(
            operation_type, affected_files
        ) and not self._request_confirmation(operation_type, affected_files):
            self.logger.info("사용자가 작업을 취소함")
            return False

        # 실제 작업 실행
        try:
            result = operation_callback()
            self._record_successful_operation(operation_type, affected_files)
            return result
        except Exception as e:
            self.logger.error(f"작업 실행 실패: {e}")
            self._record_failed_operation(operation_type, affected_files, str(e))
            return False

    def _should_create_backup(self, operation_type: str, affected_files: list[Path]) -> bool:
        """백업 생성 필요 여부 확인"""
        if not self.config.backup_enabled:
            return False

        if not self.config.backup_before_operations:
            return False

        # 위험도가 높은 작업은 항상 백업
        risk_level = self._assess_operation_risk(operation_type, affected_files)
        if risk_level == "high":
            return True

        # 삭제 작업은 항상 백업
        return operation_type == "file_delete"

    def _create_backup(self, affected_files: list[Path]) -> bool:
        """백업 생성"""
        if not self._backup_manager:
            self.logger.warning("백업 매니저가 설정되지 않음")
            return False

        try:
            backup_info = self._backup_manager.create_backup(
                affected_files, self.config.backup_strategy
            )
            if backup_info:
                self.logger.info(f"백업 생성 완료: {backup_info.backup_id}")
                self._record_backup_created()
                return True
            return False
        except Exception as e:
            self.logger.error(f"백업 생성 실패: {e}")
            return False

    def _requires_confirmation(self, operation_type: str, affected_files: list[Path]) -> bool:
        """확인 필요 여부 확인"""
        if not self._safety_status.confirmation_required:
            return False

        # 위험도가 높은 작업은 항상 확인
        risk_level = self._assess_operation_risk(operation_type, affected_files)
        if risk_level == "high":
            return True

        # 설정에 따른 확인 필요 여부
        return self.config.confirmation_required

    def _request_confirmation(self, operation_type: str, affected_files: list[Path]) -> bool:
        """확인 요청"""
        if not self._confirmation_manager:
            self.logger.warning("확인 매니저가 설정되지 않음")
            return False

        # 자동 확인 시도
        if self.config.auto_confirm_low_risk:
            risk_level = self._assess_operation_risk(operation_type, affected_files)
            if risk_level == "low":
                return self._confirmation_manager.auto_confirm_operation(
                    operation_type, affected_files, risk_level
                )

        # 수동 확인 요청
        # 실제로는 UI에서 사용자 응답을 받아야 함
        # 여기서는 기본값 반환
        return True

    def _handle_test_mode_operation(
        self, operation_type: str, affected_files: list[Path], operation_callback: Callable
    ) -> bool:
        """테스트 모드 작업 처리"""
        # 테스트 모드 이벤트 발행
        self.event_bus.publish(
            TestModeOperationEvent(
                operation_type=operation_type,
                would_affect_files=affected_files,
                simulation_result={"mode": "test", "action": "simulated"},
                test_mode=True,
            )
        )

        # 실제 작업은 실행하지 않고 시뮬레이션만
        self.logger.info(f"테스트 모드: {operation_type} 작업 시뮬레이션")
        return True

    def _handle_simulation_mode_operation(
        self, operation_type: str, affected_files: list[Path], operation_callback: Callable
    ) -> bool:
        """시뮬레이션 모드 작업 처리"""
        # 시뮬레이션 모드 이벤트 발행
        self.event_bus.publish(
            TestModeOperationEvent(
                operation_type=operation_type,
                would_affect_files=affected_files,
                simulation_result={"mode": "simulation", "action": "preview"},
                test_mode=False,
            )
        )

        # 실제 작업은 실행하지 않고 결과만 미리보기
        self.logger.info(f"시뮬레이션 모드: {operation_type} 작업 결과 미리보기")
        return True

    def _record_successful_operation(self, operation_type: str, affected_files: list[Path]) -> None:
        """성공한 작업 기록"""
        self._operation_history.append(
            {
                "timestamp": datetime.now(),
                "operation_type": operation_type,
                "file_count": len(affected_files),
                "success": True,
                "error": None,
            }
        )

        # 안전 점수 업데이트
        self._update_safety_score("successful_operation")

    def _record_failed_operation(
        self, operation_type: str, affected_files: list[Path], error_message: str
    ) -> None:
        """실패한 작업 기록"""
        self._operation_history.append(
            {
                "timestamp": datetime.now(),
                "operation_type": operation_type,
                "file_count": len(affected_files),
                "success": False,
                "error": error_message,
            }
        )

        # 위험 사고 기록
        self._risk_incidents.append(
            {
                "timestamp": datetime.now(),
                "operation_type": operation_type,
                "error_message": error_message,
                "severity": "medium",
            }
        )

        # 안전 점수 업데이트
        self._update_safety_score("failed_operation")
        self._update_safety_score("risk_incident")

    def _record_backup_created(self) -> None:
        """백업 생성 기록"""
        self._update_safety_score("backup_created")

    def _update_safety_score(self, event_type: str) -> None:
        """안전 점수 업데이트"""
        weight = self._safety_weights.get(event_type, 0.0)
        new_score = self._safety_status.safety_score + weight
        self._safety_status.safety_score = max(0.0, min(100.0, new_score))

    def _update_safety_status(self) -> None:
        """안전 상태 업데이트"""
        # 위험도 레벨 결정
        if len(self._risk_incidents) == 0:
            risk_level = "low"
        elif len(self._risk_incidents) <= 3:
            risk_level = "medium"
        else:
            risk_level = "high"

        self._safety_status.risk_level = risk_level

        # 경고 메시지 생성
        warnings = []
        if self._safety_status.safety_score < 50:
            warnings.append("안전 점수가 낮습니다. 주의가 필요합니다.")
        if len(self._risk_incidents) > 5:
            warnings.append("최근 위험 사고가 많습니다. 작업을 중단하는 것을 고려하세요.")
        if self._current_mode == SafetyMode.EMERGENCY:
            warnings.append("비상 모드입니다. 필수적인 작업만 수행하세요.")

        self._safety_status.warnings = warnings
        self._safety_status.last_updated = datetime.now()

        # 상태 업데이트 이벤트 발행
        self.event_bus.publish(
            SafetyStatusUpdateEvent(
                backup_enabled=self._safety_status.backup_enabled,
                confirmation_required=self._safety_status.confirmation_required,
                can_interrupt=self._safety_status.can_interrupt,
                safety_mode=self._current_mode,
                risk_level=self._safety_status.risk_level,
                safety_score=self._safety_status.safety_score,
                warnings=self._safety_status.warnings,
            )
        )

    def get_safety_recommendations(self) -> list[str]:
        """안전 권장사항 조회"""
        recommendations = []

        # 안전 점수 기반 권장사항
        if self._safety_status.safety_score < 30:
            recommendations.append(
                "안전 점수가 매우 낮습니다. 모든 작업을 중단하고 시스템을 점검하세요."
            )
        elif self._safety_status.safety_score < 50:
            recommendations.append(
                "안전 점수가 낮습니다. 위험한 작업을 피하고 백업을 자주 생성하세요."
            )

        # 위험 사고 기반 권장사항
        if len(self._risk_incidents) > 10:
            recommendations.append(
                "최근 위험 사고가 많습니다. 안전 모드로 전환하는 것을 고려하세요."
            )

        # 모드별 권장사항
        if self._current_mode == SafetyMode.NORMAL:
            recommendations.append(
                "일반 모드입니다. 중요한 작업 전에 백업을 생성하는 것을 권장합니다."
            )
        elif self._current_mode == SafetyMode.SAFE:
            recommendations.append("안전 모드입니다. 모든 작업에 확인이 필요합니다.")
        elif self._current_mode == SafetyMode.TEST:
            recommendations.append("테스트 모드입니다. 실제 파일은 수정되지 않습니다.")

        return recommendations

    def create_safety_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        details: str = "",
        requires_attention: bool = True,
    ) -> None:
        """안전 경고 생성"""
        self.event_bus.publish(
            SafetyAlertEvent(
                alert_type=alert_type,
                title=title,
                message=message,
                details=details,
                requires_attention=requires_attention,
                affected_operations=[self._current_mode],
            )
        )

    def get_operation_statistics(self) -> dict[str, Any]:
        """작업 통계 조회"""
        total_operations = len(self._operation_history)
        successful_operations = len([op for op in self._operation_history if op["success"]])
        failed_operations = total_operations - successful_operations

        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "success_rate": (
                (successful_operations / total_operations * 100) if total_operations > 0 else 0
            ),
            "risk_incidents": len(self._risk_incidents),
            "safety_score": self._safety_status.safety_score,
            "current_mode": self._current_mode,
        }

    def reset_safety_score(self) -> None:
        """안전 점수 초기화"""
        self._safety_status.safety_score = 100.0
        self._operation_history.clear()
        self._risk_incidents.clear()
        self.logger.info("안전 점수가 초기화됨")

    def shutdown(self) -> None:
        """안전 관리자 종료"""
        self.logger.info("안전 관리자 종료 중...")

        # 하위 매니저들 종료
        if self._interruption_manager and hasattr(self._interruption_manager, "shutdown"):
            self._interruption_manager.shutdown()

        self.logger.info("안전 관리자 종료 완료")
