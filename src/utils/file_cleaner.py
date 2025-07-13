import re
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

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

@lru_cache(maxsize=4096)
def _cached_guessit_parse(filename: str) -> dict:
    """GuessIt 파싱 결과 캐싱"""
    from guessit import guessit
    return dict(guessit(filename))

@lru_cache(maxsize=2048)
def _cached_title_refine(title: str) -> str:
    """제목 정제 결과 캐싱"""
    # 기본 정제 로직
    clean_title = title.strip()
    
    # 릴리즈 그룹 제거 ([...] 형태)
    clean_title = re.sub(r'\[.*?\]', '', clean_title).strip()
    
    # 해상도 정보 제거 (720p, 1080p 등)
    clean_title = re.sub(r'\b\d{3,4}p\b', '', clean_title, flags=re.IGNORECASE).strip()
    
    # 코덱 정보 제거 (x264, x265, HEVC 등)
    clean_title = re.sub(r'\b(x264|x265|HEVC|AVC|H\.264|H\.265)\b', '', clean_title, flags=re.IGNORECASE).strip()
    
    # 연속된 공백 정리
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    
    return clean_title

def _extract_season_from_title(title: str) -> Optional[int]:
    """
    제목에서 시즌 정보를 추출하는 함수
    
    Args:
        title: 제목 문자열
        
    Returns:
        int or None: 추출된 시즌 번호 또는 None
    """
    if not title:
        return None
    
    # 시즌 추출 패턴들 (우선순위 순서)
    season_patterns = [
        # 숫자 + th/st/nd/rd 패턴 (6th, 1st, 2nd, 3rd 등)
        r'\b(\d{1,2})(?:th|st|nd|rd)\b',
        
        # 숫자 + 기/시즌 패턴 (6기, 6시즌 등)
        r'\b(\d{1,2})(?:기|시즌|철)\b',
        
        # 숫자 + 번째 패턴 (6번째 등)
        r'\b(\d{1,2})번째\b',
        
        # Season/시즌 + 숫자 패턴 (Season 6, 시즌 6 등)
        r'\b(?:Season|시즌)\s*(\d{1,2})\b',
        
        # 단순 숫자 패턴 (제목 끝의 숫자, 주의깊게 사용)
        r'\b(\d{1,2})\s*(?:TV|Series|tv|series)?\s*$'
    ]
    
    for pattern in season_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            try:
                season_num = int(match.group(1))
                # 합리적인 시즌 번호 범위 체크 (1-50)
                if 1 <= season_num <= 50:
                    return season_num
            except (ValueError, IndexError):
                continue
                
    return None

class FileCleaner:
    """파일명 정제 클래스 (성능 최적화 버전)"""
    
    @staticmethod
    def clean_filename_static(file_path):
        """
        캐시된 GuessIt 파싱을 사용한 최적화된 파일명 정제
        ProcessPoolExecutor 호환을 위한 순수 static 메서드
        """
        from pathlib import Path
        
        file_path = Path(file_path)
        filename_stem = file_path.stem  # 확장자 제외한 파일명
        
        # 캐시된 GuessIt 파싱 사용
        meta = _cached_guessit_parse(filename_stem)
        
        # 제목 정제
        title = meta.get('title', '')
        clean_title = _cached_title_refine(title) if title else filename_stem
        
        # 시즌 정보 처리 (GuessIt이 리스트로 반환하는 경우 처리)
        season = meta.get('season', 1)
        if isinstance(season, list):
            season = season[0] if season else 1  # 리스트면 첫 번째 값 사용
        try:
            season = int(season)
        except (ValueError, TypeError):
            season = 1  # 변환 실패 시 기본값
        
        # 연도 정보 처리
        year = meta.get('year')
        if year is not None:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None
        
        # 연도-시즌 혼동 문제 해결
        # 시즌이 1900년 이상이고 연도와 동일하면 연도가 시즌으로 잘못 인식된 것
        if season >= 1900 and year and season == year:
            # 제목에서 시즌 정보 추출 시도
            title_season = _extract_season_from_title(clean_title)
            if title_season:
                season = title_season
                # 로깅
                try:
                    import logging
                    logger = logging.getLogger("animesorter.file_cleaner")
                    logger.info(f"[FileCleaner] Year-season confusion resolved using title: "
                               f"'{clean_title}' → season {season}")
                except:
                    pass
            else:
                # 제목에서 시즌을 찾지 못하면 기본값 1 사용
                season = 1
                # 로깅
                try:
                    import logging
                    logger = logging.getLogger("animesorter.file_cleaner")
                    logger.info(f"[FileCleaner] Year-season confusion detected in '{filename_stem}': "
                               f"season {year} corrected to 1 (no season found in title)")
                except:
                    pass
        
        # GuessIt이 시즌을 인식하지 못한 경우 제목에서 추출 시도
        elif season == 1 and meta.get('season') is None:
            title_season = _extract_season_from_title(clean_title)
            if title_season:
                season = title_season
                # 로깅
                try:
                    import logging
                    logger = logging.getLogger("animesorter.file_cleaner")
                    logger.info(f"[FileCleaner] Season extracted from title: "
                               f"'{clean_title}' → season {season}")
                except:
                    pass
        
        # 에피소드 정보 처리 (GuessIt이 리스트로 반환하는 경우 처리)
        episode = meta.get('episode')
        if isinstance(episode, list):
            episode = episode[0] if episode else None  # 리스트면 첫 번째 값 사용
        if episode is not None:
            try:
                episode = int(episode)
            except (ValueError, TypeError):
                episode = None  # 변환 실패 시 None
        
        # CleanResult 객체 생성
        return CleanResult(
            title=clean_title,
            original_filename=file_path,
            season=season,
            episode=episode,
            year=year,
            is_movie=meta.get('type') == 'movie',
            extra_info=dict(meta)  # 원본 GuessIt 결과 보존
        ) 