"""
상태 서비스 - 애플리케이션 상태 관리
"""

import logging

logger = logging.getLogger(__name__)
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

from src.app.domain import ParsedItem
from src.core.tmdb_client import TMDBAnimeInfo


class AppState(Enum):
    """애플리케이션 상태"""

    IDLE = "idle"
    SCANNING = "scanning"
    SEARCHING = "searching"
    ORGANIZING = "organizing"
    ERROR = "error"


@dataclass
class ScanState:
    """스캔 상태"""

    is_scanning: bool = False
    total_files: int = 0
    processed_files: int = 0
    current_file: str = ""
    scan_directory: str = ""


@dataclass
class SearchState:
    """검색 상태"""

    is_searching: bool = False
    total_groups: int = 0
    processed_groups: int = 0
    current_group: str = ""
    pending_groups: list[str] = field(default_factory=list)


@dataclass
class OrganizeState:
    """정리 상태"""

    is_organizing: bool = False
    total_files: int = 0
    processed_files: int = 0
    current_file: str = ""
    target_directory: str = ""


@dataclass
class AppData:
    """애플리케이션 데이터"""

    parsed_items: list[ParsedItem] = field(default_factory=list)
    grouped_items: dict[str, list[ParsedItem]] = field(default_factory=dict)
    tmdb_matches: dict[str, TMDBAnimeInfo] = field(default_factory=dict)
    selected_items: set[str] = field(default_factory=set)
    last_scan_directory: str = ""
    last_target_directory: str = ""


class StateService(QObject):
    """상태 서비스 - 애플리케이션 상태 관리"""

    state_changed = pyqtSignal(AppState)
    scan_progress = pyqtSignal(int, int)
    search_progress = pyqtSignal(int, int)
    organize_progress = pyqtSignal(int, int)
    data_updated = pyqtSignal(str)

    def __init__(self, event_bus=None):
        super().__init__()
        self.event_bus = event_bus
        self._current_state = AppState.IDLE
        self._scan_state = ScanState()
        self._search_state = SearchState()
        self._organize_state = OrganizeState()
        self._app_data = AppData()
        self._config_dir = Path.home() / ".animesorter"
        self._state_file = self._config_dir / "app_state.json"

    def initialize(self) -> bool:
        """서비스 초기화"""
        try:
            self._config_dir.mkdir(exist_ok=True)
            self._load_state()
            logger.info("✅ StateService 초기화 완료")
            return True
        except Exception as e:
            logger.info("❌ StateService 초기화 실패: %s", e)
            return False

    def cleanup(self):
        """서비스 정리"""
        try:
            self._save_state()
            logger.info("🧹 StateService 정리 완료")
        except Exception as e:
            logger.info("❌ StateService 정리 실패: %s", e)

    def get_current_state(self) -> AppState:
        """현재 상태 반환"""
        return self._current_state

    def set_state(self, new_state: AppState):
        """상태 변경"""
        if self._current_state != new_state:
            self._current_state = new_state
            self.state_changed.emit(new_state)
            logger.info("🔄 상태 변경: %s", new_state.value)

    def is_idle(self) -> bool:
        """대기 상태인지 확인"""
        return self._current_state == AppState.IDLE

    def is_scanning(self) -> bool:
        """스캔 중인지 확인"""
        return self._current_state == AppState.SCANNING

    def is_searching(self) -> bool:
        """검색 중인지 확인"""
        return self._current_state == AppState.SEARCHING

    def is_organizing(self) -> bool:
        """정리 중인지 확인"""
        return self._current_state == AppState.ORGANIZING

    def start_scan(self, directory: str):
        """스캔 시작"""
        self._scan_state = ScanState(is_scanning=True, scan_directory=directory)
        self.set_state(AppState.SCANNING)
        self._app_data.last_scan_directory = directory
        logger.info("🔍 스캔 시작: %s", directory)

    def update_scan_progress(self, current: int, total: int, current_file: str = ""):
        """스캔 진행률 업데이트"""
        self._scan_state.processed_files = current
        self._scan_state.total_files = total
        self._scan_state.current_file = current_file
        self.scan_progress.emit(current, total)

    def complete_scan(self):
        """스캔 완료"""
        self._scan_state.is_scanning = False
        self.set_state(AppState.IDLE)
        logger.info("✅ 스캔 완료: %s개 파일", self._scan_state.processed_files)

    def get_scan_state(self) -> ScanState:
        """스캔 상태 반환"""
        return self._scan_state

    def start_search(self, groups: list[str]):
        """검색 시작"""
        self._search_state = SearchState(
            is_searching=True, total_groups=len(groups), pending_groups=groups.copy()
        )
        self.set_state(AppState.SEARCHING)
        logger.info("🔍 검색 시작: %s개 그룹", len(groups))

    def update_search_progress(self, current: int, total: int, current_group: str = ""):
        """검색 진행률 업데이트"""
        self._search_state.processed_groups = current
        self._search_state.total_groups = total
        self._search_state.current_group = current_group
        self.search_progress.emit(current, total)

    def complete_search(self):
        """검색 완료"""
        self._search_state.is_searching = False
        self.set_state(AppState.IDLE)
        logger.info("✅ 검색 완료: %s개 그룹", self._search_state.processed_groups)

    def get_search_state(self) -> SearchState:
        """검색 상태 반환"""
        return self._search_state

    def start_organize(self, target_directory: str, total_files: int):
        """정리 시작"""
        self._organize_state = OrganizeState(
            is_organizing=True, total_files=total_files, target_directory=target_directory
        )
        self.set_state(AppState.ORGANIZING)
        self._app_data.last_target_directory = target_directory
        logger.info("📁 정리 시작: %s (%s개 파일)", target_directory, total_files)

    def update_organize_progress(self, current: int, total: int, current_file: str = ""):
        """정리 진행률 업데이트"""
        self._organize_state.processed_files = current
        self._organize_state.total_files = total
        self._organize_state.current_file = current_file
        self.organize_progress.emit(current, total)

    def complete_organize(self):
        """정리 완료"""
        self._organize_state.is_organizing = False
        self.set_state(AppState.IDLE)
        logger.info("✅ 정리 완료: %s개 파일", self._organize_state.processed_files)

    def get_organize_state(self) -> OrganizeState:
        """정리 상태 반환"""
        return self._organize_state

    def set_parsed_items(self, items: list[ParsedItem]):
        """파싱된 아이템 설정"""
        self._app_data.parsed_items = items
        self.data_updated.emit("parsed_items")
        logger.info("📊 파싱된 아이템 설정: %s개", len(items))

    def get_parsed_items(self) -> list[ParsedItem]:
        """파싱된 아이템 반환"""
        return self._app_data.parsed_items

    def set_grouped_items(self, grouped: dict[str, list[ParsedItem]]):
        """그룹화된 아이템 설정"""
        self._app_data.grouped_items = grouped
        self.data_updated.emit("grouped_items")
        logger.info("📊 그룹화된 아이템 설정: %s개 그룹", len(grouped))

    def get_grouped_items(self) -> dict[str, list[ParsedItem]]:
        """그룹화된 아이템 반환"""
        return self._app_data.grouped_items

    def set_tmdb_match(self, group_key: str, anime_info: TMDBAnimeInfo):
        """TMDB 매치 설정"""
        self._app_data.tmdb_matches[group_key] = anime_info
        self.data_updated.emit("tmdb_matches")
        logger.info("🎬 TMDB 매치 설정: %s -> %s", group_key, anime_info.name)

    def get_tmdb_match(self, group_key: str) -> TMDBAnimeInfo | None:
        """TMDB 매치 반환"""
        return self._app_data.tmdb_matches.get(group_key)

    def get_all_tmdb_matches(self) -> dict[str, TMDBAnimeInfo]:
        """모든 TMDB 매치 반환"""
        return self._app_data.tmdb_matches.copy()

    def set_selected_items(self, selected: set[str]):
        """선택된 아이템 설정"""
        self._app_data.selected_items = selected
        self.data_updated.emit("selected_items")
        logger.info("✅ 선택된 아이템 설정: %s개", len(selected))

    def get_selected_items(self) -> set[str]:
        """선택된 아이템 반환"""
        return self._app_data.selected_items.copy()

    def add_selected_item(self, item_key: str):
        """선택된 아이템 추가"""
        self._app_data.selected_items.add(item_key)
        self.data_updated.emit("selected_items")

    def remove_selected_item(self, item_key: str):
        """선택된 아이템 제거"""
        self._app_data.selected_items.discard(item_key)
        self.data_updated.emit("selected_items")

    def clear_selected_items(self):
        """선택된 아이템 모두 제거"""
        self._app_data.selected_items.clear()
        self.data_updated.emit("selected_items")

    def get_last_scan_directory(self) -> str:
        """마지막 스캔 디렉토리 반환"""
        return self._app_data.last_scan_directory

    def get_last_target_directory(self) -> str:
        """마지막 대상 디렉토리 반환"""
        return self._app_data.last_target_directory

    def get_data_stats(self) -> dict[str, Any]:
        """데이터 통계 반환"""
        return {
            "total_parsed_items": len(self._app_data.parsed_items),
            "total_groups": len(self._app_data.grouped_items),
            "total_tmdb_matches": len(self._app_data.tmdb_matches),
            "selected_items_count": len(self._app_data.selected_items),
            "last_scan_directory": self._app_data.last_scan_directory,
            "last_target_directory": self._app_data.last_target_directory,
        }

    def _save_state(self):
        """상태를 파일에 저장"""
        try:
            state_data = {
                "last_scan_directory": self._app_data.last_scan_directory,
                "last_target_directory": self._app_data.last_target_directory,
                "current_state": self._current_state.value,
            }
            with self._state_file.open("w", encoding="utf-8") as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            logger.info("💾 상태 저장 완료: %s", self._state_file)
        except Exception as e:
            logger.info("❌ 상태 저장 실패: %s", e)

    def _load_state(self):
        """파일에서 상태 로드"""
        try:
            if self._state_file.exists():
                with self._state_file.open(encoding="utf-8") as f:
                    state_data = json.load(f)
                self._app_data.last_scan_directory = state_data.get("last_scan_directory", "")
                self._app_data.last_target_directory = state_data.get("last_target_directory", "")
                state_value = state_data.get("current_state", "idle")
                self._current_state = AppState(state_value)
                logger.info("📂 상태 로드 완료: %s", self._state_file)
        except Exception as e:
            logger.info("❌ 상태 로드 실패: %s", e)

    def reset_state(self):
        """상태 초기화"""
        self._current_state = AppState.IDLE
        self._scan_state = ScanState()
        self._search_state = SearchState()
        self._organize_state = OrganizeState()
        self._app_data = AppData()
        logger.info("🔄 상태 초기화 완료")
