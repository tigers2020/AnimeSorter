"""
GUI 서비스 모듈

비즈니스 로직을 담당하는 서비스들
"""

import logging

logger = logging.getLogger(__name__)
from .file_service import FileService
from .metadata_service import MetadataService
from .state_service import StateService


# Legacy services - placeholder implementations
class BackgroundTaskService:
    """백그라운드 작업 서비스 - 플레이스홀더"""


# FileScanService는 별도 파일에서 임포트
from .file_scan_service import FileScanService


class MediaDataService:
    """미디어 데이터 서비스 - 플레이스홀더"""


class TMDBSearchService:
    """TMDB 검색 서비스 - 플레이스홀더"""


class UIUpdateService:
    """UI 업데이트 서비스 - 플레이스홀더"""


# Interface placeholders
class IBackgroundTaskService:
    """백그라운드 작업 서비스 인터페이스 - 플레이스홀더"""


class IFileScanService:
    """파일 스캔 서비스 인터페이스 - 플레이스홀더"""


class IMediaDataService:
    """미디어 데이터 서비스 인터페이스 - 플레이스홀더"""


class ITMDBSearchService:
    """TMDB 검색 서비스 인터페이스 - 플레이스홀더"""


class IUIUpdateService:
    """UI 업데이트 서비스 인터페이스 - 플레이스홀더"""


__all__ = [
    "FileService",
    "MetadataService",
    "StateService",
    "BackgroundTaskService",
    "FileScanService",
    "MediaDataService",
    "TMDBSearchService",
    "UIUpdateService",
    "IBackgroundTaskService",
    "IFileScanService",
    "IMediaDataService",
    "ITMDBSearchService",
    "IUIUpdateService",
]
