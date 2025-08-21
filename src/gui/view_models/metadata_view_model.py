"""
MetadataViewModel - 메타데이터 관리에 특화된 ViewModel

Phase 2 MVVM 아키텍처의 일부로, 미디어 파일의 메타데이터 관리 기능을 담당합니다.
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from app import (
    IMediaDataService,
    ITMDBSearchService,
    IUIUpdateService,
    # 이벤트
    MediaDataUpdatedEvent,
    # 도메인 모델
    MediaType,
    SuccessMessageEvent,
    TableDataUpdateEvent,
    TMDBMatchFoundEvent,
    TMDBMatchNotFoundEvent,
    # 인프라
    TypedEventBus,
    get_event_bus,
    get_service,
)


@dataclass
class MetadataState:
    """메타데이터 상태 정보"""

    # 메타데이터 동기화 상태
    is_syncing_metadata: bool = False
    current_sync_id: UUID | None = None

    # TMDB 검색 상태
    is_searching_tmdb: bool = False
    current_search_id: UUID | None = None

    # 메타데이터 품질 상태
    total_files: int = 0
    files_with_metadata: int = 0
    files_without_metadata: int = 0
    files_with_complete_metadata: int = 0
    files_with_partial_metadata: int = 0

    # TMDB 매칭 상태
    tmdb_matches_found: int = 0
    tmdb_matches_not_found: int = 0
    tmdb_search_progress: int = 0

    # 진행률
    metadata_sync_progress: int = 0
    current_sync_step: str = ""

    # 오류 정보
    last_error: str | None = None
    error_count: int = 0

    # 메타데이터 품질 점수
    overall_metadata_quality: float = 0.0  # 0.0 - 100.0


@dataclass
class MetadataCapabilities:
    """메타데이터 관련 UI 기능들"""

    can_sync_metadata: bool = True
    can_stop_metadata_sync: bool = False
    can_search_tmdb: bool = True
    can_stop_tmdb_search: bool = False
    can_edit_metadata: bool = True
    can_batch_edit_metadata: bool = True
    can_export_metadata: bool = False
    can_import_metadata: bool = True
    can_validate_metadata: bool = True

    @classmethod
    def syncing(cls) -> "MetadataCapabilities":
        """메타데이터 동기화 중일 때의 기능 상태"""
        return cls(
            can_sync_metadata=False,
            can_stop_metadata_sync=True,
            can_search_tmdb=False,
            can_stop_tmdb_search=False,
            can_edit_metadata=False,
            can_batch_edit_metadata=False,
            can_export_metadata=False,
            can_import_metadata=False,
            can_validate_metadata=False,
        )

    @classmethod
    def searching_tmdb(cls) -> "MetadataCapabilities":
        """TMDB 검색 중일 때의 기능 상태"""
        return cls(
            can_sync_metadata=False,
            can_stop_metadata_sync=False,
            can_search_tmdb=False,
            can_stop_tmdb_search=True,
            can_edit_metadata=False,
            can_batch_edit_metadata=False,
            can_export_metadata=False,
            can_import_metadata=False,
            can_validate_metadata=False,
        )

    @classmethod
    def ready(cls) -> "MetadataCapabilities":
        """준비 상태의 기능"""
        return cls(
            can_sync_metadata=True,
            can_stop_metadata_sync=False,
            can_search_tmdb=True,
            can_stop_tmdb_search=False,
            can_edit_metadata=True,
            can_batch_edit_metadata=True,
            can_export_metadata=True,
            can_import_metadata=True,
            can_validate_metadata=True,
        )


class MetadataViewModel(QObject):
    """메타데이터 관리 전용 ViewModel"""

    # 시그널 정의
    state_changed = pyqtSignal()
    capabilities_changed = pyqtSignal()
    metadata_sync_progress_changed = pyqtSignal(int)
    tmdb_search_progress_changed = pyqtSignal(int)
    metadata_quality_changed = pyqtSignal(float)
    files_count_changed = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # 로깅 설정
        self.logger = logging.getLogger(__name__)

        # 상태 초기화
        self._metadata_state = MetadataState()
        self._metadata_capabilities = MetadataCapabilities()

        # 서비스 연결
        self._event_bus: TypedEventBus | None = None
        self._media_data_service: IMediaDataService | None = None
        self._tmdb_search_service: ITMDBSearchService | None = None
        self._ui_update_service: IUIUpdateService | None = None

        # 초기화
        self._setup_services()
        self._setup_event_subscriptions()

        self.logger.info("MetadataViewModel 초기화 완료")

    def _setup_services(self):
        """필요한 서비스들을 설정"""
        try:
            self._event_bus = get_event_bus()
            self._media_data_service = get_service(IMediaDataService)
            self._tmdb_search_service = get_service(ITMDBSearchService)
            self._ui_update_service = get_service(IUIUpdateService)

            self.logger.info("MetadataViewModel 서비스 연결 완료")
        except Exception as e:
            self.logger.error(f"MetadataViewModel 서비스 연결 실패: {e}")

    def _setup_event_subscriptions(self):
        """이벤트 구독 설정"""
        if not self._event_bus:
            return

        try:
            # 메타데이터 관련 이벤트 구독
            self._event_bus.subscribe(
                MediaDataUpdatedEvent, self._on_metadata_updated, weak_ref=False
            )

            # TMDB 관련 이벤트 구독
            self._event_bus.subscribe(
                TMDBMatchFoundEvent, self._on_tmdb_match_found, weak_ref=False
            )
            self._event_bus.subscribe(
                TMDBMatchNotFoundEvent, self._on_tmdb_match_not_found, weak_ref=False
            )

            self.logger.info("MetadataViewModel 이벤트 구독 설정 완료")
        except Exception as e:
            self.logger.error(f"MetadataViewModel 이벤트 구독 설정 실패: {e}")

    # 메타데이터 상태 프로퍼티들
    @pyqtProperty(bool, notify=state_changed)
    def is_syncing_metadata(self) -> bool:
        """메타데이터 동기화 중인지 여부"""
        return self._metadata_state.is_syncing_metadata

    @pyqtProperty(bool, notify=state_changed)
    def is_searching_tmdb(self) -> bool:
        """TMDB 검색 중인지 여부"""
        return self._metadata_state.is_searching_tmdb

    @pyqtProperty(int, notify=state_changed)
    def total_files(self) -> int:
        """총 파일 수"""
        return self._metadata_state.total_files

    @pyqtProperty(int, notify=state_changed)
    def files_with_metadata(self) -> int:
        """메타데이터가 있는 파일 수"""
        return self._metadata_state.files_with_metadata

    @pyqtProperty(int, notify=state_changed)
    def files_without_metadata(self) -> int:
        """메타데이터가 없는 파일 수"""
        return self._metadata_state.files_without_metadata

    @pyqtProperty(int, notify=state_changed)
    def files_with_complete_metadata(self) -> int:
        """완전한 메타데이터가 있는 파일 수"""
        return self._metadata_state.files_with_complete_metadata

    @pyqtProperty(int, notify=state_changed)
    def files_with_partial_metadata(self) -> int:
        """부분적인 메타데이터가 있는 파일 수"""
        return self._metadata_state.files_with_partial_metadata

    @pyqtProperty(int, notify=state_changed)
    def tmdb_matches_found(self) -> int:
        """TMDB에서 매칭된 파일 수"""
        return self._metadata_state.tmdb_matches_found

    @pyqtProperty(int, notify=state_changed)
    def tmdb_matches_not_found(self) -> int:
        """TMDB에서 매칭되지 않은 파일 수"""
        return self._metadata_state.tmdb_matches_not_found

    @pyqtProperty(int, notify=state_changed)
    def metadata_sync_progress(self) -> int:
        """메타데이터 동기화 진행률 (0-100)"""
        return self._metadata_state.metadata_sync_progress

    @pyqtProperty(int, notify=state_changed)
    def tmdb_search_progress(self) -> int:
        """TMDB 검색 진행률 (0-100)"""
        return self._metadata_state.tmdb_search_progress

    @pyqtProperty(str, notify=state_changed)
    def current_sync_step(self) -> str:
        """현재 동기화 단계"""
        return self._metadata_state.current_sync_step

    @pyqtProperty(float, notify=state_changed)
    def overall_metadata_quality(self) -> float:
        """전체 메타데이터 품질 점수 (0.0-100.0)"""
        return self._metadata_state.overall_metadata_quality

    @pyqtProperty(str, notify=state_changed)
    def last_error(self) -> str:
        """마지막 오류 메시지"""
        return self._metadata_state.last_error or ""

    # 메타데이터 기능 프로퍼티들
    @pyqtProperty(bool, notify=capabilities_changed)
    def can_sync_metadata(self) -> bool:
        """메타데이터 동기화 가능 여부"""
        return self._metadata_capabilities.can_sync_metadata

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_stop_metadata_sync(self) -> bool:
        """메타데이터 동기화 중지 가능 여부"""
        return self._metadata_capabilities.can_stop_metadata_sync

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_search_tmdb(self) -> bool:
        """TMDB 검색 가능 여부"""
        return self._metadata_capabilities.can_search_tmdb

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_stop_tmdb_search(self) -> bool:
        """TMDB 검색 중지 가능 여부"""
        return self._metadata_capabilities.can_stop_tmdb_search

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_edit_metadata(self) -> bool:
        """메타데이터 편집 가능 여부"""
        return self._metadata_capabilities.can_edit_metadata

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_batch_edit_metadata(self) -> bool:
        """일괄 메타데이터 편집 가능 여부"""
        return self._metadata_capabilities.can_batch_edit_metadata

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_export_metadata(self) -> bool:
        """메타데이터 내보내기 가능 여부"""
        return self._metadata_capabilities.can_export_metadata

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_import_metadata(self) -> bool:
        """메타데이터 가져오기 가능 여부"""
        return self._metadata_capabilities.can_import_metadata

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_validate_metadata(self) -> bool:
        """메타데이터 검증 가능 여부"""
        return self._metadata_capabilities.can_validate_metadata

    # 공개 메서드들
    def sync_metadata(self, file_ids: list[UUID] | None = None) -> bool:
        """메타데이터 동기화 시작"""
        try:
            if not self._media_data_service:
                self.logger.error("MediaDataService가 연결되지 않았습니다")
                return False

            if self._metadata_state.is_syncing_metadata:
                self.logger.warning("이미 메타데이터 동기화 중입니다")
                return False

            # 메타데이터 동기화 시작
            success = self._media_data_service.sync_metadata(file_ids)

            if success:
                self.logger.info("메타데이터 동기화 시작")
                self._update_capabilities(MetadataCapabilities.syncing())
                return True
            self.logger.error("메타데이터 동기화 시작 실패")
            return False

        except Exception as e:
            self.logger.error(f"메타데이터 동기화 시작 중 오류 발생: {e}")
            self._set_error(str(e))
            return False

    def stop_metadata_sync(self) -> bool:
        """메타데이터 동기화 중지"""
        try:
            if not self._media_data_service:
                return False

            if not self._metadata_state.is_syncing_metadata:
                return False

            success = self._media_data_service.stop_metadata_sync(
                self._metadata_state.current_sync_id
            )

            if success:
                self.logger.info("메타데이터 동기화 중지 요청됨")
                return True
            self.logger.error("메타데이터 동기화 중지 실패")
            return False

        except Exception as e:
            self.logger.error(f"메타데이터 동기화 중지 중 오류 발생: {e}")
            return False

    def search_tmdb(self, query: str, media_type: MediaType | None = None) -> bool:
        """TMDB 검색 시작"""
        try:
            if not self._tmdb_search_service:
                self.logger.error("TMDBSearchService가 연결되지 않았습니다")
                return False

            if self._metadata_state.is_searching_tmdb:
                self.logger.warning("이미 TMDB 검색 중입니다")
                return False

            # TMDB 검색 시작
            success = self._tmdb_search_service.search(query, media_type)

            if success:
                self.logger.info(f"TMDB 검색 시작: {query}")
                self._update_capabilities(MetadataCapabilities.searching_tmdb())
                return True
            self.logger.error(f"TMDB 검색 시작 실패: {query}")
            return False

        except Exception as e:
            self.logger.error(f"TMDB 검색 시작 중 오류 발생: {e}")
            self._set_error(str(e))
            return False

    def stop_tmdb_search(self) -> bool:
        """TMDB 검색 중지"""
        try:
            if not self._tmdb_search_service:
                return False

            if not self._metadata_state.is_searching_tmdb:
                return False

            success = self._tmdb_search_service.stop_search(self._metadata_state.current_search_id)

            if success:
                self.logger.info("TMDB 검색 중지 요청됨")
                return True
            self.logger.error("TMDB 검색 중지 실패")
            return False

        except Exception as e:
            self.logger.error(f"TMDB 검색 중지 중 오류 발생: {e}")
            return False

    def edit_metadata(self, file_id: UUID, metadata: dict[str, Any]) -> bool:
        """개별 파일 메타데이터 편집"""
        try:
            if not self._media_data_service:
                return False

            success = self._media_data_service.update_metadata(file_id, metadata)

            if success:
                self.logger.info(f"메타데이터 편집 완료: {file_id}")
                return True
            self.logger.error(f"메타데이터 편집 실패: {file_id}")
            return False

        except Exception as e:
            self.logger.error(f"메타데이터 편집 중 오류 발생: {e}")
            return False

    def batch_edit_metadata(self, file_ids: list[UUID], metadata: dict[str, Any]) -> bool:
        """여러 파일 메타데이터 일괄 편집"""
        try:
            if not self._media_data_service:
                return False

            success = self._media_data_service.batch_update_metadata(file_ids, metadata)

            if success:
                self.logger.info(f"일괄 메타데이터 편집 완료: {len(file_ids)}개 파일")
                return True
            self.logger.error(f"일괄 메타데이터 편집 실패: {len(file_ids)}개 파일")
            return False

        except Exception as e:
            self.logger.error(f"일괄 메타데이터 편집 중 오류 발생: {e}")
            return False

    def export_metadata(self, file_path: str, file_ids: list[UUID] | None = None) -> bool:
        """메타데이터 내보내기"""
        try:
            if not self._media_data_service:
                return False

            success = self._media_data_service.export_metadata(file_path, file_ids)

            if success:
                self.logger.info(f"메타데이터 내보내기 완료: {file_path}")
                return True
            self.logger.error(f"메타데이터 내보내기 실패: {file_path}")
            return False

        except Exception as e:
            self.logger.error(f"메타데이터 내보내기 중 오류 발생: {e}")
            return False

    def import_metadata(self, file_path: str) -> bool:
        """메타데이터 가져오기"""
        try:
            if not self._media_data_service:
                return False

            success = self._media_data_service.import_metadata(file_path)

            if success:
                self.logger.info(f"메타데이터 가져오기 완료: {file_path}")
                return True
            self.logger.error(f"메타데이터 가져오기 실패: {file_path}")
            return False

        except Exception as e:
            self.logger.error(f"메타데이터 가져오기 중 오류 발생: {e}")
            return False

    def validate_metadata(self, file_ids: list[UUID] | None = None) -> dict[str, Any]:
        """메타데이터 검증"""
        try:
            if not self._media_data_service:
                return {}

            validation_result = self._media_data_service.validate_metadata(file_ids)

            if validation_result:
                self.logger.info("메타데이터 검증 완료")
                return validation_result
            self.logger.error("메타데이터 검증 실패")
            return {}

        except Exception as e:
            self.logger.error(f"메타데이터 검증 중 오류 발생: {e}")
            return {}

    def refresh_metadata_stats(self) -> bool:
        """메타데이터 통계 새로고침"""
        try:
            if not self._media_data_service:
                return False

            stats = self._media_data_service.get_metadata_stats()

            if stats:
                self._metadata_state.total_files = stats.get("total_files", 0)
                self._metadata_state.files_with_metadata = stats.get("files_with_metadata", 0)
                self._metadata_state.files_without_metadata = stats.get("files_without_metadata", 0)
                self._metadata_state.files_with_complete_metadata = stats.get(
                    "files_with_complete_metadata", 0
                )
                self._metadata_state.files_with_partial_metadata = stats.get(
                    "files_with_partial_metadata", 0
                )
                self._metadata_state.overall_metadata_quality = stats.get("overall_quality", 0.0)

                # 상태 변경 시그널 발생
                self.state_changed.emit()
                self.metadata_quality_changed.emit(self._metadata_state.overall_metadata_quality)

                self.logger.info("메타데이터 통계 새로고침 완료")
                return True
            self.logger.error("메타데이터 통계 새로고침 실패")
            return False

        except Exception as e:
            self.logger.error(f"메타데이터 통계 새로고침 중 오류 발생: {e}")
            return False

    # 이벤트 핸들러들
    def _on_metadata_updated(self, event: MediaDataUpdatedEvent):
        """메타데이터 업데이트 이벤트 처리"""
        try:
            # 통계 새로고침
            self.refresh_metadata_stats()

            # UI 업데이트 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(TableDataUpdateEvent())
                self._event_bus.publish(
                    SuccessMessageEvent(message="메타데이터가 업데이트되었습니다")
                )

        except Exception as e:
            self.logger.error(f"메타데이터 업데이트 이벤트 처리 중 오류 발생: {e}")

    def _on_tmdb_match_found(self, event: TMDBMatchFoundEvent):
        """TMDB 매칭 발견 이벤트 처리"""
        try:
            self._metadata_state.tmdb_matches_found += 1

            # UI 업데이트 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(
                    SuccessMessageEvent(message=f"TMDB 매칭 발견: {event.title}")
                )

            # 상태 변경 시그널 발생
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"TMDB 매칭 발견 이벤트 처리 중 오류 발생: {e}")

    def _on_tmdb_match_not_found(self, event: TMDBMatchNotFoundEvent):
        """TMDB 매칭 실패 이벤트 처리"""
        try:
            self._metadata_state.tmdb_matches_not_found += 1

            # 상태 변경 시그널 발생
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"TMDB 매칭 실패 이벤트 처리 중 오류 발생: {e}")

    # 내부 헬퍼 메서드들
    def _update_capabilities(self, new_capabilities: MetadataCapabilities):
        """UI 기능 상태 업데이트"""
        if self._metadata_capabilities != new_capabilities:
            self._metadata_capabilities = new_capabilities
            self.capabilities_changed.emit()

    def _set_error(self, error_message: str):
        """오류 상태 설정"""
        self._metadata_state.last_error = error_message
        self._metadata_state.error_count += 1
        self.error_occurred.emit(error_message)
        self.state_changed.emit()

    def get_metadata_summary(self) -> dict[str, Any]:
        """메타데이터 요약 정보 반환"""
        return {
            "is_syncing_metadata": self._metadata_state.is_syncing_metadata,
            "is_searching_tmdb": self._metadata_state.is_searching_tmdb,
            "total_files": self._metadata_state.total_files,
            "files_with_metadata": self._metadata_state.files_with_metadata,
            "files_without_metadata": self._metadata_state.files_without_metadata,
            "files_with_complete_metadata": self._metadata_state.files_with_complete_metadata,
            "files_with_partial_metadata": self._metadata_state.files_with_partial_metadata,
            "tmdb_matches_found": self._metadata_state.tmdb_matches_found,
            "tmdb_matches_not_found": self._metadata_state.tmdb_matches_not_found,
            "metadata_sync_progress": self._metadata_state.metadata_sync_progress,
            "tmdb_search_progress": self._metadata_state.tmdb_search_progress,
            "overall_metadata_quality": self._metadata_state.overall_metadata_quality,
            "current_sync_step": self._metadata_state.current_sync_step,
            "last_error": self._metadata_state.last_error,
            "error_count": self._metadata_state.error_count,
        }
