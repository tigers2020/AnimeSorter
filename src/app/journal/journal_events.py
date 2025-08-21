"""
저널링 시스템 이벤트

저널링 관련 모든 이벤트 정의
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from ..events import BaseEvent
from .rollback_engine import RollbackResult


@dataclass
class JournalEntryCreatedEvent(BaseEvent):
    """저널 엔트리 생성 이벤트"""

    entry_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    transaction_id: UUID | None = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    command_id: UUID | None = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    entry_type: str = ""  # JournalEntryType.value
    operation_description: str = ""
    source_path: Path | None = None
    destination_path: Path | None = None
    estimated_duration_ms: float | None = None


@dataclass
class JournalEntryUpdatedEvent(BaseEvent):
    """저널 엔트리 업데이트 이벤트"""

    entry_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    transaction_id: UUID | None = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    old_status: str = ""  # JournalEntryStatus.value
    new_status: str = ""  # JournalEntryStatus.value
    success: bool = False
    error_message: str | None = None
    execution_time_ms: float | None = None
    affected_files: list[Path] = field(default_factory=list)


@dataclass
class TransactionStartedEvent(BaseEvent):
    """트랜잭션 시작 이벤트"""

    transaction_id: UUID = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    transaction_name: str = ""
    description: str = ""
    parent_transaction_id: UUID | None = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    auto_rollback_on_failure: bool = True
    expected_entry_count: int | None = None


@dataclass
class TransactionCommittedEvent(BaseEvent):
    """트랜잭션 커밋 이벤트"""

    transaction_id: UUID = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    transaction_name: str = ""
    success: bool = True
    total_entries: int = 0
    successful_entries: int = 0
    failed_entries: int = 0
    execution_time_ms: float | None = None
    affected_files: list[Path] = field(default_factory=list)


@dataclass
class TransactionRolledBackEvent(BaseEvent):
    """트랜잭션 롤백 이벤트"""

    transaction_id: UUID = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    transaction_name: str = ""
    rollback_reason: str = ""
    rollback_strategy: str = ""  # RollbackStrategy.value
    successful_rollbacks: int = 0
    failed_rollbacks: int = 0
    rollback_time_ms: float | None = None
    recovery_instructions: list[str] = field(default_factory=list)


@dataclass
class TransactionFailedEvent(BaseEvent):
    """트랜잭션 실패 이벤트"""

    transaction_id: UUID = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    transaction_name: str = ""
    failure_reason: str = ""
    failed_entry_count: int = 0
    last_successful_entry_id: UUID | None = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    auto_rollback_attempted: bool = False
    rollback_success: bool = False


@dataclass
class RollbackStartedEvent(BaseEvent):
    """롤백 시작 이벤트"""

    rollback_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    target_transaction_id: UUID | None = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    target_entry_ids: list[UUID] = field(default_factory=list)
    rollback_strategy: str = ""  # RollbackStrategy.value
    rollback_reason: str = ""
    total_operations: int = 0
    is_automatic: bool = False


@dataclass
class RollbackProgressEvent(BaseEvent):
    """롤백 진행 상황 이벤트"""

    rollback_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    completed_operations: int = 0
    total_operations: int = 0
    current_entry_id: UUID | None = field(
        default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000")
    )
    current_operation: str = ""
    progress_percentage: float = 0.0
    estimated_remaining_ms: float | None = None


@dataclass
class RollbackCompletedEvent(BaseEvent):
    """롤백 완료 이벤트"""

    rollback_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    rollback_result: RollbackResult | None = None
    success: bool = False
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    skipped_operations: int = 0
    rollback_time_ms: float | None = None
    recovery_needed: bool = False
    recovery_instructions: list[str] = field(default_factory=list)


@dataclass
class JournalSavedEvent(BaseEvent):
    """저널 저장 이벤트"""

    journal_file_path: Path = field(default_factory=lambda: Path())
    total_transactions: int = 0
    total_entries: int = 0
    file_size_bytes: int = 0
    save_duration_ms: float | None = None
    backup_created: bool = False
    compression_used: bool = False


@dataclass
class JournalLoadedEvent(BaseEvent):
    """저널 로드 이벤트"""

    journal_file_path: Path = field(default_factory=lambda: Path())
    loaded_transactions: int = 0
    loaded_entries: int = 0
    file_size_bytes: int = 0
    load_duration_ms: float | None = None
    format_version: str = ""
    migration_performed: bool = False
    corrupted_entries: int = 0


@dataclass
class JournalCleanupEvent(BaseEvent):
    """저널 정리 이벤트"""

    cleanup_type: str = ""  # "automatic", "manual", "scheduled"
    removed_transactions: int = 0
    removed_entries: int = 0
    archived_transactions: int = 0
    compressed_files: int = 0
    freed_space_bytes: int = 0
    cleanup_duration_ms: float | None = None
    next_cleanup_scheduled: datetime | None = None


@dataclass
class JournalCorruptionDetectedEvent(BaseEvent):
    """저널 손상 감지 이벤트"""

    corruption_type: str = ""  # "file_corruption", "data_inconsistency", "missing_backup"
    affected_transactions: list[UUID] = field(default_factory=list)
    affected_entries: list[UUID] = field(default_factory=list)
    corruption_details: str = ""
    recovery_possible: bool = False
    backup_available: bool = False
    manual_intervention_required: bool = True


@dataclass
class JournalIntegrityCheckEvent(BaseEvent):
    """저널 무결성 검사 이벤트"""

    check_type: str = ""  # "startup", "scheduled", "manual"
    total_transactions_checked: int = 0
    total_entries_checked: int = 0
    inconsistencies_found: int = 0
    missing_files: int = 0
    orphaned_entries: int = 0
    check_duration_ms: float | None = None
    check_result: str = ""  # "passed", "warnings", "failed"
    recommendations: list[str] = field(default_factory=list)


@dataclass
class JournalPerformanceMetricsEvent(BaseEvent):
    """저널 성능 메트릭 이벤트"""

    metric_type: str = ""  # "hourly", "daily", "weekly"
    period_start: datetime = field(default_factory=datetime.now)
    period_end: datetime = field(default_factory=datetime.now)

    # 처리량 메트릭
    transactions_processed: int = 0
    entries_processed: int = 0
    average_transaction_time_ms: float = 0.0
    average_entry_time_ms: float = 0.0

    # 성공률 메트릭
    transaction_success_rate: float = 0.0
    entry_success_rate: float = 0.0
    rollback_success_rate: float = 0.0

    # 리소스 사용률
    memory_usage_mb: float = 0.0
    disk_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # 큐 상태
    pending_transactions: int = 0
    pending_entries: int = 0
    active_rollbacks: int = 0


@dataclass
class JournalConfigurationChangedEvent(BaseEvent):
    """저널 설정 변경 이벤트"""

    setting_name: str = ""
    old_value: Any = None
    new_value: Any = None
    change_reason: str = ""
    requires_restart: bool = False
    effective_immediately: bool = True


@dataclass
class JournalArchiveCreatedEvent(BaseEvent):
    """저널 아카이브 생성 이벤트"""

    archive_file_path: Path = field(default_factory=lambda: Path())
    archive_type: str = ""  # "monthly", "yearly", "manual"
    archived_period_start: datetime = field(default_factory=datetime.now)
    archived_period_end: datetime = field(default_factory=datetime.now)
    archived_transactions: int = 0
    archived_entries: int = 0
    original_size_bytes: int = 0
    compressed_size_bytes: int = 0
    compression_ratio: float = 0.0
