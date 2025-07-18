"""
AniDB API 프로바이더

AniDB API를 사용하여 애니메이션 메타데이터를 검색하고 가져옵니다.
"""

import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import aiohttp
from src.plugin.base import MetadataProvider, SearchResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AniDBConfig:
    """AniDB API 설정"""
    username: str
    password: str
    client_name: str = "animesorter"
    client_version: str = "1.0"
    api_url: str = "https://api.anidb.net:9001/httpapi"


class AniDBProvider(MetadataProvider):
    """AniDB API 프로바이더"""
    
    def __init__(self, config: AniDBConfig):
        """
        AniDB 프로바이더 초기화
        
        Args:
            config: AniDB API 설정
        """
        self.config = config
        self.session_id = None
        self.last_auth_time = 0
        self.auth_timeout = 3600  # 1시간
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if hasattr(self, 'session'):
            await self.session.close()
    
    async def _authenticate(self) -> bool:
        """AniDB API 인증"""
        current_time = time.time()
        
        # 세션이 유효한 경우 재사용
        if (self.session_id and 
            current_time - self.last_auth_time < self.auth_timeout):
            return True
        
        try:
            # 인증 요청
            auth_params = {
                'request': 'auth',
                'client': self.config.client_name,
                'clientver': self.config.client_version,
                'user': self.config.username,
                'pass': self.config.password
            }
            
            async with self.session.get(self.config.api_url, params=auth_params) as response:
                if response.status == 200:
                    text = await response.text()
                    if text.startswith('230'):
                        # 성공적인 인증
                        self.session_id = text.split('\n')[0].split(' ')[1]
                        self.last_auth_time = current_time
                        logger.info("AniDB API 인증 성공")
                        return True
                    else:
                        logger.error(f"AniDB API 인증 실패: {text}")
                        return False
                else:
                    logger.error(f"AniDB API 인증 요청 실패: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"AniDB API 인증 중 오류: {e}")
            return False
    
    async def search(self, title: str, year: Optional[int] = None) -> Optional[SearchResult]:
        """
        애니메이션 검색
        
        Args:
            title: 검색할 제목
            year: 연도 (선택사항)
            
        Returns:
            검색 결과 또는 None
        """
        if not await self._authenticate():
            return None
        
        try:
            # 검색 요청
            search_params = {
                'request': 'anime',
                'client': self.config.client_name,
                'clientver': self.config.client_version,
                'protover': '1',
                'aid': self._search_anime_id(title, year)
            }
            
            async with self.session.get(self.config.api_url, params=search_params) as response:
                if response.status == 200:
                    text = await response.text()
                    return self._parse_anime_response(text)
                else:
                    logger.error(f"AniDB 검색 요청 실패: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"AniDB 검색 중 오류: {e}")
            return None
    
    def _search_anime_id(self, title: str, year: Optional[int] = None) -> Optional[int]:
        """
        제목으로 애니메이션 ID 검색
        
        Args:
            title: 검색할 제목
            year: 연도 (선택사항)
            
        Returns:
            애니메이션 ID 또는 None
        """
        # 실제 구현에서는 AniDB의 검색 API를 사용해야 함
        # 여기서는 간단한 예시만 제공
        search_params = {
            'request': 'anime',
            'client': self.config.client_name,
            'clientver': self.config.client_version,
            'protover': '1',
            'type': 'json',
            'search': title
        }
        
        # 실제로는 비동기로 검색을 수행해야 함
        # 이 부분은 실제 AniDB API 문서를 참조하여 구현해야 함
        return None
    
    def _parse_anime_response(self, response_text: str) -> Optional[SearchResult]:
        """
        AniDB 응답 파싱
        
        Args:
            response_text: API 응답 텍스트
            
        Returns:
            파싱된 검색 결과 또는 None
        """
        try:
            # AniDB XML 응답 파싱
            # 실제 구현에서는 XML 파서를 사용해야 함
            lines = response_text.split('\n')
            
            result = {}
            for line in lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    result[key.strip()] = value.strip()
            
            if not result:
                return None
            
            return SearchResult(
                id=result.get('aid'),
                title=result.get('title'),
                original_title=result.get('title'),
                overview=result.get('description', ''),
                release_date=result.get('startdate'),
                genres=result.get('categories', '').split('|') if result.get('categories') else [],
                poster_url=None,  # AniDB는 포스터 URL을 직접 제공하지 않음
                rating=float(result.get('rating', 0)) / 10 if result.get('rating') else None,
                episode_count=int(result.get('episodes', 0)) if result.get('episodes') else None,
                status=result.get('status'),
                source='anidb'
            )
            
        except Exception as e:
            logger.error(f"AniDB 응답 파싱 오류: {e}")
            return None
    
    async def get_anime_details(self, anime_id: int) -> Optional[Dict[str, Any]]:
        """
        애니메이션 상세 정보 가져오기
        
        Args:
            anime_id: AniDB 애니메이션 ID
            
        Returns:
            상세 정보 딕셔너리 또는 None
        """
        if not await self._authenticate():
            return None
        
        try:
            params = {
                'request': 'anime',
                'client': self.config.client_name,
                'clientver': self.config.client_version,
                'protover': '1',
                'aid': anime_id
            }
            
            async with self.session.get(self.config.api_url, params=params) as response:
                if response.status == 200:
                    text = await response.text()
                    return self._parse_anime_response(text)
                else:
                    logger.error(f"AniDB 상세 정보 요청 실패: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"AniDB 상세 정보 가져오기 오류: {e}")
            return None
    
    async def search_by_filename(self, filename: str) -> Optional[SearchResult]:
        """
        파일명으로 애니메이션 검색
        
        Args:
            filename: 검색할 파일명
            
        Returns:
            검색 결과 또는 None
        """
        # 파일명에서 제목 추출
        from src.core.file_cleaner import FileCleaner
        
        cleaner = FileCleaner()
        clean_result = cleaner.clean_filename(filename)
        
        if not clean_result.title:
            return None
        
        return await self.search(clean_result.title, clean_result.year)
    
    def get_provider_name(self) -> str:
        """프로바이더 이름 반환"""
        return "AniDB"
    
    def get_provider_version(self) -> str:
        """프로바이더 버전 반환"""
        return "1.0"
    
    def is_available(self) -> bool:
        """프로바이더 사용 가능 여부"""
        return bool(self.config.username and self.config.password) 