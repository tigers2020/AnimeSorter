"""
메타데이터 제공자 인터페이스

모든 메타데이터 제공자가 구현해야 하는 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class MetadataProvider(ABC):
    """메타데이터 제공자 추상 베이스 클래스"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        메타데이터 제공자 초기화
        
        필요한 자원(API 클라이언트, 캐시 등) 초기화
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        메타데이터 제공자 종료
        
        사용한 자원 정리
        """
        pass
    
    @abstractmethod
    async def search(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """
        제목과 연도로 메타데이터 검색
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            
        Returns:
            dict or None: 검색 결과 또는 None (결과 없음)
        """
        pass
    
    @abstractmethod
    async def get_details(self, media_id: Any, media_type: str) -> Optional[Dict]:
        """
        ID와 타입으로 상세 정보 조회
        
        Args:
            media_id: 미디어 ID
            media_type: 미디어 타입 ("tv" 또는 "movie")
            
        Returns:
            dict or None: 상세 정보 또는 None
        """
        pass 