"""
메타데이터 서비스 - TMDB API 호출 및 메타데이터 관리
"""

import logging

logger = logging.getLogger(__name__)
import asyncio
from dataclasses import dataclass
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

from src.core.tmdb_client import TMDBAnimeInfo, TMDBClient


@dataclass
class MetadataSearchResult:
    """메타데이터 검색 결과"""

    success: bool
    anime_info: TMDBAnimeInfo | None = None
    error_message: str | None = None
    search_query: str = ""


class MetadataService(QObject):
    """메타데이터 서비스 - TMDB API 호출 및 메타데이터 관리"""

    search_started = pyqtSignal(str)
    search_completed = pyqtSignal(MetadataSearchResult)
    search_failed = pyqtSignal(str, str)

    def __init__(self, event_bus=None):
        super().__init__()
        self.event_bus = event_bus
        self.tmdb_client = TMDBClient()
        self._search_cache: dict[str, MetadataSearchResult] = {}
        self._max_cache_size = 1000

    def initialize(self) -> bool:
        """서비스 초기화"""
        try:
            if not self.tmdb_client.is_configured():
                logger.info("⚠️ TMDB 클라이언트가 구성되지 않았습니다.")
                return False
            logger.info("✅ MetadataService 초기화 완료")
            return True
        except Exception as e:
            logger.info("❌ MetadataService 초기화 실패: %s", e)
            return False

    def cleanup(self):
        """서비스 정리"""
        self._search_cache.clear()
        logger.info("🧹 MetadataService 정리 완료")

    async def search_anime_async(self, title: str, year: int | None = None) -> MetadataSearchResult:
        """비동기 애니메이션 검색"""
        try:
            cache_key = f"{title}_{year}" if year else title
            if cache_key in self._search_cache:
                logger.info("📋 캐시된 결과 사용: %s", title)
                return self._search_cache[cache_key]
            self.search_started.emit(title)
            anime_info = await self.tmdb_client.search_anime_async(title, year)
            if anime_info:
                result = MetadataSearchResult(
                    success=True, anime_info=anime_info, search_query=title
                )
                logger.info("✅ 검색 성공: %s -> %s", title, anime_info.name)
            else:
                result = MetadataSearchResult(
                    success=False, error_message="검색 결과가 없습니다.", search_query=title
                )
                logger.info("⚠️ 검색 결과 없음: %s", title)
            self._cache_result(cache_key, result)
            self.search_completed.emit(result)
            return result
        except Exception as e:
            error_msg = f"검색 중 오류 발생: {str(e)}"
            result = MetadataSearchResult(
                success=False, error_message=error_msg, search_query=title
            )
            logger.info("❌ 검색 실패: %s - %s", title, e)
            self.search_failed.emit(title, error_msg)
            return result

    def search_anime_sync(self, title: str, year: int | None = None) -> MetadataSearchResult:
        """동기 애니메이션 검색 (비동기 래퍼)"""
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.search_anime_async(title, year))
        except Exception as e:
            error_msg = f"동기 검색 중 오류: {str(e)}"
            result = MetadataSearchResult(
                success=False, error_message=error_msg, search_query=title
            )
            logger.info("❌ 동기 검색 실패: %s - %s", title, e)
            return result

    def get_anime_details(self, tmdb_id: int) -> TMDBAnimeInfo | None:
        """TMDB ID로 애니메이션 상세 정보 조회"""
        try:
            return self.tmdb_client.get_anime_details(tmdb_id)
        except Exception as e:
            logger.info("❌ 애니메이션 상세 정보 조회 실패 (ID: %s): %s", tmdb_id, e)
            return None

    def get_search_suggestions(self, partial_title: str, limit: int = 5) -> list[str]:
        """검색 제안 목록 반환"""
        try:
            suggestions = []
            for cached_key in self._search_cache:
                if partial_title.lower() in cached_key.lower():
                    suggestions.append(cached_key)
                    if len(suggestions) >= limit:
                        break
            return suggestions
        except Exception as e:
            logger.info("❌ 검색 제안 생성 실패: %s", e)
            return []

    def clear_cache(self):
        """검색 캐시 정리"""
        self._search_cache.clear()
        logger.info("🧹 메타데이터 검색 캐시 정리 완료")

    def get_cache_stats(self) -> dict[str, Any]:
        """캐시 통계 반환"""
        return {
            "cache_size": len(self._search_cache),
            "max_cache_size": self._max_cache_size,
            "cache_keys": list(self._search_cache.keys())[:10],
        }

    def _cache_result(self, key: str, result: MetadataSearchResult):
        """검색 결과를 캐시에 저장"""
        if len(self._search_cache) >= self._max_cache_size:
            oldest_key = next(iter(self._search_cache))
            del self._search_cache[oldest_key]
        self._search_cache[key] = result

    def is_configured(self) -> bool:
        """TMDB 클라이언트 구성 상태 확인"""
        return self.tmdb_client.is_configured()

    def get_tmdb_client(self) -> TMDBClient:
        """TMDB 클라이언트 인스턴스 반환"""
        return self.tmdb_client
