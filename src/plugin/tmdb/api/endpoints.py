"""
TMDB API 엔드포인트 래퍼

TMDB API 엔드포인트에 대한 래퍼 함수 구현
"""

from typing import Dict, Optional

from loguru import logger

from src.plugin.tmdb.api.client import TMDBClient


class TMDBEndpoints:
    """TMDB API 엔드포인트 래퍼"""
    
    def __init__(self, client: TMDBClient):
        """
        TMDBEndpoints 초기화
        
        Args:
            client: TMDBClient 인스턴스
        """
        self.client = client
        
    async def search_multi(self, query: str, year: Optional[int] = None) -> Dict:
        """
        통합 검색 (영화, TV 시리즈, 인물 등)
        
        Args:
            query: 검색어
            year: 연도 필터 (옵션)
            
        Returns:
            dict: 검색 결과
        """
        params = {"query": query}
        if year:
            params["year"] = year
            
        logger.debug(f"통합 검색: {query} (연도: {year})")
        return await self.client.request("/search/multi", params)
        
    async def search_tv(self, query: str, year: Optional[int] = None) -> Dict:
        """
        TV 시리즈 검색
        
        Args:
            query: 검색어
            year: 방영 연도 필터 (옵션)
            
        Returns:
            dict: 검색 결과
        """
        params = {"query": query}
        if year:
            params["first_air_date_year"] = year
            
        logger.debug(f"TV 시리즈 검색: {query} (연도: {year})")
        return await self.client.request("/search/tv", params)
        
    async def search_movie(self, query: str, year: Optional[int] = None) -> Dict:
        """
        영화 검색
        
        Args:
            query: 검색어
            year: 개봉 연도 필터 (옵션)
            
        Returns:
            dict: 검색 결과
        """
        params = {"query": query}
        if year:
            params["year"] = year
            
        logger.debug(f"영화 검색: {query} (연도: {year})")
        return await self.client.request("/search/movie", params)
        
    async def get_tv_details(self, tv_id: int) -> Dict:
        """
        TV 시리즈 상세 정보
        
        Args:
            tv_id: TV 시리즈 ID
            
        Returns:
            dict: TV 시리즈 상세 정보
        """
        params = {"append_to_response": "seasons,images,credits"}
        logger.debug(f"TV 시리즈 상세 정보 조회: {tv_id}")
        return await self.client.request(f"/tv/{tv_id}", params)
        
    async def get_movie_details(self, movie_id: int) -> Dict:
        """
        영화 상세 정보
        
        Args:
            movie_id: 영화 ID
            
        Returns:
            dict: 영화 상세 정보
        """
        params = {"append_to_response": "images,credits"}
        logger.debug(f"영화 상세 정보 조회: {movie_id}")
        return await self.client.request(f"/movie/{movie_id}", params)
        
    async def get_season_details(self, tv_id: int, season_number: int) -> Dict:
        """
        시즌 상세 정보
        
        Args:
            tv_id: TV 시리즈 ID
            season_number: 시즌 번호
            
        Returns:
            dict: 시즌 상세 정보
        """
        logger.debug(f"시즌 상세 정보 조회: TV ID {tv_id}, 시즌 {season_number}")
        return await self.client.request(f"/tv/{tv_id}/season/{season_number}")
        
    async def get_episode_details(self, tv_id: int, season_number: int, episode_number: int) -> Dict:
        """
        에피소드 상세 정보
        
        Args:
            tv_id: TV 시리즈 ID
            season_number: 시즌 번호
            episode_number: 에피소드 번호
            
        Returns:
            dict: 에피소드 상세 정보
        """
        logger.debug(f"에피소드 상세 정보 조회: TV ID {tv_id}, 시즌 {season_number}, 에피소드 {episode_number}")
        return await self.client.request(f"/tv/{tv_id}/season/{season_number}/episode/{episode_number}")
        
    async def get_configuration(self) -> Dict:
        """
        API 구성 정보 조회
        
        이미지 URL, 크기 옵션 등의 구성 정보
        
        Returns:
            dict: TMDB API 구성 정보
        """
        logger.debug("API 구성 정보 조회")
        return await self.client.request("/configuration") 