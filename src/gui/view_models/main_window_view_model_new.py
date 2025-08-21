"""
새로운 MainWindow ViewModel - Phase 2 MVVM 아키텍처

Phase 1에서 구현된 TypedEventBus, DI Container, 도메인 모델을 활용하여
완전한 MVVM 패턴을 구현합니다.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from app import (
    ErrorMessageEvent,
    FileCountUpdateEvent,
    # 이벤트
    FilesScannedEvent,
    IBackgroundTaskService,
    # 서비스
    IFileScanService,
    IUIUpdateService,
    # 도메인 모델
    MediaFile,
    MediaGroup,
    MediaLibrary,
    MediaMetadata,
    MediaQuality,
    MediaSource,
    MediaType,
    MenuStateUpdateEvent,
    ProcessingFlag,
    ScanStatus,
    # UI 이벤트
    StatusBarUpdateEvent,
    SuccessMessageEvent,
    TableDataUpdateEvent,
    TaskCancelledEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskProgressEvent,
    TaskStartedEvent,
    # 인프라
    TypedEventBus,
    UIStateUpdateEvent,
    WindowTitleUpdateEvent,
    get_event_bus,
    get_service,
)


@dataclass
class ApplicationState:
    """애플리케이션 전체 상태"""

    # 스캔 상태
    is_scanning: bool = False
    current_scan_id: UUID | None = None
    scanned_directory: str | None = None

    # 정리 상태
    is_organizing: bool = False

    # TMDB 검색 상태
    is_searching_tmdb: bool = False

    # 데이터 상태
    has_scanned_files: bool = False
    has_grouped_files: bool = False
    has_tmdb_matches: bool = False

    # 선택 상태
    selected_files: set[UUID] = field(default_factory=set)
    selected_groups: set[UUID] = field(default_factory=set)

    # 진행률
    scan_progress: int = 0
    organize_progress: int = 0
    tmdb_progress: int = 0

    # 메시지
    status_message: str = "AnimeSorter가 준비되었습니다"
    last_error: str | None = None


@dataclass
class UICapabilities:
    """UI에서 수행 가능한 작업들"""

    can_start_scan: bool = True
    can_stop_scan: bool = False
    can_start_organize: bool = False
    can_start_tmdb_search: bool = False
    can_clear_results: bool = False

    @classmethod
    def from_app_state(cls, state: ApplicationState) -> "UICapabilities":
        """애플리케이션 상태에서 UI 가능 작업 계산"""
        return cls(
            can_start_scan=not state.is_scanning and not state.is_organizing,
            can_stop_scan=state.is_scanning,
            can_start_organize=state.has_grouped_files
            and not state.is_organizing
            and not state.is_scanning,
            can_start_tmdb_search=state.has_scanned_files
            and not state.is_searching_tmdb
            and not state.is_organizing,
            can_clear_results=state.has_scanned_files
            and not state.is_scanning
            and not state.is_organizing,
        )


class MainWindowViewModelNew(QObject):
    """
    새로운 MainWindow ViewModel - Phase 2 MVVM 구현

    TypedEventBus, DI Container, 도메인 모델을 활용한 완전한 MVVM 패턴
    """

    # Qt 시그널 정의 (View와의 데이터 바인딩용)
    state_changed = pyqtSignal()
    capabilities_changed = pyqtSignal()
    media_library_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Phase 1 인프라 활용
        self.event_bus: TypedEventBus = get_event_bus()
        self.file_scan_service: IFileScanService = get_service(IFileScanService)
        self.ui_update_service: IUIUpdateService = get_service(IUIUpdateService)
        self.background_task_service: IBackgroundTaskService = get_service(IBackgroundTaskService)

        # 상태 관리
        self._app_state = ApplicationState()
        self._ui_capabilities = UICapabilities.from_app_state(self._app_state)

        # 도메인 모델
        self._media_library = MediaLibrary()

        # 이벤트 구독 설정
        self._setup_event_subscriptions()

        # 반응형 UI 시스템 설정
        self._setup_reactive_system()

        self.logger.info(
            "MainWindowViewModelNew 초기화 완료 (TypedEventBus + DI Container + Reactive UI)"
        )

    def _setup_event_subscriptions(self) -> None:
        """TypedEventBus 이벤트 구독 설정"""

        # 파일 스캔 이벤트
        self.event_bus.subscribe(FilesScannedEvent, self._on_files_scanned, weak_ref=False)

        # 백그라운드 작업 이벤트
        self.event_bus.subscribe(TaskStartedEvent, self._on_task_started, weak_ref=False)
        self.event_bus.subscribe(TaskProgressEvent, self._on_task_progress, weak_ref=False)
        self.event_bus.subscribe(TaskCompletedEvent, self._on_task_completed, weak_ref=False)
        self.event_bus.subscribe(TaskFailedEvent, self._on_task_failed, weak_ref=False)
        self.event_bus.subscribe(TaskCancelledEvent, self._on_task_cancelled, weak_ref=False)

        self.logger.info("이벤트 구독 설정 완료")

    def _setup_reactive_system(self) -> None:
        """반응형 UI 시스템 설정"""

        # Qt 시그널을 EventBus 이벤트와 연결
        self.state_changed.connect(self._on_state_changed_reactive)
        self.capabilities_changed.connect(self._on_capabilities_changed_reactive)
        self.media_library_changed.connect(self._on_media_library_changed_reactive)

        self.logger.info("반응형 UI 시스템 설정 완료")

    # ===== 반응형 시스템 메서드 =====

    def _on_state_changed_reactive(self) -> None:
        """상태 변경 시 자동 UI 업데이트"""
        # UI 상태 업데이트 이벤트 발행 (올바른 필드명 사용)
        self.event_bus.publish(
            UIStateUpdateEvent(
                has_data=self._app_state.has_scanned_files,
                is_processing=self._app_state.is_scanning
                or self._app_state.is_organizing
                or self._app_state.is_searching_tmdb,
                has_selection=len(self._app_state.selected_files) > 0
                or len(self._app_state.selected_groups) > 0,
                has_tmdb_matches=self._app_state.has_tmdb_matches,
                can_organize=self._ui_capabilities.can_start_organize,
            )
        )

        # 개별 메뉴 상태 업데이트 이벤트들 발행
        menu_states = [
            ("scan", self._ui_capabilities.can_start_scan),
            ("stop", self._ui_capabilities.can_stop_scan),
            ("organize", self._ui_capabilities.can_start_organize),
            ("tmdb_search", self._ui_capabilities.can_start_tmdb_search),
            ("clear", self._ui_capabilities.can_clear_results),
        ]

        for action_name, enabled in menu_states:
            self.event_bus.publish(MenuStateUpdateEvent(action_name=action_name, enabled=enabled))

        # 윈도우 제목 업데이트
        title_parts = ["AnimeSorter"]
        if self._app_state.is_scanning:
            title_parts.append("(스캔 중)")
        elif self._app_state.is_organizing:
            title_parts.append("(정리 중)")
        elif self._app_state.is_searching_tmdb:
            title_parts.append("(검색 중)")
        elif self._app_state.has_scanned_files:
            title_parts.append(f"({len(self._media_library.files)}개 파일)")

        self.event_bus.publish(WindowTitleUpdateEvent(title=" ".join(title_parts)))

    def _on_capabilities_changed_reactive(self) -> None:
        """UI 가능 작업 변경 시 자동 업데이트"""
        # 메뉴와 버튼 상태 자동 업데이트는 _on_state_changed_reactive에서 처리

    def _on_media_library_changed_reactive(self) -> None:
        """미디어 라이브러리 변경 시 자동 UI 업데이트"""

        # 파일 수 업데이트 (올바른 필드명 사용)
        stats = self._media_library.get_stats()
        self.event_bus.publish(
            FileCountUpdateEvent(
                count=stats["total_files"],
                processed=stats.get("grouped_files", 0),
                failed=stats.get("failed_files", 0),
            )
        )

        # 테이블 데이터 업데이트 (올바른 필드명 사용)
        self.event_bus.publish(
            TableDataUpdateEvent(
                table_name="media_library",
                data=list(self._media_library.files),
                selection_changed=False,
            )
        )

        # 상태바 업데이트
        if stats["total_files"] > 0:
            self.event_bus.publish(
                StatusBarUpdateEvent(
                    message=f"총 {stats['total_files']}개 파일 ({stats.get('grouped_files', 0)}개 그룹화됨)"
                )
            )

    def _trigger_reactive_update(self, update_type: str = "all") -> None:
        """반응형 업데이트 수동 트리거"""

        if update_type in ("all", "state"):
            self.state_changed.emit()

        if update_type in ("all", "capabilities"):
            self.capabilities_changed.emit()

        if update_type in ("all", "media_library"):
            self.media_library_changed.emit()

    # ===== Qt 프로퍼티 (View 바인딩) =====

    @pyqtProperty(bool, notify=capabilities_changed)
    def canStartScan(self) -> bool:
        return self._ui_capabilities.can_start_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def canStopScan(self) -> bool:
        return self._ui_capabilities.can_stop_scan

    @pyqtProperty(bool, notify=capabilities_changed)
    def canStartOrganize(self) -> bool:
        return self._ui_capabilities.can_start_organize

    @pyqtProperty(bool, notify=capabilities_changed)
    def canStartTmdbSearch(self) -> bool:
        return self._ui_capabilities.can_start_tmdb_search

    @pyqtProperty(str, notify=state_changed)
    def statusMessage(self) -> str:
        return self._app_state.status_message

    @pyqtProperty(int, notify=state_changed)
    def scanProgress(self) -> int:
        return self._app_state.scan_progress

    @pyqtProperty(int, notify=media_library_changed)
    def fileCount(self) -> int:
        """총 파일 수"""
        return len(self._media_library.files)

    @pyqtProperty(int, notify=media_library_changed)
    def groupCount(self) -> int:
        """총 그룹 수"""
        return len(self._media_library.groups)

    @pyqtProperty(int, notify=media_library_changed)
    def ungroupedFileCount(self) -> int:
        """그룹화되지 않은 파일 수"""
        return len(self._media_library.get_ungrouped_files())

    @pyqtProperty(float, notify=media_library_changed)
    def totalSizeGB(self) -> float:
        """총 파일 크기 (GB)"""
        stats = self._media_library.get_stats()
        return stats.get("total_size_gb", 0.0)

    @pyqtProperty(int, notify=media_library_changed)
    def completeGroupCount(self) -> int:
        """완성된 그룹 수"""
        stats = self._media_library.get_stats()
        return stats.get("complete_groups", 0)

    @pyqtProperty(int, notify=media_library_changed)
    def verifiedGroupCount(self) -> int:
        """검증된 그룹 수"""
        stats = self._media_library.get_stats()
        return stats.get("verified_groups", 0)

    @pyqtProperty(bool, notify=media_library_changed)
    def hasFiles(self) -> bool:
        """파일 존재 여부"""
        return len(self._media_library.files) > 0

    @pyqtProperty(bool, notify=media_library_changed)
    def hasGroups(self) -> bool:
        """그룹 존재 여부"""
        return len(self._media_library.groups) > 0

    # ===== 비즈니스 로직 메서드 =====

    def start_directory_scan(self, directory_path: str) -> bool:
        """디렉토리 스캔 시작"""
        if not self._ui_capabilities.can_start_scan:
            self.logger.warning("현재 스캔을 시작할 수 없는 상태입니다")
            return False

        try:
            self.logger.info(f"디렉토리 스캔 시작: {directory_path}")

            # FileScanService를 통한 백그라운드 스캔
            scan_id = self.file_scan_service.scan_directory(
                directory_path=Path(directory_path),
                recursive=True,
                extensions={".mkv", ".mp4", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"},
                min_file_size=1024 * 1024,  # 1MB
                max_file_size=50 * 1024 * 1024 * 1024,  # 50GB
            )

            # 상태 업데이트
            self._update_app_state(
                is_scanning=True,
                current_scan_id=scan_id,
                status_message=f"디렉토리 스캔 중: {Path(directory_path).name}",
            )

            return True

        except Exception as e:
            self.logger.error(f"디렉토리 스캔 시작 실패: {e}")
            self._publish_error(f"스캔 시작 실패: {str(e)}")
            return False

    def start_file_scan(self, file_paths: list[str]) -> bool:
        """선택된 파일들 스캔 시작"""
        if not self._ui_capabilities.can_start_scan:
            self.logger.warning("현재 스캔을 시작할 수 없는 상태입니다")
            return False

        try:
            self.logger.info(f"파일 스캔 시작: {len(file_paths)}개 파일")

            # FileScanService를 통한 백그라운드 스캔
            scan_id = self.file_scan_service.scan_files([Path(p) for p in file_paths])

            # 상태 업데이트
            self._update_app_state(
                is_scanning=True,
                current_scan_id=scan_id,
                status_message=f"파일 스캔 중: {len(file_paths)}개 파일",
            )

            return True

        except Exception as e:
            self.logger.error(f"파일 스캔 시작 실패: {e}")
            self._publish_error(f"스캔 시작 실패: {str(e)}")
            return False

    def stop_scan(self) -> bool:
        """현재 스캔 중지"""
        if not self._ui_capabilities.can_stop_scan or not self._app_state.current_scan_id:
            self.logger.warning("중지할 스캔이 없습니다")
            return False

        try:
            success = self.file_scan_service.cancel_scan(self._app_state.current_scan_id)
            if success:
                self.logger.info("스캔 중지 요청됨")
                self._publish_status("스캔 중지 중...")
            return success

        except Exception as e:
            self.logger.error(f"스캔 중지 실패: {e}")
            self._publish_error(f"스캔 중지 실패: {str(e)}")
            return False

    def clear_results(self) -> None:
        """스캔 결과 지우기"""
        if not self._ui_capabilities.can_clear_results:
            self.logger.warning("현재 결과를 지울 수 없는 상태입니다")
            return

        # 미디어 라이브러리 초기화
        self._media_library = MediaLibrary()

        # 상태 초기화
        self._update_app_state(
            has_scanned_files=False,
            has_grouped_files=False,
            has_tmdb_matches=False,
            selected_files=set(),
            selected_groups=set(),
            scan_progress=0,
            status_message="결과가 지워졌습니다",
        )

        self.media_library_changed.emit()
        self.logger.info("스캔 결과 지워짐")

    # ===== 이벤트 핸들러 =====

    def _on_files_scanned(self, event: FilesScannedEvent) -> None:
        """파일 스캔 완료 이벤트 처리"""
        self.logger.info(
            f"파일 스캔 이벤트 수신: {len(event.found_files)}개 파일, 상태: {event.status}"
        )

        if event.status == ScanStatus.COMPLETED:
            # 스캔 완료 - MediaFile 객체들 생성 및 메타데이터 추출
            self.logger.info("스캔된 파일들을 도메인 모델로 변환 중...")

            new_media_files = []
            for file_path in event.found_files:
                try:
                    # 도메인 모델 생성 (올바른 파라미터 사용)
                    media_file = MediaFile(
                        path=file_path,
                        media_type=MediaType.VIDEO,  # 기본값, __post_init__에서 확장자 기반 추정
                        flags={ProcessingFlag.NEEDS_RENAME},  # set 타입 사용
                    )

                    # 파일 메타데이터 기본 추출
                    media_file = self._extract_basic_metadata(media_file)

                    new_media_files.append(media_file)

                except Exception as e:
                    self.logger.warning(f"파일 {file_path} 도메인 모델 생성 실패: {e}")
                    continue

            # 미디어 라이브러리에 추가
            for media_file in new_media_files:
                self._media_library.add_file(media_file)

            self.logger.info(f"{len(new_media_files)}개 파일이 미디어 라이브러리에 추가됨")

            # 자동 그룹화 시도
            self._auto_group_files(new_media_files)

            # 상태 업데이트
            self._update_app_state(
                is_scanning=False,
                current_scan_id=None,
                has_scanned_files=len(new_media_files) > 0,
                has_grouped_files=len(self._media_library.groups) > 0,
                scan_progress=100,
                status_message=f"스캔 완료: {len(new_media_files)}개 파일 발견",
            )

            self._publish_success(f"스캔 완료: {len(new_media_files)}개 파일")

        elif event.status == ScanStatus.CANCELLED:
            self._update_app_state(
                is_scanning=False,
                current_scan_id=None,
                scan_progress=0,
                status_message="스캔이 취소되었습니다",
            )

        elif event.status == ScanStatus.FAILED:
            self._update_app_state(
                is_scanning=False, current_scan_id=None, scan_progress=0, status_message="스캔 실패"
            )
            self._publish_error(event.error_message or "스캔 중 오류 발생")

    def _on_task_started(self, event: TaskStartedEvent) -> None:
        """백그라운드 작업 시작 이벤트"""
        self.logger.debug(f"작업 시작: {event.task_name}")
        self._publish_status(f"작업 시작: {event.task_name}")

    def _on_task_progress(self, event: TaskProgressEvent) -> None:
        """백그라운드 작업 진행률 이벤트"""
        if self._app_state.is_scanning:
            self._update_app_state(scan_progress=event.progress_percent)

    def _on_task_completed(self, event: TaskCompletedEvent) -> None:
        """백그라운드 작업 완료 이벤트"""
        self.logger.info(f"작업 완료: {event.task_name}")
        self._publish_success(f"작업 완료: {event.task_name}")

    def _on_task_failed(self, event: TaskFailedEvent) -> None:
        """백그라운드 작업 실패 이벤트"""
        self.logger.error(f"작업 실패: {event.task_name} - {event.error_message}")
        self._publish_error(f"작업 실패: {event.error_message}")

        if self._app_state.is_scanning:
            self._update_app_state(is_scanning=False, current_scan_id=None, scan_progress=0)

    def _on_task_cancelled(self, event: TaskCancelledEvent) -> None:
        """백그라운드 작업 취소 이벤트"""
        self.logger.info(f"작업 취소: {event.task_name}")
        self._publish_status(f"작업 취소: {event.task_name}")

        if self._app_state.is_scanning:
            self._update_app_state(is_scanning=False, current_scan_id=None, scan_progress=0)

    # ===== 헬퍼 메서드 =====

    def _update_app_state(self, **kwargs) -> None:
        """애플리케이션 상태 업데이트"""
        # 미디어 라이브러리 관련 상태 변경 감지
        media_library_keys = {"has_scanned_files", "has_grouped_files", "has_tmdb_matches"}
        media_library_changed = any(key in media_library_keys for key in kwargs)

        # 상태 업데이트
        for key, value in kwargs.items():
            if hasattr(self._app_state, key):
                setattr(self._app_state, key, value)

        # UI 가능 작업 재계산
        new_capabilities = UICapabilities.from_app_state(self._app_state)

        # 변경사항이 있으면 시그널 발생
        if new_capabilities != self._ui_capabilities:
            self._ui_capabilities = new_capabilities
            self.capabilities_changed.emit()

        # 미디어 라이브러리 관련 시그널 발생
        if media_library_changed:
            self.media_library_changed.emit()

        self.state_changed.emit()

    def _publish_status(self, message: str) -> None:
        """상태 메시지 발행"""
        self.event_bus.publish(StatusBarUpdateEvent(message=message))
        self._update_app_state(status_message=message)

    def _publish_success(self, message: str) -> None:
        """성공 메시지 발행"""
        self.event_bus.publish(SuccessMessageEvent(message=message))

    def _publish_error(self, message: str) -> None:
        """에러 메시지 발행"""
        self.event_bus.publish(ErrorMessageEvent(message=message, error_type="error"))
        self._update_app_state(last_error=message)

    # ===== 프로퍼티 접근자 =====

    def get_media_library(self) -> MediaLibrary:
        """미디어 라이브러리 반환"""
        return self._media_library

    def get_app_state(self) -> ApplicationState:
        """애플리케이션 상태 반환"""
        return self._app_state

    def get_ui_capabilities(self) -> UICapabilities:
        """UI 가능 작업 반환"""
        return self._ui_capabilities

    # ===== 비즈니스 로직 메서드 =====

    def stop_current_scan(self) -> None:
        """현재 스캔 중지"""
        try:
            if not self._app_state.is_scanning or not self._app_state.current_scan_id:
                self._publish_error("중지할 스캔이 없습니다.")
                return

            self.logger.info(f"스캔 중지 요청: {self._app_state.current_scan_id}")

            # FileScanService 가져오기
            file_scan_service = get_service(IFileScanService)

            # 스캔 취소
            success = file_scan_service.cancel_scan(self._app_state.current_scan_id)

            if success:
                self._publish_status("스캔 중지 요청 완료")
                self.logger.info("스캔 중지 요청 성공")
            else:
                self._publish_error("스캔 중지 요청 실패")
                self.logger.warning("스캔 중지 요청 실패")

            # 상태는 TaskCancelledEvent에서 업데이트됨

        except Exception as e:
            self.logger.error(f"스캔 중지 실패: {e}")
            self._publish_error(f"스캔 중지 실패: {str(e)}")

            # 강제로 상태 초기화
            self._update_app_state(is_scanning=False, current_scan_id=None, scan_progress=0)

    def start_file_organization(self, operation_type: str, options: dict = None) -> None:
        """파일 정리 시작"""
        try:
            # TODO: 실제 파일 정리 로직 구현
            self.logger.info(f"파일 정리 시작: {operation_type}")
            self._publish_status(f"파일 정리 시작: {operation_type}")

            # FileOrganizationService 사용하여 구현 예정

        except Exception as e:
            self.logger.error(f"파일 정리 시작 실패: {e}")
            self._publish_error(f"파일 정리 시작 실패: {str(e)}")

    def start_metadata_search(self, search_type: str, options: dict = None) -> None:
        """메타데이터 검색 시작"""
        try:
            # TODO: 실제 메타데이터 검색 로직 구현
            self.logger.info(f"메타데이터 검색 시작: {search_type}")
            self._publish_status(f"메타데이터 검색 시작: {search_type}")

            # TMDBSearchService 사용하여 구현 예정

        except Exception as e:
            self.logger.error(f"메타데이터 검색 시작 실패: {e}")
            self._publish_error(f"메타데이터 검색 시작 실패: {str(e)}")

    # ===== 도메인 모델 헬퍼 메서드 =====

    def _extract_basic_metadata(self, media_file: MediaFile) -> MediaFile:
        """미디어 파일에서 기본 메타데이터 추출"""
        try:
            # 파일 정보 추출
            if media_file.path.exists():
                file_size = media_file.path.stat().st_size

                # MediaMetadata 생성
                media_file.metadata = MediaMetadata(
                    file_size_bytes=file_size,
                    quality=self._extract_quality_from_filename(media_file.name),
                    source=self._extract_source_from_filename(media_file.name),
                )

                # 파일명에서 에피소드/시즌 정보 추출 (기존 FileParser 활용)
                parsed_info = self._parse_filename_info(media_file.path)
                if parsed_info:
                    media_file.parsed_title = parsed_info.get("title")
                    media_file.episode = parsed_info.get("episode")
                    media_file.season = parsed_info.get("season")

                    # 원본 파일명 저장
                    media_file.original_name = media_file.name

                # 플래그 설정
                if file_size < 1024 * 1024:  # 1MB 미만
                    media_file.add_flag(ProcessingFlag.IS_SAMPLE)

                if any(
                    keyword in media_file.name.lower()
                    for keyword in ["sample", "preview", "trailer"]
                ):
                    media_file.add_flag(ProcessingFlag.IS_SAMPLE)

            self.logger.debug(f"파일 메타데이터 추출 완료: {media_file.name}")

        except Exception as e:
            self.logger.warning(f"메타데이터 추출 실패 {media_file.path}: {e}")

        return media_file

    def _extract_quality_from_filename(self, filename: str) -> MediaQuality:
        """파일명에서 품질 정보 추출"""
        filename_lower = filename.lower()

        if "4k" in filename_lower or "2160p" in filename_lower:
            return MediaQuality.UHD_4K
        if "1440p" in filename_lower:
            return MediaQuality.QHD_1440P
        if "1080p" in filename_lower:
            return MediaQuality.FHD_1080P
        if "720p" in filename_lower:
            return MediaQuality.HD_720P
        if "480p" in filename_lower:
            return MediaQuality.SD_480P

        return MediaQuality.UNKNOWN

    def _extract_source_from_filename(self, filename: str) -> MediaSource:
        """파일명에서 소스 정보 추출"""
        filename_lower = filename.lower()

        if "bluray" in filename_lower or "bdremux" in filename_lower:
            return MediaSource.BLURAY
        if "webdl" in filename_lower or "web-dl" in filename_lower:
            return MediaSource.WEBDL
        if "webrip" in filename_lower:
            return MediaSource.WEBRIP
        if "hdtv" in filename_lower:
            return MediaSource.HDTV
        if "web" in filename_lower:
            return MediaSource.WEB
        if "dvd" in filename_lower:
            return MediaSource.DVD

        return MediaSource.UNKNOWN

    def _parse_filename_info(self, file_path: Path) -> dict | None:
        """FileParser를 활용한 파일명 정보 추출"""
        try:
            # 기존 FileParser 서비스 활용
            # TODO: FileParser를 DI Container에서 가져와서 사용
            # 현재는 기본적인 정규식으로 구현

            filename = file_path.stem
            info = {}

            # 에피소드 번호 추출 (단순화된 버전)
            import re

            # S01E01 형태
            season_episode = re.search(r"[Ss](\d+)[Ee](\d+)", filename)
            if season_episode:
                info["season"] = int(season_episode.group(1))
                info["episode"] = int(season_episode.group(2))

            # Episode 01 형태
            episode_only = re.search(r"[Ee]pisode\s*(\d+)", filename)
            if episode_only and "episode" not in info:
                info["episode"] = int(episode_only.group(1))

            # 단순 숫자 형태 (- 01, _01, 01 등)
            simple_episode = re.search(r"[\-_\s](\d{2,3})[\-_\s\.]", filename)
            if simple_episode and "episode" not in info:
                episode_num = int(simple_episode.group(1))
                if 1 <= episode_num <= 999:  # 합리적인 에피소드 범위
                    info["episode"] = episode_num

            # 제목 추출 (간단한 버전)
            # [Group] Title - Episode 형태에서 Title 추출
            title_match = re.search(r"^\[.*?\]\s*(.*?)\s*[\-_]\s*(?:\d+|[Ss]\d+[Ee]\d+)", filename)
            if title_match:
                info["title"] = title_match.group(1).strip()

            return info if info else None

        except Exception as e:
            self.logger.warning(f"파일명 파싱 실패 {file_path}: {e}")
            return None

    def _auto_group_files(self, media_files: list[MediaFile]) -> None:
        """미디어 파일들 자동 그룹화"""
        try:
            self.logger.info(f"{len(media_files)}개 파일 자동 그룹화 시작...")

            # 제목별로 그룹화
            title_groups = {}
            ungrouped_files = []

            for media_file in media_files:
                title = media_file.parsed_title
                if title:
                    # 제목 정규화 (대소문자, 공백 등)
                    normalized_title = self._normalize_title(title)

                    if normalized_title not in title_groups:
                        title_groups[normalized_title] = {"original_title": title, "files": []}

                    title_groups[normalized_title]["files"].append(media_file)
                else:
                    ungrouped_files.append(media_file)

            # MediaGroup 생성
            created_groups = 0
            for _normalized_title, group_data in title_groups.items():
                files = group_data["files"]

                # 2개 이상의 파일이 있거나, 시즌 정보가 있는 경우에만 그룹 생성
                if len(files) >= 2 or any(f.season is not None for f in files):
                    media_group = MediaGroup(
                        title=group_data["original_title"],
                        season=self._extract_common_season(files),
                    )

                    # 그룹에 파일들 추가
                    for media_file in files:
                        # 파일의 group_id 설정
                        media_file.group_id = media_group.id

                        # 에피소드 정보가 있으면 그룹에 추가
                        if media_file.episode:
                            media_group.add_episode(media_file.episode, media_file.id)

                    # 총 에피소드 수 추정
                    if media_group.episodes:
                        max_episode = max(media_group.episodes.keys())
                        media_group.total_episodes = max_episode

                    # 라이브러리에 그룹 추가
                    self._media_library.add_group(media_group)
                    created_groups += 1

                    self.logger.debug(f"그룹 생성: {media_group.title} ({len(files)}개 파일)")

                else:
                    # 단일 파일은 그룹화하지 않음
                    ungrouped_files.extend(files)

            self.logger.info(
                f"자동 그룹화 완료: {created_groups}개 그룹, {len(ungrouped_files)}개 미그룹화"
            )

        except Exception as e:
            self.logger.error(f"자동 그룹화 실패: {e}")

    def _normalize_title(self, title: str) -> str:
        """제목 정규화"""
        # 대소문자 통일, 특수문자 제거, 공백 정리
        import re

        normalized = title.lower()
        normalized = re.sub(r"[^\w\s]", "", normalized)  # 특수문자 제거
        return re.sub(r"\s+", " ", normalized).strip()  # 공백 정리

    def _extract_common_season(self, files: list[MediaFile]) -> int | None:
        """파일들의 공통 시즌 추출"""
        seasons = {f.season for f in files if f.season is not None}
        if len(seasons) == 1:
            return seasons.pop()
        return None

    # ===== 정리 =====

    def dispose(self) -> None:
        """ViewModel 정리"""
        try:
            # 이벤트 구독 해제는 TypedEventBus가 weak_ref=False로 설정되어 있어
            # 객체 소멸시 자동으로 처리됨
            self.logger.info("MainWindowViewModelNew 정리 완료")
        except Exception as e:
            self.logger.error(f"ViewModel 정리 실패: {e}")
