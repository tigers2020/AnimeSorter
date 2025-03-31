"""
TMDB 응답 데이터 모델

TMDB API 응답 데이터를 위한 모델 클래스
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TMDBMediaBase:
    """TMDB 미디어 공통 속성"""
    id: int
    media_type: str  # "tv" 또는 "movie"
    overview: str = ""
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    popularity: float = 0.0
    vote_average: float = 0.0
    vote_count: int = 0
    

@dataclass
class TMDBMovie(TMDBMediaBase):
    """영화 정보"""
    title: str
    original_title: str = ""
    release_date: Optional[str] = None
    runtime: Optional[int] = None
    genres: List[dict] = field(default_factory=list)
    adult: bool = False
    

@dataclass
class TMDBTVShow(TMDBMediaBase):
    """TV 시리즈 정보"""
    name: str
    original_name: str = ""
    first_air_date: Optional[str] = None
    last_air_date: Optional[str] = None
    number_of_seasons: int = 0
    number_of_episodes: int = 0
    seasons: List[dict] = field(default_factory=list)
    genres: List[dict] = field(default_factory=list)
    

@dataclass
class TMDBSeason:
    """시즌 정보"""
    id: int
    name: str
    season_number: int
    episode_count: int
    overview: str = ""
    poster_path: Optional[str] = None
    air_date: Optional[str] = None
    

@dataclass
class TMDBEpisode:
    """에피소드 정보"""
    id: int
    name: str
    episode_number: int
    season_number: int
    overview: str = ""
    still_path: Optional[str] = None
    air_date: Optional[str] = None
    runtime: Optional[int] = None
    vote_average: float = 0.0
    

@dataclass
class TMDBPerson:
    """인물 정보"""
    id: int
    name: str
    profile_path: Optional[str] = None
    known_for_department: str = ""
    
    
@dataclass
class TMDBCastMember(TMDBPerson):
    """출연진 정보"""
    character: str = ""
    order: int = 0
    

@dataclass
class TMDBCrewMember(TMDBPerson):
    """제작진 정보"""
    department: str = ""
    job: str = "" 