"""
안전한 파일명 생성을 위한 개선된 slugify 유틸리티

한글 자모 분리, 특수문자 처리, 콜론/슬래시 처리 등을 포함한
강화된 파일명 정규화 기능을 제공합니다.
"""

import re
import unicodedata
from typing import Optional
from slugify import slugify


def safe_slugify(text: str, 
                separator: str = '_', 
                max_length: Optional[int] = None,
                allow_unicode: bool = True,
                allow_dots: bool = False) -> str:
    """
    안전한 파일명 생성을 위한 개선된 slugify
    
    Args:
        text: 정규화할 텍스트
        separator: 구분자 (기본값: '_')
        max_length: 최대 길이 제한
        allow_unicode: 유니코드 허용 여부 (한글 등)
        allow_dots: 점(.) 허용 여부
        
    Returns:
        str: 안전한 파일명
    """
    if not text:
        return ""
    
    # 1단계: 기본 정규화
    normalized = text.strip()
    
    # 2단계: 한글 자모 분리 방지
    if allow_unicode:
        # 한글 자모 분리 방지를 위한 정규화
        normalized = _prevent_hangul_decomposition(normalized)
    
    # 3단계: 파일 시스템 위험 문자 처리
    normalized = _handle_filesystem_chars(normalized, allow_dots)
    
    # 4단계: 연속된 공백/구분자 정리
    normalized = re.sub(rf'[{re.escape(separator)}\s]+', separator, normalized)
    
    # 5단계: slugify 적용
    result = slugify(
        normalized,
        separator=separator,
        max_length=max_length,
        word_boundary=True,
        save_order=True,
        stopwords=None,
        regex_pattern=None,
        allow_unicode=allow_unicode,
        lowercase=True,
        replacements=None,
        allow_2byte_chars=allow_unicode
    )
    
    # 6단계: 최종 정리
    result = _final_cleanup(result, separator)
    
    return result


def _prevent_hangul_decomposition(text: str) -> str:
    """
    한글 자모 분리 방지
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 자모 분리가 방지된 텍스트
    """
    # 한글 자모 분리 방지를 위한 정규화
    # NFC 정규화로 조합된 형태 유지
    normalized = unicodedata.normalize('NFC', text)
    
    # 한글 자모가 분리된 경우 재조합 시도
    # (실제로는 더 복잡한 로직이 필요할 수 있음)
    return normalized


def _handle_filesystem_chars(text: str, allow_dots: bool = False) -> str:
    """
    파일 시스템 위험 문자 처리
    
    Args:
        text: 원본 텍스트
        allow_dots: 점(.) 허용 여부
        
    Returns:
        str: 안전한 텍스트
    """
    # Windows/Unix 공통 위험 문자
    dangerous_chars = r'[<>:"|?*\x00-\x1f]'
    
    # 콜론(:) 특별 처리 - 파일 시스템에서 드라이브 구분자로 사용
    text = re.sub(r':', ' - ', text)
    
    # 슬래시(/) 및 백슬래시(\) 처리
    text = re.sub(r'[\\/]', ' ', text)
    
    # 점(.) 처리
    if not allow_dots:
        text = re.sub(r'\.', ' ', text)
    
    # 기타 위험 문자 제거
    text = re.sub(dangerous_chars, ' ', text)
    
    # 연속된 공백 정리
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def _final_cleanup(text: str, separator: str) -> str:
    """
    최종 정리
    
    Args:
        text: 정리할 텍스트
        separator: 구분자
        
    Returns:
        str: 최종 정리된 텍스트
    """
    # 앞뒤 구분자 제거
    text = text.strip(separator)
    
    # 빈 문자열 처리
    if not text:
        return "unnamed"
    
    # 너무 긴 파일명 처리
    if len(text) > 200:
        # 단어 경계에서 자르기
        words = text.split(separator)
        result = ""
        for word in words:
            if len(result + separator + word) <= 200:
                if result:
                    result += separator + word
                else:
                    result = word
            else:
                break
        text = result
    
    return text


def create_cache_key(title: str, 
                    year: Optional[int] = None, 
                    season: Optional[int] = None,
                    separator: str = '_') -> str:
    """
    캐시 키 생성
    
    Args:
        title: 제목
        year: 연도
        season: 시즌
        separator: 구분자
        
    Returns:
        str: 캐시 키
    """
    normalized_title = safe_slugify(title, separator=separator)
    year_part = f"{separator}{year}" if year else f"{separator}any"
    season_part = f"{separator}{season}" if season else f"{separator}any"
    
    return f"{normalized_title}{year_part}{season_part}"


def create_folder_name(title: str, 
                      year: Optional[int] = None,
                      separator: str = ' ') -> str:
    """
    폴더명 생성
    
    Args:
        title: 제목
        year: 연도
        separator: 구분자
        
    Returns:
        str: 폴더명
    """
    # 폴더명은 더 읽기 쉽게 생성
    normalized_title = safe_slugify(title, separator=separator, allow_unicode=True)
    year_part = f" ({year})" if year else ""
    
    return f"{normalized_title}{year_part}"


# 하위 호환성을 위한 별칭
def slugify_safe(text: str, **kwargs) -> str:
    """safe_slugify의 별칭"""
    return safe_slugify(text, **kwargs) 