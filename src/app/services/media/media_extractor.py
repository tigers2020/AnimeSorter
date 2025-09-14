"""
미디어 데이터 추출기

미디어 파일에서 메타데이터를 추출하고 파싱하는 기능을 담당합니다.
"""

import logging

logger = logging.getLogger(__name__)
from pathlib import Path

from src.app.domain import MediaFile, MediaMetadata, MediaQuality, MediaSource, MediaType


class MediaExtractor:
    """미디어 파일에서 메타데이터를 추출하는 클래스"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_media_file(self, file_path: Path) -> MediaFile | None:
        """미디어 파일에서 메타데이터를 추출하여 MediaFile 객체를 생성합니다."""
        try:
            if not file_path.exists():
                self.logger.warning(f"파일이 존재하지 않습니다: {file_path}")
                return None
            file_stats = file_path.stat()
            media_type = self._infer_media_type(file_path)
            quality = self._infer_quality(file_path)
            source = self._infer_source(file_path)
            title, series, season, episode = self._extract_title_info(file_path.name)
            metadata = MediaMetadata(
                file_size_bytes=file_stats.st_size, quality=quality, source=source
            )
            return MediaFile(
                path=file_path,
                media_type=media_type,
                original_name=file_path.name,
                parsed_title=title,
                season=season,
                episode=episode,
                metadata=metadata,
            )
        except Exception as e:
            self.logger.error(f"미디어 파일 추출 실패: {file_path}: {e}")
            return None

    def _infer_media_type(self, file_path: Path) -> MediaType:
        """파일 확장자로 미디어 타입을 추정합니다."""
        extension = file_path.suffix.lower()
        video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
        audio_extensions = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"}
        if extension in video_extensions:
            return MediaType.VIDEO
        if extension in audio_extensions:
            return MediaType.OTHER
        return MediaType.OTHER

    def _infer_quality(self, file_path: Path) -> MediaQuality:
        """파일명에서 품질 정보를 추정합니다."""
        filename = file_path.name.lower()
        if "1080p" in filename or "1920x1080" in filename:
            return MediaQuality.FHD_1080P
        if "720p" in filename or "1280x720" in filename:
            return MediaQuality.HD_720P
        if "4k" in filename or "2160p" in filename or "3840x2160" in filename:
            return MediaQuality.UHD_4K
        if "480p" in filename:
            return MediaQuality.SD_480P
        return MediaQuality.UNKNOWN

    def _infer_source(self, file_path: Path) -> MediaSource:
        """파일명에서 소스 정보를 추정합니다."""
        filename = file_path.name.lower()
        if "web-dl" in filename or "webdl" in filename:
            return MediaSource.WEBDL
        if "bluray" in filename or "bd" in filename:
            return MediaSource.BLURAY
        if "dvd" in filename:
            return MediaSource.DVD
        if "tv" in filename or "broadcast" in filename:
            return MediaSource.TV
        if "hdtv" in filename:
            return MediaSource.HDTV
        return MediaSource.UNKNOWN

    def _extract_title_info(
        self, filename: str
    ) -> tuple[str | None, str | None, int | None, int | None]:
        """파일명에서 제목, 시리즈, 시즌, 에피소드 정보를 추출합니다."""
        title = None
        series = None
        season = None
        episode = None
        try:
            clean_name = filename.rsplit(".", 1)[0] if "." in filename else filename
            if "S" in clean_name and any(c.isdigit() for c in clean_name.split("S")[1][:2]):
                season_part = clean_name.split("S")[1]
                season = int("".join(filter(str.isdigit, season_part[:2])))
            if "E" in clean_name and any(c.isdigit() for c in clean_name.split("E")[1][:3]):
                episode_part = clean_name.split("E")[1]
                episode = int("".join(filter(str.isdigit, episode_part[:3])))
            title_candidates = []
            parts = clean_name.split()
            for part in parts:
                is_season_info = part.startswith("S") and any(c.isdigit() for c in part[1:3])
                is_episode_info = part.startswith("E") and any(c.isdigit() for c in part[1:4])
                is_episode_word = part.startswith("Episode")
                if not (is_season_info or is_episode_info or is_episode_word):
                    title_candidates.append(part)
            if title_candidates:
                title = " ".join(title_candidates)
                series = title
        except Exception as e:
            self.logger.warning(f"제목 정보 추출 실패: {filename}: {e}")
        return title, series, season, episode

    def extract_batch(self, file_paths: list[Path]) -> list[MediaFile]:
        """여러 파일에서 미디어 데이터를 일괄 추출합니다."""
        extracted_files = []
        for file_path in file_paths:
            media_file = self.extract_media_file(file_path)
            if media_file:
                extracted_files.append(media_file)
        self.logger.info(f"일괄 추출 완료: {len(extracted_files)}/{len(file_paths)}개 파일")
        return extracted_files
