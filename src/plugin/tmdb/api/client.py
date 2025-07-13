import aiohttp
import typing as t

class TMDBApiError(Exception):
    """TMDB API 요청 실패 예외"""
    pass

class TMDBClient:
    """
    TMDB API 클라이언트 (기본 뼈대)
    """
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str, language: str = "ko-KR"):
        self.api_key = api_key
        self.language = language
        self.session: t.Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def request(self, endpoint: str, params: t.Optional[dict] = None, method: str = "GET") -> dict:
        await self.initialize()
        url = f"{self.BASE_URL}{endpoint}"
        request_params = {"api_key": self.api_key, "language": self.language}
        if params:
            request_params.update(params)
        async with self.session.request(method, url, params=request_params) as response:
            data = await response.json()
            if response.status != 200:
                msg = data.get("status_message", "Unknown error")
                raise TMDBApiError(f"TMDB API error: {msg} (status {response.status})")
            return data 