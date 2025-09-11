"""
Undo/Redo 매니저

QUndoStack을 관리하고 전체 Undo/Redo 시스템을 조정하는 핵심 컴포넌트
"""

import builtins
import contextlib
import logging

logger = logging.getLogger(__name__)
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QUndoStack

from src.app.undo_redo.qt_command_wrapper import QtCommandWrapper

# undo_redo_events 모듈이 없으므로 주석 처리
# from src.app.undo_redo.undo_redo_events import (CommandPushedToStackEvent,
#                                                 UndoRedoErrorEvent)


@dataclass
class UndoRedoConfiguration:
    """Undo/Redo 설정"""

    max_undo_count: int = 100
    merge_commands: bool = True
    auto_push: bool = True
    show_confirmation_dialogs: bool = True
    show_progress_for_batch: bool = True
    animate_ui_changes: bool = True
    async_execution: bool = False
    batch_size_threshold: int = 10
    log_undo_redo: bool = True
    detailed_logging: bool = False
    auto_cleanup: bool = True
    cleanup_interval_minutes: int = 30
    max_memory_mb: int = 100


@dataclass
class UndoRedoStatistics:
    """Undo/Redo 통계"""

    total_commands_executed: int = 0
    total_undos: int = 0
    total_redos: int = 0
    total_failures: int = 0
    commands_in_stack: int = 0
    current_index: int = 0
    stack_size_mb: float = 0.0
    last_command_time: datetime | None = None
    last_undo_time: datetime | None = None
    last_redo_time: datetime | None = None
    session_start_time: datetime = field(default_factory=datetime.now)

    def get_success_rate(self) -> float:
        """성공률 계산"""
        total = self.total_commands_executed + self.total_undos + self.total_redos
        if total == 0:
            return 100.0
        return (total - self.total_failures) / total * 100.0

    def get_session_duration(self) -> timedelta:
        """세션 시간"""
        return datetime.now() - self.session_start_time


class IUndoRedoManager(Protocol):
    """Undo/Redo 매니저 인터페이스"""

    def execute_command(self, command: QtCommandWrapper) -> bool:
        """Command 실행"""
        ...

    def undo(self) -> bool:
        """취소"""
        ...

    def redo(self) -> bool:
        """재실행"""
        ...

    def can_undo(self) -> bool:
        """취소 가능 여부"""
        ...

    def can_redo(self) -> bool:
        """재실행 가능 여부"""
        ...

    def clear(self) -> None:
        """스택 초기화"""
        ...


class UndoRedoManager(QObject):
    """Undo/Redo 매니저 구현"""

    stack_changed = pyqtSignal()
    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)
    command_executed = pyqtSignal(QtCommandWrapper)
    undo_executed = pyqtSignal(QtCommandWrapper)
    redo_executed = pyqtSignal(QtCommandWrapper)
    error_occurred = pyqtSignal(str)

    def __init__(self, config: UndoRedoConfiguration | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self.config = config or UndoRedoConfiguration()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(self.config.max_undo_count)
        self._statistics = UndoRedoStatistics()
        self._event_handlers: dict[str, list[Callable]] = {
            "command_executed": [],
            "undo_executed": [],
            "redo_executed": [],
            "stack_changed": [],
            "error_occurred": [],
        }
        self._connect_stack_signals()
        self.logger.info("Undo/Redo 매니저 초기화 완료")

    def _connect_stack_signals(self) -> None:
        """QUndoStack 시그널 연결"""
        self._undo_stack.indexChanged.connect(self._on_stack_index_changed)
        self._undo_stack.cleanChanged.connect(self._on_stack_clean_changed)
        self._undo_stack.canUndoChanged.connect(self.can_undo_changed)
        self._undo_stack.canRedoChanged.connect(self.can_redo_changed)
        self.stack_changed.connect(self._on_stack_changed_internal)
        self.command_executed.connect(self._on_command_executed_internal)
        self.undo_executed.connect(self._on_undo_executed_internal)
        self.redo_executed.connect(self._on_redo_executed_internal)
        self.error_occurred.connect(self._on_error_occurred_internal)

    def execute_command(self, command: QtCommandWrapper) -> bool:
        """Command 실행 및 스택에 추가"""
        try:
            self.logger.info(f"Command 실행: {command.text()}")
            initial_count = self._undo_stack.count()
            self._undo_stack.push(command)
            if (
                not command.is_executed
                or command.execute_result
                and not command.execute_result.is_success
            ):
                current_count = self._undo_stack.count()
                if current_count > initial_count:
                    self._undo_stack.setIndex(initial_count)
                raise RuntimeError("Command 실행 실패")
            self._statistics.total_commands_executed += 1
            self._statistics.last_command_time = datetime.now()
            self.command_executed.emit(command)
            self.logger.debug(f"Command 실행 성공: {command.text()}")
            return True
        except Exception as e:
            self.logger.error(f"Command 실행 실패: {e}")
            self._statistics.total_failures += 1
            self.error_occurred.emit(str(e))
            return False

    def undo(self) -> bool:
        """취소 실행"""
        if not self.can_undo():
            self.logger.warning("취소할 수 없음")
            return False
        try:
            current_command = self._get_current_command()
            self.logger.info(
                f"취소 실행: {current_command.text() if current_command else 'Unknown'}"
            )
            self._undo_stack.index()
            self._undo_stack.undo()
            if (
                current_command
                and hasattr(current_command, "undo_result")
                and current_command.undo_result
                and not current_command.undo_result.is_success
            ):
                self.logger.error("Command의 undo 작업이 실패했습니다")
                self._statistics.total_failures += 1
                self.error_occurred.emit("Undo 작업 실패")
                return False
            self._statistics.total_undos += 1
            self._statistics.last_undo_time = datetime.now()
            if current_command:
                self.undo_executed.emit(current_command)
            self.logger.debug("취소 성공")
            return True
        except Exception as e:
            self.logger.error(f"취소 실패: {e}")
            self._statistics.total_failures += 1
            self.error_occurred.emit(str(e))
            return False

    def redo(self) -> bool:
        """재실행"""
        if not self.can_redo():
            self.logger.warning("재실행할 수 없음")
            return False
        try:
            next_command = self._get_next_command()
            self.logger.info(f"재실행: {next_command.text() if next_command else 'Unknown'}")
            self._undo_stack.redo()
            self._statistics.total_redos += 1
            self._statistics.last_redo_time = datetime.now()
            if next_command:
                self.redo_executed.emit(next_command)
            self.logger.debug("재실행 성공")
            return True
        except Exception as e:
            self.logger.error(f"재실행 실패: {e}")
            self._statistics.total_failures += 1
            self.error_occurred.emit(str(e))
            return False

    def can_undo(self) -> bool:
        """취소 가능 여부"""
        return self._undo_stack.canUndo()

    def can_redo(self) -> bool:
        """재실행 가능 여부"""
        return self._undo_stack.canRedo()

    def undo_text(self) -> str:
        """취소할 작업 설명"""
        return self._undo_stack.undoText()

    def redo_text(self) -> str:
        """재실행할 작업 설명"""
        return self._undo_stack.redoText()

    def clear(self) -> None:
        """스택 초기화"""
        self.logger.info("Undo/Redo 스택 초기화")
        self._undo_stack.clear()
        self._statistics.commands_in_stack = 0
        self._statistics.current_index = 0
        self.stack_changed.emit()

    def get_stack_count(self) -> int:
        """스택의 Command 개수"""
        return self._undo_stack.count()

    def get_current_index(self) -> int:
        """현재 인덱스"""
        return self._undo_stack.index()

    def is_clean(self) -> bool:
        """변경사항이 저장된 상태인지"""
        return self._undo_stack.isClean()

    def set_clean(self) -> None:
        """현재 상태를 저장된 상태로 표시"""
        self._undo_stack.setClean()

    def get_statistics(self) -> UndoRedoStatistics:
        """통계 정보"""
        self._statistics.commands_in_stack = self.get_stack_count()
        self._statistics.current_index = self.get_current_index()
        return self._statistics

    def get_command_history(self) -> list[str]:
        """Command 히스토리"""
        history = []
        for i in range(self._undo_stack.count()):
            command = self._undo_stack.command(i)
            if command:
                status = "✓" if i < self.get_current_index() else "○"
                history.append(f"{status} {command.text()}")
        return history

    def _get_current_command(self) -> QtCommandWrapper | None:
        """현재 Command 조회"""
        index = self.get_current_index()
        if index > 0:
            command = self._undo_stack.command(index - 1)
            if isinstance(command, QtCommandWrapper):
                return command
        return None

    def _get_next_command(self) -> QtCommandWrapper | None:
        """다음 Command 조회"""
        index = self.get_current_index()
        if index < self.get_stack_count():
            command = self._undo_stack.command(index)
            if isinstance(command, QtCommandWrapper):
                return command
        return None

    def _on_stack_index_changed(self, index: int) -> None:
        """스택 인덱스 변경 시"""
        self.logger.debug(f"스택 인덱스 변경: {index}")
        self.stack_changed.emit()

    def _on_stack_clean_changed(self, clean: bool) -> None:
        """스택 정리 상태 변경 시"""
        self.logger.debug(f"스택 정리 상태 변경: {clean}")

    def _on_stack_changed_internal(self) -> None:
        """스택 변경 내부 핸들러"""
        # 새로운 이벤트 시스템으로 변경 - 로그만 남김
        self.logger.debug(f"Stack changed: undo={self.can_undo()}, redo={self.can_redo()}")
        # 필요시 event_publisher.publish_settings_changed() 등을 사용

    def _on_command_executed_internal(self, command: QtCommandWrapper) -> None:
        """Command 실행 내부 핸들러"""
        # 새로운 이벤트 시스템으로 변경 - 로그만 남김
        self.logger.info(f"Command pushed to stack: {command.text()}")
        # 필요시 event_publisher.publish_organize_started() 등을 사용

    def _on_undo_executed_internal(self, command: QtCommandWrapper) -> None:
        """취소 실행 내부 핸들러"""
        # 새로운 이벤트 시스템으로 변경 - 로그만 남김
        self.logger.info(f"Undo executed: {command.text()}")
        # 필요시 event_publisher.publish_user_action_required() 등을 사용

    def _on_redo_executed_internal(self, command: QtCommandWrapper) -> None:
        """재실행 내부 핸들러"""
        # 새로운 이벤트 시스템으로 변경 - 로그만 남김
        self.logger.info(f"Redo executed: {command.text()}")
        # 필요시 event_publisher.publish_user_action_required() 등을 사용

    def _on_error_occurred_internal(self, error_message: str) -> None:
        """오류 발생 내부 핸들러"""
        # 새로운 이벤트 시스템으로 변경 - 로그만 남김
        self.logger.error(f"Undo/Redo 오류: {error_message}")
        # 필요시 event_publisher.publish_error() 등을 사용

    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 추가"""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)

    def remove_event_handler(self, event_type: str, handler: Callable) -> bool:
        """이벤트 핸들러 제거"""
        if event_type in self._event_handlers and handler in self._event_handlers[event_type]:
            self._event_handlers[event_type].remove(handler)
            return True
        return False

    def shutdown(self) -> None:
        """매니저 종료"""
        self.logger.info("Undo/Redo 매니저 종료")
        self.clear()

    def __del__(self):
        """소멸자"""
        with contextlib.suppress(builtins.BaseException):
            self.shutdown()
