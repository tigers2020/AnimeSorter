"""
파일명 정제 모듈

파일명에서 메타데이터 검색에 필요한 정보 추출
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from src.exceptions import FileCleanerError


@dataclass
class CleanResult:
    """파일명 정제 결과를 저장하는 데이터 클래스"""
    title: str                      # 정제된 제목 (검색용)
    original_filename: str          # 원본 파일명
    season: int = 1                 # 시즌 번호 (기본값: 1)
    episode: Optional[int] = None   # 에피소드 번호
    year: Optional[int] = None      # 연도
    is_movie: bool = False          # 영화 여부
    extra_info: Dict = field(default_factory=dict)  # 추가 정보


# 릴리즈 그룹 패턴 (대괄호로 둘러싸인 텍스트)
RELEASE_GROUP_PATTERN = r'\[([^\]]+)\]'

# 해상도 패턴 (720p, 1080p, 2160p 등)
RESOLUTION_PATTERN = r'\b(480p|720p|1080p|2160p|4K)\b'

# 코덱 패턴 (x264, x265, HEVC 등)
CODEC_PATTERN = r'\b(x264|x265|HEVC|AVC|FLAC|AAC)\b'

# 시즌/에피소드 패턴 (S01E01, 1x01 등 다양한 형식)
SEASON_EPISODE_PATTERNS = [
    r'S(\d{1,2})E(\d{1,2})',        # S01E01 형식
    r'(\d{1,2})x(\d{1,2})',          # 1x01 형식
    r'- (\d{1,2})(\d{2}) -',         # - 102 - 형식 (시즌 1, 에피소드 02)
    r'E(\d{1,3})',                   # E01 형식 (시즌 정보 없음)
]

# 연도 패턴 (괄호 안의 4자리 연도)
YEAR_PATTERN = r'\((\d{4})\)|\[(\d{4})\]|\.(\d{4})\.'

# 영화/특별편 키워드
MOVIE_KEYWORDS = ['movie', 'film', 'theatrical', 'ova', 'special']


def clean_filename(filename: str | Path) -> CleanResult:
    """
    파일명을 정제하여 검색용 제목과 메타데이터를 추출
    
    Args:
        filename: 파일 경로 또는 파일명 문자열
        
    Returns:
        CleanResult: 정제된 결과 객체
        
    Raises:
        FileCleanerError: 파일명 정제 중 오류 발생 시
    """
    try:
        # 파일 경로인 경우 파일명만 추출
        if isinstance(filename, Path):
            original_filename = filename.name
            filename_without_ext = filename.stem
        else:
            original_filename = filename
            filename_without_ext = Path(filename).stem
            
        logger.debug(f"정제 시작: {original_filename}")
        
        # 작업용 변수에 복사
        clean_name = filename_without_ext
        
        # 결과 객체 초기화
        result = CleanResult(
            title="",
            original_filename=original_filename
        )
        
        # 1. 릴리즈 그룹 제거
        clean_name = re.sub(RELEASE_GROUP_PATTERN, '', clean_name)
        
        # 2. 해상도 제거
        clean_name = re.sub(RESOLUTION_PATTERN, '', clean_name)
        
        # 3. 코덱 제거
        clean_name = re.sub(CODEC_PATTERN, '', clean_name)
        
        # 4. 시즌/에피소드 정보 추출
        for pattern in SEASON_EPISODE_PATTERNS:
            match = re.search(pattern, clean_name)
            if match:
                if len(match.groups()) == 2:  # S01E01, 1x01, - 102 - 형식
                    if pattern == r'- (\d{1,2})(\d{2}) -':
                        # - 102 - 형식 (시즌 1, 에피소드 02)
                        result.season = int(match.group(1))
                        result.episode = int(match.group(2))
                    else:
                        # S01E01, 1x01 형식
                        result.season = int(match.group(1))
                        result.episode = int(match.group(2))
                elif len(match.groups()) == 1:  # E01 형식
                    result.episode = int(match.group(1))
                    # 시즌 정보 없음 - 기본값 1 사용
                
                # 패턴 제거
                clean_name = clean_name.replace(match.group(0), '')
                break
        
        # 5. 연도 추출
        year_match = re.search(YEAR_PATTERN, clean_name)
        if year_match:
            # 세 개의 캡처 그룹 중 비어있지 않은 것을 선택
            year_group = next((g for g in year_match.groups() if g), None)
            if year_group:
                result.year = int(year_group)
                # 패턴 제거
                clean_name = clean_name.replace(year_match.group(0), '')
        
        # 6. 영화 여부 판단
        lower_name = clean_name.lower()
        result.is_movie = any(keyword in lower_name for keyword in MOVIE_KEYWORDS)
        
        # 영화 키워드 제거
        for keyword in MOVIE_KEYWORDS:
            if keyword in lower_name:
                # 대소문자 구분 없이 키워드와 일치하는 부분 찾기
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                clean_name = pattern.sub('', clean_name)
        
        # 7. 불필요한 구두점/공백 정리
        clean_name = re.sub(r'[.\-_\[\](){},;]', ' ', clean_name)  # 구두점을 공백으로 변경
        clean_name = re.sub(r'\s+', ' ', clean_name)  # 연속된 공백 제거
        clean_name = clean_name.strip()  # 앞뒤 공백 제거
        
        # 최종 정제된 제목 설정
        result.title = clean_name
        
        logger.debug(f"정제 결과: {result}")
        return result
    
    except Exception as e:
        logger.error(f"파일명 정제 오류: {str(e)}", exc_info=True)
        raise FileCleanerError(f"파일명 정제 중 오류 발생: {str(e)}") from e 