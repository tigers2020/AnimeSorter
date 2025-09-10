"""
미디어 데이터 관리 서비스

파싱된 미디어 파일 데이터의 관리, 그룹화, 필터링을 담당하는 서비스입니다.
MainWindow의 AnimeDataManager 역할을 대체합니다.
"""

import logging

logger = logging.getLogger(__name__)
import time
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID, uuid4

from src.app.domain import MediaFile, MediaGroup
from src.app.events import TypedEventBus
from src.app.media_data_events import (MediaDataClearedEvent,
                                       MediaDataErrorEvent,
                                       MediaDataExportCompletedEvent,
                                       MediaDataExportStartedEvent,
                                       MediaDataFilter,
                                       MediaDataFilteringCompletedEvent,
                                       MediaDataFilteringStartedEvent,
                                       MediaDataGrouping,
                                       MediaDataGroupingCompletedEvent,
                                       MediaDataGroupingStartedEvent,
                                       MediaDataLoadStartedEvent,
                                       MediaDataParsingCompletedEvent,
                                       MediaDataReadyEvent,
                                       MediaDataStatistics, MediaDataStatus,
                                       MediaDataUpdatedEvent)
from src.app.services.media import (MediaExporter, MediaExtractor, MediaFilter,
                                    MediaProcessor)


class IMediaDataService(ABC):
    """미디어 데이터 서비스 인터페이스"""

    @abstractmethod
    def load_media_files(self, file_paths: list[Path]) -> UUID:
        """미디어 파일들을 로드하고 파싱"""

    @abstractmethod
    def add_media_file(self, media_file: MediaFile) -> bool:
        """단일 미디어 파일 추가"""

    @abstractmethod
    def remove_media_file(self, file_id: UUID) -> bool:
        """미디어 파일 제거"""

    @abstractmethod
    def update_media_file(self, media_file: MediaFile) -> bool:
        """미디어 파일 업데이트"""

    @abstractmethod
    def get_media_file(self, file_id: UUID) -> MediaFile | None:
        """미디어 파일 조회"""

    @abstractmethod
    def get_all_media_files(self) -> list[MediaFile]:
        """모든 미디어 파일 조회"""

    @abstractmethod
    def create_groups(self, grouping_config: MediaDataGrouping) -> UUID:
        """미디어 파일들을 그룹화"""

    @abstractmethod
    def get_groups(self) -> dict[str, MediaGroup]:
        """현재 그룹들 조회"""

    @abstractmethod
    def get_group(self, group_id: str) -> MediaGroup | None:
        """특정 그룹 조회"""

    @abstractmethod
    def apply_filters(self, filters: list[MediaDataFilter]) -> UUID:
        """필터 적용"""

    @abstractmethod
    def clear_filters(self) -> None:
        """필터 초기화"""

    @abstractmethod
    def get_statistics(self) -> MediaDataStatistics:
        """통계 정보 조회"""

    @abstractmethod
    def clear_data(self) -> None:
        """모든 데이터 초기화"""

    @abstractmethod
    def export_data(self, export_path: Path, format: str = "json") -> UUID:
        """데이터 내보내기"""

    @abstractmethod
    def dispose(self) -> None:
        """서비스 정리"""


class MediaDataService(IMediaDataService):
    """미디어 데이터 서비스 구현"""

    def __init__(self, event_bus: TypedEventBus):
        self.event_bus = event_bus
        self.logger = logging.getLogger(self.__class__.__name__)
        self.media_extractor = MediaExtractor()
        self.media_processor = MediaProcessor()
        self.media_filter = MediaFilter()
        self.media_exporter = MediaExporter()
        self._media_files: dict[UUID, MediaFile] = {}
        self._groups: dict[str, MediaGroup] = {}
        self._filtered_files: set[UUID] = set()
        self._current_filters: list[MediaDataFilter] = []
        self._current_grouping: MediaDataGrouping | None = None
        self._status = MediaDataStatus.READY
        self._is_filtered = False
        self._is_grouped = False
        self.logger.info("MediaDataService 초기화 완료")

    def load_media_files(self, file_paths: list[Path]) -> UUID:
        """미디어 파일들을 로드하고 파싱"""
        operation_id = uuid4()
        try:
            self.logger.info(f"미디어 파일 로드 시작: {len(file_paths)}개 파일")
            self.event_bus.publish(
                MediaDataLoadStartedEvent(
                    operation_id=operation_id, file_paths=file_paths, total_files=len(file_paths)
                )
            )
            self._status = MediaDataStatus.PARSING
            start_time = time.time()
            parsed_files = self.media_extractor.extract_batch(file_paths)
            processed_files = self.media_processor.process_media_files(parsed_files)
            for media_file in processed_files:
                self._media_files[media_file.id] = media_file
            parsing_duration = time.time() - start_time
            self.event_bus.publish(
                MediaDataParsingCompletedEvent(
                    operation_id=operation_id,
                    parsed_files=processed_files,
                    failed_files=[],
                    parsing_errors=[],
                    parsing_duration_seconds=parsing_duration,
                )
            )
            self._status = MediaDataStatus.READY
            self.event_bus.publish(
                MediaDataReadyEvent(
                    operation_id=operation_id,
                    total_files=len(self._media_files),
                    total_groups=len(self._groups),
                    statistics=self.get_statistics(),
                    is_filtered=self._is_filtered,
                    is_grouped=self._is_grouped,
                )
            )
            self.logger.info(f"미디어 파일 로드 완료: {len(processed_files)}개 성공")
            return operation_id
        except Exception as e:
            self.logger.error(f"미디어 파일 로드 실패: {e}")
            self._status = MediaDataStatus.ERROR
            self.event_bus.publish(
                MediaDataErrorEvent(
                    operation_id=operation_id,
                    error_type="parsing_error",
                    error_message=str(e),
                    failed_operation=MediaDataStatus.PARSING,
                    error_details={"file_paths": [str(p) for p in file_paths]},
                )
            )
            raise

    def add_media_file(self, media_file: MediaFile) -> bool:
        """단일 미디어 파일 추가"""
        try:
            normalized_file = self.media_processor.normalize_media_file(media_file)
            self._media_files[normalized_file.id] = normalized_file
            self.event_bus.publish(
                MediaDataUpdatedEvent(updated_files=[normalized_file], update_type="added")
            )
            self.logger.debug(f"미디어 파일 추가됨: {normalized_file.original_name}")
            return True
        except Exception as e:
            self.logger.error(f"미디어 파일 추가 실패: {e}")
            return False

    def remove_media_file(self, file_id: UUID) -> bool:
        """미디어 파일 제거"""
        try:
            if file_id in self._media_files:
                removed_file = self._media_files.pop(file_id)
                self._filtered_files.discard(file_id)
                self._remove_file_from_groups(file_id)
                self.event_bus.publish(
                    MediaDataUpdatedEvent(updated_files=[removed_file], update_type="removed")
                )
                self.logger.debug(f"미디어 파일 제거됨: {removed_file.original_name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"미디어 파일 제거 실패: {e}")
            return False

    def update_media_file(self, media_file: MediaFile) -> bool:
        """미디어 파일 업데이트"""
        try:
            if media_file.id in self._media_files:
                normalized_file = self.media_processor.normalize_media_file(media_file)
                self._media_files[normalized_file.id] = normalized_file
                self._update_file_in_groups(normalized_file)
                self.event_bus.publish(
                    MediaDataUpdatedEvent(updated_files=[normalized_file], update_type="modified")
                )
                self.logger.debug(f"미디어 파일 업데이트됨: {normalized_file.original_name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"미디어 파일 업데이트 실패: {e}")
            return False

    def get_media_file(self, file_id: UUID) -> MediaFile | None:
        """미디어 파일 조회"""
        return self._media_files.get(file_id)

    def get_all_media_files(self) -> list[MediaFile]:
        """모든 미디어 파일 조회"""
        if self._is_filtered:
            return [
                self._media_files[file_id]
                for file_id in self._filtered_files
                if file_id in self._media_files
            ]
        return list(self._media_files.values())

    def create_groups(self, grouping_config: MediaDataGrouping) -> UUID:
        """미디어 파일들을 그룹화"""
        operation_id = uuid4()
        try:
            self.logger.info(f"그룹화 시작: {grouping_config.strategy}")
            self.event_bus.publish(
                MediaDataGroupingStartedEvent(
                    operation_id=operation_id,
                    grouping_config=grouping_config,
                    total_files=len(self._media_files),
                )
            )
            self._status = MediaDataStatus.GROUPING
            start_time = time.time()
            self._groups.clear()
            self._current_grouping = grouping_config
            files_to_group = self.get_all_media_files()
            strategy = (
                grouping_config.strategy.value
                if hasattr(grouping_config.strategy, "value")
                else str(grouping_config.strategy)
            )
            self._groups = self.media_processor.create_media_groups(files_to_group, strategy)
            grouping_duration = time.time() - start_time
            self.event_bus.publish(
                MediaDataGroupingCompletedEvent(
                    operation_id=operation_id,
                    groups=self._groups,
                    grouping_duration_seconds=grouping_duration,
                    statistics=self.get_statistics(),
                )
            )
            self._status = MediaDataStatus.READY
            self._is_grouped = True
            self.logger.info(f"그룹화 완료: {len(self._groups)}개 그룹 생성")
            return operation_id
        except Exception as e:
            self.logger.error(f"그룹화 실패: {e}")
            self._status = MediaDataStatus.ERROR
            self.event_bus.publish(
                MediaDataErrorEvent(
                    operation_id=operation_id,
                    error_type="grouping_error",
                    error_message=str(e),
                    failed_operation=MediaDataStatus.GROUPING,
                )
            )
            raise

    def get_groups(self) -> dict[str, MediaGroup]:
        """현재 그룹들 조회"""
        return self._groups.copy()

    def get_group(self, group_id: str) -> MediaGroup | None:
        """특정 그룹 조회"""
        return self._groups.get(group_id)

    def apply_filters(self, filters: list[MediaDataFilter]) -> UUID:
        """필터 적용"""
        operation_id = uuid4()
        try:
            self.logger.info(f"필터링 시작: {len(filters)}개 필터")
            total_items = len(self._media_files)
            self.event_bus.publish(
                MediaDataFilteringStartedEvent(
                    operation_id=operation_id, filters=filters, total_items=total_items
                )
            )
            self._status = MediaDataStatus.FILTERING
            start_time = time.time()
            self._current_filters = filters
            filtered_file_ids = self.media_filter.apply_filters(
                list(self._media_files.values()), filters
            )
            self._filtered_files = set(filtered_file_ids)
            filtered_files = [self._media_files[file_id] for file_id in filtered_file_ids]
            filtered_groups = self.media_filter.create_filtered_groups(
                self._groups, self._filtered_files
            )
            filtering_duration = time.time() - start_time
            self.event_bus.publish(
                MediaDataFilteringCompletedEvent(
                    operation_id=operation_id,
                    filtered_files=filtered_files,
                    filtered_groups=filtered_groups,
                    filter_duration_seconds=filtering_duration,
                    items_before_filter=total_items,
                    items_after_filter=len(filtered_files),
                )
            )
            self._status = MediaDataStatus.READY
            self._is_filtered = True
            self.logger.info(f"필터링 완료: {total_items}개 → {len(filtered_files)}개")
            return operation_id
        except Exception as e:
            self.logger.error(f"필터링 실패: {e}")
            self._status = MediaDataStatus.ERROR
            self.event_bus.publish(
                MediaDataErrorEvent(
                    operation_id=operation_id,
                    error_type="filtering_error",
                    error_message=str(e),
                    failed_operation=MediaDataStatus.FILTERING,
                )
            )
            raise

    def clear_filters(self) -> None:
        """필터 초기화"""
        self._filtered_files.clear()
        self._current_filters.clear()
        self._is_filtered = False
        self.logger.info("필터 초기화됨")

    def get_statistics(self) -> MediaDataStatistics:
        """통계 정보 조회"""
        stats_data = self.media_processor.calculate_statistics(
            self.get_all_media_files(), self._groups
        )
        return MediaDataStatistics(
            total_files=stats_data["total_files"],
            total_groups=stats_data["total_groups"],
            files_by_type=stats_data["files_by_type"],
            files_by_quality=stats_data["files_by_quality"],
            files_by_source=stats_data["files_by_source"],
            total_size_bytes=stats_data["total_size_bytes"],
            average_file_size_mb=stats_data["average_file_size_mb"],
            largest_file_size_mb=stats_data["largest_file_size_mb"],
            smallest_file_size_mb=stats_data["smallest_file_size_mb"],
        )

    def clear_data(self) -> None:
        """모든 데이터 초기화"""
        previous_files = len(self._media_files)
        previous_groups = len(self._groups)
        self._media_files.clear()
        self._groups.clear()
        self._filtered_files.clear()
        self._current_filters.clear()
        self._current_grouping = None
        self._is_filtered = False
        self._is_grouped = False
        self._status = MediaDataStatus.READY
        self.event_bus.publish(
            MediaDataClearedEvent(
                previous_file_count=previous_files, previous_group_count=previous_groups
            )
        )
        self.logger.info(f"데이터 초기화됨: {previous_files}개 파일, {previous_groups}개 그룹")

    def export_data(self, export_path: Path, format: str = "json") -> UUID:
        """데이터 내보내기"""
        operation_id = uuid4()
        try:
            self.event_bus.publish(
                MediaDataExportStartedEvent(
                    operation_id=operation_id,
                    export_format=format,
                    export_path=export_path,
                    include_statistics=True,
                )
            )
            export_result = self.media_exporter.export_data(
                self.get_all_media_files(), self._groups, export_path, format
            )
            if export_result["success"]:
                self.event_bus.publish(
                    MediaDataExportCompletedEvent(
                        operation_id=operation_id,
                        export_path=export_path,
                        export_size_bytes=export_result["export_size_bytes"],
                        exported_files_count=export_result["exported_files_count"],
                        exported_groups_count=export_result["exported_groups_count"],
                        export_duration_seconds=export_result["export_duration_seconds"],
                    )
                )
                self.logger.info(f"데이터 내보내기 완료: {export_path}")
            else:
                raise Exception(export_result.get("error", "알 수 없는 내보내기 오류"))
            return operation_id
        except Exception as e:
            self.logger.error(f"데이터 내보내기 실패: {e}")
            self.event_bus.publish(
                MediaDataErrorEvent(
                    operation_id=operation_id,
                    error_type="export_error",
                    error_message=str(e),
                    failed_operation=MediaDataStatus.ERROR,
                )
            )
            raise

    def dispose(self) -> None:
        """서비스 정리"""
        self.clear_data()
        self.logger.info("MediaDataService 정리 완료")

    def _remove_file_from_groups(self, file_id: UUID) -> None:
        """그룹에서 파일 제거"""
        for group in self._groups.values():
            episodes_to_remove = [
                ep_num for ep_num, ep_file_id in group.episodes.items() if ep_file_id == file_id
            ]
            for ep_num in episodes_to_remove:
                del group.episodes[ep_num]
            group.total_episodes = len(group.episodes)

    def _update_file_in_groups(self, media_file: MediaFile) -> None:
        """그룹 내 파일 업데이트"""
        for group in self._groups.values():
            for ep_num, ep_file_id in group.episodes.items():
                if ep_file_id == media_file.id:
                    group.episodes[ep_num] = media_file.id
                    break
