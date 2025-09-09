"""
미디어 데이터 프로세서

미디어 데이터의 변환, 정규화, 가공을 담당하는 모듈입니다.
"""

import logging
from collections import defaultdict
from typing import Any

from src.app.domain import MediaFile, MediaGroup, MediaMetadata, MediaQuality, MediaSource


class MediaProcessor:
    """미디어 데이터를 처리하고 가공하는 클래스"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def normalize_media_file(self, media_file: MediaFile) -> MediaFile:
        """미디어 파일 데이터를 정규화합니다."""
        try:
            # 제목 정규화
            if media_file.parsed_title:
                media_file.parsed_title = self._normalize_title(media_file.parsed_title)

            # 품질 정보 정규화 (메타데이터에서)
            if media_file.metadata:
                # frozen dataclass이므로 새로운 인스턴스 생성
                new_metadata = MediaMetadata(
                    duration_seconds=media_file.metadata.duration_seconds,
                    resolution_width=media_file.metadata.resolution_width,
                    resolution_height=media_file.metadata.resolution_height,
                    bitrate_kbps=media_file.metadata.bitrate_kbps,
                    codec_video=media_file.metadata.codec_video,
                    codec_audio=media_file.metadata.codec_audio,
                    file_size_bytes=media_file.metadata.file_size_bytes,
                    quality=self._normalize_quality(media_file.metadata.quality),
                    source=self._normalize_source(media_file.metadata.source),
                )
                # MediaFile의 metadata 속성은 mutable이므로 직접 할당 가능
                media_file.metadata = new_metadata

            self.logger.debug(f"미디어 파일 정규화 완료: {media_file.original_name}")
            return media_file

        except Exception as e:
            self.logger.error(f"미디어 파일 정규화 실패: {media_file.original_name}: {e}")
            return media_file

    def process_media_files(self, media_files: list[MediaFile]) -> list[MediaFile]:
        """여러 미디어 파일을 일괄 처리합니다."""
        processed_files = []

        for media_file in media_files:
            try:
                processed_file = self.normalize_media_file(media_file)
                processed_files.append(processed_file)
            except Exception as e:
                self.logger.error(f"파일 처리 실패: {media_file.original_name}: {e}")
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
                        title=group_key,
                        total_episodes=len(group_files),
                    )
                    # 에피소드 추가
                    for i, file in enumerate(group_files):
                        media_group.add_episode(i + 1, file.id)
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
            if strategy == "by_title" or strategy == "by_series":
                key = file.parsed_title or "Unknown"
            elif strategy == "by_quality":
                key = file.metadata.quality.value if file.metadata else "Unknown"
            elif strategy == "by_source":
                key = file.metadata.source.value if file.metadata else "Unknown"
            else:
                key = "Default"

            grouped[key].append(file)

        # 그룹 내 파일 정렬 (시즌, 에피소드 순)
        for group_files in grouped.values():
            group_files.sort(key=lambda f: (f.season or 0, f.episode or 0, f.original_name or ""))

        return dict(grouped)

    def _normalize_title(self, title: str) -> str:
        """제목을 정규화합니다."""
        if not title:
            return title

        # 공백 정리
        return " ".join(title.split())

        # 특수문자 정리 (필요시 추가)
        # normalized = re.sub(r'[^\w\s\-\.]', '', normalized)

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
            "file_id": str(media_file.id),
            "original_filename": media_file.original_name or "",
            "file_path": str(media_file.path),
            "file_size_bytes": media_file.metadata.file_size_bytes if media_file.metadata else 0,
            "media_type": media_file.media_type.value,
            "quality": media_file.metadata.quality.value if media_file.metadata else "unknown",
            "source": media_file.metadata.source.value if media_file.metadata else "unknown",
            "title": media_file.parsed_title or "",
            "series": media_file.parsed_title or "",
            "season": media_file.season,
            "episode": media_file.episode,
        }

    def convert_group_to_dict(self, media_group: MediaGroup) -> dict[str, Any]:
        """MediaGroup을 딕셔너리로 변환합니다."""
        return {
            "group_id": str(media_group.id),
            "title": media_group.title,
            "total_episodes": media_group.total_episodes,
            "episode_count": media_group.episode_count,
            "files": list(media_group.episode_numbers),  # 에피소드 번호만 반환
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
        files_by_type: dict[str, int] = {}
        files_by_quality: dict[str, int] = {}
        files_by_source: dict[str, int] = {}

        total_size = 0
        file_sizes = []

        for file in media_files:
            # 타입별 통계
            type_key = file.media_type.value
            files_by_type[type_key] = files_by_type.get(type_key, 0) + 1

            # 품질별 통계
            if file.metadata:
                quality_key = file.metadata.quality.value
                files_by_quality[quality_key] = files_by_quality.get(quality_key, 0) + 1

                # 소스별 통계
                source_key = file.metadata.source.value
                files_by_source[source_key] = files_by_source.get(source_key, 0) + 1

                # 파일 크기 통계
                if file.metadata.file_size_bytes > 0:
                    total_size += file.metadata.file_size_bytes
                    file_sizes.append(file.metadata.file_size_bytes / (1024 * 1024))  # MB로 변환

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
