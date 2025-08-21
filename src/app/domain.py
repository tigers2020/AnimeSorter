"""
애니메이션 정리 도메인 모델

순수한 도메인 엔티티 정의 (비즈니스 로직 없음)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


class MediaType(Enum):
    """미디어 타입"""

    VIDEO = "video"
    SUBTITLE = "subtitle"
    THUMBNAIL = "thumbnail"
    OTHER = "other"


class ProcessingFlag(Enum):
    """처리 플래그"""

    NEEDS_RENAME = "needs_rename"
    NEEDS_MOVE = "needs_move"
    HAS_METADATA = "has_metadata"
    IS_DUPLICATE = "is_duplicate"
    IS_CORRUPTED = "is_corrupted"
    IS_SAMPLE = "is_sample"
    MANUAL_REVIEW = "manual_review"


class MediaQuality(Enum):
    """미디어 품질"""

    UNKNOWN = "unknown"
    SD_480P = "480p"
    HD_720P = "720p"
    FHD_1080P = "1080p"
    QHD_1440P = "1440p"
    UHD_4K = "4k"
    UHD_8K = "8k"


class MediaSource(Enum):
    """미디어 소스"""

    UNKNOWN = "unknown"
    BLURAY = "bluray"
    DVD = "dvd"
    WEB = "web"
    TV = "tv"
    WEBRIP = "webrip"
    WEBDL = "webdl"
    HDTV = "hdtv"


@dataclass(frozen=True)
class MediaMetadata:
    """미디어 메타데이터"""

    duration_seconds: int | None = None
    resolution_width: int | None = None
    resolution_height: int | None = None
    bitrate_kbps: int | None = None
    codec_video: str | None = None
    codec_audio: str | None = None
    file_size_bytes: int = 0
    quality: MediaQuality = MediaQuality.UNKNOWN
    source: MediaSource = MediaSource.UNKNOWN

    @property
    def resolution(self) -> str | None:
        """해상도 문자열 반환"""
        if self.resolution_width and self.resolution_height:
            return f"{self.resolution_width}x{self.resolution_height}"
        return None

    @property
    def duration_formatted(self) -> str | None:
        """포맷된 재생 시간 반환"""
        if self.duration_seconds is None:
            return None

        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


@dataclass
class MediaFile:
    """
    미디어 파일 도메인 모델

    단일 미디어 파일을 나타내는 순수 도메인 엔티티
    """

    # 필수 식별 정보
    id: UUID = field(default_factory=uuid4)
    path: Path = field(default_factory=lambda: Path())

    # 그룹 관련
    group_id: UUID | None = None

    # 에피소드 정보
    episode: int | None = None
    season: int | None = None

    # 파일 정보
    extension: str = ""
    media_type: MediaType = MediaType.VIDEO

    # 처리 관련
    flags: set[ProcessingFlag] = field(default_factory=set)

    # 메타데이터
    metadata: MediaMetadata | None = None

    # 추가 정보
    original_name: str | None = None
    parsed_title: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 사용자 정의 속성
    custom_attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """생성 후 초기화"""
        # Path 타입 강제
        if isinstance(self.path, str):
            self.path = Path(self.path)

        # 확장자 자동 추출
        if not self.extension and self.path.suffix:
            self.extension = self.path.suffix.lower()

        # 미디어 타입 자동 추정
        if self.media_type == MediaType.VIDEO and self.extension:
            if self.extension in {".srt", ".ass", ".ssa", ".vtt", ".sub"}:
                self.media_type = MediaType.SUBTITLE
            elif self.extension in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                self.media_type = MediaType.THUMBNAIL

    @property
    def name(self) -> str:
        """파일명 반환"""
        return self.path.name

    @property
    def stem(self) -> str:
        """확장자 없는 파일명 반환"""
        return self.path.stem

    @property
    def directory(self) -> Path:
        """디렉토리 경로 반환"""
        return self.path.parent

    @property
    def exists(self) -> bool:
        """파일 존재 여부 확인"""
        return self.path.exists()

    @property
    def size_mb(self) -> float:
        """파일 크기 (MB)"""
        if self.metadata and self.metadata.file_size_bytes:
            return self.metadata.file_size_bytes / (1024 * 1024)
        return 0.0

    def has_flag(self, flag: ProcessingFlag) -> bool:
        """특정 플래그 보유 여부 확인"""
        return flag in self.flags

    def add_flag(self, flag: ProcessingFlag) -> None:
        """플래그 추가"""
        self.flags.add(flag)
        self.updated_at = datetime.now()

    def remove_flag(self, flag: ProcessingFlag) -> None:
        """플래그 제거"""
        self.flags.discard(flag)
        self.updated_at = datetime.now()

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """사용자 정의 속성 가져오기"""
        return self.custom_attributes.get(key, default)

    def set_attribute(self, key: str, value: Any) -> None:
        """사용자 정의 속성 설정"""
        self.custom_attributes[key] = value
        self.updated_at = datetime.now()


@dataclass
class MediaGroup:
    """
    미디어 그룹 도메인 모델

    관련된 미디어 파일들의 논리적 그룹 (시리즈, 시즌 등)
    """

    # 필수 식별 정보
    id: UUID = field(default_factory=uuid4)
    title: str = ""

    # 시즌/에피소드 정보
    season: int | None = None
    total_episodes: int | None = None

    # 그룹에 속한 에피소드들
    episodes: dict[int, UUID] = field(default_factory=dict)  # episode_number -> file_id

    # 메타데이터
    original_title: str | None = None
    year: int | None = None
    description: str | None = None
    genres: set[str] = field(default_factory=set)

    # 외부 ID (TMDB, TVDB 등)
    external_ids: dict[str, str] = field(default_factory=dict)

    # 상태 정보
    is_complete: bool = False
    is_verified: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 사용자 정의 속성
    custom_attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def episode_count(self) -> int:
        """현재 에피소드 수"""
        return len(self.episodes)

    @property
    def episode_numbers(self) -> list[int]:
        """에피소드 번호 목록 (정렬됨)"""
        return sorted(self.episodes.keys())

    @property
    def is_single_episode(self) -> bool:
        """단일 에피소드 여부"""
        return len(self.episodes) == 1

    @property
    def is_movie(self) -> bool:
        """영화 여부 (시즌 정보 없음)"""
        return self.season is None

    @property
    def display_title(self) -> str:
        """표시용 제목"""
        if self.season is not None:
            return f"{self.title} S{self.season:02d}"
        return self.title

    def add_episode(self, episode_number: int, file_id: UUID) -> None:
        """에피소드 추가"""
        self.episodes[episode_number] = file_id
        self.updated_at = datetime.now()

        # 완성도 체크
        if self.total_episodes and len(self.episodes) >= self.total_episodes:
            self.is_complete = True

    def remove_episode(self, episode_number: int) -> UUID | None:
        """에피소드 제거"""
        file_id = self.episodes.pop(episode_number, None)
        if file_id:
            self.updated_at = datetime.now()
            self.is_complete = False
        return file_id

    def has_episode(self, episode_number: int) -> bool:
        """에피소드 존재 여부 확인"""
        return episode_number in self.episodes

    def get_episode_file_id(self, episode_number: int) -> UUID | None:
        """에피소드의 파일 ID 가져오기"""
        return self.episodes.get(episode_number)

    def get_missing_episodes(self) -> list[int]:
        """누락된 에피소드 번호 목록"""
        if not self.total_episodes:
            return []

        all_episodes = set(range(1, self.total_episodes + 1))
        existing_episodes = set(self.episodes.keys())
        return sorted(all_episodes - existing_episodes)

    def set_external_id(self, provider: str, external_id: str) -> None:
        """외부 ID 설정"""
        self.external_ids[provider] = external_id
        self.updated_at = datetime.now()

    def get_external_id(self, provider: str) -> str | None:
        """외부 ID 가져오기"""
        return self.external_ids.get(provider)

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """사용자 정의 속성 가져오기"""
        return self.custom_attributes.get(key, default)

    def set_attribute(self, key: str, value: Any) -> None:
        """사용자 정의 속성 설정"""
        self.custom_attributes[key] = value
        self.updated_at = datetime.now()


@dataclass
class MediaLibrary:
    """
    미디어 라이브러리 도메인 모델

    전체 미디어 컬렉션의 루트 애그리게이트
    """

    # 식별 정보
    id: UUID = field(default_factory=uuid4)
    name: str = "Default Library"

    # 파일 및 그룹 저장소
    files: dict[UUID, MediaFile] = field(default_factory=dict)
    groups: dict[UUID, MediaGroup] = field(default_factory=dict)

    # 라이브러리 메타데이터
    base_path: Path | None = None
    description: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 통계 정보 (캐시됨)
    _stats_cache: dict[str, Any] | None = field(default=None, init=False)
    _stats_cache_time: datetime | None = field(default=None, init=False)

    def add_file(self, media_file: MediaFile) -> None:
        """파일 추가"""
        self.files[media_file.id] = media_file
        self.updated_at = datetime.now()
        self._invalidate_stats_cache()

    def remove_file(self, file_id: UUID) -> MediaFile | None:
        """파일 제거"""
        file = self.files.pop(file_id, None)
        if file:
            # 그룹에서도 제거
            if file.group_id:
                group = self.groups.get(file.group_id)
                if group and file.episode:
                    group.remove_episode(file.episode)

            self.updated_at = datetime.now()
            self._invalidate_stats_cache()

        return file

    def get_file(self, file_id: UUID) -> MediaFile | None:
        """파일 가져오기"""
        return self.files.get(file_id)

    def add_group(self, media_group: MediaGroup) -> None:
        """그룹 추가"""
        self.groups[media_group.id] = media_group
        self.updated_at = datetime.now()
        self._invalidate_stats_cache()

    def remove_group(self, group_id: UUID) -> MediaGroup | None:
        """그룹 제거"""
        group = self.groups.pop(group_id, None)
        if group:
            # 그룹에 속한 파일들의 group_id 해제
            for file in self.files.values():
                if file.group_id == group_id:
                    file.group_id = None

            self.updated_at = datetime.now()
            self._invalidate_stats_cache()

        return group

    def get_group(self, group_id: UUID) -> MediaGroup | None:
        """그룹 가져오기"""
        return self.groups.get(group_id)

    def get_files_by_group(self, group_id: UUID) -> list[MediaFile]:
        """그룹에 속한 파일들 가져오기"""
        return [file for file in self.files.values() if file.group_id == group_id]

    def get_ungrouped_files(self) -> list[MediaFile]:
        """그룹에 속하지 않은 파일들 가져오기"""
        return [file for file in self.files.values() if file.group_id is None]

    def get_files_with_flag(self, flag: ProcessingFlag) -> list[MediaFile]:
        """특정 플래그를 가진 파일들 가져오기"""
        return [file for file in self.files.values() if file.has_flag(flag)]

    def get_stats(self) -> dict[str, Any]:
        """라이브러리 통계 정보"""
        # 캐시된 통계가 유효하면 반환 (1분 캐시)
        if (
            self._stats_cache
            and self._stats_cache_time
            and (datetime.now() - self._stats_cache_time).seconds < 60
        ):
            return self._stats_cache

        # 통계 계산
        total_files = len(self.files)
        total_groups = len(self.groups)

        file_types = {}
        processing_flags = {}
        total_size_bytes = 0

        for file in self.files.values():
            # 파일 타입별 카운트
            file_types[file.media_type.value] = file_types.get(file.media_type.value, 0) + 1

            # 플래그별 카운트
            for flag in file.flags:
                processing_flags[flag.value] = processing_flags.get(flag.value, 0) + 1

            # 총 크기
            if file.metadata:
                total_size_bytes += file.metadata.file_size_bytes

        complete_groups = sum(1 for group in self.groups.values() if group.is_complete)
        verified_groups = sum(1 for group in self.groups.values() if group.is_verified)
        ungrouped_files = len(self.get_ungrouped_files())

        self._stats_cache = {
            "total_files": total_files,
            "total_groups": total_groups,
            "complete_groups": complete_groups,
            "verified_groups": verified_groups,
            "ungrouped_files": ungrouped_files,
            "file_types": file_types,
            "processing_flags": processing_flags,
            "total_size_bytes": total_size_bytes,
            "total_size_gb": total_size_bytes / (1024**3),
        }
        self._stats_cache_time = datetime.now()

        return self._stats_cache

    def _invalidate_stats_cache(self) -> None:
        """통계 캐시 무효화"""
        self._stats_cache = None
        self._stats_cache_time = None
