"""
ScanViewModel - 스캔 기능에 특화된 ViewModel

Phase 2 MVVM 아키텍처의 일부로, 파일 스캔 기능을 담당합니다.
"""

import logging
from dataclasses import dataclass, field
from uuid import UUID

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from app import (
    ErrorMessageEvent,
    FileCountUpdateEvent,
    # 이벤트
    FilesScannedEvent,
    # 서비스
    IFileScanService,
    IUIUpdateService,
    # 도메인 모델
    ScanStatus,
    # UI 이벤트
    StatusBarUpdateEvent,
    SuccessMessageEvent,
    TaskCancelledEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskProgressEvent,
    TaskStartedEvent,
    # 인프라
    TypedEventBus,
    get_event_bus,
    get_service,
)


@dataclass
class ScanState:
    """스캔 상태 정보"""

    # 스캔 진행 상태
    is_scanning: bool = False
    current_scan_id: UUID | None = None
    scanned_directory: str | None = None

    # 스캔 결과
    total_files_found: int = 0
    scanned_files_count: int = 0
    valid_media_files: int = 0
    invalid_files: int = 0

    # 진행률
    scan_progress: int = 0
    current_step: str = ""

    # 스캔 설정
    include_subdirectories: bool = True
    file_extensions: set[str] = field(
        default_factory=lambda: {
            ".mp4",
            ".mkv",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".3gp",
            ".ogv",
            ".ts",
            ".mts",
            ".m2ts",
        }
    )
    max_file_size_mb: int = 10000  # 10GB
    scan_hidden_files: bool = False

    # 오류 정보
    last_error: str | None = None
    error_count: int = 0


@dataclass
class ScanCapabilities:
    """스캔 관련 UI 기능들"""

    can_start_scan: bool = True
    can_stop_scan: bool = False
    can_pause_scan: bool = False
    can_resume_scan: bool = False
    can_clear_scan_results: bool = False
    can_export_scan_results: bool = False
    can_filter_scan_results: bool = False

    @classmethod
    def scanning(cls) -> "ScanCapabilities":
        """스캔 중일 때의 기능 상태"""
        return cls(
            can_start_scan=False,
            can_stop_scan=True,
            can_pause_scan=True,
            can_resume_scan=False,
            can_clear_scan_results=False,
            can_export_scan_results=False,
            can_filter_scan_results=False,
        )

    @classmethod
    def paused(cls) -> "ScanCapabilities":
        """스캔 일시정지 상태의 기능"""
        return cls(
            can_start_scan=False,
            can_stop_scan=True,
            can_pause_scan=False,
            can_resume_scan=True,
            can_clear_scan_results=False,
            can_export_scan_results=False,
            can_filter_scan_results=False,
        )

    @classmethod
    def completed(cls) -> "ScanCapabilities":
        """스캔 완료 상태의 기능"""
        return cls(
            can_start_scan=True,
            can_stop_scan=False,
            can_pause_scan=False,
            can_resume_scan=False,
            can_clear_scan_results=True,
            can_export_scan_results=True,
            can_filter_scan_results=True,
        )

    @classmethod
    def error(cls) -> "ScanCapabilities":
        """스캔 오류 상태의 기능"""
        return cls(
            can_start_scan=True,
            can_stop_scan=False,
            can_pause_scan=False,
            can_resume_scan=False,
            can_clear_scan_results=True,
            can_export_scan_results=False,
            can_filter_scan_results=False,
        )


class ScanViewModel(QObject):
    """스캔 기능 전용 ViewModel"""

    # 시그널 정의
    state_changed = pyqtSignal()
    capabilities_changed = pyqtSignal()
    scan_progress_changed = pyqtSignal(int)
    scan_status_changed = pyqtSignal(str)
    files_count_changed = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # 로깅 설정
        self.logger = logging.getLogger(__name__)

        # 상태 초기화
        self._scan_state = ScanState()
        self._scan_capabilities = ScanCapabilities()

        # 서비스 연결
        self._event_bus: TypedEventBus | None = None
        self._file_scan_service: IFileScanService | None = None
        self._ui_update_service: IUIUpdateService | None = None

        # 초기화
        self._setup_services()
        self._setup_event_subscriptions()

        self.logger.info("ScanViewModel 초기화 완료")

    def _setup_services(self):
        """필요한 서비스들을 설정"""
        try:
            self._event_bus = get_event_bus()
            self._file_scan_service = get_service(IFileScanService)
            self._ui_update_service = get_service(IUIUpdateService)

            self.logger.info("ScanViewModel 서비스 연결 완료")
        except Exception as e:
            self.logger.error(f"ScanViewModel 서비스 연결 실패: {e}")

    def _setup_event_subscriptions(self):
        """이벤트 구독 설정"""
        if not self._event_bus:
            return

        try:
            # 스캔 관련 이벤트 구독
            self._event_bus.subscribe(FilesScannedEvent, self._on_files_scanned, weak_ref=False)
            self._event_bus.subscribe(TaskProgressEvent, self._on_task_progress, weak_ref=False)
            self._event_bus.subscribe(TaskStartedEvent, self._on_task_started, weak_ref=False)
            self._event_bus.subscribe(TaskCompletedEvent, self._on_task_completed, weak_ref=False)
            self._event_bus.subscribe(TaskFailedEvent, self._on_task_failed, weak_ref=False)
            self._event_bus.subscribe(TaskCancelledEvent, self._on_task_cancelled, weak_ref=False)

            self.logger.info("ScanViewModel 이벤트 구독 설정 완료")
        except Exception as e:
            self.logger.error(f"ScanViewModel 이벤트 구독 설정 실패: {e}")

    # 스캔 상태 프로퍼티들
    @pyqtProperty(bool, notify=state_changed)
    def is_scanning(self) -> bool:
        """스캔 중인지 여부"""
        return self._scan_state.is_scanning

    @pyqtProperty(str, notify=state_changed)
    def scanned_directory(self) -> str:
        """현재 스캔 중인 디렉토리"""
        return self._scan_state.scanned_directory or ""

    @pyqtProperty(int, notify=state_changed)
    def total_files_found(self) -> int:
        """발견된 총 파일 수"""
        return self._scan_state.total_files_found

    @pyqtProperty(int, notify=state_changed)
    def valid_media_files(self) -> int:
        """유효한 미디어 파일 수"""
        return self._scan_state.valid_media_files

    @pyqtProperty(int, notify=state_changed)
    def scan_progress(self) -> int:
        """스캔 진행률 (0-100)"""
        return self._scan_state.scan_progress

    @pyqtProperty(str, notify=state_changed)
    def current_step(self) -> str:
        """현재 스캔 단계"""
        return self._scan_state.current_step

    @pyqtProperty(str, notify=state_changed)
    def last_error(self) -> str:
        """마지막 오류 메시지"""
        return self._scan_state.last_error or ""

    # 스캔 기능 프로퍼티들
    @pyqtProperty(bool, notify=capabilities_changed)
    def can_start_scan(self) -> bool:
        """스캔 시작 가능 여부"""
        return self._scan_capabilities.can_start_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_stop_scan(self) -> bool:
        """스캔 중지 가능 여부"""
        return self._scan_capabilities.can_stop_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_pause_scan(self) -> bool:
        """스캔 일시정지 가능 여부"""
        return self._scan_capabilities.can_pause_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_resume_scan(self) -> bool:
        """스캔 재개 가능 여부"""
        return self._scan_capabilities.can_resume_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_clear_scan_results(self) -> bool:
        """스캔 결과 초기화 가능 여부"""
        return self._scan_capabilities.can_clear_scan_results

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_export_scan_results(self) -> bool:
        """스캔 결과 내보내기 가능 여부"""
        return self._scan_capabilities.can_export_scan_results

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_filter_scan_results(self) -> bool:
        """스캔 결과 필터링 가능 여부"""
        return self._scan_capabilities.can_filter_scan_results

    # 스캔 설정 프로퍼티들
    @pyqtProperty(bool, notify=state_changed)
    def include_subdirectories(self) -> bool:
        """하위 디렉토리 포함 여부"""
        return self._scan_state.include_subdirectories

    @include_subdirectories.setter
    def include_subdirectories(self, value: bool):
        """하위 디렉토리 포함 여부 설정"""
        if self._scan_state.include_subdirectories != value:
            self._scan_state.include_subdirectories = value
            self.state_changed.emit()

    @pyqtProperty(bool, notify=state_changed)
    def scan_hidden_files(self) -> bool:
        """숨김 파일 스캔 여부"""
        return self._scan_state.scan_hidden_files

    @scan_hidden_files.setter
    def scan_hidden_files(self, value: bool):
        """숨김 파일 스캔 여부 설정"""
        if self._scan_state.scan_hidden_files != value:
            self._scan_state.scan_hidden_files = value
            self.state_changed.emit()

    @pyqtProperty(int, notify=state_changed)
    def max_file_size_mb(self) -> int:
        """최대 파일 크기 (MB)"""
        return self._scan_state.max_file_size_mb

    @max_file_size_mb.setter
    def max_file_size_mb(self, value: int):
        """최대 파일 크기 설정 (MB)"""
        if self._scan_state.max_file_size_mb != value:
            self._scan_state.max_file_size_mb = value
            self.state_changed.emit()

    # 공개 메서드들
    def start_scan(self, directory_path: str) -> bool:
        """스캔 시작"""
        try:
            if not self._file_scan_service:
                self.logger.error("FileScanService가 연결되지 않았습니다")
                return False

            if self._scan_state.is_scanning:
                self.logger.warning("이미 스캔 중입니다")
                return False

            # 스캔 시작
            success = self._file_scan_service.start_scan(
                directory_path=directory_path,
                include_subdirectories=self._scan_state.include_subdirectories,
                file_extensions=list(self._scan_state.file_extensions),
                max_file_size_bytes=self._scan_state.max_file_size_mb * 1024 * 1024,
                scan_hidden_files=self._scan_state.scan_hidden_files,
            )

            if success:
                self.logger.info(f"스캔 시작: {directory_path}")
                return True
            self.logger.error(f"스캔 시작 실패: {directory_path}")
            return False

        except Exception as e:
            self.logger.error(f"스캔 시작 중 오류 발생: {e}")
            self._set_error(str(e))
            return False

    def stop_scan(self) -> bool:
        """스캔 중지"""
        try:
            if not self._file_scan_service:
                return False

            if not self._scan_state.is_scanning:
                return False

            success = self._file_scan_service.stop_scan(self._scan_state.current_scan_id)

            if success:
                self.logger.info("스캔 중지 요청됨")
                return True
            self.logger.error("스캔 중지 실패")
            return False

        except Exception as e:
            self.logger.error(f"스캔 중지 중 오류 발생: {e}")
            return False

    def pause_scan(self) -> bool:
        """스캔 일시정지"""
        try:
            if not self._file_scan_service:
                return False

            if not self._scan_state.is_scanning:
                return False

            success = self._file_scan_service.pause_scan(self._scan_state.current_scan_id)

            if success:
                self.logger.info("스캔 일시정지됨")
                self._update_capabilities(ScanCapabilities.paused())
                return True
            self.logger.error("스캔 일시정지 실패")
            return False

        except Exception as e:
            self.logger.error(f"스캔 일시정지 중 오류 발생: {e}")
            return False

    def resume_scan(self) -> bool:
        """스캔 재개"""
        try:
            if not self._file_scan_service:
                return False

            if self._scan_state.is_scanning:
                return False

            success = self._file_scan_service.resume_scan(self._scan_state.current_scan_id)

            if success:
                self.logger.info("스캔 재개됨")
                self._update_capabilities(ScanCapabilities.scanning())
                return True
            self.logger.error("스캔 재개 실패")
            return False

        except Exception as e:
            self.logger.error(f"스캔 재개 중 오류 발생: {e}")
            return False

    def clear_scan_results(self) -> bool:
        """스캔 결과 초기화"""
        try:
            # 상태 초기화
            self._scan_state = ScanState()
            self._update_capabilities(ScanCapabilities())

            # 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(FileCountUpdateEvent(count=0))

            self.logger.info("스캔 결과 초기화됨")
            self.state_changed.emit()
            return True

        except Exception as e:
            self.logger.error(f"스캔 결과 초기화 중 오류 발생: {e}")
            return False

    def export_scan_results(self, file_path: str) -> bool:
        """스캔 결과 내보내기"""
        try:
            # TODO: 실제 내보내기 로직 구현
            self.logger.info(f"스캔 결과 내보내기: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"스캔 결과 내보내기 중 오류 발생: {e}")
            return False

    # 이벤트 핸들러들
    def _on_files_scanned(self, event: FilesScannedEvent):
        """파일 스캔 이벤트 처리"""
        try:
            if event.scan_id != self._scan_state.current_scan_id:
                return

            if event.status == ScanStatus.STARTED:
                self._scan_state.is_scanning = True
                self._scan_state.scanned_directory = event.directory_path
                self._update_capabilities(ScanCapabilities.scanning())

            elif event.status == ScanStatus.IN_PROGRESS:
                self._scan_state.scanned_files_count = event.scanned_files_count
                self._scan_state.total_files_found = event.total_files_found
                self._scan_state.valid_media_files = len(event.found_files)

                # 진행률 계산
                if event.total_files_found > 0:
                    progress = min(
                        100, int((event.scanned_files_count / event.total_files_found) * 100)
                    )
                    self._scan_state.scan_progress = progress

            elif event.status == ScanStatus.COMPLETED:
                self._scan_state.is_scanning = False
                self._scan_state.scan_progress = 100
                self._scan_state.valid_media_files = len(event.found_files)
                self._update_capabilities(ScanCapabilities.completed())

                # UI 업데이트 이벤트 발행
                if self._event_bus:
                    self._event_bus.publish(FileCountUpdateEvent(count=len(event.found_files)))
                    self._event_bus.publish(
                        SuccessMessageEvent(
                            message=f"스캔 완료: {len(event.found_files)}개 파일 발견"
                        )
                    )

            elif event.status == ScanStatus.FAILED:
                self._scan_state.is_scanning = False
                self._scan_state.last_error = event.error_message
                self._scan_state.error_count += 1
                self._update_capabilities(ScanCapabilities.error())

                # 오류 이벤트 발행
                if self._event_bus:
                    self._event_bus.publish(
                        ErrorMessageEvent(message=f"스캔 실패: {event.error_message}")
                    )

            elif event.status == ScanStatus.CANCELLED:
                self._scan_state.is_scanning = False
                self._scan_state.scan_progress = 0
                self._update_capabilities(ScanCapabilities())

                # 취소 이벤트 발행
                if self._event_bus:
                    self._event_bus.publish(StatusBarUpdateEvent(message="스캔이 취소되었습니다"))

            # 상태 변경 시그널 발생
            self.state_changed.emit()
            self.scan_progress_changed.emit(self._scan_state.scan_progress)

        except Exception as e:
            self.logger.error(f"파일 스캔 이벤트 처리 중 오류 발생: {e}")

    def _on_task_progress(self, event: TaskProgressEvent):
        """작업 진행률 이벤트 처리"""
        try:
            if event.task_id != self._scan_state.current_scan_id:
                return

            self._scan_state.current_step = event.current_step
            self._scan_state.scan_progress = event.progress_percent

            # 진행률 변경 시그널 발생
            self.scan_progress_changed.emit(event.progress_percent)

        except Exception as e:
            self.logger.error(f"작업 진행률 이벤트 처리 중 오류 발생: {e}")

    def _on_task_started(self, event: TaskStartedEvent):
        """작업 시작 이벤트 처리"""
        try:
            if "scan" in event.task_name.lower():
                self._scan_state.current_scan_id = event.task_id
                self._scan_state.is_scanning = True
                self._update_capabilities(ScanCapabilities.scanning())
                self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"작업 시작 이벤트 처리 중 오류 발생: {e}")

    def _on_task_completed(self, event: TaskCompletedEvent):
        """작업 완료 이벤트 처리"""
        try:
            if event.task_id == self._scan_state.current_scan_id:
                self._scan_state.is_scanning = False
                self._update_capabilities(ScanCapabilities.completed())
                self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"작업 완료 이벤트 처리 중 오류 발생: {e}")

    def _on_task_failed(self, event: TaskFailedEvent):
        """작업 실패 이벤트 처리"""
        try:
            if event.task_id == self._scan_state.current_scan_id:
                self._scan_state.is_scanning = False
                self._scan_state.last_error = event.error_message
                self._scan_state.error_count += 1
                self._update_capabilities(ScanCapabilities.error())
                self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"작업 실패 이벤트 처리 중 오류 발생: {e}")

    def _on_task_cancelled(self, event: TaskCancelledEvent):
        """작업 취소 이벤트 처리"""
        try:
            if event.task_id == self._scan_state.current_scan_id:
                self._scan_state.is_scanning = False
                self._scan_state.scan_progress = 0
                self._update_capabilities(ScanCapabilities())
                self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"작업 취소 이벤트 처리 중 오류 발생: {e}")

    # 내부 헬퍼 메서드들
    def _update_capabilities(self, new_capabilities: ScanCapabilities):
        """UI 기능 상태 업데이트"""
        if self._scan_capabilities != new_capabilities:
            self._scan_capabilities = new_capabilities
            self.capabilities_changed.emit()

    def _set_error(self, error_message: str):
        """오류 상태 설정"""
        self._scan_state.last_error = error_message
        self._scan_state.error_count += 1
        self.error_occurred.emit(error_message)
        self.state_changed.emit()

    def get_scan_summary(self) -> dict[str, any]:
        """스캔 요약 정보 반환"""
        return {
            "is_scanning": self._scan_state.is_scanning,
            "scanned_directory": self._scan_state.scanned_directory,
            "total_files_found": self._scan_state.total_files_found,
            "valid_media_files": self._scan_state.valid_media_files,
            "scan_progress": self._scan_state.scan_progress,
            "current_step": self._scan_state.current_step,
            "last_error": self._scan_state.last_error,
            "error_count": self._scan_state.error_count,
        }
