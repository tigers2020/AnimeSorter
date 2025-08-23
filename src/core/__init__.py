"""
Core 모듈 - 핵심 기능 구현

이 모듈은 AnimeSorter의 핵심 기능을 제공합니다:
- 파일명 파싱
- TMDB API 클라이언트
- 메타데이터 처리
- 설정 관리
"""

from .file_manager import FileManager
from .file_parser import FileParser, ParsedMetadata
from .settings_manager import AppSettings, SettingsManager
from .tmdb_client import TMDBAnimeInfo, TMDBClient
from .types import FileOperationResult

__all__ = [
    "FileParser",
    "ParsedMetadata",
    "TMDBClient",
    "TMDBAnimeInfo",
    "FileManager",
    "FileOperationResult",
    "SettingsManager",
    "AppSettings",
]
