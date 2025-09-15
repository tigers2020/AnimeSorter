"""
Anitopy 기반 파일 파싱 모듈 - AnimeSorter

anitopy 라이브러리를 사용하여 애니메이션 파일명에서 메타데이터를 추출하는 기능을 제공합니다.
"""

import logging
from pathlib import Path
from typing import Any

import anitopy

logger = logging.getLogger(__name__)


class AnitopyFileParser:
    """anitopy를 사용한 애니메이션 파일명 파싱 엔진"""

    def __init__(self):
        """파서 초기화"""
        self.options = {
            "allowed_delimiters": " _.&+,|",
            "ignored_strings": [],
            "parse_episode_number": True,
            "parse_episode_title": True,
            "parse_file_extension": True,
            "parse_release_group": True,
        }

    def parse_filename(self, filename: str) -> dict[str, Any] | None:
        """
        파일명을 파싱하여 메타데이터를 추출합니다.

        Args:
            filename: 파싱할 파일명

        Returns:
            파싱된 메타데이터 딕셔너리 또는 None
        """
        try:
            if not filename:
                return None

            # anitopy로 파싱
            parsed_data = anitopy.parse(filename, self.options)

            if not parsed_data:
                logger.warning(f"파싱 실패: {filename}")
                return None

            logger.debug(f"anitopy 파싱 결과: {filename} -> {parsed_data}")
            return parsed_data

        except Exception as e:
            logger.error(f"파싱 중 오류 발생: {filename} - {e}")
            return None

    def extract_metadata(self, filename: str) -> dict[str, Any]:
        """
        파일명에서 메타데이터를 추출하여 표준화된 형태로 반환합니다.

        Args:
            filename: 파싱할 파일명

        Returns:
            표준화된 메타데이터 딕셔너리
        """
        parsed_data = self.parse_filename(filename)

        if not parsed_data:
            return {
                "title": self._extract_title_fallback(filename),
                "season": None,
                "episode": None,
                "year": None,
                "resolution": None,
                "video_codec": None,
                "audio_codec": None,
                "release_group": None,
                "file_extension": Path(filename).suffix.lstrip(".") if filename else None,
                "episode_title": None,
                "source": None,
                "quality": None,
                "language": None,
                "subtitles": None,
                "crc32": None,
                "confidence": 0.0,
            }

        # anitopy 결과를 표준화된 형태로 변환
        resolution = self._extract_resolution(parsed_data)
        if not resolution:
            # anitopy에서 해상도를 찾지 못한 경우 파일명에서 추출 시도
            resolution = self._extract_resolution_fallback(filename)

        return {
            "title": self._extract_title(parsed_data),
            "season": self._extract_season(parsed_data),
            "episode": self._extract_episode(parsed_data),
            "year": self._extract_year(parsed_data),
            "resolution": resolution,
            "video_codec": self._extract_video_codec(parsed_data),
            "audio_codec": self._extract_audio_codec(parsed_data),
            "release_group": self._extract_release_group(parsed_data),
            "file_extension": self._extract_file_extension(parsed_data),
            "episode_title": self._extract_episode_title(parsed_data),
            "source": self._extract_source(parsed_data),
            "quality": self._extract_quality(parsed_data),
            "language": self._extract_language(parsed_data),
            "subtitles": self._extract_subtitles(parsed_data),
            "crc32": self._extract_crc32(parsed_data),
            "confidence": 0.9,  # anitopy는 일반적으로 높은 신뢰도를 가짐
        }

    def _extract_title(self, parsed_data: dict[str, Any]) -> str | None:
        """제목 추출"""
        title = parsed_data.get("anime_title")
        if not title:
            title = parsed_data.get("file_name")

        # 제목 정규화
        if title:
            title = self._normalize_title(title)

        return title

    def _extract_season(self, parsed_data: dict[str, Any]) -> int | None:
        """시즌 번호 추출"""
        season = parsed_data.get("anime_season")
        if season:
            try:
                return int(season)
            except (ValueError, TypeError):
                pass
        return None

    def _extract_episode(self, parsed_data: dict[str, Any]) -> int | None:
        """에피소드 번호 추출"""
        episode = parsed_data.get("episode_number")
        if episode:
            try:
                return int(episode)
            except (ValueError, TypeError):
                pass
        return None

    def _extract_year(self, parsed_data: dict[str, Any]) -> int | None:
        """연도 추출"""
        year = parsed_data.get("anime_year")
        if year:
            try:
                return int(year)
            except (ValueError, TypeError):
                pass
        return None

    def _extract_resolution(self, parsed_data: dict[str, Any]) -> str | None:
        """해상도 추출"""
        resolution = parsed_data.get("video_resolution")
        if resolution:
            from src.core.resolution_normalizer import normalize_resolution

            return normalize_resolution(resolution)
        return resolution

    def _extract_video_codec(self, parsed_data: dict[str, Any]) -> str | None:
        """비디오 코덱 추출"""
        return parsed_data.get("video_term")

    def _extract_audio_codec(self, parsed_data: dict[str, Any]) -> str | None:
        """오디오 코덱 추출"""
        return parsed_data.get("audio_term")

    def _extract_release_group(self, parsed_data: dict[str, Any]) -> str | None:
        """릴리즈 그룹 추출"""
        return parsed_data.get("release_group")

    def _extract_file_extension(self, parsed_data: dict[str, Any]) -> str | None:
        """파일 확장자 추출"""
        return parsed_data.get("file_extension")

    def _extract_episode_title(self, parsed_data: dict[str, Any]) -> str | None:
        """에피소드 제목 추출"""
        return parsed_data.get("episode_title")

    def _extract_source(self, parsed_data: dict[str, Any]) -> str | None:
        """소스 추출 (TV, Web, Blu-ray 등)"""
        return parsed_data.get("source")

    def _extract_quality(self, parsed_data: dict[str, Any]) -> str | None:
        """품질 추출 (HD, SD 등)"""
        return parsed_data.get("video_term")  # anitopy에서는 video_term에 품질 정보가 포함됨

    def _extract_language(self, parsed_data: dict[str, Any]) -> str | None:
        """언어 추출"""
        return parsed_data.get("language")

    def _extract_subtitles(self, parsed_data: dict[str, Any]) -> str | None:
        """자막 정보 추출"""
        return parsed_data.get("subtitle_language")

    def _extract_crc32(self, parsed_data: dict[str, Any]) -> str | None:
        """CRC32 해시 추출"""
        return parsed_data.get("crc32")

    def _normalize_title(self, title: str) -> str:
        """제목을 정규화하여 그룹화 일관성 확보"""
        if not title:
            return "Unknown"

        import re

        # 기본 정리
        normalized = title.strip()

        # 불필요한 접미사 제거
        suffixes_to_remove = [
            r"\s*\([^)]*\)\s*$",  # 괄호 안의 내용 제거
            r"\s*\[[^\]]*\]\s*$",  # 대괄호 안의 내용 제거
            r"\s*-\s*$",  # 끝의 대시 제거
            r"\s*\.\s*$",  # 끝의 점 제거
        ]

        for pattern in suffixes_to_remove:
            normalized = re.sub(pattern, "", normalized)

        # 공백 정규화
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized.strip() or "Unknown"

    def _extract_title_fallback(self, filename: str) -> str:
        """anitopy 파싱 실패 시 제목 추출 폴백"""
        if not filename:
            return "Unknown"

        # 확장자 제거
        name = Path(filename).stem

        # 일반적인 패턴들로 제목 추출 시도
        import re

        # [그룹] 제목 패턴
        match = re.match(r"\[([^\]]+)\]\s*(.+)", name)
        if match:
            title = match.group(2).strip()
            return self._normalize_title(title)

        # S01E01 패턴 제거
        name = re.sub(r"[Ss]\d+[Ee]\d+.*", "", name)

        # 숫자로 시작하는 부분 제거
        name = re.sub(r"^\d+[._-]", "", name)

        # 특수문자 정리
        name = re.sub(r"[._-]+", " ", name)

        return self._normalize_title(name.strip())

    def _extract_resolution_fallback(self, filename: str) -> str | None:
        """파일명에서 해상도 추출 폴백"""
        if not filename:
            return None

        import re

        from src.core.resolution_normalizer import normalize_resolution

        # 해상도 패턴들
        resolution_patterns = [
            r"(\d{3,4}x\d{3,4})",  # 1920x1080, 1280x720 등
            r"(\d{3,4}p)",  # 1080p, 720p 등
            r"\b(4K|UHD|Ultra HD)\b",  # 4K 관련
            r"\b(2K|QHD|Quad HD)\b",  # 2K 관련
            r"\b(FHD|Full HD)\b",  # Full HD
            r"\b(HD)\b",  # HD
            r"\b(SD)\b",  # SD
        ]

        for pattern in resolution_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                resolution = match.group(1)
                return normalize_resolution(resolution)

        return None
