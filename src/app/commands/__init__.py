"""
Command 패턴 구현

파일 조작을 안전하고 취소 가능한 Command로 래핑
"""

from .base_command import (BaseCommand, CommandError, CommandResult,
                           CommandStatus, ICommand)
from .command_events import (BatchCommandCompletedEvent,
                             BatchCommandStartedEvent, CommandExecutedEvent,
                             CommandFailedEvent, CommandRedoneEvent,
                             CommandUndoneEvent)
from .command_invoker import CommandInvoker, ICommandInvoker
from .composite_commands import (BatchFileOperationCommand,
                                 BatchOperationConfig, ConditionalCommand)
from .file_commands import (BatchFileCommand, CopyFileCommand,
                            CreateDirectoryCommand, DeleteFileCommand,
                            MoveFileCommand, RenameFileCommand)

__all__ = [
    # Base
    "BaseCommand",
    "CommandResult",
    "CommandStatus",
    "CommandError",
    "ICommand",
    # File Commands
    "MoveFileCommand",
    "CopyFileCommand",
    "DeleteFileCommand",
    "RenameFileCommand",
    "CreateDirectoryCommand",
    "BatchFileCommand",
    # Composite Commands (Phase 3)
    "BatchFileOperationCommand",
    "ConditionalCommand",
    "BatchOperationConfig",
    # Invoker
    "CommandInvoker",
    "ICommandInvoker",
    # Events
    "CommandExecutedEvent",
    "CommandUndoneEvent",
    "CommandRedoneEvent",
    "CommandFailedEvent",
    "BatchCommandStartedEvent",
    "BatchCommandCompletedEvent",
]
