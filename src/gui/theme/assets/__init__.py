"""
테마 자산 모듈

이 모듈은 테마 시스템에서 사용하는 이미지, 아이콘 등의
자산들을 관리합니다.
"""

from pathlib import Path

# 자산 디렉토리 경로
ASSETS_DIR = Path(__file__).parent
ICONS_DIR = ASSETS_DIR / 'icons'
IMAGES_DIR = ASSETS_DIR / 'images'

__all__ = [
    'ASSETS_DIR',
    'ICONS_DIR', 
    'IMAGES_DIR',
]
