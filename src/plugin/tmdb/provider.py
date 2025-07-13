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

    def _generate_progressive_titles(self, title: str) -> List[str]:
        """
        제목을 점진적으로 단순화한 버전들을 생성
        
        Args:
            title: 원본 제목
            
        Returns:
            List[str]: 점진적으로 단순화된 제목 목록
        """
        titles = [title]  # 원본 제목을 첫 번째로
        
        # 공백으로 분리하여 단어 단위로 제거
        words = title.split()
        
        # 끝에서부터 단어를 하나씩 제거
        for i in range(len(words) - 1, 0, -1):
            simplified = " ".join(words[:i]).strip()
            if simplified and simplified not in titles:
                titles.append(simplified)
        
        return titles

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
        
        # 2. 점진적 제목 단순화 전략으로 검색 시도
        progressive_titles = self._generate_progressive_titles(title)
        
        for attempt, search_title in enumerate(progressive_titles):
            try:
                if attempt > 0:
                    self.logger.info(f"[TMDB] Fallback attempt {attempt}: '{search_title}'")
                
                multi_results = await self.endpoints.search_multi(search_title, year)
                filtered = self._filter_and_sort_results(multi_results.get("results", []), search_title)
                
                if filtered:
                    # 검색 성공
                    best = filtered[0]
                    result = await self.get_details(best["id"], best["media_type"])
                    
                    if result:
                        # 원본 제목으로 캐시에 저장 (다음에 바로 찾을 수 있도록)
                        if self.cache_db:
                            try:
                                await self.cache_db.set_cache(cache_key, result, year)
                            except Exception as e:
                                self.logger.warning(f"[TMDB] Cache save error: {e}")
                        
                        if attempt > 0:
                            self.logger.info(f"[TMDB] Fallback success with '{search_title}' for original '{title}'")
                        
                        return result
                
            except TMDBApiError as e:
                self.logger.error(f"[TMDB] API error during search attempt {attempt + 1}: {e}")
                # API 오류는 재시도하지 않고 바로 예외 발생
                raise
            except Exception as e:
                self.logger.error(f"[TMDB] Unexpected error during search attempt {attempt + 1}: {e}")
                # 예상치 못한 오류도 재시도하지 않고 예외 발생
                raise TMDBApiError(f"TMDBProvider search failed: {e}")
        
        # 모든 시도 실패
        self.logger.warning(f"[TMDB] No results for: {title} ({year}) - tried {len(progressive_titles)} variations")
        return None

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
        
        if not filtered:
            return []
        
        ANIMATION_GENRE_ID = 16
        
        # 1차: 애니메이션 장르 결과만 분리
        animation_results = [r for r in filtered if ANIMATION_GENRE_ID in r.get("genre_ids", [])]
        non_animation_results = [r for r in filtered if ANIMATION_GENRE_ID not in r.get("genre_ids", [])]
        
        def calculate_score(item, is_animation=False):
            # 제목 유사도(0~100)
            title_field = "name" if item.get("media_type") == "tv" else "title"
            title = item.get(title_field, "")
            sim = int(SequenceMatcher(None, query.lower(), title.lower()).ratio() * 100)
            
            # 인기도(0~10)
            pop = min(10, int(item.get("popularity", 0) / 10))
            
            # 애니메이션인 경우 기본 점수에 큰 보너스
            animation_bonus = 1000 if is_animation else 0
            
            return sim + pop + animation_bonus
        
        # 애니메이션 결과 정렬
        if animation_results:
            animation_scored = [(item, calculate_score(item, True)) for item in animation_results]
            animation_scored.sort(key=lambda x: x[1], reverse=True)
            
            self.logger.info(f"[TMDB] Found {len(animation_results)} animation results for '{query}', prioritizing anime")
            
            # 애니메이션 결과가 있으면 애니메이션만 반환 (강력한 우선순위)
            return [item for item, _ in animation_scored]
        
        # 애니메이션 결과가 없을 때만 다른 장르 고려
        if non_animation_results:
            self.logger.info(f"[TMDB] No animation results for '{query}', considering other genres")
            
            non_animation_scored = [(item, calculate_score(item, False)) for item in non_animation_results]
            non_animation_scored.sort(key=lambda x: x[1], reverse=True)
            
            return [item for item, _ in non_animation_scored]
        
        return []

    def _generate_cache_key(self, title: str, year: Optional[int]) -> str:
        """캐시 키 생성"""
        normalized_title = title.lower().replace(" ", "_")
        year_part = f"_{year}" if year else "_any"
        return f"{normalized_title}{year_part}" 