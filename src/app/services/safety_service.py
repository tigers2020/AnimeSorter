"""
통합된 안전 관리 서비스 - AnimeSorter

기존의 여러 Safety Manager 클래스들을 통합하여 단일 서비스로 제공합니다.
- SafetyManager
- SafetySystemManager
- BackupManager
- ConfirmationManager
- InterruptionManager
- UnifiedFileBackupManager
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from PyQt5.QtCore import QObject, pyqtSignal

from src.core.unified_event_system import get_unified_event_bus

logger = logging.getLogger(__name__)


class SafetyMode:
    """안전 모드 상수"""

    NORMAL = "normal"
    SAFE = "safe"
    TEST = "test"
    SIMULATION = "simulation"
    EMERGENCY = "emergency"


@dataclass
class SafetyConfiguration:
    """안전 설정"""

    default_mode: str = SafetyMode.NORMAL
    backup_enabled: bool = True
    backup_before_operations: bool = True
    backup_strategy: str = "copy"
    confirmation_required: bool = True
    auto_confirm_low_risk: bool = True
    confirmation_timeout_seconds: float = 30.0
    can_interrupt: bool = True
    graceful_shutdown_timeout: float = 10.0
    force_interrupt_after_timeout: bool = True
    test_mode_enabled: bool = False
    simulation_mode_enabled: bool = False
    low_risk_threshold: int = 10
    medium_risk_threshold: int = 100
    high_risk_threshold: int = 1000


@dataclass
class SafetyStatus:
    """안전 상태"""

    current_mode: str = SafetyMode.NORMAL
    backup_enabled: bool = True
    confirmation_required: bool = True
    can_interrupt: bool = True
    risk_level: str = "low"
    safety_score: float = 100.0
    warnings: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    is_test_mode: bool = False
    is_simulation_mode: bool = False
    can_modify_files: bool = True


@dataclass
class BackupInfo:
    """백업 정보"""

    backup_id: str
    source_paths: list[Path]
    backup_path: Path
    created_at: datetime
    files_backed_up: int
    backup_strategy: str


class IBackupService(Protocol):
    """백업 서비스 인터페이스"""

    def create_backup(self, source_paths: list[Path], strategy: str) -> BackupInfo | None:
        """백업 생성"""
        ...

    def restore_backup(self, backup_id: str, target_path: Path) -> bool:
        """백업 복원"""
        ...

    def list_backups(self) -> list[BackupInfo]:
        """백업 목록 조회"""
        ...


class IConfirmationService(Protocol):
    """확인 서비스 인터페이스"""

    def request_confirmation(self, message: str, details: str = "") -> bool:
        """확인 요청"""
        ...

    def auto_confirm_operation(
        self, operation_type: str, affected_files: list[Path], risk_level: str
    ) -> bool:
        """자동 확인"""
        ...


class IInterruptionService(Protocol):
    """중단 서비스 인터페이스"""

    def can_interrupt(self) -> bool:
        """중단 가능 여부"""
        ...

    def request_interruption(self) -> bool:
        """중단 요청"""
        ...


class SafetyService(QObject):
    """통합된 안전 관리 서비스"""

    # 시그널 정의
    safety_mode_changed = pyqtSignal(str, str)  # old_mode, new_mode
    backup_created = pyqtSignal(str)  # backup_id
    backup_restored = pyqtSignal(str)  # backup_id
    confirmation_requested = pyqtSignal(str, str)  # message, details
    operation_interrupted = pyqtSignal(str)  # operation_type
    safety_alert = pyqtSignal(str, str, str)  # alert_type, title, message

    def __init__(self, config: SafetyConfiguration | None = None, parent=None):
        super().__init__(parent)
        self.config = config or SafetyConfiguration()
        self.event_bus = get_unified_event_bus()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 서비스 컴포넌트들
        self._backup_service: IBackupService | None = None
        self._confirmation_service: IConfirmationService | None = None
        self._interruption_service: IInterruptionService | None = None

        # 상태 관리
        self._current_mode = self.config.default_mode
        self._safety_status = SafetyStatus(
            current_mode=self._current_mode,
            backup_enabled=self.config.backup_enabled,
            confirmation_required=self.config.confirmation_required,
            can_interrupt=self.config.can_interrupt,
        )

        # 내부 상태
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

        # 안전 점수 가중치
        self._safety_weights = {
            "successful_operation": 1.0,
            "failed_operation": -2.0,
            "backup_created": 0.5,
            "confirmation_given": 0.3,
            "risk_incident": -5.0,
            "mode_change": 0.0,
        }

        self.logger.info(f"안전 서비스 초기화됨 (모드: {self._current_mode})")

    def set_backup_service(self, backup_service: IBackupService) -> None:
        """백업 서비스 설정"""
        self._backup_service = backup_service
        self.logger.info("백업 서비스 설정됨")

    def set_confirmation_service(self, confirmation_service: IConfirmationService) -> None:
        """확인 서비스 설정"""
        self._confirmation_service = confirmation_service
        self.logger.info("확인 서비스 설정됨")

    def set_interruption_service(self, interruption_service: IInterruptionService) -> None:
        """중단 서비스 설정"""
        self._interruption_service = interruption_service
        self.logger.info("중단 서비스 설정됨")

    def get_safety_status(self) -> SafetyStatus:
        """안전 상태 조회"""
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
        self._safety_status.is_test_mode = new_mode == SafetyMode.TEST
        self._safety_status.is_simulation_mode = new_mode == SafetyMode.SIMULATION

        # 시그널 발생
        self.safety_mode_changed.emit(previous_mode, new_mode)
        self.logger.info(f"안전 모드 변경: {previous_mode} -> {new_mode}")

        return True

    def is_operation_safe(self, operation_type: str, affected_files: list[Path]) -> bool:
        """작업 안전성 확인"""
        if not self._safety_status.can_modify_files:
            self.logger.warning(f"현재 모드({self._current_mode})에서 파일 수정 불가")
            return False

        risk_level = self._assess_operation_risk(operation_type, affected_files)

        if risk_level == "high":
            return self._safety_status.confirmation_required
        if risk_level == "medium":
            return (
                self._current_mode != SafetyMode.SAFE or self._safety_status.confirmation_required
            )
        return True

    def request_safe_operation(
        self, operation_type: str, affected_files: list[Path], operation_callback: Callable
    ) -> bool:
        """안전한 작업 실행 요청"""
        # 테스트 모드 처리
        if self._safety_status.is_test_mode:
            return self._handle_test_mode_operation(
                operation_type, affected_files, operation_callback
            )

        # 시뮬레이션 모드 처리
        if self._safety_status.is_simulation_mode:
            return self._handle_simulation_mode_operation(
                operation_type, affected_files, operation_callback
            )

        # 안전성 검사
        if not self.is_operation_safe(operation_type, affected_files):
            self.logger.warning(f"작업 {operation_type}이 안전하지 않음")
            return False

        # 백업 생성
        if self._should_create_backup(operation_type, affected_files) and not self._create_backup(
            affected_files
        ):
            self.logger.error("백업 생성 실패로 작업 중단")
            return False

        # 확인 요청
        if self._requires_confirmation(
            operation_type, affected_files
        ) and not self._request_confirmation(operation_type, affected_files):
            self.logger.info("사용자가 작업을 취소함")
            return False

        # 작업 실행
        try:
            result = operation_callback()
            self._record_successful_operation(operation_type, affected_files)
            return result
        except Exception as e:
            self.logger.error(f"작업 실행 실패: {e}")
            self._record_failed_operation(operation_type, affected_files, str(e))
            return False

    def create_backup(self, source_paths: list[Path]) -> BackupInfo | None:
        """백업 생성 (UI에서 직접 호출)"""
        if not self._backup_service:
            self.logger.warning("백업 서비스가 설정되지 않음")
            return None

        try:
            backup_info = self._backup_service.create_backup(
                source_paths, self.config.backup_strategy
            )
            if backup_info:
                self.logger.info(f"백업 생성 완료: {backup_info.backup_id}")
                self._record_backup_created()
                self.backup_created.emit(backup_info.backup_id)
                return backup_info
            return None
        except Exception as e:
            self.logger.error(f"백업 생성 실패: {e}")
            return None

    def restore_backup(self, backup_id: str, target_path: Path) -> bool:
        """백업 복원 (UI에서 직접 호출)"""
        if not self._backup_service:
            self.logger.warning("백업 서비스가 설정되지 않음")
            return False

        try:
            success = self._backup_service.restore_backup(backup_id, target_path)
            if success:
                self.logger.info(f"백업 복원 완료: {backup_id}")
                self.backup_restored.emit(backup_id)
            return success
        except Exception as e:
            self.logger.error(f"백업 복원 실패: {e}")
            return False

    def list_backups(self) -> list[BackupInfo]:
        """백업 목록 조회"""
        if not self._backup_service:
            return []
        return self._backup_service.list_backups()

    def get_safety_recommendations(self) -> list[str]:
        """안전 권장사항 조회"""
        recommendations = []

        if self._safety_status.safety_score < 30:
            recommendations.append(
                "안전 점수가 매우 낮습니다. 모든 작업을 중단하고 시스템을 점검하세요."
            )
        elif self._safety_status.safety_score < 50:
            recommendations.append(
                "안전 점수가 낮습니다. 위험한 작업을 피하고 백업을 자주 생성하세요."
            )

        if len(self._risk_incidents) > 10:
            recommendations.append(
                "최근 위험 사고가 많습니다. 안전 모드로 전환하는 것을 고려하세요."
            )

        if self._current_mode == SafetyMode.NORMAL:
            recommendations.append(
                "일반 모드입니다. 중요한 작업 전에 백업을 생성하는 것을 권장합니다."
            )
        elif self._current_mode == SafetyMode.SAFE:
            recommendations.append("안전 모드입니다. 모든 작업에 확인이 필요합니다.")
        elif self._current_mode == SafetyMode.TEST:
            recommendations.append("테스트 모드입니다. 실제 파일은 수정되지 않습니다.")

        return recommendations

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
                successful_operations / total_operations * 100 if total_operations > 0 else 0
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

    # 내부 메서드들
    def _assess_operation_risk(self, operation_type: str, affected_files: list[Path]) -> str:
        """작업 위험도 평가"""
        if not affected_files:
            return "low"

        file_count = len(affected_files)

        if file_count <= self.config.low_risk_threshold:
            base_risk = "low"
        elif file_count <= self.config.medium_risk_threshold:
            base_risk = "medium"
        else:
            base_risk = "high"

        operation_risk_multipliers = {
            "file_move": 1.0,
            "file_copy": 0.8,
            "file_delete": 2.0,
            "file_rename": 0.5,
            "batch_operation": 1.5,
        }

        multiplier = operation_risk_multipliers.get(operation_type, 1.0)

        if base_risk == "low" and multiplier <= 1.0:
            return "low"
        if base_risk == "high" or multiplier >= 1.5:
            return "high"
        return "medium"

    def _should_create_backup(self, operation_type: str, affected_files: list[Path]) -> bool:
        """백업 생성 필요 여부 확인"""
        if not self.config.backup_enabled:
            return False
        if not self.config.backup_before_operations:
            return False

        risk_level = self._assess_operation_risk(operation_type, affected_files)
        if risk_level == "high":
            return True
        return operation_type == "file_delete"

    def _create_backup(self, affected_files: list[Path]) -> bool:
        """백업 생성 (내부)"""
        if not self._backup_service:
            self.logger.warning("백업 서비스가 설정되지 않음")
            return False

        try:
            backup_info = self._backup_service.create_backup(
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

        risk_level = self._assess_operation_risk(operation_type, affected_files)
        if risk_level == "high":
            return True
        return self.config.confirmation_required

    def _request_confirmation(self, operation_type: str, affected_files: list[Path]) -> bool:
        """확인 요청"""
        if not self._confirmation_service:
            self.logger.warning("확인 서비스가 설정되지 않음")
            return False

        if self.config.auto_confirm_low_risk:
            risk_level = self._assess_operation_risk(operation_type, affected_files)
            if risk_level == "low":
                return self._confirmation_service.auto_confirm_operation(
                    operation_type, affected_files, risk_level
                )

        message = f"{operation_type} 작업을 실행하시겠습니까?"
        details = f"영향받는 파일: {len(affected_files)}개"

        self.confirmation_requested.emit(message, details)
        return self._confirmation_service.request_confirmation(message, details)

    def _handle_test_mode_operation(
        self, operation_type: str, affected_files: list[Path], operation_callback: Callable
    ) -> bool:
        """테스트 모드 작업 처리"""
        self.logger.info(f"테스트 모드: {operation_type} 작업 시뮬레이션")
        return True

    def _handle_simulation_mode_operation(
        self, operation_type: str, affected_files: list[Path], operation_callback: Callable
    ) -> bool:
        """시뮬레이션 모드 작업 처리"""
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

        self._risk_incidents.append(
            {
                "timestamp": datetime.now(),
                "operation_type": operation_type,
                "error_message": error_message,
                "severity": "medium",
            }
        )

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
        # 위험도 계산
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

        self.logger.info(
            f"안전 상태 업데이트: {self._current_mode} - 점수: {self._safety_status.safety_score}"
        )
