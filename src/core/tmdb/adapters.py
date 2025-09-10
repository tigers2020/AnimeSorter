"""
TMDB 서비스 어댑터

기존 TMDB 서비스들을 인터페이스에 맞게 래핑하는 어댑터들을 정의합니다.
"""

import logging

logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Any

from src.core.tmdb.interfaces import (TMDBCacheProtocol, TMDBImageProtocol,
                                      TMDBRateLimiterProtocol)


class TMDBCacheAdapter(TMDBCacheProtocol):
    """TMDBCacheManager를 TMDBCacheProtocol에 맞게 래핑하는 어댑터"""

    def __init__(self, cache_manager):
        """기존 TMDBCacheManager 인스턴스를 래핑"""
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_cache(self, key: str) -> Any | None:
        """캐시에서 데이터 조회"""
        return self.cache_manager.get_cache(key)

    def set_cache(self, key: str, data: Any) -> None:
        """캐시에 데이터 저장"""
        self.cache_manager.set_cache(key, data)

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self.cache_manager.clear_cache()

    def get_cache_info(self) -> dict[str, Any]:
        """캐시 정보 반환"""
        return self.cache_manager.get_cache_info()

    def set_cache_enabled(self, enabled: bool) -> None:
        """캐시 활성화/비활성화"""
        self.cache_manager.set_cache_enabled(enabled)

    def set_cache_expiry(self, expiry_seconds: int) -> None:
        """캐시 만료 시간 설정"""
        self.cache_manager.set_cache_expiry(expiry_seconds)

    def set_memory_cache_size(self, size: int) -> None:
        """메모리 캐시 크기 설정"""
        self.cache_manager.set_memory_cache_size(size)


class TMDBImageAdapter(TMDBImageProtocol):
    """TMDBImageManager를 TMDBImageProtocol에 맞게 래핑하는 어댑터"""

    def __init__(self, image_manager):
        """기존 TMDBImageManager 인스턴스를 래핑"""
        self.image_manager = image_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    def download_poster(self, poster_path: str, size: str = "w185") -> str | None:
        """포스터 이미지 다운로드"""
        return self.image_manager.download_poster(poster_path, size)

    def download_backdrop(self, backdrop_path: str, size: str = "w1280") -> str | None:
        """배경 이미지 다운로드"""
        return self.image_manager.download_backdrop(backdrop_path, size)

    def download_profile(self, profile_path: str, size: str = "w185") -> str | None:
        """프로필 이미지 다운로드"""
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

    def clear_image_cache(self) -> int:
        """이미지 캐시 정리"""
        return self.image_manager.clear_image_cache()

    def get_image_cache_info(self) -> dict:
        """이미지 캐시 정보 반환"""
        return self.image_manager.get_image_cache_info()

    def set_poster_cache_dir(self, new_dir: Path) -> bool:
        """포스터 캐시 디렉토리 변경"""
        return self.image_manager.set_poster_cache_dir(new_dir)


class TMDBRateLimiterAdapter(TMDBRateLimiterProtocol):
    """TMDBRateLimiter를 TMDBRateLimiterProtocol에 맞게 래핑하는 어댑터"""

    def __init__(self, rate_limiter):
        """기존 TMDBRateLimiter 인스턴스를 래핑"""
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(self.__class__.__name__)

    def wait_if_needed(self) -> float:
        """속도 제한 확인 및 대기"""
        return self.rate_limiter.wait_if_needed()

    def get_health_status(self) -> dict[str, Any]:
        """속도 제한 상태 반환"""
        return self.rate_limiter.get_health_status()

    def set_rate_limit(self, requests_per_second: int, burst_limit: int | None = None) -> None:
        """속도 제한 설정"""
        self.rate_limiter.set_rate_limit(requests_per_second, burst_limit)

    def reset(self) -> None:
        """속도 제한 초기화"""
        self.rate_limiter.reset()

    def record_request(self, success: bool = True, response_time: float | None = None) -> None:
        """요청 기록"""
        self.rate_limiter.record_request(success, response_time)
