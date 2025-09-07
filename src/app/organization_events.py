"""
파일 정리(Organization) 관련 이벤트 정의

파일 정리 프로세스의 각 단계별 이벤트를 정의합니다.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from src.app.events import BaseEvent


class OrganizationStatus(Enum):
    """파일 정리 상태"""

    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    VALIDATION_FAILED = "validation_failed"

    PREFLIGHT_STARTED = "preflight_started"
    PREFLIGHT_COMPLETED = "preflight_completed"
    PREFLIGHT_CANCELLED = "preflight_cancelled"

    ORGANIZATION_STARTED = "organization_started"
    ORGANIZATION_PROGRESS = "organization_progress"
    ORGANIZATION_COMPLETED = "organization_completed"
    ORGANIZATION_FAILED = "organization_failed"
    ORGANIZATION_CANCELLED = "organization_cancelled"


class OrganizationErrorType(Enum):
    """파일 정리 오류 유형"""

    VALIDATION_ERROR = "validation_error"
    PREFLIGHT_ERROR = "preflight_error"
    FILE_OPERATION_ERROR = "file_operation_error"
    PERMISSION_ERROR = "permission_error"
    DISK_SPACE_ERROR = "disk_space_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class OrganizationValidationResult:
    """파일 정리 검증 결과"""

    is_valid: bool = False
    has_grouped_items: bool = False
    has_destination: bool = False
    destination_exists: bool = False
    destination_writable: bool = False
    total_groups: int = 0
    total_files: int = 0
    estimated_size_mb: float = 0.0
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class OrganizationResult:
    """파일 정리 결과"""

    success_count: int = 0
    error_count: int = 0
    skip_count: int = 0
    total_count: int = 0
    processed_files: list[Path] = field(default_factory=list)
    failed_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    operation_duration_seconds: float = 0.0
    created_directories: list[Path] = field(default_factory=list)
    cleaned_directories: int = 0  # 정리된 빈 디렉토리 수
    _processed_sources: set[str] = field(default_factory=set)  # 중복 처리 방지용


@dataclass
class OrganizationPreflightData:
    """프리플라이트 체크 데이터"""

    destination_directory: Path
    grouped_items: dict[str, Any]  # AnimeDataManager의 그룹 데이터
    estimated_operations: int = 0
    estimated_size_mb: float = 0.0
    disk_space_available_mb: float = 0.0
    will_create_directories: list[Path] = field(default_factory=list)
    potential_conflicts: list[str] = field(default_factory=list)


# ===== 이벤트 정의 =====


@dataclass
class OrganizationValidationStartedEvent(BaseEvent):
    """파일 정리 검증 시작 이벤트"""

    organization_id: UUID = field(default_factory=uuid4)
    destination_directory: Path | None = None


@dataclass
class OrganizationValidationCompletedEvent(BaseEvent):
    """파일 정리 검증 완료 이벤트"""

    organization_id: UUID = field(default_factory=uuid4)
    validation_result: OrganizationValidationResult = field(
        default_factory=OrganizationValidationResult
    )


@dataclass
class OrganizationValidationFailedEvent(BaseEvent):
    """파일 정리 검증 실패 이벤트"""

    organization_id: UUID = field(default_factory=uuid4)
    error_type: OrganizationErrorType = OrganizationErrorType.VALIDATION_ERROR
    error_message: str = ""
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class OrganizationPreflightStartedEvent(BaseEvent):
    """파일 정리 프리플라이트 시작 이벤트"""

    organization_id: UUID = field(default_factory=uuid4)
    preflight_data: OrganizationPreflightData | None = None


@dataclass
class OrganizationPreflightCompletedEvent(BaseEvent):
    """파일 정리 프리플라이트 완료 이벤트"""

    organization_id: UUID = field(default_factory=uuid4)
    user_approved: bool = False
    preflight_data: OrganizationPreflightData | None = None


@dataclass
class OrganizationStartedEvent(BaseEvent):
    """파일 정리 시작 이벤트"""

    organization_id: UUID = field(default_factory=uuid4)
    destination_directory: Path = field(default_factory=Path)
    total_files: int = 0
    total_groups: int = 0


@dataclass
class OrganizationProgressEvent(BaseEvent):
    """파일 정리 진행률 이벤트"""

    organization_id: UUID = field(default_factory=uuid4)
    current_file: int = 0
    total_files: int = 0
    current_group: str = ""
    operation_type: str = ""  # "copy", "move", "create_directory" 등
    current_file_path: Path | None = None
    progress_percent: int = 0


@dataclass
class OrganizationCompletedEvent(BaseEvent):
    """파일 정리 완료 이벤트"""

    organization_id: UUID = field(default_factory=uuid4)
    result: OrganizationResult = field(default_factory=OrganizationResult)
    status: OrganizationStatus = OrganizationStatus.ORGANIZATION_COMPLETED


@dataclass
class OrganizationFailedEvent(BaseEvent):
    """파일 정리 실패 이벤트"""

    organization_id: UUID = field(default_factory=uuid4)
    error_type: OrganizationErrorType = OrganizationErrorType.UNKNOWN_ERROR
    error_message: str = ""
    partial_result: OrganizationResult | None = None


@dataclass
class OrganizationCancelledEvent(BaseEvent):
    """파일 정리 취소 이벤트"""

    organization_id: UUID = field(default_factory=uuid4)
    cancellation_reason: str = "사용자 요청"
    partial_result: OrganizationResult | None = None
