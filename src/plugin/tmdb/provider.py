import logging
import re
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

    async def initialize(self):
        await self.client.initialize()
        if self.cache_db:
            await self.cache_db.initialize()

    async def close(self):
        await self.client.close()
        if self.cache_db:
            await self.cache_db.close()

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
                
                # 1단계: 여러 페이지에서 후보들 수집 (최대 3페이지, 60개 결과)
                all_candidates = []
                
                # search_multi로 1-3페이지 수집
                for page in range(1, 4):
                    try:
                        multi_results = await self.endpoints.search_multi(search_title, year, page=page)
                        page_results = multi_results.get("results", [])
                        if not page_results:
                            break
                        all_candidates.extend(page_results)
                        self.logger.debug(f"[TMDB] Collected {len(page_results)} results from page {page}")
                    except Exception as e:
                        self.logger.warning(f"[TMDB] Failed to get page {page}: {e}")
                        break
                
                # search_tv로도 1-2페이지 추가 수집 (TV 시리즈 특화)
                for page in range(1, 3):
                    try:
                        tv_results = await self.endpoints.search_tv(search_title, year, page=page)
                        page_results = tv_results.get("results", [])
                        if not page_results:
                            break
                        all_candidates.extend(page_results)
                        self.logger.debug(f"[TMDB] Collected {len(page_results)} TV results from page {page}")
                    except Exception as e:
                        self.logger.warning(f"[TMDB] Failed to get TV page {page}: {e}")
                        break
                
                # 중복 제거 (ID 기준)
                seen_ids = set()
                unique_candidates = []
                for candidate in all_candidates:
                    candidate_id = candidate.get("id")
                    if candidate_id and candidate_id not in seen_ids:
                        seen_ids.add(candidate_id)
                        unique_candidates.append(candidate)
                
                self.logger.info(f"[TMDB] Total unique candidates: {len(unique_candidates)}")
                candidates = self._filter_and_sort_results(unique_candidates, search_title)
                
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
        """
        개선된 검색 결과 필터링 및 정렬
        - 제목 유사도 + 금지 키워드 패널티 + popularity 기반 랭킹
        - Doctor Who Extra, tvN스페셜 등의 잘못된 매핑 방지
        """
        # 지원 미디어 타입만 필터
        filtered = [r for r in results if r.get("media_type") in ("tv", "movie")]
        
        if not filtered:
            return []
        
        # 강화된 금지 키워드 패턴 (파생 프로그램, 스페셜 등)
        BAD_KEYWORDS = re.compile(r'\b(extra|real\s*time|totally|behind|special|스페셜|특별|추가|리뷰|토크|인터뷰|behind\s*the\s*scenes|making\s*of|documentary|다큐|스페셜|특집)\b', re.IGNORECASE)
        
        # Doctor Who 관련 특별 처리
        DOCTOR_WHO_PATTERNS = [
            re.compile(r'\bdoctor\s*who\s*extra\b', re.IGNORECASE),
            re.compile(r'\bdoctor\s*who\s*behind\b', re.IGNORECASE),
            re.compile(r'\bdoctor\s*who\s*totally\b', re.IGNORECASE),
            re.compile(r'\bdoctor\s*who\s*real\s*time\b', re.IGNORECASE),
        ]
        
        # 한국어 특별편 패턴
        KOREAN_SPECIAL_PATTERNS = [
            re.compile(r'\btvn\s*스페셜\b', re.IGNORECASE),
            re.compile(r'\bsbs\s*스페셜\b', re.IGNORECASE),
            re.compile(r'\bkbs\s*스페셜\b', re.IGNORECASE),
            re.compile(r'\bmbc\s*스페셜\b', re.IGNORECASE),
            re.compile(r'\b특별편\b'),
            re.compile(r'\b특집\b'),
            re.compile(r'\b추가편\b'),
        ]
        
        # 애니메이션 장르 ID
        ANIMATION_GENRE_ID = 16
        
        # 최대 popularity 계산 (정규화용)
        max_popularity = max((item.get("popularity", 0) for item in filtered), default=1)
        
        def calculate_score(item):
            title_field = "name" if item.get("media_type") == "tv" else "title"
            title = item.get(title_field, "")
            
            # 1. 제목 유사도 (0~100)
            sim = int(SequenceMatcher(None, query.lower(), title.lower()).ratio() * 100)
            
            # 2. 높은 유사도 보너스 (95% 이상)
            if sim >= 95:
                sim += 50
            
            # 3. 강화된 금지 키워드 패널티 (-50)
            if BAD_KEYWORDS.search(title):
                sim -= 50
                self.logger.info(f"[TMDB] Bad keyword penalty applied to: {title}")
            
            # 4. Doctor Who 관련 특별 패널티 (-100)
            for pattern in DOCTOR_WHO_PATTERNS:
                if pattern.search(title):
                    sim -= 100
                    self.logger.info(f"[TMDB] Doctor Who spin-off penalty applied to: {title}")
                    break
            
            # 5. 한국어 특별편 패널티 (-80)
            for pattern in KOREAN_SPECIAL_PATTERNS:
                if pattern.search(title):
                    sim -= 80
                    self.logger.info(f"[TMDB] Korean special penalty applied to: {title}")
                    break
            
            # 6. popularity 정규화 (0~50)
            pop_norm = int(50 * (item.get("popularity", 0) / max_popularity))
            
            # 7. 애니메이션 장르 보너스 (+5)
            if ANIMATION_GENRE_ID in item.get("genre_ids", []):
                pop_norm += 5
            
            total_score = sim + pop_norm
            
            # 디버깅 로그
            self.logger.debug(f"[TMDB] Score breakdown for '{title}': similarity={sim}, popularity={pop_norm}, total={total_score}")
            
            return total_score
        
        # 모든 결과를 점수로 정렬
        scored_results = [(item, calculate_score(item)) for item in filtered]
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 결과들 로깅
        top_results = [item for item, _ in scored_results[:3]]
        for i, item in enumerate(top_results):
            media_type = item.get("media_type", "unknown")
            title_field = "name" if media_type == "tv" else "title"
            title = item.get(title_field, "Unknown")
            score = scored_results[i][1]
            self.logger.info(f"[TMDB] Top result #{i+1}: {title} (media_type: {media_type}, score: {score})")
        
        return [item for item, _ in scored_results]

    def _generate_cache_key(self, title: str, year: Optional[int]) -> str:
        """캐시 키 생성"""
        normalized_title = title.lower().replace(" ", "_")
        year_part = f"_{year}" if year else "_any"
        return f"{normalized_title}{year_part}" 