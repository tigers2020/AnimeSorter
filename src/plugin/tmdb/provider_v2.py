"""
TMDB Provider v2 - 새로운 플러그인 인터페이스 기반

기존 TMDB provider를 새로운 플러그인 시스템에 맞게 마이그레이션한 버전입니다.
"""

import asyncio
import time
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import tmdbsimple as tmdb
from rapidfuzz import fuzz, process
from slugify import slugify
import yaml
import os
import re

from ..base import (
    MetadataProvider, ProviderConfig, SearchResult, 
    PluginError, PluginConfigError, PluginInitializationError, PluginConnectionError
)
from src.utils.file_cleaner import FileCleaner
from difflib import SequenceMatcher


class TMDBProviderV2(MetadataProvider):
    """
    TMDB 메타데이터 제공자 v2 (새로운 플러그인 인터페이스 기반)
    
    tmdbsimple 라이브러리를 사용하여 TMDB API와 통신하며,
    RapidFuzz를 사용한 재순위화와 멀티페이지 검색을 지원합니다.
    """
    
    def __init__(self, config: ProviderConfig):
        """
        TMDB Provider v2 초기화
        
        Args:
            config: 제공자 설정
        """
        super().__init__(config)
        self.logger = logging.getLogger("animesorter.tmdb_provider_v2")
        
        # tmdbsimple 설정
        if not config.api_key:
            raise PluginConfigError("TMDB API key is required")
            
        tmdb.API_KEY = config.api_key
        tmdb.REQUESTS_TIMEOUT = config.timeout
        
        # 제목 오버라이드 로드
        self.title_overrides = self._load_title_overrides()
        
        # 검색 결과 캐시 (메모리)
        self._search_cache = {}
        
        self.logger.info("TMDB Provider v2 초기화 완료")
    
    async def initialize(self) -> None:
        """플러그인 초기화"""
        try:
            # API 키 유효성 검증
            if not await self.test_connection():
                raise PluginInitializationError("TMDB API connection test failed")
                
            self._initialized = True
            self.logger.info("TMDB Provider v2 초기화 성공")
            
        except Exception as e:
            self.logger.error(f"TMDB Provider v2 초기화 실패: {e}")
            raise PluginInitializationError(f"Initialization failed: {e}")
    
    async def close(self) -> None:
        """플러그인 정리"""
        self._search_cache.clear()
        self._initialized = False
        self.logger.info("TMDB Provider v2 정리 완료")
    
    def is_available(self) -> bool:
        """플러그인 사용 가능 여부 확인"""
        return self._initialized and bool(self.config.api_key)
    
    async def test_connection(self) -> bool:
        """API 연결 테스트"""
        try:
            # 간단한 검색으로 연결 테스트
            search = tmdb.Search()
            search.tv(query="test", page=1)
            return True
        except Exception as e:
            self.logger.error(f"TMDB connection test failed: {e}")
            return False
    
    def _load_title_overrides(self) -> Dict[str, int]:
        """제목 오버라이드 로드"""
        overrides = {}
        override_file = Path("config/title_overrides.yaml")
        
        if override_file.exists():
            try:
                with open(override_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'overrides' in data:
                        overrides = data['overrides']
                        self.logger.info(f"Loaded {len(overrides)} title overrides")
            except Exception as e:
                self.logger.error(f"Failed to load title overrides: {e}")
        
        return overrides
    
    async def search(self, title: str, year: Optional[int] = None) -> Optional[SearchResult]:
        """
        제목과 연도로 메타데이터 검색
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            
        Returns:
            SearchResult or None: 검색 결과 또는 None
        """
        if not self.is_available():
            raise PluginError("TMDB Provider is not available")
        
        # 오버라이드 테이블 체크 (최우선)
        if title in self.title_overrides:
            override_id = self.title_overrides[title]
            self.logger.info(f"Title override found: '{title}' → ID {override_id}")
            
            # 오버라이드된 ID로 직접 상세 정보 조회
            try:
                # TV 시리즈로 먼저 시도
                result = await self.get_details(override_id)
                if result:
                    return result
                    
            except Exception as e:
                self.logger.error(f"Failed to get override details for {title}: {e}")
        
        # 점진적 검색 시도
        progressive_titles = self._generate_progressive_titles(title)
        
        for attempt, search_title in enumerate(progressive_titles):
            try:
                if attempt > 0:
                    self.logger.info(f"Fallback attempt {attempt}: '{search_title}'")
                
                # 1단계: 멀티페이지 검색으로 후보들 찾기
                all_candidates = []
                for page in range(1, 4):  # 1-3페이지
                    try:
                        search = tmdb.Search()
                        search.tv(query=search_title, page=page)
                        tv_candidates = search.results
                        
                        # TV 시리즈 결과에 media_type 추가
                        for candidate in tv_candidates:
                            candidate['media_type'] = 'tv'
                        
                        all_candidates.extend(tv_candidates)
                        
                        # 첫 페이지에서 충분한 결과를 찾았으면 중단
                        if page == 1 and len(tv_candidates) >= 10:
                            break
                            
                    except Exception as e:
                        self.logger.warning(f"Page {page} search failed: {e}")
                        break
                
                if all_candidates:
                    # 2단계: RapidFuzz 기반 재순위화
                    reranked_candidates = self._rerank_with_rapidfuzz(all_candidates, search_title, year)
                    
                    # 3단계: 상위 후보들을 실제 detail API로 확인
                    for candidate in reranked_candidates[:3]:  # 상위 3개 후보만 확인
                        candidate_id = candidate.get("id")
                        candidate_media_type = candidate.get("media_type")
                        
                        if not candidate_id or candidate_media_type not in ("tv", "movie"):
                            continue
                            
                        try:
                            # 실제 detail API 호출로 정확한 분류 확인
                            result = await self.get_details(candidate_id)
                            
                            if result:
                                if attempt > 0:
                                    self.logger.info(f"Fallback success with '{search_title}' for original '{title}'")
                                
                                self.logger.info(f"Found: {result.title} (media_type: {result.media_type}, year: {year})")
                                return result
                                
                        except Exception as e:
                            self.logger.warning(f"Detail API failed for {candidate_id} ({candidate_media_type}): {e}")
                            continue
                
            except Exception as e:
                self.logger.error(f"Unexpected error during search attempt {attempt + 1}: {e}")
                continue
        
        # 모든 시도 실패
        self.logger.warning(f"No results for: {title} (year: {year}) - tried {len(progressive_titles)} variations")
        return None
    
    async def get_details(self, media_id: Any) -> Optional[SearchResult]:
        """
        ID로 상세 정보 조회
        
        Args:
            media_id: 미디어 ID
            
        Returns:
            SearchResult or None: 상세 정보 또는 None
        """
        if not self.is_available():
            raise PluginError("TMDB Provider is not available")
        
        try:
            # TV 시리즈로 먼저 시도
            tv = tmdb.TV(media_id)
            tv.info()
            
            # TV 시리즈 정보를 SearchResult로 변환
            result = SearchResult(
                id=media_id,
                title=tv.name,
                original_title=tv.original_name,
                media_type="tv",
                year=int(tv.first_air_date.split('-')[0]) if tv.first_air_date else None,
                overview=tv.overview or "",
                poster_path=tv.poster_path,
                backdrop_path=tv.backdrop_path,
                genres=[genre['name'] for genre in tv.genres] if tv.genres else [],
                rating=tv.vote_average,
                provider="tmdb"
            )
            
            return result
            
        except Exception as e:
            # TV 시리즈 실패 시 영화로 시도
            try:
                movie = tmdb.Movies(media_id)
                movie.info()
                
                result = SearchResult(
                    id=media_id,
                    title=movie.title,
                    original_title=movie.original_title,
                    media_type="movie",
                    year=int(movie.release_date.split('-')[0]) if movie.release_date else None,
                    overview=movie.overview or "",
                    poster_path=movie.poster_path,
                    backdrop_path=movie.backdrop_path,
                    genres=[genre['name'] for genre in movie.genres] if movie.genres else [],
                    rating=movie.vote_average,
                    provider="tmdb"
                )
                
                return result
                
            except Exception as movie_error:
                self.logger.error(f"Failed to get details for ID {media_id}: {e}, movie fallback: {movie_error}")
                return None
    
    def _generate_progressive_titles(self, title: str) -> List[str]:
        """점진적 제목 변형 생성"""
        titles = [title]
        
        # 기본 정제
        clean_title = FileCleaner.clean_title(title)
        if clean_title != title:
            titles.append(clean_title)
        
        # 시리즈 정보 제거
        series_patterns = [
            r'\s*\([^)]*시리즈[^)]*\)',
            r'\s*\[[^\]]*시리즈[^\]]*\]',
            r'\s*시리즈\s*$',
            r'\s*Season\s*\d+',
            r'\s*시즌\s*\d+'
        ]
        
        for pattern in series_patterns:
            cleaned = re.sub(pattern, '', title, flags=re.IGNORECASE)
            if cleaned != title and cleaned.strip():
                titles.append(cleaned.strip())
        
        # 중복 제거 및 순서 유지
        seen = set()
        unique_titles = []
        for t in titles:
            if t not in seen:
                seen.add(t)
                unique_titles.append(t)
        
        return unique_titles
    
    def _rerank_with_rapidfuzz(self, candidates: List[dict], query: str, year: Optional[int] = None) -> List[dict]:
        """RapidFuzz를 사용한 재순위화"""
        def calculate_rapidfuzz_score(item):
            base_score = 0
            
            # 제목 추출
            title_field = "name" if item.get("media_type") == "tv" else "title"
            item_title = item.get(title_field, "")
            
            # 제목 유사도 (0-100)
            title_similarity = fuzz.ratio(query.lower(), item_title.lower())
            base_score += title_similarity
            
            # 부분 문자열 매칭 보너스
            if query.lower() in item_title.lower():
                base_score += 20
            
            # 연도 매칭 보너스
            if year:
                item_year = None
                if item.get("media_type") == "tv":
                    air_date = item.get("first_air_date")
                    if air_date:
                        try:
                            item_year = int(air_date.split('-')[0])
                        except (ValueError, IndexError):
                            pass
                else:
                    release_date = item.get("release_date")
                    if release_date:
                        try:
                            item_year = int(release_date.split('-')[0])
                        except (ValueError, IndexError):
                            pass
                
                if item_year == year:
                    base_score += 30
                elif abs(item_year - year) <= 1:
                    base_score += 15
            
            # 인기도 보너스 (0-10)
            popularity = min(10, item.get("popularity", 0) / 10)
            base_score += popularity
            
            return base_score
        
        # 점수로 정렬
        scored_candidates = [(item, calculate_rapidfuzz_score(item)) for item in candidates]
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        return [item for item, score in scored_candidates] 