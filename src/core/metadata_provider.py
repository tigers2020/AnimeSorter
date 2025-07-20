"""
메타데이터 제공자 인터페이스

스트리밍 파이프라인에서 사용할 메타데이터 제공자 인터페이스를 정의합니다.
기존 TMDB provider를 래핑하여 통일된 인터페이스를 제공합니다.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class MetadataProvider(ABC):
    """
    메타데이터 제공자 추상 클래스
    
    모든 메타데이터 제공자는 이 인터페이스를 구현해야 합니다.
    """
    
    @abstractmethod
    async def search(
        self, 
        title: str, 
        year: Optional[int] = None, 
        season: Optional[int] = None,
        is_special: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        제목, 연도, 시즌으로 메타데이터 검색
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            season: 시즌 번호 (옵션)
            is_special: 특집 여부 (옵션)
            
        Returns:
            dict or None: 검색 결과 또는 None
        """
        pass
        
    @abstractmethod
    async def get_details(
        self, 
        item_id: int, 
        media_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        아이템 상세 정보 조회
        
        Args:
            item_id: 아이템 ID
            media_type: 미디어 타입 ('tv' 또는 'movie')
            
        Returns:
            dict or None: 상세 정보 또는 None
        """
        pass
        
    @abstractmethod
    async def initialize(self) -> None:
        """초기화"""
        pass
        
    @abstractmethod
    async def close(self) -> None:
        """리소스 정리"""
        pass


class StreamingMetadataProvider:
    """
    스트리밍 파이프라인용 메타데이터 제공자
    
    기존 TMDB provider를 래핑하여 스트리밍 파이프라인에서 사용할 수 있도록 합니다.
    """
    
    def __init__(self, tmdb_provider, cache_db=None):
        """
        StreamingMetadataProvider 초기화
        
        Args:
            tmdb_provider: 기존 TMDB provider 인스턴스
            cache_db: 캐시 데이터베이스 (옵션)
        """
        self.tmdb_provider = tmdb_provider
        self.cache_db = cache_db
        self.logger = logging.getLogger(__name__)
        
    async def search(
        self, 
        title: str, 
        year: Optional[int] = None, 
        season: Optional[int] = None,
        is_special: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        제목, 연도, 시즌으로 메타데이터 검색
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            season: 시즌 번호 (옵션)
            is_special: 특집 여부 (옵션)
            
        Returns:
            dict or None: 검색 결과 또는 None
        """
        try:
            # TMDB provider의 search 메서드 호출
            result = await self.tmdb_provider.search(
                title=title,
                year=year,
                season=season,
                is_special=is_special
            )
            
            if result:
                self.logger.info(f"Found metadata for '{title}': {result.get('name', result.get('title', 'Unknown'))}")
            else:
                self.logger.warning(f"No metadata found for '{title}'")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error searching metadata for '{title}': {e}")
            return None
            
    async def get_details(
        self, 
        item_id: int, 
        media_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        아이템 상세 정보 조회
        
        Args:
            item_id: 아이템 ID
            media_type: 미디어 타입 ('tv' 또는 'movie')
            
        Returns:
            dict or None: 상세 정보 또는 None
        """
        try:
            # TMDB provider의 get_details 메서드 호출
            result = await self.tmdb_provider.get_details(
                item_id=item_id,
                media_type=media_type
            )
            
            if result:
                self.logger.info(f"Retrieved details for {media_type} ID {item_id}")
            else:
                self.logger.warning(f"No details found for {media_type} ID {item_id}")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting details for {media_type} ID {item_id}: {e}")
            return None
            
    async def initialize(self) -> None:
        """초기화"""
        try:
            # TMDB provider 초기화 (필요한 경우)
            if hasattr(self.tmdb_provider, 'initialize'):
                await self.tmdb_provider.initialize()
                
            # 캐시 데이터베이스 초기화
            if self.cache_db:
                await self.cache_db.initialize()
                
            self.logger.info("StreamingMetadataProvider initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing StreamingMetadataProvider: {e}")
            
    async def close(self) -> None:
        """리소스 정리"""
        try:
            # TMDB provider 정리
            if hasattr(self.tmdb_provider, 'close'):
                await self.tmdb_provider.close()
                
            # 캐시 데이터베이스 정리
            if self.cache_db:
                await self.cache_db.close()
                
            self.logger.info("StreamingMetadataProvider closed")
            
        except Exception as e:
            self.logger.error(f"Error closing StreamingMetadataProvider: {e}")
            
    async def search_with_retry(
        self, 
        title: str, 
        year: Optional[int] = None, 
        season: Optional[int] = None,
        is_special: bool = False,
        max_retries: int = 3,
        delay: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        재시도 메커니즘이 포함된 메타데이터 검색
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            season: 시즌 번호 (옵션)
            is_special: 특집 여부 (옵션)
            max_retries: 최대 재시도 횟수
            delay: 재시도 간격 (초)
            
        Returns:
            dict or None: 검색 결과 또는 None
        """
        retries = 0
        last_error = None
        
        while retries < max_retries:
            try:
                result = await self.search(title, year, season, is_special)
                if result:
                    return result
                    
            except Exception as e:
                retries += 1
                last_error = e
                self.logger.warning(
                    f"Search attempt {retries}/{max_retries} failed for '{title}': {e}"
                )
                
                if retries < max_retries:
                    # 지수 백오프 (1s, 2s, 4s, ...)
                    wait_time = delay * (2 ** (retries - 1))
                    self.logger.info(f"Retrying in {wait_time:.1f} seconds...")
                    await asyncio.sleep(wait_time)
                    
        # 모든 재시도 실패
        self.logger.error(f"All {max_retries} search attempts failed for '{title}': {last_error}")
        return None
        
    def get_provider_info(self) -> Dict[str, Any]:
        """제공자 정보 반환"""
        return {
            "name": "TMDB",
            "version": "1.0",
            "supports_tv": True,
            "supports_movies": True,
            "supports_seasons": True,
            "supports_specials": True
        } 