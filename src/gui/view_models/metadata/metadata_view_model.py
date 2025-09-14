"""
Metadata ViewModel - Phase 3.5 뷰모델 분할
메타데이터 관리의 ViewModel 로직을 담당합니다.
"""

import logging

logger = logging.getLogger(__name__)
from typing import Any

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from src.app import (
    ErrorMessageEvent,
    IMediaDataService,
    IUIUpdateService,
    StatusBarUpdateEvent,
    SuccessMessageEvent,
    TypedEventBus,
    get_event_bus,
    get_service,
)

from .metadata_state import MetadataCapabilities, MetadataState


class MetadataViewModel(QObject):
    """메타데이터 관리 ViewModel"""

    state_changed = pyqtSignal()
    capabilities_changed = pyqtSignal()
    search_progress_changed = pyqtSignal(int)
    processing_progress_changed = pyqtSignal(int)
    operation_changed = pyqtSignal(str)
    file_changed = pyqtSignal(str)
    metadata_updated = pyqtSignal()
    error_occurred = pyqtSignal(str)
    success_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._state = MetadataState()
        self._capabilities = MetadataCapabilities()
        self.event_bus: TypedEventBus = get_event_bus()
        self.media_data_service: IMediaDataService = get_service(IMediaDataService)
        self.ui_update_service: IUIUpdateService = get_service(IUIUpdateService)
        self._connect_events()

    def _connect_events(self):
        """이벤트 연결 설정"""
        self.event_bus.subscribe(StatusBarUpdateEvent, self._on_status_bar_update)
        self.event_bus.subscribe(SuccessMessageEvent, self._on_success_message)
        self.event_bus.subscribe(ErrorMessageEvent, self._on_error_message)

    @pyqtProperty(bool, notify=state_changed)
    def is_searching_metadata(self) -> bool:
        return self._state.is_searching_metadata

    @pyqtProperty(bool, notify=state_changed)
    def is_processing_metadata(self) -> bool:
        return self._state.is_processing_metadata

    @pyqtProperty(str, notify=state_changed)
    def search_query(self) -> str:
        return self._state.search_query

    @pyqtProperty(int, notify=state_changed)
    def total_files_with_metadata(self) -> int:
        return self._state.total_files_with_metadata

    @pyqtProperty(int, notify=state_changed)
    def files_without_metadata(self) -> int:
        return self._state.files_without_metadata

    @pyqtProperty(float, notify=state_changed)
    def metadata_quality_score(self) -> float:
        return self._state.metadata_quality_score

    @pyqtProperty(int, notify=state_changed)
    def metadata_search_progress(self) -> int:
        return self._state.metadata_search_progress

    @pyqtProperty(int, notify=state_changed)
    def metadata_processing_progress(self) -> int:
        return self._state.metadata_processing_progress

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

    @pyqtProperty(bool, notify=state_changed)
    def tmdb_enabled(self) -> bool:
        return self._state.tmdb_enabled

    @pyqtProperty(bool, notify=state_changed)
    def anidb_enabled(self) -> bool:
        return self._state.anidb_enabled

    @pyqtProperty(bool, notify=state_changed)
    def myanimelist_enabled(self) -> bool:
        return self._state.myanimelist_enabled

    @pyqtProperty(int, notify=state_changed)
    def successful_searches(self) -> int:
        return self._state.successful_searches

    @pyqtProperty(int, notify=state_changed)
    def failed_searches(self) -> int:
        return self._state.failed_searches

    @pyqtProperty(int, notify=state_changed)
    def partial_matches(self) -> int:
        return self._state.partial_matches

    @pyqtProperty(int, notify=state_changed)
    def exact_matches(self) -> int:
        return self._state.exact_matches

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_start_metadata_search(self) -> bool:
        return self._capabilities.can_start_metadata_search

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_stop_metadata_search(self) -> bool:
        return self._capabilities.can_stop_metadata_search

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_start_metadata_processing(self) -> bool:
        return self._capabilities.can_start_metadata_processing

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_stop_metadata_processing(self) -> bool:
        return self._capabilities.can_stop_metadata_processing

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_edit_metadata(self) -> bool:
        return self._capabilities.can_edit_metadata

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_export_metadata(self) -> bool:
        return self._capabilities.can_export_metadata

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_import_metadata(self) -> bool:
        return self._capabilities.can_import_metadata

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_validate_metadata(self) -> bool:
        return self._capabilities.can_validate_metadata

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_bulk_edit_metadata(self) -> bool:
        return self._capabilities.can_bulk_edit_metadata

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
        if self._state.is_searching_metadata:
            self._capabilities = MetadataCapabilities.searching()
        elif self._state.is_processing_metadata:
            self._capabilities = MetadataCapabilities.processing()
        elif self._state.total_files_with_metadata > 0:
            self._capabilities = MetadataCapabilities.has_metadata()
        else:
            self._capabilities = MetadataCapabilities()
        if old_capabilities != self._capabilities:
            self.capabilities_changed.emit()

    def start_metadata_search(self, query: str = ""):
        """메타데이터 검색 시작"""
        if not self.can_start_metadata_search:
            self.logger.warning("메타데이터 검색을 시작할 수 없습니다")
            return
        try:
            self.media_data_service.start_metadata_search(query)
        except Exception as e:
            self.logger.error(f"메타데이터 검색 시작 실패: {e}")
            self.error_occurred.emit(f"메타데이터 검색 시작 실패: {e}")

    def stop_metadata_search(self):
        """메타데이터 검색 중지"""
        if not self.can_stop_metadata_search:
            self.logger.warning("메타데이터 검색을 중지할 수 없습니다")
            return
        try:
            if self._state.current_search_id:
                self.media_data_service.stop_metadata_search(self._state.current_search_id)
        except Exception as e:
            self.logger.error(f"메타데이터 검색 중지 실패: {e}")
            self.error_occurred.emit(f"메타데이터 검색 중지 실패: {e}")

    def start_metadata_processing(self):
        """메타데이터 처리 시작"""
        if not self.can_start_metadata_processing:
            self.logger.warning("메타데이터 처리를 시작할 수 없습니다")
            return
        try:
            self.media_data_service.start_metadata_processing()
        except Exception as e:
            self.logger.error(f"메타데이터 처리 시작 실패: {e}")
            self.error_occurred.emit(f"메타데이터 처리 시작 실패: {e}")

    def stop_metadata_processing(self):
        """메타데이터 처리 중지"""
        if not self.can_stop_metadata_processing:
            self.logger.warning("메타데이터 처리를 중지할 수 없습니다")
            return
        try:
            if self._state.current_processing_id:
                self.media_data_service.stop_metadata_processing(self._state.current_processing_id)
        except Exception as e:
            self.logger.error(f"메타데이터 처리 중지 실패: {e}")
            self.error_occurred.emit(f"메타데이터 처리 중지 실패: {e}")

    def update_metadata_source_settings(self, **kwargs):
        """메타데이터 소스 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        self.state_changed.emit()

    def get_metadata_quality_report(self) -> dict[str, Any]:
        """메타데이터 품질 보고서 가져오기"""
        try:
            return self.media_data_service.get_metadata_quality_report()
        except Exception as e:
            self.logger.error(f"메타데이터 품질 보고서 가져오기 실패: {e}")
            return {}

    def export_metadata(self, file_path: str, format: str = "json"):
        """메타데이터 내보내기"""
        if not self.can_export_metadata:
            self.logger.warning("메타데이터를 내보낼 수 없습니다")
            return
        try:
            self.media_data_service.export_metadata(file_path, format)
        except Exception as e:
            self.logger.error(f"메타데이터 내보내기 실패: {e}")
            self.error_occurred.emit(f"메타데이터 내보내기 실패: {e}")

    def import_metadata(self, file_path: str, format: str = "json"):
        """메타데이터 가져오기"""
        if not self.can_import_metadata:
            self.logger.warning("메타데이터를 가져올 수 없습니다")
            return
        try:
            self.media_data_service.import_metadata(file_path, format)
        except Exception as e:
            self.logger.error(f"메타데이터 가져오기 실패: {e}")
            self.error_occurred.emit(f"메타데이터 가져오기 실패: {e}")

    def validate_metadata(self) -> dict[str, Any]:
        """메타데이터 유효성 검사"""
        if not self.can_validate_metadata:
            self.logger.warning("메타데이터 유효성을 검사할 수 없습니다")
            return {}
        try:
            return self.media_data_service.validate_metadata()
        except Exception as e:
            self.logger.error(f"메타데이터 유효성 검사 실패: {e}")
            return {}
