"""
미디어 데이터 관리 서비스

파싱된 미디어 파일 데이터의 관리, 그룹화, 필터링을 담당하는 서비스입니다.
MainWindow의 AnimeDataManager 역할을 대체합니다.
"""

import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from ..domain import MediaFile, MediaGroup, MediaQuality, MediaSource, MediaType
from ..events import TypedEventBus
from ..media_data_events import (
    GroupingStrategy,
    MediaDataClearedEvent,
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
    MediaDataParsingProgressEvent,
    MediaDataReadyEvent,
    MediaDataStatistics,
    MediaDataStatus,
    MediaDataUpdatedEvent,
)


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

        # 데이터 저장소
        self._media_files: dict[UUID, MediaFile] = {}
        self._groups: dict[str, MediaGroup] = {}
        self._filtered_files: set[UUID] = set()
        self._current_filters: list[MediaDataFilter] = []
        self._current_grouping: MediaDataGrouping | None = None

        # 상태 관리
        self._status = MediaDataStatus.READY
        self._is_filtered = False
        self._is_grouped = False

        self.logger.info("MediaDataService 초기화 완료")

    def load_media_files(self, file_paths: list[Path]) -> UUID:
        """미디어 파일들을 로드하고 파싱"""
        operation_id = uuid4()

        try:
            self.logger.info(f"미디어 파일 로드 시작: {len(file_paths)}개 파일")

            # 로드 시작 이벤트 발행
            self.event_bus.publish(
                MediaDataLoadStartedEvent(
                    operation_id=operation_id, file_paths=file_paths, total_files=len(file_paths)
                )
            )

            self._status = MediaDataStatus.PARSING
            parsed_files = []
            failed_files = []
            parsing_errors = []

            start_time = time.time()

            # 각 파일 파싱
            for i, file_path in enumerate(file_paths):
                try:
                    # 진행률 이벤트 발행
                    progress_percent = int((i / len(file_paths)) * 100)
                    self.event_bus.publish(
                        MediaDataParsingProgressEvent(
                            operation_id=operation_id,
                            current_file=i + 1,
                            total_files=len(file_paths),
                            current_file_path=file_path,
                            progress_percent=progress_percent,
                            parsing_status=MediaDataStatus.PARSING,
                        )
                    )

                    # 미디어 파일 파싱 (실제 파싱 로직은 여기서 호출)
                    media_file = self._parse_media_file(file_path)
                    if media_file:
                        parsed_files.append(media_file)
                        self._media_files[media_file.file_id] = media_file
                    else:
                        failed_files.append(file_path)
                        parsing_errors.append(f"파싱 실패: {file_path}")

                except Exception as e:
                    self.logger.error(f"파일 파싱 오류: {file_path}: {e}")
                    failed_files.append(file_path)
                    parsing_errors.append(f"파싱 오류: {file_path}: {str(e)}")

            parsing_duration = time.time() - start_time

            # 파싱 완료 이벤트 발행
            self.event_bus.publish(
                MediaDataParsingCompletedEvent(
                    operation_id=operation_id,
                    parsed_files=parsed_files,
                    failed_files=failed_files,
                    parsing_errors=parsing_errors,
                    parsing_duration_seconds=parsing_duration,
                )
            )

            self._status = MediaDataStatus.READY

            # 준비 완료 이벤트 발행
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

            self.logger.info(
                f"미디어 파일 로드 완료: {len(parsed_files)}개 성공, {len(failed_files)}개 실패"
            )
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
            self._media_files[media_file.file_id] = media_file

            # 업데이트 이벤트 발행
            self.event_bus.publish(
                MediaDataUpdatedEvent(updated_files=[media_file], update_type="added")
            )

            self.logger.debug(f"미디어 파일 추가됨: {media_file.original_filename}")
            return True

        except Exception as e:
            self.logger.error(f"미디어 파일 추가 실패: {e}")
            return False

    def remove_media_file(self, file_id: UUID) -> bool:
        """미디어 파일 제거"""
        try:
            if file_id in self._media_files:
                removed_file = self._media_files.pop(file_id)

                # 필터된 파일 목록에서도 제거
                self._filtered_files.discard(file_id)

                # 그룹에서도 제거
                self._remove_file_from_groups(file_id)

                # 업데이트 이벤트 발행
                self.event_bus.publish(
                    MediaDataUpdatedEvent(updated_files=[removed_file], update_type="removed")
                )

                self.logger.debug(f"미디어 파일 제거됨: {removed_file.original_filename}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"미디어 파일 제거 실패: {e}")
            return False

    def update_media_file(self, media_file: MediaFile) -> bool:
        """미디어 파일 업데이트"""
        try:
            if media_file.file_id in self._media_files:
                self._media_files[media_file.file_id] = media_file

                # 그룹 업데이트
                self._update_file_in_groups(media_file)

                # 업데이트 이벤트 발행
                self.event_bus.publish(
                    MediaDataUpdatedEvent(updated_files=[media_file], update_type="modified")
                )

                self.logger.debug(f"미디어 파일 업데이트됨: {media_file.original_filename}")
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

            # 그룹화 시작 이벤트 발행
            self.event_bus.publish(
                MediaDataGroupingStartedEvent(
                    operation_id=operation_id,
                    grouping_config=grouping_config,
                    total_files=len(self._media_files),
                )
            )

            self._status = MediaDataStatus.GROUPING
            start_time = time.time()

            # 기존 그룹 초기화
            self._groups.clear()
            self._current_grouping = grouping_config

            # 그룹화 실행
            files_to_group = self.get_all_media_files()
            grouped_files = self._group_files_by_strategy(files_to_group, grouping_config)

            # MediaGroup 객체 생성
            for group_key, group_files in grouped_files.items():
                if group_files:  # 빈 그룹 제외
                    media_group = MediaGroup(
                        group_id=group_key,
                        title=group_key,
                        files=group_files,
                        total_episodes=len(group_files),
                        media_type=group_files[0].media_type if group_files else MediaType.UNKNOWN,
                    )
                    self._groups[group_key] = media_group

            grouping_duration = time.time() - start_time

            # 그룹화 완료 이벤트 발행
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

            # 필터링 시작 이벤트 발행
            total_items = len(self._media_files)
            self.event_bus.publish(
                MediaDataFilteringStartedEvent(
                    operation_id=operation_id, filters=filters, total_items=total_items
                )
            )

            self._status = MediaDataStatus.FILTERING
            start_time = time.time()

            # 필터 적용
            self._current_filters = filters
            filtered_file_ids = self._apply_filters_to_files(
                list(self._media_files.values()), filters
            )
            self._filtered_files = set(filtered_file_ids)

            # 필터링된 파일들과 그룹들
            filtered_files = [self._media_files[file_id] for file_id in filtered_file_ids]
            filtered_groups = self._create_filtered_groups(filtered_files)

            filtering_duration = time.time() - start_time

            # 필터링 완료 이벤트 발행
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
        files = self.get_all_media_files()

        # 타입별 통계
        files_by_type = defaultdict(int)
        files_by_quality = defaultdict(int)
        files_by_source = defaultdict(int)

        total_size = 0
        file_sizes = []

        for file in files:
            files_by_type[file.media_type.value] += 1
            files_by_quality[file.quality.value] += 1
            files_by_source[file.source.value] += 1

            if file.file_size_bytes > 0:
                total_size += file.file_size_bytes
                file_sizes.append(file.file_size_bytes / (1024 * 1024))  # MB로 변환

        # 평균, 최대, 최소 파일 크기 계산
        average_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0.0
        largest_size = max(file_sizes) if file_sizes else 0.0
        smallest_size = min(file_sizes) if file_sizes else 0.0

        return MediaDataStatistics(
            total_files=len(files),
            total_groups=len(self._groups),
            files_by_type=dict(files_by_type),
            files_by_quality=dict(files_by_quality),
            files_by_source=dict(files_by_source),
            total_size_bytes=total_size,
            average_file_size_mb=average_size,
            largest_file_size_mb=largest_size,
            smallest_file_size_mb=smallest_size,
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

        # 초기화 이벤트 발행
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
            # 내보내기 시작 이벤트 발행
            self.event_bus.publish(
                MediaDataExportStartedEvent(
                    operation_id=operation_id,
                    export_format=format,
                    export_path=export_path,
                    include_statistics=True,
                )
            )

            start_time = time.time()

            # 내보낼 데이터 준비
            export_data = {
                "files": [self._media_file_to_dict(file) for file in self.get_all_media_files()],
                "groups": {
                    gid: self._media_group_to_dict(group) for gid, group in self._groups.items()
                },
                "statistics": self._statistics_to_dict(self.get_statistics()),
                "metadata": {
                    "export_timestamp": time.time(),
                    "total_files": len(self._media_files),
                    "total_groups": len(self._groups),
                    "is_filtered": self._is_filtered,
                    "is_grouped": self._is_grouped,
                },
            }

            # 형식에 따라 내보내기
            if format.lower() == "json":
                self._export_to_json(export_data, export_path)
            else:
                raise ValueError(f"지원하지 않는 내보내기 형식: {format}")

            export_duration = time.time() - start_time
            export_size = export_path.stat().st_size if export_path.exists() else 0

            # 내보내기 완료 이벤트 발행
            self.event_bus.publish(
                MediaDataExportCompletedEvent(
                    operation_id=operation_id,
                    export_path=export_path,
                    export_size_bytes=export_size,
                    exported_files_count=len(export_data["files"]),
                    exported_groups_count=len(export_data["groups"]),
                    export_duration_seconds=export_duration,
                )
            )

            self.logger.info(f"데이터 내보내기 완료: {export_path}")
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

    # ===== 헬퍼 메서드 =====

    def _parse_media_file(self, file_path: Path) -> MediaFile | None:
        """미디어 파일 파싱 (실제 파서 연동 필요)"""
        try:
            # TODO: 실제 FileParser와 연동
            # 현재는 더미 데이터 생성
            if file_path.exists():
                return MediaFile(
                    file_id=uuid4(),
                    original_filename=file_path.name,
                    file_path=file_path,
                    file_size_bytes=file_path.stat().st_size,
                    media_type=MediaType.ANIME,
                    quality=MediaQuality.HD_1080P,
                    source=MediaSource.WEB_DL,
                )
            return None

        except Exception as e:
            self.logger.error(f"파일 파싱 실패: {file_path}: {e}")
            return None

    def _group_files_by_strategy(
        self, files: list[MediaFile], grouping_config: MediaDataGrouping
    ) -> dict[str, list[MediaFile]]:
        """전략에 따른 파일 그룹화"""
        grouped = defaultdict(list)

        for file in files:
            if grouping_config.strategy == GroupingStrategy.BY_TITLE:
                key = file.title or "Unknown"
            elif grouping_config.strategy == GroupingStrategy.BY_SERIES:
                key = file.series or file.title or "Unknown"
            elif grouping_config.strategy == GroupingStrategy.BY_QUALITY:
                key = file.quality.value
            elif grouping_config.strategy == GroupingStrategy.BY_SOURCE:
                key = file.source.value
            else:
                key = "Default"

            grouped[key].append(file)

        # 정렬
        if grouping_config.sort_files_within_groups:
            for group_files in grouped.values():
                group_files.sort(key=lambda f: (f.season or 0, f.episode or 0, f.original_filename))

        return dict(grouped)

    def _apply_filters_to_files(
        self, files: list[MediaFile], filters: list[MediaDataFilter]
    ) -> list[UUID]:
        """파일에 필터 적용"""
        filtered_file_ids = []

        for file in files:
            passes_all_filters = True

            for filter_criteria in filters:
                if not self._file_passes_filter(file, filter_criteria):
                    passes_all_filters = False
                    break

            if passes_all_filters:
                filtered_file_ids.append(file.file_id)

        return filtered_file_ids

    def _file_passes_filter(self, file: MediaFile, filter_criteria: MediaDataFilter) -> bool:
        """단일 파일이 필터를 통과하는지 확인"""
        # TODO: 실제 필터링 로직 구현
        return True  # 임시로 모든 파일 통과

    def _create_filtered_groups(self, filtered_files: list[MediaFile]) -> dict[str, MediaGroup]:
        """필터링된 파일들로 그룹 생성"""
        if not self._current_grouping:
            return {}

        grouped_files = self._group_files_by_strategy(filtered_files, self._current_grouping)
        filtered_groups = {}

        for group_key, group_files in grouped_files.items():
            if group_files:
                media_group = MediaGroup(
                    group_id=f"filtered_{group_key}",
                    title=group_key,
                    files=group_files,
                    total_episodes=len(group_files),
                    media_type=group_files[0].media_type if group_files else MediaType.UNKNOWN,
                )
                filtered_groups[f"filtered_{group_key}"] = media_group

        return filtered_groups

    def _remove_file_from_groups(self, file_id: UUID) -> None:
        """그룹에서 파일 제거"""
        for group in self._groups.values():
            group.files = [f for f in group.files if f.file_id != file_id]
            group.total_episodes = len(group.files)

    def _update_file_in_groups(self, media_file: MediaFile) -> None:
        """그룹 내 파일 업데이트"""
        for group in self._groups.values():
            for i, file in enumerate(group.files):
                if file.file_id == media_file.file_id:
                    group.files[i] = media_file
                    break

    def _media_file_to_dict(self, media_file: MediaFile) -> dict[str, Any]:
        """MediaFile을 딕셔너리로 변환"""
        return {
            "file_id": str(media_file.file_id),
            "original_filename": media_file.original_filename,
            "file_path": str(media_file.file_path),
            "file_size_bytes": media_file.file_size_bytes,
            "media_type": media_file.media_type.value,
            "quality": media_file.quality.value,
            "source": media_file.source.value,
            "title": media_file.title,
            "series": media_file.series,
            "season": media_file.season,
            "episode": media_file.episode,
        }

    def _media_group_to_dict(self, media_group: MediaGroup) -> dict[str, Any]:
        """MediaGroup을 딕셔너리로 변환"""
        return {
            "group_id": media_group.group_id,
            "title": media_group.title,
            "total_episodes": media_group.total_episodes,
            "media_type": media_group.media_type.value,
            "files": [self._media_file_to_dict(f) for f in media_group.files],
        }

    def _statistics_to_dict(self, statistics: MediaDataStatistics) -> dict[str, Any]:
        """MediaDataStatistics를 딕셔너리로 변환"""
        return {
            "total_files": statistics.total_files,
            "total_groups": statistics.total_groups,
            "files_by_type": statistics.files_by_type,
            "files_by_quality": statistics.files_by_quality,
            "files_by_source": statistics.files_by_source,
            "total_size_bytes": statistics.total_size_bytes,
            "average_file_size_mb": statistics.average_file_size_mb,
            "largest_file_size_mb": statistics.largest_file_size_mb,
            "smallest_file_size_mb": statistics.smallest_file_size_mb,
        }

    def _export_to_json(self, data: dict[str, Any], export_path: Path) -> None:
        """JSON 형식으로 데이터 내보내기"""
        import json

        export_path.parent.mkdir(parents=True, exist_ok=True)

        with export_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
