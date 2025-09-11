"""
상세 뷰 뷰모델

선택된 그룹의 상세 정보를 관리하는 뷰모델
"""

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass
from typing import Any

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from src.core.events import ITypedEventBus
from src.core.file_parser import ParsedMetadata as ParsedItem
from src.core.tmdb_client import TMDBAnimeInfo


@dataclass
class DetailInfo:
    """상세 정보"""

    group_key: str
    title: str
    season: int | None
    episode_count: int
    total_size: int
    file_list: list[ParsedItem]
    tmdb_match: TMDBAnimeInfo | None = None
    final_path: str = ""
    poster_url: str = ""
    overview: str = ""


class DetailViewModel(QObject):
    """상세 뷰 뷰모델"""

    detail_changed = pyqtSignal()
    selection_changed = pyqtSignal()

    def __init__(self, event_bus: ITypedEventBus, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self._selected_group_key: str | None = None
        self._detail_info: DetailInfo | None = None
        self._connect_event_bus()

    def initialize(self) -> bool:
        """뷰모델 초기화"""
        try:
            logger.info("✅ DetailViewModel 초기화 완료")
            return True
        except Exception as e:
            logger.info("❌ DetailViewModel 초기화 실패: %s", e)
            return False

    def cleanup(self):
        """뷰모델 정리"""
        try:
            self._disconnect_event_bus()
            logger.info("🧹 DetailViewModel 정리 완료")
        except Exception as e:
            logger.info("❌ DetailViewModel 정리 실패: %s", e)

    def _connect_event_bus(self):
        """이벤트 버스 연결"""
        if self.event_bus:
            self.event_bus.subscribe("group_selection_changed", self._on_group_selection_changed)
            self.event_bus.subscribe("grouped_items_updated", self._on_grouped_items_updated)
            self.event_bus.subscribe("tmdb_matches_updated", self._on_tmdb_matches_updated)

    def _disconnect_event_bus(self):
        """이벤트 버스 연결 해제"""
        if self.event_bus:
            self.event_bus.unsubscribe("group_selection_changed", self._on_group_selection_changed)
            self.event_bus.unsubscribe("grouped_items_updated", self._on_grouped_items_updated)
            self.event_bus.unsubscribe("tmdb_matches_updated", self._on_tmdb_matches_updated)

    def _on_group_selection_changed(self, selected_groups: list[str]):
        """그룹 선택 변경 처리"""
        if selected_groups:
            self.set_selected_group(selected_groups[0])
        else:
            self.clear_selection()

    def _on_grouped_items_updated(self, grouped_items: dict[str, list[ParsedItem]]):
        """그룹화된 아이템 업데이트"""
        if self._selected_group_key:
            self._update_detail_info()

    def _on_tmdb_matches_updated(self, tmdb_matches: dict[str, TMDBAnimeInfo]):
        """TMDB 매치 업데이트"""
        if self._selected_group_key:
            self._update_detail_info()

    def set_selected_group(self, group_key: str):
        """선택된 그룹 설정"""
        self._selected_group_key = group_key
        self._update_detail_info()
        self.selection_changed.emit()

    def clear_selection(self):
        """선택 해제"""
        self._selected_group_key = None
        self._detail_info = None
        self.detail_changed.emit()
        self.selection_changed.emit()

    def _update_detail_info(self):
        """상세 정보 업데이트"""
        if not self._selected_group_key:
            return
        try:
            if not self.event_bus:
                return
            grouped_items = self.event_bus.publish("get_grouped_items", [])
            items = grouped_items.get(self._selected_group_key, [])
            if not items:
                self.clear_selection()
                return
            tmdb_matches = self.event_bus.publish("get_all_tmdb_matches", [])
            tmdb_match = tmdb_matches.get(self._selected_group_key)
            first_item = items[0]
            detail_info = DetailInfo(
                group_key=self._selected_group_key,
                title=first_item.title,
                season=first_item.season,
                episode_count=len(items),
                total_size=sum(item.file_size for item in items if item.file_size),
                file_list=items,
                tmdb_match=tmdb_match,
            )
            detail_info.final_path = self._calculate_final_path(detail_info)
            if tmdb_match and tmdb_match.poster_path:
                detail_info.poster_url = f"https://image.tmdb.org/t/p/w500{tmdb_match.poster_path}"
            if tmdb_match and tmdb_match.overview:
                detail_info.overview = tmdb_match.overview
            self._detail_info = detail_info
            self.detail_changed.emit()
        except Exception as e:
            logger.info("❌ 상세 정보 업데이트 실패: %s", e)
            self.clear_selection()

    def _calculate_final_path(self, detail_info: DetailInfo) -> str:
        """최종 경로 계산"""
        try:
            title = detail_info.tmdb_match.name if detail_info.tmdb_match else detail_info.title
            sanitized_title = self._sanitize_title(title)
            if detail_info.season:
                season_str = f"Season{detail_info.season:02d}"
                return f"{sanitized_title}/{season_str}"
            return sanitized_title
        except Exception as e:
            logger.info("❌ 최종 경로 계산 실패: %s", e)
            return detail_info.title

    def _sanitize_title(self, title: str) -> str:
        """제목 정제 (특수문자 제거, 공백 정규화)"""
        import re

        sanitized = re.sub("[^\\w\\s가-힣]", "", title)
        sanitized = re.sub("\\s+", " ", sanitized)
        return sanitized.strip()

    @pyqtProperty(bool, notify=selection_changed)
    def has_selection(self) -> bool:
        """선택된 그룹이 있는지 확인"""
        return self._selected_group_key is not None

    @pyqtProperty(str, notify=detail_changed)
    def group_key(self) -> str:
        """그룹 키"""
        return self._selected_group_key or ""

    @pyqtProperty(str, notify=detail_changed)
    def title(self) -> str:
        """제목"""
        if self._detail_info:
            return self._detail_info.title
        return ""

    @pyqtProperty(str, notify=detail_changed)
    def korean_title(self) -> str:
        """한글 제목 (TMDB 매치가 있는 경우)"""
        if self._detail_info and self._detail_info.tmdb_match:
            return self._detail_info.tmdb_match.name
        return ""

    @pyqtProperty(int, notify=detail_changed)
    def season(self) -> int:
        """시즌"""
        if self._detail_info and self._detail_info.season:
            return self._detail_info.season
        return 0

    @pyqtProperty(str, notify=detail_changed)
    def season_display(self) -> str:
        """시즌 표시 텍스트"""
        if self._detail_info and self._detail_info.season:
            return f"시즌 {self._detail_info.season}"
        return "시즌 정보 없음"

    @pyqtProperty(int, notify=detail_changed)
    def episode_count(self) -> int:
        """에피소드 수"""
        if self._detail_info:
            return self._detail_info.episode_count
        return 0

    @pyqtProperty(int, notify=detail_changed)
    def total_size(self) -> int:
        """전체 크기 (바이트)"""
        if self._detail_info:
            return self._detail_info.total_size
        return 0

    @pyqtProperty(str, notify=detail_changed)
    def total_size_display(self) -> str:
        """전체 크기 표시 텍스트"""
        if self._detail_info:
            size = self._detail_info.total_size
            if size < 1024:
                return f"{size} B"
            if size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            if size < 1024 * 1024 * 1024:
                return f"{size / (1024 * 1024):.1f} MB"
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
        return "0 B"

    @pyqtProperty(str, notify=detail_changed)
    def final_path(self) -> str:
        """최종 경로"""
        if self._detail_info:
            return self._detail_info.final_path
        return ""

    @pyqtProperty(str, notify=detail_changed)
    def poster_url(self) -> str:
        """포스터 URL"""
        if self._detail_info:
            return self._detail_info.poster_url
        return ""

    @pyqtProperty(str, notify=detail_changed)
    def overview(self) -> str:
        """개요"""
        if self._detail_info:
            return self._detail_info.overview
        return ""

    @pyqtProperty(bool, notify=detail_changed)
    def has_tmdb_match(self) -> bool:
        """TMDB 매치가 있는지 확인"""
        return self._detail_info is not None and self._detail_info.tmdb_match is not None

    @pyqtProperty(bool, notify=detail_changed)
    def has_poster(self) -> bool:
        """포스터가 있는지 확인"""
        return bool(self.poster_url)

    @pyqtProperty(bool, notify=detail_changed)
    def has_overview(self) -> bool:
        """개요가 있는지 확인"""
        return bool(self.overview)

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

    def get_detail_info(self) -> DetailInfo | None:
        """상세 정보 반환"""
        return self._detail_info

    def get_file_list(self) -> list[ParsedItem]:
        """파일 목록 반환"""
        if self._detail_info:
            return self._detail_info.file_list
        return []

    def get_tmdb_match(self) -> TMDBAnimeInfo | None:
        """TMDB 매치 반환"""
        if self._detail_info:
            return self._detail_info.tmdb_match
        return None

    def refresh_detail(self):
        """상세 정보 새로고침"""
        if self._selected_group_key:
            self._update_detail_info()

    def get_file_info_summary(self) -> dict[str, Any]:
        """파일 정보 요약 반환"""
        if not self._detail_info:
            return {}
        files = self._detail_info.file_list
        extensions = {}
        for file in files:
            ext = file.extension.lower()
            if ext not in extensions:
                extensions[ext] = 0
            extensions[ext] += 1
        resolutions = {}
        for file in files:
            res = file.resolution or "Unknown"
            if res not in resolutions:
                resolutions[res] = 0
            resolutions[res] += 1
        return {
            "total_files": len(files),
            "extensions": extensions,
            "resolutions": resolutions,
            "average_size": self._detail_info.total_size // len(files) if files else 0,
        }
