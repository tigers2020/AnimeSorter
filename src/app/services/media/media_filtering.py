"""
미디어 데이터 필터링

미디어 파일과 그룹에 대한 필터링 기능을 담당하는 모듈입니다.
"""

import logging

logger = logging.getLogger(__name__)
from uuid import UUID

from src.app.domain import (MediaFile, MediaGroup, MediaQuality, MediaSource,
                            MediaType)

# MediaDataFilter는 새로운 12개 핵심 이벤트 시스템으로 대체됨
# from src.core.events import MediaDataFilter


class MediaFilter:
    """미디어 데이터 필터링을 담당하는 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def apply_filters(self, files: list[MediaFile], filters: list) -> list[UUID]:
        """파일에 필터를 적용하여 통과한 파일 ID 목록을 반환합니다."""
        try:
            if not filters:
                return [file.id for file in files]
            filtered_file_ids = []
            for file in files:
                if self._file_passes_all_filters(file, filters):
                    filtered_file_ids.append(file.id)
            self.logger.info(f"필터링 완료: {len(files)}개 → {len(filtered_file_ids)}개")
            return filtered_file_ids
        except Exception as e:
            self.logger.error(f"필터링 실패: {e}")
            return [file.id for file in files]

    def _file_passes_all_filters(self, file: MediaFile, filters: list) -> bool:
        """파일이 모든 필터를 통과하는지 확인합니다."""
        return all(self._file_passes_filter(file, filter_criteria) for filter_criteria in filters)

    def _file_passes_filter(self, file: MediaFile, filter_criteria) -> bool:
        """파일이 단일 필터를 통과하는지 확인합니다."""
        try:
            filter_type = filter_criteria.criteria.value
            filter_value = filter_criteria.value
            if filter_type == "media_type":
                return self._check_media_type_filter(file, filter_value)
            if filter_type == "quality":
                return self._check_quality_filter(file, filter_value)
            if filter_type == "source":
                return self._check_source_filter(file, filter_value)
            if filter_type == "title":
                return self._check_title_filter(file, filter_value)
            if filter_type == "series":
                return self._check_series_filter(file, filter_value)
            if filter_type == "season":
                return self._check_season_filter(file, filter_value)
            if filter_type == "episode":
                return self._check_episode_filter(file, filter_value)
            if filter_type == "file_size":
                return self._check_file_size_filter(file, filter_value)
            self.logger.warning(f"알 수 없는 필터 타입: {filter_type}")
            return True
        except Exception as e:
            self.logger.error(f"필터 확인 실패: {filter_type}={filter_value}: {e}")
            return True

    def _check_media_type_filter(self, file: MediaFile, filter_value: str) -> bool:
        """미디어 타입 필터를 확인합니다."""
        if not filter_value:
            return True
        try:
            target_type = MediaType(filter_value)
            return file.media_type == target_type
        except ValueError:
            return file.media_type.value == filter_value

    def _check_quality_filter(self, file: MediaFile, filter_value: str) -> bool:
        """품질 필터를 확인합니다."""
        if not filter_value:
            return True
        if not file.metadata:
            return False
        try:
            target_quality = MediaQuality(filter_value)
            return file.metadata.quality == target_quality
        except ValueError:
            return file.metadata.quality.value == filter_value

    def _check_source_filter(self, file: MediaFile, filter_value: str) -> bool:
        """소스 필터를 확인합니다."""
        if not filter_value:
            return True
        if not file.metadata:
            return False
        try:
            target_source = MediaSource(filter_value)
            return file.metadata.source == target_source
        except ValueError:
            return file.metadata.source.value == filter_value

    def _check_title_filter(self, file: MediaFile, filter_value: str) -> bool:
        """제목 필터를 확인합니다."""
        if not filter_value or not file.parsed_title:
            return True
        return filter_value.lower() in file.parsed_title.lower()

    def _check_series_filter(self, file: MediaFile, filter_value: str) -> bool:
        """시리즈 필터를 확인합니다."""
        if not filter_value:
            return True
        return True

    def _check_season_filter(self, file: MediaFile, filter_value: str) -> bool:
        """시즌 필터를 확인합니다."""
        if not filter_value or file.season is None:
            return True
        try:
            target_season = int(filter_value)
            return file.season == target_season
        except ValueError:
            return True

    def _check_episode_filter(self, file: MediaFile, filter_value: str) -> bool:
        """에피소드 필터를 확인합니다."""
        if not filter_value or file.episode is None:
            return True
        try:
            target_episode = int(filter_value)
            return file.episode == target_episode
        except ValueError:
            return True

    def _check_file_size_filter(self, file: MediaFile, filter_value: str) -> bool:
        """파일 크기 필터를 확인합니다."""
        if not filter_value or not file.metadata or file.metadata.file_size_bytes <= 0:
            return True
        try:
            file_size_mb = file.metadata.file_size_bytes / (1024 * 1024)
            target_size_mb = float(filter_value)
            return file_size_mb >= target_size_mb
        except ValueError:
            return True

    def create_filtered_groups(
        self, groups: dict[str, MediaGroup], filtered_file_ids: set[UUID]
    ) -> dict[str, MediaGroup]:
        """필터링된 파일들로 그룹을 생성합니다."""
        try:
            filtered_groups = {}
            for group_id, group in groups.items():
                filtered_episodes = {
                    ep_num: file_id
                    for ep_num, file_id in group.episodes.items()
                    if file_id in filtered_file_ids
                }
                if filtered_episodes:
                    filtered_group = MediaGroup(
                        id=group.id,
                        title=group.title,
                        season=group.season,
                        total_episodes=len(filtered_episodes),
                    )
                    for ep_num, file_id in filtered_episodes.items():
                        filtered_group.add_episode(ep_num, file_id)
                    filtered_groups[f"filtered_{group_id}"] = filtered_group
            self.logger.info(f"필터링된 그룹 생성 완료: {len(filtered_groups)}개")
            return filtered_groups
        except Exception as e:
            self.logger.error(f"필터링된 그룹 생성 실패: {e}")
            return {}

    def clear_filters(self) -> None:
        """필터를 초기화합니다."""
        self.logger.info("필터 초기화됨")

    def get_filter_summary(self, filters: list) -> str:
        """적용된 필터들의 요약을 반환합니다."""
        if not filters:
            return "필터 없음"
        filter_descriptions = []
        for filter_criteria in filters:
            desc = f"{filter_criteria.criteria.value}={filter_criteria.value}"
            filter_descriptions.append(desc)
        return f"필터: {', '.join(filter_descriptions)}"
