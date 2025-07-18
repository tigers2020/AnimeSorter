import aiohttp
import typing as t
import asyncio
from aiohttp import ClientTimeout, TCPConnector

class TMDBApiError(Exception):
    """TMDB API 요청 실패 예외"""
    pass

class TMDBClient:
    """
    TMDB API 클라이언트 (연결 풀 최적화)
    """
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str, language: str = "ko-KR", max_connections: int = 100, max_connections_per_host: int = 10):
        """
        TMDBClient 초기화
        
        Args:
            api_key: TMDB API 키
            language: 응답 언어 (기본값: 한국어)
            max_connections: 전체 최대 연결 수
            max_connections_per_host: 호스트당 최대 연결 수
        """
        self.api_key = api_key
        self.language = language
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host
        self.session: t.Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """연결 풀이 최적화된 세션 초기화"""
        if self.session is None or self.session.closed:
            # 연결 풀 최적화 설정
            connector = TCPConnector(
                limit=self.max_connections,  # 전체 최대 연결 수
                limit_per_host=self.max_connections_per_host,  # 호스트당 최대 연결 수
                keepalive_timeout=30,  # 연결 유지 시간 (초)
                enable_cleanup_closed=True,  # 닫힌 연결 정리
                ttl_dns_cache=300,  # DNS 캐시 TTL (초)
                use_dns_cache=True,  # DNS 캐시 사용
            )
            
            # 타임아웃 설정
            timeout = ClientTimeout(
                total=30,  # 전체 요청 타임아웃
                connect=10,  # 연결 타임아웃
                sock_read=30,  # 소켓 읽기 타임아웃
            )
            
            # 최적화된 세션 생성
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'AnimeSorter/1.0',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate',
                }
            )

    async def close(self):
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def request(self, endpoint: str, params: t.Optional[dict] = None, method: str = "GET") -> dict:
        """
        API 요청 전송 (연결 풀 최적화)
        
        Args:
            endpoint: API 엔드포인트
            params: 요청 파라미터
            method: HTTP 메서드
            
        Returns:
            dict: API 응답 JSON
            
        Raises:
            TMDBApiError: API 요청 실패 시
        """
        await self.initialize()
        url = f"{self.BASE_URL}{endpoint}"
        request_params = {"api_key": self.api_key, "language": self.language}
        if params:
            request_params.update(params)
            
        try:
            async with self.session.request(method, url, params=request_params) as response:
                data = await response.json()
                if response.status != 200:
                    msg = data.get("status_message", "Unknown error")
                    raise TMDBApiError(f"TMDB API error: {msg} (status {response.status})")
                return data
        except asyncio.TimeoutError:
            raise TMDBApiError("Request timeout")
        except aiohttp.ClientError as e:
            raise TMDBApiError(f"Network error: {str(e)}")
        except Exception as e:
            raise TMDBApiError(f"Unexpected error: {str(e)}")

    def get_connection_stats(self) -> dict:
        """연결 풀 통계 정보 반환"""
        if not self.session or self.session.closed:
            return {"status": "closed"}
            
        connector = self.session.connector
        if not connector:
            return {"status": "no_connector"}
            
        return {
            "status": "active",
            "limit": connector.limit,
            "limit_per_host": connector.limit_per_host,
            "acquired": len(connector._acquired),
            "available": len(connector._available),
            "dns_cache_size": len(connector._resolver_cache) if hasattr(connector, '_resolver_cache') else 0
        } 