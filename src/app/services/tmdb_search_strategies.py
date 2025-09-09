"""
TMDB 검색 전략 모듈

다양한 검색 전략을 구현하여 검색 정확도를 향상시킵니다.
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from src.core import (
    TMDBAnimeInfoModel as TMDBAnimeInfo,  # type: ignore[import-untyped]
    TMDBClient,  # type: ignore[import-untyped]
)


class SearchStrategy(ABC):
    """검색 전략 인터페이스"""

    @abstractmethod
    def search(self, tmdb_client: TMDBClient, query: str, **kwargs: Any) -> list[TMDBAnimeInfo]:
        """검색 실행"""

    @abstractmethod
    def get_confidence_score(self, query: str, result: TMDBAnimeInfo) -> float:
        """검색 결과의 신뢰도 점수 계산"""


class ExactMatchStrategy(SearchStrategy):
    """정확한 매칭 전략"""

    def search(self, tmdb_client: TMDBClient, query: str, **kwargs: Any) -> list[TMDBAnimeInfo]:
        """정확한 제목 매칭으로 검색"""
        try:
            results = tmdb_client.search_anime(query, **kwargs)
            return [r for r in results if self.get_confidence_score(query, r) > 0.8]
        except Exception as e:
            logging.error(f"정확한 매칭 검색 실패: {e}")
            return []

    def get_confidence_score(self, query: str, result: TMDBAnimeInfo) -> float:
        """정확한 매칭 신뢰도 점수"""
        query_lower = query.lower().strip()
        title_lower = result.name.lower().strip()
        original_lower = result.original_name.lower().strip()

        # 완전 일치
        if query_lower in (title_lower, original_lower):
            return 1.0

        # 부분 일치
        if query_lower in title_lower or query_lower in original_lower:
            return 0.9

        # 단어 단위 일치
        query_words = set(re.findall(r"\w+", query_lower))
        title_words = set(re.findall(r"\w+", title_lower))
        original_words = set(re.findall(r"\w+", original_lower))

        if query_words.issubset(title_words) or query_words.issubset(original_words):
            return 0.8

        return 0.0


class FuzzyMatchStrategy(SearchStrategy):
    """퍼지 매칭 전략"""

    def search(self, tmdb_client: TMDBClient, query: str, **kwargs: Any) -> list[TMDBAnimeInfo]:
        """퍼지 매칭으로 검색"""
        try:
            # 여러 변형으로 검색 시도
            search_variations = self._generate_search_variations(query)
            all_results = []

            for variation in search_variations:
                results = tmdb_client.search_anime(variation, **kwargs)
                all_results.extend(results)

            # 중복 제거 및 신뢰도 점수로 정렬
            unique_results = self._deduplicate_results(all_results)
            scored_results = [(r, self.get_confidence_score(query, r)) for r in unique_results]
            scored_results.sort(key=lambda x: x[1], reverse=True)

            return [r for r, score in scored_results if score > 0.3]

        except Exception as e:
            logging.error(f"퍼지 매칭 검색 실패: {e}")
            return []

    def get_confidence_score(self, query: str, result: TMDBAnimeInfo) -> float:
        """퍼지 매칭 신뢰도 점수"""
        query_lower = query.lower().strip()
        title_lower = result.name.lower().strip()
        original_lower = result.original_name.lower().strip()

        # 기본 점수
        score = 0.0

        # 제목 유사도
        title_similarity = self._calculate_similarity(query_lower, title_lower)
        original_similarity = self._calculate_similarity(query_lower, original_lower)
        score = max(title_similarity, original_similarity)

        # 장르 가중치 (애니메이션 장르인 경우)
        if result.genres:
            anime_genre_ids = [16, 10759]  # 애니메이션, 액션&어드벤처
            if any(genre.get("id") in anime_genre_ids for genre in result.genres):
                score += 0.1

        # 인기도 가중치
        if result.popularity > 50:
            score += 0.05

        return min(1.0, score)

    def _generate_search_variations(self, query: str) -> list[str]:
        """검색 쿼리 변형 생성"""
        variations = [query]

        # 괄호 제거
        clean_query = re.sub(r"[\(\)\[\]]", "", query).strip()
        if clean_query != query:
            variations.append(clean_query)

        # 특수문자 제거
        clean_query = re.sub(r"[^\w\s]", "", query).strip()
        if clean_query != query:
            variations.append(clean_query)

        # 숫자 제거
        clean_query = re.sub(r"\d+", "", query).strip()
        if clean_query != query:
            variations.append(clean_query)

        # 공백 정규화
        normalized_query = re.sub(r"\s+", " ", query).strip()
        if normalized_query != query:
            variations.append(normalized_query)

        return list(set(variations))

    def _deduplicate_results(self, results: list[TMDBAnimeInfo]) -> list[TMDBAnimeInfo]:
        """중복 결과 제거"""
        seen_ids = set()
        unique_results = []

        for result in results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                unique_results.append(result)

        return unique_results

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """문자열 유사도 계산 (간단한 Jaccard 유사도)"""
        if not str1 or not str2:
            return 0.0

        words1 = set(str1.split())
        words2 = set(str2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0


class YearBasedStrategy(SearchStrategy):
    """연도 기반 검색 전략"""

    def search(self, tmdb_client: TMDBClient, query: str, **kwargs) -> list[TMDBAnimeInfo]:
        """연도 정보를 활용한 검색"""
        try:
            # 연도 추출
            year = self._extract_year(query)
            if year:
                kwargs["year"] = year

            results = tmdb_client.search_anime(query, **kwargs)
            return [r for r in results if self.get_confidence_score(query, r) > 0.5]

        except Exception as e:
            logging.error(f"연도 기반 검색 실패: {e}")
            return []

    def get_confidence_score(self, query: str, result: TMDBAnimeInfo) -> float:
        """연도 기반 신뢰도 점수"""
        score = 0.5  # 기본 점수

        # 연도 매칭
        query_year = self._extract_year(query)
        if query_year and result.first_air_date:
            try:
                result_year = int(result.first_air_date[:4])
                if abs(query_year - result_year) <= 1:  # 1년 차이까지 허용
                    score += 0.3
                elif abs(query_year - result_year) <= 3:  # 3년 차이까지 허용
                    score += 0.1
            except (ValueError, IndexError):
                pass

        return score

    def _extract_year(self, query: str) -> int | None:
        """쿼리에서 연도 추출"""
        year_pattern = r"\b(19|20)\d{2}\b"
        match = re.search(year_pattern, query)
        if match:
            return int(match.group())
        return None


class SeasonBasedStrategy(SearchStrategy):
    """시즌 기반 검색 전략"""

    def search(self, tmdb_client: TMDBClient, query: str, **kwargs) -> list[TMDBAnimeInfo]:
        """시즌 정보를 활용한 검색"""
        try:
            # 시즌 정보 추출
            season_info = self._extract_season_info(query)
            if season_info:
                # 시즌 정보가 있는 경우 더 정확한 검색
                results = tmdb_client.search_anime(query, **kwargs)
                return [r for r in results if self.get_confidence_score(query, r) > 0.6]

            # 일반 검색
            results = tmdb_client.search_anime(query, **kwargs)
            return [r for r in results if self.get_confidence_score(query, r) > 0.4]

        except Exception as e:
            logging.error(f"시즌 기반 검색 실패: {e}")
            return []

    def get_confidence_score(self, query: str, result: TMDBAnimeInfo) -> float:
        """시즌 기반 신뢰도 점수"""
        score = 0.4  # 기본 점수

        # 시즌 정보 매칭
        season_info = self._extract_season_info(query)
        if (
            season_info
            and result.number_of_seasons
            and result.number_of_seasons >= season_info["number"]
        ):
            score += 0.2

        return score

    def _extract_season_info(self, query: str) -> dict | None:
        """쿼리에서 시즌 정보 추출"""
        # 시즌 1, Season 1, S1 등의 패턴
        season_patterns = [
            r"시즌\s*(\d+)",
            r"season\s*(\d+)",
            r"s(\d+)",
            r"(\d+)기",
        ]

        for pattern in season_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return {"number": int(match.group(1))}

        return None


class SearchStrategyFactory:
    """검색 전략 팩토리"""

    @staticmethod
    def create_strategy(strategy_type: str) -> SearchStrategy:
        """전략 타입에 따른 검색 전략 생성"""
        strategies = {
            "exact": ExactMatchStrategy(),
            "fuzzy": FuzzyMatchStrategy(),
            "year": YearBasedStrategy(),
            "season": SeasonBasedStrategy(),
        }

        return strategies.get(strategy_type, FuzzyMatchStrategy())

    @staticmethod
    def get_all_strategies() -> list[SearchStrategy]:
        """모든 검색 전략 반환"""
        return [
            ExactMatchStrategy(),
            FuzzyMatchStrategy(),
            YearBasedStrategy(),
            SeasonBasedStrategy(),
        ]

    @staticmethod
    def get_strategy_names() -> list[str]:
        """사용 가능한 전략 이름 목록 반환"""
        return ["exact", "fuzzy", "year", "season"]
