"""
Core 모듈 - 핵심 기능 구현

이 모듈은 AnimeSorter의 핵심 기능을 제공합니다:
- 파일명 파싱
- TMDB API 클라이언트
- 메타데이터 처리
- 설정 관리
"""

import logging

logger = logging.getLogger(__name__)
from .resolution_normalizer import (
    get_best_resolution,
    get_resolution_priority,
    normalize_resolution,
)
from .tmdb_client import TMDBAnimeInfo, TMDBClient
from .tmdb_models import TMDBAnimeInfo as TMDBAnimeInfoModel
from .types import FileOperationResult
from .unified_config import unified_config_manager
from .video_metadata_extractor import VideoMetadataExtractor

__all__ = [
    "TMDBClient",
    "TMDBAnimeInfo",
    "FileOperationResult",
    "unified_config_manager",
    "VideoMetadataExtractor",
    "TMDBAnimeInfoModel",
    "normalize_resolution",
    "get_best_resolution",
    "get_resolution_priority",
]
