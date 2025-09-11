"""
확인 다이얼로그 매니저
"""

import logging

logger = logging.getLogger(__name__)
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from src.core.unified_event_system import get_unified_event_bus

# 백업 이벤트들은 새로운 12개 핵심 이벤트 시스템으로 대체됨
# from src.core.events import (BatchOperationWarningEvent,
#                                    ConfirmationRequiredEvent,
#                                    ConfirmationResponseEvent)


@dataclass
class ConfirmationRequest:
    """확인 요청"""

    confirmation_id: UUID = field(default_factory=lambda: uuid4())
    title: str = ""
    message: str = ""
    details: str = ""
    severity: str = "warning"
    requires_confirmation: bool = True
    can_cancel: bool = True
    default_action: str = "cancel"
    affected_files: list[Path] = field(default_factory=list)
    operation_type: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    on_confirm: Callable[[], None] | None = None
    on_cancel: Callable[[], None] | None = None
    on_timeout: Callable[[], None] | None = None
    timeout_seconds: float | None = None
    auto_confirm_on_timeout: bool = False


@dataclass
class ConfirmationResponse:
    """확인 응답"""

    confirmation_id: UUID = field(default_factory=lambda: uuid4())
    user_response: str = "cancel"
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
        self.event_bus = get_unified_event_bus()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._pending_confirmations: dict[UUID, ConfirmationRequest] = {}
        self._auto_confirm_rules: dict[str, dict[str, Any]] = {
            "file_move": {"low_risk": True, "medium_risk": False, "high_risk": False},
            "file_copy": {"low_risk": True, "medium_risk": True, "high_risk": False},
            "file_delete": {"low_risk": False, "medium_risk": False, "high_risk": False},
            "file_rename": {"low_risk": True, "medium_risk": False, "high_risk": False},
        }
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
            return self._auto_confirm(request)
        self._pending_confirmations[request.confirmation_id] = request
        # 새로운 이벤트 시스템으로 변경 - 로그만 남김
        self.logger.info(f"확인 요청: {request.confirmation_id} - {request.title}")
        # 필요시 event_publisher.publish_user_action_required() 등을 사용
        if request.timeout_seconds:
            self._schedule_timeout(request)
        return ConfirmationResponse(
            confirmation_id=request.confirmation_id,
            user_response=request.default_action,
            was_auto_response=True,
        )

    def _auto_confirm(self, request: ConfirmationRequest) -> ConfirmationResponse:
        """자동 확인 처리"""
        risk_level = self._assess_risk(request.operation_type, request.affected_files)
        auto_confirm = self._should_auto_confirm(request.operation_type, risk_level)
        response = ConfirmationResponse(
            confirmation_id=request.confirmation_id,
            user_response="confirm" if auto_confirm else "cancel",
            was_auto_response=True,
        )
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
        file_count = len(affected_files)
        total_size_mb = 0.0
        for file_path in affected_files:
            try:
                if file_path.exists() and file_path.is_file():
                    total_size_mb += file_path.stat().st_size / (1024 * 1024)
            except (OSError, PermissionError) as e:
                self.logger.warning(f"파일 크기 계산 실패: {file_path} - {e}")
        extensions = set()
        for file_path in affected_files:
            if file_path.suffix:
                extensions.add(file_path.suffix.lower())
        forbidden_paths = []
        for file_path in affected_files:
            try:
                file_path_str = str(file_path).lower()
                for forbidden in ["/system", "/windows", "/program files", "/usr", "/etc"]:
                    if forbidden in file_path_str:
                        forbidden_paths.append(forbidden)
            except (OSError, ValueError) as e:
                self.logger.warning(f"경로 검증 실패: {file_path} - {e}")
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
        response_time = (datetime.now() - request.created_at).total_seconds() * 1000
        # 새로운 이벤트 시스템으로 변경 - 로그만 남김
        self.logger.info(f"확인 응답: {confirmation_id} - {response}")
        # 필요시 event_publisher.publish_user_action_required() 등을 사용
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
        can_proceed = total_files <= 200
        warning_message = f"{total_files}개 파일에 대한 {operation_type} 작업"
        if estimated_time_seconds > 60:
            warning_message += f" (예상 시간: {estimated_time_seconds / 60:.1f}분)"
        # 새로운 이벤트 시스템으로 변경 - 로그만 남김
        self.logger.warning(f"일괄 작업 경고: {operation_type} - {total_files}개 파일")
        # 필요시 event_publisher.publish_user_action_required() 등을 사용

    def cleanup_expired_confirmations(self, max_age_hours: float = 24.0) -> int:
        """만료된 확인 요청 정리"""
        cutoff_time = datetime.now().timestamp() - max_age_hours * 3600
        expired_ids = []
        for conf_id, request in self._pending_confirmations.items():
            if request.created_at.timestamp() < cutoff_time:
                expired_ids.append(conf_id)
        for conf_id in expired_ids:
            self.cancel_confirmation(conf_id)
        return len(expired_ids)
