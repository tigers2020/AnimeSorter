"""
Organize ViewModel - Phase 3.2 뷰모델 분할
파일 정리 기능의 ViewModel 로직을 담당합니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from src.app import (
    ErrorMessageEvent,
    FileDeletedEvent,
    FileMovedEvent,
    IFileOrganizationService,
    IUIUpdateService,
    OrganizationCancelledEvent,
    OrganizationCompletedEvent,
    OrganizationFailedEvent,
    OrganizationProgressEvent,
    OrganizationStartedEvent,
    StatusBarUpdateEvent,
    SuccessMessageEvent,
    TypedEventBus,
    get_event_bus,
    get_service,
)

from .organization_state import OrganizationCapabilities, OrganizationState


class OrganizeViewModel(QObject):
    """파일 정리 ViewModel"""

    state_changed = pyqtSignal()
    capabilities_changed = pyqtSignal()
    progress_changed = pyqtSignal(int)
    operation_changed = pyqtSignal(str)
    file_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    success_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._state = OrganizationState()
        self._capabilities = OrganizationCapabilities()
        self.event_bus: TypedEventBus = get_event_bus()
        self.file_organization_service: IFileOrganizationService = get_service(
            IFileOrganizationService
        )
        self.ui_update_service: IUIUpdateService = get_service(IUIUpdateService)
        self._connect_events()

    def _connect_events(self):
        """이벤트 연결 설정"""
        self.event_bus.subscribe(OrganizationStartedEvent, self._on_organization_started)
        self.event_bus.subscribe(OrganizationProgressEvent, self._on_organization_progress)
        self.event_bus.subscribe(OrganizationCompletedEvent, self._on_organization_completed)
        self.event_bus.subscribe(OrganizationFailedEvent, self._on_organization_failed)
        self.event_bus.subscribe(OrganizationCancelledEvent, self._on_organization_cancelled)
        self.event_bus.subscribe(FileMovedEvent, self._on_file_moved)
        self.event_bus.subscribe(FileDeletedEvent, self._on_file_deleted)
        self.event_bus.subscribe(StatusBarUpdateEvent, self._on_status_bar_update)
        self.event_bus.subscribe(SuccessMessageEvent, self._on_success_message)
        self.event_bus.subscribe(ErrorMessageEvent, self._on_error_message)

    @pyqtProperty(bool, notify=state_changed)
    def is_organizing(self) -> bool:
        return self._state.is_organizing

    @pyqtProperty(str, notify=state_changed)
    def organization_mode(self) -> str:
        return self._state.organization_mode

    @pyqtProperty(int, notify=state_changed)
    def total_files_to_process(self) -> int:
        return self._state.total_files_to_process

    @pyqtProperty(int, notify=state_changed)
    def processed_files_count(self) -> int:
        return self._state.processed_files_count

    @pyqtProperty(int, notify=state_changed)
    def successful_operations(self) -> int:
        return self._state.successful_operations

    @pyqtProperty(int, notify=state_changed)
    def failed_operations(self) -> int:
        return self._state.failed_operations

    @pyqtProperty(int, notify=state_changed)
    def skipped_operations(self) -> int:
        return self._state.skipped_operations

    @pyqtProperty(int, notify=state_changed)
    def organization_progress(self) -> int:
        return self._state.organization_progress

    @pyqtProperty(str, notify=state_changed)
    def current_operation(self) -> str:
        return self._state.current_operation

    @pyqtProperty(str, notify=state_changed)
    def current_file(self) -> str:
        return self._state.current_file

    @pyqtProperty(str, notify=state_changed)
    def last_error(self) -> str:
        return self._state.last_error or ""

    @pyqtProperty(int, notify=state_changed)
    def error_count(self) -> int:
        return self._state.error_count

    @pyqtProperty(int, notify=state_changed)
    def files_moved(self) -> int:
        return self._state.files_moved

    @pyqtProperty(int, notify=state_changed)
    def files_renamed(self) -> int:
        return self._state.files_renamed

    @pyqtProperty(int, notify=state_changed)
    def files_deleted(self) -> int:
        return self._state.files_deleted

    @pyqtProperty(int, notify=state_changed)
    def directories_created(self) -> int:
        return self._state.directories_created

    @pyqtProperty(bool, notify=state_changed)
    def create_directories(self) -> bool:
        return self._state.create_directories

    @pyqtProperty(bool, notify=state_changed)
    def overwrite_existing(self) -> bool:
        return self._state.overwrite_existing

    @pyqtProperty(bool, notify=state_changed)
    def use_hard_links(self) -> bool:
        return self._state.use_hard_links

    @pyqtProperty(bool, notify=state_changed)
    def preserve_timestamps(self) -> bool:
        return self._state.preserve_timestamps

    @pyqtProperty(bool, notify=state_changed)
    def backup_before_organize(self) -> bool:
        return self._state.backup_before_organize

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_start_organization(self) -> bool:
        return self._capabilities.can_start_organization

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_stop_organization(self) -> bool:
        return self._capabilities.can_stop_organization

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_pause_organization(self) -> bool:
        return self._capabilities.can_pause_organization

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_resume_organization(self) -> bool:
        return self._capabilities.can_resume_organization

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_preview_organization(self) -> bool:
        return self._capabilities.can_preview_organization

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_undo_last_operation(self) -> bool:
        return self._capabilities.can_undo_last_operation

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_redo_last_operation(self) -> bool:
        return self._capabilities.can_redo_last_operation

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_clear_organization_results(self) -> bool:
        return self._capabilities.can_clear_organization_results

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_export_organization_log(self) -> bool:
        return self._capabilities.can_export_organization_log

    def _on_organization_started(self, event: OrganizationStartedEvent):
        """정리 시작 이벤트 처리"""
        self._state.is_organizing = True
        self._state.current_organization_id = event.organization_id
        self._state.total_files_to_process = event.total_files
        self._state.processed_files_count = 0
        self._state.organization_progress = 0
        self._state.current_operation = "정리 시작"
        self._state.current_file = ""
        self._update_capabilities()
        self.state_changed.emit()

    def _on_organization_progress(self, event: OrganizationProgressEvent):
        """정리 진행률 이벤트 처리"""
        self._state.processed_files_count = event.processed_files
        self._state.organization_progress = event.progress
        self._state.current_operation = event.operation
        self._state.current_file = event.current_file
        self.progress_changed.emit(event.progress)
        self.operation_changed.emit(event.operation)
        self.file_changed.emit(event.current_file)

    def _on_organization_completed(self, event: OrganizationCompletedEvent):
        """정리 완료 이벤트 처리"""
        self._state.is_organizing = False
        self._state.current_organization_id = None
        self._state.organization_progress = 100
        self._state.current_operation = "정리 완료"
        self._state.current_file = ""
        self._state.successful_operations = event.successful_operations
        self._state.failed_operations = event.failed_operations
        self._state.skipped_operations = event.skipped_operations
        self._update_capabilities()
        self.state_changed.emit()
        self.success_occurred.emit("파일 정리가 완료되었습니다")

    def _on_organization_failed(self, event: OrganizationFailedEvent):
        """정리 실패 이벤트 처리"""
        self._state.is_organizing = False
        self._state.current_organization_id = None
        self._state.last_error = event.error_message
        self._state.error_count += 1
        self._update_capabilities()
        self.state_changed.emit()
        self.error_occurred.emit(event.error_message)

    def _on_organization_cancelled(self, event: OrganizationCancelledEvent):
        """정리 취소 이벤트 처리"""
        self._state.is_organizing = False
        self._state.current_organization_id = None
        self._state.current_operation = "정리 취소됨"
        self._update_capabilities()
        self.state_changed.emit()

    def _on_file_moved(self, event: FileMovedEvent):
        """파일 이동 이벤트 처리"""
        self._state.files_moved += 1
        self.state_changed.emit()

    def _on_file_deleted(self, event: FileDeletedEvent):
        """파일 삭제 이벤트 처리"""
        self._state.files_deleted += 1
        self.state_changed.emit()

    def _on_status_bar_update(self, event: StatusBarUpdateEvent):
        """상태바 업데이트 이벤트 처리"""

    def _on_success_message(self, event: SuccessMessageEvent):
        """성공 메시지 이벤트 처리"""
        self.success_occurred.emit(event.message)

    def _on_error_message(self, event: ErrorMessageEvent):
        """오류 메시지 이벤트 처리"""
        self._state.last_error = event.message
        self._state.error_count += 1
        self.state_changed.emit()
        self.error_occurred.emit(event.message)

    def _update_capabilities(self):
        """UI 기능 상태 업데이트"""
        old_capabilities = self._capabilities
        if self._state.is_organizing:
            self._capabilities = OrganizationCapabilities.organizing()
        else:
            self._capabilities = OrganizationCapabilities()
        if old_capabilities != self._capabilities:
            self.capabilities_changed.emit()

    def start_organization(self, mode: str = "simulation"):
        """정리 시작"""
        if not self.can_start_organization:
            self.logger.warning("정리를 시작할 수 없습니다")
            return
        try:
            self._state.organization_mode = mode
            self.file_organization_service.start_organization(mode)
        except Exception as e:
            self.logger.error(f"정리 시작 실패: {e}")
            self.error_occurred.emit(f"정리 시작 실패: {e}")

    def stop_organization(self):
        """정리 중지"""
        if not self.can_stop_organization:
            self.logger.warning("정리를 중지할 수 없습니다")
            return
        try:
            if self._state.current_organization_id:
                self.file_organization_service.stop_organization(
                    self._state.current_organization_id
                )
        except Exception as e:
            self.logger.error(f"정리 중지 실패: {e}")
            self.error_occurred.emit(f"정리 중지 실패: {e}")

    def pause_organization(self):
        """정리 일시정지"""
        if not self.can_pause_organization:
            self.logger.warning("정리를 일시정지할 수 없습니다")
            return
        try:
            if self._state.current_organization_id:
                self.file_organization_service.pause_organization(
                    self._state.current_organization_id
                )
        except Exception as e:
            self.logger.error(f"정리 일시정지 실패: {e}")
            self.error_occurred.emit(f"정리 일시정지 실패: {e}")

    def resume_organization(self):
        """정리 재개"""
        if not self.can_resume_organization:
            self.logger.warning("정리를 재개할 수 없습니다")
            return
        try:
            if self._state.current_organization_id:
                self.file_organization_service.resume_organization(
                    self._state.current_organization_id
                )
        except Exception as e:
            self.logger.error(f"정리 재개 실패: {e}")
            self.error_occurred.emit(f"정리 재개 실패: {e}")

    def preview_organization(self):
        """정리 미리보기"""
        if not self.can_preview_organization:
            self.logger.warning("정리 미리보기를 할 수 없습니다")
            return
        try:
            self.file_organization_service.preview_organization()
        except Exception as e:
            self.logger.error(f"정리 미리보기 실패: {e}")
            self.error_occurred.emit(f"정리 미리보기 실패: {e}")

    def clear_results(self):
        """정리 결과 초기화"""
        if not self.can_clear_organization_results:
            self.logger.warning("정리 결과를 초기화할 수 없습니다")
            return
        self._state.total_files_to_process = 0
        self._state.processed_files_count = 0
        self._state.successful_operations = 0
        self._state.failed_operations = 0
        self._state.skipped_operations = 0
        self._state.organization_progress = 0
        self._state.current_operation = ""
        self._state.current_file = ""
        self._state.last_error = None
        self._state.error_count = 0
        self._state.files_moved = 0
        self._state.files_renamed = 0
        self._state.files_deleted = 0
        self._state.directories_created = 0
        self._update_capabilities()
        self.state_changed.emit()

    def update_settings(self, **kwargs):
        """정리 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        self.state_changed.emit()
