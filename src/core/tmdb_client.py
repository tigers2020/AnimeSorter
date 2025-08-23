"""
TMDB API 클라이언트 - AnimeSorter (리팩토링됨)

The Movie Database API를 사용하여 애니메이션 메타데이터를 검색하고 조회합니다.
tmdbsimple 라이브러리를 기반으로 구현되었으며, 모듈화된 구조로 리팩토링되었습니다.
"""

import logging
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import tmdbsimple as tmdb

from .tmdb_cache import TMDBCacheManager
from .tmdb_image import TMDBImageManager
from .tmdb_models import TMDBAnimeInfo
from .tmdb_rate_limiter import TMDBRateLimiter


class TMDBClient:
    """TMDB API 클라이언트 (리팩토링됨)"""

    def __init__(self, api_key: str | None = None, language: str = "ko-KR"):
        """TMDB 클라이언트 초기화"""
        self.language = language
        self.cache_dir = Path(".animesorter_cache")
        self.cache_dir.mkdir(exist_ok=True)

        # API 키 설정
        if api_key:
            self.api_key = api_key
            tmdb.API_KEY = api_key
        else:
            # 환경 변수에서 API 키 가져오기
            api_key = os.getenv("TMDB_API_KEY")
            if api_key:
                self.api_key = api_key
                tmdb.API_KEY = api_key
            else:
                raise ValueError(
                    "TMDB API 키가 필요합니다. 환경 변수 TMDB_API_KEY를 설정하거나 생성자에 전달하세요."
                )

        # 요청 타임아웃 설정 (권장: 5초)
        tmdb.REQUESTS_TIMEOUT = 5

        # 커스텀 세션 설정 (연결 풀링 최적화)
        self.session = tmdb.REQUESTS_SESSION

        # 모듈화된 서비스들 초기화
        self.cache_manager = TMDBCacheManager(self.cache_dir)
        self.image_manager = TMDBImageManager(self.cache_dir / "posters")
        self.rate_limiter = TMDBRateLimiter(requests_per_second=4, burst_limit=8)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("TMDB 클라이언트 초기화 완료 (모듈화된 구조)")

    def search_anime(
        self,
        query: str,
        year: int | None = None,
        include_adult: bool = False,
        first_air_date_year: int | None = None,
    ) -> list[TMDBAnimeInfo]:
        """애니메이션 제목으로 검색 (리팩토링됨)"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()

            # 캐시 확인
            cache_key = f"search_{query}_{year}_{include_adult}_{first_air_date_year}"
            cached_result = self.cache_manager.get_cache(cache_key)
            if cached_result:
                return [TMDBAnimeInfo(**item) for item in cached_result]

            # TMDB 검색 실행
            search = tmdb.Search()
            search_params = {
                "query": query,
                "language": self.language,
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
            self.cache_manager.set_cache(cache_key, [asdict(info) for info in anime_info_list])

            return anime_info_list

        except Exception as e:
            self.logger.error(f"TMDB 검색 오류: {e}")
            return []

    def get_anime_details(self, tv_id: int, language: str | None = None) -> TMDBAnimeInfo | None:
        """애니메이션 상세 정보 조회 (리팩토링됨)"""
        try:
            # 속도 제한 확인
            self.rate_limiter.wait_if_needed()

            # 캐시 확인
            cache_key = f"details_{tv_id}_{language or self.language}"
            cached_result = self.cache_manager.get_cache(cache_key)
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
                self.cache_manager.set_cache(cache_key, asdict(anime_info))

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
            cached_result = self.cache_manager.get_cache(cache_key)
            if cached_result:
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
            self.cache_manager.set_cache(cache_key, [asdict(info) for info in anime_info_list])

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
            cache_key = f"season_{tv_id}_{season_number}_{language or self.language}"
            cached_result = self.cache_manager.get_cache(cache_key)
            if cached_result:
                return cached_result

            # TMDB 시즌 정보 조회
            season = tmdb.TV_Seasons(tv_id, season_number)
            response = season.info(language=language or self.language)

            # 결과 캐싱
            self.cache_manager.set_cache(cache_key, response)

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
                f"episode_{tv_id}_{season_number}_{episode_number}_{language or self.language}"
            )
            cached_result = self.cache_manager.get_cache(cache_key)
            if cached_result:
                return cached_result

            # TMDB 에피소드 정보 조회
            episode = tmdb.TV_Episodes(tv_id, season_number, episode_number)
            response = episode.info(language=language or self.language)

            # 결과 캐싱
            self.cache_manager.set_cache(cache_key, response)

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
                id=tmdb_data.get("id"),
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

    def clear_cache(self) -> None:
        """캐시 초기화"""
        try:
            self.cache_manager.clear_cache()
            self.logger.info("캐시가 초기화되었습니다.")
        except Exception as e:
            self.logger.error(f"캐시 초기화 오류: {e}")

    def get_cache_info(self) -> dict[str, Any]:
        """캐시 정보 반환"""
        try:
            cache_info = self.cache_manager.get_cache_info()
            image_cache_info = self.image_manager.get_image_cache_info()

            return {
                "api_cache": cache_info,
                "image_cache": image_cache_info,
                "rate_limiter": self.rate_limiter.get_health_status(),
            }
        except Exception as e:
            return {"error": str(e)}

    def set_language(self, language: str) -> None:
        """언어 설정 변경"""
        self.language = language

    def set_cache_enabled(self, enabled: bool) -> None:
        """캐시 활성화/비활성화"""
        self.cache_manager.set_cache_enabled(enabled)

    def set_cache_expiry(self, expiry_seconds: int) -> None:
        """캐시 만료 시간 설정"""
        self.cache_manager.set_cache_expiry(expiry_seconds)

    def set_memory_cache_size(self, size: int) -> None:
        """메모리 캐시 크기 설정"""
        self.cache_manager.set_memory_cache_size(size)

    async def download_poster_async(self, poster_path: str, size: str = "w185") -> str | None:
        """TMDB 포스터 이미지 비동기 다운로드"""
        return await self.image_manager.download_poster_async(poster_path, size)

    def download_poster(self, poster_path: str, size: str = "w185") -> str | None:
        """TMDB 포스터 이미지 다운로드 (동기 버전)"""
        return self.image_manager.download_poster(poster_path, size)

    def download_backdrop(self, backdrop_path: str, size: str = "w1280") -> str | None:
        """TMDB 배경 이미지 다운로드"""
        return self.image_manager.download_backdrop(backdrop_path, size)

    def download_profile(self, profile_path: str, size: str = "w185") -> str | None:
        """TMDB 프로필 이미지 다운로드"""
        return self.image_manager.download_profile(profile_path, size)

    def get_poster_path(self, poster_path: str, size: str = "w185") -> str | None:
        """포스터 이미지 경로 반환 (다운로드 포함)"""
        return self.image_manager.get_poster_path(poster_path, size)

    def get_backdrop_path(self, backdrop_path: str, size: str = "w1280") -> str | None:
        """배경 이미지 경로 반환 (다운로드 포함)"""
        return self.image_manager.get_backdrop_path(backdrop_path, size)

    def get_profile_path(self, profile_path: str, size: str = "w185") -> str | None:
        """프로필 이미지 경로 반환 (다운로드 포함)"""
        return self.image_manager.get_profile_path(profile_path, size)

    def get_image_url(self, image_path: str, size: str = "w185") -> str:
        """TMDB 이미지 URL 생성"""
        return self.image_manager.get_image_url(image_path, size)

    def clear_image_cache(self) -> int:
        """이미지 캐시 정리"""
        return self.image_manager.clear_image_cache()

    def get_image_cache_info(self) -> dict:
        """이미지 캐시 정보 반환"""
        return self.image_manager.get_image_cache_info()

    def set_poster_cache_dir(self, new_dir: Path) -> bool:
        """포스터 캐시 디렉토리 변경"""
        return self.image_manager.set_poster_cache_dir(new_dir)

    def update_api_key(self, new_api_key: str) -> None:
        """API 키 업데이트"""
        if new_api_key and new_api_key != self.api_key:
            self.api_key = new_api_key
            tmdb.API_KEY = new_api_key
            self.logger.info("TMDB API 키가 업데이트되었습니다")

    def get_api_key(self) -> str:
        """현재 API 키 반환"""
        return self.api_key

    def get_rate_limiter_status(self) -> dict:
        """속도 제한 관리자 상태 반환"""
        return self.rate_limiter.get_health_status()

    def set_rate_limit(self, requests_per_second: int, burst_limit: Optional[int] = None) -> None:
        """속도 제한 설정 변경"""
        self.rate_limiter.set_rate_limit(requests_per_second, burst_limit)

    def reset_rate_limiter(self) -> None:
        """속도 제한 관리자 초기화"""
        self.rate_limiter.reset()

    async def close_resources(self) -> None:
        """리소스 정리"""
        await self.image_manager.close_async_session()
