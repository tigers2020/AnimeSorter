"""
TMDB 의존성 주입 컨테이너

TMDB 서비스들의 의존성을 관리하고 인스턴스를 생성하는 컨테이너입니다.
기존 서비스들을 래핑하여 의존성 주입 패턴을 적용합니다.
"""

import logging
from pathlib import Path
from typing import Any

from src.core.tmdb.adapters import (
    TMDBCacheAdapter,
    TMDBImageAdapter,
    TMDBRateLimiterAdapter,
)
from src.core.tmdb.interfaces import (
    TMDBConfig,
    TMDBClientFactory,
    TMDBClientProtocol,
    TMDBServiceProtocol,
    TMDBCacheProtocol,
    TMDBImageProtocol,
    TMDBRateLimiterProtocol,
)
from src.core.tmdb.tmdbsimple_service import TMDBSimpleService
from src.core.tmdb_cache import TMDBCacheManager
from src.core.tmdb_image import TMDBImageManager
from src.core.tmdb_rate_limiter import TMDBRateLimiter


class TMDBClientFactoryImpl(TMDBClientFactory):
    """TMDB 클라이언트 팩토리 구현체"""
    
    def __init__(self):
        """팩토리 초기화"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_service(self, config: TMDBConfig) -> TMDBServiceProtocol:
        """TMDB 서비스 생성"""
        # 의존성 생성
        cache = self.create_cache(config)
        rate_limiter = self.create_rate_limiter(config)
        
        # 서비스 생성
        return TMDBSimpleService(config, cache, rate_limiter)
    
    def create_cache(self, config: TMDBConfig) -> TMDBCacheProtocol:
        """캐시 생성"""
        cache_dir = Path(".animesorter_cache")
        cache_manager = TMDBCacheManager(
            cache_dir=cache_dir,
            cache_expiry=config.cache_expiry,
            memory_cache_size=config.memory_cache_size,
        )
        return TMDBCacheAdapter(cache_manager)
    
    def create_image_manager(self, config: TMDBConfig) -> TMDBImageProtocol:
        """이미지 관리자 생성"""
        cache_dir = Path(".animesorter_cache")
        poster_cache_dir = cache_dir / "posters"
        image_manager = TMDBImageManager(poster_cache_dir)
        return TMDBImageAdapter(image_manager)
    
    def create_rate_limiter(self, config: TMDBConfig) -> TMDBRateLimiterProtocol:
        """속도 제한 관리자 생성"""
        rate_limiter = TMDBRateLimiter(
            requests_per_second=config.requests_per_second,
            burst_limit=config.burst_limit,
        )
        return TMDBRateLimiterAdapter(rate_limiter)


class TMDBClientContainer:
    """TMDB 클라이언트 의존성 주입 컨테이너"""
    
    def __init__(self, factory: TMDBClientFactory | None = None):
        """컨테이너 초기화"""
        self.factory = factory or TMDBClientFactoryImpl()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 싱글톤 인스턴스들
        self._client: TMDBClientProtocol | None = None
        self._config: TMDBConfig | None = None
    
    def configure(self, config: TMDBConfig) -> None:
        """컨테이너 설정"""
        self._config = config
        self.logger.info("TMDB 컨테이너 설정 완료")
    
    def get_client(self) -> TMDBClientProtocol:
        """TMDB 클라이언트 인스턴스 반환 (싱글톤)"""
        if self._client is None:
            if self._config is None:
                raise ValueError("컨테이너가 설정되지 않았습니다. configure()를 먼저 호출하세요.")
            
            self._client = self._create_client(self._config)
        
        return self._client
    
    def _create_client(self, config: TMDBConfig) -> TMDBClientProtocol:
        """TMDB 클라이언트 생성"""
        # 의존성 생성
        service = self.factory.create_service(config)
        cache = self.factory.create_cache(config)
        image_manager = self.factory.create_image_manager(config)
        rate_limiter = self.factory.create_rate_limiter(config)
        
        # 클라이언트 생성
        return TMDBClientImpl(config, service, cache, image_manager, rate_limiter)
    
    def reset(self) -> None:
        """컨테이너 초기화"""
        if self._client:
            # 리소스 정리
            import asyncio
            try:
                asyncio.create_task(self._client.close_resources())
            except Exception as e:
                self.logger.warning(f"리소스 정리 중 오류: {e}")
        
        self._client = None
        self._config = None
        self.logger.info("TMDB 컨테이너 초기화 완료")


class TMDBClientImpl(TMDBClientProtocol):
    """TMDB 클라이언트 구현체 - 의존성 주입 패턴 적용"""
    
    def __init__(
        self,
        config: TMDBConfig,
        service: TMDBServiceProtocol,
        cache: TMDBCacheProtocol,
        image_manager: TMDBImageProtocol,
        rate_limiter: TMDBRateLimiterProtocol,
    ):
        """TMDB 클라이언트 초기화"""
        self.config = config
        self.service = service
        self.cache = cache
        self.image_manager = image_manager
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.logger.info("TMDB 클라이언트 초기화 완료 (의존성 주입 패턴)")
    
    # 서비스 메서드들 - 위임
    def search_anime(
        self,
        query: str,
        year: int | None = None,
        include_adult: bool = False,
        first_air_date_year: int | None = None,
    ) -> list[Any]:
        """애니메이션 제목으로 검색"""
        return self.service.search_anime(query, year, include_adult, first_air_date_year)
    
    def get_anime_details(self, tv_id: int, language: str | None = None) -> Any | None:
        """애니메이션 상세 정보 조회"""
        return self.service.get_anime_details(tv_id, language)
    
    def search_anime_optimized(self, query: str, language: str = "ko-KR") -> list[Any]:
        """최적화된 애니메이션 검색"""
        return self.service.search_anime_optimized(query, language)
    
    def get_anime_season(
        self, tv_id: int, season_number: int, language: str | None = None
    ) -> dict[str, Any] | None:
        """시즌 정보 조회"""
        return self.service.get_anime_season(tv_id, season_number, language)
    
    def get_anime_episode(
        self, tv_id: int, season_number: int, episode_number: int, language: str | None = None
    ) -> dict[str, Any] | None:
        """에피소드 정보 조회"""
        return self.service.get_anime_episode(tv_id, season_number, episode_number, language)
    
    # 이미지 관련 메서드들 - 위임
    def download_poster(self, poster_path: str, size: str = "w185") -> str | None:
        """TMDB 포스터 이미지 다운로드"""
        return self.image_manager.download_poster(poster_path, size)
    
    def download_backdrop(self, backdrop_path: str, size: str = "w1280") -> str | None:
        """TMDB 배경 이미지 다운로드"""
        return self.image_manager.download_backdrop(backdrop_path, size)
    
    def download_profile(self, profile_path: str, size: str = "w185") -> str | None:
        """TMDB 프로필 이미지 다운로드"""
        return self.image_manager.download_profile(profile_path, size)
    
    def get_poster_path(self, poster_path: str, size: str = "w185") -> str | None:
        """포스터 이미지 경로 반환 (다운로드 포함)"""
        return self.image_manager.get_poster_path(poster_path, size)
    
    def get_backdrop_path(self, backdrop_path: str, size: str = "w1280") -> str | None:
        """배경 이미지 경로 반환 (다운로드 포함)"""
        return self.image_manager.get_backdrop_path(backdrop_path, size)
    
    def get_profile_path(self, profile_path: str, size: str = "w185") -> str | None:
        """프로필 이미지 경로 반환 (다운로드 포함)"""
        return self.image_manager.get_profile_path(profile_path, size)
    
    def get_image_url(self, image_path: str, size: str = "w185") -> str:
        """TMDB 이미지 URL 생성"""
        return self.image_manager.get_image_url(image_path, size)
    
    # 캐시 관련 메서드들 - 위임
    def clear_cache(self) -> None:
        """캐시 초기화"""
        self.cache.clear_cache()
    
    def get_cache_info(self) -> dict[str, Any]:
        """캐시 정보 반환"""
        cache_info = self.cache.get_cache_info()
        image_cache_info = self.image_manager.get_image_cache_info()
        rate_limiter_info = self.rate_limiter.get_health_status()
        
        return {
            "api_cache": cache_info,
            "image_cache": image_cache_info,
            "rate_limiter": rate_limiter_info,
        }
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """캐시 활성화/비활성화"""
        self.cache.set_cache_enabled(enabled)
    
    def set_cache_expiry(self, expiry_seconds: int) -> None:
        """캐시 만료 시간 설정"""
        self.cache.set_cache_expiry(expiry_seconds)
    
    def set_memory_cache_size(self, size: int) -> None:
        """메모리 캐시 크기 설정"""
        self.cache.set_memory_cache_size(size)
    
    # 설정 관련 메서드들
    def set_language(self, language: str) -> None:
        """언어 설정 변경"""
        self.config.language = language
    
    def update_api_key(self, new_api_key: str) -> None:
        """API 키 업데이트"""
        if new_api_key and new_api_key != self.config.api_key:
            self.config.api_key = new_api_key
            
            # tmdbsimple 설정 업데이트
            import tmdbsimple as tmdb
            tmdb.API_KEY = new_api_key
            
            self.logger.info("TMDB API 키가 업데이트되었습니다")
    
    def get_api_key(self) -> str:
        """현재 API 키 반환"""
        return self.config.api_key
    
    # 속도 제한 관련 메서드들 - 위임
    def get_rate_limiter_status(self) -> dict:
        """속도 제한 관리자 상태 반환"""
        return self.rate_limiter.get_health_status()
    
    def set_rate_limit(self, requests_per_second: int, burst_limit: int | None = None) -> None:
        """속도 제한 설정 변경"""
        self.rate_limiter.set_rate_limit(requests_per_second, burst_limit)
    
    def reset_rate_limiter(self) -> None:
        """속도 제한 관리자 초기화"""
        self.rate_limiter.reset()
    
    # 비동기 메서드들 - 위임
    async def download_poster_async(self, poster_path: str, size: str = "w185") -> str | None:
        """TMDB 포스터 이미지 비동기 다운로드"""
        # TMDBImageManager의 비동기 메서드 호출
        if hasattr(self.image_manager, 'image_manager'):
            return await self.image_manager.image_manager.download_poster_async(poster_path, size)
        else:
            # 동기 메서드로 폴백
            return self.image_manager.download_poster(poster_path, size)
    
    async def close_resources(self) -> None:
        """리소스 정리"""
        if hasattr(self.image_manager, 'image_manager'):
            await self.image_manager.image_manager.close_async_session()


# 전역 컨테이너 인스턴스
_tmdb_container: TMDBClientContainer | None = None


def get_tmdb_container() -> TMDBClientContainer:
    """전역 TMDB 컨테이너 인스턴스 반환"""
    global _tmdb_container
    if _tmdb_container is None:
        _tmdb_container = TMDBClientContainer()
    return _tmdb_container


def configure_tmdb(config: TMDBConfig) -> None:
    """TMDB 컨테이너 설정"""
    container = get_tmdb_container()
    container.configure(config)


def get_tmdb_client() -> TMDBClientProtocol:
    """TMDB 클라이언트 인스턴스 반환"""
    container = get_tmdb_container()
    return container.get_client()
