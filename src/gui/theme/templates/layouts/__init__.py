"""
레이아웃 템플릿 패키지

이 패키지는 레이아웃 관련 QSS 템플릿들을 정의합니다.
"""

from pathlib import Path

# 레이아웃 템플릿 디렉토리
LAYOUTS_DIR = Path(__file__).parent

# 기본 레이아웃 템플릿들
__all__ = [
    'LAYOUTS_DIR'
]
