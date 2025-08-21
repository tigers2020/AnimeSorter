"""
QUndoStack 브리지

Phase 3: Command 시스템과 Qt의 Undo/Redo 시스템을 연결하는 브리지
스테이징 디렉토리와 JSONL 저널링을 통합하여 안전한 Undo/Redo 제공
"""

import logging
from typing import Any
from uuid import UUID

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QUndoStack

from ..commands import ICommand
from ..journal import IJournalManager
from ..staging import IStagingManager, StagedFile
from .qt_command_wrapper import QtCommandWrapper


class QUndoStackBridge(QObject):
    """QUndoStack과 Command 시스템을 연결하는 브리지"""

    # 시그널 정의
    command_executed = pyqtSignal(str, object)  # command_id, result
    command_undone = pyqtSignal(str, object)  # command_id, result
    command_redone = pyqtSignal(str, object)  # command_id, result
    command_failed = pyqtSignal(str, str)  # command_id, error_message

    # 스테이징 관련 시그널
    staging_started = pyqtSignal(str, list)  # command_id, staged_files
    staging_completed = pyqtSignal(str, list)  # command_id, staged_files
    staging_failed = pyqtSignal(str, str)  # command_id, error_message

    # 저널링 관련 시그널
    journal_entry_created = pyqtSignal(str, str)  # command_id, journal_entry_id
    journal_entry_updated = pyqtSignal(str, str)  # command_id, journal_entry_id

    def __init__(
        self,
        undo_stack: QUndoStack | None = None,
        staging_manager: IStagingManager | None = None,
        journal_manager: IJournalManager | None = None,
    ):
        super().__init__()

        self.logger = logging.getLogger(self.__class__.__name__)

        # Qt Undo/Redo 스택
        self._undo_stack = undo_stack or QUndoStack()

        # Phase 3: 스테이징 및 저널링 매니저
        self._staging_manager = staging_manager
        self._journal_manager = journal_manager

        # Command 추적
        self._command_map: dict[str, ICommand] = {}  # command_id -> command
        self._staging_map: dict[str, list[StagedFile]] = {}  # command_id -> staged_files

        # 설정
        self._auto_staging = True
        self._auto_journaling = True
        self._staging_cleanup_on_undo = True

        # 이벤트 연결
        self._connect_undo_stack_signals()

        self.logger.info("QUndoStack 브리지 초기화 완료")

    def _connect_undo_stack_signals(self):
        """QUndoStack 시그널 연결"""
        # Qt 5.15+ 에서는 indexChanged 시그널 사용
        if hasattr(self._undo_stack, "indexChanged"):
            self._undo_stack.indexChanged.connect(self._on_undo_stack_index_changed)

        # 기존 시그널들도 연결
        if hasattr(self._undo_stack, "canUndoChanged"):
            self._undo_stack.canUndoChanged.connect(self._on_can_undo_changed)
        if hasattr(self._undo_stack, "canRedoChanged"):
            self._undo_stack.canRedoChanged.connect(self._on_can_redo_changed)

    def set_staging_manager(self, staging_manager: IStagingManager):
        """스테이징 매니저 설정"""
        self._staging_manager = staging_manager
        self.logger.info("스테이징 매니저 설정됨")

    def set_journal_manager(self, journal_manager: IJournalManager):
        """저널 매니저 설정"""
        self._journal_manager = journal_manager
        self.logger.info("저널 매니저 설정됨")

    def execute_command(self, command: ICommand) -> bool:
        """Command 실행 (Phase 3: 스테이징 + 저널링 통합)"""
        try:
            self.logger.info(f"Command 실행 시작: {command.description}")

            # Phase 3: 스테이징 매니저 설정
            if self._staging_manager and hasattr(command, "set_staging_manager"):
                command.set_staging_manager(self._staging_manager)

            # Phase 3: 저널 매니저 설정
            if self._journal_manager and hasattr(command, "set_journal_manager"):
                command.set_journal_manager(self._journal_manager)

            # 스테이징 시작 알림
            if self._auto_staging and self._staging_manager:
                self.staging_started.emit(str(command.command_id), [])

            # Qt Command 래퍼 생성
            qt_command = QtCommandWrapper(command)

            # Command 매핑 저장
            command_id_str = str(command.command_id)
            self._command_map[command_id_str] = command

            # QUndoStack에 추가 및 실행
            self._undo_stack.push(qt_command)

            # 실행 결과 확인
            if hasattr(command, "result") and command.result:
                result = command.result

                if result.is_success:
                    # 성공: 스테이징 정보 저장
                    if hasattr(result, "staged_files") and result.staged_files:
                        self._staging_map[command_id_str] = result.staged_files
                        self.staging_completed.emit(command_id_str, result.staged_files)

                    # 저널링 정보 확인
                    if hasattr(result, "journal_entry_id") and result.journal_entry_id:
                        self.journal_entry_created.emit(
                            command_id_str, str(result.journal_entry_id)
                        )

                    self.command_executed.emit(command_id_str, result)
                    self.logger.info(f"Command 실행 성공: {command.description}")
                    return True
                # 실패: 에러 처리
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

            # QUndoStack에서 취소 실행
            self._undo_stack.undo()

            # 취소된 Command 정보 가져오기
            current_index = self._undo_stack.index()
            if current_index > 0:
                # 이전 Command가 취소된 것
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

            # QUndoStack에서 재실행 실행
            self._undo_stack.redo()

            # 재실행된 Command 정보 가져오기
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

            # 스테이징 정리 (설정에 따라)
            if self._staging_cleanup_on_undo and command_id in self._staging_map:
                self._cleanup_staging_for_command(command_id)

            # 저널링 업데이트
            if self._journal_manager and hasattr(command, "result") and command.result:
                result = command.result
                if hasattr(result, "journal_entry_id") and result.journal_entry_id:
                    self._update_journal_entry_status(result.journal_entry_id, "undone")

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

            # 저널링 업데이트
            if self._journal_manager and hasattr(command, "result") and command.result:
                result = command.result
                if hasattr(result, "journal_entry_id") and result.journal_entry_id:
                    self._update_journal_entry_status(result.journal_entry_id, "redone")

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

            # 스테이징된 파일들 정리
            for staged_file in staged_files:
                try:
                    # 스테이징 파일 삭제
                    if staged_file.staging_path.exists():
                        if staged_file.staging_path.is_file():
                            staged_file.staging_path.unlink()
                        elif staged_file.staging_path.is_dir():
                            import shutil

                            shutil.rmtree(staged_file.staging_path)

                    # 백업 파일도 정리
                    backup_path = staged_file.metadata.get("backup_path")
                    if backup_path:
                        backup_path_obj = staged_file.original_path.parent / backup_path
                        if backup_path_obj.exists():
                            backup_path_obj.unlink()

                except Exception as e:
                    self.logger.warning(
                        f"스테이징 파일 정리 실패: {staged_file.staging_path} - {e}"
                    )

            # 매핑에서 제거
            del self._staging_map[command_id]
            self.logger.info(f"Command {command_id}의 스테이징 파일 정리 완료")

        except Exception as e:
            self.logger.error(f"스테이징 정리 중 오류: {e}")

    def _update_journal_entry_status(self, journal_entry_id: UUID, status: str):
        """저널 엔트리 상태 업데이트"""
        try:
            if not self._journal_manager:
                return

            # 저널 엔트리 조회 및 상태 업데이트
            # (실제 구현은 JournalManager의 API에 따라 달라질 수 있음)
            self.logger.debug(f"저널 엔트리 상태 업데이트: {journal_entry_id} -> {status}")

        except Exception as e:
            self.logger.error(f"저널 엔트리 상태 업데이트 실패: {e}")

    def _get_command_id_at_index(self, index: int) -> str | None:
        """특정 인덱스의 Command ID 조회"""
        try:
            # QUndoStack의 Command 목록에서 해당 인덱스의 Command 찾기
            # (실제 구현은 Qt 버전에 따라 달라질 수 있음)
            if 0 <= index < self._undo_stack.count():
                # 여기서는 간단한 방법으로 구현
                # 실제로는 QUndoStack의 내부 구조를 더 정확하게 파악해야 함
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

    # === 공개 API ===

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
            # 스테이징 파일들 정리
            for command_id in list(self._staging_map.keys()):
                self._cleanup_staging_for_command(command_id)

            # Command 매핑 정리
            self._command_map.clear()
            self._staging_map.clear()

            # QUndoStack 정리
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
                    )
                    if hasattr(command, "result")
                    else False,
                    "staged_files_count": len(self._staging_map.get(command_id, [])),
                }

                if hasattr(command, "result") and command.result:
                    result = command.result
                    history_item.update(
                        {
                            "executed_at": result.executed_at.isoformat()
                            if result.executed_at
                            else None,
                            "completed_at": result.completed_at.isoformat()
                            if result.completed_at
                            else None,
                            "execution_time_ms": result.execution_time_ms,
                            "affected_files_count": len(result.affected_files),
                            "journal_entry_id": str(result.journal_entry_id)
                            if result.journal_entry_id
                            else None,
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
