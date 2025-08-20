"""
TMDB API 클라이언트 - AnimeSorter (최적화됨)

The Movie Database API를 사용하여 애니메이션 메타데이터를 검색하고 조회합니다.
tmdbsimple 라이브러리를 기반으로 구현되었으며, 성능 최적화가 적용되었습니다.
"""

import os
import json
import time
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
import tmdbsimple as tmdb
from dataclasses import dataclass, asdict
from datetime import datetime
from functools import lru_cache
import threading
from collections import deque


@dataclass
class TMDBAnimeInfo:
    """TMDB 애니메이션 정보"""
    id: int
    name: str
    original_name: str
    overview: str
    first_air_date: str
    last_air_date: str
    number_of_seasons: int
    number_of_episodes: int
    status: str
    type: str
    popularity: float
    vote_average: float
    vote_count: int
    genres: List[Dict[str, Any]]
    poster_path: str
    backdrop_path: str
    episode_run_time: List[int]
    networks: List[Dict[str, Any]]
    production_companies: List[Dict[str, Any]]
    languages: List[str]
    origin_country: List[str]
    in_production: bool
    last_episode_to_air: Optional[Dict[str, Any]]
    next_episode_to_air: Optional[Dict[str, Any]]
    seasons: List[Dict[str, Any]]
    external_ids: Dict[str, Any]
    images: Dict[str, Any]
    credits: Dict[str, Any]
    videos: Dict[str, Any]
    keywords: Dict[str, Any]
    recommendations: Dict[str, Any]
    similar: Dict[str, Any]
    translations: Dict[str, Any]
    content_ratings: Dict[str, Any]
    watch_providers: Dict[str, Any]


class RateLimiter:
    """API 속도 제한 관리"""
    
    def __init__(self, max_requests: int = 40, time_window: int = 10):
        """
        Args:
            max_requests: 시간 창 내 최대 요청 수
            time_window: 시간 창 (초)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """필요한 경우 대기"""
        with self.lock:
            now = time.time()
            
            # 만료된 요청 제거
            while self.requests and now - self.requests[0] > self.time_window:
                self.requests.popleft()
            
            # 속도 제한 확인
            if len(self.requests) >= self.max_requests:
                sleep_time = self.requests[0] + self.time_window - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            # 새 요청 추가
            self.requests.append(now)


class TMDBClient:
    """TMDB API 클라이언트 (최적화됨)"""
    
    def __init__(self, api_key: Optional[str] = None, language: str = 'ko-KR'):
        """TMDB 클라이언트 초기화"""
        self.language = language
        self.cache_dir = Path('.animesorter_cache')
        self.cache_dir.mkdir(exist_ok=True)
        
        # API 키 설정
        if api_key:
            tmdb.API_KEY = api_key
        else:
            # 환경 변수에서 API 키 가져오기
            api_key = os.getenv('TMDB_API_KEY')
            if api_key:
                tmdb.API_KEY = api_key
            else:
                raise ValueError("TMDB API 키가 필요합니다. 환경 변수 TMDB_API_KEY를 설정하거나 생성자에 전달하세요.")
        
        # 요청 타임아웃 설정 (권장: 5초)
        tmdb.REQUESTS_TIMEOUT = 5
        
        # 커스텀 세션 설정 (연결 풀링 최적화)
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,  # 연결 풀 크기
            pool_maxsize=20,      # 최대 연결 수
            max_retries=3,        # 재시도 횟수
            pool_block=False      # 비블로킹
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.session.headers.update({
            'User-Agent': 'AnimeSorter/2.0.0',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
        tmdb.REQUESTS_SESSION = self.session
        
        # 캐시 설정 (개선됨)
        self.cache_enabled = True
        self.cache_expiry = 3600  # 1시간
        self.memory_cache = {}  # 메모리 캐시 (빠른 접근용)
        self.memory_cache_size = 1000
        self.cache_lock = threading.Lock()
        
        # 포스터 이미지 캐시 디렉토리
        self.poster_cache_dir = self.cache_dir / 'posters'
        self.poster_cache_dir.mkdir(exist_ok=True)
        
        # 속도 제한 관리
        self.rate_limiter = RateLimiter(max_requests=40, time_window=10)
        
        # 비동기 세션 (이미지 다운로드용)
        self.async_session = None
        self.async_lock = threading.Lock()
        
    async def _get_async_session(self) -> aiohttp.ClientSession:
        """비동기 세션 가져오기 (싱글톤 패턴)"""
        if self.async_session is None or self.async_session.closed:
            async with self.async_lock:
                if self.async_session is None or self.async_session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=20,  # 동시 연결 제한
                        limit_per_host=10,  # 호스트당 연결 제한
                        ttl_dns_cache=300,  # DNS 캐시 TTL
                        use_dns_cache=True
                    )
                    timeout = aiohttp.ClientTimeout(total=10, connect=5)
                    self.async_session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout,
                        headers={
                            'User-Agent': 'AnimeSorter/2.0.0',
                            'Accept': 'image/*'
                        }
                    )
        return self.async_session
    
    async def close_async_session(self):
        """비동기 세션 종료"""
        if self.async_session and not self.async_session.closed:
            await self.async_session.close()
    
    def search_anime(self, query: str, year: Optional[int] = None, 
                     include_adult: bool = False, first_air_date_year: Optional[int] = None) -> List[TMDBAnimeInfo]:
        """애니메이션 제목으로 검색 (최적화됨)"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()
            
            # 캐시 확인 (메모리 캐시 우선)
            cache_key = f"search_{query}_{year}_{include_adult}_{first_air_date_year}"
            cached_result = self._get_cache_optimized(cache_key)
            if cached_result:
                return [TMDBAnimeInfo(**item) for item in cached_result]
            
            # TMDB 검색 실행
            search = tmdb.Search()
            search_params = {
                'query': query,
                'language': self.language,
                'include_adult': include_adult
            }
            
            # 연도 필터 추가
            if year:
                search_params['first_air_date_year'] = year
            elif first_air_date_year:
                search_params['first_air_date_year'] = first_air_date_year
            else:
                # 연도가 지정되지 않은 경우 최근 10년 범위로 검색
                current_year = datetime.now().year
                search_params['with_first_air_date_gte'] = f"{current_year-10}-01-01"
                search_params['with_first_air_date_lte'] = f"{current_year}-12-31"
            
            response = search.tv(**search_params)
            
            # 애니메이션 장르 필터링 (장르 ID: 16=애니메이션, 10759=액션&어드벤처)
            anime_results = []
            for result in response.get('results', []):
                genre_ids = result.get('genre_ids', [])
                if any(genre_id in genre_ids for genre_id in [16, 10759]):
                    anime_results.append(result)
            
            # 상위 10개 결과만 반환
            limited_results = anime_results[:10]
            
            # TMDBAnimeInfo 객체로 변환
            anime_info_list = []
            for result in limited_results:
                anime_info = self._convert_to_anime_info(result)
                if anime_info:
                    anime_info_list.append(anime_info)
            
            # 결과 캐싱
            if self.cache_enabled:
                self._set_cache_optimized(cache_key, [asdict(info) for info in anime_info_list])
            
            return anime_info_list
            
        except Exception as e:
            logging.error(f"TMDB 검색 오류: {e}")
            return []
    
    def get_anime_details(self, tv_id: int, language: Optional[str] = None) -> Optional[TMDBAnimeInfo]:
        """애니메이션 상세 정보 조회 (최적화됨)"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()
            
            # 캐시 확인
            cache_key = f"details_{tv_id}_{language or self.language}"
            cached_result = self._get_cache_optimized(cache_key)
            if cached_result:
                return TMDBAnimeInfo(**cached_result)
            
            # TMDB 상세 정보 조회
            tv = tmdb.TV(tv_id)
            response = tv.info(language=language or self.language)
            
            # 추가 정보 조회 (병렬 처리 가능하지만 TMDB API 제한으로 순차 처리)
            try:
                credits = tv.credits()
                images = tv.images()
                external_ids = tv.external_ids()
                videos = tv.videos()
                keywords = tv.keywords()
                recommendations = tv.recommendations()
                similar = tv.similar()
                translations = tv.translations()
                content_ratings = tv.content_ratings()
                watch_providers = tv.watch_providers()
                
                # 응답에 추가 정보 병합
                response.update({
                    'credits': credits,
                    'images': images,
                    'external_ids': external_ids,
                    'videos': videos,
                    'keywords': keywords,
                    'recommendations': recommendations,
                    'similar': similar,
                    'translations': translations,
                    'content_ratings': content_ratings,
                    'watch_providers': watch_providers
                })
            except Exception as e:
                logging.warning(f"추가 정보 조회 실패: {e}")
            
            # TMDBAnimeInfo 객체로 변환
            anime_info = self._convert_to_anime_info(response)
            
            # 결과 캐싱
            if self.cache_enabled and anime_info:
                self._set_cache_optimized(cache_key, asdict(anime_info))
            
            return anime_info
            
        except Exception as e:
            logging.error(f"TMDB 상세 정보 조회 오류: {e}")
            return None
    
    @lru_cache(maxsize=100)
    def search_anime_optimized(self, query: str, language: str = 'ko-KR') -> List[TMDBAnimeInfo]:
        """최적화된 애니메이션 검색 (캐시됨)"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()
            
            # 캐시 확인
            cache_key = f"optimized_search_{query}_{language}"
            cached_result = self._get_cache_optimized(cache_key)
            if cached_result:
                return [TMDBAnimeInfo(**item) for item in cached_result]
            
            search = tmdb.Search()
            response = search.tv(
                query=query,
                language=language,
                first_air_date_year=2020,  # 최신 작품 우선
                sort_by='popularity.desc'   # 인기도 순 정렬
            )
            
            # 결과 필터링 (애니메이션 장르 우선)
            anime_results = []
            for result in response.get('results', []):
                genre_ids = result.get('genre_ids', [])
                if any(genre_id in genre_ids for genre_id in [16, 10759]):
                    anime_results.append(result)
            
            # 상위 10개 결과만 반환
            limited_results = anime_results[:10]
            
            # TMDBAnimeInfo 객체로 변환
            anime_info_list = []
            for result in limited_results:
                anime_info = self._convert_to_anime_info(result)
                if anime_info:
                    anime_info_list.append(anime_info)
            
            # 결과 캐싱
            if self.cache_enabled:
                self._set_cache_optimized(cache_key, [asdict(info) for info in anime_info_list])
            
            return anime_info_list
            
        except Exception as e:
            logging.error(f"TMDB 최적화 검색 오류: {e}")
            return []
    
    def get_anime_season(self, tv_id: int, season_number: int, language: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """시즌 정보 조회 (최적화됨)"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()
            
            # 캐시 확인
            cache_key = f"season_{tv_id}_{season_number}_{language or self.language}"
            cached_result = self._get_cache_optimized(cache_key)
            if cached_result:
                return cached_result
            
            # TMDB 시즌 정보 조회
            season = tmdb.TV_Seasons(tv_id, season_number)
            response = season.info(language=language or self.language)
            
            # 결과 캐싱
            if self.cache_enabled:
                self._set_cache_optimized(cache_key, response)
            
            return response
            
        except Exception as e:
            logging.error(f"TMDB 시즌 정보 조회 오류: {e}")
            return None
    
    def get_anime_episode(self, tv_id: int, season_number: int, episode_number: int, 
                          language: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """에피소드 정보 조회 (최적화됨)"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()
            
            # 캐시 확인
            cache_key = f"episode_{tv_id}_{season_number}_{episode_number}_{language or self.language}"
            cached_result = self._get_cache_optimized(cache_key)
            if cached_result:
                return cached_result
            
            # TMDB 에피소드 정보 조회
            episode = tmdb.TV_Episodes(tv_id, season_number, episode_number)
            response = episode.info(language=language or self.language)
            
            # 결과 캐싱
            if self.cache_enabled:
                self._set_cache_optimized(cache_key, response)
            
            return response
            
        except Exception as e:
            logging.error(f"TMDB 에피소드 정보 조회 오류: {e}")
            return None
    
    def _convert_to_anime_info(self, tmdb_data: Dict[str, Any]) -> Optional[TMDBAnimeInfo]:
        """TMDB 응답을 TMDBAnimeInfo 객체로 변환"""
        try:
            # 필수 필드 확인
            if 'id' not in tmdb_data or 'name' not in tmdb_data:
                return None
            
            # 기본 필드 설정
            anime_info = TMDBAnimeInfo(
                id=tmdb_data.get('id'),
                name=tmdb_data.get('name', ''),
                original_name=tmdb_data.get('original_name', ''),
                overview=tmdb_data.get('overview', ''),
                first_air_date=tmdb_data.get('first_air_date', ''),
                last_air_date=tmdb_data.get('last_air_date', ''),
                number_of_seasons=tmdb_data.get('number_of_seasons', 0),
                number_of_episodes=tmdb_data.get('number_of_episodes', 0),
                status=tmdb_data.get('status', ''),
                type=tmdb_data.get('type', ''),
                popularity=tmdb_data.get('popularity', 0.0),
                vote_average=tmdb_data.get('vote_average', 0.0),
                vote_count=tmdb_data.get('vote_count', 0),
                genres=tmdb_data.get('genres', []),
                poster_path=tmdb_data.get('poster_path', ''),
                backdrop_path=tmdb_data.get('backdrop_path', ''),
                episode_run_time=tmdb_data.get('episode_run_time', []),
                networks=tmdb_data.get('networks', []),
                production_companies=tmdb_data.get('production_companies', []),
                languages=tmdb_data.get('languages', []),
                origin_country=tmdb_data.get('origin_country', []),
                in_production=tmdb_data.get('in_production', False),
                last_episode_to_air=tmdb_data.get('last_episode_to_air'),
                next_episode_to_air=tmdb_data.get('next_episode_to_air'),
                seasons=tmdb_data.get('seasons', []),
                external_ids=tmdb_data.get('external_ids', {}),
                images=tmdb_data.get('images', {}),
                credits=tmdb_data.get('credits', {}),
                videos=tmdb_data.get('videos', {}),
                keywords=tmdb_data.get('keywords', {}),
                recommendations=tmdb_data.get('recommendations', {}),
                similar=tmdb_data.get('similar', {}),
                translations=tmdb_data.get('translations', {}),
                content_ratings=tmdb_data.get('content_ratings', {}),
                watch_providers=tmdb_data.get('watch_providers', {})
            )
            
            return anime_info
            
        except Exception as e:
            logging.error(f"TMDB 데이터 변환 오류: {e}")
            return None
    
    def _get_cache_optimized(self, key: str) -> Optional[Any]:
        """최적화된 캐시에서 데이터 가져오기"""
        if not self.cache_enabled:
            return None
        
        # 메모리 캐시 확인 (빠른 접근)
        with self.cache_lock:
            if key in self.memory_cache:
                return self.memory_cache[key]
        
        # 디스크 캐시 확인
        try:
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                # 캐시 만료 확인
                if time.time() - cache_file.stat().st_mtime < self.cache_expiry:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # 메모리 캐시에 추가
                        with self.cache_lock:
                            if len(self.memory_cache) >= self.memory_cache_size:
                                # LRU 방식으로 가장 오래된 항목 제거
                                oldest_key = next(iter(self.memory_cache))
                                del self.memory_cache[oldest_key]
                            self.memory_cache[key] = data
                        
                        return data
                else:
                    # 만료된 캐시 삭제
                    cache_file.unlink()
        except Exception as e:
            logging.warning(f"캐시 읽기 오류: {e}")
        
        return None
    
    def _set_cache_optimized(self, key: str, data: Any) -> None:
        """데이터를 최적화된 캐시에 저장"""
        if not self.cache_enabled:
            return
        
        try:
            # 메모리 캐시에 저장
            with self.cache_lock:
                if len(self.memory_cache) >= self.memory_cache_size:
                    # LRU 방식으로 가장 오래된 항목 제거
                    oldest_key = next(iter(self.memory_cache))
                    del self.memory_cache[oldest_key]
                self.memory_cache[key] = data
            
            # 디스크 캐시에 저장
            cache_file = self.cache_dir / f"{key}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning(f"캐시 저장 오류: {e}")
    
    def clear_cache(self) -> None:
        """캐시 초기화 (최적화됨)"""
        try:
            # 메모리 캐시 초기화
            with self.cache_lock:
                self.memory_cache.clear()
            
            # 디스크 캐시 초기화
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            
            # LRU 캐시 초기화
            self.search_anime_optimized.cache_clear()
            
            logging.info("캐시가 초기화되었습니다.")
        except Exception as e:
            logging.error(f"캐시 초기화 오류: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """캐시 정보 반환 (개선됨)"""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            with self.cache_lock:
                memory_cache_size = len(self.memory_cache)
            
            return {
                'cache_enabled': self.cache_enabled,
                'cache_dir': str(self.cache_dir),
                'file_count': len(cache_files),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'expiry_seconds': self.cache_expiry,
                'memory_cache_size': memory_cache_size,
                'memory_cache_max_size': self.memory_cache_size,
                'lru_cache_info': self.search_anime_optimized.cache_info()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def set_language(self, language: str) -> None:
        """언어 설정 변경"""
        self.language = language
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """캐시 활성화/비활성화"""
        self.cache_enabled = enabled
    
    def set_cache_expiry(self, expiry_seconds: int) -> None:
        """캐시 만료 시간 설정"""
        self.cache_expiry = expiry_seconds
    
    def set_memory_cache_size(self, size: int) -> None:
        """메모리 캐시 크기 설정"""
        with self.cache_lock:
            if size < len(self.memory_cache):
                # 크기를 줄이는 경우, 가장 오래된 항목들 제거
                while len(self.memory_cache) > size:
                    oldest_key = next(iter(self.memory_cache))
                    del self.memory_cache[oldest_key]
            self.memory_cache_size = size
    
    async def download_poster_async(self, poster_path: str, size: str = 'w185') -> Optional[str]:
        """TMDB 포스터 이미지 비동기 다운로드 (최적화됨)"""
        if not poster_path:
            return None
            
        try:
            # TMDB 이미지 URL 구성
            base_url = "https://image.tmdb.org/t/p"
            image_url = f"{base_url}/{size}{poster_path}"
            
            # 캐시 파일명 생성
            filename = poster_path.split('/')[-1]
            cache_filename = f"{size}_{filename}"
            cache_path = self.poster_cache_dir / cache_filename
            
            # 이미 캐시된 경우 반환
            if cache_path.exists():
                return str(cache_path)
            
            # 비동기 세션 가져오기
            session = await self._get_async_session()
            
            # 이미지 다운로드
            async with session.get(image_url) as response:
                response.raise_for_status()
                content = await response.read()
            
            # 캐시에 저장
            with open(cache_path, 'wb') as f:
                f.write(content)
            
            logging.info(f"포스터 다운로드 완료: {cache_filename}")
            return str(cache_path)
            
        except Exception as e:
            logging.error(f"포스터 다운로드 실패: {e}")
            return None
    
    def download_poster(self, poster_path: str, size: str = 'w185') -> Optional[str]:
        """TMDB 포스터 이미지 다운로드 (동기 버전)"""
        if not poster_path:
            return None
            
        try:
            # TMDB 이미지 URL 구성
            base_url = "https://image.tmdb.org/t/p"
            image_url = f"{base_url}/{size}{poster_path}"
            
            # 캐시 파일명 생성
            filename = poster_path.split('/')[-1]
            cache_filename = f"{size}_{filename}"
            cache_path = self.poster_cache_dir / cache_filename
            
            # 이미 캐시된 경우 반환
            if cache_path.exists():
                return str(cache_path)
            
            # 이미지 다운로드
            response = self.session.get(image_url, timeout=10)
            response.raise_for_status()
            
            # 캐시에 저장
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            
            logging.info(f"포스터 다운로드 완료: {cache_filename}")
            return str(cache_path)
            
        except Exception as e:
            logging.error(f"포스터 다운로드 실패: {e}")
            return None
    
    def get_poster_path(self, poster_path: str, size: str = 'w185') -> Optional[str]:
        """포스터 이미지 경로 반환 (다운로드 포함)"""
        if not poster_path:
            return None
        
        # 이미지 다운로드 시도
        local_path = self.download_poster(poster_path, size)
        return local_path
    
    # 기존 메서드들 (하위 호환성을 위해 유지)
    def _get_cache(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 가져오기 (기존 메서드)"""
        return self._get_cache_optimized(key)
    
    def _set_cache(self, key: str, data: Any) -> None:
        """데이터를 캐시에 저장 (기존 메서드)"""
        self._set_cache_optimized(key, data)
