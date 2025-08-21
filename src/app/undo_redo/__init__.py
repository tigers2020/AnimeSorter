"""
Undo/Redo 시스템

QUndoStack 기반 사용자 친화적 취소/재실행 시스템
"""

from .qt_command_wrapper import (
    QtBatchFileCommand,
    QtCommandWrapper,
    QtCopyFileCommand,
    QtCreateDirectoryCommand,
    QtDeleteFileCommand,
    QtMoveFileCommand,
    QtRenameFileCommand,
)
from .qundo_stack_bridge import (
    QUndoStackBridge,
)
from .ui_integration import (
    UndoRedoMenuManager,
    UndoRedoShortcutManager,
    UndoRedoToolbarManager,
    UndoRedoUIIntegration,
)
from .undo_redo_events import (
    CommandPushedToStackEvent,
    RedoExecutedEvent,
    StackClearedEvent,
    UndoExecutedEvent,
    UndoRedoEnabledEvent,
    UndoRedoErrorEvent,
    UndoRedoStackChangedEvent,
)
from .undo_redo_manager import (
    IUndoRedoManager,
    UndoRedoConfiguration,
    UndoRedoManager,
    UndoRedoStatistics,
)

__all__ = [
    # Qt Command Wrappers
    "QtCommandWrapper",
    "QtMoveFileCommand",
    "QtCopyFileCommand",
    "QtDeleteFileCommand",
    "QtRenameFileCommand",
    "QtCreateDirectoryCommand",
    "QtBatchFileCommand",
    # Undo/Redo Manager
    "UndoRedoManager",
    "IUndoRedoManager",
    "UndoRedoConfiguration",
    "UndoRedoStatistics",
    # QUndoStack Bridge (Phase 3)
    "QUndoStackBridge",
    # Events
    "UndoExecutedEvent",
    "RedoExecutedEvent",
    "UndoRedoStackChangedEvent",
    "UndoRedoEnabledEvent",
    "CommandPushedToStackEvent",
    "StackClearedEvent",
    "UndoRedoErrorEvent",
    # UI Integration
    "UndoRedoUIIntegration",
    "UndoRedoMenuManager",
    "UndoRedoToolbarManager",
    "UndoRedoShortcutManager",
]
