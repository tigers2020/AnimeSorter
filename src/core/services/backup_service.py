"""
Backup service for handling file backups with standardized policies.

This module provides a centralized backup service that implements consistent
backup policies across the application, including timestamp-based naming,
metadata preservation, and proper error handling.
"""

import shutil
from datetime import datetime
from pathlib import Path

from src.core.interfaces.backup_interface import IBackupService
from src.core.structured_logging import get_logger

logger = get_logger(__name__)


class BackupService(IBackupService):
    """
    Centralized service for handling file backups with standardized policies.

    This service provides a consistent interface for creating backups of files
    with timestamp-based naming, metadata preservation, and proper error handling.
    """

    def __init__(self):
        """Initialize the BackupService."""
        self.logger = logger

    def create_backup(self, source_path: Path, destination_dir: Path | None = None) -> Path:
        """
        Create a backup of the specified file with standardized naming and policies.

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
        # Validate source file
        if not source_path.exists():
            error_msg = f"Source file does not exist: {source_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        if not source_path.is_file():
            error_msg = f"Source path is not a file: {source_path}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # Determine backup destination directory
        if destination_dir is None:
            backup_dir = source_path.parent / ".backup"
        else:
            backup_dir = destination_dir / ".backup"

        try:
            # Create backup directory if it doesn't exist
            backup_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Backup directory ensured: {backup_dir}")

            # Generate backup filename with timestamp
            backup_filename = self._generate_backup_filename(source_path)
            backup_path = backup_dir / backup_filename

            # Ensure backup filename is unique
            backup_path = self._ensure_unique_filename(backup_path)

            # Create backup using shutil.copy2 to preserve metadata
            shutil.copy2(source_path, backup_path)
            self.logger.info(f"Backup created successfully: {source_path} -> {backup_path}")

            return backup_path

        except OSError as e:
            error_msg = f"Failed to create backup for {source_path}: {e}"
            self.logger.error(error_msg)
            raise OSError(error_msg) from e

    def _generate_backup_filename(self, source_path: Path) -> str:
        """
        Generate a backup filename with timestamp.

        Args:
            source_path: Path to the original file

        Returns:
            Backup filename with timestamp format: original_name_YYYYMMDD_HHMMSS_MS.ext
        """
        # Get current timestamp
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Remove last 3 digits of microseconds

        # Split filename and extension
        stem = source_path.stem
        suffix = source_path.suffix

        # Create backup filename
        backup_filename = f"{stem}_{timestamp}{suffix}"

        self.logger.debug(f"Generated backup filename: {backup_filename}")
        return backup_filename

    def _ensure_unique_filename(self, backup_path: Path) -> Path:
        """
        Ensure the backup filename is unique by adding a counter if needed.

        Args:
            backup_path: Initial backup path

        Returns:
            Unique backup path
        """
        if not backup_path.exists():
            return backup_path

        # If file exists, add a counter
        counter = 1
        stem = backup_path.stem
        suffix = backup_path.suffix
        parent = backup_path.parent

        while True:
            new_filename = f"{stem}_{counter:03d}{suffix}"
            new_path = parent / new_filename

            if not new_path.exists():
                self.logger.debug(f"Ensured unique backup filename: {new_path}")
                return new_path

            counter += 1

            # Safety check to prevent infinite loop
            if counter > 999:
                raise OSError(f"Unable to generate unique backup filename for {backup_path}")

    def cleanup_old_backups(self, backup_dir: Path, max_age_days: int = 30) -> int:
        """
        Clean up old backup files older than the specified number of days.

        Args:
            backup_dir: Directory containing backup files
            max_age_days: Maximum age of backup files in days

        Returns:
            Number of files cleaned up
        """
        if not backup_dir.exists() or not backup_dir.is_dir():
            self.logger.warning(f"Backup directory does not exist: {backup_dir}")
            return 0

        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
        cleaned_count = 0

        try:
            for backup_file in backup_dir.iterdir():
                if backup_file.is_file():
                    file_age = backup_file.stat().st_mtime
                    if file_age < cutoff_time:
                        backup_file.unlink()
                        cleaned_count += 1
                        self.logger.info(f"Cleaned up old backup: {backup_file}")

            self.logger.info(f"Cleaned up {cleaned_count} old backup files from {backup_dir}")
            return cleaned_count

        except OSError as e:
            error_msg = f"Failed to cleanup old backups in {backup_dir}: {e}"
            self.logger.error(error_msg)
            raise OSError(error_msg) from e
