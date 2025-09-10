"""
File Operation Commands

This module implements the Command pattern for file operations,
providing a centralized way to execute, undo, and manage file operations.
"""

import logging
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.core.interfaces.file_organization_interface import FileOperationType


@dataclass
class CommandResult:
    """Result of a command execution"""

    success: bool
    message: str
    data: dict[str, Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class IFileCommand(ABC):
    """Interface for file operation commands"""

    @abstractmethod
    def execute(self) -> CommandResult:
        """Execute the command"""

    @abstractmethod
    def undo(self) -> CommandResult:
        """Undo the command"""

    @abstractmethod
    def can_undo(self) -> bool:
        """Check if the command can be undone"""

    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of the command"""


class FileOperationCommand(IFileCommand):
    """Base class for file operation commands"""

    def __init__(
        self,
        source_path: Path,
        target_path: Path,
        operation_type: FileOperationType,
        logger: logging.Logger = None,
    ):
        self.source_path = source_path
        self.target_path = target_path
        self.operation_type = operation_type
        self.logger = logger or logging.getLogger(__name__)
        self._executed = False
        self._backup_path: Optional[Path] = None

    def execute(self) -> CommandResult:
        """Execute the file operation"""
        try:
            if self._executed:
                return CommandResult(
                    success=False,
                    message="Command already executed",
                    error="Command has already been executed",
                )

            # Validate source file
            if not self.source_path.exists():
                return CommandResult(
                    success=False,
                    message=f"Source file does not exist: {self.source_path}",
                    error="Source file not found",
                )

            # Create target directory if needed
            self.target_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle existing target file
            if self.target_path.exists():
                self._backup_path = self._create_backup()
                if not self._backup_path:
                    return CommandResult(
                        success=False,
                        message="Failed to create backup for existing file",
                        error="Backup creation failed",
                    )

            # Execute the operation
            result = self._perform_operation()
            if result.success:
                self._executed = True
                self.logger.info(f"File operation completed: {self.get_description()}")
            else:
                self.logger.error(f"File operation failed: {result.message}")

            return result

        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return CommandResult(
                success=False, message=f"Command execution failed: {str(e)}", error=str(e)
            )

    def undo(self) -> CommandResult:
        """Undo the file operation"""
        try:
            if not self._executed:
                return CommandResult(
                    success=False,
                    message="Command not executed yet",
                    error="Cannot undo unexecuted command",
                )

            if not self.can_undo():
                return CommandResult(
                    success=False,
                    message="Command cannot be undone",
                    error="Undo not supported for this operation type",
                )

            # Restore from backup if available
            if self._backup_path and self._backup_path.exists():
                shutil.move(str(self._backup_path), str(self.target_path))
                self._backup_path.unlink()  # Remove backup file
                self.logger.info(f"File operation undone: {self.get_description()}")
                return CommandResult(success=True, message="Operation undone successfully")
            else:
                # Try to reverse the operation
                return self._reverse_operation()

        except Exception as e:
            self.logger.error(f"Command undo failed: {e}")
            return CommandResult(
                success=False, message=f"Command undo failed: {str(e)}", error=str(e)
            )

    def can_undo(self) -> bool:
        """Check if the command can be undone"""
        return self.operation_type in [FileOperationType.COPY, FileOperationType.MOVE]

    def get_description(self) -> str:
        """Get human-readable description of the command"""
        return f"{self.operation_type.value} {self.source_path.name} -> {self.target_path.name}"

    def _create_backup(self) -> Optional[Path]:
        """Create backup of existing target file"""
        try:
            timestamp = int(time.time())
            backup_path = self.target_path.with_suffix(
                f"{self.target_path.suffix}.backup_{timestamp}"
            )
            shutil.copy2(self.target_path, backup_path)
            return backup_path
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            return None

    def _perform_operation(self) -> CommandResult:
        """Perform the actual file operation"""
        try:
            if self.operation_type == FileOperationType.COPY:
                shutil.copy2(self.source_path, self.target_path)
            elif self.operation_type == FileOperationType.MOVE:
                shutil.move(self.source_path, self.target_path)
            elif self.operation_type == FileOperationType.RENAME:
                self.source_path.rename(self.target_path)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unsupported operation type: {self.operation_type}",
                    error="Unsupported operation",
                )

            return CommandResult(
                success=True, message=f"File {self.operation_type.value} completed successfully"
            )

        except Exception as e:
            return CommandResult(
                success=False, message=f"File operation failed: {str(e)}", error=str(e)
            )

    def _reverse_operation(self) -> CommandResult:
        """Reverse the operation (for undo without backup)"""
        try:
            if self.operation_type == FileOperationType.COPY:
                # For copy, just delete the target file
                self.target_path.unlink()
            elif self.operation_type == FileOperationType.MOVE:
                # For move, move the file back
                shutil.move(self.target_path, self.source_path)
            else:
                return CommandResult(
                    success=False,
                    message="Cannot reverse this operation type",
                    error="Unsupported reverse operation",
                )

            return CommandResult(success=True, message="Operation reversed successfully")

        except Exception as e:
            return CommandResult(
                success=False, message=f"Operation reversal failed: {str(e)}", error=str(e)
            )


class BatchFileOperationCommand(IFileCommand):
    """Command for executing multiple file operations in batch"""

    def __init__(self, operations: list[FileOperationCommand], logger: logging.Logger = None):
        self.operations = operations
        self.logger = logger or logging.getLogger(__name__)
        self._executed_operations: list[FileOperationCommand] = []

    def execute(self) -> CommandResult:
        """Execute all operations in the batch"""
        try:
            successful_operations = []
            failed_operations = []

            for operation in self.operations:
                result = operation.execute()
                if result.success:
                    successful_operations.append(operation)
                    self._executed_operations.append(operation)
                else:
                    failed_operations.append(operation)
                    self.logger.error(f"Operation failed: {result.message}")

            return CommandResult(
                success=len(failed_operations) == 0,
                message=f"Batch operation completed: {len(successful_operations)} successful, {len(failed_operations)} failed",
                data={
                    "successful_count": len(successful_operations),
                    "failed_count": len(failed_operations),
                    "total_count": len(self.operations),
                },
            )

        except Exception as e:
            self.logger.error(f"Batch operation failed: {e}")
            return CommandResult(
                success=False, message=f"Batch operation failed: {str(e)}", error=str(e)
            )

    def undo(self) -> CommandResult:
        """Undo all executed operations in reverse order"""
        try:
            if not self._executed_operations:
                return CommandResult(
                    success=False, message="No operations to undo", error="No executed operations"
                )

            successful_undos = 0
            failed_undos = 0

            # Undo in reverse order
            for operation in reversed(self._executed_operations):
                if operation.can_undo():
                    result = operation.undo()
                    if result.success:
                        successful_undos += 1
                    else:
                        failed_undos += 1
                        self.logger.error(f"Undo failed: {result.message}")

            return CommandResult(
                success=failed_undos == 0,
                message=f"Batch undo completed: {successful_undos} successful, {failed_undos} failed",
                data={
                    "successful_undos": successful_undos,
                    "failed_undos": failed_undos,
                    "total_undos": len(self._executed_operations),
                },
            )

        except Exception as e:
            self.logger.error(f"Batch undo failed: {e}")
            return CommandResult(
                success=False, message=f"Batch undo failed: {str(e)}", error=str(e)
            )

    def can_undo(self) -> bool:
        """Check if all operations can be undone"""
        return all(operation.can_undo() for operation in self.operations)

    def get_description(self) -> str:
        """Get description of the batch operation"""
        return f"Batch operation: {len(self.operations)} file operations"


class FileOperationCommandInvoker:
    """Invoker for file operation commands with undo/redo support"""

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self._command_history: list[IFileCommand] = []
        self._current_position = -1

    def execute_command(self, command: IFileCommand) -> CommandResult:
        """Execute a command and add it to history"""
        try:
            result = command.execute()

            if result.success:
                # Remove any commands after current position (for redo)
                self._command_history = self._command_history[: self._current_position + 1]

                # Add new command to history
                self._command_history.append(command)
                self._current_position += 1

                self.logger.info(
                    f"Command executed and added to history: {command.get_description()}"
                )
            else:
                self.logger.error(f"Command execution failed: {result.message}")

            return result

        except Exception as e:
            self.logger.error(f"Command execution error: {e}")
            return CommandResult(
                success=False, message=f"Command execution error: {str(e)}", error=str(e)
            )

    def undo_last_command(self) -> CommandResult:
        """Undo the last executed command"""
        try:
            if self._current_position < 0:
                return CommandResult(
                    success=False, message="No commands to undo", error="Command history is empty"
                )

            command = self._command_history[self._current_position]
            result = command.undo()

            if result.success:
                self._current_position -= 1
                self.logger.info(f"Command undone: {command.get_description()}")
            else:
                self.logger.error(f"Command undo failed: {result.message}")

            return result

        except Exception as e:
            self.logger.error(f"Undo error: {e}")
            return CommandResult(success=False, message=f"Undo error: {str(e)}", error=str(e))

    def redo_last_command(self) -> CommandResult:
        """Redo the last undone command"""
        try:
            if self._current_position >= len(self._command_history) - 1:
                return CommandResult(
                    success=False,
                    message="No commands to redo",
                    error="No undone commands available",
                )

            self._current_position += 1
            command = self._command_history[self._current_position]
            result = command.execute()

            if result.success:
                self.logger.info(f"Command redone: {command.get_description()}")
            else:
                self.logger.error(f"Command redo failed: {result.message}")

            return result

        except Exception as e:
            self.logger.error(f"Redo error: {e}")
            return CommandResult(success=False, message=f"Redo error: {str(e)}", error=str(e))

    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return self._current_position >= 0

    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return self._current_position < len(self._command_history) - 1

    def get_history(self) -> list[IFileCommand]:
        """Get command history"""
        return self._command_history.copy()

    def clear_history(self):
        """Clear command history"""
        self._command_history.clear()
        self._current_position = -1
        self.logger.info("Command history cleared")

    def get_history_description(self) -> list[str]:
        """Get human-readable descriptions of command history"""
        return [cmd.get_description() for cmd in self._command_history]
