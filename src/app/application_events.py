"""
애니메이션 정리 애플리케이션 이벤트

도메인 이벤트와 애플리케이션 이벤트 정의
"""

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from src.app.events import BaseEvent


class ScanStatus(Enum):
    """스캔 상태"""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OperationType(Enum):
    """파일 조작 타입"""

    COPY = "copy"
    MOVE = "move"
    RENAME = "rename"
    DELETE = "delete"
    CREATE_DIRECTORY = "create_directory"
    BACKUP = "backup"


class OperationStatus(Enum):
    """조작 상태"""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class FileScanStartedEvent(BaseEvent):
    """파일 스캔 시작 이벤트"""

    scan_id: UUID = field(default_factory=uuid4)
    directory_path: Path = field(default_factory=lambda: Path())
    recursive: bool = True
    file_extensions: list[str] = field(default_factory=list)


@dataclass
class FileScanProgressEvent(BaseEvent):
    """파일 스캔 진행 이벤트"""

    scan_id: UUID = field(default_factory=uuid4)
    current_file: Path = field(default_factory=lambda: Path())
    processed_count: int = 0
    total_estimated: int | None = None
    progress_percentage: float | None = None


@dataclass
class FilesScannedEvent(BaseEvent):
    """파일 스캔 완료 이벤트"""

    scan_id: UUID = field(default_factory=uuid4)
    directory_path: Path = field(default_factory=lambda: Path())
    found_files: list[Path] = field(default_factory=list)
    scan_duration_seconds: float = 0.0
    status: ScanStatus = ScanStatus.COMPLETED
    error_message: str | None = None


@dataclass
class MetadataExtractionStartedEvent(BaseEvent):
    """메타데이터 추출 시작 이벤트"""

    file_id: UUID = field(default_factory=uuid4)
    file_path: Path = field(default_factory=lambda: Path())


@dataclass
class MetadataExtractionCompletedEvent(BaseEvent):
    """메타데이터 추출 완료 이벤트"""

    file_id: UUID = field(default_factory=uuid4)
    file_path: Path = field(default_factory=lambda: Path())
    metadata: dict[str, Any] = field(default_factory=dict)
    extraction_duration_seconds: float = 0.0
    success: bool = True
    error_message: str | None = None


@dataclass
class MetadataSyncedEvent(BaseEvent):
    """메타데이터 동기화 완료 이벤트"""

    file_ids: list[UUID] = field(default_factory=list)
    sync_duration_seconds: float = 0.0
    successful_count: int = 0
    failed_count: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class FileOperationPlannedEvent(BaseEvent):
    """파일 조작 계획 수립 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    operation_type: OperationType = OperationType.COPY
    source_path: Path = field(default_factory=lambda: Path())
    target_path: Path | None = None
    file_id: UUID | None = None
    group_id: UUID | None = None
    estimated_size_bytes: int = 0
    backup_required: bool = False
    conflicts: list[str] = field(default_factory=list)


@dataclass
class BatchOperationPlannedEvent(BaseEvent):
    """배치 파일 조작 계획 이벤트"""

    batch_id: UUID = field(default_factory=uuid4)
    operation_ids: list[UUID] = field(default_factory=list)
    total_operations: int = 0
    total_size_bytes: int = 0
    estimated_duration_seconds: float = 0.0
    has_conflicts: bool = False


@dataclass
class FileOperationStartedEvent(BaseEvent):
    """파일 조작 시작 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    operation_type: OperationType = OperationType.COPY
    source_path: Path = field(default_factory=lambda: Path())
    target_path: Path | None = None


@dataclass
class FileOperationProgressEvent(BaseEvent):
    """파일 조작 진행 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    bytes_processed: int = 0
    total_bytes: int = 0
    progress_percentage: float = 0.0
    current_speed_bps: float = 0.0


@dataclass
class FileOperationAppliedEvent(BaseEvent):
    """파일 조작 적용 완료 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    operation_type: OperationType = OperationType.COPY
    source_path: Path = field(default_factory=lambda: Path())
    target_path: Path | None = None
    actual_bytes_processed: int = 0
    operation_duration_seconds: float = 0.0
    status: OperationStatus = OperationStatus.COMPLETED
    backup_path: Path | None = None


@dataclass
class BatchOperationCompletedEvent(BaseEvent):
    """배치 조작 완료 이벤트"""

    batch_id: UUID = field(default_factory=uuid4)
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    skipped_operations: int = 0
    total_duration_seconds: float = 0.0
    total_bytes_processed: int = 0


@dataclass
class OperationFailedEvent(BaseEvent):
    """조작 실패 이벤트"""

    operation_id: UUID | None = None
    operation_type: OperationType | None = None
    error_code: str = ""
    error_message: str = ""
    file_path: Path | None = None
    stack_trace: str | None = None
    retry_count: int = 0
    is_recoverable: bool = False


@dataclass
class ValidationFailedEvent(BaseEvent):
    """검증 실패 이벤트"""

    file_id: UUID | None = None
    file_path: Path | None = None
    validation_type: str = ""
    expected_value: Any = None
    actual_value: Any = None
    error_message: str = ""


@dataclass
class MediaFileCreatedEvent(BaseEvent):
    """미디어 파일 생성 이벤트"""

    file_id: UUID = field(default_factory=uuid4)
    file_path: Path = field(default_factory=lambda: Path())
    media_type: str = ""
    initial_flags: list[str] = field(default_factory=list)


@dataclass
class MediaFileUpdatedEvent(BaseEvent):
    """미디어 파일 업데이트 이벤트"""

    file_id: UUID = field(default_factory=uuid4)
    file_path: Path = field(default_factory=lambda: Path())
    changed_fields: list[str] = field(default_factory=list)
    old_values: dict[str, Any] = field(default_factory=dict)
    new_values: dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaFileDeletedEvent(BaseEvent):
    """미디어 파일 삭제 이벤트"""

    file_id: UUID = field(default_factory=uuid4)
    file_path: Path = field(default_factory=lambda: Path())
    was_grouped: bool = False
    group_id: UUID | None = None


@dataclass
class MediaFileMovedEvent(BaseEvent):
    """미디어 파일 이동 이벤트"""

    file_id: UUID = field(default_factory=uuid4)
    old_path: Path = field(default_factory=lambda: Path())
    new_path: Path = field(default_factory=lambda: Path())
    operation_id: UUID | None = None


@dataclass
class MediaFileFlagChangedEvent(BaseEvent):
    """미디어 파일 플래그 변경 이벤트"""

    file_id: UUID = field(default_factory=uuid4)
    file_path: Path = field(default_factory=lambda: Path())
    flag: str = ""
    added: bool = True
    reason: str | None = None


@dataclass
class MediaGroupCreatedEvent(BaseEvent):
    """미디어 그룹 생성 이벤트"""

    group_id: UUID = field(default_factory=uuid4)
    title: str = ""
    season: int | None = None
    initial_episode_count: int = 0


@dataclass
class MediaGroupUpdatedEvent(BaseEvent):
    """미디어 그룹 업데이트 이벤트"""

    group_id: UUID = field(default_factory=uuid4)
    title: str = ""
    changed_fields: list[str] = field(default_factory=list)
    old_values: dict[str, Any] = field(default_factory=dict)
    new_values: dict[str, Any] = field(default_factory=dict)


@dataclass
class EpisodeAddedToGroupEvent(BaseEvent):
    """그룹에 에피소드 추가 이벤트"""

    group_id: UUID = field(default_factory=uuid4)
    file_id: UUID = field(default_factory=uuid4)
    episode_number: int = 0
    group_title: str = ""
    is_group_complete: bool = False


@dataclass
class EpisodeRemovedFromGroupEvent(BaseEvent):
    """그룹에서 에피소드 제거 이벤트"""

    group_id: UUID = field(default_factory=uuid4)
    file_id: UUID = field(default_factory=uuid4)
    episode_number: int = 0
    group_title: str = ""


@dataclass
class MediaGroupCompletedEvent(BaseEvent):
    """미디어 그룹 완성 이벤트"""

    group_id: UUID = field(default_factory=uuid4)
    title: str = ""
    season: int | None = None
    total_episodes: int = 0
    completion_time: datetime = field(default_factory=datetime.now)


@dataclass
class ExternalMetadataSearchStartedEvent(BaseEvent):
    """외부 메타데이터 검색 시작 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    query: str = ""
    provider: str = ""
    search_type: str = ""


@dataclass
class ExternalMetadataFoundEvent(BaseEvent):
    """외부 메타데이터 발견 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    provider: str = ""
    external_id: str = ""
    title: str = ""
    year: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0


@dataclass
class ExternalMetadataLinkedEvent(BaseEvent):
    """외부 메타데이터 연결 이벤트"""

    group_id: UUID = field(default_factory=uuid4)
    provider: str = ""
    external_id: str = ""
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    linked_by_user: bool = False


@dataclass
class UserActionEvent(BaseEvent):
    """사용자 액션 이벤트"""

    action_type: str = ""
    action_data: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None
    session_id: str | None = None


@dataclass
class SelectionChangedEvent(BaseEvent):
    """선택 변경 이벤트"""

    selected_file_ids: list[UUID] = field(default_factory=list)
    selected_group_ids: list[UUID] = field(default_factory=list)
    selection_count: int = 0
    selection_type: str = ""


@dataclass
class ViewModeChangedEvent(BaseEvent):
    """뷰 모드 변경 이벤트"""

    view_mode: str = ""
    previous_mode: str = ""
    filter_settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class SettingsChangedEvent(BaseEvent):
    """설정 변경 이벤트"""

    setting_key: str = ""
    old_value: Any = None
    new_value: Any = None
    category: str = ""


@dataclass
class ApplicationStateChangedEvent(BaseEvent):
    """애플리케이션 상태 변경 이벤트"""

    state: str = ""
    previous_state: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetricEvent(BaseEvent):
    """성능 메트릭 이벤트"""

    metric_name: str = ""
    value: float = 0.0
    unit: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryUsageEvent(BaseEvent):
    """메모리 사용량 이벤트"""

    used_memory_bytes: int = 0
    available_memory_bytes: int = 0
    memory_percentage: float = 0.0
    gc_collections: int = 0


@dataclass
class DiskSpaceEvent(BaseEvent):
    """디스크 공간 이벤트"""

    path: Path = field(default_factory=lambda: Path())
    total_bytes: int = 0
    used_bytes: int = 0
    available_bytes: int = 0
    usage_percentage: float = 0.0
    warning_threshold_reached: bool = False


@dataclass
class ApplicationStartedEvent(BaseEvent):
    """애플리케이션 시작 이벤트"""

    version: str = ""
    startup_duration_seconds: float = 0.0
    configuration: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplicationShutdownEvent(BaseEvent):
    """애플리케이션 종료 이벤트"""

    shutdown_reason: str = ""
    uptime_seconds: float = 0.0
    unsaved_changes: bool = False
