"""
TMDB 모듈 - 의존성 주입 패턴 적용

tmdbsimple 라이브러리를 기반으로 한 TMDB 서비스들을 의존성 주입 패턴으로 구성합니다.
기존 인터페이스는 유지하면서 내부적으로는 테스트 가능하고 확장 가능한 구조를 제공합니다.
"""

from src.core.tmdb.container import (
    TMDBClientContainer,
    TMDBConfig,
    configure_tmdb,
    get_tmdb_client,
)
from src.core.tmdb.interfaces import (
    TMDBClientFactory,
    TMDBClientProtocol,
    TMDBConfig,
    TMDBImageProtocol,
    TMDBRateLimiterProtocol,
    TMDBServiceProtocol,
    TMDBCacheProtocol,
)
from src.core.tmdb.tmdbsimple_service import TMDBSimpleService

__all__ = [
    # 컨테이너 관련
    "TMDBClientContainer",
    "TMDBConfig",
    "configure_tmdb",
    "get_tmdb_client",
    # 인터페이스
    "TMDBClientFactory",
    "TMDBClientProtocol",
    "TMDBImageProtocol",
    "TMDBRateLimiterProtocol",
    "TMDBServiceProtocol",
    "TMDBCacheProtocol",
    # 서비스 구현체
    "TMDBSimpleService",
]
