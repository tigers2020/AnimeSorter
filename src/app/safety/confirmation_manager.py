"""
확인 다이얼로그 매니저
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from ..events import get_event_bus
from ..safety_events import (
    BatchOperationWarningEvent,
    ConfirmationRequiredEvent,
    ConfirmationResponseEvent,
)


@dataclass
class ConfirmationRequest:
    """확인 요청"""

    confirmation_id: UUID = field(default_factory=lambda: uuid4())
    title: str = ""
    message: str = ""
    details: str = ""
    severity: str = "warning"  # info, warning, danger
    requires_confirmation: bool = True
    can_cancel: bool = True
    default_action: str = "cancel"  # confirm, cancel
    affected_files: list[Path] = field(default_factory=list)
    operation_type: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    # 콜백 함수들
    on_confirm: Callable[[], None] | None = None
    on_cancel: Callable[[], None] | None = None
    on_timeout: Callable[[], None] | None = None

    # 타임아웃 설정
    timeout_seconds: float | None = None
    auto_confirm_on_timeout: bool = False


@dataclass
class ConfirmationResponse:
    """확인 응답"""

    confirmation_id: UUID = field(default_factory=lambda: uuid4())
    user_response: str = "cancel"  # confirm, cancel, timeout
    user_comment: str | None = None
    response_time_ms: float = 0.0
    responded_at: datetime = field(default_factory=datetime.now)
    was_auto_response: bool = False


class IConfirmationManager(Protocol):
    """확인 매니저 인터페이스"""

    def request_confirmation(self, request: ConfirmationRequest) -> ConfirmationResponse | None:
        """확인 요청"""
        ...

    def auto_confirm_operation(
        self, operation_type: str, affected_files: list[Path], risk_level: str = "low"
    ) -> bool:
        """자동 확인 (위험도 기반)"""
        ...

    def get_pending_confirmations(self) -> list[ConfirmationRequest]:
        """대기 중인 확인 요청 목록"""
        ...

    def cancel_confirmation(self, confirmation_id: UUID) -> bool:
        """확인 요청 취소"""
        ...


class ConfirmationManager:
    """확인 매니저"""

    def __init__(self):
        self.event_bus = get_event_bus()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 대기 중인 확인 요청들
        self._pending_confirmations: dict[UUID, ConfirmationRequest] = {}

        # 자동 확인 규칙
        self._auto_confirm_rules: dict[str, dict[str, Any]] = {
            "file_move": {"low_risk": True, "medium_risk": False, "high_risk": False},
            "file_copy": {"low_risk": True, "medium_risk": True, "high_risk": False},
            "file_delete": {"low_risk": False, "medium_risk": False, "high_risk": False},
            "file_rename": {"low_risk": True, "medium_risk": False, "high_risk": False},
        }

        # 위험도 평가 규칙
        self._risk_assessment_rules = {
            "low_risk": {
                "max_files": 10,
                "max_total_size_mb": 100,
                "allowed_extensions": [".txt", ".jpg", ".png", ".mp4", ".mkv"],
                "forbidden_paths": [],
            },
            "medium_risk": {
                "max_files": 100,
                "max_total_size_mb": 1000,
                "allowed_extensions": [".txt", ".jpg", ".png", ".mp4", ".mkv", ".avi", ".mov"],
                "forbidden_paths": ["/system", "/windows", "/program files"],
            },
            "high_risk": {
                "max_files": float("inf"),
                "max_total_size_mb": float("inf"),
                "allowed_extensions": [],
                "forbidden_paths": [],
            },
        }

    def request_confirmation(self, request: ConfirmationRequest) -> ConfirmationResponse | None:
        """확인 요청"""
        if not request.requires_confirmation:
            # 자동 확인이 필요한 경우
            return self._auto_confirm(request)

        # 확인 요청을 대기 목록에 추가
        self._pending_confirmations[request.confirmation_id] = request

        # 확인 필요 이벤트 발행
        self.event_bus.publish(
            ConfirmationRequiredEvent(
                confirmation_id=request.confirmation_id,
                title=request.title,
                message=request.message,
                details=request.details,
                severity=request.severity,
                requires_confirmation=request.requires_confirmation,
                can_cancel=request.can_cancel,
                default_action=request.default_action,
                affected_files=request.affected_files,
                operation_type=request.operation_type,
            )
        )

        # 타임아웃 설정
        if request.timeout_seconds:
            self._schedule_timeout(request)

        # 사용자 응답 대기 (실제로는 비동기로 처리)
        # 여기서는 기본값 반환
        return ConfirmationResponse(
            confirmation_id=request.confirmation_id,
            user_response=request.default_action,
            was_auto_response=True,
        )

    def _auto_confirm(self, request: ConfirmationRequest) -> ConfirmationResponse:
        """자동 확인 처리"""
        # 위험도 평가
        risk_level = self._assess_risk(request.operation_type, request.affected_files)

        # 자동 확인 규칙 확인
        auto_confirm = self._should_auto_confirm(request.operation_type, risk_level)

        response = ConfirmationResponse(
            confirmation_id=request.confirmation_id,
            user_response="confirm" if auto_confirm else "cancel",
            was_auto_response=True,
        )

        # 자동 확인 결과에 따른 콜백 실행
        if auto_confirm and request.on_confirm:
            try:
                request.on_confirm()
            except Exception as e:
                self.logger.error(f"자동 확인 콜백 실행 실패: {e}")
        elif not auto_confirm and request.on_cancel:
            try:
                request.on_cancel()
            except Exception as e:
                self.logger.error(f"자동 취소 콜백 실행 실패: {e}")

        return response

    def _assess_risk(self, operation_type: str, affected_files: list[Path]) -> str:
        """위험도 평가"""
        if not affected_files:
            return "low_risk"

        # 파일 수 확인
        file_count = len(affected_files)

        # 총 크기 계산
        total_size_mb = 0
        for file_path in affected_files:
            try:
                if file_path.exists() and file_path.is_file():
                    total_size_mb += file_path.stat().st_size / (1024 * 1024)
            except Exception:
                pass

        # 확장자 확인
        extensions = set()
        for file_path in affected_files:
            if file_path.suffix:
                extensions.add(file_path.suffix.lower())

        # 경로 확인
        forbidden_paths = []
        for file_path in affected_files:
            try:
                file_path_str = str(file_path).lower()
                for forbidden in ["/system", "/windows", "/program files", "/usr", "/etc"]:
                    if forbidden in file_path_str:
                        forbidden_paths.append(forbidden)
            except Exception:
                pass

        # 위험도 결정
        if (
            file_count <= 10
            and total_size_mb <= 100
            and not forbidden_paths
            and all(ext in [".txt", ".jpg", ".png", ".mp4", ".mkv"] for ext in extensions)
        ):
            return "low_risk"
        if file_count <= 100 and total_size_mb <= 1000 and not forbidden_paths:
            return "medium_risk"
        return "high_risk"

    def _should_auto_confirm(self, operation_type: str, risk_level: str) -> bool:
        """자동 확인 여부 결정"""
        if operation_type not in self._auto_confirm_rules:
            return False

        return self._auto_confirm_rules[operation_type].get(risk_level, False)

    def _schedule_timeout(self, request: ConfirmationRequest) -> None:
        """타임아웃 스케줄링"""
        # TODO: 실제 타임아웃 스케줄링 구현

    def auto_confirm_operation(
        self, operation_type: str, affected_files: list[Path], risk_level: str = "low"
    ) -> bool:
        """자동 확인 (위험도 기반)"""
        request = ConfirmationRequest(
            title=f"자동 확인: {operation_type}",
            message=f"{len(affected_files)}개 파일에 대한 {operation_type} 작업",
            details=f"위험도: {risk_level}",
            operation_type=operation_type,
            affected_files=affected_files,
            requires_confirmation=False,
        )

        response = self._auto_confirm(request)
        return response.user_response == "confirm"

    def get_pending_confirmations(self) -> list[ConfirmationRequest]:
        """대기 중인 확인 요청 목록"""
        return list(self._pending_confirmations.values())

    def cancel_confirmation(self, confirmation_id: UUID) -> bool:
        """확인 요청 취소"""
        if confirmation_id not in self._pending_confirmations:
            return False

        request = self._pending_confirmations[confirmation_id]
        del self._pending_confirmations[confirmation_id]

        # 취소 콜백 실행
        if request.on_cancel:
            try:
                request.on_cancel()
            except Exception as e:
                self.logger.error(f"취소 콜백 실행 실패: {e}")

        return True

    def process_user_response(
        self, confirmation_id: UUID, response: str, comment: str | None = None
    ) -> bool:
        """사용자 응답 처리"""
        if confirmation_id not in self._pending_confirmations:
            return False

        request = self._pending_confirmations[confirmation_id]
        del self._pending_confirmations[confirmation_id]

        # 응답 시간 계산
        response_time = (datetime.now() - request.created_at).total_seconds() * 1000

        # 응답 이벤트 발행
        self.event_bus.publish(
            ConfirmationResponseEvent(
                confirmation_id=confirmation_id,
                user_response=response,
                user_comment=comment,
                response_time_ms=response_time,
            )
        )

        # 응답에 따른 콜백 실행
        if response == "confirm" and request.on_confirm:
            try:
                request.on_confirm()
            except Exception as e:
                self.logger.error(f"확인 콜백 실행 실패: {e}")
                return False
        elif response == "cancel" and request.on_cancel:
            try:
                request.on_cancel()
            except Exception as e:
                self.logger.error(f"취소 콜백 실행 실패: {e}")
                return False

        return True

    def create_batch_warning(
        self, operation_type: str, total_files: int, estimated_time_seconds: float = 0.0
    ) -> None:
        """일괄 작업 경고 생성"""
        risk_level = "medium" if total_files > 50 else "low"
        can_proceed = total_files <= 200  # 200개 이상이면 사용자 확인 필요

        warning_message = f"{total_files}개 파일에 대한 {operation_type} 작업"
        if estimated_time_seconds > 60:
            warning_message += f" (예상 시간: {estimated_time_seconds / 60:.1f}분)"

        self.event_bus.publish(
            BatchOperationWarningEvent(
                operation_type=operation_type,
                total_files=total_files,
                estimated_time_seconds=estimated_time_seconds,
                risk_level=risk_level,
                warning_message=warning_message,
                can_proceed=can_proceed,
            )
        )

    def cleanup_expired_confirmations(self, max_age_hours: float = 24.0) -> int:
        """만료된 확인 요청 정리"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        expired_ids = []

        for conf_id, request in self._pending_confirmations.items():
            if request.created_at.timestamp() < cutoff_time:
                expired_ids.append(conf_id)

        for conf_id in expired_ids:
            self.cancel_confirmation(conf_id)

        return len(expired_ids)
