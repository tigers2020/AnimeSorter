"""
메타데이터 서비스 - TMDB API 호출 및 메타데이터 관리
"""

import asyncio
from dataclasses import dataclass
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

from src.core.tmdb_client import TMDBAnimeInfo, TMDBClient
from src.gui.interfaces.i_service import IService


@dataclass
class MetadataSearchResult:
    """메타데이터 검색 결과"""

    success: bool
    anime_info: TMDBAnimeInfo | None = None
    error_message: str | None = None
    search_query: str = ""


class MetadataService(QObject, IService):
    """메타데이터 서비스 - TMDB API 호출 및 메타데이터 관리"""

    # 시그널 정의
    search_started = pyqtSignal(str)  # 검색 시작
    search_completed = pyqtSignal(MetadataSearchResult)  # 검색 완료
    search_failed = pyqtSignal(str, str)  # 검색 실패 (쿼리, 에러메시지)

    def __init__(self, event_bus=None):
        super().__init__()
        self.event_bus = event_bus
        self.tmdb_client = TMDBClient()
        self._search_cache: dict[str, MetadataSearchResult] = {}
        self._max_cache_size = 1000

    def initialize(self) -> bool:
        """서비스 초기화"""
        try:
            # TMDB 클라이언트 초기화 확인
            if not self.tmdb_client.is_configured():
                print("⚠️ TMDB 클라이언트가 구성되지 않았습니다.")
                return False
            print("✅ MetadataService 초기화 완료")
            return True
        except Exception as e:
            print(f"❌ MetadataService 초기화 실패: {e}")
            return False

    def cleanup(self):
        """서비스 정리"""
        self._search_cache.clear()
        print("🧹 MetadataService 정리 완료")

    async def search_anime_async(self, title: str, year: int | None = None) -> MetadataSearchResult:
        """비동기 애니메이션 검색"""
        try:
            # 캐시 확인
            cache_key = f"{title}_{year}" if year else title
            if cache_key in self._search_cache:
                print(f"📋 캐시된 결과 사용: {title}")
                return self._search_cache[cache_key]

            # 검색 시작 시그널
            self.search_started.emit(title)

            # TMDB 검색 실행
            anime_info = await self.tmdb_client.search_anime_async(title, year)

            if anime_info:
                result = MetadataSearchResult(
                    success=True, anime_info=anime_info, search_query=title
                )
                print(f"✅ 검색 성공: {title} -> {anime_info.name}")
            else:
                result = MetadataSearchResult(
                    success=False, error_message="검색 결과가 없습니다.", search_query=title
                )
                print(f"⚠️ 검색 결과 없음: {title}")

            # 캐시에 저장
            self._cache_result(cache_key, result)

            # 검색 완료 시그널
            self.search_completed.emit(result)
            return result

        except Exception as e:
            error_msg = f"검색 중 오류 발생: {str(e)}"
            result = MetadataSearchResult(
                success=False, error_message=error_msg, search_query=title
            )
            print(f"❌ 검색 실패: {title} - {e}")
            self.search_failed.emit(title, error_msg)
            return result

    def search_anime_sync(self, title: str, year: int | None = None) -> MetadataSearchResult:
        """동기 애니메이션 검색 (비동기 래퍼)"""
        try:
            # 새로운 이벤트 루프 생성 또는 기존 루프 사용
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
            print(f"❌ 동기 검색 실패: {title} - {e}")
            return result

    def get_anime_details(self, tmdb_id: int) -> TMDBAnimeInfo | None:
        """TMDB ID로 애니메이션 상세 정보 조회"""
        try:
            return self.tmdb_client.get_anime_details(tmdb_id)
        except Exception as e:
            print(f"❌ 애니메이션 상세 정보 조회 실패 (ID: {tmdb_id}): {e}")
            return None

    def get_search_suggestions(self, partial_title: str, limit: int = 5) -> list[str]:
        """검색 제안 목록 반환"""
        try:
            suggestions = []
            for cached_key in self._search_cache.keys():
                if partial_title.lower() in cached_key.lower():
                    suggestions.append(cached_key)
                    if len(suggestions) >= limit:
                        break
            return suggestions
        except Exception as e:
            print(f"❌ 검색 제안 생성 실패: {e}")
            return []

    def clear_cache(self):
        """검색 캐시 정리"""
        self._search_cache.clear()
        print("🧹 메타데이터 검색 캐시 정리 완료")

    def get_cache_stats(self) -> dict[str, Any]:
        """캐시 통계 반환"""
        return {
            "cache_size": len(self._search_cache),
            "max_cache_size": self._max_cache_size,
            "cache_keys": list(self._search_cache.keys())[:10],  # 처음 10개만
        }

    def _cache_result(self, key: str, result: MetadataSearchResult):
        """검색 결과를 캐시에 저장"""
        # 캐시 크기 제한 확인
        if len(self._search_cache) >= self._max_cache_size:
            # 가장 오래된 항목 제거 (FIFO)
            oldest_key = next(iter(self._search_cache))
            del self._search_cache[oldest_key]

        self._search_cache[key] = result

    def is_configured(self) -> bool:
        """TMDB 클라이언트 구성 상태 확인"""
        return self.tmdb_client.is_configured()

    def get_tmdb_client(self) -> TMDBClient:
        """TMDB 클라이언트 인스턴스 반환"""
        return self.tmdb_client
