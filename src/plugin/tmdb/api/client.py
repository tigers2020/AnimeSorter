"""
TMDB API 클라이언트

TMDB API와 통신하는 클라이언트 클래스
"""

import asyncio
from typing import Dict, Optional

import aiohttp
from loguru import logger

from src.exceptions import NetworkError, TMDBApiError

# API 기본 URL
TMDB_API_BASE_URL = "https://api.themoviedb.org/3"

# 이미지 기본 URL (설정에서 동적으로 가져올 수도 있음)
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

# 이미지 크기 옵션
POSTER_SIZES = ["w92", "w154", "w185", "w342", "w500", "w780", "original"]
BACKDROP_SIZES = ["w300", "w780", "w1280", "original"]


class TMDBClient:
    """TMDB API 클라이언트"""
    
    def __init__(self, api_key: str, language: str = "ko-KR"):
        """
        TMDBClient 초기화
        
        Args:
            api_key: TMDB API 키
            language: 응답 언어 (기본값: 한국어)
        """
        self.api_key = api_key
        self.language = language
        self.session = None
        
    async def initialize(self) -> None:
        """aiohttp 세션 초기화"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            logger.debug("TMDB API 클라이언트 세션 초기화 완료")
            
    async def close(self) -> None:
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            logger.debug("TMDB API 클라이언트 세션 종료")
            
    async def request(
        self, 
        endpoint: str, 
        params: Optional[Dict] = None, 
        method: str = "GET",
        retry_count: int = 3,
        retry_delay: float = 1.0
    ) -> Dict:
        """
        API 요청 전송
        
        Args:
            endpoint: API 엔드포인트 (예: "/search/tv")
            params: 요청 파라미터
            method: HTTP 메서드 (기본값: GET)
            retry_count: 재시도 횟수
            retry_delay: 재시도 간격 (초)
            
        Returns:
            dict: API 응답 JSON
            
        Raises:
            TMDBApiError: API 요청 실패 시
            NetworkError: 네트워크 오류 발생 시
        """
        await self.initialize()
        
        url = f"{TMDB_API_BASE_URL}{endpoint}"
        request_params = {
            "api_key": self.api_key,
            "language": self.language
        }
        
        if params:
            request_params.update(params)
            
        attempt = 0
        last_error = None
        
        while attempt < retry_count:
            try:
                logger.debug(f"TMDB API 요청: {endpoint} (파라미터: {request_params})")
                
                async with self.session.request(method, url, params=request_params) as response:
                    data = await response.json()
                    
                    # 응답 상태 코드 확인
                    if response.status != 200:
                        error_message = data.get("status_message", "Unknown error")
                        logger.warning(f"TMDB API 오류: {error_message} (코드: {response.status})")
                        
                        # 429 (Too Many Requests) 오류 시 재시도
                        if response.status == 429:
                            attempt += 1
                            wait_time = retry_delay * (2 ** (attempt - 1))  # 지수 백오프
                            logger.info(f"속도 제한에 도달함. {wait_time:.1f}초 후 재시도 ({attempt}/{retry_count})...")
                            await asyncio.sleep(wait_time)
                            continue
                            
                        raise TMDBApiError(
                            f"API 오류: {error_message}",
                            status_code=response.status,
                            reason=error_message
                        )
                        
                    logger.debug(f"TMDB API 응답 성공: {endpoint}")
                    return data
                    
            except aiohttp.ClientError as e:
                last_error = e
                attempt += 1
                
                if attempt < retry_count:
                    wait_time = retry_delay * (2 ** (attempt - 1))
                    logger.warning(f"네트워크 오류, {wait_time:.1f}초 후 재시도 ({attempt}/{retry_count}): {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"모든 재시도 실패: {str(e)}")
                    raise NetworkError(f"API 요청 실패: {str(e)}") from e
                    
            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError("Timeout")
                attempt += 1
                
                if attempt < retry_count:
                    wait_time = retry_delay * (2 ** (attempt - 1))
                    logger.warning(f"요청 타임아웃, {wait_time:.1f}초 후 재시도 ({attempt}/{retry_count})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("모든 재시도 타임아웃")
                    raise NetworkError("API 요청 타임아웃") from None
        
        # 모든 재시도 실패
        raise NetworkError(f"최대 재시도 횟수 초과: {str(last_error)}")


def get_poster_url(poster_path: Optional[str], size: str = "w342") -> Optional[str]:
    """
    포스터 이미지 URL 생성
    
    Args:
        poster_path: 포스터 경로 (예: "/nkayOAUBUu4mMvyNf9iHSUiPjF1.jpg")
        size: 이미지 크기 (기본값: "w342")
        
    Returns:
        str or None: 포스터 URL 또는 None
    """
    if not poster_path:
        return None
        
    if size not in POSTER_SIZES:
        size = "w342"  # 기본 크기
        
    return f"{TMDB_IMAGE_BASE_URL}{size}{poster_path}"


def get_backdrop_url(backdrop_path: Optional[str], size: str = "w780") -> Optional[str]:
    """
    배경 이미지 URL 생성
    
    Args:
        backdrop_path: 배경 이미지 경로
        size: 이미지 크기 (기본값: "w780")
        
    Returns:
        str or None: 배경 이미지 URL 또는 None
    """
    if not backdrop_path:
        return None
        
    if size not in BACKDROP_SIZES:
        size = "w780"  # 기본 크기
        
    return f"{TMDB_IMAGE_BASE_URL}{size}{backdrop_path}" 