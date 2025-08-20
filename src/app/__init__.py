"""
AnimeSorter Application Core

애플리케이션 레벨의 핵심 컴포넌트들을 제공합니다.
"""

# 백그라운드 작업 이벤트
from .background_events import (
    TaskCancelledEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskPriority,
    TaskProgressEvent,
    TaskQueueStatusEvent,
    TaskRetryEvent,
    TaskStartedEvent,
    TaskStatus,
)

# 백그라운드 작업 클래스
from .background_task import BaseTask, TaskResult, TaskSignals
from .container import DIContainer, get_container
from .domain import (
    MediaFile,
    MediaGroup,
    MediaLibrary,
    MediaMetadata,
    MediaQuality,
    MediaSource,
    MediaType,
    ProcessingFlag,
)
from .events import BaseEvent, TypedEventBus, get_event_bus
from .services import (
    BackgroundTaskService,
    FileScanService,
    IBackgroundTaskService,
    IFileScanService,
    IUIUpdateService,
    UIUpdateService,
)
from .setup import cleanup_application, get_service, initialize_application
from .simple_events import (
    FileOperationAppliedEvent,
    # 파일 조작 이벤트
    FileOperationPlannedEvent,
    # 스캔 이벤트
    FilesScannedEvent,
    # 미디어 파일/그룹 이벤트
    MediaFileCreatedEvent,
    MediaGroupCreatedEvent,
    # 메타데이터 이벤트
    MetadataSyncedEvent,
    OperationFailedEvent,
    OperationStatus,
    OperationType,
    # 상태 열거형
    ScanStatus,
)
from .ui_events import (
    ErrorMessageEvent,
    FileCountUpdateEvent,
    MemoryUsageUpdateEvent,
    MenuStateUpdateEvent,
    ProgressUpdateEvent,
    # UI 업데이트 이벤트
    StatusBarUpdateEvent,
    SuccessMessageEvent,
    TableDataUpdateEvent,
    ThemeUpdateEvent,
    UIStateUpdateEvent,
    WindowTitleUpdateEvent,
)

__all__ = [
    "DIContainer",
    "get_container",
    "TypedEventBus",
    "BaseEvent",
    "get_event_bus",
    "MediaFile",
    "MediaGroup",
    "MediaLibrary",
    "MediaType",
    "ProcessingFlag",
    "MediaQuality",
    "MediaSource",
    "MediaMetadata",
    # 애플리케이션 이벤트
    "FilesScannedEvent",
    "MetadataSyncedEvent",
    "FileOperationPlannedEvent",
    "FileOperationAppliedEvent",
    "OperationFailedEvent",
    "MediaFileCreatedEvent",
    "MediaGroupCreatedEvent",
    "ScanStatus",
    "OperationType",
    "OperationStatus",
    # UI 이벤트
    "StatusBarUpdateEvent",
    "ProgressUpdateEvent",
    "FileCountUpdateEvent",
    "MemoryUsageUpdateEvent",
    "UIStateUpdateEvent",
    "ErrorMessageEvent",
    "SuccessMessageEvent",
    "TableDataUpdateEvent",
    "WindowTitleUpdateEvent",
    "MenuStateUpdateEvent",
    "ThemeUpdateEvent",
    # 백그라운드 작업 이벤트
    "TaskStatus",
    "TaskPriority",
    "TaskStartedEvent",
    "TaskProgressEvent",
    "TaskCompletedEvent",
    "TaskFailedEvent",
    "TaskCancelledEvent",
    "TaskQueueStatusEvent",
    "TaskRetryEvent",
    # 백그라운드 작업 클래스
    "BaseTask",
    "TaskResult",
    "TaskSignals",
    # 서비스
    "IFileScanService",
    "FileScanService",
    "IUIUpdateService",
    "UIUpdateService",
    "IBackgroundTaskService",
    "BackgroundTaskService",
    # 초기화
    "initialize_application",
    "cleanup_application",
    "get_service",
]
