"""
Unified File Organization Interface

This module defines the core interfaces for file organization operations,
providing a consistent contract for all file handling operations across the application.
"""

import logging

logger = logging.getLogger(__name__)
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.core.types import FileOperationResult


class FileOperationType(Enum):
    """File operation types"""

    COPY = "copy"
    MOVE = "move"
    RENAME = "rename"
    DELETE = "delete"
    BACKUP = "backup"


class FileConflictResolution(Enum):
    """File conflict resolution strategies"""

    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"
    BACKUP_AND_OVERWRITE = "backup_and_overwrite"


@dataclass
class FileOperationPlan:
    """Represents a planned file operation"""

    source_path: Path
    target_path: Path
    operation_type: FileOperationType
    backup_path: Path | None = None
    conflict_resolution: FileConflictResolution = FileConflictResolution.RENAME
    estimated_size: int = 0
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FileScanResult:
    """Result of file scanning operation"""

    files_found: list[Path]
    total_size: int
    scan_duration: float
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class IFileScanner(ABC):
    """Interface for file scanning operations"""

    @abstractmethod
    def scan_directory(
        self, directory_path: Path, recursive: bool = True, file_extensions: set[str] = None
    ) -> FileScanResult:
        """Scan directory for files matching criteria"""

    @abstractmethod
    def validate_file(self, file_path: Path) -> bool:
        """Validate if file is processable"""


class IFileNamingStrategy(ABC):
    """Interface for file naming strategies"""

    @abstractmethod
    def generate_target_path(
        self, source_path: Path, metadata: dict[str, Any], destination_root: Path
    ) -> Path:
        """Generate target path based on naming strategy"""

    @abstractmethod
    def resolve_conflict(self, target_path: Path, resolution: FileConflictResolution) -> Path:
        """Resolve file naming conflicts"""


class IFileOperationExecutor(ABC):
    """Interface for executing file operations"""

    @abstractmethod
    def execute_operation(self, plan: FileOperationPlan) -> FileOperationResult:
        """Execute a single file operation"""

    @abstractmethod
    def execute_batch_operations(
        self,
        plans: list[FileOperationPlan],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[FileOperationResult]:
        """Execute multiple file operations in batch"""

    @abstractmethod
    def simulate_operations(self, plans: list[FileOperationPlan]) -> dict[str, Any]:
        """Simulate file operations without executing them"""


class IFileBackupManager(ABC):
    """Interface for file backup operations"""

    @abstractmethod
    def create_backup(self, file_path: Path) -> Path:
        """Create backup of a file"""

    @abstractmethod
    def restore_backup(self, backup_path: Path, target_path: Path) -> bool:
        """Restore file from backup"""

    @abstractmethod
    def cleanup_old_backups(self, max_age_days: int = 30) -> int:
        """Clean up old backup files"""


class IFileOrganizationService(ABC):
    """Main interface for file organization operations"""

    @abstractmethod
    def scan_and_plan_organization(
        self,
        source_directory: Path,
        destination_root: Path,
        naming_strategy: str = "standard",
        operation_type: FileOperationType = FileOperationType.COPY,
    ) -> list[FileOperationPlan]:
        """Scan directory and create organization plan"""

    @abstractmethod
    def execute_organization_plan(
        self,
        plans: list[FileOperationPlan],
        dry_run: bool = True,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[FileOperationResult]:
        """Execute file organization plan"""

    @abstractmethod
    def validate_organization_plan(self, plans: list[FileOperationPlan]) -> dict[str, Any]:
        """Validate organization plan for conflicts and issues"""

    @abstractmethod
    def get_organization_statistics(self, plans: list[FileOperationPlan]) -> dict[str, Any]:
        """Get statistics about organization plan"""
