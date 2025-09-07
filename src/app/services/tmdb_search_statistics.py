"""
TMDB 검색 통계 모듈

검색 성능과 결과에 대한 통계 정보를 수집하고 분석합니다.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from src.app.tmdb_search_events import (TMDBMatch, TMDBMatchConfidence,
                                  TMDBSearchStatistics, TMDBSearchStatus,
                                  TMDBSearchType)


class SearchStatisticsCollector:
    """검색 통계 수집기"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 검색 통계 데이터
        self._search_history: list[dict[str, Any]] = []
        self._match_history: list[dict[str, Any]] = []
        self._performance_metrics: dict[str, list[float]] = defaultdict(list)

        # 실시간 통계
        self._current_stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0,
            "total_matches": 0,
            "high_confidence_matches": 0,
            "medium_confidence_matches": 0,
            "low_confidence_matches": 0,
            "no_confidence_matches": 0,
        }

    def record_search_start(self, search_id: str, search_type: TMDBSearchType, query: str) -> None:
        """검색 시작 기록"""
        try:
            search_record = {
                "search_id": search_id,
                "search_type": search_type.value,
                "query": query,
                "start_time": time.time(),
                "start_datetime": datetime.now(),
                "status": TMDBSearchStatus.SEARCHING.value,
                "results_count": 0,
                "match_found": False,
                "confidence": None,
                "score": 0.0,
                "duration": 0.0,
                "error": None,
            }

            self._search_history.append(search_record)
            self._current_stats["total_searches"] += 1

        except Exception as e:
            self.logger.error(f"검색 시작 기록 실패: {e}")

    def record_search_completion(
        self,
        search_id: str,
        status: TMDBSearchStatus,
        results_count: int = 0,
        error: str | None = None,
    ) -> None:
        """검색 완료 기록"""
        try:
            # 해당 검색 기록 찾기
            for record in self._search_history:
                if record["search_id"] == search_id:
                    record["status"] = status.value
                    record["results_count"] = results_count
                    record["error"] = error

                    # 성공/실패 통계 업데이트
                    if status == TMDBSearchStatus.COMPLETED:
                        self._current_stats["successful_searches"] += 1
                    elif status == TMDBSearchStatus.FAILED:
                        self._current_stats["failed_searches"] += 1

                    # 성능 메트릭 기록
                    if record["start_time"]:
                        duration = time.time() - record["start_time"]
                        record["duration"] = duration
                        self._performance_metrics["search_duration"].append(duration)

                    break

        except Exception as e:
            self.logger.error(f"검색 완료 기록 실패: {e}")

    def record_match_result(self, search_id: str, match: TMDBMatch | None) -> None:
        """매칭 결과 기록"""
        try:
            # 검색 기록에 매칭 정보 추가
            for record in self._search_history:
                if record["search_id"] == search_id:
                    if match:
                        record["match_found"] = True
                        record["confidence"] = match.confidence.value
                        record["score"] = match.confidence_score

                        # 매칭 통계 업데이트
                        self._current_stats["total_matches"] += 1

                        if match.confidence == TMDBMatchConfidence.HIGH:
                            self._current_stats["high_confidence_matches"] += 1
                        elif match.confidence == TMDBMatchConfidence.MEDIUM:
                            self._current_stats["medium_confidence_matches"] += 1
                        elif match.confidence == TMDBMatchConfidence.LOW:
                            self._current_stats["low_confidence_matches"] += 1
                        else:
                            self._current_stats["no_confidence_matches"] += 1
                    else:
                        record["match_found"] = False
                        record["confidence"] = TMDBMatchConfidence.UNCERTAIN.value
                        record["score"] = 0.0
                    break

            # 매칭 히스토리에 추가
            if match:
                match_record = {
                    "search_id": search_id,
                    "timestamp": time.time(),
                    "datetime": datetime.now(),
                    "group_id": str(
                        match.search_result.tmdb_id
                    ),  # group_id는 없으므로 tmdb_id 사용
                    "tmdb_id": match.search_result.tmdb_id,
                    "title": match.search_result.title,
                    "confidence": match.confidence.value,
                    "score": match.confidence_score,
                }
                self._match_history.append(match_record)

        except Exception as e:
            self.logger.error(f"매칭 결과 기록 실패: {e}")

    def get_current_statistics(self) -> TMDBSearchStatistics:
        """현재 통계 정보 반환"""
        try:
            # 성능 메트릭 계산
            avg_search_duration = 0.0
            if self._performance_metrics["search_duration"]:
                avg_search_duration = sum(self._performance_metrics["search_duration"]) / len(
                    self._performance_metrics["search_duration"]
                )

            # 성공률 계산
            success_rate = 0.0
            if self._current_stats["total_searches"] > 0:
                success_rate = (
                    self._current_stats["successful_searches"]
                    / self._current_stats["total_searches"]
                ) * 100

            # 매칭 성공률 계산
            match_rate = 0.0
            if self._current_stats["successful_searches"] > 0:
                match_rate = (
                    self._current_stats["total_matches"]
                    / self._current_stats["successful_searches"]
                ) * 100

            return TMDBSearchStatistics(
                total_searches=self._current_stats["total_searches"],
                successful_searches=self._current_stats["successful_searches"],
                failed_searches=self._current_stats["failed_searches"],
                cached_results=self._current_stats.get("cached_results", 0),
                api_calls_count=self._current_stats.get("api_calls_count", 0),
                average_search_time_ms=avg_search_duration * 1000,  # 초를 밀리초로 변환
                cache_hit_rate=self._current_stats.get("cache_hit_rate", 0.0),
            )

        except Exception as e:
            self.logger.error(f"통계 정보 생성 실패: {e}")
            return TMDBSearchStatistics()

    def get_search_history(
        self, days: int = 7, search_type: TMDBSearchType | None = None
    ) -> list[dict[str, Any]]:
        """검색 히스토리 반환"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)

            filtered_history = []
            for record in self._search_history:
                if record["start_time"] >= cutoff_time:
                    if search_type is None or record["search_type"] == search_type.value:
                        filtered_history.append(record.copy())

            return filtered_history

        except Exception as e:
            self.logger.error(f"검색 히스토리 조회 실패: {e}")
            return []

    def get_match_history(
        self, days: int = 7, min_confidence: TMDBMatchConfidence | None = None
    ) -> list[dict[str, Any]]:
        """매칭 히스토리 반환"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)

            filtered_history = []
            for record in self._match_history:
                if record["timestamp"] >= cutoff_time:
                    if min_confidence is None or record["confidence"] >= min_confidence.value:
                        filtered_history.append(record.copy())

            return filtered_history

        except Exception as e:
            self.logger.error(f"매칭 히스토리 조회 실패: {e}")
            return []

    def get_performance_metrics(self, metric_name: str = "search_duration") -> dict[str, Any]:
        """성능 메트릭 반환"""
        try:
            if metric_name not in self._performance_metrics:
                return {"error": f"Unknown metric: {metric_name}"}

            values = self._performance_metrics[metric_name]
            if not values:
                return {"count": 0, "average": 0.0, "min": 0.0, "max": 0.0}

            return {
                "count": len(values),
                "average": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "recent_values": values[-10:],  # 최근 10개 값
            }

        except Exception as e:
            self.logger.error(f"성능 메트릭 조회 실패: {e}")
            return {"error": str(e)}

    def get_search_type_statistics(self) -> dict[str, dict[str, Any]]:
        """검색 타입별 통계"""
        try:
            type_stats: dict[str, dict[str, Any]] = defaultdict(
                lambda: {
                    "count": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_duration": 0.0,
                    "total_results": 0,
                    "matches_found": 0,
                }
            )

            for record in self._search_history:
                search_type = record["search_type"]
                type_stats[search_type]["count"] += 1

                if record["status"] == TMDBSearchStatus.COMPLETED.value:
                    type_stats[search_type]["successful"] += 1
                elif record["status"] == TMDBSearchStatus.FAILED.value:
                    type_stats[search_type]["failed"] += 1

                type_stats[search_type]["total_duration"] += record.get("duration", 0.0)
                type_stats[search_type]["total_results"] += record.get("results_count", 0)

                if record.get("match_found", False):
                    type_stats[search_type]["matches_found"] += 1

            # 평균 계산
            for stats in type_stats.values():
                if stats["count"] > 0:
                    stats["success_rate"] = (stats["successful"] / stats["count"]) * 100
                    stats["average_duration"] = stats["total_duration"] / stats["count"]
                    stats["average_results"] = stats["total_results"] / stats["count"]
                    stats["match_rate"] = (
                        (stats["matches_found"] / stats["successful"]) * 100
                        if stats["successful"] > 0
                        else 0.0
                    )

            return dict(type_stats)

        except Exception as e:
            self.logger.error(f"검색 타입별 통계 생성 실패: {e}")
            return {}

    def get_confidence_distribution(self, days: int = 7) -> dict[str, int]:
        """신뢰도 분포 통계"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)

            confidence_dist: dict[str, int] = defaultdict(int)
            for record in self._match_history:
                if record["timestamp"] >= cutoff_time:
                    confidence = record["confidence"]
                    confidence_dist[confidence] += 1

            return dict(confidence_dist)

        except Exception as e:
            self.logger.error(f"신뢰도 분포 통계 생성 실패: {e}")
            return {}

    def get_score_distribution(self, days: int = 7) -> dict[str, int]:
        """점수 분포 통계"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)

            score_dist = {"0.0-0.3": 0, "0.3-0.5": 0, "0.5-0.7": 0, "0.7-0.9": 0, "0.9-1.0": 0}

            for record in self._match_history:
                if record["timestamp"] >= cutoff_time:
                    score = record["score"]
                    if score < 0.3:
                        score_dist["0.0-0.3"] += 1
                    elif score < 0.5:
                        score_dist["0.3-0.5"] += 1
                    elif score < 0.7:
                        score_dist["0.5-0.7"] += 1
                    elif score < 0.9:
                        score_dist["0.7-0.9"] += 1
                    else:
                        score_dist["0.9-1.0"] += 1

            return score_dist

        except Exception as e:
            self.logger.error(f"점수 분포 통계 생성 실패: {e}")
            return {}

    def clear_old_data(self, days: int = 30) -> int:
        """오래된 데이터 정리"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)

            # 검색 히스토리 정리
            initial_search_count = len(self._search_history)
            self._search_history = [
                r for r in self._search_history if r["start_time"] >= cutoff_time
            ]
            search_cleaned = initial_search_count - len(self._search_history)

            # 매칭 히스토리 정리
            initial_match_count = len(self._match_history)
            self._match_history = [r for r in self._match_history if r["timestamp"] >= cutoff_time]
            match_cleaned = initial_match_count - len(self._match_history)

            # 성능 메트릭 정리 (최근 100개만 유지)
            for metric_name in self._performance_metrics:
                if len(self._performance_metrics[metric_name]) > 100:
                    self._performance_metrics[metric_name] = self._performance_metrics[metric_name][
                        -100:
                    ]

            total_cleaned = search_cleaned + match_cleaned
            self.logger.info(
                f"오래된 데이터 정리 완료: 검색 {search_cleaned}개, 매칭 {match_cleaned}개"
            )

            return total_cleaned

        except Exception as e:
            self.logger.error(f"오래된 데이터 정리 실패: {e}")
            return 0

    def reset_statistics(self) -> None:
        """통계 초기화"""
        try:
            self._search_history.clear()
            self._match_history.clear()
            self._performance_metrics.clear()

            # 현재 통계 초기화
            for key in self._current_stats:
                self._current_stats[key] = 0

            self.logger.info("검색 통계가 초기화되었습니다.")

        except Exception as e:
            self.logger.error(f"통계 초기화 실패: {e}")

    def export_statistics(self, format: str = "json") -> dict[str, Any]:
        """통계 데이터 내보내기"""
        try:
            return {
                "current_statistics": self.get_current_statistics().__dict__,
                "search_type_statistics": self.get_search_type_statistics(),
                "confidence_distribution": self.get_confidence_distribution(),
                "score_distribution": self.get_score_distribution(),
                "performance_metrics": dict(self._performance_metrics),
                "export_timestamp": datetime.now().isoformat(),
                "data_summary": {
                    "total_search_records": len(self._search_history),
                    "total_match_records": len(self._match_history),
                    "oldest_search": (
                        min([r["start_datetime"] for r in self._search_history])
                        if self._search_history
                        else None
                    ),
                    "newest_search": (
                        max([r["start_datetime"] for r in self._search_history])
                        if self._search_history
                        else None
                    ),
                },
            }

        except Exception as e:
            self.logger.error(f"통계 데이터 내보내기 실패: {e}")
            return {"error": str(e)}
