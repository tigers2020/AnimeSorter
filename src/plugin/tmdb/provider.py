"""
TMDB Provider - tmdbsimple 라이브러리 기반
"""

import asyncio
import time
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import tmdbsimple as tmdb
from rapidfuzz import fuzz, process
from slugify import slugify
from ...utils.safe_slugify import safe_slugify

import yaml
import os
import re
from src.utils.file_cleaner import FileCleaner
from difflib import SequenceMatcher

class TMDBProvider:
    """
    TMDB 메타데이터 제공자 (tmdbsimple 기반)
    
    tmdbsimple 라이브러리를 사용하여 TMDB API와 통신하며,
    RapidFuzz를 사용한 재순위화와 멀티페이지 검색을 지원합니다.
    """
    
    def __init__(self, api_key: str, cache_db=None, language: str = "ko-KR"):
        """
        TMDB Provider 초기화
        
        Args:
            api_key: TMDB API 키
            cache_db: 캐시 데이터베이스 (옵션)
            language: 응답 언어 (기본값: ko-KR)
        """
        self.logger = logging.getLogger("animesorter.tmdb_provider")
        
        # tmdbsimple 설정
        tmdb.API_KEY = api_key
        tmdb.REQUESTS_TIMEOUT = 10  # 10초 타임아웃
        
        # 언어 설정 (tmdbsimple은 전역 설정을 사용)
        self.language = language
        
        # 캐시 설정
        self.cache_db = cache_db
        
        # 제목 오버라이드 로드
        self.title_overrides = self._load_title_overrides()
        
        # 검색 결과 캐시 (메모리)
        self._search_cache = {}
        
        self.logger.info("TMDB Provider (tmdbsimple) 초기화 완료")
    
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
                        self.logger.info(f"[TMDB] Loaded {len(overrides)} title overrides")
            except Exception as e:
                self.logger.error(f"[TMDB] Failed to load title overrides: {e}")
        
        return overrides
    
    async def search(self, title: str, year: Optional[int] = None, season: Optional[int] = None, is_special: bool = False) -> Optional[dict]:
        """
        제목, 연도, 시즌으로 메타데이터 검색 (tmdbsimple 기반)
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            season: 시즌 번호 (옵션)
            
        Returns:
            dict or None: 검색 결과 또는 None
        """
        # 오버라이드 테이블 체크 (최우선)
        if title in self.title_overrides:
            override_id = self.title_overrides[title]
            self.logger.info(f"[TMDB] Title override found: '{title}' → ID {override_id}")
            
            # 오버라이드된 ID로 직접 상세 정보 조회
            try:
                # TV 시리즈로 먼저 시도
                result = await self.get_details(override_id, "tv")
                if result:
                    return result
                
                # 실패하면 영화로 시도
                result = await self.get_details(override_id, "movie")
                if result:
                    return result
                    
            except Exception as e:
                self.logger.error(f"[TMDB] Failed to get override details for {title}: {e}")
        
        # 캐시 확인 (시즌 정보 포함)
        if self.cache_db:
            cache_key = self._generate_cache_key(title, year, season)
            cached_result = await self.cache_db.get_cache(cache_key)
            if cached_result:
                self.logger.info(f"[TMDB] Cache hit for: {title} (year: {year}, season: {season})")
                return cached_result
        
        # 점진적 검색 시도
        progressive_titles = self._generate_progressive_titles(title)
        
        for attempt, search_title in enumerate(progressive_titles):
            try:
                if attempt > 0:
                    self.logger.info(f"[TMDB] Fallback attempt {attempt}: '{search_title}'")
                
                # 1단계: 다중 언어 폴백 검색으로 후보들 찾기
                all_candidates = []
                languages = ['ko-KR', 'en-US', 'ja-JP']  # 한국어 → 영어 → 일본어 순서
                
                for lang in languages:
                    try:
                        # tmdbsimple Search 객체 사용 (언어별 검색)
                        search = tmdb.Search()
                        
                        # TV 시리즈 검색 (언어별)
                        search.tv(query=search_title, page=1, language=lang)
                        tv_candidates = search.results
                        
                        # TV 시리즈 결과에 media_type과 검색 언어 추가
                        for candidate in tv_candidates:
                            candidate['media_type'] = 'tv'
                            candidate['search_language'] = lang
                        
                        all_candidates.extend(tv_candidates)
                        
                        # 한국어에서 충분한 결과를 찾았으면 다른 언어는 시도하지 않음
                        if lang == 'ko-KR' and len(tv_candidates) >= 5:
                            self.logger.info(f"[TMDB] Found {len(tv_candidates)} results with {lang}, skipping other languages")
                            break
                            
                    except Exception as e:
                        self.logger.warning(f"[TMDB] {lang} search failed: {e}")
                        continue
                
                # 중복 제거 (ID 기준)
                seen_ids = set()
                unique_candidates = []
                for candidate in all_candidates:
                    if candidate.get('id') not in seen_ids:
                        seen_ids.add(candidate.get('id'))
                        unique_candidates.append(candidate)
                
                all_candidates = unique_candidates
                self.logger.info(f"[TMDB] Found {len(all_candidates)} unique candidates across {len(languages)} languages")
                
                if all_candidates:
                    # 2단계: RapidFuzz 기반 재순위화
                    reranked_candidates = self._rerank_with_rapidfuzz(all_candidates, search_title, year, season)
                    
                    # 3단계: 상위 후보들을 실제 detail API로 확인
                    for candidate in reranked_candidates[:3]:  # 상위 3개 후보만 확인
                        candidate_id = candidate.get("id")
                        candidate_media_type = candidate.get("media_type")
                        
                        if not candidate_id or candidate_media_type not in ("tv", "movie"):
                            continue
                            
                        try:
                            # 실제 detail API 호출로 정확한 분류 확인
                            result = await self.get_details(candidate_id, candidate_media_type)
                            
                            if result:
                                # 시즌 정보가 있는 경우에만 시즌별 정보 추가 (성능 최적화)
                                if season and candidate_media_type == "tv":
                                    # 특집인 경우 Season 0으로 처리
                                    actual_season = 0 if is_special else season
                                    result = await self._add_season_info(result, actual_season)
                                
                                # 원본 제목으로 캐시에 저장 (JSON 직렬화 가능한 형태로 변환)
                                if self.cache_db:
                                    try:
                                        cache_key = self._generate_cache_key(title, year, season)
                                        # JSON 직렬화 가능한 형태로 변환
                                        cache_result = self._prepare_for_cache(result)
                                        await self.cache_db.set_cache(cache_key, cache_result, year)
                                    except Exception as e:
                                        self.logger.warning(f"[TMDB] Cache save error: {e}")
                                
                                if attempt > 0:
                                    self.logger.info(f"[TMDB] Fallback success with '{search_title}' for original '{title}'")
                                
                                self.logger.info(f"[TMDB] Found: {result.get('name', result.get('title', 'Unknown'))} (media_type: {result.get('media_type')}, year: {year}, season: {season})")
                                return result
                                
                        except Exception as e:
                            self.logger.warning(f"[TMDB] Detail API failed for {candidate_id} ({candidate_media_type}): {e}")
                            continue
                
            except Exception as e:
                self.logger.error(f"[TMDB] Unexpected error during search attempt {attempt + 1}: {e}")
                continue
        
        # 모든 시도 실패
        self.logger.warning(f"[TMDB] No results for: {title} (year: {year}, season: {season}) - tried {len(progressive_titles)} variations")
        return None
    
    async def get_details(self, item_id: int, media_type: str) -> Optional[dict]:
        """
        아이템 상세 정보 조회 (tmdbsimple 기반)
        
        Args:
            item_id: TMDB 아이템 ID
            media_type: 미디어 타입 ('tv' 또는 'movie')
            
        Returns:
            dict or None: 상세 정보 또는 None
        """
        try:
            if media_type == "tv":
                # tmdbsimple TV 객체 사용
                tv = tmdb.TV(item_id)
                tv.info(append_to_response="seasons,images")
                
                # 결과를 표준 형식으로 변환
                result = {
                    'id': tv.id,
                    'name': tv.name,
                    'original_name': tv.original_name,
                    'overview': tv.overview,
                    'first_air_date': tv.first_air_date,
                    'last_air_date': tv.last_air_date,
                    'number_of_seasons': tv.number_of_seasons,
                    'number_of_episodes': tv.number_of_episodes,
                    'status': tv.status,
                    'type': tv.type,
                    'popularity': tv.popularity,
                    'vote_average': tv.vote_average,
                    'vote_count': tv.vote_count,
                    'media_type': 'tv',
                    'seasons': tv.seasons if hasattr(tv, 'seasons') else [],
                    'images': tv.images if hasattr(tv, 'images') else {}
                }
                
            elif media_type == "movie":
                # tmdbsimple Movie 객체 사용
                movie = tmdb.Movies(item_id)
                movie.info(append_to_response="images,credits")
                
                # 결과를 표준 형식으로 변환
                result = {
                    'id': movie.id,
                    'title': movie.title,
                    'original_title': movie.original_title,
                    'overview': movie.overview,
                    'release_date': movie.release_date,
                    'runtime': movie.runtime,
                    'budget': movie.budget,
                    'revenue': movie.revenue,
                    'status': movie.status,
                    'popularity': movie.popularity,
                    'vote_average': movie.vote_average,
                    'vote_count': movie.vote_count,
                    'media_type': 'movie',
                    'images': movie.images if hasattr(movie, 'images') else {},
                    'credits': movie.credits if hasattr(movie, 'credits') else {}
                }
            
            else:
                self.logger.error(f"[TMDB] Unsupported media_type: {media_type}")
                return None
            
            return result
            
        except Exception as e:
            self.logger.error(f"[TMDB] Failed to get details for {item_id} ({media_type}): {e}")
            return None
    
    async def _add_season_info(self, result: dict, season: int) -> dict:
        """
        시즌별 정보 추가 (tmdbsimple 기반) - 404 오류 처리 개선
        
        Args:
            result: 기본 결과
            season: 시즌 번호
            
        Returns:
            dict: 시즌 정보가 추가된 결과
        """
        try:
            tv_id = result.get('id')
            if not tv_id:
                return result
            
            # 특집(SP) 처리: Season 0으로 강제 변환
            if season == 0 or (hasattr(self, '_is_special_episode') and self._is_special_episode):
                season = 0
                self.logger.info(f"[TMDB] Special episode detected, using Season 0 for {result.get('name', 'Unknown')}")
            
            try:
                # tmdbsimple TV Seasons 객체 사용
                tv_seasons = tmdb.TV_Seasons(tv_id, season)
                tv_seasons.info(append_to_response="images")
                
                # 시즌 정보 추가 (tmdbsimple 구조에 맞게 수정)
                season_info = {
                    'season_number': getattr(tv_seasons, 'season_number', season),
                    'name': getattr(tv_seasons, 'name', f'Season {season}'),
                    'overview': getattr(tv_seasons, 'overview', ''),
                    'air_date': getattr(tv_seasons, 'air_date', ''),
                    'episodes': getattr(tv_seasons, 'episodes', [])
                }
                
                # episode_count는 episodes 리스트의 길이로 계산
                season_info['episode_count'] = len(season_info['episodes'])
                
                # images는 별도로 처리
                if hasattr(tv_seasons, 'images'):
                    season_info['images'] = tv_seasons.images
                else:
                    season_info['images'] = {}
                
                result['season_info'] = season_info
                
                self.logger.info(f"[TMDB] Added season {season} info for {result.get('name', 'Unknown')}")
                
            except Exception as season_error:
                # 시즌 404 오류 처리
                if "404" in str(season_error) or "not found" in str(season_error).lower():
                    self.logger.warning(f"[TMDB] Season {season} not found for {result.get('name', 'Unknown')} (ID: {tv_id})")
                    
                    # 시즌 2 이상인 경우 시리즈 레벨 메타데이터로 폴백
                    if season >= 2:
                        self.logger.info(f"[TMDB] Using series-level metadata for Season {season} (not yet available on TMDB)")
                        # 시리즈 정보에 시즌 정보 추가 (기본값)
                        result['season_info'] = {
                            'season_number': season,
                            'name': f'Season {season}',
                            'overview': f'Season {season} information not yet available on TMDB',
                            'air_date': '',
                            'episodes': [],
                            'episode_count': 0,
                            'images': {},
                            'is_fallback': True
                        }
                    else:
                        self.logger.warning(f"[TMDB] Season {season} not available, skipping season info")
                else:
                    # 다른 오류는 그대로 로깅
                    self.logger.warning(f"[TMDB] Failed to add season {season} info: {season_error}")
            
        except Exception as e:
            self.logger.warning(f"[TMDB] Failed to add season {season} info: {e}")
        
        return result
    
    def _generate_progressive_titles(self, title: str) -> List[str]:
        """
        점진적 검색을 위한 제목 변형 생성
        
        Args:
            title: 원본 제목
            
        Returns:
            List[str]: 검색할 제목 변형들
        """
        titles = [title]
        
        # 연도 제거
        year_pattern = r'\s*\(\d{4}\)\s*'
        clean_title = re.sub(year_pattern, '', title).strip()
        if clean_title != title:
            titles.append(clean_title)
        
        # 특수문자 제거
        clean_title = re.sub(r'[^\w\s가-힣]', ' ', clean_title).strip()
        if clean_title != title and clean_title not in titles:
            titles.append(clean_title)
        
        # 한국어 제목 처리
        if any(ord(c) > 127 for c in title):
            # 한국어가 포함된 경우 영어 제목도 시도
            # (실제로는 더 정교한 번역이 필요하지만 여기서는 간단히 처리)
            pass
        
        return titles
    
    def _generate_cache_key(self, title: str, year: Optional[int] = None, season: Optional[int] = None) -> str:
        """
        캐시 키 생성
        
        Args:
            title: 제목
            year: 연도
            season: 시즌
            
        Returns:
            str: 캐시 키
        """
        normalized_title = safe_slugify(title, separator='_')
        year_part = f"_{year}" if year else "_any"
        season_part = f"_{season}" if season else "_any"
        return f"{normalized_title}{year_part}{season_part}"
    
    def _rerank_with_rapidfuzz(self, candidates: List[dict], query: str, year: Optional[int] = None, season: Optional[int] = None) -> List[dict]:
        """
        RapidFuzz를 사용한 후보 재순위화
        
        Args:
            candidates: 검색 후보들
            query: 원본 검색 쿼리
            year: 연도
            season: 시즌
            
        Returns:
            List[dict]: 재순위화된 후보들
        """
        def calculate_rapidfuzz_score(item):
            # 제목 추출
            title_field = "name" if item.get("media_type") == "tv" else "title"
            title = item.get(title_field, "")
            
            if not title:
                return 0
            
            # RapidFuzz 점수 계산 (개선된 버전)
            token_set_ratio = fuzz.token_set_ratio(query.lower(), title.lower())
            token_sort_ratio = fuzz.token_sort_ratio(query.lower(), title.lower())
            ratio = fuzz.ratio(query.lower(), title.lower())
            
            # 가중 평균 점수 (token_set_ratio에 더 높은 가중치)
            base_score = (token_set_ratio * 0.6 + token_sort_ratio * 0.3 + ratio * 0.1)
            
            # 최소 점수 임계값 적용
            if base_score < 70:
                self.logger.debug(f"[TMDB] Low score for '{title}': {base_score:.1f} (query: '{query}')")
                # 두 번째 패스: 연도 필터 제거하고 재시도
                if year:
                    self.logger.debug(f"[TMDB] Retrying without year filter for '{title}'")
                    base_score += 20  # 연도 필터 제거 보너스
            
            # 연도 매칭 보너스
            if year:
                item_year = None
                if item.get("media_type") == "tv":
                    first_air_date = item.get("first_air_date", "")
                    if first_air_date:
                        try:
                            item_year = int(first_air_date.split("-")[0])
                        except (ValueError, IndexError):
                            pass
                else:
                    release_date = item.get("release_date", "")
                    if release_date:
                        try:
                            item_year = int(release_date.split("-")[0])
                        except (ValueError, IndexError):
                            pass
                
                if item_year == year:
                    base_score += 200  # 연도 정확 매칭 보너스
                elif item_year and abs(item_year - year) <= 1:
                    base_score += 50   # 연도 근접 매칭 보너스
            
            # 시즌 정보가 있는 경우 TV 시리즈 우선
            if season and item.get("media_type") == "tv":
                base_score += 100
            
            # 스핀오프/추가 콘텐츠 페널티
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in ['extra', 'real time', 'totally', 'behind the scenes', 'making of']):
                base_score -= 30
            
            # 제목 길이 차이 페널티
            length_diff = abs(len(query) - len(title))
            if length_diff > 3:
                base_score -= 10
            
            # 인기도 보너스 (작은 보너스만)
            popularity = item.get("popularity", 0)
            if popularity > 0:
                base_score += min(10, popularity / 100)
            
            return base_score
        
        # 점수 계산 및 정렬
        scored_candidates = [(item, calculate_rapidfuzz_score(item)) for item in candidates]
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 결과들 로깅
        top_results = scored_candidates[:3]
        for item, score in top_results:
            media_type = item.get("media_type", "unknown")
            title_field = "name" if media_type == "tv" else "title"
            title = item.get(title_field, "Unknown")
            self.logger.info(f"[TMDB] RapidFuzz top result: {title} (score: {score:.1f})")
        
        return [item for item, _ in scored_candidates]
    
    async def batch_search(self, title_year_season_list: List[tuple]) -> List[Optional[dict]]:
        """
        배치 검색 (tmdbsimple 기반)
        
        Args:
            title_year_season_list: (title, year, season) 튜플 리스트
            
        Returns:
            List[Optional[dict]]: 검색 결과 리스트
        """
        results = []
        
        for title, year, season in title_year_season_list:
            try:
                result = await self.search(title, year, season)
                results.append(result)
            except Exception as e:
                self.logger.error(f"[TMDB] Batch search failed for {title}: {e}")
                results.append(None)
        
        return results
    
    def _prepare_for_cache(self, result: dict) -> dict:
        """
        캐시 저장을 위해 결과를 JSON 직렬화 가능한 형태로 변환
        
        Args:
            result: 원본 결과
            
        Returns:
            dict: JSON 직렬화 가능한 결과
        """
        if not result:
            return {}
        
        # 깊은 복사로 변환
        cache_result = {}
        
        for key, value in result.items():
            if key == 'images' and isinstance(value, dict):
                # images는 poster_path와 backdrop_path만 유지
                cache_result[key] = {
                    'poster_path': value.get('poster_path'),
                    'backdrop_path': value.get('backdrop_path')
                }
            elif key == 'seasons' and isinstance(value, list):
                # seasons는 기본 정보만 유지
                cache_result[key] = [
                    {
                        'id': season.get('id'),
                        'name': season.get('name'),
                        'season_number': season.get('season_number'),
                        'episode_count': season.get('episode_count'),
                        'air_date': season.get('air_date')
                    }
                    for season in value
                ]
            elif key == 'season_info' and isinstance(value, dict):
                # season_info는 기본 정보만 유지
                cache_result[key] = {
                    'season_number': value.get('season_number'),
                    'name': value.get('name'),
                    'overview': value.get('overview'),
                    'air_date': value.get('air_date'),
                    'episode_count': value.get('episode_count'),
                    'is_fallback': value.get('is_fallback', False)
                }
            elif key == 'credits' and isinstance(value, dict):
                # credits는 기본 정보만 유지
                cache_result[key] = {
                    'cast': value.get('cast', [])[:10],  # 상위 10명만
                    'crew': value.get('crew', [])[:5]    # 상위 5명만
                }
            elif isinstance(value, (str, int, float, bool, type(None))):
                # 기본 타입은 그대로 유지
                cache_result[key] = value
            elif isinstance(value, list):
                # 리스트는 기본 타입만 유지
                cache_result[key] = [
                    item for item in value 
                    if isinstance(item, (str, int, float, bool, type(None), dict))
                ]
            elif isinstance(value, dict):
                # 딕셔너리는 재귀적으로 처리
                cache_result[key] = self._prepare_for_cache(value)
            else:
                # 기타 타입은 문자열로 변환
                cache_result[key] = str(value)
        
        return cache_result
    
    def close(self):
        """
        TMDB Provider 정리 (tmdbsimple은 별도 정리가 필요하지 않음)
        """
        # tmdbsimple은 별도의 정리 작업이 필요하지 않음
        # 메모리 캐시만 정리
        self._search_cache.clear()
        self.logger.info("TMDB Provider (tmdbsimple) 정리 완료")
    
    async def batch_get_details(self, id_media_type_list: List[tuple]) -> List[Optional[dict]]:
        """
        배치 상세 정보 조회 (tmdbsimple 기반)
        
        Args:
            id_media_type_list: (id, media_type) 튜플 리스트
            
        Returns:
            List[Optional[dict]]: 상세 정보 리스트
        """
        results = []
        
        for item_id, media_type in id_media_type_list:
            try:
                result = await self.get_details(item_id, media_type)
                results.append(result)
            except Exception as e:
                self.logger.error(f"[TMDB] Batch get details failed for {item_id} ({media_type}): {e}")
                results.append(None)
        
        return results 