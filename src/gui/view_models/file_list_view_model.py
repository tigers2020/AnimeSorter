"""
파일 리스트 뷰모델

파일 목록과 그룹화된 데이터를 관리하는 뷰모델
"""

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass
from typing import Any

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from src.core.events import ITypedEventBus
from src.core.tmdb_client import TMDBAnimeInfo
from src.gui.managers.anime_data_manager import ParsedItem


@dataclass
class GroupInfo:
    """그룹 정보"""

    key: str
    title: str
    season: int | None
    episode_count: int
    total_size: int
    tmdb_match: TMDBAnimeInfo | None = None
    final_path: str = ""


class FileListViewModel(QObject):
    """파일 리스트 뷰모델"""

    data_changed = pyqtSignal()
    selection_changed = pyqtSignal()
    group_updated = pyqtSignal(str)

    def __init__(self, event_bus: ITypedEventBus, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self._parsed_items: list[ParsedItem] = []
        self._grouped_items: dict[str, list[ParsedItem]] = {}
        self._group_info: dict[str, GroupInfo] = {}
        self._selected_items: set[str] = set()
        self._tmdb_matches: dict[str, TMDBAnimeInfo] = {}
        self._filter_text: str = ""
        self._filter_season: int | None = None
        self._show_only_selected: bool = False
        self._sort_by: str = "title"
        self._sort_ascending: bool = True
        self._connect_event_bus()

    def initialize(self) -> bool:
        """뷰모델 초기화"""
        try:
            logger.info("✅ FileListViewModel 초기화 완료")
            return True
        except Exception as e:
            logger.info("❌ FileListViewModel 초기화 실패: %s", e)
            return False

    def cleanup(self):
        """뷰모델 정리"""
        try:
            self._disconnect_event_bus()
            logger.info("🧹 FileListViewModel 정리 완료")
        except Exception as e:
            logger.info("❌ FileListViewModel 정리 실패: %s", e)

    def _connect_event_bus(self):
        """이벤트 버스 연결"""
        if self.event_bus:
            self.event_bus.subscribe("parsed_items_updated", self._on_parsed_items_updated)
            self.event_bus.subscribe("grouped_items_updated", self._on_grouped_items_updated)
            self.event_bus.subscribe("tmdb_matches_updated", self._on_tmdb_matches_updated)
            self.event_bus.subscribe("selected_items_updated", self._on_selected_items_updated)

    def _disconnect_event_bus(self):
        """이벤트 버스 연결 해제"""
        if self.event_bus:
            self.event_bus.unsubscribe("parsed_items_updated", self._on_parsed_items_updated)
            self.event_bus.unsubscribe("grouped_items_updated", self._on_grouped_items_updated)
            self.event_bus.unsubscribe("tmdb_matches_updated", self._on_tmdb_matches_updated)
            self.event_bus.unsubscribe("selected_items_updated", self._on_selected_items_updated)

    def _on_parsed_items_updated(self, items: list[ParsedItem]):
        """파싱된 아이템 업데이트"""
        self._parsed_items = items
        self._update_group_info()
        self.data_changed.emit()

    def _on_grouped_items_updated(self, grouped: dict[str, list[ParsedItem]]):
        """그룹화된 아이템 업데이트"""
        self._grouped_items = grouped
        self._update_group_info()
        self.data_changed.emit()

    def _on_tmdb_matches_updated(self, matches: dict[str, TMDBAnimeInfo]):
        """TMDB 매치 업데이트"""
        self._tmdb_matches = matches
        self._update_group_info()
        self.data_changed.emit()

    def _on_selected_items_updated(self, selected: set[str]):
        """선택된 아이템 업데이트"""
        self._selected_items = selected
        self.selection_changed.emit()

    def _update_group_info(self):
        """그룹 정보 업데이트"""
        self._group_info.clear()
        for group_key, items in self._grouped_items.items():
            if not items:
                continue
            first_item = items[0]
            group_info = GroupInfo(
                key=group_key,
                title=first_item.title,
                season=first_item.season,
                episode_count=len(items),
                total_size=sum(item.file_size for item in items if item.file_size),
                tmdb_match=self._tmdb_matches.get(group_key),
            )
            group_info.final_path = self._calculate_final_path(group_info)
            self._group_info[group_key] = group_info

    def _calculate_final_path(self, group_info: GroupInfo) -> str:
        """최종 경로 계산"""
        try:
            title = group_info.tmdb_match.name if group_info.tmdb_match else group_info.title
            sanitized_title = self._sanitize_title(title)
            if group_info.season:
                season_str = f"Season{group_info.season:02d}"
                return f"{sanitized_title}/{season_str}"
            return sanitized_title
        except Exception as e:
            logger.info("❌ 최종 경로 계산 실패: %s", e)
            return group_info.title

    def _sanitize_title(self, title: str) -> str:
        """제목 정제 (특수문자 제거, 공백 정규화)"""
        import re

        sanitized = re.sub("[^\\w\\s가-힣]", "", title)
        sanitized = re.sub("\\s+", " ", sanitized)
        return sanitized.strip()

    def set_filter_text(self, text: str):
        """필터 텍스트 설정"""
        self._filter_text = text.lower()
        self.data_changed.emit()

    def set_filter_season(self, season: int | None):
        """시즌 필터 설정"""
        self._filter_season = season
        self.data_changed.emit()

    def set_show_only_selected(self, show: bool):
        """선택된 항목만 표시 설정"""
        self._show_only_selected = show
        self.data_changed.emit()

    def get_filtered_groups(self) -> list[GroupInfo]:
        """필터링된 그룹 목록 반환"""
        filtered_groups = []
        for group_info in self._group_info.values():
            if (
                self._filter_text
                and self._filter_text not in group_info.title.lower()
                and (
                    group_info.tmdb_match
                    and self._filter_text not in group_info.tmdb_match.name.lower()
                )
            ):
                continue
            if self._filter_season is not None and group_info.season != self._filter_season:
                continue
            if self._show_only_selected and group_info.key not in self._selected_items:
                continue
            filtered_groups.append(group_info)
        self._sort_groups(filtered_groups)
        return filtered_groups

    def _sort_groups(self, groups: list[GroupInfo]):
        """그룹 정렬"""
        reverse = not self._sort_ascending
        if self._sort_by == "title":
            groups.sort(key=lambda g: g.title.lower(), reverse=reverse)
        elif self._sort_by == "season":
            groups.sort(key=lambda g: g.season or 0, reverse=reverse)
        elif self._sort_by == "episode_count":
            groups.sort(key=lambda g: g.episode_count, reverse=reverse)
        elif self._sort_by == "total_size":
            groups.sort(key=lambda g: g.total_size, reverse=reverse)
        elif self._sort_by == "final_path":
            groups.sort(key=lambda g: g.final_path.lower(), reverse=reverse)

    def select_group(self, group_key: str):
        """그룹 선택"""
        self._selected_items.add(group_key)
        self.selection_changed.emit()

    def deselect_group(self, group_key: str):
        """그룹 선택 해제"""
        self._selected_items.discard(group_key)
        self.selection_changed.emit()

    def select_all_groups(self):
        """모든 그룹 선택"""
        self._selected_items.update(self._group_info.keys())
        self.selection_changed.emit()

    def deselect_all_groups(self):
        """모든 그룹 선택 해제"""
        self._selected_items.clear()
        self.selection_changed.emit()

    def toggle_group_selection(self, group_key: str):
        """그룹 선택 토글"""
        if group_key in self._selected_items:
            self.deselect_group(group_key)
        else:
            self.select_group(group_key)

    @pyqtProperty(int, notify=data_changed)
    def total_groups(self) -> int:
        """전체 그룹 수"""
        return len(self._group_info)

    @pyqtProperty(int, notify=data_changed)
    def filtered_groups_count(self) -> int:
        """필터링된 그룹 수"""
        return len(self.get_filtered_groups())

    @pyqtProperty(int, notify=selection_changed)
    def selected_groups_count(self) -> int:
        """선택된 그룹 수"""
        return len(self._selected_items)

    @pyqtProperty(bool, notify=selection_changed)
    def has_selected_groups(self) -> bool:
        """선택된 그룹이 있는지 확인"""
        return len(self._selected_items) > 0

    @pyqtProperty(bool, notify=data_changed)
    def has_groups(self) -> bool:
        """그룹이 있는지 확인"""
        return len(self._group_info) > 0

    @pyqtProperty(str, notify=data_changed)
    def filter_text(self) -> str:
        """필터 텍스트"""
        return self._filter_text

    @pyqtProperty(bool, notify=data_changed)
    def show_only_selected(self) -> bool:
        """선택된 항목만 표시 여부"""
        return self._show_only_selected

    def set_property(self, name: str, value: Any, validate: bool = True) -> bool:
        """프로퍼티 설정"""
        try:
            if hasattr(self, f"_{name}"):
                setattr(self, f"_{name}", value)
                return True
            return False
        except Exception as e:
            logger.info("❌ 프로퍼티 설정 실패: %s = %s - %s", name, value, e)
            return False

    def get_property(self, name: str) -> Any:
        """프로퍼티 가져오기"""
        try:
            if hasattr(self, f"_{name}"):
                return getattr(self, f"_{name}")
            return None
        except Exception as e:
            logger.info("❌ 프로퍼티 가져오기 실패: %s - %s", name, e)
            return None

    def get_all_properties(self) -> dict[str, Any]:
        """모든 프로퍼티 가져오기"""
        properties = {}
        for attr_name in dir(self):
            if attr_name.startswith("_") and not attr_name.startswith("__"):
                prop_name = attr_name[1:]
                properties[prop_name] = getattr(self, attr_name)
        return properties

    def get_group_info(self, group_key: str) -> GroupInfo | None:
        """그룹 정보 가져오기"""
        return self._group_info.get(group_key)

    def get_group_items(self, group_key: str) -> list[ParsedItem]:
        """그룹의 아이템 목록 가져오기"""
        return self._grouped_items.get(group_key, [])

    def get_selected_groups(self) -> list[str]:
        """선택된 그룹 목록 반환"""
        return list(self._selected_items)

    def get_selected_items(self) -> list[ParsedItem]:
        """선택된 그룹의 모든 아이템 반환"""
        selected_items = []
        for group_key in self._selected_items:
            selected_items.extend(self._grouped_items.get(group_key, []))
        return selected_items

    def is_group_selected(self, group_key: str) -> bool:
        """그룹이 선택되었는지 확인"""
        return group_key in self._selected_items

    def get_tmdb_match(self, group_key: str) -> TMDBAnimeInfo | None:
        """그룹의 TMDB 매치 가져오기"""
        return self._tmdb_matches.get(group_key)

    def set_sort_by(self, sort_by: str, ascending: bool = True):
        """정렬 설정"""
        self._sort_by = sort_by
        self._sort_ascending = ascending
        self.data_changed.emit()

    def refresh_data(self):
        """데이터 새로고침"""
        self._update_group_info()
        self.data_changed.emit()

    def clear_data(self):
        """데이터 초기화"""
        self._parsed_items.clear()
        self._grouped_items.clear()
        self._group_info.clear()
        self._selected_items.clear()
        self._tmdb_matches.clear()
        self.data_changed.emit()
        self.selection_changed.emit()
