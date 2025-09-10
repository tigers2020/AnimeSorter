"""
File Processing Progress Events

Comprehensive event system for tracking file processing operations with detailed progress information.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from .events import BaseEvent


class FileProcessingStatus(Enum):
    """File processing status"""

    STARTED = "started"
    SCANNING = "scanning"
    PARSING = "parsing"
    VALIDATING = "validating"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class FileOperationType(Enum):
    """File operation types for progress tracking"""

    SCAN = "scan"
    PARSE = "parse"
    VALIDATE = "validate"
    PLAN = "plan"
    COPY = "copy"
    MOVE = "move"
    RENAME = "rename"
    DELETE = "delete"
    BACKUP = "backup"
    RESTORE = "restore"


@dataclass
class FileProcessingStartedEvent(BaseEvent):
    """File processing operation started event"""

    operation_id: UUID = field(default_factory=uuid4)
    operation_type: str = "file_processing"
    total_files: int = 0
    total_size_bytes: int = 0
    estimated_duration_seconds: Optional[float] = None
    source_directory: Optional[Path] = None
    destination_directory: Optional[Path] = None
    processing_mode: str = "normal"  # normal, dry_run, simulation
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingProgressEvent(BaseEvent):
    """File processing progress event with detailed information"""

    operation_id: UUID = field(default_factory=uuid4)
    current_file_index: int = 0
    total_files: int = 0
    current_file_path: Optional[Path] = None
    current_file_size: int = 0
    bytes_processed: int = 0
    total_bytes: int = 0
    progress_percentage: float = 0.0
    current_operation: FileOperationType = FileOperationType.SCAN
    current_step: str = ""
    processing_speed_mbps: float = 0.0  # MB per second
    estimated_remaining_seconds: Optional[float] = None
    success_count: int = 0
    error_count: int = 0
    skip_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingStepEvent(BaseEvent):
    """File processing step change event"""

    operation_id: UUID = field(default_factory=uuid4)
    previous_step: str = ""
    current_step: str = ""
    step_progress: float = 0.0  # Progress within current step (0.0 - 1.0)
    step_description: str = ""
    estimated_step_duration_seconds: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingFileEvent(BaseEvent):
    """Individual file processing event"""

    file_path: Optional[Path] = None
    file_size: int = 0
    operation_type: FileOperationType = FileOperationType.SCAN
    status: FileProcessingStatus = FileProcessingStatus.STARTED
    operation_id: UUID = field(default_factory=uuid4)
    processing_time_seconds: float = 0.0
    error_message: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingBatchEvent(BaseEvent):
    """Batch file processing event"""

    operation_id: UUID = field(default_factory=uuid4)
    batch_index: int = 0
    total_batches: int = 0
    batch_size: int = 0
    files_in_batch: list[Path] = field(default_factory=list)
    batch_progress_percentage: float = 0.0
    estimated_batch_duration_seconds: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingSpeedEvent(BaseEvent):
    """File processing speed update event"""

    operation_id: UUID = field(default_factory=uuid4)
    current_speed_mbps: float = 0.0
    average_speed_mbps: float = 0.0
    peak_speed_mbps: float = 0.0
    speed_trend: str = "stable"  # increasing, decreasing, stable
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingStatisticsEvent(BaseEvent):
    """File processing statistics update event"""

    operation_id: UUID = field(default_factory=uuid4)
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_size_bytes: int = 0
    processed_size_bytes: int = 0
    average_file_size_bytes: float = 0.0
    processing_time_seconds: float = 0.0
    average_processing_time_per_file: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingCompletedEvent(BaseEvent):
    """File processing operation completed event"""

    operation_id: UUID = field(default_factory=uuid4)
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_size_bytes: int = 0
    processed_size_bytes: int = 0
    total_processing_time_seconds: float = 0.0
    average_speed_mbps: float = 0.0
    peak_speed_mbps: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingFailedEvent(BaseEvent):
    """File processing operation failed event"""

    error_message: str = ""
    operation_id: UUID = field(default_factory=uuid4)
    error_type: str = "unknown"
    failed_at_step: str = ""
    processed_files_before_failure: int = 0
    total_files: int = 0
    partial_results: Optional[dict[str, Any]] = None
    can_retry: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingCancelledEvent(BaseEvent):
    """File processing operation cancelled event"""

    operation_id: UUID = field(default_factory=uuid4)
    cancelled_at_step: str = ""
    processed_files_before_cancellation: int = 0
    total_files: int = 0
    cancellation_reason: str = "user_requested"
    partial_results: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingPausedEvent(BaseEvent):
    """File processing operation paused event"""

    operation_id: UUID = field(default_factory=uuid4)
    paused_at_step: str = ""
    processed_files_before_pause: int = 0
    total_files: int = 0
    pause_reason: str = "user_requested"
    can_resume: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileProcessingResumedEvent(BaseEvent):
    """File processing operation resumed event"""

    operation_id: UUID = field(default_factory=uuid4)
    resumed_at_step: str = ""
    processed_files_before_pause: int = 0
    total_files: int = 0
    pause_duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# Progress callback type definitions
from typing import Protocol


class ProgressCallback(Protocol):
    """Progress callback protocol for file processing operations"""

    def __call__(
        self,
        current: int,
        total: int,
        current_file: Optional[Path] = None,
        operation_type: FileOperationType = FileOperationType.SCAN,
        step: str = "",
        speed_mbps: float = 0.0,
        **kwargs: Any,
    ) -> None:
        """Progress callback function"""
        ...


class DetailedProgressCallback(Protocol):
    """Detailed progress callback protocol with comprehensive information"""

    def __call__(self, progress_event: FileProcessingProgressEvent) -> None:
        """Detailed progress callback function"""
        ...


# Utility functions for progress calculation
def calculate_progress_percentage(current: int, total: int) -> float:
    """Calculate progress percentage"""
    if total <= 0:
        return 0.0
    return min(100.0, max(0.0, (current / total) * 100.0))


def calculate_processing_speed(bytes_processed: int, time_elapsed_seconds: float) -> float:
    """Calculate processing speed in MB/s"""
    if time_elapsed_seconds <= 0:
        return 0.0
    return (bytes_processed / (1024 * 1024)) / time_elapsed_seconds


def estimate_remaining_time(
    bytes_processed: int, total_bytes: int, time_elapsed_seconds: float
) -> Optional[float]:
    """Estimate remaining processing time in seconds"""
    if bytes_processed <= 0 or time_elapsed_seconds <= 0:
        return None

    remaining_bytes = total_bytes - bytes_processed
    if remaining_bytes <= 0:
        return 0.0

    speed_mbps = calculate_processing_speed(bytes_processed, time_elapsed_seconds)
    if speed_mbps <= 0:
        return None

    remaining_mb = remaining_bytes / (1024 * 1024)
    return remaining_mb / speed_mbps
