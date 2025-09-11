"""
Undo/Redo 시스템

QUndoStack 기반 사용자 친화적 취소/재실행 시스템
"""

import logging

logger = logging.getLogger(__name__)
# undo_redo_events 모듈이 없으므로 주석 처리
# from .undo_redo_events import (CommandPushedToStackEvent,
#                                StackClearedEvent,
#                                UndoRedoEnabledEvent, UndoRedoErrorEvent)
# UndoRedoManager는 새로운 서비스 아키텍처로 대체됨
# from .undo_redo_manager import ...
# 임시로 기본 클래스들 정의
from dataclasses import dataclass
from typing import Protocol

from .qt_command_wrapper import (QtBatchFileCommand, QtCommandWrapper,
                                 QtCopyFileCommand, QtCreateDirectoryCommand,
                                 QtDeleteFileCommand, QtMoveFileCommand)
from .qundo_stack_bridge import QUndoStackBridge
from .ui_integration import (UndoRedoMenuManager, UndoRedoShortcutManager,
                             UndoRedoToolbarManager, UndoRedoUIIntegration)


class IUndoRedoManager(Protocol):
    """Undo/Redo 관리자 인터페이스"""

    def can_undo(self) -> bool:
        """실행 취소 가능 여부"""
        ...

    def can_redo(self) -> bool:
        """재실행 가능 여부"""
        ...

    def undo(self) -> bool:
        """실행 취소"""
        ...

    def redo(self) -> bool:
        """재실행"""
        ...


@dataclass
class UndoRedoConfiguration:
    """Undo/Redo 설정"""

    max_stack_size: int = 50
    enable_shortcuts: bool = True


@dataclass
class UndoRedoStatistics:
    """Undo/Redo 통계"""

    undo_count: int = 0
    redo_count: int = 0
    stack_size: int = 0


class UndoRedoManager:
    """Undo/Redo 관리자 (임시 구현)"""

    def __init__(self, config: UndoRedoConfiguration = None):
        self.config = config or UndoRedoConfiguration()
        self._can_undo = False
        self._can_redo = False

    def can_undo(self) -> bool:
        """실행 취소 가능 여부"""
        return self._can_undo

    def can_redo(self) -> bool:
        """재실행 가능 여부"""
        return self._can_redo

    def undo(self) -> bool:
        """실행 취소"""
        return True

    def redo(self) -> bool:
        """재실행"""
        return True


__all__ = [
    "QtCommandWrapper",
    "QtMoveFileCommand",
    "QtCopyFileCommand",
    "QtDeleteFileCommand",
    "QtCreateDirectoryCommand",
    "QtBatchFileCommand",
    "UndoRedoManager",
    "IUndoRedoManager",
    "UndoRedoConfiguration",
    "UndoRedoStatistics",
    "QUndoStackBridge",
    # undo_redo_events 모듈이 없으므로 주석 처리
    # "UndoExecutedEvent",
    # "RedoExecutedEvent",
    # "UndoRedoStackChangedEvent",
    # "UndoRedoEnabledEvent",
    # "CommandPushedToStackEvent",
    # "StackClearedEvent",
    # "UndoRedoErrorEvent",
    "UndoRedoUIIntegration",
    "UndoRedoMenuManager",
    "UndoRedoToolbarManager",
    "UndoRedoShortcutManager",
]
