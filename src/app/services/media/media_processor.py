"""
미디어 데이터 프로세서

미디어 데이터의 변환, 정규화, 가공을 담당하는 모듈입니다.
"""

import logging
from collections import defaultdict
from typing import Any

from ...domain import MediaFile, MediaGroup, MediaQuality, MediaSource, MediaType


class MediaProcessor:
    """미디어 데이터를 처리하고 가공하는 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def normalize_media_file(self, media_file: MediaFile) -> MediaFile:
        """미디어 파일 데이터를 정규화합니다."""
        try:
            # 제목 정규화
            if media_file.title:
                media_file.title = self._normalize_title(media_file.title)

            # 시리즈 정규화
            if media_file.series:
                media_file.series = self._normalize_title(media_file.series)

            # 품질 정보 정규화
            media_file.quality = self._normalize_quality(media_file.quality)

            # 소스 정보 정규화
            media_file.source = self._normalize_source(media_file.source)

            self.logger.debug(f"미디어 파일 정규화 완료: {media_file.original_filename}")
            return media_file

        except Exception as e:
            self.logger.error(f"미디어 파일 정규화 실패: {media_file.original_filename}: {e}")
            return media_file

    def process_media_files(self, media_files: list[MediaFile]) -> list[MediaFile]:
        """여러 미디어 파일을 일괄 처리합니다."""
        processed_files = []

        for media_file in media_files:
            try:
                processed_file = self.normalize_media_file(media_file)
                processed_files.append(processed_file)
            except Exception as e:
                self.logger.error(f"파일 처리 실패: {media_file.original_filename}: {e}")
                # 처리 실패한 파일도 그대로 추가
                processed_files.append(media_file)

        self.logger.info(f"미디어 파일 일괄 처리 완료: {len(processed_files)}개")
        return processed_files

    def create_media_groups(
        self, media_files: list[MediaFile], strategy: str = "by_title"
    ) -> dict[str, MediaGroup]:
        """미디어 파일들을 그룹화합니다."""
        try:
            grouped_files = self._group_files_by_strategy(media_files, strategy)
            media_groups = {}

            for group_key, group_files in grouped_files.items():
                if group_files:  # 빈 그룹 제외
                    media_group = MediaGroup(
                        group_id=group_key,
                        title=group_key,
                        files=group_files,
                        total_episodes=len(group_files),
                        media_type=group_files[0].media_type if group_files else MediaType.UNKNOWN,
                    )
                    media_groups[group_key] = media_group

            self.logger.info(f"미디어 그룹 생성 완료: {len(media_groups)}개 그룹")
            return media_groups

        except Exception as e:
            self.logger.error(f"미디어 그룹 생성 실패: {e}")
            return {}

    def _group_files_by_strategy(
        self, files: list[MediaFile], strategy: str
    ) -> dict[str, list[MediaFile]]:
        """전략에 따른 파일 그룹화"""
        grouped = defaultdict(list)

        for file in files:
            if strategy == "by_title":
                key = file.title or "Unknown"
            elif strategy == "by_series":
                key = file.series or file.title or "Unknown"
            elif strategy == "by_quality":
                key = file.quality.value
            elif strategy == "by_source":
                key = file.source.value
            else:
                key = "Default"

            grouped[key].append(file)

        # 그룹 내 파일 정렬 (시즌, 에피소드 순)
        for group_files in grouped.values():
            group_files.sort(key=lambda f: (f.season or 0, f.episode or 0, f.original_filename))

        return dict(grouped)

    def _normalize_title(self, title: str) -> str:
        """제목을 정규화합니다."""
        if not title:
            return title

        # 공백 정리
        normalized = " ".join(title.split())

        # 특수문자 정리 (필요시 추가)
        # normalized = re.sub(r'[^\w\s\-\.]', '', normalized)

        return normalized

    def _normalize_quality(self, quality: MediaQuality) -> MediaQuality:
        """품질 정보를 정규화합니다."""
        # 현재는 그대로 반환, 필요시 추가 로직 구현
        return quality

    def _normalize_source(self, source: MediaSource) -> MediaSource:
        """소스 정보를 정규화합니다."""
        # 현재는 그대로 반환, 필요시 추가 로직 구현
        return source

    def convert_to_dict(self, media_file: MediaFile) -> dict[str, Any]:
        """MediaFile을 딕셔너리로 변환합니다."""
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

    def convert_group_to_dict(self, media_group: MediaGroup) -> dict[str, Any]:
        """MediaGroup을 딕셔너리로 변환합니다."""
        return {
            "group_id": media_group.group_id,
            "title": media_group.title,
            "total_episodes": media_group.total_episodes,
            "media_type": media_group.media_type.value,
            "files": [self.convert_to_dict(f) for f in media_group.files],
        }

    def calculate_statistics(
        self, media_files: list[MediaFile], groups: dict[str, MediaGroup] = None
    ) -> dict[str, Any]:
        """미디어 파일들의 통계 정보를 계산합니다."""
        if not media_files:
            return {
                "total_files": 0,
                "total_groups": len(groups) if groups else 0,
                "files_by_type": {},
                "files_by_quality": {},
                "files_by_source": {},
                "total_size_bytes": 0,
                "average_file_size_mb": 0.0,
                "largest_file_size_mb": 0.0,
                "smallest_file_size_mb": 0.0,
            }

        # 타입별, 품질별, 소스별 통계
        files_by_type = {}
        files_by_quality = {}
        files_by_source = {}

        total_size = 0
        file_sizes = []

        for file in media_files:
            # 타입별 통계
            type_key = file.media_type.value
            files_by_type[type_key] = files_by_type.get(type_key, 0) + 1

            # 품질별 통계
            quality_key = file.quality.value
            files_by_quality[quality_key] = files_by_quality.get(quality_key, 0) + 1

            # 소스별 통계
            source_key = file.source.value
            files_by_source[source_key] = files_by_source.get(source_key, 0) + 1

            # 파일 크기 통계
            if file.file_size_bytes > 0:
                total_size += file.file_size_bytes
                file_sizes.append(file.file_size_bytes / (1024 * 1024))  # MB로 변환

        # 파일 크기 통계 계산
        average_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0.0
        largest_size = max(file_sizes) if file_sizes else 0.0
        smallest_size = min(file_sizes) if file_sizes else 0.0

        return {
            "total_files": len(media_files),
            "total_groups": len(groups) if groups else 0,
            "files_by_type": files_by_type,
            "files_by_quality": files_by_quality,
            "files_by_source": files_by_source,
            "total_size_bytes": total_size,
            "average_file_size_mb": round(average_size, 2),
            "largest_file_size_mb": round(largest_size, 2),
            "smallest_file_size_mb": round(smallest_size, 2),
        }
