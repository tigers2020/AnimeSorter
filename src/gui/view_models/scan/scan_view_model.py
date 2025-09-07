"""
Scan ViewModel - Phase 3.6 뷰모델 분할
파일 스캔 기능의 ViewModel 로직을 담당합니다.
"""

import logging
from typing import Any

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from src.app import (ErrorMessageEvent, FileCountUpdateEvent, FilesScannedEvent,
                     IFileScanService, IUIUpdateService, ScanCompletedEvent,
                     ScanFailedEvent, ScanProgressEvent, ScanStartedEvent,
                     ScanStoppedEvent, StatusBarUpdateEvent, SuccessMessageEvent,
                     TypedEventBus, get_event_bus, get_service)

from src.scan_state import ScanCapabilities, ScanState


class ScanViewModel(QObject):
    """파일 스캔 ViewModel"""

    # 시그널
    state_changed = pyqtSignal()
    capabilities_changed = pyqtSignal()
    progress_changed = pyqtSignal(int)
    operation_changed = pyqtSignal(str)
    file_changed = pyqtSignal(str)
    directory_changed = pyqtSignal(str)
    scan_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    success_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # 상태 초기화
        self._state = ScanState()
        self._capabilities = ScanCapabilities()

        # 서비스 및 이벤트 버스
        self.event_bus: TypedEventBus = get_event_bus()
        self.file_scan_service: IFileScanService = get_service(IFileScanService)
        self.ui_update_service: IUIUpdateService = get_service(IUIUpdateService)

        # 이벤트 연결
        self._connect_events()

    def _connect_events(self):
        """이벤트 연결 설정"""
        # 스캔 관련 이벤트
        self.event_bus.subscribe(ScanStartedEvent, self._on_scan_started)
        self.event_bus.subscribe(ScanProgressEvent, self._on_scan_progress)
        self.event_bus.subscribe(ScanCompletedEvent, self._on_scan_completed)
        self.event_bus.subscribe(ScanFailedEvent, self._on_scan_failed)
        self.event_bus.subscribe(ScanStoppedEvent, self._on_scan_stopped)

        # 파일 관련 이벤트
        self.event_bus.subscribe(FilesScannedEvent, self._on_files_scanned)
        self.event_bus.subscribe(FileCountUpdateEvent, self._on_file_count_updated)

        # UI 이벤트
        self.event_bus.subscribe(StatusBarUpdateEvent, self._on_status_bar_update)
        self.event_bus.subscribe(SuccessMessageEvent, self._on_success_message)
        self.event_bus.subscribe(ErrorMessageEvent, self._on_error_message)

    # 상태 속성들
    @pyqtProperty(bool, notify=state_changed)
    def is_scanning(self) -> bool:
        return self._state.is_scanning

    @pyqtProperty(str, notify=state_changed)
    def scanned_directory(self) -> str:
        return self._state.scanned_directory

    @pyqtProperty(bool, notify=state_changed)
    def recursive_scan(self) -> bool:
        return self._state.recursive_scan

    @pyqtProperty(list, notify=state_changed)
    def supported_extensions(self) -> list:
        return list(self._state.supported_extensions)

    @pyqtProperty(int, notify=state_changed)
    def min_file_size(self) -> int:
        return self._state.min_file_size

    @pyqtProperty(int, notify=state_changed)
    def max_file_size(self) -> int:
        return self._state.max_file_size

    @pyqtProperty(bool, notify=state_changed)
    def include_hidden_files(self) -> bool:
        return self._state.include_hidden_files

    @pyqtProperty(int, notify=state_changed)
    def total_files_found(self) -> int:
        return self._state.total_files_found

    @pyqtProperty(int, notify=state_changed)
    def total_directories_scanned(self) -> int:
        return self._state.total_directories_scanned

    @pyqtProperty(dict, notify=state_changed)
    def files_by_extension(self) -> dict:
        return self._state.files_by_extension

    @pyqtProperty(dict, notify=state_changed)
    def files_by_size_range(self) -> dict:
        return self._state.files_by_size_range

    @pyqtProperty(int, notify=state_changed)
    def scan_progress(self) -> int:
        return self._state.scan_progress

    @pyqtProperty(str, notify=state_changed)
    def current_operation(self) -> str:
        return self._state.current_operation

    @pyqtProperty(str, notify=state_changed)
    def current_file(self) -> str:
        return self._state.current_file

    @pyqtProperty(str, notify=state_changed)
    def current_directory(self) -> str:
        return self._state.current_directory

    @pyqtProperty(str, notify=state_changed)
    def last_error(self) -> str:
        return self._state.last_error or ""

    @pyqtProperty(int, notify=state_changed)
    def error_count(self) -> int:
        return self._state.error_count

    @pyqtProperty(int, notify=state_changed)
    def skipped_files(self) -> int:
        return self._state.skipped_files

    @pyqtProperty(int, notify=state_changed)
    def access_denied_files(self) -> int:
        return self._state.access_denied_files

    @pyqtProperty(int, notify=state_changed)
    def total_size_scanned(self) -> int:
        return self._state.total_size_scanned

    @pyqtProperty(float, notify=state_changed)
    def average_file_size(self) -> float:
        return self._state.average_file_size

    @pyqtProperty(int, notify=state_changed)
    def largest_file_size(self) -> int:
        return self._state.largest_file_size

    @pyqtProperty(int, notify=state_changed)
    def smallest_file_size(self) -> int:
        return self._state.smallest_file_size

    # UI 기능 속성들
    @pyqtProperty(bool, notify=capabilities_changed)
    def can_start_scan(self) -> bool:
        return self._capabilities.can_start_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_stop_scan(self) -> bool:
        return self._capabilities.can_stop_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_pause_scan(self) -> bool:
        return self._capabilities.can_pause_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_resume_scan(self) -> bool:
        return self._capabilities.can_resume_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_clear_scan_results(self) -> bool:
        return self._capabilities.can_clear_scan_results

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_export_scan_results(self) -> bool:
        return self._capabilities.can_export_scan_results

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_save_scan_configuration(self) -> bool:
        return self._capabilities.can_save_scan_configuration

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_load_scan_configuration(self) -> bool:
        return self._capabilities.can_load_scan_configuration

    # 이벤트 핸들러들
    def _on_scan_started(self, event: ScanStartedEvent):
        """스캔 시작 이벤트 처리"""
        self._state.is_scanning = True
        self._state.current_scan_id = event.scan_id
        self._state.scanned_directory = str(event.directory_path)
        self._state.scan_progress = 0
        self._state.current_operation = "스캔 시작"
        self._state.current_file = ""
        self._state.current_directory = ""

        self._update_capabilities()
        self.state_changed.emit()

    def _on_scan_progress(self, event: ScanProgressEvent):
        """스캔 진행률 이벤트 처리"""
        self._state.scan_progress = event.progress
        self._state.current_operation = event.operation
        self._state.current_file = event.current_file
        self._state.current_directory = event.current_directory

        self.progress_changed.emit(event.progress)
        self.operation_changed.emit(event.operation)
        self.file_changed.emit(event.current_file)
        self.directory_changed.emit(event.current_directory)

    def _on_scan_completed(self, event: ScanCompletedEvent):
        """스캔 완료 이벤트 처리"""
        self._state.is_scanning = False
        self._state.current_scan_id = None
        self._state.scan_progress = 100
        self._state.current_operation = "스캔 완료"
        self._state.current_file = ""
        self._state.current_directory = ""

        # 결과 통계 업데이트
        self._state.total_files_found = event.total_files
        self._state.total_directories_scanned = event.total_directories
        self._state.total_size_scanned = event.total_size
        self._state.average_file_size = event.average_file_size
        self._state.largest_file_size = event.largest_file_size
        self._state.smallest_file_size = event.smallest_file_size

        self._update_capabilities()
        self.state_changed.emit()
        self.scan_completed.emit()
        self.success_occurred.emit("파일 스캔이 완료되었습니다")

    def _on_scan_failed(self, event: ScanFailedEvent):
        """스캔 실패 이벤트 처리"""
        self._state.is_scanning = False
        self._state.current_scan_id = None
        self._state.last_error = event.error_message
        self._state.error_count += 1

        self._update_capabilities()
        self.state_changed.emit()
        self.error_occurred.emit(event.error_message)

    def _on_scan_stopped(self, event: ScanStoppedEvent):
        """스캔 중지 이벤트 처리"""
        self._state.is_scanning = False
        self._state.current_scan_id = None
        self._state.current_operation = "스캔 중지됨"

        self._update_capabilities()
        self.state_changed.emit()

    def _on_files_scanned(self, event: FilesScannedEvent):
        """파일 스캔 완료 이벤트 처리"""
        # 파일 확장자별 통계 업데이트
        for file_info in event.files:
            extension = file_info.extension.lower()
            if extension not in self._state.files_by_extension:
                self._state.files_by_extension[extension] = 0
            self._state.files_by_extension[extension] += 1

            # 파일 크기 범위별 통계 업데이트
            size_range = self._get_size_range(file_info.size)
            if size_range not in self._state.files_by_size_range:
                self._state.files_by_size_range[size_range] = 0
            self._state.files_by_size_range[size_range] += 1

        self.state_changed.emit()

    def _on_file_count_updated(self, event: FileCountUpdateEvent):
        """파일 수 업데이트 이벤트 처리"""
        self._state.total_files_found = event.total_files
        self.state_changed.emit()

    def _on_status_bar_update(self, event: StatusBarUpdateEvent):
        """상태바 업데이트 이벤트 처리"""
        # 상태바 메시지는 View에서 직접 처리

    def _on_success_message(self, event: SuccessMessageEvent):
        """성공 메시지 이벤트 처리"""
        self.success_occurred.emit(event.message)

    def _on_error_message(self, event: ErrorMessageEvent):
        """오류 메시지 이벤트 처리"""
        self._state.last_error = event.message
        self._state.error_count += 1
        self.state_changed.emit()
        self.error_occurred.emit(event.message)

    def _get_size_range(self, file_size: int) -> str:
        """파일 크기를 범위로 분류"""
        if file_size < 1024 * 1024:  # 1MB 미만
            return "< 1MB"
        if file_size < 100 * 1024 * 1024:  # 100MB 미만
            return "1MB - 100MB"
        if file_size < 1024 * 1024 * 1024:  # 1GB 미만
            return "100MB - 1GB"
        if file_size < 10 * 1024 * 1024 * 1024:  # 10GB 미만
            return "1GB - 10GB"
        return "> 10GB"

    def _update_capabilities(self):
        """UI 기능 상태 업데이트"""
        old_capabilities = self._capabilities

        if self._state.is_scanning:
            self._capabilities = ScanCapabilities.scanning()
        else:
            self._capabilities = ScanCapabilities()

        if old_capabilities != self._capabilities:
            self.capabilities_changed.emit()

    # 공개 메서드들
    def start_scan(
        self,
        directory_path: str,
        recursive: bool = True,
        extensions: set[str] = None,
        min_size: int = None,
        max_size: int = None,
        include_hidden: bool = False,
    ):
        """스캔 시작"""
        if not self.can_start_scan:
            self.logger.warning("스캔을 시작할 수 없습니다")
            return

        try:
            # 스캔 설정 업데이트
            if recursive is not None:
                self._state.recursive_scan = recursive
            if extensions is not None:
                self._state.supported_extensions = extensions
            if min_size is not None:
                self._state.min_file_size = min_size
            if max_size is not None:
                self._state.max_file_size = max_size
            if include_hidden is not None:
                self._state.include_hidden_files = include_hidden

            self.file_scan_service.scan_directory(
                directory_path=directory_path,
                recursive=self._state.recursive_scan,
                extensions=self._state.supported_extensions,
                min_file_size=self._state.min_file_size,
                max_file_size=self._state.max_file_size,
            )

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
                self.file_scan_service.stop_scan(self._state.current_scan_id)
        except Exception as e:
            self.logger.error(f"스캔 중지 실패: {e}")
            self.error_occurred.emit(f"스캔 중지 실패: {e}")

    def pause_scan(self):
        """스캔 일시정지"""
        if not self.can_pause_scan:
            self.logger.warning("스캔을 일시정지할 수 없습니다")
            return

        try:
            if self._state.current_scan_id:
                self.file_scan_service.pause_scan(self._state.current_scan_id)
        except Exception as e:
            self.logger.error(f"스캔 일시정지 실패: {e}")
            self.error_occurred.emit(f"스캔 일시정지 실패: {e}")

    def resume_scan(self):
        """스캔 재개"""
        if not self.can_resume_scan:
            self.logger.warning("스캔을 재개할 수 없습니다")
            return

        try:
            if self._state.current_scan_id:
                self.file_scan_service.resume_scan(self._state.current_scan_id)
        except Exception as e:
            self.logger.error(f"스캔 재개 실패: {e}")
            self.error_occurred.emit(f"스캔 재개 실패: {e}")

    def clear_results(self):
        """스캔 결과 초기화"""
        if not self.can_clear_scan_results:
            self.logger.warning("스캔 결과를 초기화할 수 없습니다")
            return

        self._state.total_files_found = 0
        self._state.total_directories_scanned = 0
        self._state.files_by_extension.clear()
        self._state.files_by_size_range.clear()
        self._state.scan_progress = 0
        self._state.current_operation = ""
        self._state.current_file = ""
        self._state.current_directory = ""
        self._state.last_error = None
        self._state.error_count = 0
        self._state.skipped_files = 0
        self._state.access_denied_files = 0
        self._state.total_size_scanned = 0
        self._state.average_file_size = 0.0
        self._state.largest_file_size = 0
        self._state.smallest_file_size = 0

        self._update_capabilities()
        self.state_changed.emit()

    def export_results(self, file_path: str, format: str = "json"):
        """스캔 결과 내보내기"""
        if not self.can_export_scan_results:
            self.logger.warning("스캔 결과를 내보낼 수 없습니다")
            return

        try:
            # 스캔 결과를 파일로 내보내기
            results = {
                "scanned_directory": self._state.scanned_directory,
                "total_files_found": self._state.total_files_found,
                "total_directories_scanned": self._state.total_directories_scanned,
                "files_by_extension": self._state.files_by_extension,
                "files_by_size_range": self._state.files_by_size_range,
                "total_size_scanned": self._state.total_size_scanned,
                "average_file_size": self._state.average_file_size,
                "largest_file_size": self._state.largest_file_size,
                "smallest_file_size": self._state.smallest_file_size,
                "scan_settings": {
                    "recursive_scan": self._state.recursive_scan,
                    "supported_extensions": list(self._state.supported_extensions),
                    "min_file_size": self._state.min_file_size,
                    "max_file_size": self._state.max_file_size,
                    "include_hidden_files": self._state.include_hidden_files,
                },
            }

            # 파일로 저장 (간단한 구현)
            import json

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            self.success_occurred.emit(f"스캔 결과가 내보내졌습니다: {file_path}")

        except Exception as e:
            self.logger.error(f"스캔 결과 내보내기 실패: {e}")
            self.error_occurred.emit(f"스캔 결과 내보내기 실패: {e}")

    def update_scan_settings(self, **kwargs):
        """스캔 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)

        self.state_changed.emit()

    def get_scan_statistics(self) -> dict[str, Any]:
        """스캔 통계 가져오기"""
        return {
            "total_files_found": self._state.total_files_found,
            "total_directories_scanned": self._state.total_directories_scanned,
            "total_size_scanned": self._state.total_size_scanned,
            "average_file_size": self._state.average_file_size,
            "largest_file_size": self._state.largest_file_size,
            "smallest_file_size": self._state.smallest_file_size,
            "files_by_extension": self._state.files_by_extension,
            "files_by_size_range": self._state.files_by_size_range,
            "error_count": self._state.error_count,
            "skipped_files": self._state.skipped_files,
            "access_denied_files": self._state.access_denied_files,
        }
