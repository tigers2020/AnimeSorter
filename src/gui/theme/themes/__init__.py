"""
테마 정의 모듈

이 모듈은 애플리케이션에서 사용할 수 있는
다양한 테마 정의들을 포함합니다.
"""

from pathlib import Path

# 테마 디렉토리 경로
THEMES_DIR = Path(__file__).parent

# 기본 테마들
DEFAULT_THEMES = {
    "light": "light_theme.json",
    "dark": "dark_theme.json",
    "auto": "auto_theme.json",
}

__all__ = [
    "THEMES_DIR",
    "DEFAULT_THEMES",
]
