"""
TMDB 메타데이터 제공자

MetadataProvider 인터페이스를 구현한 TMDB 제공자
"""

import re
from typing import Any, Dict, List, Optional

from thefuzz import fuzz
from loguru import logger

from src.cache_db import CacheDB
from src.exceptions import MetadataError, TMDBApiError
from src.plugin.base import MetadataProvider
from src.plugin.tmdb.api.client import TMDBClient
from src.plugin.tmdb.api.endpoints import TMDBEndpoints


class TMDBProvider(MetadataProvider):
    """TMDB 메타데이터 제공자"""
    
    def __init__(self, api_key: str, cache_db: Optional[CacheDB] = None, language: str = "ko-KR"):
        """
        TMDBProvider 초기화
        
        Args:
            api_key: TMDB API 키
            cache_db: 캐시 데이터베이스 인스턴스 (옵션)
            language: 응답 언어 (기본값: 한국어)
        """
        self.client = TMDBClient(api_key, language)
        self.endpoints = TMDBEndpoints(self.client)
        self.cache_db = cache_db
        
    async def initialize(self) -> None:
        """초기화"""
        await self.client.initialize()
        if self.cache_db:
            await self.cache_db.initialize()
            
    async def close(self) -> None:
        """리소스 정리"""
        await self.client.close()
        if self.cache_db:
            await self.cache_db.close()
        
    async def search(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """
        제목과 연도로 메타데이터 검색
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            
        Returns:
            dict or None: 검색 결과 또는 None (결과 없음)
        """
        # 캐시 확인
        if self.cache_db:
            cache_key = self._generate_cache_key(title, year)
            cached_result = await self.cache_db.get_cache(cache_key)
            if cached_result:
                logger.info(f"'{title}' ({year})에 대한 캐시 결과 사용")
                return cached_result
        
        # 검색어 정제
        query = self._clean_query(title)
        
        try:
            # 멀티 검색 먼저 시도
            multi_results = await self.endpoints.search_multi(query, year)
            
            # 결과 필터링 및 정렬
            filtered_results = self._filter_and_sort_results(
                multi_results.get("results", []), title
            )
            
            if not filtered_results:
                logger.warning(f"'{title}' ({year})에 대한 검색 결과가 없습니다.")
                return None
                
            # 가장 관련성 높은 결과 선택
            best_match = filtered_results[0]
            logger.info(f"'{title}'에 대한 최적 일치: {best_match.get('name', best_match.get('title', 'Unknown'))}")
            
            # 상세 정보 가져오기
            result = await self.get_details(best_match["id"], best_match["media_type"])
            
            # 캐시에 저장
            if result and self.cache_db:
                await self.cache_db.set_cache(cache_key, result, year)
                
            return result
        except TMDBApiError as e:
            logger.error(f"TMDB API 오류: {str(e)}")
            raise MetadataError(f"메타데이터 검색 실패: {str(e)}") from e
        
    async def get_details(self, media_id: Any, media_type: str) -> Optional[Dict]:
        """
        ID와 타입으로 상세 정보 조회
        
        Args:
            media_id: 미디어 ID
            media_type: 미디어 타입 ("tv" 또는 "movie")
            
        Returns:
            dict or None: 상세 정보 또는 None
        """
        try:
            # media_type에 따라 적절한 엔드포인트 호출
            if media_type == "tv":
                details = await self.endpoints.get_tv_details(media_id)
            elif media_type == "movie":
                details = await self.endpoints.get_movie_details(media_id)
            else:
                logger.warning(f"지원되지 않는 미디어 타입: {media_type}")
                return None
                
            # media_type 필드 추가 (API 응답에 포함되지 않기 때문)
            details["media_type"] = media_type
            
            return details
        except TMDBApiError as e:
            logger.error(f"미디어 상세 정보 조회 실패 (ID: {media_id}, Type: {media_type}): {str(e)}")
            return None
        
    def _filter_and_sort_results(self, results: List[Dict], query: str) -> List[Dict]:
        """
        결과 필터링 및 정렬
        
        애니메이션 관련 결과를 우선시하고 제목 유사도로 정렬
        
        Args:
            results: 검색 결과 목록
            query: 원본 검색어
            
        Returns:
            List[dict]: 필터링 및 정렬된 결과
        """
        # 지원되는 미디어 타입만 필터링
        filtered = [r for r in results if r.get("media_type") in ("tv", "movie")]
        
        if not filtered:
            return []
        
        # 애니메이션 장르 ID (TMDB 기준)
        ANIMATION_GENRE_ID = 16
        
        # 점수 계산 함수
        def calculate_score(item):
            base_score = 0
            
            # 제목 유사도 (0-100)
            title_field = "name" if item.get("media_type") == "tv" else "title"
            item_title = item.get(title_field, "")
            
            # 기본 제목 유사도
            title_similarity = fuzz.ratio(query.lower(), item_title.lower())
            base_score += title_similarity
            
            # 애니메이션 장르 보너스 (+20)
            if ANIMATION_GENRE_ID in item.get("genre_ids", []):
                base_score += 20
                
            # 인기도 보너스 (0-10)
            popularity = min(10, item.get("popularity", 0) / 10)
            base_score += popularity
            
            return base_score
            
        # 점수로 정렬
        scored_results = [(item, calculate_score(item)) for item in filtered]
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        return [item for item, score in scored_results]
    
    def _generate_cache_key(self, title: str, year: Optional[int]) -> str:
        """캐시 키 생성"""
        if self.cache_db:
            return self.cache_db._generate_key(title, year)
        
        # CacheDB 없는 경우 직접 구현
        normalized_title = title.lower().replace(" ", "_")
        normalized_title = "".join(c for c in normalized_title if c.isalnum() or c == "_")
        year_part = f"_{year}" if year else "_any"
        return f"{normalized_title}{year_part}"
    
    def _clean_query(self, query: str) -> str:
        """
        검색어 정제
        
        Args:
            query: 원본 검색어
            
        Returns:
            str: 정제된 검색어
        """
        # 괄호 안의 내용 제거 (예: "제목 (부제)")
        cleaned = re.sub(r'\([^)]*\)', '', query)
        
        # 특수문자 제거하고 공백으로 대체
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        
        # 연속된 공백 제거
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned 