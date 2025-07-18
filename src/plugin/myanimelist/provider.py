"""
MyAnimeList API 프로바이더

MyAnimeList API를 사용하여 애니메이션 메타데이터를 검색하고 가져옵니다.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import aiohttp
from src.plugin.base import MetadataProvider, SearchResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MyAnimeListConfig:
    """MyAnimeList API 설정"""
    client_id: str
    client_secret: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    api_url: str = "https://api.myanimelist.net/v2"


class MyAnimeListProvider(MetadataProvider):
    """MyAnimeList API 프로바이더"""
    
    def __init__(self, config: MyAnimeListConfig):
        """
        MyAnimeList 프로바이더 초기화
        
        Args:
            config: MyAnimeList API 설정
        """
        self.config = config
        self.access_token = config.access_token
        self.refresh_token = config.refresh_token
        self.token_expires_at = 0
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if hasattr(self, 'session'):
            await self.session.close()
    
    async def _authenticate(self) -> bool:
        """MyAnimeList API 인증"""
        current_time = time.time()
        
        # 토큰이 유효한 경우 재사용
        if (self.access_token and 
            current_time < self.token_expires_at):
            return True
        
        # 리프레시 토큰이 있는 경우 갱신
        if self.refresh_token:
            return await self._refresh_token()
        
        # 클라이언트 크리덴셜 플로우로 인증
        return await self._client_credentials_auth()
    
    async def _client_credentials_auth(self) -> bool:
        """클라이언트 크리덴셜 플로우 인증"""
        try:
            auth_url = "https://myanimelist.net/v1/oauth2/token"
            auth_data = {
                'client_id': self.config.client_id,
                'client_secret': self.config.client_secret,
                'grant_type': 'client_credentials'
            }
            
            async with self.session.post(auth_url, data=auth_data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.access_token = token_data.get('access_token')
                    self.token_expires_at = time.time() + token_data.get('expires_in', 3600)
                    logger.info("MyAnimeList API 인증 성공")
                    return True
                else:
                    logger.error(f"MyAnimeList API 인증 실패: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"MyAnimeList API 인증 중 오류: {e}")
            return False
    
    async def _refresh_token(self) -> bool:
        """액세스 토큰 갱신"""
        try:
            auth_url = "https://myanimelist.net/v1/oauth2/token"
            auth_data = {
                'client_id': self.config.client_id,
                'client_secret': self.config.client_secret,
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            async with self.session.post(auth_url, data=auth_data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.access_token = token_data.get('access_token')
                    self.refresh_token = token_data.get('refresh_token', self.refresh_token)
                    self.token_expires_at = time.time() + token_data.get('expires_in', 3600)
                    logger.info("MyAnimeList 토큰 갱신 성공")
                    return True
                else:
                    logger.error(f"MyAnimeList 토큰 갱신 실패: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"MyAnimeList 토큰 갱신 중 오류: {e}")
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
            search_url = f"{self.config.api_url}/anime"
            params = {
                'q': title,
                'limit': 10,
                'fields': 'id,title,main_picture,mean,media_type,status,genres,num_episodes,synopsis,start_date'
            }
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            async with self.session.get(search_url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_search_response(data, title, year)
                else:
                    logger.error(f"MyAnimeList 검색 요청 실패: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"MyAnimeList 검색 중 오류: {e}")
            return None
    
    def _parse_search_response(self, data: Dict, title: str, year: Optional[int] = None) -> Optional[SearchResult]:
        """
        검색 응답 파싱
        
        Args:
            data: API 응답 데이터
            title: 원본 검색 제목
            year: 검색 연도
            
        Returns:
            파싱된 검색 결과 또는 None
        """
        try:
            anime_list = data.get('data', [])
            if not anime_list:
                return None
            
            # 가장 적합한 결과 선택
            best_match = self._find_best_match(anime_list, title, year)
            if not best_match:
                return None
            
            anime = best_match['node']
            
            # 장르 정보 추출
            genres = []
            if 'genres' in anime:
                genres = [genre['name'] for genre in anime['genres']]
            
            # 포스터 URL 추출
            poster_url = None
            if 'main_picture' in anime and anime['main_picture']:
                poster_url = anime['main_picture'].get('large')
            
            return SearchResult(
                id=anime.get('id'),
                title=anime.get('title'),
                original_title=anime.get('title'),
                overview=anime.get('synopsis', ''),
                release_date=anime.get('start_date'),
                genres=genres,
                poster_url=poster_url,
                rating=anime.get('mean'),
                episode_count=anime.get('num_episodes'),
                status=anime.get('status'),
                source='myanimelist'
            )
            
        except Exception as e:
            logger.error(f"MyAnimeList 응답 파싱 오류: {e}")
            return None
    
    def _find_best_match(self, anime_list: List[Dict], title: str, year: Optional[int] = None) -> Optional[Dict]:
        """
        가장 적합한 애니메이션 찾기
        
        Args:
            anime_list: 애니메이션 목록
            title: 검색 제목
            year: 검색 연도
            
        Returns:
            가장 적합한 애니메이션 또는 None
        """
        if not anime_list:
            return None
        
        # 제목 유사도 계산
        best_score = 0
        best_match = None
        
        for anime in anime_list:
            anime_title = anime['node'].get('title', '').lower()
            search_title = title.lower()
            
            # 간단한 유사도 계산
            score = self._calculate_similarity(anime_title, search_title)
            
            # 연도가 일치하면 점수 증가
            if year and anime['node'].get('start_date'):
                try:
                    anime_year = int(anime['node']['start_date'][:4])
                    if anime_year == year:
                        score += 0.3
                except (ValueError, IndexError):
                    pass
            
            if score > best_score:
                best_score = score
                best_match = anime
        
        # 최소 유사도 임계값
        if best_score > 0.5:
            return best_match
        
        return None
    
    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """
        제목 유사도 계산
        
        Args:
            title1: 첫 번째 제목
            title2: 두 번째 제목
            
        Returns:
            유사도 점수 (0.0 ~ 1.0)
        """
        # 간단한 문자열 유사도 계산
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    async def get_anime_details(self, anime_id: int) -> Optional[Dict[str, Any]]:
        """
        애니메이션 상세 정보 가져오기
        
        Args:
            anime_id: MyAnimeList 애니메이션 ID
            
        Returns:
            상세 정보 딕셔너리 또는 None
        """
        if not await self._authenticate():
            return None
        
        try:
            detail_url = f"{self.config.api_url}/anime/{anime_id}"
            params = {
                'fields': 'id,title,main_picture,mean,media_type,status,genres,num_episodes,synopsis,start_date,end_date,rating,studios,source'
            }
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            async with self.session.get(detail_url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"MyAnimeList 상세 정보 요청 실패: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"MyAnimeList 상세 정보 가져오기 오류: {e}")
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
        return "MyAnimeList"
    
    def get_provider_version(self) -> str:
        """프로바이더 버전 반환"""
        return "1.0"
    
    def is_available(self) -> bool:
        """프로바이더 사용 가능 여부"""
        return bool(self.config.client_id and self.config.client_secret) 