"""
Unified File Organization Service

This service consolidates all file organization logic from various managers
and services to eliminate code duplication and provide a single source of truth
for file operations.
"""

import logging
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from src.app.file_processing_events import (FileOperationType,
                                            FileProcessingProgressEvent,
                                            calculate_processing_speed,
                                            calculate_progress_percentage,
                                            estimate_remaining_time)
from src.core.backup.backup_manager import (BackupPolicy,
                                            CentralizedBackupManager)
from src.core.commands.file_operation_commands import (
    BatchFileOperationCommand, FileOperationCommand,
    FileOperationCommandInvoker)
from src.core.file_parser import FileParser
from src.core.file_validation import FileValidator
from src.core.interfaces.file_organization_interface import (
    FileConflictResolution, FileOperationPlan, FileOperationResult,
    FileOperationType, FileScanResult, IFileBackupManager, IFileNamingStrategy,
    IFileOperationExecutor, IFileOrganizationService, IFileScanner)
from src.core.strategies.file_naming_strategies import (NamingConfig,
                                                        NamingStrategyFactory)


@dataclass
class FileOrganizationConfig:
    """Configuration for file organization operations"""

    safe_mode: bool = True
    backup_before_operation: bool = True
    overwrite_existing: bool = False
    create_directories: bool = True
    max_path_length: int = 260
    min_file_size: int = 1024 * 1024  # 1MB
    video_extensions: set[str] = None
    subtitle_extensions: set[str] = None
    naming_strategy: str = "standard"
    naming_config: NamingConfig = None
    backup_policy: BackupPolicy = None

    # Enhanced unique filename generation settings
    max_unique_filename_attempts: int = 1000  # Maximum attempts for unique filename generation
    enable_timestamp_fallback: bool = True  # Enable timestamp fallback for unique names

    def __post_init__(self):
        if self.video_extensions is None:
            self.video_extensions = {
                ".mkv",
                ".mp4",
                ".avi",
                ".mov",
                ".wmv",
                ".flv",
                ".webm",
                ".m4v",
                ".mpg",
                ".mpeg",
                ".ts",
                ".m2ts",
            }
        if self.subtitle_extensions is None:
            self.subtitle_extensions = {
                ".srt",
                ".ass",
                ".ssa",
                ".sub",
                ".vtt",
                ".idx",
                ".smi",
                ".sami",
                ".txt",
            }
        if self.naming_config is None:
            self.naming_config = NamingConfig()
        if self.backup_policy is None:
            self.backup_policy = BackupPolicy()

        # Apply enhanced unique filename generation settings to naming config
        self.naming_config.max_unique_attempts = self.max_unique_filename_attempts
        self.naming_config.enable_timestamp_fallback = self.enable_timestamp_fallback


class UnifiedFileScanner(IFileScanner):
    """Unified file scanning implementation"""

    def __init__(self, config: FileOrganizationConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def scan_directory(
        self, directory_path: Path, recursive: bool = True, file_extensions: set[str] = None
    ) -> FileScanResult:
        """Scan directory for files matching criteria"""
        start_time = time.time()
        files_found = []
        errors = []

        try:
            if not directory_path.exists():
                errors.append(f"Directory does not exist: {directory_path}")
                return FileScanResult(files_found, 0, 0, errors)

            if file_extensions is None:
                file_extensions = self.config.video_extensions

            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"

            total_size = 0
            for file_path in directory_path.glob(pattern):
                if file_path.is_file() and file_path.suffix.lower() in file_extensions:
                    try:
                        file_size = file_path.stat().st_size
                        if file_size >= self.config.min_file_size:
                            files_found.append(file_path)
                            total_size += file_size
                    except OSError as e:
                        errors.append(f"Cannot access {file_path}: {e}")

            scan_duration = time.time() - start_time
            self.logger.info(
                f"Directory scan completed: {len(files_found)} files found in {scan_duration:.2f}s"
            )

            return FileScanResult(files_found, total_size, scan_duration, errors)

        except Exception as e:
            errors.append(f"Scan failed: {e}")
            self.logger.error(f"Directory scan failed: {e}")
            return FileScanResult(files_found, 0, time.time() - start_time, errors)

    def validate_file(self, file_path: Path) -> bool:
        """Validate if file is processable"""
        try:
            if not file_path.exists():
                return False

            if not file_path.is_file():
                return False

            # Check file size
            file_size = file_path.stat().st_size
            if file_size < self.config.min_file_size:
                return False

            # Check path length
            if len(str(file_path)) > self.config.max_path_length:
                return False

            return True

        except Exception as e:
            self.logger.error(f"File validation failed for {file_path}: {e}")
            return False


class StandardFileNamingStrategy(IFileNamingStrategy):
    """Standard file naming strategy implementation"""

    def __init__(self, config: FileOrganizationConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def generate_target_path(
        self, source_path: Path, metadata: dict[str, Any], destination_root: Path
    ) -> Path:
        """Generate target path based on naming strategy"""
        try:
            # Extract metadata
            title = metadata.get("title", "Unknown")
            season = metadata.get("season", 1)
            episode = metadata.get("episode", 1)
            resolution = metadata.get("resolution", "")

            # Sanitize title
            safe_title = self._sanitize_filename(title)

            # Create directory structure
            season_folder = f"Season{season:02d}"
            target_dir = destination_root / safe_title / season_folder

            # Generate filename
            filename = f"{safe_title} - S{season:02d}E{episode:02d}"
            if resolution and resolution != "Unknown":
                filename += f" [{resolution}]"

            filename += source_path.suffix

            return target_dir / filename

        except Exception as e:
            self.logger.error(f"Target path generation failed: {e}")
            return destination_root / source_path.name

    def resolve_conflict(self, target_path: Path, resolution: FileConflictResolution) -> Path:
        """Resolve file naming conflicts"""
        if not target_path.exists():
            return target_path

        if resolution == FileConflictResolution.SKIP:
            return target_path

        elif resolution == FileConflictResolution.OVERWRITE:
            return target_path

        elif resolution == FileConflictResolution.RENAME:
            counter = 1
            while True:
                stem = target_path.stem
                suffix = target_path.suffix
                new_name = f"{stem}_{counter}{suffix}"
                new_path = target_path.parent / new_name
                if not new_path.exists():
                    return new_path
                counter += 1

        elif resolution == FileConflictResolution.BACKUP_AND_OVERWRITE:
            # Create backup first
            backup_path = target_path.with_suffix(f"{target_path.suffix}.backup_{int(time.time())}")
            try:
                shutil.copy2(target_path, backup_path)
                self.logger.info(f"Backup created: {backup_path}")
            except Exception as e:
                self.logger.error(f"Backup creation failed: {e}")
            return target_path

        return target_path

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
        sanitized = filename

        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")

        # Normalize whitespace
        sanitized = " ".join(sanitized.split())
        sanitized = sanitized.strip()

        if not sanitized:
            sanitized = "Unknown"

        return sanitized


class UnifiedFileOperationExecutor(IFileOperationExecutor):
    """Unified file operation execution implementation"""

    def __init__(
        self,
        config: FileOrganizationConfig,
        logger: logging.Logger,
        naming_strategy: IFileNamingStrategy,
    ):
        self.config = config
        self.logger = logger
        self.naming_strategy = naming_strategy
        self.operation_id = uuid4()
        self.start_time = None
        self.processed_bytes = 0
        self.total_bytes = 0
        self.success_count = 0
        self.error_count = 0
        self.skip_count = 0

    def execute_operation(self, plan: FileOperationPlan) -> FileOperationResult:
        """Execute a single file operation"""
        start_time = time.time()

        try:
            # Validate source file
            if not plan.source_path.exists():
                return FileOperationResult(
                    success=False,
                    source_path=plan.source_path,
                    target_path=plan.target_path,
                    operation_type=plan.operation_type,
                    error_message="Source file does not exist",
                )

            # Create target directory if needed
            if self.config.create_directories:
                plan.target_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle conflicts - use rename strategy instead of failing
            if plan.target_path.exists():
                if not self.config.overwrite_existing:
                    # Resolve conflict by renaming
                    plan.target_path = self.naming_strategy.resolve_conflict(
                        plan.target_path, FileConflictResolution.RENAME
                    )
                    print(f"🔍 해상도 추출 시도: {plan.source_path.name}")
                    print(f"  ✅ 패턴 매칭: (충돌 해결) -> {plan.target_path.name}")

            # Create backup if needed
            backup_path = None
            if self.config.backup_before_operation and plan.target_path.exists():
                backup_path = plan.target_path.with_suffix(
                    f"{plan.target_path.suffix}.backup_{int(time.time())}"
                )
                shutil.copy2(plan.target_path, backup_path)

            # Execute operation
            if plan.operation_type == FileOperationType.COPY:
                shutil.copy2(plan.source_path, plan.target_path)
            elif plan.operation_type == FileOperationType.MOVE:
                shutil.move(plan.source_path, plan.target_path)
            elif plan.operation_type == FileOperationType.RENAME:
                plan.source_path.rename(plan.target_path)
            else:
                raise ValueError(f"Unsupported operation type: {plan.operation_type}")

            # Get actual file size
            actual_size = plan.target_path.stat().st_size if plan.target_path.exists() else 0
            processing_time = time.time() - start_time

            self.logger.info(
                f"File operation completed: {plan.source_path.name} -> {plan.target_path.name}"
            )

            return FileOperationResult(
                success=True,
                source_path=plan.source_path,
                target_path=plan.target_path,
                operation_type=plan.operation_type,
                backup_path=backup_path,
                actual_size=actual_size,
                processing_time=processing_time,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"File operation failed: {e}")

            return FileOperationResult(
                success=False,
                source_path=plan.source_path,
                target_path=plan.target_path,
                operation_type=plan.operation_type,
                error_message=str(e),
                processing_time=processing_time,
            )

    def execute_batch_operations(
        self,
        plans: list[FileOperationPlan],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        detailed_progress_callback: Optional[Callable[[FileProcessingProgressEvent], None]] = None,
    ) -> list[FileOperationResult]:
        """Execute multiple file operations in batch with detailed progress tracking"""
        self.operation_id = uuid4()
        self.start_time = time.time()
        self.processed_bytes = 0
        self.total_bytes = sum(plan.estimated_size for plan in plans)
        self.success_count = 0
        self.error_count = 0
        self.skip_count = 0

        results = []
        total_plans = len(plans)

        for i, plan in enumerate(plans):
            # Calculate progress before operation
            progress_percentage = calculate_progress_percentage(i, total_plans)
            time_elapsed = time.time() - self.start_time
            speed_mbps = calculate_processing_speed(self.processed_bytes, time_elapsed)
            remaining_time = estimate_remaining_time(
                self.processed_bytes, self.total_bytes, time_elapsed
            )

            # Create detailed progress event
            if detailed_progress_callback:
                progress_event = FileProcessingProgressEvent(
                    operation_id=self.operation_id,
                    current_file_index=i,
                    total_files=total_plans,
                    current_file_path=plan.source_path,
                    current_file_size=plan.estimated_size,
                    bytes_processed=self.processed_bytes,
                    total_bytes=self.total_bytes,
                    progress_percentage=progress_percentage,
                    current_operation=(
                        FileOperationType.COPY
                        if plan.operation_type.value == "copy"
                        else FileOperationType.MOVE
                    ),
                    current_step=f"Processing {plan.source_path.name}",
                    processing_speed_mbps=speed_mbps,
                    estimated_remaining_seconds=remaining_time,
                    success_count=self.success_count,
                    error_count=self.error_count,
                    skip_count=self.skip_count,
                )
                detailed_progress_callback(progress_event)

            # Execute operation
            result = self.execute_operation(plan)
            results.append(result)

            # Update statistics
            if result.success:
                self.success_count += 1
                self.processed_bytes += plan.estimated_size
            else:
                self.error_count += 1

            # Simple progress callback for backward compatibility
            if progress_callback:
                progress_callback(i + 1, total_plans)

        return results

    def simulate_operations(self, plans: list[FileOperationPlan]) -> dict[str, Any]:
        """Simulate file operations without executing them"""
        simulation_results = {
            "total_plans": len(plans),
            "successful": 0,
            "conflicts": 0,
            "errors": 0,
            "total_size": 0,
            "details": [],
        }

        for plan in plans:
            detail = {
                "source": str(plan.source_path),
                "target": str(plan.target_path),
                "operation": plan.operation_type.value,
                "status": "success",
                "issues": [],
            }

            # Check for conflicts
            if plan.target_path.exists():
                detail["status"] = "conflict"
                detail["issues"].append("Target file already exists")
                simulation_results["conflicts"] += 1
            else:
                simulation_results["successful"] += 1

            # Check source file
            if not plan.source_path.exists():
                detail["status"] = "error"
                detail["issues"].append("Source file does not exist")
                simulation_results["errors"] += 1

            # Calculate size
            if plan.source_path.exists():
                try:
                    file_size = plan.source_path.stat().st_size
                    simulation_results["total_size"] += file_size
                    detail["size"] = file_size
                except OSError:
                    detail["issues"].append("Cannot access source file")

            simulation_results["details"].append(detail)

        return simulation_results


class UnifiedFileBackupManager(IFileBackupManager):
    """Unified file backup management implementation"""

    def __init__(self, backup_root: Path, config: FileOrganizationConfig, logger: logging.Logger):
        self.backup_root = backup_root
        self.config = config
        self.logger = logger

    def create_backup(self, file_path: Path) -> Path:
        """Create backup of a file"""
        try:
            timestamp = int(time.time())
            backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
            backup_path = self.backup_root / backup_name

            # Ensure backup directory exists
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(file_path, backup_path)
            self.logger.info(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.error(f"Backup creation failed for {file_path}: {e}")
            raise

    def restore_backup(self, backup_path: Path, target_path: Path) -> bool:
        """Restore file from backup"""
        try:
            if not backup_path.exists():
                self.logger.error(f"Backup file does not exist: {backup_path}")
                return False

            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(backup_path, target_path)
            self.logger.info(f"File restored from backup: {target_path}")
            return True

        except Exception as e:
            self.logger.error(f"Backup restore failed: {e}")
            return False

    def cleanup_old_backups(self, max_age_days: int = 30) -> int:
        """Clean up old backup files"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            cleaned_count = 0

            for backup_file in self.backup_root.rglob("*"):
                if backup_file.is_file():
                    file_age = current_time - backup_file.stat().st_mtime
                    if file_age > max_age_seconds:
                        backup_file.unlink()
                        cleaned_count += 1

            self.logger.info(f"Cleaned up {cleaned_count} old backup files")
            return cleaned_count

        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")
            return 0


class UnifiedFileOrganizationService(IFileOrganizationService):
    """Unified file organization service implementation with Command pattern support"""

    def __init__(self, config: FileOrganizationConfig = None, logger: logging.Logger = None):
        self.config = config or FileOrganizationConfig()
        self.logger = logger or logging.getLogger(__name__)

        # Initialize components
        self.scanner = UnifiedFileScanner(self.config, self.logger)

        # Initialize naming strategy using factory
        self.naming_strategy = NamingStrategyFactory.create_strategy(
            self.config.naming_strategy, self.config.naming_config, self.logger
        )

        self.operation_executor = UnifiedFileOperationExecutor(
            self.config, self.logger, self.naming_strategy
        )

        # Initialize centralized backup manager
        self.backup_manager = CentralizedBackupManager(
            Path("_backup"), self.config.backup_policy, self.logger
        )

        # Initialize parsers
        self.file_parser = FileParser()
        self.file_validator = FileValidator()

        # Initialize command invoker for undo/redo support
        self.command_invoker = FileOperationCommandInvoker(self.logger)

        self.logger.info("UnifiedFileOrganizationService initialized with Command pattern support")

    def scan_and_plan_organization(
        self,
        source_directory: Path,
        destination_root: Path,
        naming_strategy: str = "standard",
        operation_type: FileOperationType = FileOperationType.COPY,
    ) -> list[FileOperationPlan]:
        """Scan directory and create organization plan"""
        try:
            # Scan for files
            scan_result = self.scanner.scan_directory(source_directory)

            if not scan_result.files_found:
                self.logger.warning("No files found for organization")
                return []

            plans = []

            for file_path in scan_result.files_found:
                try:
                    # Parse file metadata
                    parsed_metadata = self.file_parser.parse_filename(str(file_path))

                    if not parsed_metadata or not parsed_metadata.title:
                        self.logger.warning(f"Could not parse metadata for {file_path}")
                        continue

                    # Prepare metadata for naming strategy
                    metadata = {
                        "title": parsed_metadata.title,
                        "season": parsed_metadata.season or 1,
                        "episode": parsed_metadata.episode or 1,
                        "resolution": parsed_metadata.resolution or "Unknown",
                        "year": parsed_metadata.year,
                        "group": parsed_metadata.group or "Unknown",
                    }

                    # Generate target path
                    target_path = self.naming_strategy.generate_target_path(
                        file_path, metadata, destination_root
                    )

                    # Resolve conflicts
                    target_path = self.naming_strategy.resolve_conflict(
                        target_path, FileConflictResolution.RENAME
                    )

                    # Create operation plan
                    plan = FileOperationPlan(
                        source_path=file_path,
                        target_path=target_path,
                        operation_type=operation_type,
                        estimated_size=file_path.stat().st_size,
                        metadata=metadata,
                    )

                    plans.append(plan)

                except Exception as e:
                    self.logger.error(f"Failed to create plan for {file_path}: {e}")

            self.logger.info(f"Created {len(plans)} organization plans")
            return plans

        except Exception as e:
            self.logger.error(f"Organization planning failed: {e}")
            return []

    def execute_organization_plan(
        self,
        plans: list[FileOperationPlan],
        dry_run: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        detailed_progress_callback: Optional[Callable[[FileProcessingProgressEvent], None]] = None,
    ) -> list[FileOperationResult]:
        """Execute file organization plan with detailed progress tracking"""
        if dry_run:
            self.logger.info("Executing organization plan in dry-run mode")
            return self.operation_executor.simulate_operations(plans)
        else:
            self.logger.info("Executing organization plan")
            return self.operation_executor.execute_batch_operations(
                plans, progress_callback, detailed_progress_callback
            )

    def validate_organization_plan(self, plans: list[FileOperationPlan]) -> dict[str, Any]:
        """Validate organization plan for conflicts and issues"""
        validation_result = {
            "valid": True,
            "total_plans": len(plans),
            "conflicts": 0,
            "errors": 0,
            "warnings": 0,
            "issues": [],
        }

        for i, plan in enumerate(plans):
            issues = []

            # Check source file
            if not plan.source_path.exists():
                issues.append(f"Source file does not exist: {plan.source_path}")
                validation_result["errors"] += 1

            # Check target conflicts
            if plan.target_path.exists():
                issues.append(f"Target file already exists: {plan.target_path}")
                validation_result["conflicts"] += 1

            # Check path length
            if len(str(plan.target_path)) > self.config.max_path_length:
                issues.append(f"Target path too long: {len(str(plan.target_path))} characters")
                validation_result["warnings"] += 1

            # Check directory permissions
            try:
                plan.target_path.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                issues.append(f"Cannot create target directory: {plan.target_path.parent}")
                validation_result["errors"] += 1

            if issues:
                validation_result["issues"].append(
                    {
                        "plan_index": i,
                        "source": str(plan.source_path),
                        "target": str(plan.target_path),
                        "issues": issues,
                    }
                )

        if validation_result["errors"] > 0 or validation_result["conflicts"] > 0:
            validation_result["valid"] = False

        return validation_result

    def get_organization_statistics(self, plans: list[FileOperationPlan]) -> dict[str, Any]:
        """Get statistics about organization plan"""
        total_size = sum(plan.estimated_size for plan in plans)

        # Count by operation type
        operation_counts = {}
        for plan in plans:
            op_type = plan.operation_type.value
            operation_counts[op_type] = operation_counts.get(op_type, 0) + 1

        # Estimate processing time (rough calculation)
        estimated_time = total_size / (100 * 1024 * 1024)  # Assume 100MB/s processing speed

        return {
            "total_plans": len(plans),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "operation_counts": operation_counts,
            "estimated_time_seconds": max(1, int(estimated_time)),
            "average_file_size_mb": (total_size / len(plans)) / (1024 * 1024) if plans else 0,
        }

    def execute_organization_with_commands(
        self,
        plans: list[FileOperationPlan],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        detailed_progress_callback: Optional[Callable[[FileProcessingProgressEvent], None]] = None,
    ) -> dict[str, Any]:
        """Execute organization plan using Command pattern for undo/redo support with progress tracking"""
        try:
            operation_id = uuid4()
            start_time = time.time()
            total_plans = len(plans)

            # Convert plans to commands
            commands = []
            for i, plan in enumerate(plans):
                command = FileOperationCommand(
                    plan.source_path, plan.target_path, plan.operation_type, self.logger
                )
                commands.append(command)

                # Progress callback for command creation
                if detailed_progress_callback:
                    progress_event = FileProcessingProgressEvent(
                        operation_id=operation_id,
                        current_file_index=i,
                        total_files=total_plans,
                        current_file_path=plan.source_path,
                        current_file_size=plan.estimated_size,
                        progress_percentage=calculate_progress_percentage(i, total_plans),
                        current_operation=(
                            FileOperationType.COPY
                            if plan.operation_type.value == "copy"
                            else FileOperationType.MOVE
                        ),
                        current_step="Preparing commands",
                    )
                    detailed_progress_callback(progress_event)

            # Create batch command
            batch_command = BatchFileOperationCommand(commands, self.logger)

            # Execute using command invoker
            result = self.command_invoker.execute_command(batch_command)

            # Final progress callback
            if progress_callback:
                progress_callback(len(plans), len(plans))

            if detailed_progress_callback:
                final_progress_event = FileProcessingProgressEvent(
                    operation_id=operation_id,
                    current_file_index=total_plans,
                    total_files=total_plans,
                    progress_percentage=100.0,
                    current_step="Command execution completed",
                )
                detailed_progress_callback(final_progress_event)

            return {
                "success": result.success,
                "message": result.message,
                "data": result.data,
                "error": result.error,
            }

        except Exception as e:
            self.logger.error(f"Command-based organization execution failed: {e}")
            return {
                "success": False,
                "message": f"Organization execution failed: {str(e)}",
                "error": str(e),
            }

    def undo_last_organization(self) -> dict[str, Any]:
        """Undo the last organization operation"""
        try:
            result = self.command_invoker.undo_last_command()
            return {"success": result.success, "message": result.message, "error": result.error}
        except Exception as e:
            self.logger.error(f"Undo operation failed: {e}")
            return {"success": False, "message": f"Undo failed: {str(e)}", "error": str(e)}

    def redo_last_organization(self) -> dict[str, Any]:
        """Redo the last undone organization operation"""
        try:
            result = self.command_invoker.redo_last_command()
            return {"success": result.success, "message": result.message, "error": result.error}
        except Exception as e:
            self.logger.error(f"Redo operation failed: {e}")
            return {"success": False, "message": f"Redo failed: {str(e)}", "error": str(e)}

    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return self.command_invoker.can_undo()

    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return self.command_invoker.can_redo()

    def get_command_history(self) -> list[str]:
        """Get command history descriptions"""
        return self.command_invoker.get_history_description()

    def clear_command_history(self):
        """Clear command history"""
        self.command_invoker.clear_history()
        self.logger.info("Command history cleared")

    def set_naming_strategy(self, strategy_name: str, config: NamingConfig = None):
        """Change the naming strategy"""
        try:
            self.naming_strategy = NamingStrategyFactory.create_strategy(
                strategy_name, config or self.config.naming_config, self.logger
            )
            self.config.naming_strategy = strategy_name
            if config:
                self.config.naming_config = config
            self.logger.info(f"Naming strategy changed to: {strategy_name}")
        except ValueError as e:
            self.logger.error(f"Failed to set naming strategy: {e}")
            raise

    def get_available_naming_strategies(self) -> list[str]:
        """Get list of available naming strategies"""
        return NamingStrategyFactory.get_available_strategies()

    def get_naming_strategy_description(self, strategy_name: str) -> str:
        """Get description of a naming strategy"""
        return NamingStrategyFactory.get_strategy_description(strategy_name)

    def get_current_naming_strategy(self) -> str:
        """Get current naming strategy name"""
        return self.config.naming_strategy

    def get_backup_stats(self) -> dict[str, Any]:
        """Get backup statistics"""
        return self.backup_manager.get_backup_stats()

    def list_backups(self, original_path: Path = None) -> list[Any]:
        """List all backups or backups for a specific file"""
        return self.backup_manager.list_backups(original_path)

    def cleanup_backups(self, max_age_days: int = None) -> int:
        """Clean up old backup files"""
        return self.backup_manager.cleanup_old_backups(max_age_days)

    def set_backup_policy(self, policy: BackupPolicy):
        """Update backup policy"""
        self.config.backup_policy = policy
        # Reinitialize backup manager with new policy
        self.backup_manager = CentralizedBackupManager(Path("_backup"), policy, self.logger)
        self.logger.info("Backup policy updated")

    def get_backup_policy(self) -> BackupPolicy:
        """Get current backup policy"""
        return self.config.backup_policy
