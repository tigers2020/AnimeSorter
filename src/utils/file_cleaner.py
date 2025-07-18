import re
import warnings
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Union

@dataclass
class CleanResult:
    """파일명 정제 결과"""
    title: str
    original_filename: str | Path
    season: int = 1
    episode: Optional[int] = None
    year: Optional[int] = None
    is_movie: bool = False
    extra_info: Dict[str, Any] = field(default_factory=dict)

# 멀티프로세싱을 위한 완전히 독립적인 함수들 (캐싱 없음)
def parse_filename_standalone_simple(path: Union[str, Path]) -> CleanResult:
    """
    멀티프로세싱용 간단한 파싱 함수 (캐싱 없음, pickle 안전)
    
    Args:
        path: 파일 경로
        
    Returns:
        CleanResult: 정제된 결과
    """
    filename = Path(path).name
    stem = Path(path).stem
    
    # 1단계: Anitopy 파싱 (애니메이션 특화)
    anitopy_result = _anitopy_parse_simple(stem)
    
    # 2단계: GuessIt 폴백 (필요시)
    if anitopy_result and _validate_parsed_data_simple(anitopy_result):
        parsed_data = anitopy_result
        parser_used = "anitopy"
    else:
        guessit_result = _guessit_parse_simple(stem)
        if guessit_result and _validate_parsed_data_simple(guessit_result):
            parsed_data = guessit_result
            parser_used = "guessit"
        else:
            # 두 파서 모두 실패 - 기본값으로 처리
            parsed_data = {"title": stem, "raw_data": {}}
            parser_used = "fallback"
    
    # 3단계: 데이터 정규화 및 정제
    result = _normalize_and_clean_simple(parsed_data, filename)
    result.extra_info["parser_used"] = parser_used
    
    return result

def _anitopy_parse_simple(filename: str) -> Optional[dict]:
    """Anitopy 파싱 (멀티프로세싱용, 캐싱 없음)"""
    try:
        from anitopy import parse as anitopy_parse
        data = anitopy_parse(filename)
        
        # 필수 필드 검증
        if not data.get("anime_title"):
            return None
            
        return {
            "title": data["anime_title"],
            "season": data.get("anime_season"),
            "episode": data.get("episode_number"),
            "year": data.get("anime_year"),
            "anime_type": data.get("anime_type"),
            "release_group": data.get("release_group"),
            "video_resolution": data.get("video_resolution"),
            "video_term": data.get("video_term"),
            "audio_term": data.get("audio_term"),
            "file_extension": data.get("file_extension"),
            "episode_title": data.get("episode_title"),
            "raw_data": data
        }
    except Exception:
        return None

def _guessit_parse_simple(filename: str) -> Optional[dict]:
    """GuessIt 파싱 (멀티프로세싱용, 캐싱 없음)"""
    try:
        from guessit import guessit
        data = guessit(filename)
        
        # 필수 필드 검증
        if not data.get("title"):
            return None
            
        return {
            "title": data["title"],
            "season": data.get("season"),
            "episode": data.get("episode"),
            "year": data.get("year"),
            "release_group": data.get("release_group"),
            "video_resolution": data.get("screen_size"),
            "video_term": data.get("video_codec"),
            "audio_term": data.get("audio_codec"),
            "file_extension": data.get("container"),
            "episode_title": data.get("episode_title"),
            "raw_data": data
        }
    except Exception:
        return None

def _validate_parsed_data_simple(data: dict) -> bool:
    """파싱된 데이터의 유효성 검증 (멀티프로세싱용)"""
    # 필수 필드: title
    if not data.get("title"):
        return False
    return True

def _normalize_and_clean_simple(parsed_data: dict, original_filename: str) -> CleanResult:
    """파싱된 데이터를 정규화하고 정제 (멀티프로세싱용)"""
    title = parsed_data.get("title", "")
    
    # 1단계: 기본 정제 (기술적 정보 제거)
    title = _remove_technical_info_simple(title)
    
    # 2단계: 에피소드 제목 제거
    title = _remove_episode_titles_simple(title)
    
    # 3단계: 릴리즈 그룹 제거
    title = _remove_release_groups_simple(title)
    
    # 4단계: 최종 정리
    title = _final_cleanup_simple(title)
    
    # 5단계: 데이터 정규화
    season = _normalize_season_simple(parsed_data.get("season"))
    episode = _normalize_episode_simple(parsed_data.get("episode"))
    year = _normalize_year_simple(parsed_data.get("year"))
    
    # 6단계: 영화 여부 판단
    is_movie = _is_movie_simple(parsed_data, title)
    
    return CleanResult(
        title=title,
        original_filename=original_filename,
        season=season,
        episode=episode,
        year=year,
        is_movie=is_movie,
        extra_info={
            "original_title": parsed_data.get("title", ""),
            "release_group": parsed_data.get("release_group"),
            "video_resolution": parsed_data.get("video_resolution"),
            "video_term": parsed_data.get("video_term"),
            "audio_term": parsed_data.get("audio_term"),
            "file_extension": parsed_data.get("file_extension"),
            "episode_title": parsed_data.get("episode_title"),
        }
    )

def _is_movie_simple(parsed_data: dict, title: str) -> bool:
    """영화 여부 판단 (멀티프로세싱용)"""
    # 1. 파싱된 데이터에서 확인
    anime_type = parsed_data.get("anime_type")
    if anime_type and isinstance(anime_type, str):
        anime_type = anime_type.lower()
        if anime_type in ["movie", "film", "theatrical"]:
            return True
    
    # 2. 제목에서 키워드 확인
    movie_keywords = ["movie", "film", "theatrical", "ova", "special"]
    title_lower = title.lower()
    for keyword in movie_keywords:
        if keyword in title_lower:
            return True
    
    # 3. 에피소드 정보가 없으면 영화로 간주
    if parsed_data.get("episode") is None and parsed_data.get("season") is None:
        return True
    
    return False

def _remove_technical_info_simple(title: str) -> str:
    """기술적 정보 제거 (멀티프로세싱용)"""
    # 기술적 정보 패턴들
    patterns = [
        r'\b(480p|720p|1080p|1440p|2160p|4K|UHD)\b',
        r'\b(x264|x265|HEVC|AVC|H\.264|H\.265)\b',
        r'\b(AAC|AC3|FLAC|DTS|OPUS)\b',
        r'\b(BluRay|WEB-DL|HDRip|BRRip|DVDRip)\b',
        r'\b(10bit|8bit)\b',
        r'\b(Subbed|Dubbed|Dual Audio)\b',
        r'\b(UNCENSORED|CENSORED)\b',
        r'\b(Complete|Batch)\b',
        r'\b(OVA|OAD|ONA|Movie|Special)\b',
        r'\b(Season|S\d+|Episode|E\d+)\b',
        r'\b(EP?\d+|Episode\s*\d+)\b',
        r'\b(Vol\.?\d+|Volume\s*\d+)\b',
        r'\b(CD\d+|Disc\s*\d+)\b',
        r'\b(REPACK|PROPER|FINAL|REAL)\b',
        r'\b(REMASTERED|EXTENDED|DIRECTOR\'S CUT)\b',
        r'\b(UNCUT|CUT)\b',
        r'\b(DUAL|MULTI)\b',
        r'\b(ENG|JPN|KOR|CHI)\b',
        r'\b(HD|SD|LD)\b',
        r'\b(MP4|MKV|AVI|MOV|WMV|FLV)\b',
        r'\b(CRC32|MD5|SHA1)\b',
        r'\b(RAR|ZIP|7Z)\b',
        r'\b(\.part\d+\.rar|\.r\d+)\b',
        r'\b(Multi-Subs|Multiple Subtitle)\b',
    ]
    
    for pattern in patterns:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    
    return title

def _remove_episode_titles_simple(title: str) -> str:
    """에피소드 제목 제거 (멀티프로세싱용)"""
    # 에피소드 제목 패턴들
    patterns = [
        r'-\s*([^-]+?)\s*(?:\[|\(|\{|$)',
        r'「([^」]+)」',
        r'"([^"]+)"',
        r"'([^']+)'",
    ]
    
    for pattern in patterns:
        title = re.sub(pattern, '', title)
    
    return title

def _remove_release_groups_simple(title: str) -> str:
    """릴리즈 그룹 제거 (멀티프로세싱용)"""
    # 릴리즈 그룹 패턴들
    patterns = [
        r'\[([^\]]+)\]',
        r'\(([^)]+)\)',
        r'\{([^}]+)\}',
    ]
    
    for pattern in patterns:
        title = re.sub(pattern, '', title)
    
    return title

def _final_cleanup_simple(title: str) -> str:
    """최종 정리 (멀티프로세싱용)"""
    # 연속된 공백을 하나로
    title = re.sub(r'\s+', ' ', title)
    # 연속된 구두점을 하나로
    title = re.sub(r'[._-]+', '.', title)
    # 앞뒤 공백 제거
    title = title.strip()
    # 빈 문자열이면 원본 반환
    if not title:
        return title
    # 마지막 구두점 제거
    title = re.sub(r'[._-]+$', '', title)
    # 빈 대괄호, 소괄호, 중괄호 제거
    title = re.sub(r'\s*[\[\]\(\)\{\}]\s*', '', title)
    # 다시 공백 정리
    title = re.sub(r'\s+', ' ', title).strip()
    # 연속된 점 제거
    title = re.sub(r'\s*\.\s*', ' ', title)
    # 최종 공백 정리
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def _normalize_season_simple(season) -> int:
    """시즌 정규화 (멀티프로세싱용)"""
    if season is None:
        return 1
    try:
        season_int = int(season)
        return max(1, season_int)
    except (ValueError, TypeError):
        return 1

def _normalize_episode_simple(episode) -> Optional[int]:
    """에피소드 정규화 (멀티프로세싱용)"""
    if episode is None:
        return None
    try:
        episode_int = int(episode)
        return max(1, episode_int)
    except (ValueError, TypeError):
        return None

def _normalize_year_simple(year) -> Optional[int]:
    """연도 정규화 (멀티프로세싱용)"""
    if year is None:
        return None
    try:
        year_int = int(year)
        # 합리적인 연도 범위 (1900-2030)
        if 1900 <= year_int <= 2030:
            return year_int
        return None
    except (ValueError, TypeError):
        return None

class FileCleaner:
    """파일명 정제 클래스 - Anitopy 우선, GuessIt 폴백 전략"""
    
    # 강화된 정제 패턴들
    RELEASE_GROUP_PATTERNS = [
        r'\[([^\]]+)\]',  # [SubsPlease], [HorribleSubs] 등
        r'\(([^)]+)\)',   # (SubsPlease), (HorribleSubs) 등
        r'\{([^}]+)\}',   # {SubsPlease}, {HorribleSubs} 등
    ]
    
    TECHNICAL_PATTERNS = [
        r'\b(480p|720p|1080p|1440p|2160p|4K|UHD)\b',
        r'\b(x264|x265|HEVC|AVC|H\.264|H\.265)\b',
        r'\b(AAC|AC3|FLAC|DTS|OPUS)\b',
        r'\b(BluRay|WEB-DL|HDRip|BRRip|DVDRip)\b',
        r'\b(10bit|8bit)\b',
        r'\b(Subbed|Dubbed|Dual Audio)\b',
        r'\b(UNCENSORED|CENSORED)\b',
        r'\b(Complete|Batch)\b',
        r'\b(OVA|OAD|ONA|Movie|Special)\b',
        r'\b(Season|S\d+|Episode|E\d+)\b',
        r'\b(\d{4})\b',  # 연도
        r'\b(EP?\d+|Episode\s*\d+)\b',  # 에피소드 번호
        r'\b(Vol\.?\d+|Volume\s*\d+)\b',  # 볼륨
        r'\b(CD\d+|Disc\s*\d+)\b',  # CD/Disc
        r'\b(REPACK|PROPER|FINAL|REAL)\b',
        r'\b(REMASTERED|EXTENDED|DIRECTOR\'S CUT)\b',
        r'\b(UNCUT|CUT)\b',
        r'\b(DUAL|MULTI)\b',
        r'\b(ENG|JPN|KOR|CHI)\b',  # 언어 코드
        r'\b(HD|SD|LD)\b',
        r'\b(MP4|MKV|AVI|MOV|WMV|FLV)\b',
        r'\b(CRC32|MD5|SHA1)\b',
        r'\b(RAR|ZIP|7Z)\b',
        r'\b(\.part\d+\.rar|\.r\d+)\b',  # 압축 파일 파트
        r'\b(Multi-Subs|Multiple Subtitle)\b',  # 다중 자막
    ]
    
    EPISODE_TITLE_PATTERNS = [
        r'-\s*([^-]+?)\s*(?:\[|\(|\{|$)',  # - 에피소드 제목 [기술정보]
        r'「([^」]+)」',  # 일본식 괄호
        r'"([^"]+)"',  # 쌍따옴표
        r"'([^']+)'",  # 홑따옴표
    ]
    
    @staticmethod
    def parse(path: Union[str, Path], *, strict: bool = False) -> CleanResult:
        """
        2단계 파싱 전략: Anitopy 우선 → GuessIt 폴백
        
        Args:
            path: 파일 경로
            strict: True면 필수 필드 없을 때 ValueError 발생
            
        Returns:
            CleanResult: 정제된 결과
            
        Raises:
            ValueError: strict=True이고 필수 필드가 없을 때
        """
        return parse_filename_standalone_simple(path)
    
    @staticmethod
    def _validate_parsed_data(data: dict) -> bool:
        """파싱된 데이터의 유효성 검증"""
        return _validate_parsed_data_simple(data)
    
    @staticmethod
    def _normalize_and_clean(parsed_data: dict, original_filename: str) -> CleanResult:
        """파싱된 데이터를 정규화하고 정제"""
        return _normalize_and_clean_simple(parsed_data, original_filename)
    
    @staticmethod
    def _remove_technical_info(title: str) -> str:
        """기술적 정보 제거"""
        return _remove_technical_info_simple(title)
    
    @staticmethod
    def _remove_episode_titles(title: str) -> str:
        """에피소드 제목 제거"""
        return _remove_episode_titles_simple(title)
    
    @staticmethod
    def _remove_release_groups(title: str) -> str:
        """릴리즈 그룹 제거"""
        return _remove_release_groups_simple(title)
    
    @staticmethod
    def _final_cleanup(title: str) -> str:
        """최종 정리 (연속된 공백, 구두점 정리)"""
        return _final_cleanup_simple(title)
    
    @staticmethod
    def _normalize_season(season) -> int:
        """시즌 정규화"""
        return _normalize_season_simple(season)
    
    @staticmethod
    def _normalize_episode(episode) -> Optional[int]:
        """에피소드 정규화"""
        return _normalize_episode_simple(episode)
    
    @staticmethod
    def _normalize_year(year) -> Optional[int]:
        """연도 정규화"""
        return _normalize_year_simple(year)
    
    @staticmethod
    def _is_movie(parsed_data: dict, title: str) -> bool:
        """영화 여부 판단"""
        return _is_movie_simple(parsed_data, title)
    
    @staticmethod
    def clean_filename_static(filename: str | Path) -> CleanResult:
        """
        파일명 정제 (정적 메서드) - 하위 호환성 유지
        
        Args:
            filename: 파일 경로 또는 파일명
            
        Returns:
            CleanResult: 정제된 결과
        """
        warnings.warn(
            "clean_filename_static is deprecated. Use FileCleaner.parse() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return parse_filename_standalone_simple(filename)

# 하위 호환성을 위한 함수들
def clean_filename(filename: str | Path) -> CleanResult:
    """파일명 정제 함수 (하위 호환성)"""
    return FileCleaner.parse(filename)

def clean_filename_static(filename: str | Path) -> CleanResult:
    """파일명 정제 함수 (하위 호환성)"""
    return FileCleaner.clean_filename_static(filename) 