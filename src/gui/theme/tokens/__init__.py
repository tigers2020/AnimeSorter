"""
테마 토큰 패키지

이 패키지는 테마 시스템에서 사용하는 디자인 토큰들을 정의합니다.
"""

from pathlib import Path

# 토큰 디렉토리 경로
TOKENS_DIR = Path(__file__).parent

# 기본 토큰 파일들
BASE_TOKENS_FILE = TOKENS_DIR / "base.json"
LIGHT_TOKENS_FILE = TOKENS_DIR / "light.json"
DARK_TOKENS_FILE = TOKENS_DIR / "dark.json"
HIGH_CONTRAST_TOKENS_FILE = TOKENS_DIR / "high_contrast.json"

# 사용 가능한 토큰 파일들
AVAILABLE_TOKEN_FILES = [
    "base.json",
    "light.json", 
    "dark.json",
    "high_contrast.json"
]

__all__ = [
    'TOKENS_DIR',
    'BASE_TOKENS_FILE',
    'LIGHT_TOKENS_FILE', 
    'DARK_TOKENS_FILE',
    'HIGH_CONTRAST_TOKENS_FILE',
    'AVAILABLE_TOKEN_FILES'
]
