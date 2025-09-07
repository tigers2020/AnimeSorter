"""
UI Command 브리지

Phase 3: 모든 UI 액션을 Command 시스템을 통해 수행
스테이징 디렉토리와 JSONL 저널링을 통합하여 안전한 UI 작업 제공
"""

import logging

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QProgressDialog

from src.commands import CommandResult, ICommand
from src.app.journal import IJournalManager
from src.staging import IStagingManager
from src.undo_redo import QUndoStackBridge


class UICommandBridge(QObject):
    """UI와 Command 시스템을 연결하는 브리지"""

    # 시그널 정의
    command_executed = pyqtSignal(str, object)  # command_id, result
    command_failed = pyqtSignal(str, str)  # command_id, error_message
    command_progress = pyqtSignal(int, int, str)  # current, total, description

    # 스테이징 관련 시그널
    staging_progress = pyqtSignal(int, int, str)  # current, total, description
    staging_completed = pyqtSignal(list)  # staged_files

    # 저널링 관련 시그널
    journal_updated = pyqtSignal(str, str)  # command_id, journal_entry_id

    def __init__(
        self,
        main_window: QMainWindow,
        undo_stack_bridge: QUndoStackBridge,
        staging_manager: IStagingManager | None = None,
        journal_manager: IJournalManager | None = None,
    ):
        super().__init__(main_window)

        self.main_window = main_window
        self.undo_stack_bridge = undo_stack_bridge
        self.staging_manager = staging_manager
        self.journal_manager = journal_manager

        self.logger = logging.getLogger(self.__class__.__name__)

        # UI 상태 관리
        self._is_processing = False
        self._current_operation = ""
        self._progress_dialog: QProgressDialog | None = None

        # 진행 상황 추적
        self._total_operations = 0
        self._completed_operations = 0

        # 이벤트 연결
        self._connect_undo_stack_signals()

        self.logger.info("UI Command 브리지 초기화 완료")

    def _connect_undo_stack_signals(self):
        """Undo 스택 브리지 시그널 연결"""
        if self.undo_stack_bridge:
            self.undo_stack_bridge.command_executed.connect(self._on_command_executed)
            self.undo_stack_bridge.command_failed.connect(self._on_command_failed)
            self.undo_stack_bridge.staging_started.connect(self._on_staging_started)
            self.undo_stack_bridge.staging_completed.connect(self._on_staging_completed)
            self.undo_stack_bridge.journal_entry_created.connect(self._on_journal_entry_created)

    def execute_command(self, command: ICommand, show_progress: bool = True) -> bool:
        """Command 실행 (UI 통합)"""
        try:
            if self._is_processing:
                self.logger.warning("이미 작업이 진행 중입니다")
                return False

            self._is_processing = True
            self._current_operation = command.description

            self.logger.info(f"UI Command 실행 시작: {command.description}")

            # 진행 상황 다이얼로그 표시
            if show_progress:
                self._show_progress_dialog(command.description)

            # Undo 스택 브리지를 통해 Command 실행
            if self.undo_stack_bridge:
                success = self.undo_stack_bridge.execute_command(command)

                if success:
                    self.logger.info(f"UI Command 실행 성공: {command.description}")
                    return True
                self.logger.error(f"UI Command 실행 실패: {command.description}")
                return False
            self.logger.error("Undo 스택 브리지가 설정되지 않음")
            return False

        except Exception as e:
            self.logger.error(f"UI Command 실행 중 오류: {e}")
            self._show_error_dialog("Command 실행 오류", str(e))
            return False

        finally:
            self._is_processing = False
            self._hide_progress_dialog()

    def execute_batch_commands(self, commands: list[ICommand], description: str = "") -> bool:
        """배치 Command 실행 (UI 통합)"""
        try:
            if self._is_processing:
                self.logger.warning("이미 작업이 진행 중입니다")
                return False

            self._is_processing = True
            self._total_operations = len(commands)
            self._completed_operations = 0
            self._current_operation = description or f"배치 작업 ({len(commands)}개)"

            self.logger.info(f"배치 Command 실행 시작: {self._current_operation}")

            # 진행 상황 다이얼로그 표시
            self._show_progress_dialog(self._current_operation, len(commands))

            # 각 Command를 순차적으로 실행
            for i, command in enumerate(commands):
                try:
                    self._current_operation = f"{i + 1}/{len(commands)}: {command.description}"

                    # 진행 상황 업데이트
                    self._update_progress(i, len(commands), self._current_operation)

                    # Command 실행
                    if self.undo_stack_bridge:
                        success = self.undo_stack_bridge.execute_command(command)

                        if success:
                            self._completed_operations += 1
                            self.logger.debug(f"배치 Command 성공: {command.description}")
                        else:
                            self.logger.error(f"배치 Command 실패: {command.description}")
                            # 사용자에게 계속 진행할지 묻기
                            if not self._ask_continue_on_failure(command.description):
                                break
                    else:
                        self.logger.error("Undo 스택 브리지가 설정되지 않음")
                        return False

                except Exception as e:
                    self.logger.error(f"배치 Command 실행 중 오류: {command.description} - {e}")
                    if not self._ask_continue_on_failure(command.description):
                        break

            # 최종 결과 표시
            success_count = self._completed_operations
            total_count = len(commands)

            if success_count == total_count:
                self._show_success_dialog(
                    "배치 작업 완료", f"모든 {total_count}개 작업이 성공적으로 완료되었습니다."
                )
            else:
                self._show_info_dialog(
                    "배치 작업 완료", f"작업 완료: {success_count}/{total_count}개 성공"
                )

            self.logger.info(f"배치 Command 실행 완료: {success_count}/{total_count}개 성공")
            return success_count == total_count

        except Exception as e:
            self.logger.error(f"배치 Command 실행 중 오류: {e}")
            self._show_error_dialog("배치 작업 오류", str(e))
            return False

        finally:
            self._is_processing = False
            self._hide_progress_dialog()

    def undo_last_operation(self) -> bool:
        """마지막 작업 취소"""
        try:
            if self._is_processing:
                self.logger.warning("작업 진행 중에는 취소할 수 없습니다")
                return False

            if not self.undo_stack_bridge or not self.undo_stack_bridge.can_undo:
                self.logger.debug("취소할 작업이 없습니다")
                return False

            # 사용자 확인
            if not self._ask_confirmation("작업 취소", "마지막 작업을 취소하시겠습니까?"):
                return False

            self.logger.info("마지막 작업 취소 시작")

            # Undo 실행
            success = self.undo_stack_bridge.undo_last_command()

            if success:
                self._show_success_dialog("작업 취소", "마지막 작업이 성공적으로 취소되었습니다.")
                self.logger.info("마지막 작업 취소 완료")
            else:
                self._show_error_dialog("작업 취소", "작업 취소에 실패했습니다.")
                self.logger.error("마지막 작업 취소 실패")

            return success

        except Exception as e:
            self.logger.error(f"작업 취소 중 오류: {e}")
            self._show_error_dialog("작업 취소 오류", str(e))
            return False

    def redo_last_operation(self) -> bool:
        """마지막 취소된 작업 재실행"""
        try:
            if self._is_processing:
                self.logger.warning("작업 진행 중에는 재실행할 수 없습니다")
                return False

            if not self.undo_stack_bridge or not self.undo_stack_bridge.can_redo:
                self.logger.debug("재실행할 작업이 없습니다")
                return False

            self.logger.info("마지막 작업 재실행 시작")

            # Redo 실행
            success = self.undo_stack_bridge.redo_last_command()

            if success:
                self._show_success_dialog(
                    "작업 재실행", "마지막 작업이 성공적으로 재실행되었습니다."
                )
                self.logger.info("마지막 작업 재실행 완료")
            else:
                self._show_error_dialog("작업 재실행", "작업 재실행에 실패했습니다.")
                self.logger.error("마지막 작업 재실행 실패")

            return success

        except Exception as e:
            self.logger.error(f"작업 재실행 중 오류: {e}")
            self._show_error_dialog("작업 재실행 오류", str(e))
            return False

    def show_command_history(self):
        """Command 실행 히스토리 표시"""
        try:
            if not self.undo_stack_bridge:
                self._show_error_dialog("히스토리", "Undo 스택 브리지가 설정되지 않았습니다.")
                return

            history = self.undo_stack_bridge.get_command_history()

            if not history:
                self._show_info_dialog("히스토리", "실행된 Command가 없습니다.")
                return

            # 히스토리 정보를 사용자에게 표시
            history_text = "Command 실행 히스토리:\n\n"
            for i, item in enumerate(history, 1):
                history_text += f"{i}. {item['description']}\n"
                history_text += f"   상태: {'성공' if item['is_success'] else '실패'}\n"
                history_text += f"   스테이징 파일: {item['staged_files_count']}개\n"
                if item.get("execution_time_ms"):
                    history_text += f"   실행 시간: {item['execution_time_ms']:.1f}ms\n"
                history_text += "\n"

            self._show_info_dialog("Command 히스토리", history_text)

        except Exception as e:
            self.logger.error(f"Command 히스토리 표시 중 오류: {e}")
            self._show_error_dialog("히스토리 오류", str(e))

    def show_staging_summary(self):
        """스테이징 상태 요약 표시"""
        try:
            if not self.undo_stack_bridge:
                self._show_error_dialog("스테이징", "Undo 스택 브리지가 설정되지 않았습니다.")
                return

            summary = self.undo_stack_bridge.get_staging_summary()

            if "error" in summary:
                self._show_error_dialog("스테이징", summary["error"])
                return

            # 스테이징 요약 정보를 사용자에게 표시
            summary_text = "스테이징 상태 요약:\n\n"
            summary_text += f"총 스테이징된 파일: {summary.get('total_staged_files', 0)}개\n"
            summary_text += f"총 크기: {summary.get('total_size_mb', 0):.2f} MB\n"
            summary_text += f"스테이징 디렉토리: {summary.get('staging_directory', 'N/A')}\n"
            summary_text += f"자동 정리: {'활성화' if summary.get('auto_cleanup_enabled', False) else '비활성화'}\n"

            if summary.get("status_distribution"):
                summary_text += "\n상태별 분포:\n"
                for status, count in summary["status_distribution"].items():
                    summary_text += f"  {status}: {count}개\n"

            self._show_info_dialog("스테이징 상태", summary_text)

        except Exception as e:
            self.logger.error(f"스테이징 요약 표시 중 오류: {e}")
            self._show_error_dialog("스테이징 오류", str(e))

    # === 진행 상황 관리 ===

    def _show_progress_dialog(self, title: str, total_operations: int = 1):
        """진행 상황 다이얼로그 표시"""
        try:
            self._progress_dialog = QProgressDialog(
                title, "취소", 0, total_operations, self.main_window
            )
            self._progress_dialog.setWindowTitle("작업 진행 상황")
            self._progress_dialog.setModal(True)
            self._progress_dialog.setAutoClose(False)
            self._progress_dialog.setAutoReset(False)
            self._progress_dialog.show()

        except Exception as e:
            self.logger.error(f"진행 상황 다이얼로그 표시 실패: {e}")

    def _update_progress(self, current: int, total: int, description: str):
        """진행 상황 업데이트"""
        try:
            if self._progress_dialog:
                self._progress_dialog.setValue(current)
                self._progress_dialog.setLabelText(description)

            # 시그널 발행
            self.command_progress.emit(current, total, description)

        except Exception as e:
            self.logger.error(f"진행 상황 업데이트 실패: {e}")

    def _hide_progress_dialog(self):
        """진행 상황 다이얼로그 숨기기"""
        try:
            if self._progress_dialog:
                self._progress_dialog.close()
                self._progress_dialog = None

        except Exception as e:
            self.logger.error(f"진행 상황 다이얼로그 숨기기 실패: {e}")

    # === 사용자 상호작용 ===

    def _ask_confirmation(self, title: str, message: str) -> bool:
        """사용자 확인 요청"""
        try:
            reply = QMessageBox.question(
                self.main_window, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            return reply == QMessageBox.Yes

        except Exception as e:
            self.logger.error(f"사용자 확인 요청 실패: {e}")
            return False

    def _ask_continue_on_failure(self, operation_description: str) -> bool:
        """실패 시 계속 진행할지 묻기"""
        try:
            reply = QMessageBox.question(
                self.main_window,
                "작업 실패",
                f"작업이 실패했습니다: {operation_description}\n\n계속 진행하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            return reply == QMessageBox.Yes

        except Exception as e:
            self.logger.error(f"계속 진행 확인 요청 실패: {e}")
            return False

    def _show_error_dialog(self, title: str, message: str):
        """오류 다이얼로그 표시"""
        try:
            QMessageBox.critical(self.main_window, title, message)
        except Exception as e:
            self.logger.error(f"오류 다이얼로그 표시 실패: {e}")

    def _show_success_dialog(self, title: str, message: str):
        """성공 다이얼로그 표시"""
        try:
            QMessageBox.information(self.main_window, title, message)
        except Exception as e:
            self.logger.error(f"성공 다이얼로그 표시 실패: {e}")

    def _show_info_dialog(self, title: str, message: str):
        """정보 다이얼로그 표시"""
        try:
            QMessageBox.information(self.main_window, title, message)
        except Exception as e:
            self.logger.error(f"정보 다이얼로그 표시 실패: {e}")

    # === 이벤트 핸들러 ===

    def _on_command_executed(self, command_id: str, result: CommandResult):
        """Command 실행 완료 처리"""
        try:
            self.logger.debug(f"Command 실행 완료: {command_id}")
            self.command_executed.emit(command_id, result)

        except Exception as e:
            self.logger.error(f"Command 실행 완료 처리 중 오류: {e}")

    def _on_command_failed(self, command_id: str, error_message: str):
        """Command 실행 실패 처리"""
        try:
            self.logger.debug(f"Command 실행 실패: {command_id} - {error_message}")
            self.command_failed.emit(command_id, error_message)

        except Exception as e:
            self.logger.error(f"Command 실행 실패 처리 중 오류: {e}")

    def _on_staging_started(self, command_id: str, staged_files: list):
        """스테이징 시작 처리"""
        try:
            self.logger.debug(f"스테이징 시작: {command_id}")
            self.staging_progress.emit(0, len(staged_files), "스테이징 시작")

        except Exception as e:
            self.logger.error(f"스테이징 시작 처리 중 오류: {e}")

    def _on_staging_completed(self, command_id: str, staged_files: list):
        """스테이징 완료 처리"""
        try:
            self.logger.debug(f"스테이징 완료: {command_id} - {len(staged_files)}개 파일")
            self.staging_completed.emit(staged_files)

        except Exception as e:
            self.logger.error(f"스테이징 완료 처리 중 오류: {e}")

    def _on_journal_entry_created(self, command_id: str, journal_entry_id: str):
        """저널 엔트리 생성 처리"""
        try:
            self.logger.debug(f"저널 엔트리 생성: {command_id} -> {journal_entry_id}")
            self.journal_updated.emit(command_id, journal_entry_id)

        except Exception as e:
            self.logger.error(f"저널 엔트리 생성 처리 중 오류: {e}")

    # === 공개 API ===

    @property
    def is_processing(self) -> bool:
        """작업 진행 중 여부"""
        return self._is_processing

    @property
    def current_operation(self) -> str:
        """현재 진행 중인 작업"""
        return self._current_operation

    @property
    def can_undo(self) -> bool:
        """Undo 가능 여부"""
        return bool(self.undo_stack_bridge and self.undo_stack_bridge.can_undo)

    @property
    def can_redo(self) -> bool:
        """Redo 가능 여부"""
        return bool(self.undo_stack_bridge and self.undo_stack_bridge.can_redo)

    def clear_history(self):
        """Command 히스토리 정리"""
        try:
            if self.undo_stack_bridge:
                self.undo_stack_bridge.clear()
                self.logger.info("Command 히스토리 정리 완료")

        except Exception as e:
            self.logger.error(f"Command 히스토리 정리 중 오류: {e}")

    def set_staging_manager(self, staging_manager: IStagingManager):
        """스테이징 매니저 설정"""
        self.staging_manager = staging_manager
        self.logger.info("스테이징 매니저 설정됨")

    def set_journal_manager(self, journal_manager: IJournalManager):
        """저널 매니저 설정"""
        self.journal_manager = journal_manager
        self.logger.info("저널 매니저 설정됨")
