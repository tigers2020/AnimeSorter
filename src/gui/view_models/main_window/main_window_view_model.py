"""
MainWindow ViewModel - Phase 3.1 뷰모델 분할
메인 윈도우의 ViewModel 로직을 담당합니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from src.app import (ErrorMessageEvent, FileCountUpdateEvent,
                     FilesScannedEvent, IBackgroundTaskService,
                     IFileScanService, IUIUpdateService, MenuStateUpdateEvent,
                     StatusBarUpdateEvent, SuccessMessageEvent,
                     TableDataUpdateEvent, TaskCancelledEvent,
                     TaskCompletedEvent, TaskFailedEvent, TaskProgressEvent,
                     TaskStartedEvent, TypedEventBus, UIStateUpdateEvent,
                     WindowTitleUpdateEvent, get_event_bus, get_service)

from .application_state import ApplicationState, UICapabilities


class MainWindowViewModel(QObject):
    """메인 윈도우 ViewModel"""

    state_changed = pyqtSignal()
    capabilities_changed = pyqtSignal()
    status_message_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(str, int)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._state = ApplicationState()
        self._capabilities = UICapabilities.from_app_state(self._state)
        self.event_bus: TypedEventBus = get_event_bus()
        self.file_scan_service: IFileScanService = get_service(IFileScanService)
        self.ui_update_service: IUIUpdateService = get_service(IUIUpdateService)
        self.background_task_service: IBackgroundTaskService = get_service(IBackgroundTaskService)
        self._connect_events()

    def _connect_events(self):
        """이벤트 연결 설정"""
        self.event_bus.subscribe(FilesScannedEvent, self._on_files_scanned)
        self.event_bus.subscribe(FileCountUpdateEvent, self._on_file_count_updated)
        self.event_bus.subscribe(TaskStartedEvent, self._on_task_started)
        self.event_bus.subscribe(TaskProgressEvent, self._on_task_progress)
        self.event_bus.subscribe(TaskCompletedEvent, self._on_task_completed)
        self.event_bus.subscribe(TaskFailedEvent, self._on_task_failed)
        self.event_bus.subscribe(TaskCancelledEvent, self._on_task_cancelled)
        self.event_bus.subscribe(StatusBarUpdateEvent, self._on_status_bar_update)
        self.event_bus.subscribe(SuccessMessageEvent, self._on_success_message)
        self.event_bus.subscribe(ErrorMessageEvent, self._on_error_message)
        self.event_bus.subscribe(WindowTitleUpdateEvent, self._on_window_title_update)
        self.event_bus.subscribe(UIStateUpdateEvent, self._on_ui_state_update)
        self.event_bus.subscribe(MenuStateUpdateEvent, self._on_menu_state_update)
        self.event_bus.subscribe(TableDataUpdateEvent, self._on_table_data_update)

    @pyqtProperty(bool, notify=state_changed)
    def is_scanning(self) -> bool:
        return self._state.is_scanning

    @pyqtProperty(bool, notify=state_changed)
    def is_organizing(self) -> bool:
        return self._state.is_organizing

    @pyqtProperty(bool, notify=state_changed)
    def is_searching_tmdb(self) -> bool:
        return self._state.is_searching_tmdb

    @pyqtProperty(bool, notify=state_changed)
    def has_scanned_files(self) -> bool:
        return self._state.has_scanned_files

    @pyqtProperty(bool, notify=state_changed)
    def has_grouped_files(self) -> bool:
        return self._state.has_grouped_files

    @pyqtProperty(bool, notify=state_changed)
    def has_tmdb_matches(self) -> bool:
        return self._state.has_tmdb_matches

    @pyqtProperty(str, notify=state_changed)
    def status_message(self) -> str:
        return self._state.status_message

    @pyqtProperty(int, notify=state_changed)
    def scan_progress(self) -> int:
        return self._state.scan_progress

    @pyqtProperty(int, notify=state_changed)
    def organize_progress(self) -> int:
        return self._state.organize_progress

    @pyqtProperty(int, notify=state_changed)
    def tmdb_progress(self) -> int:
        return self._state.tmdb_progress

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_start_scan(self) -> bool:
        return self._capabilities.can_start_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_stop_scan(self) -> bool:
        return self._capabilities.can_stop_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_start_organize(self) -> bool:
        return self._capabilities.can_start_organize

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_start_tmdb_search(self) -> bool:
        return self._capabilities.can_start_tmdb_search

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_clear_results(self) -> bool:
        return self._capabilities.can_clear_results

    def _on_files_scanned(self, event: FilesScannedEvent):
        """파일 스캔 완료 이벤트 처리"""
        self._state.has_scanned_files = True
        self._state.scanned_directory = str(event.directory_path)
        self._update_capabilities()
        self.state_changed.emit()

    def _on_file_count_updated(self, event: FileCountUpdateEvent):
        """파일 수 업데이트 이벤트 처리"""
        self._state.has_scanned_files = event.total_files > 0
        self._update_capabilities()
        self.state_changed.emit()

    def _on_task_started(self, event: TaskStartedEvent):
        """작업 시작 이벤트 처리"""
        if event.task_type == "scan":
            self._state.is_scanning = True
            self._state.current_scan_id = event.task_id
        elif event.task_type == "organize":
            self._state.is_organizing = True
        elif event.task_type == "tmdb_search":
            self._state.is_searching_tmdb = True
        self._update_capabilities()
        self.state_changed.emit()

    def _on_task_progress(self, event: TaskProgressEvent):
        """작업 진행률 이벤트 처리"""
        if event.task_type == "scan":
            self._state.scan_progress = event.progress
        elif event.task_type == "organize":
            self._state.organize_progress = event.progress
        elif event.task_type == "tmdb_search":
            self._state.tmdb_progress = event.progress
        self.progress_changed.emit(event.task_type, event.progress)

    def _on_task_completed(self, event: TaskCompletedEvent):
        """작업 완료 이벤트 처리"""
        if event.task_type == "scan":
            self._state.is_scanning = False
            self._state.current_scan_id = None
            self._state.scan_progress = 100
        elif event.task_type == "organize":
            self._state.is_organizing = False
            self._state.organize_progress = 100
        elif event.task_type == "tmdb_search":
            self._state.is_searching_tmdb = False
            self._state.tmdb_progress = 100
        self._update_capabilities()
        self.state_changed.emit()

    def _on_task_failed(self, event: TaskFailedEvent):
        """작업 실패 이벤트 처리"""
        if event.task_type == "scan":
            self._state.is_scanning = False
            self._state.current_scan_id = None
        elif event.task_type == "organize":
            self._state.is_organizing = False
        elif event.task_type == "tmdb_search":
            self._state.is_searching_tmdb = False
        self._state.last_error = event.error_message
        self._update_capabilities()
        self.state_changed.emit()
        self.error_occurred.emit(event.error_message)

    def _on_task_cancelled(self, event: TaskCancelledEvent):
        """작업 취소 이벤트 처리"""
        if event.task_type == "scan":
            self._state.is_scanning = False
            self._state.current_scan_id = None
        elif event.task_type == "organize":
            self._state.is_organizing = False
        elif event.task_type == "tmdb_search":
            self._state.is_searching_tmdb = False
        self._update_capabilities()
        self.state_changed.emit()

    def _on_status_bar_update(self, event: StatusBarUpdateEvent):
        """상태바 업데이트 이벤트 처리"""
        self._state.status_message = event.message
        self.status_message_changed.emit(event.message)

    def _on_success_message(self, event: SuccessMessageEvent):
        """성공 메시지 이벤트 처리"""
        self._state.status_message = event.message
        self._state.last_error = None
        self.status_message_changed.emit(event.message)

    def _on_error_message(self, event: ErrorMessageEvent):
        """오류 메시지 이벤트 처리"""
        self._state.status_message = event.message
        self._state.last_error = event.message
        self.status_message_changed.emit(event.message)
        self.error_occurred.emit(event.message)

    def _on_window_title_update(self, event: WindowTitleUpdateEvent):
        """윈도우 제목 업데이트 이벤트 처리"""

    def _on_ui_state_update(self, event: UIStateUpdateEvent):
        """UI 상태 업데이트 이벤트 처리"""

    def _on_menu_state_update(self, event: MenuStateUpdateEvent):
        """메뉴 상태 업데이트 이벤트 처리"""

    def _on_table_data_update(self, event: TableDataUpdateEvent):
        """테이블 데이터 업데이트 이벤트 처리"""

    def _update_capabilities(self):
        """UI 기능 상태 업데이트"""
        old_capabilities = self._capabilities
        self._capabilities = UICapabilities.from_app_state(self._state)
        if old_capabilities != self._capabilities:
            self.capabilities_changed.emit()

    def start_scan(self, directory_path: str):
        """스캔 시작"""
        if not self.can_start_scan:
            self.logger.warning("스캔을 시작할 수 없습니다")
            return
        try:
            self.file_scan_service.scan_directory(directory_path)
        except Exception as e:
            self.logger.error(f"스캔 시작 실패: {e}")
            self.error_occurred.emit(f"스캔 시작 실패: {e}")

    def stop_scan(self):
        """스캔 중지"""
        if not self.can_stop_scan:
            self.logger.warning("스캔을 중지할 수 없습니다")
            return
        try:
            if self._state.current_scan_id:
                self.background_task_service.cancel_task(self._state.current_scan_id)
        except Exception as e:
            self.logger.error(f"스캔 중지 실패: {e}")
            self.error_occurred.emit(f"스캔 중지 실패: {e}")

    def clear_results(self):
        """결과 초기화"""
        if not self.can_clear_results:
            self.logger.warning("결과를 초기화할 수 없습니다")
            return
        self._state.has_scanned_files = False
        self._state.has_grouped_files = False
        self._state.has_tmdb_matches = False
        self._state.selected_files.clear()
        self._state.selected_groups.clear()
        self._state.scan_progress = 0
        self._state.organize_progress = 0
        self._state.tmdb_progress = 0
        self._update_capabilities()
        self.state_changed.emit()

    def select_files(self, file_ids: set[str]):
        """파일 선택"""
        self._state.selected_files = set(file_ids)
        self.state_changed.emit()

    def select_groups(self, group_ids: set[str]):
        """그룹 선택"""
        self._state.selected_groups = set(group_ids)
        self.state_changed.emit()
