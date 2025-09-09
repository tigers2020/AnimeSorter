"""
TMDB 서비스 인터페이스 정의

의존성 주입을 위한 추상 인터페이스들을 정의합니다.
기존 서비스들을 인터페이스로 추상화하여 테스트 가능하고 확장 가능한 구조를 만듭니다.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.core.tmdb_models import TMDBAnimeInfo


@dataclass
class TMDBConfig:
    """TMDB 설정 데이터 클래스"""
    api_key: str
    language: str = "ko-KR"
    timeout: int = 5
    requests_per_second: int = 4
    burst_limit: int = 8
    cache_expiry: int = 3600
    memory_cache_size: int = 1000


class TMDBServiceProtocol(Protocol):
    """TMDB 서비스 프로토콜 - tmdbsimple 기반 서비스"""
    
    def search_anime(
        self,
        query: str,
        year: int | None = None,
        include_adult: bool = False,
        first_air_date_year: int | None = None,
    ) -> list[TMDBAnimeInfo]:
        """애니메이션 검색"""
        ...
    
    def get_anime_details(self, tv_id: int, language: str | None = None) -> TMDBAnimeInfo | None:
        """애니메이션 상세 정보 조회"""
        ...
    
    def search_anime_optimized(self, query: str, language: str = "ko-KR") -> list[TMDBAnimeInfo]:
        """최적화된 애니메이션 검색"""
        ...
    
    def get_anime_season(
        self, tv_id: int, season_number: int, language: str | None = None
    ) -> dict[str, Any] | None:
        """시즌 정보 조회"""
        ...
    
    def get_anime_episode(
        self, tv_id: int, season_number: int, episode_number: int, language: str | None = None
    ) -> dict[str, Any] | None:
        """에피소드 정보 조회"""
        ...


class TMDBCacheProtocol(Protocol):
    """TMDB 캐시 프로토콜 - 기존 TMDBCacheManager와 호환"""
    
    def get_cache(self, key: str) -> Any | None:
        """캐시에서 데이터 조회"""
        ...
    
    def set_cache(self, key: str, data: Any) -> None:
        """캐시에 데이터 저장"""
        ...
    
    def clear_cache(self) -> None:
        """캐시 초기화"""
        ...
    
    def get_cache_info(self) -> dict[str, Any]:
        """캐시 정보 반환"""
        ...
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """캐시 활성화/비활성화"""
        ...
    
    def set_cache_expiry(self, expiry_seconds: int) -> None:
        """캐시 만료 시간 설정"""
        ...
    
    def set_memory_cache_size(self, size: int) -> None:
        """메모리 캐시 크기 설정"""
        ...


class TMDBImageProtocol(Protocol):
    """TMDB 이미지 프로토콜 - 기존 TMDBImageManager와 호환"""
    
    def download_poster(self, poster_path: str, size: str = "w185") -> str | None:
        """포스터 이미지 다운로드"""
        ...
    
    def download_backdrop(self, backdrop_path: str, size: str = "w1280") -> str | None:
        """배경 이미지 다운로드"""
        ...
    
    def download_profile(self, profile_path: str, size: str = "w185") -> str | None:
        """프로필 이미지 다운로드"""
        ...
    
    def get_poster_path(self, poster_path: str, size: str = "w185") -> str | None:
        """포스터 이미지 경로 반환 (다운로드 포함)"""
        ...
    
    def get_backdrop_path(self, backdrop_path: str, size: str = "w1280") -> str | None:
        """배경 이미지 경로 반환 (다운로드 포함)"""
        ...
    
    def get_profile_path(self, profile_path: str, size: str = "w185") -> str | None:
        """프로필 이미지 경로 반환 (다운로드 포함)"""
        ...
    
    def get_image_url(self, image_path: str, size: str = "w185") -> str:
        """TMDB 이미지 URL 생성"""
        ...
    
    def clear_image_cache(self) -> int:
        """이미지 캐시 정리"""
        ...
    
    def get_image_cache_info(self) -> dict:
        """이미지 캐시 정보 반환"""
        ...
    
    def set_poster_cache_dir(self, new_dir: Path) -> bool:
        """포스터 캐시 디렉토리 변경"""
        ...


class TMDBRateLimiterProtocol(Protocol):
    """TMDB 속도 제한 프로토콜 - 기존 TMDBRateLimiter와 호환"""
    
    def wait_if_needed(self) -> float:
        """속도 제한 확인 및 대기"""
        ...
    
    def get_health_status(self) -> dict[str, Any]:
        """속도 제한 상태 반환"""
        ...
    
    def set_rate_limit(self, requests_per_second: int, burst_limit: int | None = None) -> None:
        """속도 제한 설정"""
        ...
    
    def reset(self) -> None:
        """속도 제한 초기화"""
        ...
    
    def record_request(self, success: bool = True, response_time: float | None = None) -> None:
        """요청 기록"""
        ...


class TMDBClientFactory(ABC):
    """TMDB 클라이언트 팩토리 추상 클래스"""
    
    @abstractmethod
    def create_service(self, config: TMDBConfig) -> TMDBServiceProtocol:
        """TMDB 서비스 생성"""
        pass
    
    @abstractmethod
    def create_cache(self, config: TMDBConfig) -> TMDBCacheProtocol:
        """캐시 생성"""
        pass
    
    @abstractmethod
    def create_image_manager(self, config: TMDBConfig) -> TMDBImageProtocol:
        """이미지 관리자 생성"""
        pass
    
    @abstractmethod
    def create_rate_limiter(self, config: TMDBConfig) -> TMDBRateLimiterProtocol:
        """속도 제한 관리자 생성"""
        pass


class TMDBClientProtocol(Protocol):
    """TMDB 클라이언트 프로토콜 - 기존 TMDBClient와 호환"""
    
    # 서비스 메서드들
    def search_anime(
        self,
        query: str,
        year: int | None = None,
        include_adult: bool = False,
        first_air_date_year: int | None = None,
    ) -> list[TMDBAnimeInfo]:
        """애니메이션 제목으로 검색"""
        ...
    
    def get_anime_details(self, tv_id: int, language: str | None = None) -> TMDBAnimeInfo | None:
        """애니메이션 상세 정보 조회"""
        ...
    
    def search_anime_optimized(self, query: str, language: str = "ko-KR") -> list[TMDBAnimeInfo]:
        """최적화된 애니메이션 검색"""
        ...
    
    def get_anime_season(
        self, tv_id: int, season_number: int, language: str | None = None
    ) -> dict[str, Any] | None:
        """시즌 정보 조회"""
        ...
    
    def get_anime_episode(
        self, tv_id: int, season_number: int, episode_number: int, language: str | None = None
    ) -> dict[str, Any] | None:
        """에피소드 정보 조회"""
        ...
    
    # 이미지 관련 메서드들
    def download_poster(self, poster_path: str, size: str = "w185") -> str | None:
        """TMDB 포스터 이미지 다운로드"""
        ...
    
    def download_backdrop(self, backdrop_path: str, size: str = "w1280") -> str | None:
        """TMDB 배경 이미지 다운로드"""
        ...
    
    def download_profile(self, profile_path: str, size: str = "w185") -> str | None:
        """TMDB 프로필 이미지 다운로드"""
        ...
    
    def get_poster_path(self, poster_path: str, size: str = "w185") -> str | None:
        """포스터 이미지 경로 반환 (다운로드 포함)"""
        ...
    
    def get_backdrop_path(self, backdrop_path: str, size: str = "w1280") -> str | None:
        """배경 이미지 경로 반환 (다운로드 포함)"""
        ...
    
    def get_profile_path(self, profile_path: str, size: str = "w185") -> str | None:
        """프로필 이미지 경로 반환 (다운로드 포함)"""
        ...
    
    def get_image_url(self, image_path: str, size: str = "w185") -> str:
        """TMDB 이미지 URL 생성"""
        ...
    
    # 캐시 관련 메서드들
    def clear_cache(self) -> None:
        """캐시 초기화"""
        ...
    
    def get_cache_info(self) -> dict[str, Any]:
        """캐시 정보 반환"""
        ...
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """캐시 활성화/비활성화"""
        ...
    
    def set_cache_expiry(self, expiry_seconds: int) -> None:
        """캐시 만료 시간 설정"""
        ...
    
    def set_memory_cache_size(self, size: int) -> None:
        """메모리 캐시 크기 설정"""
        ...
    
    # 설정 관련 메서드들
    def set_language(self, language: str) -> None:
        """언어 설정 변경"""
        ...
    
    def update_api_key(self, new_api_key: str) -> None:
        """API 키 업데이트"""
        ...
    
    def get_api_key(self) -> str:
        """현재 API 키 반환"""
        ...
    
    # 속도 제한 관련 메서드들
    def get_rate_limiter_status(self) -> dict:
        """속도 제한 관리자 상태 반환"""
        ...
    
    def set_rate_limit(self, requests_per_second: int, burst_limit: int | None = None) -> None:
        """속도 제한 설정 변경"""
        ...
    
    def reset_rate_limiter(self) -> None:
        """속도 제한 관리자 초기화"""
        ...
    
    # 비동기 메서드들
    async def download_poster_async(self, poster_path: str, size: str = "w185") -> str | None:
        """TMDB 포스터 이미지 비동기 다운로드"""
        ...
    
    async def close_resources(self) -> None:
        """리소스 정리"""
        ...
