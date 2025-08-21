"""
OrganizeViewModel - 파일 정리 기능에 특화된 ViewModel

Phase 2 MVVM 아키텍처의 일부로, 파일 정리 및 조직화 기능을 담당합니다.
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from app import (
    DirectoryCreatedEvent,
    ErrorMessageEvent,
    FileDeletedEvent,
    FileMovedEvent,
    FileRenamedEvent,
    # 서비스
    IFileOrganizationService,
    IUIUpdateService,
    # 도메인 모델
    OrganizationCancelledEvent,
    OrganizationCompletedEvent,
    OrganizationFailedEvent,
    OrganizationProgressEvent,
    # 이벤트
    OrganizationStartedEvent,
    StatusBarUpdateEvent,
    SuccessMessageEvent,
    TypedEventBus,
    get_event_bus,
    get_service,
)


@dataclass
class OrganizationState:
    """파일 정리 상태 정보"""

    # 정리 진행 상태
    is_organizing: bool = False
    current_organization_id: UUID | None = None

    # 정리 모드
    organization_mode: str = "simulation"  # simulation, safe, normal, aggressive

    # 정리 결과
    total_files_to_process: int = 0
    processed_files_count: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    skipped_operations: int = 0

    # 진행률
    organization_progress: int = 0
    current_operation: str = ""
    current_file: str = ""

    # 정리 설정
    create_directories: bool = True
    overwrite_existing: bool = False
    use_hard_links: bool = False
    preserve_timestamps: bool = True
    backup_before_organize: bool = True

    # 오류 정보
    last_error: str | None = None
    error_count: int = 0

    # 정리 통계
    files_moved: int = 0
    files_renamed: int = 0
    files_deleted: int = 0
    directories_created: int = 0


@dataclass
class OrganizationCapabilities:
    """파일 정리 관련 UI 기능들"""

    can_start_organization: bool = True
    can_stop_organization: bool = False
    can_pause_organization: bool = False
    can_resume_organization: bool = False
    can_preview_organization: bool = True
    can_undo_last_operation: bool = False
    can_redo_last_operation: bool = False
    can_clear_organization_results: bool = False
    can_export_organization_log: bool = False

    @classmethod
    def organizing(cls) -> "OrganizationCapabilities":
        """정리 중일 때의 기능 상태"""
        return cls(
            can_start_organization=False,
            can_stop_organization=True,
            can_pause_organization=True,
            can_resume_organization=False,
            can_preview_organization=False,
            can_undo_last_operation=False,
            can_redo_last_operation=False,
            can_clear_organization_results=False,
            can_export_organization_log=False,
        )

    @classmethod
    def paused(cls) -> "OrganizationCapabilities":
        """정리 일시정지 상태의 기능"""
        return cls(
            can_start_organization=False,
            can_stop_organization=True,
            can_pause_organization=False,
            can_resume_organization=True,
            can_preview_organization=False,
            can_undo_last_operation=False,
            can_redo_last_operation=False,
            can_clear_organization_results=False,
            can_export_organization_log=False,
        )

    @classmethod
    def completed(cls) -> "OrganizationCapabilities":
        """정리 완료 상태의 기능"""
        return cls(
            can_start_organization=True,
            can_stop_organization=False,
            can_pause_organization=False,
            can_resume_organization=False,
            can_preview_organization=True,
            can_undo_last_operation=True,
            can_redo_last_operation=True,
            can_clear_organization_results=True,
            can_export_organization_log=True,
        )

    @classmethod
    def error(cls) -> "OrganizationCapabilities":
        """정리 오류 상태의 기능"""
        return cls(
            can_start_organization=True,
            can_stop_organization=False,
            can_pause_organization=False,
            can_resume_organization=False,
            can_preview_organization=True,
            can_undo_last_operation=True,
            can_redo_last_operation=False,
            can_clear_organization_results=True,
            can_export_organization_log=True,
        )


class OrganizeViewModel(QObject):
    """파일 정리 기능 전용 ViewModel"""

    # 시그널 정의
    state_changed = pyqtSignal()
    capabilities_changed = pyqtSignal()
    organization_progress_changed = pyqtSignal(int)
    current_operation_changed = pyqtSignal(str)
    current_file_changed = pyqtSignal(str)
    operation_result_changed = pyqtSignal(str, str)  # operation_type, result
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # 로깅 설정
        self.logger = logging.getLogger(__name__)

        # 상태 초기화
        self._organization_state = OrganizationState()
        self._organization_capabilities = OrganizationCapabilities()

        # 서비스 연결
        self._event_bus: TypedEventBus | None = None
        self._file_organization_service: IFileOrganizationService | None = None
        self._ui_update_service: IUIUpdateService | None = None

        # 초기화
        self._setup_services()
        self._setup_event_subscriptions()

        self.logger.info("OrganizeViewModel 초기화 완료")

    def _setup_services(self):
        """필요한 서비스들을 설정"""
        try:
            self._event_bus = get_event_bus()
            self._file_organization_service = get_service(IFileOrganizationService)
            self._ui_update_service = get_service(IUIUpdateService)

            self.logger.info("OrganizeViewModel 서비스 연결 완료")
        except Exception as e:
            self.logger.error(f"OrganizeViewModel 서비스 연결 실패: {e}")

    def _setup_event_subscriptions(self):
        """이벤트 구독 설정"""
        if not self._event_bus:
            return

        try:
            # 파일 정리 관련 이벤트 구독
            self._event_bus.subscribe(
                OrganizationStartedEvent, self._on_organization_started, weak_ref=False
            )
            self._event_bus.subscribe(
                OrganizationProgressEvent, self._on_organization_progress, weak_ref=False
            )
            self._event_bus.subscribe(
                OrganizationCompletedEvent, self._on_organization_completed, weak_ref=False
            )
            self._event_bus.subscribe(
                OrganizationFailedEvent, self._on_organization_failed, weak_ref=False
            )
            self._event_bus.subscribe(
                OrganizationCancelledEvent, self._on_organization_cancelled, weak_ref=False
            )

            # 개별 파일 작업 이벤트 구독
            self._event_bus.subscribe(FileMovedEvent, self._on_file_moved, weak_ref=False)
            self._event_bus.subscribe(FileRenamedEvent, self._on_file_renamed, weak_ref=False)
            self._event_bus.subscribe(FileDeletedEvent, self._on_file_deleted, weak_ref=False)
            self._event_bus.subscribe(
                DirectoryCreatedEvent, self._on_directory_created, weak_ref=False
            )

            self.logger.info("OrganizeViewModel 이벤트 구독 설정 완료")
        except Exception as e:
            self.logger.error(f"OrganizeViewModel 이벤트 구독 설정 실패: {e}")

    # 파일 정리 상태 프로퍼티들
    @pyqtProperty(bool, notify=state_changed)
    def is_organizing(self) -> bool:
        """파일 정리 중인지 여부"""
        return self._organization_state.is_organizing

    @pyqtProperty(str, notify=state_changed)
    def organization_mode(self) -> str:
        """현재 정리 모드"""
        return self._organization_state.organization_mode

    @pyqtProperty(int, notify=state_changed)
    def total_files_to_process(self) -> int:
        """처리할 총 파일 수"""
        return self._organization_state.total_files_to_process

    @pyqtProperty(int, notify=state_changed)
    def processed_files_count(self) -> int:
        """처리된 파일 수"""
        return self._organization_state.processed_files_count

    @pyqtProperty(int, notify=state_changed)
    def successful_operations(self) -> int:
        """성공한 작업 수"""
        return self._organization_state.successful_operations

    @pyqtProperty(int, notify=state_changed)
    def failed_operations(self) -> int:
        """실패한 작업 수"""
        return self._organization_state.failed_operations

    @pyqtProperty(int, notify=state_changed)
    def organization_progress(self) -> int:
        """정리 진행률 (0-100)"""
        return self._organization_state.organization_progress

    @pyqtProperty(str, notify=state_changed)
    def current_operation(self) -> str:
        """현재 작업 유형"""
        return self._organization_state.current_operation

    @pyqtProperty(str, notify=state_changed)
    def current_file(self) -> str:
        """현재 처리 중인 파일"""
        return self._organization_state.current_file

    @pyqtProperty(int, notify=state_changed)
    def files_moved(self) -> int:
        """이동된 파일 수"""
        return self._organization_state.files_moved

    @pyqtProperty(int, notify=state_changed)
    def files_renamed(self) -> int:
        """이름이 변경된 파일 수"""
        return self._organization_state.files_renamed

    @pyqtProperty(int, notify=state_changed)
    def files_deleted(self) -> int:
        """삭제된 파일 수"""
        return self._organization_state.files_deleted

    @pyqtProperty(int, notify=state_changed)
    def directories_created(self) -> int:
        """생성된 디렉토리 수"""
        return self._organization_state.directories_created

    @pyqtProperty(str, notify=state_changed)
    def last_error(self) -> str:
        """마지막 오류 메시지"""
        return self._organization_state.last_error or ""

    # 파일 정리 기능 프로퍼티들
    @pyqtProperty(bool, notify=capabilities_changed)
    def can_start_organization(self) -> bool:
        """파일 정리 시작 가능 여부"""
        return self._organization_capabilities.can_start_organization

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_stop_organization(self) -> bool:
        """파일 정리 중지 가능 여부"""
        return self._organization_capabilities.can_stop_organization

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_pause_organization(self) -> bool:
        """파일 정리 일시정지 가능 여부"""
        return self._organization_capabilities.can_pause_organization

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_resume_organization(self) -> bool:
        """파일 정리 재개 가능 여부"""
        return self._organization_capabilities.can_resume_organization

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_preview_organization(self) -> bool:
        """파일 정리 미리보기 가능 여부"""
        return self._organization_capabilities.can_preview_organization

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_undo_last_operation(self) -> bool:
        """마지막 작업 실행 취소 가능 여부"""
        return self._organization_capabilities.can_undo_last_operation

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_redo_last_operation(self) -> bool:
        """마지막 작업 재실행 가능 여부"""
        return self._organization_capabilities.can_redo_last_operation

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_clear_organization_results(self) -> bool:
        """정리 결과 초기화 가능 여부"""
        return self._organization_capabilities.can_clear_organization_results

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_export_organization_log(self) -> bool:
        """정리 로그 내보내기 가능 여부"""
        return self._organization_capabilities.can_export_organization_log

    # 정리 설정 프로퍼티들
    @pyqtProperty(bool, notify=state_changed)
    def create_directories(self) -> bool:
        """디렉토리 생성 여부"""
        return self._organization_state.create_directories

    @create_directories.setter
    def create_directories(self, value: bool):
        """디렉토리 생성 여부 설정"""
        if self._organization_state.create_directories != value:
            self._organization_state.create_directories = value
            self.state_changed.emit()

    @pyqtProperty(bool, notify=state_changed)
    def overwrite_existing(self) -> bool:
        """기존 파일 덮어쓰기 여부"""
        return self._organization_state.overwrite_existing

    @overwrite_existing.setter
    def overwrite_existing(self, value: bool):
        """기존 파일 덮어쓰기 여부 설정"""
        if self._organization_state.overwrite_existing != value:
            self._organization_state.overwrite_existing = value
            self.state_changed.emit()

    @pyqtProperty(bool, notify=state_changed)
    def use_hard_links(self) -> bool:
        """하드 링크 사용 여부"""
        return self._organization_state.use_hard_links

    @use_hard_links.setter
    def use_hard_links(self, value: bool):
        """하드 링크 사용 여부 설정"""
        if self._organization_state.use_hard_links != value:
            self._organization_state.use_hard_links = value
            self.state_changed.emit()

    @pyqtProperty(bool, notify=state_changed)
    def preserve_timestamps(self) -> bool:
        """타임스탬프 보존 여부"""
        return self._organization_state.preserve_timestamps

    @preserve_timestamps.setter
    def preserve_timestamps(self, value: bool):
        """타임스탬프 보존 여부 설정"""
        if self._organization_state.preserve_timestamps != value:
            self._organization_state.preserve_timestamps = value
            self.state_changed.emit()

    @pyqtProperty(bool, notify=state_changed)
    def backup_before_organize(self) -> bool:
        """정리 전 백업 여부"""
        return self._organization_state.backup_before_organize

    @backup_before_organize.setter
    def backup_before_organize(self, value: bool):
        """정리 전 백업 여부 설정"""
        if self._organization_state.backup_before_organize != value:
            self._organization_state.backup_before_organize = value
            self.state_changed.emit()

    # 공개 메서드들
    def start_organization(self, file_ids: list[UUID], target_directory: str) -> bool:
        """파일 정리 시작"""
        try:
            if not self._file_organization_service:
                self.logger.error("FileOrganizationService가 연결되지 않았습니다")
                return False

            if self._organization_state.is_organizing:
                self.logger.warning("이미 파일 정리 중입니다")
                return False

            # 파일 정리 시작
            success = self._file_organization_service.start_organization(
                file_ids=file_ids,
                target_directory=target_directory,
                mode=self._organization_state.organization_mode,
                create_directories=self._organization_state.create_directories,
                overwrite_existing=self._organization_state.overwrite_existing,
                use_hard_links=self._organization_state.use_hard_links,
                preserve_timestamps=self._organization_state.preserve_timestamps,
                backup_before_organize=self._organization_state.backup_before_organize,
            )

            if success:
                self.logger.info(f"파일 정리 시작: {len(file_ids)}개 파일")
                self._update_capabilities(OrganizationCapabilities.organizing())
                return True
            self.logger.error("파일 정리 시작 실패")
            return False

        except Exception as e:
            self.logger.error(f"파일 정리 시작 중 오류 발생: {e}")
            self._set_error(str(e))
            return False

    def stop_organization(self) -> bool:
        """파일 정리 중지"""
        try:
            if not self._file_organization_service:
                return False

            if not self._organization_state.is_organizing:
                return False

            success = self._file_organization_service.stop_organization(
                self._organization_state.current_organization_id
            )

            if success:
                self.logger.info("파일 정리 중지 요청됨")
                return True
            self.logger.error("파일 정리 중지 실패")
            return False

        except Exception as e:
            self.logger.error(f"파일 정리 중지 중 오류 발생: {e}")
            return False

    def pause_organization(self) -> bool:
        """파일 정리 일시정지"""
        try:
            if not self._file_organization_service:
                return False

            if not self._organization_state.is_organizing:
                return False

            success = self._file_organization_service.pause_organization(
                self._organization_state.current_organization_id
            )

            if success:
                self.logger.info("파일 정리 일시정지됨")
                self._update_capabilities(OrganizationCapabilities.paused())
                return True
            self.logger.error("파일 정리 일시정지 실패")
            return False

        except Exception as e:
            self.logger.error(f"파일 정리 일시정지 중 오류 발생: {e}")
            return False

    def resume_organization(self) -> bool:
        """파일 정리 재개"""
        try:
            if not self._file_organization_service:
                return False

            if self._organization_state.is_organizing:
                return False

            success = self._file_organization_service.resume_organization(
                self._organization_state.current_organization_id
            )

            if success:
                self.logger.info("파일 정리 재개됨")
                self._update_capabilities(OrganizationCapabilities.organizing())
                return True
            self.logger.error("파일 정리 재개 실패")
            return False

        except Exception as e:
            self.logger.error(f"파일 정리 재개 중 오류 발생: {e}")
            return False

    def preview_organization(self, file_ids: list[UUID], target_directory: str) -> dict[str, Any]:
        """파일 정리 미리보기"""
        try:
            if not self._file_organization_service:
                return {}

            preview_result = self._file_organization_service.preview_organization(
                file_ids=file_ids,
                target_directory=target_directory,
                mode=self._organization_state.organization_mode,
            )

            if preview_result:
                self.logger.info("파일 정리 미리보기 완료")
                return preview_result
            self.logger.error("파일 정리 미리보기 실패")
            return {}

        except Exception as e:
            self.logger.error(f"파일 정리 미리보기 중 오류 발생: {e}")
            return {}

    def undo_last_operation(self) -> bool:
        """마지막 작업 실행 취소"""
        try:
            if not self._file_organization_service:
                return False

            success = self._file_organization_service.undo_last_operation()

            if success:
                self.logger.info("마지막 작업 실행 취소됨")
                return True
            self.logger.error("마지막 작업 실행 취소 실패")
            return False

        except Exception as e:
            self.logger.error(f"마지막 작업 실행 취소 중 오류 발생: {e}")
            return False

    def redo_last_operation(self) -> bool:
        """마지막 작업 재실행"""
        try:
            if not self._file_organization_service:
                return False

            success = self._file_organization_service.redo_last_operation()

            if success:
                self.logger.info("마지막 작업 재실행됨")
                return True
            self.logger.error("마지막 작업 재실행 실패")
            return False

        except Exception as e:
            self.logger.error(f"마지막 작업 재실행 중 오류 발생: {e}")
            return False

    def clear_organization_results(self) -> bool:
        """정리 결과 초기화"""
        try:
            # 상태 초기화
            self._organization_state = OrganizationState()
            self._update_capabilities(OrganizationCapabilities())

            self.logger.info("정리 결과 초기화됨")
            self.state_changed.emit()
            return True

        except Exception as e:
            self.logger.error(f"정리 결과 초기화 중 오류 발생: {e}")
            return False

    def export_organization_log(self, file_path: str) -> bool:
        """정리 로그 내보내기"""
        try:
            if not self._file_organization_service:
                return False

            success = self._file_organization_service.export_organization_log(file_path)

            if success:
                self.logger.info(f"정리 로그 내보내기 완료: {file_path}")
                return True
            self.logger.error(f"정리 로그 내보내기 실패: {file_path}")
            return False

        except Exception as e:
            self.logger.error(f"정리 로그 내보내기 중 오류 발생: {e}")
            return False

    def change_organization_mode(self, mode: str) -> bool:
        """정리 모드 변경"""
        try:
            valid_modes = ["simulation", "safe", "normal", "aggressive"]
            if mode not in valid_modes:
                self.logger.error(f"유효하지 않은 정리 모드: {mode}")
                return False

            if self._organization_state.organization_mode != mode:
                self._organization_state.organization_mode = mode
                self.logger.info(f"정리 모드 변경: {mode}")
                self.state_changed.emit()
                return True

            return True

        except Exception as e:
            self.logger.error(f"정리 모드 변경 중 오류 발생: {e}")
            return False

    # 이벤트 핸들러들
    def _on_organization_started(self, event: OrganizationStartedEvent):
        """파일 정리 시작 이벤트 처리"""
        try:
            self._organization_state.is_organizing = True
            self._organization_state.current_organization_id = event.organization_id
            self._organization_state.total_files_to_process = event.total_files
            self._organization_state.processed_files_count = 0
            self._organization_state.organization_progress = 0
            self._update_capabilities(OrganizationCapabilities.organizing())

            # 상태 변경 시그널 발생
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"파일 정리 시작 이벤트 처리 중 오류 발생: {e}")

    def _on_organization_progress(self, event: OrganizationProgressEvent):
        """파일 정리 진행률 이벤트 처리"""
        try:
            if event.organization_id != self._organization_state.current_organization_id:
                return

            self._organization_state.processed_files_count = event.processed_files
            self._organization_state.organization_progress = event.progress_percent
            self._organization_state.current_operation = event.current_operation
            self._organization_state.current_file = event.current_file

            # 진행률 변경 시그널 발생
            self.organization_progress_changed.emit(event.progress_percent)
            self.current_operation_changed.emit(event.current_operation)
            self.current_file_changed.emit(event.current_file)

        except Exception as e:
            self.logger.error(f"파일 정리 진행률 이벤트 처리 중 오류 발생: {e}")

    def _on_organization_completed(self, event: OrganizationCompletedEvent):
        """파일 정리 완료 이벤트 처리"""
        try:
            if event.organization_id != self._organization_state.current_organization_id:
                return

            self._organization_state.is_organizing = False
            self._organization_state.organization_progress = 100
            self._organization_state.successful_operations = event.successful_operations
            self._organization_state.failed_operations = event.failed_operations
            self._update_capabilities(OrganizationCapabilities.completed())

            # UI 업데이트 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(
                    SuccessMessageEvent(
                        message=f"파일 정리 완료: {event.successful_operations}개 성공"
                    )
                )

            # 상태 변경 시그널 발생
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"파일 정리 완료 이벤트 처리 중 오류 발생: {e}")

    def _on_organization_failed(self, event: OrganizationFailedEvent):
        """파일 정리 실패 이벤트 처리"""
        try:
            if event.organization_id != self._organization_state.current_organization_id:
                return

            self._organization_state.is_organizing = False
            self._organization_state.last_error = event.error_message
            self._organization_state.error_count += 1
            self._update_capabilities(OrganizationCapabilities.error())

            # 오류 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(
                    ErrorMessageEvent(message=f"파일 정리 실패: {event.error_message}")
                )

            # 상태 변경 시그널 발생
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"파일 정리 실패 이벤트 처리 중 오류 발생: {e}")

    def _on_organization_cancelled(self, event: OrganizationCancelledEvent):
        """파일 정리 취소 이벤트 처리"""
        try:
            if event.organization_id != self._organization_state.current_organization_id:
                return

            self._organization_state.is_organizing = False
            self._organization_state.organization_progress = 0
            self._update_capabilities(OrganizationCapabilities())

            # 취소 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(StatusBarUpdateEvent(message="파일 정리가 취소되었습니다"))

            # 상태 변경 시그널 발생
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"파일 정리 취소 이벤트 처리 중 오류 발생: {e}")

    def _on_file_moved(self, event: FileMovedEvent):
        """파일 이동 이벤트 처리"""
        try:
            self._organization_state.files_moved += 1
            self._organization_state.successful_operations += 1

            # 작업 결과 변경 시그널 발생
            self.operation_result_changed.emit("move", "success")
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"파일 이동 이벤트 처리 중 오류 발생: {e}")

    def _on_file_renamed(self, event: FileRenamedEvent):
        """파일 이름 변경 이벤트 처리"""
        try:
            self._organization_state.files_renamed += 1
            self._organization_state.successful_operations += 1

            # 작업 결과 변경 시그널 발생
            self.operation_result_changed.emit("rename", "success")
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"파일 이름 변경 이벤트 처리 중 오류 발생: {e}")

    def _on_file_deleted(self, event: FileDeletedEvent):
        """파일 삭제 이벤트 처리"""
        try:
            self._organization_state.files_deleted += 1
            self._organization_state.successful_operations += 1

            # 작업 결과 변경 시그널 발생
            self.operation_result_changed.emit("delete", "success")
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"파일 삭제 이벤트 처리 중 오류 발생: {e}")

    def _on_directory_created(self, event: DirectoryCreatedEvent):
        """디렉토리 생성 이벤트 처리"""
        try:
            self._organization_state.directories_created += 1
            self._organization_state.successful_operations += 1

            # 작업 결과 변경 시그널 발생
            self.operation_result_changed.emit("create_directory", "success")
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"디렉토리 생성 이벤트 처리 중 오류 발생: {e}")

    # 내부 헬퍼 메서드들
    def _update_capabilities(self, new_capabilities: OrganizationCapabilities):
        """UI 기능 상태 업데이트"""
        if self._organization_capabilities != new_capabilities:
            self._organization_capabilities = new_capabilities
            self.capabilities_changed.emit()

    def _set_error(self, error_message: str):
        """오류 상태 설정"""
        self._organization_state.last_error = error_message
        self._organization_state.error_count += 1
        self.error_occurred.emit(error_message)
        self.state_changed.emit()

    def get_organization_summary(self) -> dict[str, Any]:
        """파일 정리 요약 정보 반환"""
        return {
            "is_organizing": self._organization_state.is_organizing,
            "organization_mode": self._organization_state.organization_mode,
            "total_files_to_process": self._organization_state.total_files_to_process,
            "processed_files_count": self._organization_state.processed_files_count,
            "successful_operations": self._organization_state.successful_operations,
            "failed_operations": self._organization_state.failed_operations,
            "skipped_operations": self._organization_state.skipped_operations,
            "organization_progress": self._organization_state.organization_progress,
            "current_operation": self._organization_state.current_operation,
            "current_file": self._organization_state.current_file,
            "files_moved": self._organization_state.files_moved,
            "files_renamed": self._organization_state.files_renamed,
            "files_deleted": self._organization_state.files_deleted,
            "directories_created": self._organization_state.directories_created,
            "last_error": self._organization_state.last_error,
            "error_count": self._organization_state.error_count,
        }
