from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class TMDBMediaBase:
    id: int
    media_type: str
    overview: str = ""
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None

@dataclass
class TMDBMovie(TMDBMediaBase):
    title: str = ""
    original_title: str = ""
    release_date: Optional[str] = None
    runtime: Optional[int] = None
    genres: List[dict] = field(default_factory=list)

@dataclass
class TMDBTVShow(TMDBMediaBase):
    name: str = ""
    original_name: str = ""
    first_air_date: Optional[str] = None
    last_air_date: Optional[str] = None
    number_of_seasons: int = 0
    number_of_episodes: int = 0
    seasons: List[dict] = field(default_factory=list)
    genres: List[dict] = field(default_factory=list) 