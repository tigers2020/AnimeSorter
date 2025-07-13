import logging
from typing import Optional, Any, List
from .api.client import TMDBClient, TMDBApiError
from .api.endpoints import TMDBEndpoints
from src.utils.file_cleaner import FileCleaner
from difflib import SequenceMatcher

class TMDBProvider:
    """
    TMDB 메타데이터 제공자 (캐시/로깅/예외 구조 개선)
    """
    def __init__(self, api_key: str, cache_db: Optional[Any] = None, language: str = "ko-KR"):
        self.client = TMDBClient(api_key, language)
        self.endpoints = TMDBEndpoints(self.client)
        self.cache_db = cache_db
        self.logger = logging.getLogger("animesorter.tmdb")

    async def initialize(self):
        await self.client.initialize()
        if self.cache_db:
            await self.cache_db.initialize()

    async def close(self):
        await self.client.close()
        if self.cache_db:
            await self.cache_db.close()

    async def search(self, title: str, year: Optional[int] = None) -> Optional[dict]:
        cache_key = self._generate_cache_key(title, year)
        # 1. 캐시 우선 조회
        if self.cache_db:
            try:
                cached = await self.cache_db.get_cache(cache_key)
                if cached:
                    self.logger.info(f"[TMDB] Cache hit: {cache_key}")
                    return cached
            except Exception as e:
                self.logger.warning(f"[TMDB] Cache error: {e}")
        # 2. API 검색
        try:
            multi_results = await self.endpoints.search_multi(title, year)
            filtered = self._filter_and_sort_results(multi_results.get("results", []), title)
            if not filtered:
                self.logger.warning(f"[TMDB] No results for: {title} ({year})")
                return None
            best = filtered[0]
            result = await self.get_details(best["id"], best["media_type"])
            # 3. 캐시에 저장
            if result and self.cache_db:
                try:
                    await self.cache_db.set_cache(cache_key, result, year)
                except Exception as e:
                    self.logger.warning(f"[TMDB] Cache save error: {e}")
            return result
        except TMDBApiError as e:
            self.logger.error(f"[TMDB] API error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"[TMDB] Unexpected error: {e}", exc_info=True)
            raise TMDBApiError(f"TMDBProvider search failed: {e}")

    async def get_details(self, media_id: Any, media_type: str) -> Optional[dict]:
        try:
            if media_type == "tv":
                return await self.endpoints.get_tv_details(media_id)
            elif media_type == "movie":
                return await self.endpoints.get_movie_details(media_id)
            else:
                self.logger.warning(f"[TMDB] Unknown media_type: {media_type}")
                return None
        except TMDBApiError as e:
            self.logger.error(f"[TMDB] Failed to get details: {e}")
            raise
        except Exception as e:
            self.logger.error(f"[TMDB] Unexpected error in get_details: {e}", exc_info=True)
            raise TMDBApiError(f"get_details failed: {e}")

    def _filter_and_sort_results(self, results: List[dict], query: str) -> List[dict]:
        # 지원 미디어 타입만 필터
        filtered = [r for r in results if r.get("media_type") in ("tv", "movie")]
        ANIMATION_GENRE_ID = 16
        def score(item):
            # 제목 유사도(0~100)
            title_field = "name" if item.get("media_type") == "tv" else "title"
            title = item.get(title_field, "")
            sim = int(SequenceMatcher(None, query.lower(), title.lower()).ratio() * 100)
            # 애니메이션 장르 보너스
            genre_bonus = 20 if ANIMATION_GENRE_ID in item.get("genre_ids", []) else 0
            # 인기도(0~10)
            pop = min(10, int(item.get("popularity", 0) / 10))
            return sim + genre_bonus + pop
        scored = [(item, score(item)) for item in filtered]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in scored]

    def _generate_cache_key(self, title: str, year: Optional[int]) -> str:
        # 캐시 키 규칙: 소문자, 공백/특수문자→_ , 연도 없으면 any
        import re
        key = re.sub(r"[^a-z0-9]+", "_", title.lower())
        key = key.strip("_")
        year_part = str(year) if year else "any"
        return f"{key}_{year_part}" 