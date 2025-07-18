import typing as t
from .client import TMDBClient

class TMDBEndpoints:
    """
    TMDB API 엔드포인트 래퍼 (기본 뼈대)
    """
    def __init__(self, client: TMDBClient):
        self.client = client

    async def search_multi(self, query: str, year: t.Optional[int] = None, page: int = 1) -> dict:
        params = {"query": query, "page": page}
        if year:
            params["year"] = year
        return await self.client.request("/search/multi", params)

    async def search_tv(self, query: str, year: t.Optional[int] = None, page: int = 1) -> dict:
        params = {"query": query, "page": page}
        if year:
            params["first_air_date_year"] = year
        return await self.client.request("/search/tv", params)

    async def search_movie(self, query: str, year: t.Optional[int] = None, page: int = 1) -> dict:
        params = {"query": query, "page": page}
        if year:
            params["year"] = year
        return await self.client.request("/search/movie", params)

    async def get_tv_details(self, tv_id: int) -> dict:
        params = {"append_to_response": "seasons,images,genres"}
        return await self.client.request(f"/tv/{tv_id}", params)

    async def get_movie_details(self, movie_id: int) -> dict:
        params = {"append_to_response": "images,credits,genres"}
        return await self.client.request(f"/movie/{movie_id}", params) 