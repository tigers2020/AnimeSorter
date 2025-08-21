"""
안전장치 시스템 이벤트 정의
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from .events import BaseEvent

# ===== 백업 시스템 이벤트 =====


@dataclass
class BackupStartedEvent(BaseEvent):
    """백업 시작 이벤트"""

    backup_id: UUID = field(default_factory=lambda: uuid4())
    source_paths: list[Path] = field(default_factory=list)
    backup_location: Path = field(default_factory=Path)
    backup_type: str = "auto"  # auto, manual, scheduled
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BackupCompletedEvent(BaseEvent):
    """백업 완료 이벤트"""

    backup_id: UUID = field(default_factory=lambda: uuid4())
    source_paths: list[Path] = field(default_factory=list)
    backup_location: Path = field(default_factory=Path)
    backup_size_bytes: int = 0
    files_backed_up: int = 0
    success: bool = True
    error_message: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BackupFailedEvent(BaseEvent):
    """백업 실패 이벤트"""

    backup_id: UUID = field(default_factory=lambda: uuid4())
    source_paths: list[Path] = field(default_factory=list)
    backup_location: Path = field(default_factory=Path)
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BackupCleanupEvent(BaseEvent):
    """백업 정리 이벤트"""

    backup_ids: list[UUID] = field(default_factory=list)
    cleanup_type: str = "auto"  # auto, manual, space_cleanup
    freed_space_bytes: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


# ===== 확인 다이얼로그 이벤트 =====


@dataclass
class ConfirmationRequiredEvent(BaseEvent):
    """사용자 확인 필요 이벤트"""

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
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConfirmationResponseEvent(BaseEvent):
    """사용자 확인 응답 이벤트"""

    confirmation_id: UUID = field(default_factory=lambda: uuid4())
    user_response: str = "cancel"  # confirm, cancel
    user_comment: str | None = None
    response_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BatchOperationWarningEvent(BaseEvent):
    """일괄 작업 경고 이벤트"""

    operation_id: UUID = field(default_factory=lambda: uuid4())
    operation_type: str = ""
    total_files: int = 0
    estimated_time_seconds: float = 0.0
    risk_level: str = "medium"  # low, medium, high
    warning_message: str = ""
    can_proceed: bool = True
    timestamp: datetime = field(default_factory=datetime.now)


# ===== 중단 기능 이벤트 =====


@dataclass
class OperationInterruptRequestedEvent(BaseEvent):
    """작업 중단 요청 이벤트"""

    operation_id: UUID = field(default_factory=lambda: uuid4())
    operation_type: str = ""
    reason: str = "user_request"  # user_request, system_error, timeout
    can_interrupt: bool = True
    graceful_shutdown: bool = True
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OperationInterruptedEvent(BaseEvent):
    """작업 중단 완료 이벤트"""

    operation_id: UUID = field(default_factory=lambda: uuid4())
    operation_type: str = ""
    interrupt_reason: str = ""
    files_processed: int = 0
    files_remaining: int = 0
    cleanup_successful: bool = True
    error_message: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OperationResumeRequestedEvent(BaseEvent):
    """작업 재개 요청 이벤트"""

    operation_id: UUID = field(default_factory=lambda: uuid4())
    operation_type: str = ""
    resume_from_file: Path | None = None
    skip_processed_files: bool = True
    timestamp: datetime = field(default_factory=datetime.now)


# ===== 안전 모드 이벤트 =====


@dataclass
class SafetyModeChangedEvent(BaseEvent):
    """안전 모드 변경 이벤트"""

    previous_mode: str = ""
    new_mode: str = ""
    mode_description: str = ""
    is_test_mode: bool = False
    is_simulation_mode: bool = False
    can_modify_files: bool = True
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TestModeOperationEvent(BaseEvent):
    """테스트 모드 작업 이벤트"""

    operation_id: UUID = field(default_factory=lambda: uuid4())
    operation_type: str = ""
    would_affect_files: list[Path] = field(default_factory=list)
    simulation_result: dict[str, Any] = field(default_factory=dict)
    test_mode: bool = True
    timestamp: datetime = field(default_factory=datetime.now)


# ===== 종합 안전 상태 이벤트 =====


@dataclass
class SafetyStatusUpdateEvent(BaseEvent):
    """안전 상태 업데이트 이벤트"""

    backup_enabled: bool = True
    confirmation_required: bool = True
    can_interrupt: bool = True
    safety_mode: str = "normal"
    risk_level: str = "low"
    safety_score: float = 100.0  # 0-100
    warnings: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SafetyAlertEvent(BaseEvent):
    """안전 경고 이벤트"""

    alert_id: UUID = field(default_factory=lambda: uuid4())
    alert_type: str = "warning"  # info, warning, danger, critical
    title: str = ""
    message: str = ""
    details: str = ""
    requires_attention: bool = True
    can_dismiss: bool = True
    affected_operations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
