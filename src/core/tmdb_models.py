"""
TMDB 데이터 모델

TMDB API 응답을 위한 데이터 클래스들을 정의합니다.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class TMDBAnimeInfo:
    """TMDB 애니메이션 정보"""

    id: int
    name: str
    original_name: str
    overview: str
    first_air_date: str
    last_air_date: str
    number_of_seasons: int
    number_of_episodes: int
    status: str
    type: str
    popularity: float
    vote_average: float
    vote_count: int
    genres: list[dict[str, Any]]
    poster_path: str
    backdrop_path: str
    episode_run_time: list[int]
    networks: list[dict[str, Any]]
    production_companies: list[dict[str, Any]]
    languages: list[str]
    origin_country: list[str]
    in_production: bool
    last_episode_to_air: dict[str, Any] | None
    next_episode_to_air: dict[str, Any] | None
    seasons: list[dict[str, Any]]
    external_ids: dict[str, Any]
    images: dict[str, Any]
    credits: dict[str, Any]
    videos: dict[str, Any]
    keywords: dict[str, Any]
    recommendations: dict[str, Any]
    similar: dict[str, Any]
    translations: dict[str, Any]
    content_ratings: dict[str, Any]
    watch_providers: dict[str, Any]


@dataclass
class TMDBSeasonInfo:
    """TMDB 시즌 정보"""

    id: int
    name: str
    overview: str
    air_date: str
    season_number: int
    episode_count: int
    poster_path: str
    episodes: list[dict[str, Any]]


@dataclass
class TMDBEpisodeInfo:
    """TMDB 에피소드 정보"""

    id: int
    name: str
    overview: str
    air_date: str
    season_number: int
    episode_number: int
    still_path: str
    runtime: int
    guest_stars: list[dict[str, Any]]
    crew: list[dict[str, Any]]


@dataclass
class TMDBGenreInfo:
    """TMDB 장르 정보"""

    id: int
    name: str


@dataclass
class TMDBCompanyInfo:
    """TMDB 제작사 정보"""

    id: int
    name: str
    logo_path: str | None
    origin_country: str


@dataclass
class TMDBNetworkInfo:
    """TMDB 방송사 정보"""

    id: int
    name: str
    logo_path: str | None
    origin_country: str


@dataclass
class TMDBPersonInfo:
    """TMDB 인물 정보"""

    id: int
    name: str
    profile_path: str | None
    character: str | None
    job: str | None
    department: str | None


@dataclass
class TMDBImageInfo:
    """TMDB 이미지 정보"""

    file_path: str
    width: int
    height: int
    aspect_ratio: float
    vote_average: float
    vote_count: int
    iso_639_1: str | None


@dataclass
class TMDBVideoInfo:
    """TMDB 비디오 정보"""

    id: str
    key: str
    name: str
    site: str
    size: int
    type: str
    official: bool
    published_at: str
    iso_639_1: str
    iso_3166_1: str


@dataclass
class TMDBExternalIds:
    """TMDB 외부 ID 정보"""

    imdb_id: str | None
    freebase_mid: str | None
    freebase_id: str | None
    tvdb_id: int | None
    tvrage_id: int | None
    wikidata_id: str | None
    facebook_id: str | None
    instagram_id: str | None
    twitter_id: str | None


@dataclass
class TMDBContentRatings:
    """TMDB 콘텐츠 등급 정보"""

    iso_3166_1: str
    rating: str
    rating_meaning: str | None


@dataclass
class TMDBWatchProvider:
    """TMDB 시청 가능 플랫폼 정보"""

    provider_id: int
    provider_name: str
    logo_path: str | None
    priority: int
    display_priority: int


@dataclass
class TMDBRecommendation:
    """TMDB 추천 작품 정보"""

    id: int
    name: str
    overview: str
    first_air_date: str
    poster_path: str
    vote_average: float
    vote_count: int
    genre_ids: list[int]


@dataclass
class TMDBTranslation:
    """TMDB 번역 정보"""

    iso_639_1: str
    iso_3166_1: str
    name: str
    english_name: str
    data: dict[str, Any]
