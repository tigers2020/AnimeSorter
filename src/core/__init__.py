"""
Core 모듈 - 핵심 기능 구현

이 모듈은 AnimeSorter의 핵심 기능을 제공합니다:
- 파일명 파싱
- TMDB API 클라이언트
- 메타데이터 처리
- 설정 관리
"""

# Legacy FileManager import removed - using UnifiedFileOrganizationService instead
from .file_parser import FileParser, ParsedMetadata
from .tmdb_client import TMDBAnimeInfo, TMDBClient
from .tmdb_models import TMDBAnimeInfo as TMDBAnimeInfoModel
from .types import FileOperationResult
from .unified_config import unified_config_manager
from .video_metadata_extractor import VideoMetadataExtractor

__all__ = [
    "FileParser",
    "ParsedMetadata",
    "TMDBClient",
    "TMDBAnimeInfo",
    # "FileManager",  # Legacy - using UnifiedFileOrganizationService instead
    "FileOperationResult",
    "unified_config_manager",
    "VideoMetadataExtractor",
    "TMDBAnimeInfoModel",
]
