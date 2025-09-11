"""
미디어 데이터 관리 관련 이벤트 정의

파싱된 미디어 파일 데이터의 관리, 그룹화, 필터링 과정의 이벤트를 정의합니다.
"""

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from src.app.domain import MediaFile, MediaGroup
from src.core.unified_event_system import BaseEvent


class MediaDataStatus(Enum):
    """미디어 데이터 상태"""

    LOADING = "loading"
    PARSING = "parsing"
    GROUPING = "grouping"
    FILTERING = "filtering"
    READY = "ready"
    ERROR = "error"


class GroupingStrategy(Enum):
    """그룹화 전략"""

    BY_TITLE = "by_title"
    BY_SERIES = "by_series"
    BY_SEASON = "by_season"
    BY_QUALITY = "by_quality"
    BY_SOURCE = "by_source"
    CUSTOM = "custom"


class FilterCriteria(Enum):
    """필터링 기준"""

    MEDIA_TYPE = "media_type"
    QUALITY = "quality"
    SOURCE = "source"
    SIZE_RANGE = "size_range"
    DATE_RANGE = "date_range"
    EPISODE_RANGE = "episode_range"
    TITLE_PATTERN = "title_pattern"


@dataclass
class MediaDataStatistics:
    """미디어 데이터 통계"""

    total_files: int = 0
    total_groups: int = 0
    files_by_type: dict[str, int] = field(default_factory=dict)
    files_by_quality: dict[str, int] = field(default_factory=dict)
    files_by_source: dict[str, int] = field(default_factory=dict)
    total_size_bytes: int = 0
    average_file_size_mb: float = 0.0
    largest_file_size_mb: float = 0.0
    smallest_file_size_mb: float = 0.0


@dataclass
class MediaDataFilter:
    """미디어 데이터 필터"""

    criteria: FilterCriteria
    value: Any
    operator: str = "equals"
    case_sensitive: bool = False


@dataclass
class MediaDataGrouping:
    """미디어 데이터 그룹화 설정"""

    strategy: GroupingStrategy = GroupingStrategy.BY_TITLE
    custom_key_function: str | None = None
    sort_groups: bool = True
    sort_files_within_groups: bool = True


@dataclass
class MediaDataLoadStartedEvent(BaseEvent):
    """미디어 데이터 로드 시작 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    file_paths: list[Path] = field(default_factory=list)
    total_files: int = 0


@dataclass
class MediaDataParsingProgressEvent(BaseEvent):
    """미디어 데이터 파싱 진행률 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    current_file: int = 0
    total_files: int = 0
    current_file_path: Path | None = None
    progress_percent: int = 0
    parsing_status: MediaDataStatus = MediaDataStatus.PARSING


@dataclass
class MediaDataParsingCompletedEvent(BaseEvent):
    """미디어 데이터 파싱 완료 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    parsed_files: list[MediaFile] = field(default_factory=list)
    failed_files: list[Path] = field(default_factory=list)
    parsing_errors: list[str] = field(default_factory=list)
    parsing_duration_seconds: float = 0.0


@dataclass
class MediaDataGroupingStartedEvent(BaseEvent):
    """미디어 데이터 그룹화 시작 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    grouping_config: MediaDataGrouping = field(default_factory=MediaDataGrouping)
    total_files: int = 0


@dataclass
class MediaDataGroupingCompletedEvent(BaseEvent):
    """미디어 데이터 그룹화 완료 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    groups: dict[str, MediaGroup] = field(default_factory=dict)
    grouping_duration_seconds: float = 0.0
    statistics: MediaDataStatistics = field(default_factory=MediaDataStatistics)


@dataclass
class MediaDataFilteringStartedEvent(BaseEvent):
    """미디어 데이터 필터링 시작 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    filters: list[MediaDataFilter] = field(default_factory=list)
    total_items: int = 0


@dataclass
class MediaDataFilteringCompletedEvent(BaseEvent):
    """미디어 데이터 필터링 완료 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    filtered_files: list[MediaFile] = field(default_factory=list)
    filtered_groups: dict[str, MediaGroup] = field(default_factory=dict)
    filter_duration_seconds: float = 0.0
    items_before_filter: int = 0
    items_after_filter: int = 0


@dataclass
class MediaDataReadyEvent(BaseEvent):
    """미디어 데이터 준비 완료 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    total_files: int = 0
    total_groups: int = 0
    statistics: MediaDataStatistics = field(default_factory=MediaDataStatistics)
    is_filtered: bool = False
    is_grouped: bool = False


@dataclass
class MediaDataErrorEvent(BaseEvent):
    """미디어 데이터 오류 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    error_type: str = "unknown"
    error_message: str = ""
    failed_operation: MediaDataStatus = MediaDataStatus.ERROR
    error_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaDataUpdatedEvent(BaseEvent):
    """미디어 데이터 업데이트 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    updated_files: list[MediaFile] = field(default_factory=list)
    updated_groups: list[str] = field(default_factory=list)
    update_type: str = "modified"


@dataclass
class MediaDataClearedEvent(BaseEvent):
    """미디어 데이터 초기화 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    previous_file_count: int = 0
    previous_group_count: int = 0


@dataclass
class MediaDataExportStartedEvent(BaseEvent):
    """미디어 데이터 내보내기 시작 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    export_format: str = "json"
    export_path: Path = field(default_factory=Path)
    include_statistics: bool = True


@dataclass
class MediaDataExportCompletedEvent(BaseEvent):
    """미디어 데이터 내보내기 완료 이벤트"""

    operation_id: UUID = field(default_factory=uuid4)
    export_path: Path = field(default_factory=Path)
    export_size_bytes: int = 0
    exported_files_count: int = 0
    exported_groups_count: int = 0
    export_duration_seconds: float = 0.0
