"""
미디어 데이터 추출기

미디어 파일에서 메타데이터를 추출하는 기능을 담당하는 모듈입니다.
anitopy를 사용하여 애니메이션 파일명에서 메타데이터를 추출합니다.
"""

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.app.domain import (
    MediaFile,
    MediaGroup,
    MediaMetadata,
    MediaQuality,
    MediaSource,
    MediaType,
)
from src.core.file_parser import FileParser

logger = logging.getLogger(__name__)


class MediaExtractor:
    """미디어 파일에서 메타데이터를 추출하는 클래스"""

    def __init__(self) -> None:
        """미디어 추출기 초기화"""
        self.file_parser = FileParser()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("MediaExtractor 초기화 완료")

    def extract_batch(self, file_paths: list[str]) -> list[MediaFile]:
        """
        여러 파일의 메타데이터를 일괄 추출합니다.

        Args:
            file_paths: 추출할 파일 경로 목록

        Returns:
            추출된 MediaFile 객체 목록
        """
        self.logger.info(f"일괄 메타데이터 추출 시작: {len(file_paths)}개 파일")

        media_files = []
        for file_path in file_paths:
            try:
                media_file = self.extract_single(file_path)
                if media_file:
                    media_files.append(media_file)
            except Exception as e:
                self.logger.error(f"파일 메타데이터 추출 실패: {file_path} - {e}")
                continue

        self.logger.info(f"일괄 메타데이터 추출 완료: {len(media_files)}개 파일 처리됨")
        return media_files

    def extract_single(self, file_path: str) -> MediaFile | None:
        """
        단일 파일의 메타데이터를 추출합니다.

        Args:
            file_path: 추출할 파일 경로

        Returns:
            추출된 MediaFile 객체 또는 None
        """
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                self.logger.warning(f"파일이 존재하지 않음: {file_path}")
                return None

            filename = path_obj.name
            self.logger.debug(f"메타데이터 추출 시작: {filename}")

            # anitopy를 사용하여 파일명 파싱
            metadata = self.file_parser.extract_metadata(filename)

            # MediaFile 객체 생성
            media_file = self._create_media_file(file_path, metadata)

            self.logger.debug(f"메타데이터 추출 완료: {filename}")
            return media_file

        except Exception as e:
            self.logger.error(f"파일 메타데이터 추출 중 오류 발생: {file_path} - {e}")
            return None

    def _create_media_file(self, file_path: str, metadata: dict[str, Any]) -> MediaFile:
        """
        파싱된 메타데이터로부터 MediaFile 객체를 생성합니다.

        Args:
            file_path: 파일 경로
            metadata: 파싱된 메타데이터

        Returns:
            생성된 MediaFile 객체
        """
        path_obj = Path(file_path)

        # 기본 정보
        season = metadata.get("season")
        episode = metadata.get("episode")

        # 품질 정보
        resolution = metadata.get("resolution")
        quality = self._determine_quality(resolution)

        # 소스 정보
        source = self._determine_source(metadata.get("source"))

        # 미디어 타입 결정
        media_type = self._determine_media_type(episode, season)

        # 메타데이터 객체 생성
        media_metadata = MediaMetadata(
            resolution_width=self._parse_resolution_width(metadata.get("resolution")),
            resolution_height=self._parse_resolution_height(metadata.get("resolution")),
            codec_video=metadata.get("video_codec"),
            codec_audio=metadata.get("audio_codec"),
            file_size_bytes=path_obj.stat().st_size if path_obj.exists() else 0,
            quality=quality,
            source=source,
        )

        # MediaFile 객체 생성
        return MediaFile(
            id=uuid4(),
            path=path_obj,
            episode=episode,
            season=season,
            extension=path_obj.suffix,
            media_type=media_type,
            metadata=media_metadata,
        )

    def _parse_resolution_width(self, resolution: str | None) -> int | None:
        """해상도 문자열에서 너비를 추출합니다."""
        if not resolution:
            return None
        try:
            if "x" in resolution:
                return int(resolution.split("x")[0])
            if "p" in resolution.lower():
                return int(resolution.lower().replace("p", ""))
        except (ValueError, IndexError):
            pass
        return None

    def _parse_resolution_height(self, resolution: str | None) -> int | None:
        """해상도 문자열에서 높이를 추출합니다."""
        if not resolution:
            return None
        try:
            if "x" in resolution:
                return int(resolution.split("x")[1])
            if "p" in resolution.lower():
                height_map = {
                    "480p": 480,
                    "720p": 720,
                    "1080p": 1080,
                    "1440p": 1440,
                    "4k": 2160,
                    "8k": 4320,
                }
                return height_map.get(resolution.lower())
        except (ValueError, IndexError):
            pass
        return None

    def _determine_quality(self, resolution: str | None) -> MediaQuality:
        """
        해상도 정보로부터 품질을 결정합니다.

        Args:
            resolution: 해상도 문자열

        Returns:
            MediaQuality 열거형 값
        """
        if not resolution:
            return MediaQuality.UNKNOWN

        resolution_lower = resolution.lower()

        if "4k" in resolution_lower or "uhd" in resolution_lower:
            return MediaQuality.UHD_4K
        if "1080" in resolution_lower or "fhd" in resolution_lower:
            return MediaQuality.FHD_1080P
        if "720" in resolution_lower or "hd" in resolution_lower:
            return MediaQuality.HD_720P
        if "480" in resolution_lower or "sd" in resolution_lower:
            return MediaQuality.SD_480P
        return MediaQuality.UNKNOWN

    def _determine_source(self, source: str | None) -> MediaSource:
        """
        소스 정보로부터 MediaSource를 결정합니다.

        Args:
            source: 소스 문자열

        Returns:
            MediaSource 열거형 값
        """
        if not source:
            return MediaSource.UNKNOWN

        source_lower = source.lower()

        if "bluray" in source_lower or "blu-ray" in source_lower:
            return MediaSource.BLURAY
        if "web" in source_lower or "streaming" in source_lower:
            return MediaSource.WEB
        if "tv" in source_lower or "broadcast" in source_lower:
            return MediaSource.TV
        if "dvd" in source_lower:
            return MediaSource.DVD
        return MediaSource.UNKNOWN

    def _determine_media_type(self, episode: int | None, season: int | None) -> MediaType:
        """
        에피소드와 시즌 정보로부터 미디어 타입을 결정합니다.

        Args:
            episode: 에피소드 번호
            season: 시즌 번호

        Returns:
            MediaType 열거형 값
        """
        if episode is not None:
            return MediaType.VIDEO
        if season is not None:
            return MediaType.VIDEO
        return MediaType.VIDEO

    def extract_from_group(self, group: MediaGroup) -> list[MediaFile]:
        """
        미디어 그룹에서 파일들을 추출합니다.

        Args:
            group: 미디어 그룹

        Returns:
            추출된 MediaFile 객체 목록
        """
        # MediaGroup의 episodes에서 파일 경로를 추출
        # 현재는 빈 리스트를 반환합니다 (구현 필요)
        return []

    def get_extraction_statistics(self, file_paths: list[str]) -> dict[str, Any]:
        """
        추출 통계 정보를 반환합니다.

        Args:
            file_paths: 추출할 파일 경로 목록

        Returns:
            추출 통계 딕셔너리
        """
        total_files = len(file_paths)
        successful_extractions = 0
        failed_extractions = 0

        for file_path in file_paths:
            try:
                media_file = self.extract_single(file_path)
                if media_file:
                    successful_extractions += 1
                else:
                    failed_extractions += 1
            except Exception:
                failed_extractions += 1

        return {
            "total_files": total_files,
            "successful_extractions": successful_extractions,
            "failed_extractions": failed_extractions,
            "success_rate": successful_extractions / total_files if total_files > 0 else 0.0,
        }
