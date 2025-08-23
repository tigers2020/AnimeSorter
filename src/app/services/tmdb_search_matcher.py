"""
TMDB 검색 결과 매칭 모듈

검색 결과와 미디어 파일을 매칭하고 신뢰도 점수를 계산합니다.
"""

import logging
import re
from typing import Any, Optional

from core.tmdb_models import TMDBAnimeInfo

from ..tmdb_search_events import TMDBMatch, TMDBMatchConfidence


class SearchResultMatcher:
    """검색 결과 매칭 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def match_results_to_group(
        self, group_title: str, search_results: list[TMDBAnimeInfo], auto_match: bool = True
    ) -> Optional[TMDBMatch]:
        """검색 결과를 그룹에 매칭"""
        if not search_results:
            return None

        if auto_match:
            return self._auto_match(group_title, search_results)
        else:
            return self._manual_match(group_title, search_results)

    def _auto_match(
        self, group_title: str, search_results: list[TMDBAnimeInfo]
    ) -> Optional[TMDBMatch]:
        """자동 매칭 수행"""
        try:
            # 각 결과에 대한 신뢰도 점수 계산
            scored_results = []
            for result in search_results:
                score = self._calculate_match_score(group_title, result)
                scored_results.append((result, score))

            # 점수로 정렬
            scored_results.sort(key=lambda x: x[1], reverse=True)

            # 최고 점수 결과 선택
            if scored_results and scored_results[0][1] > 0.6:
                best_result, best_score = scored_results[0]
                confidence = self._score_to_confidence(best_score)

                return TMDBMatch(
                    group_id="",  # 그룹 ID는 호출자가 설정
                    tmdb_id=best_result.id,
                    title=best_result.name,
                    original_title=best_result.original_name,
                    confidence=confidence,
                    score=best_score,
                    metadata=best_result,
                )

        except Exception as e:
            self.logger.error(f"자동 매칭 실패: {e}")

        return None

    def _manual_match(
        self, group_title: str, search_results: list[TMDBAnimeInfo]
    ) -> Optional[TMDBMatch]:
        """수동 매칭을 위한 정보 제공"""
        # 수동 매칭의 경우 모든 결과를 반환하되, 점수 정보 포함
        if search_results:
            best_result = search_results[0]  # 첫 번째 결과를 기본값으로
            score = self._calculate_match_score(group_title, best_result)
            confidence = self._score_to_confidence(score)

            return TMDBMatch(
                group_id="",  # 그룹 ID는 호출자가 설정
                tmdb_id=best_result.id,
                title=best_result.name,
                original_title=best_result.original_name,
                confidence=confidence,
                score=score,
                metadata=best_result,
            )

        return None

    def _calculate_match_score(self, group_title: str, result: TMDBAnimeInfo) -> float:
        """매칭 점수 계산"""
        score = 0.0

        # 제목 매칭 점수
        title_score = self._calculate_title_similarity(group_title, result.name)
        original_score = self._calculate_title_similarity(group_title, result.original_name)
        score += max(title_score, original_score) * 0.6

        # 장르 점수
        genre_score = self._calculate_genre_score(result.genres)
        score += genre_score * 0.2

        # 연도 점수
        year_score = self._calculate_year_score(group_title, result.first_air_date)
        score += year_score * 0.1

        # 시즌 점수
        season_score = self._calculate_season_score(group_title, result.number_of_seasons)
        score += season_score * 0.1

        return min(1.0, score)

    def _calculate_title_similarity(self, group_title: str, tmdb_title: str) -> float:
        """제목 유사도 계산"""
        if not group_title or not tmdb_title:
            return 0.0

        group_lower = group_title.lower().strip()
        tmdb_lower = tmdb_title.lower().strip()

        # 완전 일치
        if group_lower == tmdb_lower:
            return 1.0

        # 부분 일치
        if group_lower in tmdb_lower or tmdb_lower in group_lower:
            return 0.9

        # 단어 단위 유사도
        group_words = set(re.findall(r"\w+", group_lower))
        tmdb_words = set(re.findall(r"\w+", tmdb_lower))

        if not group_words or not tmdb_words:
            return 0.0

        intersection = len(group_words.intersection(tmdb_words))
        union = len(group_words.union(tmdb_words))

        return intersection / union if union > 0 else 0.0

    def _calculate_genre_score(self, genres: list[dict[str, Any]]) -> float:
        """장르 점수 계산"""
        if not genres:
            return 0.0

        # 애니메이션 관련 장르 ID
        anime_genre_ids = [16, 10759, 10762, 10765]  # 애니메이션, 액션&어드벤처, 키즈, Sci-Fi&Fantasy

        for genre in genres:
            if genre.get("id") in anime_genre_ids:
                return 1.0

        return 0.0

    def _calculate_year_score(self, group_title: str, first_air_date: str) -> float:
        """연도 매칭 점수 계산"""
        if not first_air_date:
            return 0.0

        try:
            # 그룹 제목에서 연도 추출
            year_pattern = r"\b(19|20)\d{2}\b"
            year_match = re.search(year_pattern, group_title)

            if year_match:
                group_year = int(year_match.group())
                tmdb_year = int(first_air_date[:4])

                # 연도 차이에 따른 점수
                year_diff = abs(group_year - tmdb_year)
                if year_diff == 0:
                    return 1.0
                elif year_diff == 1:
                    return 0.8
                elif year_diff <= 3:
                    return 0.6
                elif year_diff <= 5:
                    return 0.4
                else:
                    return 0.2

        except (ValueError, IndexError):
            pass

        return 0.0

    def _calculate_season_score(self, group_title: str, number_of_seasons: int) -> float:
        """시즌 매칭 점수 계산"""
        if not number_of_seasons:
            return 0.0

        try:
            # 그룹 제목에서 시즌 정보 추출
            season_patterns = [
                r"시즌\s*(\d+)",
                r"season\s*(\d+)",
                r"s(\d+)",
                r"(\d+)기",
            ]

            for pattern in season_patterns:
                match = re.search(pattern, group_title, re.IGNORECASE)
                if match:
                    group_season = int(match.group(1))

                    # 시즌 수 매칭
                    if group_season <= number_of_seasons:
                        return 1.0
                    else:
                        return 0.5

        except (ValueError, IndexError):
            pass

        return 0.0

    def _score_to_confidence(self, score: float) -> TMDBMatchConfidence:
        """점수를 신뢰도로 변환"""
        if score >= 0.9:
            return TMDBMatchConfidence.HIGH
        elif score >= 0.7:
            return TMDBMatchConfidence.MEDIUM
        elif score >= 0.5:
            return TMDBMatchConfidence.LOW
        else:
            return TMDBMatchConfidence.NONE

    def get_match_suggestions(
        self, group_title: str, search_results: list[TMDBAnimeInfo], max_suggestions: int = 5
    ) -> list[tuple[TMDBAnimeInfo, float]]:
        """매칭 제안 목록 반환"""
        try:
            # 각 결과에 대한 점수 계산
            scored_results = []
            for result in search_results:
                score = self._calculate_match_score(group_title, result)
                scored_results.append((result, score))

            # 점수로 정렬
            scored_results.sort(key=lambda x: x[1], reverse=True)

            # 상위 결과 반환
            return scored_results[:max_suggestions]

        except Exception as e:
            self.logger.error(f"매칭 제안 생성 실패: {e}")
            return []

    def validate_match(self, group_title: str, match: TMDBMatch) -> bool:
        """매칭 결과 검증"""
        try:
            # 최소 신뢰도 확인
            if match.confidence == TMDBMatchConfidence.NONE:
                return False

            # 점수 확인
            if match.score < 0.3:
                return False

            # 제목 유사도 재확인
            title_similarity = self._calculate_title_similarity(group_title, match.title)
            if title_similarity < 0.2:
                return False

            return True

        except Exception as e:
            self.logger.error(f"매칭 검증 실패: {e}")
            return False

    def get_match_statistics(self, matches: list[TMDBMatch]) -> dict[str, Any]:
        """매칭 통계 정보 반환"""
        try:
            if not matches:
                return {
                    "total_matches": 0,
                    "confidence_distribution": {},
                    "average_score": 0.0,
                    "score_distribution": {},
                }

            # 신뢰도 분포
            confidence_dist = {}
            for match in matches:
                confidence = match.confidence.value
                confidence_dist[confidence] = confidence_dist.get(confidence, 0) + 1

            # 점수 분포
            score_dist = {"0.0-0.3": 0, "0.3-0.5": 0, "0.5-0.7": 0, "0.7-0.9": 0, "0.9-1.0": 0}
            total_score = 0.0

            for match in matches:
                total_score += match.score

                if match.score < 0.3:
                    score_dist["0.0-0.3"] += 1
                elif match.score < 0.5:
                    score_dist["0.3-0.5"] += 1
                elif match.score < 0.7:
                    score_dist["0.5-0.7"] += 1
                elif match.score < 0.9:
                    score_dist["0.7-0.9"] += 1
                else:
                    score_dist["0.9-1.0"] += 1

            return {
                "total_matches": len(matches),
                "confidence_distribution": confidence_dist,
                "average_score": total_score / len(matches) if matches else 0.0,
                "score_distribution": score_dist,
            }

        except Exception as e:
            self.logger.error(f"매칭 통계 생성 실패: {e}")
            return {"error": str(e)}
