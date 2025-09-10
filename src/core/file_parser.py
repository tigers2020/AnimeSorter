"""
파일명 파싱 모듈 - AnimeSorter

애니메이션 파일명에서 메타데이터를 추출하는 기능을 제공합니다.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ParsedMetadata:
    """파싱된 파일 메타데이터"""

    title: str
    season: int | None = None
    episode: int | None = None
    year: int | None = None
    resolution: str | None = None
    group: str | None = None
    codec: str | None = None
    container: str | None = None
    audio_codec: str | None = None
    language: str | None = None
    quality: str | None = None
    source: str | None = None
    confidence: float = 0.0


class FileParser:
    """애니메이션 파일명 파싱 엔진 (최적화됨)"""

    def __init__(self):
        """파서 초기화"""
        self.patterns = self._compile_patterns()
        self._parse_cache_size = 256

    def _compile_patterns(self) -> list[tuple[re.Pattern[str], str, float]]:
        """파싱 패턴 컴파일 (최적화된 순서)"""
        return [
            (
                re.compile("^(.+?)\\.S(\\d+)E(\\d+)\\.(\\d+p)\\.([^.]+)\\.([^.]+)$", re.IGNORECASE),
                "title_season_episode_resolution_dots",
                0.95,
            ),
            (
                re.compile(
                    "^\\[([^\\]]+)\\]\\s*(.+?)\\s+S(\\d+)\\s*-\\s*(\\d+)\\s*\\(([^)]*(?:\\d+p|HD|SD)[^)]*)\\)\\s*\\[([^\\]]+)\\]",
                    re.IGNORECASE,
                ),
                "group_title_season_episode_resolution_code",
                0.95,
            ),
            (
                re.compile("^(.+?)\\.S(\\d+)E(\\d+)", re.IGNORECASE),
                "title_season_episode_simple",
                0.9,
            ),
            (
                re.compile("^(.+?)\\s+S(\\d+)E(\\d+)", re.IGNORECASE),
                "title_season_episode_space",
                0.9,
            ),
            (re.compile("^(.+?)\\.E(\\d+)", re.IGNORECASE), "title_episode_exx", 0.9),
            (
                re.compile(
                    "^\\[([^\\]]+)\\]\\s*(.+?)\\s+S(\\d+)\\s*-\\s*(\\d+)\\s*\\(([^)]*(?:\\d+p|HD|SD)[^)]*)\\)",
                    re.IGNORECASE,
                ),
                "group_title_season_episode_resolution",
                0.9,
            ),
            (
                re.compile(
                    "^\\[([^\\]]+)\\]\\s*(.+?)\\s+S(\\d+)\\s*-\\s*(\\d+)\\s*\\[([^\\]]+)\\]",
                    re.IGNORECASE,
                ),
                "group_title_season_episode_code",
                0.9,
            ),
            (
                re.compile(
                    "^(.+?)\\s+S(\\d+)\\s*-\\s*(\\d+)\\s*\\(([^)]*(?:\\d+p|HD|SD)[^)]*)\\)\\s*\\[([^\\]]+)\\]",
                    re.IGNORECASE,
                ),
                "title_season_episode_resolution_code",
                0.9,
            ),
            (
                re.compile("^(.+?)\\.E(\\d+)\\.(\\d+p)", re.IGNORECASE),
                "title_episode_exx_resolution",
                0.9,
            ),
            (
                re.compile(
                    "^\\[([^\\]]+)\\]\\s*(.+?)\\s*-\\s*(\\d+(?:\\.\\d+)?)\\s*\\(([^)]*(?:\\d+p|HD|SD)[^)]*)\\)",
                    re.IGNORECASE,
                ),
                "group_title_episode_decimal_resolution",
                0.9,
            ),
            (
                re.compile(
                    "^\\[([^\\]]+)\\]\\s*(.+?)\\s*-\\s*(\\d+)\\s*\\([^)]*\\b(\\d{3,5}x\\d{3,5}|\\d{3,5}p)\\b[^)]*\\)",
                    re.IGNORECASE,
                ),
                "group_title_episode_with_resolution",
                0.9,
            ),
            (
                re.compile(
                    "^\\[([^\\]]+)\\]\\s*(.+?)\\s*-\\s*(\\d+)\\s*\\[([^\\]]*(?:\\d+p)[^\\]]*)\\]",
                    re.IGNORECASE,
                ),
                "group_title_episode_bracket_resolution",
                0.9,
            ),
            (
                re.compile("^\\[([^\\]]+)\\]\\s*(.+?)\\s+S(\\d+)\\s*-\\s*(\\d+)", re.IGNORECASE),
                "group_title_season_episode",
                0.85,
            ),
            (
                re.compile(
                    "^(.+?)\\s+S(\\d+)\\s*-\\s*(\\d+)\\s*\\(([^)]*(?:\\d+p|HD|SD)[^)]*)\\)",
                    re.IGNORECASE,
                ),
                "title_season_episode_resolution",
                0.85,
            ),
            (
                re.compile(
                    "^(.+?)\\s*(\\d+)화\\s*(?:[\\[\\(][^\\]\\)]*(1080p?|720p?|480p?|\\d{3,4}x\\d{3,4})[^\\]\\)]*[\\]\\)])?",
                    re.IGNORECASE,
                ),
                "title_episode_korean",
                0.85,
            ),
            (
                re.compile("^(.+?)\\s+S(\\d+)\\s*-\\s*(\\d+)\\s*\\[([^\\]]+)\\]", re.IGNORECASE),
                "title_season_episode_code",
                0.85,
            ),
            (
                re.compile("^(.+?)\\s+S(\\d+)\\s*-\\s*(\\d+)", re.IGNORECASE),
                "title_season_episode",
                0.8,
            ),
            (
                re.compile(
                    "^\\[([^\\]]+)\\]\\s*(.+?)\\s*-\\s*(\\d+)\\s*(?:\\([^)]+\\))?", re.IGNORECASE
                ),
                "group_title_episode",
                0.8,
            ),
            (re.compile("^(.+?)\\s+EP(\\d+)", re.IGNORECASE), "title_episode_ep", 0.8),
            (
                re.compile("^(.+?)\\s*-\\s*(\\d+)\\s*(RAW|END|FIN|COMPLETE)", re.IGNORECASE),
                "title_episode_special",
                0.8,
            ),
            (
                re.compile("^(?!\\[)(.+?)\\s+(?:Season\\s*(\\d+))?\\s*(\\d+)$", re.IGNORECASE),
                "title_season_episode_space",
                0.8,
            ),
            (
                re.compile("^\\[([^\\]]+)\\]([^-\\s]+)\\s*(\\d+)", re.IGNORECASE),
                "group_title_episode_nospace",
                0.8,
            ),
            (re.compile("^(.+?)\\s+(\\d+)$", re.IGNORECASE), "title_episode_simple", 0.8),
            (re.compile("^(.+?)\\s*第(\\d+)話", re.IGNORECASE), "title_episode_japanese", 0.8),
            (
                re.compile("^(.+?)\\s*(\\d+)화\\s*(?:\\([^)]*\\))?", re.IGNORECASE),
                "title_episode_korean_hwa",
                0.8,
            ),
            (
                re.compile(
                    "^\\[([^\\]]+)\\]\\s*(.+?)\\s*(\\d+)\\s*(?:\\([^)]*\\))?", re.IGNORECASE
                ),
                "group_title_episode_bracket",
                0.8,
            ),
            (
                re.compile(
                    "^\\[([^\\]]+)\\]\\s*(.+?)\\s*-\\s*(\\d+)\\s*(?:\\([^)]*\\))?", re.IGNORECASE
                ),
                "group_title_episode_dash",
                0.8,
            ),
            (
                re.compile("^(.+?)\\s*-\\s*(\\d+)\\s*(?:\\([^)]*\\))?", re.IGNORECASE),
                "title_episode_dash",
                0.8,
            ),
            (
                re.compile("^(.+?)\\s+(\\d+)\\s*(?:\\([^)]*\\))?", re.IGNORECASE),
                "title_episode_space",
                0.8,
            ),
            (
                re.compile("^(\\d+)기\\s*(.+?)\\s*[上下]?\\s*\\.", re.IGNORECASE),
                "season_title_episode_korean",
                0.8,
            ),
            (
                re.compile("^(.+?)_(\\d+)\\s*(?:DVD|BD|HD)?", re.IGNORECASE),
                "title_episode_underscore",
                0.8,
            ),
            (
                re.compile("^(.+?)\\s+S(\\d+)E(\\d+)\\s+(.+?)(?:\\s*\\[.*\\])?$", re.IGNORECASE),
                "title_season_episode_long",
                0.8,
            ),
            (
                re.compile("^\\[([^\\]]+)\\]\\[([^\\]]+)\\]\\s*(.+?)\\s*(\\d+)", re.IGNORECASE),
                "double_group_title_episode",
                0.8,
            ),
            (
                re.compile(
                    "^(.+?)\\s+(?:Prologue|OVA|Special|Movie)(?:\\s*\\([^)]*\\))?$", re.IGNORECASE
                ),
                "title_special",
                0.8,
            ),
        ]

    def parse_filename(self, filename: str) -> ParsedMetadata | None:
        """파일명에서 메타데이터 추출 (캐시됨)"""
        logger.debug(f"파일명 파싱 시작: {filename}")
        if not filename:
            return None
        path = Path(filename)
        name_without_ext = path.stem
        container = path.suffix.lower()
        for pattern, pattern_type, base_confidence in self.patterns:
            match = pattern.match(name_without_ext)
            if match:
                metadata = self._extract_metadata(match, pattern_type, base_confidence, container)
                if metadata:
                    if not metadata.resolution:
                        full_path_resolution = self._extract_resolution_cached(str(path))
                        if full_path_resolution:
                            metadata.resolution = full_path_resolution
                    return metadata
        fallback_metadata = self._improved_fallback_parse(name_without_ext, container)
        if fallback_metadata and not fallback_metadata.resolution:
            full_path_resolution = self._extract_resolution_cached(str(path))
            if full_path_resolution:
                fallback_metadata.resolution = full_path_resolution
        return fallback_metadata

    def _extract_metadata(
        self, match: re.Match[str], pattern_type: str, base_confidence: float, container: str
    ) -> ParsedMetadata | None:
        """매치된 패턴에서 메타데이터 추출 (최적화됨)"""
        try:
            groups = match.groups()
            if pattern_type == "title_season_episode_resolution_dots":
                title, season, episode, resolution, codec, _ = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    resolution=resolution,
                    codec=codec,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_season_episode_simple":
                title, season, episode = groups
                full_filename = match.string
                resolution = self._extract_resolution_cached(full_filename)
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    resolution=resolution,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_season_episode_space":
                title, season, episode = groups
                full_filename = match.string
                resolution = self._extract_resolution_cached(full_filename)
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    resolution=resolution,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_exx":
                title, episode = groups
                full_filename = match.string
                resolution = self._extract_resolution_cached(full_filename)
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=1,
                    episode=int(episode),
                    resolution=resolution,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_season_episode_resolution_code":
                group, title, season, episode, resolution, code = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    resolution=resolution,
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_season_episode_resolution":
                group, title, season, episode, resolution = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    resolution=resolution,
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_season_episode_code":
                group, title, season, episode, code = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_season_episode":
                group, title, season, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_episode_with_resolution":
                group, title, episode, resolution = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    resolution=resolution,
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_episode_decimal_resolution":
                group, title, episode, resolution = groups
                episode_int = int(float(episode))
                clean_resolution = self._extract_resolution_cached(resolution)
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=episode_int,
                    resolution=clean_resolution,
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_korean":
                title, episode, resolution = groups
                if not resolution:
                    full_filename = match.string
                    resolution = self._extract_resolution_cached(full_filename)
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    resolution=resolution,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_exx_resolution":
                title, episode, resolution = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=1,
                    episode=int(episode),
                    resolution=resolution,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_episode_bracket_resolution":
                group, title, episode, resolution = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    resolution=resolution,
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_episode":
                group, title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_ep":
                title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_special":
                title, episode, special = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    quality=special,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_season_episode_space":
                title, season, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season) if season else 1,
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_season_episode_resolution_code":
                title, season, episode, resolution, code = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    resolution=resolution,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_season_episode_resolution":
                title, season, episode, resolution = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    resolution=resolution,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_season_episode_code":
                title, season, episode, code = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_season_episode":
                title, season, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_episode_nospace":
                group, title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_simple":
                title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_japanese":
                title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_korean_hwa":
                title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_episode_bracket":
                group, title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "group_title_episode_dash":
                group, title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    group=group,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_dash":
                title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_space":
                title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "season_title_episode_korean":
                season, title = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=1,
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_episode_underscore":
                title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_season_episode_long":
                title, season, episode, extra = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    season=int(season),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "double_group_title_episode":
                group1, group2, title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=int(episode),
                    group=f"{group1}][{group2}",
                    container=container,
                    confidence=base_confidence,
                )
            if pattern_type == "title_special":
                title = groups[0]
                return ParsedMetadata(
                    title=self._clean_title_cached(title),
                    episode=None,
                    container=container,
                    confidence=base_confidence,
                )
        except (ValueError, IndexError) as e:
            logger.error(f"메타데이터 추출 오류: {e}")
            return None
        return None

    def _improved_fallback_parse(self, filename: str, container: str) -> ParsedMetadata | None:
        """개선된 fallback 파싱 (캐시됨)"""
        try:
            episode_match = re.search("(\\d{1,2})", filename)
            episode = int(episode_match.group(1)) if episode_match else None
            resolution = self._extract_resolution_cached(filename)
            title = filename
            if episode:
                title = re.sub(f"\\D{episode}\\D", " ", title)
            title = self._clean_title_cached(title)
            return ParsedMetadata(
                title=title,
                episode=episode,
                resolution=resolution,
                container=container,
                confidence=0.4,
            )
        except Exception as e:
            logger.error(f"Fallback 파싱 오류: {e}")
            return None

    def _extract_resolution_cached(self, text: str) -> str | None:
        """텍스트에서 해상도 추출 (캐시됨)"""
        logger.debug(f"해상도 추출 시도: {text}")
        resolution_patterns = [
            ("(\\d{3,4}x\\d{3,4})", "exact"),
            ("\\b(1080p?)\\b", "1080p"),
            ("\\b(720p?)\\b", "720p"),
            ("\\b(480p?)\\b", "480p"),
            ("\\b(\\d{3,4}p)\\b", "p"),
            ("(4K|2160p)", "4k"),
            ("(2K|1440p)", "2k"),
            ("(HD)", "720p"),
            ("(SD)", "480p"),
            ("(\\d{3,4}i)", "interlaced"),
        ]
        for pattern, res_type in resolution_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                resolution = match.group(1).upper()
                logger.debug(f"패턴 매칭: {pattern} -> {resolution} ({res_type})")
                if res_type == "exact":
                    resolution_lower = resolution.lower()
                    if "1920x1080" in resolution_lower or "1080x1920" in resolution_lower:
                        logger.debug(f"정규화: {resolution} -> 1080p")
                        return "1080p"
                    if "1280x720" in resolution_lower or "720x1280" in resolution_lower:
                        logger.debug(f"정규화: {resolution} -> 720p")
                        return "720p"
                    if "854x480" in resolution_lower or "480x854" in resolution_lower:
                        logger.debug(f"정규화: {resolution} -> 480p")
                        return "480p"
                    if "640x480" in resolution_lower:
                        logger.debug(f"정규화: {resolution} -> 480p")
                        return "480p"
                    logger.debug(f"정규화 없음: {resolution}")
                    return resolution
                if res_type == "1080p":
                    logger.debug(f"1080p 반환: {resolution}")
                    return "1080p"
                if res_type == "720p":
                    logger.debug(f"720p 반환: {resolution}")
                    return "720p"
                if res_type == "480p":
                    logger.debug(f"480p 반환: {resolution}")
                    return "480p"
                if res_type == "p":
                    if resolution.upper() in ["080P", "80P"]:
                        return "1080p"
                    if resolution.upper() in ["720P", "20P"]:
                        return "720p"
                    if resolution.upper() in ["480P", "80P"]:
                        return "480p"
                    return resolution
                if res_type == "4k":
                    return "4K"
                if res_type == "2k":
                    return "2K"
                if res_type == "interlaced":
                    return resolution
                return resolution
        return None

    def _clean_title_cached(self, title: str) -> str:
        """제목에서 불필요한 정보 제거 (캐시됨)"""
        if not title:
            return ""
        # 최우선: '.'을 공백으로 변환 (파일명의 점을 공백으로)
        title = re.sub("\\.", " ", title)
        title = re.sub("^\\[([^\\]]+)\\]\\s*", "", title)
        title = re.sub("\\[([^\\]]+)\\]$", "", title)
        title = re.sub("\\.(?=S\\d+E\\d+|E\\d+|EP\\d+)", " ", title)
        title = re.sub("_+", " ", title)
        title = re.sub("\\s+", " ", title)
        title = re.sub("\\b(?:E\\d+|EP\\d+|Episode\\s*\\d+)\\b", "", title, flags=re.IGNORECASE)
        title = re.sub("\\b(?:S\\d+|Season\\s*\\d+)\\b", "", title, flags=re.IGNORECASE)
        title = re.sub("\\b\\d{6,8}\\b", "", title)
        title = self._remove_technical_info_cached(title)
        title = title.strip()
        return re.sub("\\s+", " ", title)

    def _remove_technical_info_cached(self, title: str) -> str:
        """기술적 정보 제거 (캐시됨)"""
        codecs = ["x264", "x265", "H.264", "H.265", "AVC", "HEVC", "DivX", "XviD"]
        for codec in codecs:
            title = re.sub(f"\\b{codec}\\b", "", title, flags=re.IGNORECASE)
        audio_patterns = [
            "\\bAAC\\b",
            "\\bAC3\\b",
            "\\bMP3\\b",
            "\\bFLAC\\b",
            "\\bDTS\\b",
            "\\b\\d+ch\\b",
            "\\b\\d+\\.\\d+ch\\b",
        ]
        for pattern in audio_patterns:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)
        quality_patterns = [
            "\\b(?:WEB-DL|BluRay|DVDRip|TVRip|HDTV|PDTV)\\b",
            "\\b(?:RAW|SUB|DUB|UNCUT|EXTENDED|DIRECTOR\\'S CUT)\\b",
        ]
        for pattern in quality_patterns:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)
        language_patterns = [
            "\\b(?:KOR|JPN|ENG|CHI|GER|FRE|SPA|ITA|RUS)\\b",
            "\\b(?:Korean|Japanese|English|Chinese|German|French|Spanish|Italian|Russian)\\b",
        ]
        for pattern in language_patterns:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)
        return title

    def _extract_resolution(self, text: str) -> str | None:
        """텍스트에서 해상도 추출 (기존 메서드)"""
        return self._extract_resolution_cached(text)

    def _clean_title(self, title: str) -> str:
        """제목에서 불필요한 정보 제거 (기존 메서드)"""
        return self._clean_title_cached(title)

    def _remove_technical_info(self, title: str) -> str:
        """기술적 정보 제거 (기존 메서드)"""
        return self._remove_technical_info_cached(title)

    def get_supported_formats(self) -> list[str]:
        """지원되는 파일 형식 반환"""
        return [
            ".mp4",
            ".mkv",
            ".avi",
            ".mov",
            ".wmv",
            ".m4v",
            ".flv",
            ".webm",
            ".srt",
            ".ass",
            ".ssa",
            ".sub",
            ".idx",
            ".smi",
            ".vtt",
        ]

    def is_video_file(self, filename: str) -> bool:
        """비디오 파일 여부 확인"""
        video_extensions = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v", ".flv", ".webm"]
        return any(filename.lower().endswith(ext) for ext in video_extensions)

    def get_parsing_stats(self, results: list[ParsedMetadata]) -> dict[str, Any]:
        """파싱 통계 반환"""
        if not results:
            return {}
        total_files = len(results)
        successful_parses = len([r for r in results if r.confidence > 0])
        average_confidence = (
            sum(r.confidence for r in results) / total_files if total_files > 0 else 0
        )
        return {
            "total_files": total_files,
            "successful_parses": successful_parses,
            "success_rate": successful_parses / total_files if total_files > 0 else 0,
            "average_confidence": average_confidence,
            "confidence_distribution": {
                "high": len([r for r in results if r.confidence >= 0.8]),
                "medium": len([r for r in results if 0.5 <= r.confidence < 0.8]),
                "low": len([r for r in results if r.confidence < 0.5]),
            },
        }

    def clear_cache(self):
        """캐시를 모두 지웁니다 (메모리 관리용)"""

    def get_cache_info(self) -> dict[str, int]:
        """캐시 정보를 반환합니다"""
        return {}

    def batch_parse(self, filenames: list[str]) -> list[ParsedMetadata | None]:
        """여러 파일명을 일괄 파싱 (테스트 호환성)"""
        results = []
        for filename in filenames:
            result = self.parse_filename(filename)
            results.append(result)
        return results
