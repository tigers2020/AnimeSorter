"""
TMDB 검색 관련 이벤트 정의

TMDB API를 통한 메타데이터 검색, 매칭, 캐싱 과정의 이벤트를 정의합니다.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from .events import BaseEvent


class TMDBSearchStatus(Enum):
    """TMDB 검색 상태"""

    IDLE = "idle"
    SEARCHING = "searching"
    MATCHING = "matching"
    CACHING = "caching"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TMDBMediaType(Enum):
    """TMDB 미디어 타입"""

    TV = "tv"
    MOVIE = "movie"
    ANIME = "anime"
    UNKNOWN = "unknown"


class TMDBSearchType(Enum):
    """TMDB 검색 타입"""

    AUTOMATIC = "automatic"  # 자동 검색
    MANUAL = "manual"  # 수동 검색
    BULK_SEARCH = "bulk_search"  # 대량 검색
    SINGLE_MATCH = "single_match"  # 단일 매칭


class TMDBMatchConfidence(Enum):
    """TMDB 매칭 신뢰도"""

    EXACT = "exact"  # 정확한 매칭 (100%)
    HIGH = "high"  # 높은 신뢰도 (80-99%)
    MEDIUM = "medium"  # 중간 신뢰도 (60-79%)
    LOW = "low"  # 낮은 신뢰도 (40-59%)
    UNCERTAIN = "uncertain"  # 불확실 (0-39%)


@dataclass
class TMDBSearchResult:
    """TMDB 검색 결과"""

    tmdb_id: int
    title: str
    original_title: str
    media_type: TMDBMediaType
    release_date: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    vote_average: float = 0.0
    vote_count: int = 0
    genres: list[str] = field(default_factory=list)
    runtime: int | None = None
    status: str | None = None
    # TV 시리즈 전용 필드
    number_of_seasons: int | None = None
    number_of_episodes: int | None = None
    episode_run_time: list[int] = field(default_factory=list)
    first_air_date: str | None = None
    last_air_date: str | None = None
    # 추가 메타데이터
    external_ids: dict[str, Any] = field(default_factory=dict)
    alternative_titles: list[str] = field(default_factory=list)


@dataclass
class TMDBMatch:
    """TMDB 매칭 결과"""

    search_result: TMDBSearchResult
    confidence: TMDBMatchConfidence
    confidence_score: float  # 0.0 - 1.0
    match_criteria: list[str] = field(default_factory=list)  # 매칭에 사용된 기준들
    alternative_matches: list["TMDBMatch"] = field(default_factory=list)


@dataclass
class TMDBSearchQuery:
    """TMDB 검색 쿼리"""

    query_string: str
    media_type: TMDBMediaType = TMDBMediaType.TV
    search_type: TMDBSearchType = TMDBSearchType.AUTOMATIC
    year: int | None = None
    language: str = "ko-KR"
    include_adult: bool = False
    # 검색 옵션
    use_fuzzy_matching: bool = True
    max_results: int = 20
    cache_results: bool = True


@dataclass
class TMDBSearchStatistics:
    """TMDB 검색 통계"""

    total_searches: int = 0
    successful_searches: int = 0
    failed_searches: int = 0
    cached_results: int = 0
    api_calls_count: int = 0
    average_search_time_ms: float = 0.0
    cache_hit_rate: float = 0.0  # 캐시 히트율


# ===== 이벤트 정의 =====


@dataclass
class TMDBSearchStartedEvent(BaseEvent):
    """TMDB 검색 시작 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    query: TMDBSearchQuery = field(default_factory=TMDBSearchQuery)
    group_id: str | None = None  # 그룹 단위 검색 시


@dataclass
class TMDBSearchProgressEvent(BaseEvent):
    """TMDB 검색 진행률 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    current_item: int = 0
    total_items: int = 0
    current_query: str = ""
    status: TMDBSearchStatus = TMDBSearchStatus.SEARCHING
    progress_percent: int = 0


@dataclass
class TMDBSearchResultsEvent(BaseEvent):
    """TMDB 검색 결과 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    query: TMDBSearchQuery = field(default_factory=TMDBSearchQuery)
    results: list[TMDBSearchResult] = field(default_factory=list)
    search_duration_ms: float = 0.0
    from_cache: bool = False


@dataclass
class TMDBMatchFoundEvent(BaseEvent):
    """TMDB 매칭 발견 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    group_id: str | None = None
    match: TMDBMatch = field(
        default_factory=lambda: TMDBMatch(
            search_result=TMDBSearchResult(
                tmdb_id=0, title="", original_title="", media_type=TMDBMediaType.UNKNOWN
            ),
            confidence=TMDBMatchConfidence.UNCERTAIN,
            confidence_score=0.0,
        )
    )
    auto_matched: bool = False  # 자동 매칭 여부


@dataclass
class TMDBMatchNotFoundEvent(BaseEvent):
    """TMDB 매칭 실패 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    group_id: str | None = None
    query: TMDBSearchQuery = field(default_factory=TMDBSearchQuery)
    search_duration_ms: float = 0.0
    failure_reason: str = "no_matches"
    alternative_suggestions: list[str] = field(default_factory=list)


@dataclass
class TMDBSearchCompletedEvent(BaseEvent):
    """TMDB 검색 완료 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    query: TMDBSearchQuery = field(default_factory=TMDBSearchQuery)
    total_results: int = 0
    matches_found: int = 0
    search_duration_ms: float = 0.0
    statistics: TMDBSearchStatistics = field(default_factory=TMDBSearchStatistics)


@dataclass
class TMDBSearchFailedEvent(BaseEvent):
    """TMDB 검색 실패 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    query: TMDBSearchQuery = field(default_factory=TMDBSearchQuery)
    error_type: str = "unknown_error"
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TMDBSearchCancelledEvent(BaseEvent):
    """TMDB 검색 취소 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    cancellation_reason: str = "사용자 요청"
    partial_results: list[TMDBSearchResult] = field(default_factory=list)


@dataclass
class TMDBCacheUpdatedEvent(BaseEvent):
    """TMDB 캐시 업데이트 이벤트"""

    cache_operation: str = "add"  # "add", "remove", "clear", "update"
    cache_key: str = ""
    cache_size: int = 0
    cache_hit_rate: float = 0.0


@dataclass
class TMDBRateLimitEvent(BaseEvent):
    """TMDB API 레이트 리미트 이벤트"""

    remaining_requests: int = 0
    reset_time: float = 0.0  # Unix timestamp
    retry_after_seconds: int = 0


@dataclass
class TMDBManualSelectionRequestedEvent(BaseEvent):
    """TMDB 수동 선택 요청 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    group_id: str | None = None
    query: TMDBSearchQuery = field(default_factory=TMDBSearchQuery)
    candidate_matches: list[TMDBMatch] = field(default_factory=list)
    requires_user_input: bool = True


@dataclass
class TMDBManualSelectionCompletedEvent(BaseEvent):
    """TMDB 수동 선택 완료 이벤트"""

    search_id: UUID = field(default_factory=uuid4)
    group_id: str | None = None
    selected_match: TMDBMatch | None = None
    user_cancelled: bool = False


@dataclass
class TMDBBulkSearchStartedEvent(BaseEvent):
    """TMDB 대량 검색 시작 이벤트"""

    bulk_search_id: UUID = field(default_factory=uuid4)
    group_ids: list[str] = field(default_factory=list)
    total_groups: int = 0
    search_strategy: str = "sequential"  # "sequential", "parallel"


@dataclass
class TMDBBulkSearchProgressEvent(BaseEvent):
    """TMDB 대량 검색 진행률 이벤트"""

    bulk_search_id: UUID = field(default_factory=uuid4)
    current_group: int = 0
    total_groups: int = 0
    current_group_id: str = ""
    completed_groups: int = 0
    failed_groups: int = 0
    progress_percent: int = 0


@dataclass
class TMDBBulkSearchCompletedEvent(BaseEvent):
    """TMDB 대량 검색 완료 이벤트"""

    bulk_search_id: UUID = field(default_factory=uuid4)
    total_groups: int = 0
    successful_matches: int = 0
    failed_searches: int = 0
    manual_selections_required: int = 0
    bulk_search_duration_ms: float = 0.0
    statistics: TMDBSearchStatistics = field(default_factory=TMDBSearchStatistics)


# Export all events
__all__ = [
    # Enums
    "TMDBSearchStatus",
    "TMDBMediaType",
    "TMDBSearchType",
    "TMDBMatchConfidence",
    # Data classes
    "TMDBSearchResult",
    "TMDBMatch",
    "TMDBSearchQuery",
    "TMDBSearchStatistics",
    # Events
    "TMDBSearchStartedEvent",
    "TMDBSearchProgressEvent",
    "TMDBSearchResultsEvent",
    "TMDBMatchFoundEvent",
    "TMDBMatchNotFoundEvent",
    "TMDBSearchCompletedEvent",
    "TMDBSearchFailedEvent",
    "TMDBSearchCancelledEvent",
    "TMDBCacheUpdatedEvent",
    "TMDBRateLimitEvent",
    "TMDBManualSelectionRequestedEvent",
    "TMDBManualSelectionCompletedEvent",
    "TMDBBulkSearchStartedEvent",
    "TMDBBulkSearchProgressEvent",
    "TMDBBulkSearchCompletedEvent",
]
