"""
이벤트 Payload 스키마 정의

12개 핵심 이벤트의 표준화된 payload 구조를 정의합니다.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ScanStatus(str, Enum):
    """스캔 상태"""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrganizationStatus(str, Enum):
    """파일 정리 상태"""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ErrorType(str, Enum):
    """오류 유형"""

    VALIDATION_ERROR = "validation_error"
    FILE_OPERATION_ERROR = "file_operation_error"
    PERMISSION_ERROR = "permission_error"
    DISK_SPACE_ERROR = "disk_space_error"
    UNKNOWN_ERROR = "unknown_error"


# 1. SCAN_STARTED
class ScanStartedPayload(BaseModel):
    """스캔 시작 이벤트 payload"""

    scan_id: str
    directory_path: str
    recursive: bool = True
    file_extensions: list[str] = Field(default_factory=list)


# 2. SCAN_PROGRESS
class ScanProgressPayload(BaseModel):
    """스캔 진행 이벤트 payload"""

    scan_id: str
    processed: int
    total: int
    current_file: Optional[str] = None
    progress_percent: float = Field(ge=0, le=100)
    current_step: str = "scanning"


# 3. SCAN_COMPLETED
class ScanCompletedPayload(BaseModel):
    """스캔 완료 이벤트 payload"""

    scan_id: str
    found_files: list[str]
    stats: dict[str, Any] = Field(default_factory=dict)
    duration_seconds: float = 0.0
    status: ScanStatus = ScanStatus.COMPLETED
    error_message: Optional[str] = None


# 4. PLAN_CREATED
class PlanCreatedPayload(BaseModel):
    """계획 생성 이벤트 payload"""

    plan_id: str
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    skips: list[dict[str, Any]] = Field(default_factory=list)
    moves: list[dict[str, Any]] = Field(default_factory=list)
    total_operations: int = 0


# 5. PLAN_VALIDATED
class PlanValidatedPayload(BaseModel):
    """계획 검증 이벤트 payload"""

    plan_id: str
    warnings: list[str] = Field(default_factory=list)
    is_valid: bool = True
    validation_errors: list[str] = Field(default_factory=list)


# 6. ORGANIZE_STARTED
class OrganizeStartedPayload(BaseModel):
    """정리 시작 이벤트 payload"""

    organization_id: str
    total_files: int
    estimated_duration: Optional[float] = None


# 7. ORGANIZE_CONFLICT
class OrganizeConflictPayload(BaseModel):
    """정리 충돌 이벤트 payload"""

    organization_id: str
    path: str
    reason: str
    resolution_hint: Optional[str] = None
    conflict_type: str = "file_exists"


# 8. ORGANIZE_SKIPPED
class OrganizeSkippedPayload(BaseModel):
    """정리 스킵 이벤트 payload"""

    organization_id: str
    path: str
    reason: str
    skip_count: int = 1


# 9. ORGANIZE_COMPLETED
class OrganizeCompletedPayload(BaseModel):
    """정리 완료 이벤트 payload"""

    organization_id: str
    moved: int
    backed_up: int
    duration: float
    stats: dict[str, Any] = Field(default_factory=dict)


# 10. USER_ACTION_REQUIRED
class UserActionRequiredPayload(BaseModel):
    """사용자 액션 요청 이벤트 payload"""

    action_id: str
    message: str
    action_type: str  # "confirm", "resolve", "choose"
    options: list[str] = Field(default_factory=list)
    timeout_seconds: Optional[int] = None


# 11. ERROR
class ErrorPayload(BaseModel):
    """오류 이벤트 payload"""

    error_id: str
    error_type: ErrorType
    message: str
    details: Optional[str] = None
    where: str  # "scan", "organize", "plan", etc.
    context: dict[str, Any] = Field(default_factory=dict)


# 12. SETTINGS_CHANGED
class SettingsChangedPayload(BaseModel):
    """설정 변경 이벤트 payload"""

    changed_keys: list[str]
    old_values: dict[str, Any] = Field(default_factory=dict)
    new_values: dict[str, Any] = Field(default_factory=dict)
    source: str = "user"
