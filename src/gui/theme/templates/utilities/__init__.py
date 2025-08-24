"""
유틸리티 템플릿 패키지

이 패키지는 공통으로 사용되는 QSS 유틸리티들을 정의합니다.
"""

from pathlib import Path

# 유틸리티 템플릿 디렉토리
UTILITIES_DIR = Path(__file__).parent

# 기본 유틸리티 템플릿들
__all__ = [
    'UTILITIES_DIR'
]
