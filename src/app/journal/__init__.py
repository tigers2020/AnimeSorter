"""
저널링 시스템

모든 파일 조작을 기록하고 필요 시 롤백할 수 있는 종합 시스템
"""

from .journal_entry import (
    FileOperationDetails,
    IJournalEntry,
    JournalEntry,
    JournalEntryStatus,
    JournalEntryType,
)
from .journal_events import (
    JournalCleanupEvent,
    JournalEntryCreatedEvent,
    JournalEntryUpdatedEvent,
    RollbackCompletedEvent,
    RollbackStartedEvent,
    TransactionCommittedEvent,
    TransactionRolledBackEvent,
    TransactionStartedEvent,
)
from .journal_manager import (
    IJournalManager,
    JournalConfiguration,
    JournalManager,
)
from .rollback_engine import (
    IRollbackEngine,
    RollbackEngine,
    RollbackResult,
    RollbackStrategy,
)
from .transaction import (
    ITransaction,
    Transaction,
    TransactionStatus,
)

__all__ = [
    # Journal Entry
    "JournalEntry",
    "JournalEntryType",
    "JournalEntryStatus",
    "FileOperationDetails",
    "IJournalEntry",
    # Transaction
    "Transaction",
    "TransactionStatus",
    "ITransaction",
    # Journal Manager
    "JournalManager",
    "IJournalManager",
    "JournalConfiguration",
    # Rollback Engine
    "RollbackEngine",
    "IRollbackEngine",
    "RollbackResult",
    "RollbackStrategy",
    # Events
    "JournalEntryCreatedEvent",
    "JournalEntryUpdatedEvent",
    "TransactionStartedEvent",
    "TransactionCommittedEvent",
    "TransactionRolledBackEvent",
    "RollbackStartedEvent",
    "RollbackCompletedEvent",
    "JournalCleanupEvent",
]
