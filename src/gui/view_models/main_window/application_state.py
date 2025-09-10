"""
애플리케이션 상태 및 UI 기능 관리 - Phase 3.1 뷰모델 분할
MainWindow ViewModel의 상태 관리 부분을 분리합니다.
"""

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class ApplicationState:
    """애플리케이션 전체 상태"""

    is_scanning: bool = False
    current_scan_id: UUID | None = None
    scanned_directory: str | None = None
    is_organizing: bool = False
    is_searching_tmdb: bool = False
    has_scanned_files: bool = False
    has_grouped_files: bool = False
    has_tmdb_matches: bool = False
    selected_files: set[UUID] = field(default_factory=set)
    selected_groups: set[UUID] = field(default_factory=set)
    scan_progress: int = 0
    organize_progress: int = 0
    tmdb_progress: int = 0
    status_message: str = "AnimeSorter가 준비되었습니다"
    last_error: str | None = None


@dataclass
class UICapabilities:
    """UI에서 수행 가능한 작업들"""

    can_start_scan: bool = True
    can_stop_scan: bool = False
    can_start_organize: bool = False
    can_start_tmdb_search: bool = False
    can_clear_results: bool = False

    @classmethod
    def from_app_state(cls, state: ApplicationState) -> "UICapabilities":
        """애플리케이션 상태에서 UI 가능 작업 계산"""
        return cls(
            can_start_scan=not state.is_scanning and not state.is_organizing,
            can_stop_scan=state.is_scanning,
            can_start_organize=state.has_scanned_files
            and not state.is_scanning
            and not state.is_organizing,
            can_start_tmdb_search=state.has_scanned_files and not state.is_searching_tmdb,
            can_clear_results=state.has_scanned_files or state.has_grouped_files,
        )

    @classmethod
    def scanning(cls) -> "UICapabilities":
        """스캔 중일 때의 기능 상태"""
        return cls(
            can_start_scan=False,
            can_stop_scan=True,
            can_start_organize=False,
            can_start_tmdb_search=False,
            can_clear_results=False,
        )

    @classmethod
    def organizing(cls) -> "UICapabilities":
        """정리 중일 때의 기능 상태"""
        return cls(
            can_start_scan=False,
            can_stop_scan=False,
            can_start_organize=False,
            can_start_tmdb_search=False,
            can_clear_results=False,
        )

    @classmethod
    def searching_tmdb(cls) -> "UICapabilities":
        """TMDB 검색 중일 때의 기능 상태"""
        return cls(
            can_start_scan=False,
            can_stop_scan=False,
            can_start_organize=False,
            can_start_tmdb_search=False,
            can_clear_results=False,
        )
