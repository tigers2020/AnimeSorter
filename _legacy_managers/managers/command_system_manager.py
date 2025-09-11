"""
Command System Manager for MainWindow

MainWindow의 Command System 관련 메서드들을 관리하는 클래스입니다.
Command 실행, Undo/Redo, UI Command 브리지를 담당합니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import QMainWindow

from src.app import ICommandInvoker, IUndoRedoManager, get_service
# Journal 시스템 제거됨
from src.app.staging import StagingManager
from src.app.ui import UICommandBridge
from src.app.undo_redo import QUndoStackBridge


class CommandSystemManager:
    """Command System 관련 메서드들을 관리하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        """CommandSystemManager 초기화"""
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        self.command_invoker: ICommandInvoker | None = None
        self.undo_redo_manager: IUndoRedoManager | None = None
        self.staging_manager: StagingManager | None = None
        # Journal 시스템 제거됨
        self.undo_stack_bridge: QUndoStackBridge | None = None
        self.ui_command_bridge: UICommandBridge | None = None
        self.init_command_system()
        self.init_undo_redo_system()

    def init_command_system(self):
        """Command System 초기화"""
        try:
            self.command_invoker = get_service(ICommandInvoker)
            self.logger.info(f"✅ CommandInvoker 연결됨: {id(self.command_invoker)}")
        except Exception as e:
            self.logger.error(f"⚠️ Command System 초기화 실패: {e}")
            self.command_invoker = None

    def init_undo_redo_system(self):
        """Undo/Redo System 초기화"""
        try:
            self.undo_redo_manager = get_service(IUndoRedoManager)
            self.logger.info(f"✅ UndoRedoManager 연결됨: {id(self.undo_redo_manager)}")
            self.init_ui_command_system()
            self.logger.info("✅ UI Command 시스템 초기화 완료")
        except Exception as e:
            self.logger.error(f"⚠️ Undo/Redo System 초기화 실패: {e}")
            self.undo_redo_manager = None

    def init_ui_command_system(self):
        """UI Command 시스템 초기화"""
        try:
            self.staging_manager = StagingManager()
            self.logger.info(f"✅ StagingManager 초기화됨: {id(self.staging_manager)}")
            # Journal 시스템 제거됨
            self.undo_stack_bridge = QUndoStackBridge(staging_manager=self.staging_manager)
            self.logger.info(f"✅ QUndoStackBridge 초기화됨: {id(self.undo_stack_bridge)}")
            self.ui_command_bridge = UICommandBridge(
                main_window=self.main_window,
                undo_stack_bridge=self.undo_stack_bridge,
                staging_manager=self.staging_manager,
            )
            self.logger.info(f"✅ UICommandBridge 초기화됨: {id(self.ui_command_bridge)}")
            self.setup_ui_command_signals()
            self.logger.info("✅ UI Command 시그널 연결 완료")
        except Exception as e:
            self.logger.error(f"⚠️ UI Command 시스템 초기화 실패: {e}")
            self.staging_manager = None
            # Journal 시스템 제거됨
            self.undo_stack_bridge = None
            self.ui_command_bridge = None

    def setup_ui_command_signals(self):
        """UI Command 시그널 연결"""
        try:
            if self.ui_command_bridge:
                self.ui_command_bridge.command_executed.connect(self.on_command_executed)
                self.ui_command_bridge.command_failed.connect(self.on_command_failed)
                self.ui_command_bridge.command_progress.connect(self.on_command_progress)
                self.ui_command_bridge.staging_progress.connect(self.on_staging_progress)
                self.ui_command_bridge.staging_completed.connect(self.on_staging_completed)
                # Journal 시스템 제거됨
                self.logger.info("✅ UI Command 시그널 연결 완료")
        except Exception as e:
            self.logger.error(f"⚠️ UI Command 시그널 연결 실패: {e}")

    def undo_last_operation(self):
        """마지막 작업 실행 취소 (기존 시스템)"""
        try:
            if not (self.undo_redo_manager and self.undo_redo_manager.can_undo()):
                self.logger.warning("⚠️ 실행 취소할 작업이 없습니다 (기존 시스템)")
                return
            success = self.undo_redo_manager.undo()
            if not success:
                self.logger.error("❌ 실행 취소 실패 (기존 시스템)")
                return
            self.logger.info("✅ 실행 취소 완료 (기존 시스템)")
        except Exception as e:
            self.logger.error(f"❌ 실행 취소 실패 (기존 시스템): {e}")

    def redo_last_operation(self):
        """마지막 작업 재실행 (기존 시스템)"""
        try:
            if not (self.undo_redo_manager and self.undo_redo_manager.can_redo()):
                self.logger.warning("⚠️ 재실행할 작업이 없습니다 (기존 시스템)")
                return
            success = self.undo_redo_manager.redo()
            if not success:
                self.logger.error("❌ 재실행 실패 (기존 시스템)")
                return
            self.logger.info("✅ 재실행 완료 (기존 시스템)")
        except Exception as e:
            self.logger.error(f"❌ 재실행 실패 (기존 시스템): {e}")

    def undo_last_operation_new(self):
        """마지막 작업 실행 취소 (새로운 UI Command 시스템)"""
        return self.undo_last_operation_ui()

    def redo_last_operation_new(self):
        """마지막 작업 재실행 (새로운 UI Command 시스템)"""
        return self.redo_last_operation_ui()

    def on_command_executed(self, command_id: str, result):
        """Command 실행 완료 처리"""
        try:
            self.logger.info(f"✅ UI Command 실행 완료: {command_id}")
            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(
                    f"Command 실행 완료: {result.description if hasattr(result, 'description') else command_id}"
                )
            if hasattr(result, "staged_files") and result.staged_files:
                self.logger.info(f"📁 {len(result.staged_files)}개 파일이 스테이징되었습니다")
        except Exception as e:
            self.logger.error(f"❌ Command 실행 완료 처리 중 오류: {e}")

    def on_command_failed(self, command_id: str, error_message: str):
        """Command 실행 실패 처리"""
        try:
            self.logger.error(f"❌ UI Command 실행 실패: {command_id} - {error_message}")
            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(f"Command 실행 실패: {error_message}")
        except Exception as e:
            self.logger.error(f"❌ Command 실행 실패 처리 중 오류: {e}")

    def on_command_progress(self, current: int, total: int, description: str):
        """Command 진행 상황 처리"""
        try:
            self.logger.info(f"📊 Command 진행 상황: {current}/{total} - {description}")
            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(
                    f"진행 중: {description} ({current}/{total})"
                )
        except Exception as e:
            self.logger.error(f"❌ Command 진행 상황 처리 중 오류: {e}")

    def on_staging_progress(self, current: int, total: int, description: str):
        """스테이징 진행 상황 처리"""
        try:
            self.logger.info(f"📁 스테이징 진행 상황: {current}/{total} - {description}")
            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(
                    f"스테이징 중: {description} ({current}/{total})"
                )
        except Exception as e:
            self.logger.error(f"❌ 스테이징 진행 상황 처리 중 오류: {e}")

    def on_staging_completed(self, staged_files: list):
        """스테이징 완료 처리"""
        try:
            self.logger.info(f"✅ 스테이징 완료: {len(staged_files)}개 파일")
            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(
                    f"스테이징 완료: {len(staged_files)}개 파일 준비됨"
                )
        except Exception as e:
            self.logger.error(f"❌ 스테이징 완료 처리 중 오류: {e}")

    # Journal 시스템 제거됨

    def handle_command_executed(self, event):
        """Command 실행 완료 이벤트 처리"""
        try:
            self.logger.info(f"▶️ [CommandSystemManager] 명령 실행: {event.command_id}")
            self.main_window.update_status_bar("명령 실행됨")
        except Exception as e:
            self.logger.error(f"❌ Command 실행 완료 이벤트 처리 중 오류: {e}")

    def handle_command_undone(self, event):
        """Command 실행 취소 이벤트 처리"""
        try:
            self.logger.info(f"↩️ [CommandSystemManager] 명령 실행 취소: {event.command_id}")
            self.main_window.update_status_bar("명령 실행 취소됨")
        except Exception as e:
            self.logger.error(f"❌ Command 실행 취소 이벤트 처리 중 오류: {e}")

    def handle_command_redone(self, event):
        """Command 재실행 이벤트 처리"""
        try:
            self.logger.info(f"↪️ [CommandSystemManager] 명령 재실행: {event.command_id}")
            self.main_window.update_status_bar("명령 재실행됨")
        except Exception as e:
            self.logger.error(f"❌ Command 재실행 이벤트 처리 중 오류: {e}")

    def handle_command_failed(self, event):
        """Command 실패 이벤트 처리"""
        try:
            self.logger.error(
                f"❌ [CommandSystemManager] 명령 실패: {event.command_id} - {event.error_message}"
            )
            self.main_window.show_error_message("명령 실패", event.error_message)
        except Exception as e:
            self.logger.error(f"❌ Command 실패 이벤트 처리 중 오류: {e}")

    def execute_command(self, command, show_progress: bool = True) -> bool:
        """UI Command 브리지를 통해 Command 실행"""
        if not self.ui_command_bridge:
            self.logger.error("❌ UI Command 브리지가 초기화되지 않았습니다")
            return False
        return self.ui_command_bridge.execute_command(command, show_progress)

    def execute_batch_commands(self, commands: list, description: str = "") -> bool:
        """UI Command 브리지를 통해 배치 Command 실행"""
        if not self.ui_command_bridge:
            self.logger.error("❌ UI Command 브리지가 초기화되지 않았습니다")
            return False
        return self.ui_command_bridge.execute_batch_commands(commands, description)

    def undo_last_operation_ui(self) -> bool:
        """UI Command 브리지를 통해 마지막 작업 취소"""
        if not self.ui_command_bridge:
            self.logger.error("❌ UI Command 브리지가 초기화되지 않았습니다")
            return False
        return self.ui_command_bridge.undo_last_operation()

    def redo_last_operation_ui(self) -> bool:
        """UI Command 브리지를 통해 마지막 작업 재실행"""
        if not self.ui_command_bridge:
            self.logger.error("❌ UI Command 브리지가 초기화되지 않았습니다")
            return False
        return self.ui_command_bridge.redo_last_operation()

    def show_command_history_ui(self):
        """UI Command 브리지를 통해 Command 히스토리 표시"""
        if not self.ui_command_bridge:
            self.logger.error("❌ UI Command 브리지가 초기화되지 않았습니다")
            return
        self.ui_command_bridge.show_command_history()

    def show_staging_summary_ui(self):
        """UI Command 브리지를 통해 스테이징 요약 표시"""
        if not self.ui_command_bridge:
            self.logger.error("❌ UI Command 브리지가 초기화되지 않았습니다")
            return
        self.ui_command_bridge.show_staging_summary()
