import logging
import yaml
import os
from typing import Optional, Any, List
from .api.client import TMDBClient, TMDBApiError
from .api.endpoints import TMDBEndpoints
from src.utils.file_cleaner import FileCleaner
from difflib import SequenceMatcher

import asyncio
import time

class TMDBProvider:
    """
    TMDB 메타데이터 제공자 (캐시/로깅/예외 구조 개선)
    """
    def __init__(self, api_key: str, cache_db: Optional[Any] = None, language: str = "ko-KR"):
        self.client = TMDBClient(api_key, language)
        self.endpoints = TMDBEndpoints(self.client)
        self.cache_db = cache_db
        self.logger = logging.getLogger("animesorter.tmdb")
        self.title_overrides = self._load_title_overrides()

    async def initialize(self):
        await self.client.initialize()
        if self.cache_db:
            await self.cache_db.initialize()

    async def close(self):
        await self.client.close()
        if self.cache_db:
            await self.cache_db.close()
    
    def _load_title_overrides(self) -> dict:
        """
        제목 오버라이드 테이블 로드
        
        Returns:
            dict: 제목 → TMDB ID 매핑
        """
        overrides = {}
        override_file = "config/title_overrides.yaml"
        
        try:
            if os.path.exists(override_file):
                with open(override_file, 'r', encoding='utf-8') as f:
                    overrides = yaml.safe_load(f) or {}
                self.logger.info(f"[TMDB] Loaded {len(overrides)} title overrides")
            else:
                self.logger.info(f"[TMDB] No override file found: {override_file}")
        except Exception as e:
            self.logger.error(f"[TMDB] Failed to load title overrides: {e}")
        
        return overrides

    def _generate_progressive_titles(self, title: str) -> List[str]:
        """
        제목을 점진적으로 단순화한 버전들을 생성
        
        Args:
            title: 원본 제목
            
        Returns:
            List[str]: 점진적으로 단순화된 제목 목록
        """
        import re
        
        titles = [title]  # 원본 제목을 첫 번째로
        
        # 1단계: 기본 정제 (괄호, 특수문자 제거)
        cleaned = re.sub(r'[\(\)\[\]\{\}]', '', title)  # 괄호 제거
        cleaned = re.sub(r'[^\w\s\-]', ' ', cleaned)    # 특수문자 제거 (하이픈 제외)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # 연속 공백 정리
        
        if cleaned and cleaned != title:
            titles.append(cleaned)
        
        # 2단계: 불필요한 단어 제거
        unnecessary_words = [
            '무등급감독판', '감독판', 'extended', 'director', 'cut', 'edition',
            'the', 'movie', 'film', '시리즈', 'series', 'season', '시즌',
            'episode', '에피소드', 'part', '파트', 'volume', '볼륨',
            'complete', '완전판', 'full', 'version', '버전'
        ]
        
        # 정확한 단어 매칭을 위해 정규식 사용
        filtered_title = cleaned
        for word in unnecessary_words:
            # 단어 경계를 사용하여 정확한 매칭
            pattern = r'\b' + re.escape(word) + r'\b'
            filtered_title = re.sub(pattern, '', filtered_title, flags=re.IGNORECASE)
        
        # 연속 공백 정리
        filtered_title = re.sub(r'\s+', ' ', filtered_title).strip()
        
        if filtered_title and filtered_title != cleaned:
            if filtered_title not in titles:
                titles.append(filtered_title)
        
        # 3단계: 숫자 제거 (연도 제외)
        # 연도 패턴 (4자리 숫자)은 보존하고 나머지 숫자 제거
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, filtered_title)
        
        # 숫자 제거 (연도 제외)
        no_numbers = re.sub(r'\b\d+\b', '', filtered_title)
        no_numbers = re.sub(r'\s+', ' ', no_numbers).strip()
        
        if no_numbers and no_numbers != filtered_title:
            titles.append(no_numbers)
        
        # 4단계: 연도가 있는 경우 연도 제거 버전도 추가
        if years:
            for year in years:
                year_removed = re.sub(r'\b' + year + r'\b', '', filtered_title)
                year_removed = re.sub(r'\s+', ' ', year_removed).strip()
                if year_removed and year_removed not in titles:
                    titles.append(year_removed)
        
        # 5단계: 한국어-영어 제목 매핑 추가
        korean_to_english = {
            '리딕': 'Riddick',
            '소닉': 'Sonic',
            '헤지호그': 'Hedgehog',
            '우마무스메': 'Uma Musume',
            '프리티 더비': 'Pretty Derby',
            '데몬 헌터스': 'Demon Hunters',
            '퇴마록': 'Exorcism Chronicles',
            '하이에나': 'Hyena',
            '피겨스': 'Figures',
            '히든': 'Hidden',
            '스내푸': 'Snap',
            '스트라이크': 'Strike',
            '일하는 세포': 'Cells at Work',
            '세포': 'Cells',
        }
        
        # 한국어 단어를 영어로 변환한 버전 추가
        for korean, english in korean_to_english.items():
            if korean in filtered_title:
                english_version = filtered_title.replace(korean, english)
                if english_version not in titles:
                    titles.append(english_version)
        
        # 6단계: 공백으로 분리하여 단어 단위로 제거 (기존 로직)
        words = title.split()
        for i in range(len(words) - 1, 0, -1):
            simplified = " ".join(words[:i]).strip()
            if simplified and simplified not in titles:
                titles.append(simplified)
        
        # 7단계: 정제된 제목에서도 단어 단위 제거
        if len(titles) > 1:
            cleaned_words = titles[1].split()  # 첫 번째 정제된 제목 사용
            for i in range(len(cleaned_words) - 1, 0, -1):
                simplified = " ".join(cleaned_words[:i]).strip()
                if simplified and simplified not in titles:
                    titles.append(simplified)
        
        # 중복 제거 및 빈 문자열 필터링
        unique_titles = []
        for t in titles:
            if t and t.strip():
                # 불완전한 제목 정리 (끝에 하이픈이나 특수문자 제거)
                cleaned_t = re.sub(r'[-_.,;:!?]+$', '', t.strip())  # 끝에 특수문자 제거
                cleaned_t = re.sub(r'^\s*[-_.,;:!?]+\s*', '', cleaned_t)  # 시작에 특수문자 제거
                cleaned_t = re.sub(r'\s+', ' ', cleaned_t).strip()  # 연속 공백 정리
                
                if cleaned_t and cleaned_t not in unique_titles:
                    unique_titles.append(cleaned_t)
        
        return unique_titles

    async def search(self, title: str, year: Optional[int] = None) -> Optional[dict]:
        """
        제목과 연도로 메타데이터 검색
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
        Returns:
            dict or None: 검색 결과 또는 None (결과 없음)
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
        
        # 캐시 확인
        if self.cache_db:
            cache_key = self._generate_cache_key(title, year)
            cached_result = await self.cache_db.get_cache(cache_key)
            if cached_result:
                self.logger.info(f"[TMDB] Cache hit for: {title}")
                
                # 캐시된 데이터에 media_type이 없으면 추론
                if 'media_type' not in cached_result or cached_result['media_type'] == 'unknown':
                    # TV 시리즈와 영화 구분 (name 필드가 있으면 TV, title 필드가 있으면 영화)
                    if 'name' in cached_result and cached_result['name']:
                        cached_result['media_type'] = 'tv'
                        self.logger.info(f"[TMDB] Inferred media_type: tv for {title}")
                    elif 'title' in cached_result and cached_result['title']:
                        cached_result['media_type'] = 'movie'
                        self.logger.info(f"[TMDB] Inferred media_type: movie for {title}")
                    else:
                        # 기본값은 tv (애니메이션)
                        cached_result['media_type'] = 'tv'
                        self.logger.info(f"[TMDB] Default media_type: tv for {title}")
                
                return cached_result

        # 점진적 검색 시도
        progressive_titles = self._generate_progressive_titles(title)
        
        for attempt, search_title in enumerate(progressive_titles):
            try:
                if attempt > 0:
                    self.logger.info(f"[TMDB] Fallback attempt {attempt}: '{search_title}'")
                
                # 1단계: search_multi로 후보들 찾기 (연도 파라미터 개선)
                multi_results = await self.endpoints.search_multi(search_title, year)
                candidates = self._filter_and_sort_results(multi_results.get("results", []), search_title)
                
                if candidates:
                    # 2단계: 상위 후보들을 실제 detail API로 확인
                    for candidate in candidates[:3]:  # 상위 3개 후보만 확인
                        candidate_id = candidate.get("id")
                        candidate_media_type = candidate.get("media_type")
                        
                        if not candidate_id or candidate_media_type not in ("tv", "movie"):
                            continue
                            
                        try:
                            # 실제 detail API 호출로 정확한 분류 확인
                            result = await self.get_details(candidate_id, candidate_media_type)
                            
                            if result:
                                # 원본 제목으로 캐시에 저장
                                if self.cache_db:
                                    try:
                                        await self.cache_db.set_cache(cache_key, result, year)
                                    except Exception as e:
                                        self.logger.warning(f"[TMDB] Cache save error: {e}")
                                
                                if attempt > 0:
                                    self.logger.info(f"[TMDB] Fallback success with '{search_title}' for original '{title}'")
                                
                                self.logger.info(f"[TMDB] Found: {result.get('name', result.get('title', 'Unknown'))} (media_type: {result.get('media_type')})")
                                return result
                                
                        except Exception as e:
                            self.logger.warning(f"[TMDB] Detail API failed for {candidate_id} ({candidate_media_type}): {e}")
                            continue
                
            except TMDBApiError as e:
                self.logger.error(f"[TMDB] API error during search attempt {attempt + 1}: {e}")
                raise
            except Exception as e:
                self.logger.error(f"[TMDB] Unexpected error during search attempt {attempt + 1}: {e}")
                raise TMDBApiError(f"TMDBProvider search failed: {e}")
        
        # 모든 시도 실패
        self.logger.warning(f"[TMDB] No results for: {title} ({year}) - tried {len(progressive_titles)} variations")
        return None

    async def get_details(self, media_id: Any, media_type: str) -> Optional[dict]:
        try:
            if media_type == "tv":
                result = await self.endpoints.get_tv_details(media_id)
                # media_type 필드 추가
                result['media_type'] = 'tv'
                return result
            elif media_type == "movie":
                result = await self.endpoints.get_movie_details(media_id)
                # media_type 필드 추가
                result['media_type'] = 'movie'
                return result
            else:
                self.logger.warning(f"[TMDB] Unknown media_type: {media_type}")
                return None
        except TMDBApiError as e:
            self.logger.error(f"[TMDB] Failed to get details: {e}")
            raise
        except Exception as e:
            self.logger.error(f"[TMDB] Unexpected error in get_details: {e}", exc_info=True)
            raise TMDBApiError(f"get_details failed: {e}")

    async def batch_search(
        self,
        title_year_list: list[tuple[str, int | None]],
        max_concurrent: int = 5,
        retry: int = 2,
        min_interval: float = 0.2
    ) -> list[Optional[dict]]:
        """
        여러 제목/연도 쌍을 비동기로 검색 (동시성/재시도/속도제한)
        Args:
            title_year_list: (제목, 연도) 쌍 리스트
            max_concurrent: 동시 요청 제한
            retry: 실패 시 재시도 횟수
            min_interval: 각 요청 간 최소 간격(초)
        Returns:
            Optional[dict] 리스트 (검색 결과)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = [None] * len(title_year_list)
        last_call = 0.0

        async def search_one(idx, title, year):
            nonlocal last_call
            for attempt in range(1, retry + 2):
                try:
                    async with semaphore:
                        # 속도 제한
                        now = time.monotonic()
                        wait = max(0, min_interval - (now - last_call))
                        if wait > 0:
                            await asyncio.sleep(wait)
                        last_call = time.monotonic()
                        res = await self.search(title, year)
                        results[idx] = res
                        return
                except Exception as e:
                    if attempt < retry + 1:
                        await asyncio.sleep(0.5 * attempt)  # 지수 백오프
                        continue
                    self.logger.error(f"[TMDB] batch_search 실패: {title} ({year}) - {e}")
                    results[idx] = None

        tasks = [search_one(i, t, y) for i, (t, y) in enumerate(title_year_list)]
        await asyncio.gather(*tasks)
        return results

    async def batch_get_details(
        self,
        id_type_list: list[tuple[Any, str]],
        max_concurrent: int = 5,
        retry: int = 2,
        min_interval: float = 0.2
    ) -> list[Optional[dict]]:
        """
        여러 (id, media_type) 쌍을 비동기로 상세조회 (동시성/재시도/속도제한)
        Args:
            id_type_list: (id, media_type) 쌍 리스트
            max_concurrent: 동시 요청 제한
            retry: 실패 시 재시도 횟수
            min_interval: 각 요청 간 최소 간격(초)
        Returns:
            Optional[dict] 리스트 (상세 결과)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = [None] * len(id_type_list)
        last_call = 0.0

        async def get_one(idx, media_id, media_type):
            nonlocal last_call
            for attempt in range(1, retry + 2):
                try:
                    async with semaphore:
                        now = time.monotonic()
                        wait = max(0, min_interval - (now - last_call))
                        if wait > 0:
                            await asyncio.sleep(wait)
                        last_call = time.monotonic()
                        res = await self.get_details(media_id, media_type)
                        results[idx] = res
                        return
                except Exception as e:
                    if attempt < retry + 1:
                        await asyncio.sleep(0.5 * attempt)
                        continue
                    self.logger.error(f"[TMDB] batch_get_details 실패: {media_id} ({media_type}) - {e}")
                    results[idx] = None

        tasks = [get_one(i, mid, mtype) for i, (mid, mtype) in enumerate(id_type_list)]
        await asyncio.gather(*tasks)
        return results

    def _filter_and_sort_results(self, results: List[dict], query: str) -> List[dict]:
        # 지원 미디어 타입만 필터
        filtered = [r for r in results if r.get("media_type") in ("tv", "movie")]
        
        if not filtered:
            return []
        
        ANIMATION_GENRE_ID = 16
        
        def calculate_score(item):
            # 제목 유사도(0~100)
            title_field = "name" if item.get("media_type") == "tv" else "title"
            title = item.get(title_field, "")
            
            # 정확한 제목 매칭 보너스 (높은 우선순위)
            query_lower = query.lower().strip()
            title_lower = title.lower().strip()
            
            # 정확한 제목 매칭
            if query_lower == title_lower:
                return 1000  # 매우 높은 점수
            
            # 제목이 쿼리로 시작하는 경우 (예: "Doctor Who" vs "Doctor Who Extra")
            if title_lower.startswith(query_lower + " "):
                return 500  # 높은 점수
            
            # 쿼리가 제목으로 시작하는 경우
            if query_lower.startswith(title_lower + " "):
                return 400  # 높은 점수
            
            # 일반적인 유사도 계산
            sim = int(SequenceMatcher(None, query_lower, title_lower).ratio() * 100)
            
            # 인기도(0~10)
            pop = min(10, int(item.get("popularity", 0) / 10))
            
            # media_type 기반 점수 (movie와 tv를 동등하게 처리)
            base_score = sim + pop
            
            # 애니메이션 장르 보너스 (작은 보너스만)
            if ANIMATION_GENRE_ID in item.get("genre_ids", []):
                base_score += 5  # 작은 보너스만
            
            return base_score
        
        # 모든 결과를 점수로 정렬
        scored_results = [(item, calculate_score(item)) for item in filtered]
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 결과들 로깅 (점수 포함)
        top_results = [(item, score) for item, score in scored_results[:3]]
        for item, score in top_results:
            media_type = item.get("media_type", "unknown")
            title_field = "name" if media_type == "tv" else "title"
            title = item.get(title_field, "Unknown")
            self.logger.info(f"[TMDB] Top result: {title} (media_type: {media_type}, score: {score})")
        
        return [item for item, _ in scored_results]

    def _generate_cache_key(self, title: str, year: Optional[int]) -> str:
        """캐시 키 생성"""
        normalized_title = title.lower().replace(" ", "_")
        year_part = f"_{year}" if year else "_any"
        return f"{normalized_title}{year_part}" 