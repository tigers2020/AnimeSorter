"""
Command Invoker 구현

Command들을 실행하고 관리하는 중앙 관리자
"""

import logging

logger = logging.getLogger(__name__)
from typing import Protocol
from uuid import UUID

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QUndoStack

from src.app.commands.base_command import CommandError, CommandResult, CommandStatus, ICommand
from src.app.commands.command_events import (
    CommandExecutedEvent,
    CommandFailedEvent,
    CommandQueueUpdatedEvent,
    CommandRedoneEvent,
    CommandUndoneEvent,
)
from src.app.events import get_event_bus


class ICommandInvoker(Protocol):
    """Command Invoker 인터페이스"""

    def execute_command(self, command: ICommand) -> CommandResult:
        """Command 실행"""
        ...

    def undo(self) -> bool:
        """마지막 Command 취소"""
        ...

    def redo(self) -> bool:
        """취소된 Command 재실행"""
        ...

    def can_undo(self) -> bool:
        """취소 가능 여부"""
        ...

    def can_redo(self) -> bool:
        """재실행 가능 여부"""
        ...

    def clear_history(self) -> None:
        """Command 히스토리 지우기"""
        ...


class CommandInvoker(QObject):
    """Command 실행 관리자"""

    command_executed = pyqtSignal(UUID, str)
    command_failed = pyqtSignal(UUID, str, str)
    command_undone = pyqtSignal(UUID, str)
    command_redone = pyqtSignal(UUID, str)
    queue_updated = pyqtSignal(int, int, int)

    def __init__(self, event_bus=None):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.event_bus = event_bus or get_event_bus()
        self.undo_stack = QUndoStack(self)
        self._executed_commands: list[ICommand] = []
        self._command_history: dict[UUID, CommandResult] = {}
        self._undo_index = -1
        self._total_executed = 0
        self._total_undone = 0
        self._total_failed = 0
        self._setup_signals()

    def _setup_signals(self) -> None:
        """시그널 연결 설정"""
        if self.event_bus:
            self.command_executed.connect(self._on_command_executed_signal)
            self.command_failed.connect(self._on_command_failed_signal)
            self.command_undone.connect(self._on_command_undone_signal)
            self.command_redone.connect(self._on_command_redone_signal)
            self.queue_updated.connect(self._on_queue_updated_signal)

    def execute_command(self, command: ICommand) -> CommandResult:
        """Command 실행"""
        self.logger.info(f"Command 실행 요청: {command.description}")
        self._total_executed += 1
        try:
            result = command.execute()
            if result.is_success:
                self._on_command_success(command, result)
            else:
                self._on_command_failure(command, result)
            return result
        except Exception as e:
            self.logger.error(f"Command 실행 중 예외: {command.description} - {e}")
            result = CommandResult(command_id=command.command_id, status=CommandStatus.FAILED)
            result.error = CommandError(error_type=type(e).__name__, message=str(e), exception=e)
            self._on_command_failure(command, result)
            return result

    def undo(self) -> bool:
        """마지막 Command 취소"""
        if not self.can_undo():
            self.logger.warning("취소할 Command가 없습니다")
            return False
        command = self._executed_commands[self._undo_index]
        try:
            self.logger.info(f"Command 취소: {command.description}")
            command.undo()
            self._undo_index -= 1
            self._total_undone += 1
            self.command_undone.emit(command.command_id, command.description)
            self._update_queue_status()
            return True
        except Exception as e:
            self.logger.error(f"Command 취소 실패: {command.description} - {e}")
            return False

    def redo(self) -> bool:
        """취소된 Command 재실행"""
        if not self.can_redo():
            self.logger.warning("재실행할 Command가 없습니다")
            return False
        command = self._executed_commands[self._undo_index + 1]
        try:
            self.logger.info(f"Command 재실행: {command.description}")
            result = command.execute()
            if result.is_success:
                self._undo_index += 1
                self.command_redone.emit(command.command_id, command.description)
                self._update_queue_status()
                return True
            self.logger.error(f"Command 재실행 실패: {command.description}")
            return False
        except Exception as e:
            self.logger.error(f"Command 재실행 중 예외: {command.description} - {e}")
            return False

    def can_undo(self) -> bool:
        """취소 가능 여부"""
        return (
            self._undo_index >= 0
            and self._undo_index < len(self._executed_commands)
            and self._executed_commands[self._undo_index].can_undo
        )

    def can_redo(self) -> bool:
        """재실행 가능 여부"""
        return self._undo_index + 1 < len(self._executed_commands)

    def clear_history(self) -> None:
        """Command 히스토리 지우기"""
        self.logger.info("Command 히스토리 지우기")
        self._executed_commands.clear()
        self._command_history.clear()
        self._undo_index = -1
        self.undo_stack.clear()
        self._update_queue_status()

    def get_history(self) -> list[CommandResult]:
        """Command 히스토리 조회"""
        return list(self._command_history.values())

    def get_statistics(self) -> dict[str, int]:
        """실행 통계 조회"""
        return {
            "total_executed": self._total_executed,
            "total_undone": self._total_undone,
            "total_failed": self._total_failed,
            "current_history_size": len(self._executed_commands),
            "can_undo_count": 1 if self.can_undo() else 0,
            "can_redo_count": (
                len(self._executed_commands) - self._undo_index - 1 if self.can_redo() else 0
            ),
        }

    def _on_command_success(self, command: ICommand, result: CommandResult) -> None:
        """Command 실행 성공 처리"""
        self._executed_commands.append(command)
        self._command_history[command.command_id] = result
        self._undo_index = len(self._executed_commands) - 1
        self.command_executed.emit(command.command_id, command.description)
        self._update_queue_status()
        self.logger.info(f"Command 실행 성공: {command.description}")

    def _on_command_failure(self, command: ICommand, result: CommandResult) -> None:
        """Command 실행 실패 처리"""
        self._command_history[command.command_id] = result
        self._total_failed += 1
        error_msg = result.error.message if result.error else "알 수 없는 오류"
        self.command_failed.emit(command.command_id, command.description, error_msg)
        self.logger.error(f"Command 실행 실패: {command.description} - {error_msg}")

    def _update_queue_status(self) -> None:
        """큐 상태 업데이트 이벤트 발행"""
        stats = self.get_statistics()
        self.queue_updated.emit(0, stats["can_undo_count"], stats["can_redo_count"])

    def _on_command_executed_signal(self, command_id: UUID, description: str) -> None:
        """Command 실행 완료 시그널 → EventBus 이벤트"""
        if self.event_bus and command_id in self._command_history:
            result = self._command_history[command_id]
            self.event_bus.publish(
                CommandExecutedEvent(
                    command_id=command_id,
                    command_type=type(result).__name__,
                    description=description,
                    result=result,
                    affected_files=result.affected_files,
                    execution_time_ms=result.execution_time_ms or 0.0,
                )
            )

    def _on_command_failed_signal(self, command_id: UUID, description: str, error: str) -> None:
        """Command 실행 실패 시그널 → EventBus 이벤트"""
        if self.event_bus:
            self.event_bus.publish(
                CommandFailedEvent(
                    command_id=command_id,
                    command_type="Unknown",
                    description=description,
                    error_type="ExecutionError",
                    error_message=error,
                )
            )

    def _on_command_undone_signal(self, command_id: UUID, description: str) -> None:
        """Command 취소 시그널 → EventBus 이벤트"""
        if self.event_bus and command_id in self._command_history:
            result = self._command_history[command_id]
            self.event_bus.publish(
                CommandUndoneEvent(
                    command_id=command_id,
                    command_type=type(result).__name__,
                    description=description,
                    result=result,
                    undo_time_ms=0.0,
                )
            )

    def _on_command_redone_signal(self, command_id: UUID, description: str) -> None:
        """Command 재실행 시그널 → EventBus 이벤트"""
        if self.event_bus and command_id in self._command_history:
            result = self._command_history[command_id]
            self.event_bus.publish(
                CommandRedoneEvent(
                    command_id=command_id,
                    command_type=type(result).__name__,
                    description=description,
                    result=result,
                    redo_time_ms=0.0,
                )
            )

    def _on_queue_updated_signal(self, pending: int, can_undo: int, can_redo: int) -> None:
        """큐 상태 업데이트 시그널 → EventBus 이벤트"""
        if self.event_bus:
            self.event_bus.publish(
                CommandQueueUpdatedEvent(
                    queue_size=len(self._executed_commands),
                    pending_commands=pending,
                    executing_commands=0,
                    can_undo_count=can_undo,
                    can_redo_count=can_redo,
                )
            )
