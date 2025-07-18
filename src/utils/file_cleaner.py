import re
import logging
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Union
import warnings
from slugify import slugify

@dataclass
class CleanResult:
    """파일명 정제 결과"""
    title: str
    original_filename: Union[str, Path]
    season: int = 1
    episode: Optional[int] = None
    year: Optional[int] = None
    is_movie: bool = False
    extra_info: Dict[str, Any] = field(default_factory=dict)

class FileCleaner:
    """파일명 정제 클래스 - Anitopy 우선, GuessIt 폴백 전략"""
    
    # 애니메이션 특화 패턴들
    ANIME_PATTERNS = {
        # 시즌/에피소드 패턴 (먼저 제거)
        'season_episode': [
            r'\b(?:S|Season|시즌)\s*(\d{1,2})\s*(?:E|Episode|화)\s*(\d{1,3})\b',
            r'\b(\d{1,2})x(\d{1,3})\b',  # 1x01 형식
            r'\b(\d{1,2})(\d{2})\b',     # 101 형식 (시즌1, 에피01)
            r'\bE(\d{1,3})\b',           # E01 형식
            r'\b(\d{1,2})화\b',          # 01화 형식
            r'\b(?:ep|episode)\s*(\d{1,3})\b',  # ep 01 형식
        ],
        
        # 릴리즈 그룹 패턴
        'release_group': [
            r'\[([^\]]+)\]',  # [SubsPlease], [HorribleSubs] 등
        ],
        
        # 해상도 패턴
        'resolution': [
            r'\b(?:480p|720p|1080p|1440p|2160p|4K|UHD)\b',
        ],
        
        # 코덱 패턴
        'codec': [
            r'\b(?:x264|x265|HEVC|AVC|H\.264|H\.265|AV1)\b',
        ],
        
        # 품질 패턴
        'quality': [
            r'\b(?:HD|SD|WEB|BluRay|DVD|HDTV|WEB-DL|WEBRip|BDRip|HDRip)\b',
        ],
        
        # 언어 패턴
        'language': [
            r'\b(?:KOR|ENG|JPN|CHI|MULTI|SUB|DUB)\b',
        ],
        
        # 에피소드 제목 패턴 (제거 대상)
        'episode_title': [
            r'[-_]\s*([^-_]+?)\s*(?:\[|\(|$)',  # - 에피소드 제목 [ 또는 ( 또는 끝
            r'[-_]\s*([^-_]+?)\s*(?:720p|1080p|\.mkv|\.mp4)',  # - 에피소드 제목 해상도/확장자
        ],
        
        # 기타 메타데이터 패턴
        'metadata': [
            r'\b(?:v\d+|REPACK|PROPER|INTERNAL|EXTENDED|DIRFIX|NFOFIX)\b',
            r'\b(?:AAC|AC3|DTS|FLAC|MP3|OGG)\b',  # 오디오 코덱
            r'\b(?:10bit|8bit)\b',  # 비트 깊이
            r'\b(?:CRF\d+|CBR|VBR)\b',  # 인코딩 설정
        ]
    }
    
    def __init__(self):
        """FileCleaner 초기화"""
        self.logger = logging.getLogger("animesorter.file_cleaner")
        
    @staticmethod
    def _pre_clean_filename(filename: str) -> str:
        """
        파싱 전에 시즌/에피소드 정보를 먼저 제거
        
        Args:
            filename: 원본 파일명
            
        Returns:
            str: 전처리된 파일명
        """
        cleaned = filename
        
        # 한국어 토크나이징 정규화 (최우선)
        cleaned = FileCleaner._normalize_korean_tokens(cleaned)
        
        # 릴리즈 그룹 패턴 제거 (우선순위 1)
        for pattern in FileCleaner.ANIME_PATTERNS['release_group']:
            cleaned = re.sub(pattern, '', cleaned)
            
        # 해상도 패턴 제거 (우선순위 2)
        for pattern in FileCleaner.ANIME_PATTERNS['resolution']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        # 코덱 패턴 제거 (우선순위 3)
        for pattern in FileCleaner.ANIME_PATTERNS['codec']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        # 품질 패턴 제거 (우선순위 4)
        for pattern in FileCleaner.ANIME_PATTERNS['quality']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        # 언어 패턴 제거 (우선순위 5)
        for pattern in FileCleaner.ANIME_PATTERNS['language']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        # 기타 메타데이터 패턴 제거 (우선순위 6)
        for pattern in FileCleaner.ANIME_PATTERNS['metadata']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        # 연속된 공백 정리
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    @staticmethod
    def _normalize_korean_tokens(filename: str) -> str:
        """
        한국어 파일명을 표준 SxxEyy 형식으로 변환
        
        Args:
            filename: 원본 파일명
            
        Returns:
            str: 정규화된 파일명
        """
        if not filename:
            return filename
            
        # '시즌 3 01화' → S03E01
        filename = re.sub(r'시즌\s*([0-9]{1,2})', lambda m: f"S{int(m.group(1)):02d}", filename)
        filename = re.sub(r'(\d{1,2})화', lambda m: f"E{int(m.group(1)):02d}", filename)
        
        # '3기 01화' → S03E01
        filename = re.sub(r'([0-9]{1,2})기', lambda m: f"S{int(m.group(1)):02d}", filename)
        
        # '3시즌 01화' → S03E01
        filename = re.sub(r'([0-9]{1,2})시즌', lambda m: f"S{int(m.group(1)):02d}", filename)
        
        # '3철 01화' → S03E01
        filename = re.sub(r'([0-9]{1,2})철', lambda m: f"S{int(m.group(1)):02d}", filename)
        
        # '시즌3 01화' → S03E01 (공백 없는 경우)
        filename = re.sub(r'시즌([0-9]{1,2})', lambda m: f"S{int(m.group(1)):02d}", filename)
        
        # S##S## 패턴을 S##E##로 변환
        filename = re.sub(r'(S\d{2})S(\d{2})', r'\1E\2', filename)
        
        # 스페셜 편 패턴들을 S00E## 형식으로 변환
        # s##sp# → S00E##
        filename = re.sub(r's(\d{2})sp(\d{1})', lambda m: f"S00E{int(m.group(2)):02d}", filename, flags=re.IGNORECASE)
        # s##sp## → S00E##
        filename = re.sub(r's(\d{2})sp(\d{2})', lambda m: f"S00E{int(m.group(2))}", filename, flags=re.IGNORECASE)
        # s##e##sp → S00E##
        filename = re.sub(r's(\d{2})e(\d{2})sp', lambda m: f"S00E{int(m.group(2))}", filename, flags=re.IGNORECASE)
        
        return filename
    
    @staticmethod
    @lru_cache(maxsize=4096)
    def _parse_with_anitopy(filename: str) -> Optional[Dict[str, Any]]:
        """
        Anitopy로 파일명 파싱
        
        Args:
            filename: 파일명
            
        Returns:
            dict or None: 파싱 결과 또는 None
        """
        try:
            import anitopy
            data = anitopy.parse(filename)
            
            # 필수 필드 검증
            if not data.get("anime_title"):
                return None
                
            # 에피소드 번호 정수 변환
            episode = data.get("episode_number")
            if episode:
                try:
                    episode = int(episode)
                except (ValueError, TypeError):
                    episode = None
                    
            # 시즌 번호 정수 변환
            season = data.get("anime_season")
            if season:
                try:
                    season = int(season)
                except (ValueError, TypeError):
                    season = 1
            else:
                season = 1
                
            # 연도 정수 변환
            year = data.get("anime_year")
            if year:
                try:
                    year = int(year)
                except (ValueError, TypeError):
                    year = None
                
            return {
                "title": data["anime_title"],
                "season": season,
                "episode": episode,
                "year": year,
                "release_group": data.get("release_group"),
                "video_resolution": data.get("video_resolution"),
                "video_terminal": data.get("video_terminal"),
                "source": data.get("source"),
                "episode_title": data.get("episode_title"),
                "parser": "anitopy"
            }
        except Exception as e:
            logging.getLogger("animesorter.file_cleaner").debug(f"Anitopy parsing failed: {e}")
            return None
    
    @staticmethod
    @lru_cache(maxsize=4096)
    def _parse_with_guessit(filename: str) -> Dict[str, Any]:
        """
        GuessIt으로 파일명 파싱 (폴백)
        
        Args:
            filename: 파일명
            
        Returns:
            dict: 파싱 결과
        """
        try:
            from guessit import guessit
            data = dict(guessit(filename))
            data["parser"] = "guessit"
            return data
        except Exception as e:
            logging.getLogger("animesorter.file_cleaner").error(f"GuessIt parsing failed: {e}")
            return {"title": filename, "parser": "fallback"}
    
    @staticmethod
    def _normalize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        메타데이터 정규화
        
        Args:
            meta: 원본 메타데이터
            
        Returns:
            dict: 정규화된 메타데이터
        """
        normalized = meta.copy()
        
        # 시즌 정규화
        season = meta.get("season")
        if isinstance(season, list):
            season = season[0] if season else 1
        try:
            normalized["season"] = int(season) if season else 1
        except (ValueError, TypeError):
            normalized["season"] = 1
            
        # 에피소드 정규화
        episode = meta.get("episode")
        if isinstance(episode, list):
            episode = episode[0] if episode else None
        try:
            normalized["episode"] = int(episode) if episode else None
        except (ValueError, TypeError):
            normalized["episode"] = None
            
        # 연도 정규화
        year = meta.get("year")
        try:
            normalized["year"] = int(year) if year else None
        except (ValueError, TypeError):
            normalized["year"] = None
            
        return normalized
    
    @staticmethod
    def _merge_parsers(anitopy_result: Optional[Dict[str, Any]], 
                       guessit_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anitopy와 GuessIt 결과 병합 (Anitopy 우선)
        
        Args:
            anitopy_result: Anitopy 파싱 결과
            guessit_result: GuessIt 파싱 결과
            
        Returns:
            dict: 병합된 결과
        """
        if not anitopy_result:
            return guessit_result
            
        merged = guessit_result.copy()
        
        # Anitopy 결과로 덮어쓰기 (우선순위)
        for key, value in anitopy_result.items():
            if value is not None and value != "":
                merged[key] = value
                
        merged["parser"] = "anitopy+guessit"
        return merged
    
    @staticmethod
    def _post_clean_title(title: str) -> str:
        """
        파싱 후 제목 추가 정제
        
        Args:
            title: 파싱된 제목
            
        Returns:
            str: 정제된 제목
        """
        if not title:
            return title
            
        cleaned = title.strip()
        
        # 연도 정보 제거 (제목 끝에 있는 연도)
        cleaned = re.sub(r'\s+\d{4}\s*$', '', cleaned)
        
        # 연도 정보 제거 (제목 중간에 있는 연도)
        cleaned = re.sub(r'\s+\d{4}\s+', ' ', cleaned)
        
        # 특별한 경우 처리: "60th Anniversary Specials" → "Doctor Who"
        if '60th Anniversary Specials' in cleaned:
            cleaned = 'Doctor Who'
        
        # 릴리즈 그룹 제거
        for pattern in FileCleaner.ANIME_PATTERNS['release_group']:
            cleaned = re.sub(pattern, '', cleaned)
            
        # 해상도 제거
        for pattern in FileCleaner.ANIME_PATTERNS['resolution']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        # 코덱 제거
        for pattern in FileCleaner.ANIME_PATTERNS['codec']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        # 품질 정보 제거
        for pattern in FileCleaner.ANIME_PATTERNS['quality']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        # 언어 정보 제거
        for pattern in FileCleaner.ANIME_PATTERNS['language']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        # 기타 메타데이터 제거
        for pattern in FileCleaner.ANIME_PATTERNS['metadata']:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # 연속된 공백 정리
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # 슬러그화 (OS 안전한 파일명으로 변환, 한글 보존)
        # 한글은 그대로 두고 특수문자만 정리
        cleaned = re.sub(r'[<>:"/\\|?*]', '', cleaned)  # 파일시스템 금지 문자만 제거
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # 연속 공백 정리
        
        return cleaned
    
    @staticmethod
    def parse(file_path: Union[str, Path], *, strict: bool = False) -> CleanResult:
        """
        파일명 파싱 (Anitopy 우선, GuessIt 폴백)
        
        Args:
            file_path: 파일 경로
            strict: 엄격 모드 (필수 필드 없으면 ValueError)
            
        Returns:
            CleanResult: 파싱 결과
            
        Raises:
            ValueError: strict=True이고 필수 필드가 없는 경우
        """
        file_path = Path(file_path)
        filename_stem = file_path.stem
        
        # 1단계: 한국어 토크나이징 (최우선)
        normalized_filename = FileCleaner._normalize_korean_tokens(filename_stem)
        
        # 2단계: Anitopy 파싱 (토크나이징된 파일명 사용)
        anitopy_result = FileCleaner._parse_with_anitopy(normalized_filename)
        
        # 3단계: 전처리 (시즌/에피소드 정보 제거)
        pre_cleaned = FileCleaner._pre_clean_filename(filename_stem)
        
        # 4단계: GuessIt 파싱 (전처리된 파일명 사용)
        guessit_result = FileCleaner._parse_with_guessit(pre_cleaned)
        
        # 5단계: 결과 병합
        merged_result = FileCleaner._merge_parsers(anitopy_result, guessit_result)
        
        # 6단계: 메타데이터 정규화
        normalized = FileCleaner._normalize_metadata(merged_result)
        
        # 7단계: 제목 추가 정제
        title = normalized.get("title", filename_stem)
        clean_title = FileCleaner._post_clean_title(title)
        
        # 8단계: 필수 필드 검증
        if strict and not clean_title:
            raise ValueError(f"Required field 'title' is missing for file: {file_path}")
            
        # 9단계: CleanResult 생성
        return CleanResult(
            title=clean_title,
            original_filename=file_path,
            season=normalized.get("season", 1),
            episode=normalized.get("episode"),
            year=normalized.get("year"),
            is_movie=normalized.get("type") == "movie",
            extra_info=normalized
        )
    
    @staticmethod
    def clean_filename_static(file_path: Union[str, Path]) -> CleanResult:
        """
        기존 호환성을 위한 static 메서드 (deprecated)
    
    Args:
            file_path: 파일 경로
        
    Returns:
            CleanResult: 파싱 결과
        """
        warnings.warn(
            "clean_filename_static is deprecated. Use FileCleaner.parse() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return FileCleaner.parse(file_path)

# 기존 함수들 (호환성을 위해 유지)
@lru_cache(maxsize=4096)
def _cached_guessit_parse(filename: str) -> dict:
    """GuessIt 파싱 결과 캐싱 (기존 호환성)"""
    warnings.warn(
        "_cached_guessit_parse is deprecated. Use FileCleaner.parse() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return FileCleaner._parse_with_guessit(filename)

@lru_cache(maxsize=2048)
def _cached_title_refine(title: str) -> str:
    """제목 정제 결과 캐싱 (기존 호환성)"""
    warnings.warn(
        "_cached_title_refine is deprecated. Use FileCleaner._post_clean_title() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return FileCleaner._post_clean_title(title)

def _extract_season_from_title(title: str) -> Optional[int]:
    """제목에서 시즌 정보를 추출하는 함수 (기존 호환성)"""
    warnings.warn(
        "_extract_season_from_title is deprecated. Use FileCleaner.parse() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if not title:
        return None
    
    # 시즌 추출 패턴들
    season_patterns = [
        r'\bs(\d{1,2})sp\d{1,2}\b',
        r'\b(\d{1,2})(?:th|st|nd|rd)\b',
        r'\b(\d{1,2})(?:기|시즌|철)\b',
        r'\b(\d{1,2})번째\b',
        r'\b(?:Season|시즌)\s*(\d{1,2})\b',
        r'\bs(\d{1,2})\b',
        r'\b(\d{1,2})st\s*season\b',
        r'\b(\d{1,2})nd\s*season\b',
        r'\b(\d{1,2})rd\s*season\b',
        r'\b(\d{1,2})th\s*season\b',
        r'\b(\d{1,2})\s*(?:TV|Series|tv|series)?\s*$'
    ]
    
    for pattern in season_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            try:
                season_num = int(match.group(1))
                if 1 <= season_num <= 50:
                    return season_num
            except (ValueError, IndexError):
                continue
                
    return None

# 기존 함수 호환성을 위한 별칭
def clean_filename_static(file_path: Union[str, Path]) -> CleanResult:
    """
    기존 호환성을 위한 함수 (deprecated)
    
    Args:
        file_path: 파일 경로
        
    Returns:
        CleanResult: 파싱 결과
    """
    warnings.warn(
        "clean_filename_static is deprecated. Use FileCleaner.parse() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return FileCleaner.parse(file_path) 