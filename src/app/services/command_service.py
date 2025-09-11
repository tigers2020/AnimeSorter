"""
통합된 명령 관리 서비스 - AnimeSorter

기존의 여러 Command Manager 클래스들을 통합하여 단일 서비스로 제공합니다.
- CommandSystemManager
- UndoRedoManager
- UndoRedoShortcutManager
- UndoRedoMenuManager
- UndoRedoToolbarManager
- StagingManager
- CoreEventHandlerManager
- EventBusManager
- UICommandBridge
- QUndoStackBridge
"""

import logging
from typing import Any, Optional, Protocol

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)


class ICommand(Protocol):
    """명령 인터페이스"""

    def execute(self) -> bool:
        """명령 실행"""
        ...

    def undo(self) -> bool:
        """명령 실행 취소"""
        ...

    def redo(self) -> bool:
        """명령 재실행"""
        ...

    def get_description(self) -> str:
        """명령 설명 반환"""
        ...


class ICommandInvoker(Protocol):
    """명령 실행자 인터페이스"""

    def execute_command(self, command: ICommand) -> bool:
        """명령 실행"""
        ...

    def can_undo(self) -> bool:
        """실행 취소 가능 여부"""
        ...

    def can_redo(self) -> bool:
        """재실행 가능 여부"""
        ...


class IUndoRedoManager(Protocol):
    """실행 취소/재실행 관리자 인터페이스"""

    def undo(self) -> bool:
        """실행 취소"""
        ...

    def redo(self) -> bool:
        """재실행"""
        ...

    def can_undo(self) -> bool:
        """실행 취소 가능 여부"""
        ...

    def can_redo(self) -> bool:
        """재실행 가능 여부"""
        ...


class IStagingManager(Protocol):
    """스테이징 관리자 인터페이스"""

    def stage_files(self, files: list[str]) -> bool:
        """파일 스테이징"""
        ...

    def unstage_files(self, files: list[str]) -> bool:
        """파일 언스테이징"""
        ...

    def get_staged_files(self) -> list[str]:
        """스테이징된 파일 목록"""
        ...


class CommandResult:
    """명령 실행 결과"""

    def __init__(
        self,
        success: bool,
        description: str = "",
        staged_files: list[str] = None,
        error_message: str = "",
    ):
        self.success = success
        self.description = description
        self.staged_files = staged_files or []
        self.error_message = error_message


class CommandService(QObject):
    """통합된 명령 관리 서비스"""

    # 시그널 정의
    command_executed = pyqtSignal(str, object)  # command_id, result
    command_failed = pyqtSignal(str, str)  # command_id, error_message
    command_progress = pyqtSignal(int, int, str)  # current, total, description
    staging_progress = pyqtSignal(int, int, str)  # current, total, description
    staging_completed = pyqtSignal(list)  # staged_files
    undo_available = pyqtSignal(bool)
    redo_available = pyqtSignal(bool)

    def __init__(self, main_window: QMainWindow, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 서비스 컴포넌트들
        self._command_invoker: Optional[ICommandInvoker] = None
        self._undo_redo_manager: Optional[IUndoRedoManager] = None
        self._staging_manager: Optional[IStagingManager] = None
        self._ui_command_bridge = None
        self._undo_stack_bridge = None

        # 명령 히스토리
        self._command_history: list[dict[str, Any]] = []
        self._current_command_index = -1

        self._initialize_components()
        self.logger.info("명령 서비스 초기화 완료")

    def _initialize_components(self):
        """명령 서비스 컴포넌트들 초기화"""
        try:
            self._initialize_command_invoker()
            self._initialize_undo_redo_manager()
            self._initialize_staging_manager()
            self._initialize_ui_bridges()
            self.logger.info("✅ 명령 서비스 컴포넌트 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 명령 서비스 컴포넌트 초기화 실패: {e}")

    def _initialize_command_invoker(self):
        """명령 실행자 초기화"""
        try:
            from src.app import ICommandInvoker, get_service

            self._command_invoker = get_service(ICommandInvoker)
            if self._command_invoker:
                self.logger.info("✅ 명령 실행자 초기화 완료")
            else:
                self.logger.warning("⚠️ 명령 실행자를 가져올 수 없음")
        except Exception as e:
            self.logger.error(f"❌ 명령 실행자 초기화 실패: {e}")

    def _initialize_undo_redo_manager(self):
        """실행 취소/재실행 관리자 초기화"""
        try:
            from src.app import IUndoRedoManager, get_service

            self._undo_redo_manager = get_service(IUndoRedoManager)
            if self._undo_redo_manager:
                self.logger.info("✅ 실행 취소/재실행 관리자 초기화 완료")
            else:
                self.logger.warning("⚠️ 실행 취소/재실행 관리자를 가져올 수 없음")
        except Exception as e:
            self.logger.error(f"❌ 실행 취소/재실행 관리자 초기화 실패: {e}")

    def _initialize_staging_manager(self):
        """스테이징 관리자 초기화"""
        try:
            from src.app.staging import StagingManager

            self._staging_manager = StagingManager()
            self.logger.info("✅ 스테이징 관리자 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 스테이징 관리자 초기화 실패: {e}")

    def _initialize_ui_bridges(self):
        """UI 브리지 초기화"""
        try:
            from src.app.ui import UICommandBridge
            from src.app.undo_redo import QUndoStackBridge

            # UndoStack 브리지 초기화
            if self._staging_manager:
                self._undo_stack_bridge = QUndoStackBridge(staging_manager=self._staging_manager)
                self.logger.info("✅ UndoStack 브리지 초기화 완료")

            # UI 명령 브리지 초기화
            if self._undo_stack_bridge and self._staging_manager:
                self._ui_command_bridge = UICommandBridge(
                    main_window=self.main_window,
                    undo_stack_bridge=self._undo_stack_bridge,
                    staging_manager=self._staging_manager,
                )
                self._setup_ui_command_signals()
                self.logger.info("✅ UI 명령 브리지 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ UI 브리지 초기화 실패: {e}")

    def _setup_ui_command_signals(self):
        """UI 명령 시그널 연결"""
        try:
            if self._ui_command_bridge:
                self._ui_command_bridge.command_executed.connect(self.on_command_executed)
                self._ui_command_bridge.command_failed.connect(self.on_command_failed)
                self._ui_command_bridge.command_progress.connect(self.on_command_progress)
                self._ui_command_bridge.staging_progress.connect(self.on_staging_progress)
                self._ui_command_bridge.staging_completed.connect(self.on_staging_completed)
                self.logger.info("✅ UI 명령 시그널 연결 완료")
        except Exception as e:
            self.logger.error(f"❌ UI 명령 시그널 연결 실패: {e}")

    # 명령 실행
    def execute_command(self, command: ICommand, show_progress: bool = True) -> bool:
        """명령 실행"""
        if not self._ui_command_bridge:
            self.logger.error("❌ UI 명령 브리지가 초기화되지 않았습니다")
            return False

        try:
            result = self._ui_command_bridge.execute_command(command, show_progress)
            if result:
                self._add_to_history(command)
                self._update_undo_redo_availability()
            return result
        except Exception as e:
            self.logger.error(f"❌ 명령 실행 실패: {e}")
            return False

    def execute_batch_commands(self, commands: list[ICommand], description: str = "") -> bool:
        """배치 명령 실행"""
        if not self._ui_command_bridge:
            self.logger.error("❌ UI 명령 브리지가 초기화되지 않았습니다")
            return False

        try:
            result = self._ui_command_bridge.execute_batch_commands(commands, description)
            if result:
                for command in commands:
                    self._add_to_history(command)
                self._update_undo_redo_availability()
            return result
        except Exception as e:
            self.logger.error(f"❌ 배치 명령 실행 실패: {e}")
            return False

    # 실행 취소/재실행
    def undo_last_operation(self) -> bool:
        """마지막 작업 실행 취소"""
        if not self._undo_redo_manager:
            self.logger.warning("⚠️ 실행 취소할 작업이 없습니다")
            return False

        try:
            if not self._undo_redo_manager.can_undo():
                self.logger.warning("⚠️ 실행 취소할 작업이 없습니다")
                return False

            success = self._undo_redo_manager.undo()
            if success:
                self._update_undo_redo_availability()
                self.logger.info("✅ 실행 취소 완료")
            return success
        except Exception as e:
            self.logger.error(f"❌ 실행 취소 실패: {e}")
            return False

    def redo_last_operation(self) -> bool:
        """마지막 작업 재실행"""
        if not self._undo_redo_manager:
            self.logger.warning("⚠️ 재실행할 작업이 없습니다")
            return False

        try:
            if not self._undo_redo_manager.can_redo():
                self.logger.warning("⚠️ 재실행할 작업이 없습니다")
                return False

            success = self._undo_redo_manager.redo()
            if success:
                self._update_undo_redo_availability()
                self.logger.info("✅ 재실행 완료")
            return success
        except Exception as e:
            self.logger.error(f"❌ 재실행 실패: {e}")
            return False

    def can_undo(self) -> bool:
        """실행 취소 가능 여부"""
        if self._undo_redo_manager:
            return self._undo_redo_manager.can_undo()
        return False

    def can_redo(self) -> bool:
        """재실행 가능 여부"""
        if self._undo_redo_manager:
            return self._undo_redo_manager.can_redo()
        return False

    # 스테이징 관리
    def stage_files(self, files: list[str]) -> bool:
        """파일 스테이징"""
        if not self._staging_manager:
            self.logger.error("❌ 스테이징 관리자가 초기화되지 않았습니다")
            return False

        try:
            result = self._staging_manager.stage_files(files)
            if result:
                self.logger.info(f"✅ {len(files)}개 파일 스테이징 완료")
            return result
        except Exception as e:
            self.logger.error(f"❌ 파일 스테이징 실패: {e}")
            return False

    def unstage_files(self, files: list[str]) -> bool:
        """파일 언스테이징"""
        if not self._staging_manager:
            self.logger.error("❌ 스테이징 관리자가 초기화되지 않았습니다")
            return False

        try:
            result = self._staging_manager.unstage_files(files)
            if result:
                self.logger.info(f"✅ {len(files)}개 파일 언스테이징 완료")
            return result
        except Exception as e:
            self.logger.error(f"❌ 파일 언스테이징 실패: {e}")
            return False

    def get_staged_files(self) -> list[str]:
        """스테이징된 파일 목록"""
        if self._staging_manager:
            return self._staging_manager.get_staged_files()
        return []

    # 명령 히스토리 관리
    def get_command_history(self) -> list[dict[str, Any]]:
        """명령 히스토리 반환"""
        return self._command_history.copy()

    def clear_command_history(self):
        """명령 히스토리 초기화"""
        self._command_history.clear()
        self._current_command_index = -1
        self._update_undo_redo_availability()
        self.logger.info("✅ 명령 히스토리 초기화 완료")

    def show_command_history_ui(self):
        """명령 히스토리 UI 표시"""
        if self._ui_command_bridge:
            self._ui_command_bridge.show_command_history()

    def show_staging_summary_ui(self):
        """스테이징 요약 UI 표시"""
        if self._ui_command_bridge:
            self._ui_command_bridge.show_staging_summary()

    # 이벤트 핸들러
    def on_command_executed(self, command_id: str, result: CommandResult):
        """명령 실행 완료 처리"""
        try:
            self.logger.info(f"✅ 명령 실행 완료: {command_id}")
            self.command_executed.emit(command_id, result)

            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(
                    f"명령 실행 완료: {result.description if hasattr(result, 'description') else command_id}"
                )

            if hasattr(result, "staged_files") and result.staged_files:
                self.logger.info(f"📁 {len(result.staged_files)}개 파일이 스테이징되었습니다")
        except Exception as e:
            self.logger.error(f"❌ 명령 실행 완료 처리 중 오류: {e}")

    def on_command_failed(self, command_id: str, error_message: str):
        """명령 실행 실패 처리"""
        try:
            self.logger.error(f"❌ 명령 실행 실패: {command_id} - {error_message}")
            self.command_failed.emit(command_id, error_message)

            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(f"명령 실행 실패: {error_message}")
        except Exception as e:
            self.logger.error(f"❌ 명령 실행 실패 처리 중 오류: {e}")

    def on_command_progress(self, current: int, total: int, description: str):
        """명령 진행 상황 처리"""
        try:
            self.logger.info(f"📊 명령 진행 상황: {current}/{total} - {description}")
            self.command_progress.emit(current, total, description)

            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(
                    f"진행 중: {description} ({current}/{total})"
                )
        except Exception as e:
            self.logger.error(f"❌ 명령 진행 상황 처리 중 오류: {e}")

    def on_staging_progress(self, current: int, total: int, description: str):
        """스테이징 진행 상황 처리"""
        try:
            self.logger.info(f"📁 스테이징 진행 상황: {current}/{total} - {description}")
            self.staging_progress.emit(current, total, description)

            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(
                    f"스테이징 중: {description} ({current}/{total})"
                )
        except Exception as e:
            self.logger.error(f"❌ 스테이징 진행 상황 처리 중 오류: {e}")

    def on_staging_completed(self, staged_files: list[str]):
        """스테이징 완료 처리"""
        try:
            self.logger.info(f"✅ 스테이징 완료: {len(staged_files)}개 파일")
            self.staging_completed.emit(staged_files)

            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(
                    f"스테이징 완료: {len(staged_files)}개 파일 준비됨"
                )
        except Exception as e:
            self.logger.error(f"❌ 스테이징 완료 처리 중 오류: {e}")

    # 내부 메서드들
    def _add_to_history(self, command: ICommand):
        """명령을 히스토리에 추가"""
        command_info = {
            "timestamp": self._get_current_timestamp(),
            "description": command.get_description(),
            "command": command,
        }

        # 현재 인덱스 이후의 히스토리 제거 (새로운 명령 실행 시)
        if self._current_command_index < len(self._command_history) - 1:
            self._command_history = self._command_history[: self._current_command_index + 1]

        self._command_history.append(command_info)
        self._current_command_index = len(self._command_history) - 1

        # 히스토리 크기 제한 (최대 100개)
        if len(self._command_history) > 100:
            self._command_history.pop(0)
            self._current_command_index -= 1

    def _update_undo_redo_availability(self):
        """실행 취소/재실행 가능 상태 업데이트"""
        can_undo = self.can_undo()
        can_redo = self.can_redo()

        self.undo_available.emit(can_undo)
        self.redo_available.emit(can_redo)

    def _get_current_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 서비스 상태 관리
    def get_service_health_status(self) -> dict[str, Any]:
        """서비스 건강 상태 반환"""
        return {
            "command_invoker_available": self._command_invoker is not None,
            "undo_redo_manager_available": self._undo_redo_manager is not None,
            "staging_manager_available": self._staging_manager is not None,
            "ui_command_bridge_available": self._ui_command_bridge is not None,
            "undo_stack_bridge_available": self._undo_stack_bridge is not None,
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo(),
            "staged_files_count": len(self.get_staged_files()),
            "command_history_count": len(self._command_history),
        }

    def shutdown(self):
        """서비스 종료"""
        try:
            self.logger.info("명령 서비스 종료 중...")

            # 명령 히스토리 초기화
            self.clear_command_history()

            # UI 브리지 정리
            if self._ui_command_bridge:
                self._ui_command_bridge = None

            if self._undo_stack_bridge:
                self._undo_stack_bridge = None

            self.logger.info("✅ 명령 서비스 종료 완료")
        except Exception as e:
            self.logger.error(f"❌ 명령 서비스 종료 실패: {e}")
