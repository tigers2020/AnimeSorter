"""
tmdbsimple 기반 TMDB 서비스 구현체

tmdbsimple 라이브러리를 사용하여 TMDB API와 통신하는 서비스 구현체입니다.
기존 TMDBClient의 로직을 서비스로 분리하여 의존성 주입이 가능하도록 합니다.
"""

import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any

import tmdbsimple as tmdb

from src.core.tmdb.interfaces import (
    TMDBConfig,
    TMDBServiceProtocol,
    TMDBCacheProtocol,
    TMDBRateLimiterProtocol,
)
from src.core.tmdb_models import TMDBAnimeInfo


class TMDBSimpleService(TMDBServiceProtocol):
    """
    tmdbsimple 기반 TMDB 서비스 구현체
    
    tmdbsimple 라이브러리를 사용하여 TMDB API와 통신합니다.
    기존 TMDBClient의 검색 및 상세 정보 조회 로직을 서비스로 분리했습니다.
    """
    
    def __init__(
        self,
        config: TMDBConfig,
        cache: TMDBCacheProtocol,
        rate_limiter: TMDBRateLimiterProtocol,
    ):
        """TMDB 서비스 초기화"""
        self.config = config
        self.cache = cache
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # tmdbsimple 설정
        tmdb.API_KEY = config.api_key
        tmdb.REQUESTS_TIMEOUT = config.timeout
        
        self.logger.info("TMDBSimpleService 초기화 완료")
    
    def search_anime(
        self,
        query: str,
        year: int | None = None,
        include_adult: bool = False,
        first_air_date_year: int | None = None,
    ) -> list[TMDBAnimeInfo]:
        """애니메이션 제목으로 검색"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()
            
            # 캐시 확인
            cache_key = f"search_{query}_{year}_{include_adult}_{first_air_date_year}"
            cached_result = self.cache.get_cache(cache_key)
            if cached_result:
                # 캐시된 데이터에서 tmdb_id를 id로 매핑 (호환성 유지)
                for item in cached_result:
                    if "tmdb_id" in item and "id" not in item:
                        item["id"] = item["tmdb_id"]
                return [TMDBAnimeInfo(**item) for item in cached_result]
            
            # TMDB 검색 실행
            search = tmdb.Search()
            search_params = {
                "query": query,
                "language": self.config.language,
                "include_adult": include_adult,
            }
            
            # 연도 필터 추가
            if year:
                search_params["first_air_date_year"] = year
            elif first_air_date_year:
                search_params["first_air_date_year"] = first_air_date_year
            else:
                # 연도가 지정되지 않은 경우 최근 10년 범위로 검색
                current_year = datetime.now().year
                search_params["with_first_air_date_gte"] = f"{current_year - 10}-01-01"
                search_params["with_first_air_date_lte"] = f"{current_year}-12-31"
            
            response = search.tv(**search_params)
            
            # 애니메이션 장르 필터링 (장르 ID: 16=애니메이션, 10759=액션&어드벤처)
            anime_results = []
            for result in response.get("results", []):
                genre_ids = result.get("genre_ids", [])
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
            self.cache.set_cache(cache_key, [asdict(info) for info in anime_info_list])
            
            return anime_info_list
            
        except Exception as e:
            self.logger.error(f"TMDB 검색 오류: {e}")
            return []
    
    def get_anime_details(self, tv_id: int, language: str | None = None) -> TMDBAnimeInfo | None:
        """애니메이션 상세 정보 조회"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()
            
            # 캐시 확인
            cache_key = f"details_{tv_id}_{language or self.config.language}"
            cached_result = self.cache.get_cache(cache_key)
            if cached_result:
                # 캐시된 데이터에서 tmdb_id를 id로 매핑 (호환성 유지)
                if "tmdb_id" in cached_result and "id" not in cached_result:
                    cached_result["id"] = cached_result["tmdb_id"]
                return TMDBAnimeInfo(**cached_result)
            
            # TMDB 상세 정보 조회
            tv = tmdb.TV(tv_id)
            response = tv.info(language=language or self.config.language)
            
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
                response.update(
                    {
                        "credits": credits,
                        "images": images,
                        "external_ids": external_ids,
                        "videos": videos,
                        "keywords": keywords,
                        "recommendations": recommendations,
                        "similar": similar,
                        "translations": translations,
                        "content_ratings": content_ratings,
                        "watch_providers": watch_providers,
                    }
                )
            except Exception as e:
                self.logger.warning(f"추가 정보 조회 실패: {e}")
            
            # TMDBAnimeInfo 객체로 변환
            anime_info = self._convert_to_anime_info(response)
            
            # 결과 캐싱
            if anime_info:
                self.cache.set_cache(cache_key, asdict(anime_info))
            
            return anime_info
            
        except Exception as e:
            self.logger.error(f"TMDB 상세 정보 조회 오류: {e}")
            return None
    
    def search_anime_optimized(self, query: str, language: str = "ko-KR") -> list[TMDBAnimeInfo]:
        """최적화된 애니메이션 검색 (캐시됨)"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()
            
            # 캐시 확인
            cache_key = f"optimized_search_{query}_{language}"
            cached_result = self.cache.get_cache(cache_key)
            if cached_result:
                # 캐시된 데이터에서 tmdb_id를 id로 매핑 (호환성 유지)
                for item in cached_result:
                    if "tmdb_id" in item and "id" not in item:
                        item["id"] = item["tmdb_id"]
                return [TMDBAnimeInfo(**item) for item in cached_result]
            
            search = tmdb.Search()
            response = search.tv(
                query=query,
                language=language,
                first_air_date_year=2020,  # 최신 작품 우선
                sort_by="popularity.desc",  # 인기도 순 정렬
            )
            
            # 결과 필터링 (애니메이션 장르 우선)
            anime_results = []
            for result in response.get("results", []):
                genre_ids = result.get("genre_ids", [])
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
            self.cache.set_cache(cache_key, [asdict(info) for info in anime_info_list])
            
            return anime_info_list
            
        except Exception as e:
            self.logger.error(f"TMDB 최적화 검색 오류: {e}")
            return []
    
    def get_anime_season(
        self, tv_id: int, season_number: int, language: str | None = None
    ) -> dict[str, Any] | None:
        """시즌 정보 조회 (최적화됨)"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()
            
            # 캐시 확인
            cache_key = f"season_{tv_id}_{season_number}_{language or self.config.language}"
            cached_result = self.cache.get_cache(cache_key)
            if cached_result:
                return cached_result
            
            # TMDB 시즌 정보 조회
            season = tmdb.TV_Seasons(tv_id, season_number)
            response = season.info(language=language or self.config.language)
            
            # 결과 캐싱
            self.cache.set_cache(cache_key, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"TMDB 시즌 정보 조회 오류: {e}")
            return None
    
    def get_anime_episode(
        self, tv_id: int, season_number: int, episode_number: int, language: str | None = None
    ) -> dict[str, Any] | None:
        """에피소드 정보 조회 (최적화됨)"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()
            
            # 캐시 확인
            cache_key = (
                f"episode_{tv_id}_{season_number}_{episode_number}_{language or self.config.language}"
            )
            cached_result = self.cache.get_cache(cache_key)
            if cached_result:
                return cached_result
            
            # TMDB 에피소드 정보 조회
            episode = tmdb.TV_Episodes(tv_id, season_number, episode_number)
            response = episode.info(language=language or self.config.language)
            
            # 결과 캐싱
            self.cache.set_cache(cache_key, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"TMDB 에피소드 정보 조회 오류: {e}")
            return None
    
    def _convert_to_anime_info(self, tmdb_data: dict[str, Any]) -> TMDBAnimeInfo | None:
        """TMDB 응답을 TMDBAnimeInfo 객체로 변환"""
        try:
            # 필수 필드 확인
            if "id" not in tmdb_data or "name" not in tmdb_data:
                return None
            
            # 기본 필드 설정
            return TMDBAnimeInfo(
                id=tmdb_data.get("id", 0),
                name=tmdb_data.get("name", ""),
                original_name=tmdb_data.get("original_name", ""),
                overview=tmdb_data.get("overview", ""),
                first_air_date=tmdb_data.get("first_air_date", ""),
                last_air_date=tmdb_data.get("last_air_date", ""),
                number_of_seasons=tmdb_data.get("number_of_seasons", 0),
                number_of_episodes=tmdb_data.get("number_of_episodes", 0),
                status=tmdb_data.get("status", ""),
                type=tmdb_data.get("type", ""),
                popularity=tmdb_data.get("popularity", 0.0),
                vote_average=tmdb_data.get("vote_average", 0.0),
                vote_count=tmdb_data.get("vote_count", 0),
                genres=tmdb_data.get("genres", []),
                poster_path=tmdb_data.get("poster_path", ""),
                backdrop_path=tmdb_data.get("backdrop_path", ""),
                episode_run_time=tmdb_data.get("episode_run_time", []),
                networks=tmdb_data.get("networks", []),
                production_companies=tmdb_data.get("production_companies", []),
                languages=tmdb_data.get("languages", []),
                origin_country=tmdb_data.get("origin_country", []),
                in_production=tmdb_data.get("in_production", False),
                last_episode_to_air=tmdb_data.get("last_episode_to_air"),
                next_episode_to_air=tmdb_data.get("next_episode_to_air"),
                seasons=tmdb_data.get("seasons", []),
                external_ids=tmdb_data.get("external_ids", {}),
                images=tmdb_data.get("images", {}),
                credits=tmdb_data.get("credits", {}),
                videos=tmdb_data.get("videos", {}),
                keywords=tmdb_data.get("keywords", {}),
                recommendations=tmdb_data.get("recommendations", {}),
                similar=tmdb_data.get("similar", {}),
                translations=tmdb_data.get("translations", {}),
                content_ratings=tmdb_data.get("content_ratings", {}),
                watch_providers=tmdb_data.get("watch_providers", {}),
            )
            
        except Exception as e:
            self.logger.error(f"TMDB 데이터 변환 오류: {e}")
            return None
