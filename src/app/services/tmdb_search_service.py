"""
TMDB 검색 서비스 (리팩토링됨)

TMDB API를 통한 메타데이터 검색, 매칭, 캐싱을 담당하는 서비스입니다.
모듈화된 구조로 리팩토링되어 유지보수성이 향상되었습니다.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID, uuid4

from src.app.events import TypedEventBus
from src.app.services.tmdb_search_matcher import SearchResultMatcher
from src.app.services.tmdb_search_statistics import SearchStatisticsCollector
from src.app.services.tmdb_search_strategies import SearchStrategyFactory
from src.app.tmdb_search_events import (
    TMDBBulkSearchCompletedEvent,
    TMDBBulkSearchProgressEvent,
    TMDBBulkSearchStartedEvent,
    TMDBCacheUpdatedEvent,
    TMDBManualSelectionCompletedEvent,
    TMDBManualSelectionRequestedEvent,
    TMDBMatch,
    TMDBMatchConfidence,
    TMDBMatchFoundEvent,
    TMDBMediaType,
    TMDBSearchCancelledEvent,
    TMDBSearchCompletedEvent,
    TMDBSearchFailedEvent,
    TMDBSearchProgressEvent,
    TMDBSearchQuery,
    TMDBSearchResult,
    TMDBSearchResultsEvent,
    TMDBSearchStartedEvent,
    TMDBSearchStatistics,
    TMDBSearchStatus,
    TMDBSearchType,
)


class ITMDBSearchService(ABC):
    """TMDB 검색 서비스 인터페이스"""

    @abstractmethod
    def search_by_title(
        self, title: str, media_type: TMDBMediaType = TMDBMediaType.TV, year: int | None = None
    ) -> UUID:
        """제목으로 TMDB 검색"""

    @abstractmethod
    def search_for_group(self, group_id: str, group_title: str, auto_match: bool = True) -> UUID:
        """그룹에 대한 TMDB 검색"""

    @abstractmethod
    def bulk_search_groups(self, group_data: dict[str, Any], auto_match: bool = True) -> UUID:
        """그룹들 대량 검색"""

    @abstractmethod
    def get_search_results(self, search_id: UUID) -> list[TMDBSearchResult]:
        """검색 결과 조회"""

    @abstractmethod
    def get_match_for_group(self, group_id: str) -> TMDBMatch | None:
        """그룹의 매칭 결과 조회"""

    @abstractmethod
    def manual_select_match(
        self, search_id: UUID, group_id: str, selected_result: TMDBSearchResult
    ) -> None:
        """수동 매칭 선택"""

    @abstractmethod
    def cancel_search(self, search_id: UUID) -> bool:
        """검색 취소"""

    @abstractmethod
    def clear_cache(self) -> None:
        """캐시 초기화"""

    @abstractmethod
    def get_statistics(self) -> TMDBSearchStatistics:
        """검색 통계 조회"""

    @abstractmethod
    def dispose(self) -> None:
        """서비스 정리"""


class TMDBSearchService(ITMDBSearchService):
    """
    TMDB 검색 서비스 구현 (리팩토링됨)

    TMDBClient를 내부적으로 사용하여 고급 검색 기능 제공.
    GUI에서는 TMDBClient를 직접 사용하는 대신 이 서비스를 사용하는 것을 권장.
    """

    def __init__(self, event_bus: TypedEventBus, tmdb_client: Any | None = None):
        self.event_bus = event_bus
        self.tmdb_client = tmdb_client  # 실제 TMDB 클라이언트 (예: TMDBClient)
        self.logger = logging.getLogger(self.__class__.__name__)

        # TMDBClient가 제공되지 않은 경우 자동 생성
        if self.tmdb_client is None:
            try:
                from src.core.tmdb_client import TMDBClient

                self.tmdb_client = TMDBClient()
                self.logger.info("TMDBClient 자동 생성됨")
            except Exception as e:
                self.logger.error(f"TMDBClient 자동 생성 실패: {e}")
                self.tmdb_client = None

        # 모듈화된 서비스들 초기화
        self.search_strategies = SearchStrategyFactory()
        self.result_matcher = SearchResultMatcher()
        self.statistics_collector = SearchStatisticsCollector()

        # 내부 상태
        self._active_searches: dict[UUID, TMDBSearchQuery] = {}
        self._search_results: dict[UUID, list[TMDBSearchResult]] = {}
        self._group_matches: dict[str, TMDBMatch] = {}
        self._search_cache: dict[str, list[TMDBSearchResult]] = {}
        self._statistics = TMDBSearchStatistics()

        # 검색 설정
        self._max_concurrent_searches = 3
        self._cache_ttl_hours = 24
        self._retry_attempts = 3
        self._rate_limit_delay_ms = 200

        self.logger.info("TMDBSearchService 초기화 완료")

    def search_by_title(
        self, title: str, media_type: TMDBMediaType = TMDBMediaType.TV, year: int | None = None
    ) -> UUID:
        """제목으로 TMDB 검색"""
        search_id = uuid4()

        query = TMDBSearchQuery(
            query_string=title, media_type=media_type, search_type=TMDBSearchType.MANUAL, year=year
        )

        try:
            self.logger.info(f"TMDB 제목 검색 시작: '{title}' (타입: {media_type.value})")

            # 검색 시작 이벤트 발행
            self.event_bus.publish(TMDBSearchStartedEvent(search_id=search_id, query=query))

            self._active_searches[search_id] = query

            # 캐시 확인
            cache_key = self._generate_cache_key(title, media_type, year)
            if cache_key in self._search_cache:
                self.logger.debug(f"캐시에서 검색 결과 반환: {cache_key}")
                results = self._search_cache[cache_key]
                self._handle_search_results(search_id, query, results, from_cache=True)
                return search_id

            # 실제 TMDB API 검색 (비동기로 처리)
            self._perform_tmdb_search(search_id, query)

            return search_id

        except Exception as e:
            self.logger.error(f"TMDB 검색 실패: {title}: {e}")
            self._handle_search_error(search_id, query, str(e))
            return search_id

    def search_for_group(self, group_id: str, group_title: str, auto_match: bool = True) -> UUID:
        """그룹에 대한 TMDB 검색"""
        search_id = uuid4()

        # 그룹 제목에서 검색용 제목 추출
        cleaned_title = self._clean_title_for_search(group_title)

        query = TMDBSearchQuery(
            query_string=cleaned_title,
            media_type=TMDBMediaType.TV,  # 기본적으로 TV 시리즈로 가정
            search_type=TMDBSearchType.AUTOMATIC if auto_match else TMDBSearchType.MANUAL,
        )

        try:
            self.logger.info(f"그룹 TMDB 검색 시작: '{group_title}' -> '{cleaned_title}'")

            # 검색 시작 이벤트 발행
            self.event_bus.publish(
                TMDBSearchStartedEvent(search_id=search_id, query=query, group_id=group_id)
            )

            self._active_searches[search_id] = query

            # 캐시 확인
            cache_key = self._generate_cache_key(cleaned_title, TMDBMediaType.TV)
            if cache_key in self._search_cache:
                results = self._search_cache[cache_key]
                self._handle_search_results(search_id, query, results, from_cache=True)

                # 자동 매칭 시도
                if auto_match:
                    self._attempt_auto_match(search_id, group_id, group_title, results)

                return search_id

            # 실제 TMDB API 검색
            self._perform_tmdb_search(search_id, query, group_id, auto_match)

            return search_id

        except Exception as e:
            self.logger.error(f"그룹 TMDB 검색 실패: {group_title}: {e}")
            self._handle_search_error(search_id, query, str(e))
            return search_id

    def bulk_search_groups(self, group_data: dict[str, Any], auto_match: bool = True) -> UUID:
        """그룹들 대량 검색"""
        bulk_search_id = uuid4()

        try:
            group_ids = list(group_data.keys())
            self.logger.info(f"TMDB 대량 검색 시작: {len(group_ids)}개 그룹")

            # 대량 검색 시작 이벤트 발행
            self.event_bus.publish(
                TMDBBulkSearchStartedEvent(
                    bulk_search_id=bulk_search_id,
                    group_ids=group_ids,
                    total_groups=len(group_ids),
                    search_strategy="sequential",
                )
            )

            # 각 그룹에 대해 순차적으로 검색
            self._perform_bulk_search(bulk_search_id, group_data, auto_match)

            return bulk_search_id

        except Exception as e:
            self.logger.error(f"TMDB 대량 검색 실패: {e}")
            return bulk_search_id

    def get_search_results(self, search_id: UUID) -> list[TMDBSearchResult]:
        """검색 결과 조회"""
        return self._search_results.get(search_id, [])

    def get_match_for_group(self, group_id: str) -> TMDBMatch | None:
        """그룹의 매칭 결과 조회"""
        return self._group_matches.get(group_id)

    def manual_select_match(
        self, search_id: UUID, group_id: str, selected_result: TMDBSearchResult
    ) -> None:
        """수동 매칭 선택"""
        try:
            # 수동 선택된 결과로 매칭 생성
            match = TMDBMatch(
                search_result=selected_result,
                confidence=TMDBMatchConfidence.HIGH,  # 수동 선택은 높은 신뢰도
                confidence_score=0.95,
                match_criteria=["manual_selection"],
            )

            self._group_matches[group_id] = match

            # 매칭 발견 이벤트 발행
            self.event_bus.publish(
                TMDBMatchFoundEvent(
                    search_id=search_id, group_id=group_id, match=match, auto_matched=False
                )
            )

            # 수동 선택 완료 이벤트 발행
            self.event_bus.publish(
                TMDBManualSelectionCompletedEvent(
                    search_id=search_id,
                    group_id=group_id,
                    selected_match=match,
                    user_cancelled=False,
                )
            )

            self.logger.info(f"수동 매칭 완료: {group_id} -> {selected_result.title}")

        except Exception as e:
            self.logger.error(f"수동 매칭 선택 실패: {e}")

    def cancel_search(self, search_id: UUID) -> bool:
        """검색 취소"""
        try:
            if search_id in self._active_searches:
                self._active_searches.pop(search_id)

                # 취소 이벤트 발행
                self.event_bus.publish(
                    TMDBSearchCancelledEvent(
                        search_id=search_id,
                        cancellation_reason="사용자 요청",
                        partial_results=self._search_results.get(search_id, []),
                    )
                )

                # 검색 결과 정리
                self._search_results.pop(search_id, None)

                self.logger.info(f"TMDB 검색 취소됨: {search_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"TMDB 검색 취소 실패: {e}")
            return False

    def clear_cache(self) -> None:
        """캐시 초기화"""
        cache_size = len(self._search_cache)
        self._search_cache.clear()

        # 캐시 업데이트 이벤트 발행
        self.event_bus.publish(
            TMDBCacheUpdatedEvent(
                cache_operation="clear", cache_key="all", cache_size=0, cache_hit_rate=0.0
            )
        )

        self.logger.info(f"TMDB 캐시 초기화됨: {cache_size}개 항목 제거")

    def get_statistics(self) -> TMDBSearchStatistics:
        """검색 통계 조회 (리팩토링됨)"""
        return self.statistics_collector.get_current_statistics()

    def dispose(self) -> None:
        """서비스 정리"""
        # 모든 활성 검색 취소
        for search_id in list(self._active_searches.keys()):
            self.cancel_search(search_id)

        # 캐시 초기화
        self.clear_cache()

        self.logger.info("TMDBSearchService 정리 완료")

    # ===== 헬퍼 메서드 =====

    def _clean_title_for_search(self, title: str) -> str:
        """검색용 제목 정리"""
        # 릴리스 그룹명 제거
        import re

        cleaned = re.sub(r"^\[.*?\]\s*", "", title)

        # 해상도 정보 제거
        cleaned = re.sub(r"\s*\(\d+p\)\s*", "", cleaned)
        cleaned = re.sub(r"\s*\d+p\s*", "", cleaned)

        # 시즌 정보 정리
        cleaned = re.sub(r"\s*[Ss]eason\s*\d+", "", cleaned)
        cleaned = re.sub(r"\s*[Ss]\d+", "", cleaned)

        # 불필요한 공백 제거
        return re.sub(r"\s+", " ", cleaned).strip()

    def _generate_cache_key(
        self, title: str, media_type: TMDBMediaType, year: int | None = None
    ) -> str:
        """캐시 키 생성"""
        key_parts = [title.lower(), media_type.value]
        if year:
            key_parts.append(str(year))
        return "|".join(key_parts)

    def _convert_tmdb_results_to_search_results(self, tmdb_results: list) -> list[TMDBSearchResult]:
        """TMDB 결과를 TMDBSearchResult로 변환"""
        search_results = []

        for tmdb_result in tmdb_results:
            search_result = TMDBSearchResult(
                tmdb_id=tmdb_result.id,
                title=tmdb_result.name,
                original_title=tmdb_result.original_name,
                overview=tmdb_result.overview,
                first_air_date=tmdb_result.first_air_date,
                poster_path=tmdb_result.poster_path,
                backdrop_path=tmdb_result.backdrop_path,
                vote_average=tmdb_result.vote_average,
                vote_count=tmdb_result.vote_count,
                genres=tmdb_result.genres,
                media_type=TMDBMediaType.TV,
            )
            search_results.append(search_result)

        return search_results

    def _perform_tmdb_search(
        self,
        search_id: UUID,
        query: TMDBSearchQuery,
        group_id: str | None = None,
        auto_match: bool = False,
    ) -> None:
        """실제 TMDB API 검색 수행 (리팩토링됨)"""
        try:
            start_time = time.time()

            # 통계 수집기에 검색 시작 기록
            self.statistics_collector.record_search_start(
                str(search_id), query.search_type, query.query_string
            )

            # 진행률 이벤트 발행
            self.event_bus.publish(
                TMDBSearchProgressEvent(
                    search_id=search_id,
                    current_item=1,
                    total_items=1,
                    current_query=query.query_string,
                    status=TMDBSearchStatus.SEARCHING,
                    progress_percent=50,
                )
            )

            # 검색 전략을 사용하여 실제 검색 수행
            if self.tmdb_client:
                # 기본 검색 전략 사용
                strategy = self.search_strategies.create_strategy("fuzzy")
                search_kwargs = {}
                if query.year:
                    search_kwargs["year"] = query.year

                tmdb_results = strategy.search(
                    self.tmdb_client, query.query_string, **search_kwargs
                )

                # TMDB 결과를 TMDBSearchResult로 변환
                results = self._convert_tmdb_results_to_search_results(tmdb_results)
            else:
                # TMDB 클라이언트가 없는 경우 더미 결과 생성
                results = self._create_dummy_search_results(query.query_string)

            (time.time() - start_time) * 1000

            # 통계 수집기에 검색 완료 기록
            self.statistics_collector.record_search_completion(
                str(search_id), TMDBSearchStatus.COMPLETED, len(results)
            )

            # 결과 처리
            self._handle_search_results(search_id, query, results, from_cache=False)

            # 자동 매칭 시도 (그룹 검색인 경우)
            if group_id and auto_match:
                self._attempt_auto_match(search_id, group_id, query.query_string, results)

        except Exception as e:
            self.logger.error(f"TMDB API 검색 실패: {e}")

            # 통계 수집기에 검색 실패 기록
            self.statistics_collector.record_search_completion(
                str(search_id), TMDBSearchStatus.FAILED, error=str(e)
            )

            self._handle_search_error(search_id, query, str(e))

    def _handle_search_results(
        self,
        search_id: UUID,
        query: TMDBSearchQuery,
        results: list[TMDBSearchResult],
        from_cache: bool = False,
    ) -> None:
        """검색 결과 처리"""
        self._search_results[search_id] = results

        # 캐시에 저장 (캐시에서 온 결과가 아닌 경우)
        if not from_cache and query.cache_results:
            cache_key = self._generate_cache_key(query.query_string, query.media_type, query.year)
            self._search_cache[cache_key] = results

            # 캐시 업데이트 이벤트 발행
            self.event_bus.publish(
                TMDBCacheUpdatedEvent(
                    cache_operation="add",
                    cache_key=cache_key,
                    cache_size=len(self._search_cache),
                    cache_hit_rate=self._calculate_cache_hit_rate(),
                )
            )

        if from_cache:
            self._statistics.cached_results += 1

        # 검색 결과 이벤트 발행
        search_duration_ms = 0.0  # 캐시에서 온 경우 0
        self.event_bus.publish(
            TMDBSearchResultsEvent(
                search_id=search_id,
                query=query,
                results=results,
                search_duration_ms=search_duration_ms,
                from_cache=from_cache,
            )
        )

        # 검색 완료 이벤트 발행
        self.event_bus.publish(
            TMDBSearchCompletedEvent(
                search_id=search_id,
                query=query,
                total_results=len(results),
                matches_found=len(results),
                search_duration_ms=search_duration_ms,
                statistics=self.get_statistics(),
            )
        )

        # 활성 검색에서 제거
        self._active_searches.pop(search_id, None)

    def _handle_search_error(
        self, search_id: UUID, query: TMDBSearchQuery, error_message: str
    ) -> None:
        """검색 오류 처리"""
        self._statistics.failed_searches += 1

        # 검색 실패 이벤트 발행
        self.event_bus.publish(
            TMDBSearchFailedEvent(
                search_id=search_id,
                query=query,
                error_type="api_error",
                error_message=error_message,
                retry_count=0,
                max_retries=self._retry_attempts,
            )
        )

        # 활성 검색에서 제거
        self._active_searches.pop(search_id, None)

    def _attempt_auto_match(
        self, search_id: UUID, group_id: str, group_title: str, results: list[TMDBSearchResult]
    ) -> None:
        """자동 매칭 시도 (리팩토링됨)"""
        if not results:
            return

        try:
            # 새로운 매칭 로직을 사용하여 자동 매칭 시도
            # TMDBSearchResult를 TMDBAnimeInfo로 변환 (간단한 변환)
            tmdb_results = []
            for result in results:
                # 간단한 변환 (실제로는 더 정교한 변환이 필요)
                tmdb_result = type(
                    "TMDBAnimeInfo",
                    (),
                    {
                        "id": getattr(result, "tmdb_id", 0),
                        "name": result.title,
                        "original_name": result.original_title,
                        "genres": [],
                        "first_air_date": "",
                        "number_of_seasons": 0,
                        "popularity": 0.0,
                    },
                )()
                tmdb_results.append(tmdb_result)

            # 매칭 수행
            match = self.result_matcher.match_results_to_group(
                group_title, tmdb_results, auto_match=True
            )

            if match and match.confidence != TMDBMatchConfidence.UNCERTAIN:
                # 자동 매칭 성공
                self._group_matches[group_id] = match

                # 통계 수집기에 매칭 결과 기록
                self.statistics_collector.record_match_result(str(search_id), match)

                # 매칭 발견 이벤트 발행
                self.event_bus.publish(
                    TMDBMatchFoundEvent(
                        search_id=search_id, group_id=group_id, match=match, auto_matched=True
                    )
                )

                self.logger.info(
                    f"자동 매칭 성공: {group_id} -> {match.search_result.title} (신뢰도: {match.confidence.value})"
                )
            else:
                # 자동 매칭 실패, 수동 선택 요청
                # 매칭 제안 생성
                suggestions = self.result_matcher.get_match_suggestions(
                    group_title, tmdb_results, max_suggestions=5
                )

                candidate_matches = []
                for tmdb_result, score in suggestions:
                    candidate_match = TMDBMatch(
                        search_result=TMDBSearchResult(
                            tmdb_id=tmdb_result.id,
                            title=tmdb_result.name,
                            original_title=tmdb_result.original_name,
                            media_type=TMDBMediaType.TV,
                        ),
                        confidence=self.result_matcher._score_to_confidence(score),
                        confidence_score=score,
                    )
                    candidate_matches.append(candidate_match)

                self.event_bus.publish(
                    TMDBManualSelectionRequestedEvent(
                        search_id=search_id,
                        group_id=group_id,
                        query=TMDBSearchQuery(query_string=group_title),
                        candidate_matches=candidate_matches,
                        requires_user_input=True,
                    )
                )

                self.logger.info(f"수동 선택 요청: {group_id} (후보: {len(candidate_matches)}개)")

        except Exception as e:
            self.logger.error(f"자동 매칭 실패: {e}")
            # 매칭 실패 시 수동 선택 요청
            self.event_bus.publish(
                TMDBManualSelectionRequestedEvent(
                    search_id=search_id,
                    group_id=group_id,
                    query=TMDBSearchQuery(query_string=group_title),
                    candidate_matches=[],
                    requires_user_input=True,
                )
            )

    def _calculate_match_confidence(
        self, original_title: str, search_result: TMDBSearchResult
    ) -> TMDBMatchConfidence:
        """매칭 신뢰도 계산"""
        # 간단한 제목 유사도 기반 신뢰도 계산
        original_lower = original_title.lower()
        result_title_lower = search_result.title.lower()
        result_original_lower = search_result.original_title.lower()

        # 정확한 매칭
        if original_lower in (result_title_lower, result_original_lower):
            return TMDBMatchConfidence.EXACT

        # 포함 관계 확인
        if (
            original_lower in result_title_lower
            or result_title_lower in original_lower
            or original_lower in result_original_lower
            or result_original_lower in original_lower
        ):
            return TMDBMatchConfidence.HIGH

        # 단어 기반 유사도 (간단한 구현)
        original_words = set(original_lower.split())
        result_words = set(result_title_lower.split())

        if original_words and result_words:
            similarity = len(original_words & result_words) / len(original_words | result_words)

            if similarity >= 0.8:
                return TMDBMatchConfidence.HIGH
            if similarity >= 0.6:
                return TMDBMatchConfidence.MEDIUM
            if similarity >= 0.4:
                return TMDBMatchConfidence.LOW

        return TMDBMatchConfidence.UNCERTAIN

    def _perform_bulk_search(
        self, bulk_search_id: UUID, group_data: dict[str, Any], auto_match: bool
    ) -> None:
        """대량 검색 수행"""
        try:
            start_time = time.time()
            completed_groups = 0
            failed_groups = 0
            manual_selections_required = 0

            for i, (group_id, group_info) in enumerate(group_data.items()):
                try:
                    # 진행률 이벤트 발행
                    progress_percent = int((i / len(group_data)) * 100)
                    self.event_bus.publish(
                        TMDBBulkSearchProgressEvent(
                            bulk_search_id=bulk_search_id,
                            current_group=i + 1,
                            total_groups=len(group_data),
                            current_group_id=group_id,
                            completed_groups=completed_groups,
                            failed_groups=failed_groups,
                            progress_percent=progress_percent,
                        )
                    )

                    # 개별 그룹 검색
                    group_title = group_info.get("title", group_id)
                    self.search_for_group(group_id, group_title, auto_match)

                    # 잠시 대기 (API 레이트 리미트 방지)
                    time.sleep(self._rate_limit_delay_ms / 1000.0)

                    completed_groups += 1

                except Exception as e:
                    self.logger.error(f"그룹 검색 실패: {group_id}: {e}")
                    failed_groups += 1

            bulk_search_duration_ms = (time.time() - start_time) * 1000

            # 대량 검색 완료 이벤트 발행
            self.event_bus.publish(
                TMDBBulkSearchCompletedEvent(
                    bulk_search_id=bulk_search_id,
                    total_groups=len(group_data),
                    successful_matches=completed_groups,
                    failed_searches=failed_groups,
                    manual_selections_required=manual_selections_required,
                    bulk_search_duration_ms=bulk_search_duration_ms,
                    statistics=self.get_statistics(),
                )
            )

            self.logger.info(f"대량 검색 완료: {completed_groups}개 성공, {failed_groups}개 실패")

        except Exception as e:
            self.logger.error(f"대량 검색 실패: {e}")

    def _create_dummy_search_results(self, query: str) -> list[TMDBSearchResult]:
        """더미 검색 결과 생성 (실제 TMDB API 연동 전 테스트용)"""
        return [
            TMDBSearchResult(
                tmdb_id=12345,
                title=f"{query} (TV Series)",
                original_title=query,
                media_type=TMDBMediaType.TV,
                release_date="2020-01-01",
                overview=f"This is a dummy overview for {query}",
                vote_average=8.5,
                vote_count=1000,
                genres=["Animation", "Comedy"],
                number_of_seasons=3,
                number_of_episodes=36,
            ),
            TMDBSearchResult(
                tmdb_id=12346,
                title=f"{query} Movie",
                original_title=f"{query} 映画",
                media_type=TMDBMediaType.MOVIE,
                release_date="2021-07-15",
                overview=f"Movie adaptation of {query}",
                vote_average=7.8,
                vote_count=500,
                genres=["Animation", "Adventure"],
                runtime=120,
            ),
        ]

    def _calculate_cache_hit_rate(self) -> float:
        """캐시 히트율 계산"""
        if self._statistics.total_searches > 0:
            return self._statistics.cached_results / self._statistics.total_searches
        return 0.0
