"""
Backup service interface.

This module defines the interface for backup services,
providing a contract for file backup operations.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class IBackupService(ABC):
    """
    Interface for backup services.

    This interface defines the contract for file backup operations,
    ensuring consistent backup behavior across different implementations.
    """

    @abstractmethod
    def create_backup(self, source_path: Path, destination_dir: Path | None = None) -> Path:
        """
        Create a backup of the specified file.

        Args:
            source_path: Path to the file to backup
            destination_dir: Optional destination directory. If None, uses the
                           same directory as the source file

        Returns:
            Path to the created backup file

        Raises:
            FileNotFoundError: If source file doesn't exist
            OSError: If backup creation fails due to filesystem issues
            ValueError: If source_path is not a file
        """

    @abstractmethod
    def cleanup_old_backups(self, backup_dir: Path, max_age_days: int = 30) -> int:
        """
        Clean up old backup files older than the specified number of days.

        Args:
            backup_dir: Directory containing backup files
            max_age_days: Maximum age of backup files in days

        Returns:
            Number of files cleaned up
        """
