"""
플러그인 시스템 기본 인터페이스 정의

이 모듈은 메타데이터 제공자 플러그인들이 구현해야 하는
공통 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchResult:
    """검색 결과를 나타내는 데이터 클래스"""
    id: Any
    title: str
    original_title: str = ""
    media_type: str = "unknown"  # "tv", "movie", "ova", etc.
    year: Optional[int] = None
    overview: str = ""
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    genres: List[str] = None
    rating: Optional[float] = None
    provider: str = ""
    
    def __post_init__(self):
        if self.genres is None:
            self.genres = []


@dataclass
class ProviderConfig:
    """플러그인 제공자 설정"""
    name: str
    enabled: bool = True
    priority: int = 0  # 높을수록 우선순위가 높음
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    language: str = "ko-KR"


class MetadataProvider(ABC):
    """메타데이터 제공자 기본 인터페이스"""
    
    def __init__(self, config: ProviderConfig):
        """
        MetadataProvider 초기화
        
        Args:
            config: 제공자 설정
        """
        self.config = config
        self._initialized = False
        
    @abstractmethod
    async def initialize(self) -> None:
        """
        플러그인 초기화
        
        API 키 검증, 연결 테스트, 리소스 할당 등을 수행합니다.
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        플러그인 정리
        
        리소스 해제, 연결 종료 등을 수행합니다.
        """
        pass
    
    @abstractmethod
    async def search(self, title: str, year: Optional[int] = None) -> Optional[SearchResult]:
        """
        제목과 연도로 메타데이터 검색
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            
        Returns:
            SearchResult or None: 검색 결과 또는 None (결과 없음)
        """
        pass
    
    @abstractmethod
    async def get_details(self, media_id: Any) -> Optional[SearchResult]:
        """
        ID로 상세 정보 조회
        
        Args:
            media_id: 미디어 ID
            
        Returns:
            SearchResult or None: 상세 정보 또는 None
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        플러그인 사용 가능 여부 확인
        
        Returns:
            bool: 사용 가능 여부
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        API 연결 테스트
        
        Returns:
            bool: 연결 성공 여부
        """
        pass


class PluginError(Exception):
    """플러그인 관련 기본 예외"""
    pass


class PluginInitializationError(PluginError):
    """플러그인 초기화 실패 예외"""
    pass


class PluginConnectionError(PluginError):
    """플러그인 연결 실패 예외"""
    pass


class PluginSearchError(PluginError):
    """플러그인 검색 실패 예외"""
    pass


class PluginConfigError(PluginError):
    """플러그인 설정 오류 예외"""
    pass 