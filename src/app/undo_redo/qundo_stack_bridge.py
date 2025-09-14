"""
QUndoStack 브리지

Phase 3: Command 시스템과 Qt의 Undo/Redo 시스템을 연결하는 브리지
스테이징 디렉토리와 JSONL 저널링을 통합하여 안전한 Undo/Redo 제공
"""

import logging

logger = logging.getLogger(__name__)
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QUndoStack

from src.app.commands import ICommand
from src.app.staging import IStagingManager, StagedFile
from src.app.undo_redo.qt_command_wrapper import QtCommandWrapper


class QUndoStackBridge(QObject):
    """QUndoStack과 Command 시스템을 연결하는 브리지"""

    command_executed = pyqtSignal(str, object)
    command_undone = pyqtSignal(str, object)
    command_redone = pyqtSignal(str, object)
    command_failed = pyqtSignal(str, str)
    staging_started = pyqtSignal(str, list)
    staging_completed = pyqtSignal(str, list)
    staging_failed = pyqtSignal(str, str)

    def __init__(
        self,
        undo_stack: QUndoStack | None = None,
        staging_manager: IStagingManager | None = None,
    ):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._undo_stack = undo_stack or QUndoStack()
        self._staging_manager = staging_manager
        self._command_map: dict[str, ICommand] = {}
        self._staging_map: dict[str, list[StagedFile]] = {}
        self._auto_staging = True
        self._staging_cleanup_on_undo = True
        self._connect_undo_stack_signals()
        self.logger.info("QUndoStack 브리지 초기화 완료")

    def _connect_undo_stack_signals(self):
        """QUndoStack 시그널 연결"""
        if hasattr(self._undo_stack, "indexChanged"):
            self._undo_stack.indexChanged.connect(self._on_undo_stack_index_changed)
        if hasattr(self._undo_stack, "canUndoChanged"):
            self._undo_stack.canUndoChanged.connect(self._on_can_undo_changed)
        if hasattr(self._undo_stack, "canRedoChanged"):
            self._undo_stack.canRedoChanged.connect(self._on_can_redo_changed)

    def set_staging_manager(self, staging_manager: IStagingManager):
        """스테이징 매니저 설정"""
        self._staging_manager = staging_manager
        self.logger.info("스테이징 매니저 설정됨")

    def execute_command(self, command: ICommand) -> bool:
        """Command 실행 (Phase 3: 스테이징 + 저널링 통합)"""
        try:
            self.logger.info(f"Command 실행 시작: {command.description}")
            if self._staging_manager and hasattr(command, "set_staging_manager"):
                command.set_staging_manager(self._staging_manager)
            if self._auto_staging and self._staging_manager:
                self.staging_started.emit(str(command.command_id), [])
            qt_command = QtCommandWrapper(command)
            command_id_str = str(command.command_id)
            self._command_map[command_id_str] = command
            self._undo_stack.push(qt_command)
            if hasattr(command, "result") and command.result:
                result = command.result
                if result.is_success:
                    if hasattr(result, "staged_files") and result.staged_files:
                        self._staging_map[command_id_str] = result.staged_files
                        self.staging_completed.emit(command_id_str, result.staged_files)
                    self.command_executed.emit(command_id_str, result)
                    self.logger.info(f"Command 실행 성공: {command.description}")
                    return True
                error_msg = result.error.message if result.error else "알 수 없는 오류"
                self.command_failed.emit(command_id_str, error_msg)
                self.logger.error(f"Command 실행 실패: {command.description} - {error_msg}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Command 실행 중 오류: {e}")
            self.command_failed.emit(str(command.command_id), str(e))
            return False

    def undo_last_command(self) -> bool:
        """마지막 Command 취소"""
        try:
            if not self._undo_stack.canUndo():
                self.logger.warning("취소할 Command가 없습니다")
                return False
            self.logger.info("마지막 Command 취소 시작")
            self._undo_stack.undo()
            current_index = self._undo_stack.index()
            if current_index > 0:
                command_id = self._get_command_id_at_index(current_index)
                if command_id:
                    self._handle_command_undone(command_id)
            return True
        except Exception as e:
            self.logger.error(f"Command 취소 중 오류: {e}")
            return False

    def redo_last_command(self) -> bool:
        """마지막 취소된 Command 재실행"""
        try:
            if not self._undo_stack.canRedo():
                self.logger.warning("재실행할 Command가 없습니다")
                return False
            self.logger.info("마지막 Command 재실행 시작")
            self._undo_stack.redo()
            current_index = self._undo_stack.index()
            command_id = self._get_command_id_at_index(current_index)
            if command_id:
                self._handle_command_redone(command_id)
            return True
        except Exception as e:
            self.logger.error(f"Command 재실행 중 오류: {e}")
            return False

    def _handle_command_undone(self, command_id: str):
        """Command 취소 처리"""
        try:
            command = self._command_map.get(command_id)
            if not command:
                return
            if self._staging_cleanup_on_undo and command_id in self._staging_map:
                self._cleanup_staging_for_command(command_id)
            self.command_undone.emit(
                command_id, command.result if hasattr(command, "result") else None
            )
            self.logger.info(f"Command 취소 완료: {command.description}")
        except Exception as e:
            self.logger.error(f"Command 취소 처리 중 오류: {e}")

    def _handle_command_redone(self, command_id: str):
        """Command 재실행 처리"""
        try:
            command = self._command_map.get(command_id)
            if not command:
                return
            self.command_redone.emit(
                command_id, command.result if hasattr(command, "result") else None
            )
            self.logger.info(f"Command 재실행 완료: {command.description}")
        except Exception as e:
            self.logger.error(f"Command 재실행 처리 중 오류: {e}")

    def _cleanup_staging_for_command(self, command_id: str):
        """Command의 스테이징 파일 정리"""
        try:
            if command_id not in self._staging_map:
                return
            staged_files = self._staging_map[command_id]
            if not self._staging_manager:
                return
            for staged_file in staged_files:
                try:
                    if staged_file.staging_path.exists():
                        if staged_file.staging_path.is_file():
                            staged_file.staging_path.unlink()
                        elif staged_file.staging_path.is_dir():
                            import shutil

                            shutil.rmtree(staged_file.staging_path)
                    backup_path = staged_file.metadata.get("backup_path")
                    if backup_path:
                        backup_path_obj = staged_file.original_path.parent / backup_path
                        if backup_path_obj.exists():
                            backup_path_obj.unlink()
                except Exception as e:
                    self.logger.warning(
                        f"스테이징 파일 정리 실패: {staged_file.staging_path} - {e}"
                    )
            del self._staging_map[command_id]
            self.logger.info(f"Command {command_id}의 스테이징 파일 정리 완료")
        except Exception as e:
            self.logger.error(f"스테이징 정리 중 오류: {e}")

    def _get_command_id_at_index(self, index: int) -> str | None:
        """특정 인덱스의 Command ID 조회"""
        try:
            if 0 <= index < self._undo_stack.count():
                return None
            return None
        except Exception as e:
            self.logger.error(f"Command ID 조회 실패: {e}")
            return None

    def _on_undo_stack_index_changed(self, index: int):
        """Undo 스택 인덱스 변경 처리"""
        self.logger.debug(f"Undo 스택 인덱스 변경: {index}")

    def _on_can_undo_changed(self, can_undo: bool):
        """Undo 가능 여부 변경 처리"""
        self.logger.debug(f"Undo 가능 여부 변경: {can_undo}")

    def _on_can_redo_changed(self, can_redo: bool):
        """Redo 가능 여부 변경 처리"""
        self.logger.debug(f"Redo 가능 여부 변경: {can_redo}")

    @property
    def undo_stack(self) -> QUndoStack:
        """내부 QUndoStack 반환"""
        return self._undo_stack

    @property
    def can_undo(self) -> bool:
        """Undo 가능 여부"""
        return self._undo_stack.canUndo()

    @property
    def can_redo(self) -> bool:
        """Redo 가능 여부"""
        return self._undo_stack.canRedo()

    @property
    def undo_text(self) -> str:
        """다음 Undo 작업의 텍스트"""
        return self._undo_stack.undoText()

    @property
    def redo_text(self) -> str:
        """다음 Redo 작업의 텍스트"""
        return self._undo_stack.redoText()

    def clear(self):
        """모든 Command 정리"""
        try:
            for command_id in list(self._staging_map.keys()):
                self._cleanup_staging_for_command(command_id)
            self._command_map.clear()
            self._staging_map.clear()
            self._undo_stack.clear()
            self.logger.info("모든 Command 정리 완료")
        except Exception as e:
            self.logger.error(f"Command 정리 중 오류: {e}")

    def get_command_history(self) -> list[dict[str, Any]]:
        """Command 실행 히스토리 반환"""
        try:
            history = []
            for command_id, command in self._command_map.items():
                history_item = {
                    "command_id": command_id,
                    "description": command.description,
                    "has_result": hasattr(command, "result") and command.result is not None,
                    "is_success": (
                        hasattr(command, "result") and command.result and command.result.is_success
                        if hasattr(command, "result")
                        else False
                    ),
                    "staged_files_count": len(self._staging_map.get(command_id, [])),
                }
                if hasattr(command, "result") and command.result:
                    result = command.result
                    history_item.update(
                        {
                            "executed_at": (
                                result.executed_at.isoformat() if result.executed_at else None
                            ),
                            "completed_at": (
                                result.completed_at.isoformat() if result.completed_at else None
                            ),
                            "execution_time_ms": result.execution_time_ms,
                            "affected_files_count": len(result.affected_files),
                        }
                    )
                history.append(history_item)
            return history
        except Exception as e:
            self.logger.error(f"Command 히스토리 조회 실패: {e}")
            return []

    def get_staging_summary(self) -> dict[str, Any]:
        """스테이징 상태 요약"""
        try:
            if not self._staging_manager:
                return {"error": "스테이징 매니저가 설정되지 않음"}
            return self._staging_manager.get_staging_summary()
        except Exception as e:
            self.logger.error(f"스테이징 요약 조회 실패: {e}")
            return {"error": str(e)}
