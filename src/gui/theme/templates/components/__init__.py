"""
컴포넌트 템플릿 패키지

이 패키지는 UI 컴포넌트별 QSS 템플릿들을 정의합니다.
"""

from pathlib import Path

# 컴포넌트 템플릿 디렉토리
COMPONENTS_DIR = Path(__file__).parent

# 기본 컴포넌트 템플릿들
__all__ = ["COMPONENTS_DIR"]
