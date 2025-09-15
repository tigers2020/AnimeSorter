"""
테이블 모델 및 필터 프록시
파싱된 애니메이션 아이템을 테이블에 표시하고 필터링하는 기능을 제공합니다.
"""

import logging

logger = logging.getLogger(__name__)
import re
from pathlib import Path
from typing import Any

from managers.anime_data_manager import ParsedItem
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QRect, Qt, QVariant
from PyQt5.QtGui import QFont, QFontMetrics, QPainter, QPixmap


class GroupedListModel(QAbstractTableModel):
    """그룹화된 애니메이션 목록을 표시하는 모델"""

    headers = [
        "제목",
        "최종 이동 경로",
        "시즌",
        "에피소드 수",
        "해상도",
        "비디오 코덱",
        "오디오 코덱",
        "릴리즈 그룹",
        "상태",
    ]

    def __init__(
        self,
        grouped_items: dict[str, list] = None,
        tmdb_client=None,
        destination_directory: str = None,
    ):
        super().__init__()
        self.grouped_items = grouped_items or {}
        self.tmdb_client = tmdb_client
        self.destination_directory = destination_directory or "대상 폴더"
        self._group_list = []
        self._max_title_width = 0
        self._tooltip_cache: dict[str, Any] = {}
        self._update_group_list()

    def set_grouped_items(self, grouped_items: dict[str, list]):
        """그룹화된 아이템 설정 (Phase 9.1: 성능 최적화)"""
        if len(grouped_items) > 1000:
            self.beginResetModel()
            self.grouped_items = grouped_items
            self._update_group_list()
            self.endResetModel()
        else:
            self.beginResetModel()
            self.grouped_items = grouped_items
            self._update_group_list()
            self.endResetModel()

    def _update_group_list(self):
        """그룹 리스트 업데이트"""
        self._group_list = []
        self._max_title_width = 0
        for group_key, items in self.grouped_items.items():
            if not items:
                continue
            representative = items[0]
            episodes = [item.episode for item in items if item.episode is not None]
            if episodes:
                min_ep = min(episodes)
                max_ep = max(episodes)
                if min_ep == max_ep:
                    episode_info = f"E{min_ep:02d}"
                else:
                    episode_info = f"E{min_ep:02d}-E{max_ep:02d}"
            else:
                episode_info = "Unknown"
            # 해상도 정보 수집
            resolutions = {}
            video_codecs = {}
            audio_codecs = {}
            release_groups = {}

            for item in items:
                # 해상도 처리 - 통일된 정규화 사용
                from src.core.resolution_normalizer import normalize_resolution

                res = normalize_resolution(item.resolution or "Unknown")
                resolutions[res] = resolutions.get(res, 0) + 1

                # 비디오 코덱 수집
                if item.video_codec:
                    video_codecs[item.video_codec] = video_codecs.get(item.video_codec, 0) + 1

                # 오디오 코덱 수집
                if item.audio_codec:
                    audio_codecs[item.audio_codec] = audio_codecs.get(item.audio_codec, 0) + 1

                # 릴리즈 그룹 수집
                if item.release_group:
                    release_groups[item.release_group] = (
                        release_groups.get(item.release_group, 0) + 1
                    )

            # 최고 해상도 선택 - 통일된 정규화 사용
            from src.core.resolution_normalizer import get_best_resolution

            best_resolution = (
                get_best_resolution(list(resolutions.keys())) if resolutions else "Unknown"
            )

            # 가장 많이 사용된 비디오 코덱
            best_video_codec = (
                max(video_codecs.items(), key=lambda x: x[1])[0] if video_codecs else "Unknown"
            )

            # 가장 많이 사용된 오디오 코덱
            best_audio_codec = (
                max(audio_codecs.items(), key=lambda x: x[1])[0] if audio_codecs else "Unknown"
            )

            # 가장 많이 사용된 릴리즈 그룹
            best_release_group = (
                max(release_groups.items(), key=lambda x: x[1])[0] if release_groups else "Unknown"
            )
            if representative.tmdbMatch:
                group_status = "tmdb_matched"
            else:
                statuses = [item.status for item in items]
                if all(s == "parsed" for s in statuses):
                    group_status = "complete"
                elif any(s == "error" for s in statuses):
                    group_status = "error"
                elif any(s == "needs_review" for s in statuses):
                    group_status = "partial"
                else:
                    group_status = "pending"
            self._batch_process_group(
                group_key,
                representative,
                episode_info,
                best_resolution,
                best_video_codec,
                best_audio_codec,
                best_release_group,
                group_status,
            )
        self._group_list.sort(key=lambda x: (x["title"].lower(), x["season"], x["episode_info"]))
        self._calculate_max_title_width()

    def _batch_process_group(
        self,
        group_key: str,
        representative: ParsedItem,
        episode_info: str,
        best_resolution: str,
        best_video_codec: str,
        best_audio_codec: str,
        best_release_group: str,
        group_status: str,
    ):
        """그룹 정보를 배치로 처리하여 성능 향상 (Phase 9.1)"""
        final_path = self._calculate_final_path(representative, self.grouped_items[group_key])
        title = representative.title or representative.detectedTitle or "Unknown"
        if representative.tmdbMatch and representative.tmdbMatch.name:
            title = representative.tmdbMatch.name
        group_info = {
            "key": group_key,
            "title": title,
            "season": representative.season or 1,
            "episode_info": episode_info,
            "file_count": len(self.grouped_items[group_key]),
            "best_resolution": best_resolution,
            "best_video_codec": best_video_codec,
            "best_audio_codec": best_audio_codec,
            "best_release_group": best_release_group,
            "status": group_status,
            "items": self.grouped_items[group_key],
            "tmdb_match": representative.tmdbMatch,
            "tmdb_anime": representative.tmdbMatch,
            "final_path": final_path,
        }
        self._group_list.append(group_info)
        title_width = len(title)
        if title_width > self._max_title_width:
            self._max_title_width = title_width

    def _calculate_final_path(self, representative, items):
        """최종 이동 경로 계산"""
        try:
            base_destination = self.destination_directory
            if representative.tmdbMatch and representative.tmdbMatch.name:
                raw_title = representative.tmdbMatch.name
            else:
                raw_title = representative.title or representative.detectedTitle or "Unknown"
            safe_title = re.sub("[^a-zA-Z0-9가-힣\\s]", "", raw_title)
            safe_title = re.sub("\\s+", " ", safe_title)
            safe_title = safe_title.strip()
            if not safe_title:
                safe_title = "Unknown"
            season = representative.season or 1
            season_folder = f"Season{season:02d}"
            file_names = []
            for item in items:
                if hasattr(item, "filename") and item.filename:
                    file_names.append(item.filename)
                elif hasattr(item, "sourcePath") and item.sourcePath:
                    file_names.append(Path(item.sourcePath).name)
            if file_names:
                file_name_display = file_names[0]
                if len(file_names) > 1:
                    file_name_display += f" (+{len(file_names) - 1}개)"
            else:
                file_name_display = "original_file_names"
            return f"{base_destination}/{safe_title}/{season_folder}/{file_name_display}"
        except Exception as e:
            logger.info("⚠️ 최종 경로 계산 실패: %s", e)
            return "경로 계산 오류"

    def _calculate_max_title_width(self):
        """최대 제목 너비 계산"""
        try:
            font_metrics = QFontMetrics(
                self.parent().font() if self.parent() else QFontMetrics(QFont())
            )
            max_width = 0
            for group_info in self._group_list:
                title = group_info.get("title", "")
                if title:
                    width = font_metrics.horizontalAdvance(title)
                    max_width = max(max_width, width)
            self._max_title_width = max_width + 40 if max_width > 0 else 300
        except Exception as e:
            logger.info("제목 너비 계산 실패: %s", e)
            self._max_title_width = 300

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._group_list)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        if index.row() >= len(self._group_list):
            return QVariant()
        group_info = self._group_list[index.row()]
        col = index.column()
        if role == Qt.DisplayRole:
            if col == 0:
                if group_info.get("tmdb_match") and group_info["tmdb_match"].name:
                    return group_info["tmdb_match"].name
                return group_info.get("title", "Unknown")
            if col == 1:
                return group_info.get("final_path", "N/A")
            if col == 2:
                season = group_info.get("season")
                return f"S{season:02d}" if season is not None else "-"
            if col == 3:
                return str(group_info.get("file_count", 0))
            if col == 4:
                return group_info.get("best_resolution", "-")
            if col == 5:
                return group_info.get("best_video_codec", "-")
            if col == 6:
                return group_info.get("best_audio_codec", "-")
            if col == 7:
                return group_info.get("best_release_group", "-")
            if col == 8:
                status = group_info.get("status", "unknown")
                status_map = {
                    "complete": "✅ 완료",
                    "partial": "⚠️ 부분",
                    "pending": "⏳ 대기중",
                    "error": "❌ 오류",
                    "tmdb_matched": "🎯 TMDB 매치",
                }
                return status_map.get(status, status)
        elif role == Qt.ToolTipRole:
            if col == 0:
                if (
                    group_info.get("tmdb_match")
                    and group_info["tmdb_match"].poster_path
                    and self.tmdb_client
                ):
                    poster_path = group_info["tmdb_match"].poster_path
                    cache_key = f"tooltip_{poster_path}"
                    if cache_key in self._tooltip_cache:
                        return self._tooltip_cache[cache_key]
                    try:
                        poster_path = self.tmdb_client.get_poster_path(
                            group_info["tmdb_match"].poster_path, "w185"
                        )
                        if poster_path and Path(poster_path).exists():
                            pixmap = QPixmap(poster_path)
                            if not pixmap.isNull():
                                scaled_pixmap = pixmap.scaled(
                                    200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation
                                )
                                from PyQt5.QtWidgets import QApplication

                                app = QApplication.instance()
                                if app:
                                    palette = app.palette()
                                    background_color = palette.color(palette.ToolTipBase)
                                    final_pixmap = QPixmap(220, 320)
                                    final_pixmap.fill(background_color)
                                    painter = QPainter(final_pixmap)
                                    painter.setRenderHint(QPainter.Antialiasing)
                                    border_color = palette.color(palette.ToolTipText)
                                    border_color.setAlpha(50)
                                    painter.setPen(border_color)
                                    painter.drawRect(9, 9, 202, 302)
                                    poster_rect = QRect(10, 10, 200, 300)
                                    painter.drawPixmap(poster_rect, scaled_pixmap)
                                    painter.end()
                                    self._tooltip_cache[cache_key] = final_pixmap
                                    return final_pixmap
                                self._tooltip_cache[cache_key] = scaled_pixmap
                                return scaled_pixmap
                    except Exception as e:
                        logger.info("포스터 툴팁 로드 실패: %s", e)
                title = group_info.get("title", "Unknown")
                if group_info.get("tmdb_match") and group_info["tmdb_match"].name:
                    title = group_info["tmdb_match"].name
                return f"제목: {title}"
        elif role == Qt.AccessibleTextRole:
            if col == 0:
                title = group_info.get("title", "Unknown")
                if group_info.get("tmdb_match") and group_info["tmdb_match"].name:
                    title = group_info["tmdb_match"].name
                if group_info.get("tmdb_match") and group_info["tmdb_match"].poster_path:
                    return f"{title} - 포스터 이미지가 있습니다. 마우스를 올리면 포스터를 볼 수 있습니다."
                return f"{title} - 포스터 이미지가 없습니다."
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return QVariant()

    def get_group_at_row(self, row: int) -> dict | None:
        """특정 행의 그룹 정보 반환"""
        if 0 <= row < len(self._group_list):
            return self._group_list[row]
        return None

    def get_column_widths(self) -> dict[int, int]:
        """컬럼별 권장 너비 반환"""
        return {
            (0): self._max_title_width,  # 제목
            (1): 250,  # 최종 이동 경로
            (2): 80,  # 시즌
            (3): 100,  # 에피소드 수
            (4): 100,  # 해상도
            (5): 120,  # 비디오 코덱
            (6): 120,  # 오디오 코덱
            (7): 150,  # 릴리즈 그룹
            (8): 100,  # 상태
        }

    def get_stretch_columns(self) -> list[int]:
        """확장 가능한 컬럼 인덱스 반환"""
        return [1]


class DetailFileModel(QAbstractTableModel):
    """그룹 내 상세 파일 목록을 표시하는 모델"""

    headers = ["파일명", "시즌", "에피소드", "해상도", "코덱", "상태"]

    def __init__(self, items: list[ParsedItem] = None, tmdb_client=None):
        super().__init__()
        self.items = items or []
        self.tmdb_client = tmdb_client
        self._tooltip_cache: dict[str, Any] = {}

    def set_items(self, items: list[ParsedItem]):
        """아이템 목록 설정 및 테이블 새로고침"""
        self.beginResetModel()
        self.items = items
        self.endResetModel()

    def set_files(self, files: list[ParsedItem]):
        """파일 목록 설정 (Phase 9.1: 성능 최적화)"""
        if len(files) > 1000:
            self.beginResetModel()
            self.files = files
            self.endResetModel()
        else:
            self.beginResetModel()
            self.files = files
            self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.items)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        item = self.items[index.row()]
        col = index.column()
        if role == Qt.DisplayRole:
            if col == 0:
                return Path(item.sourcePath).name if item.sourcePath else "—"
            if col == 1:
                return f"S{item.season:02d}" if item.season is not None else "-"
            if col == 2:
                return f"E{item.episode:02d}" if item.episode is not None else "-"
            if col == 3:
                return item.resolution or "-"
            if col == 4:
                return item.codec or "-"
            if col == 5:
                status_map = {
                    "parsed": "✅ 완료",
                    "needs_review": "⚠️ 검토필요",
                    "error": "❌ 오류",
                    "skipped": "⏭️ 건너뛰기",
                    "pending": "⏳ 대기중",
                }
                return status_map.get(item.status, item.status)
        elif role == Qt.ToolTipRole:
            if col == 0:
                if item.tmdbMatch and item.tmdbMatch.poster_path and self.tmdb_client:
                    poster_path = item.tmdbMatch.poster_path
                    cache_key = f"tooltip_{poster_path}"
                    if cache_key in self._tooltip_cache:
                        return self._tooltip_cache[cache_key]
                    try:
                        poster_path = self.tmdb_client.get_poster_path(
                            item.tmdbMatch.poster_path, "w185"
                        )
                        if poster_path and Path(poster_path).exists():
                            pixmap = QPixmap(poster_path)
                            if not pixmap.isNull():
                                scaled_pixmap = pixmap.scaled(
                                    200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation
                                )
                                from PyQt5.QtWidgets import QApplication

                                app = QApplication.instance()
                                if app:
                                    palette = app.palette()
                                    background_color = palette.color(palette.ToolTipBase)
                                    final_pixmap = QPixmap(220, 320)
                                    final_pixmap.fill(background_color)
                                    painter = QPainter(final_pixmap)
                                    painter.setRenderHint(QPainter.Antialiasing)
                                    border_color = palette.color(palette.ToolTipText)
                                    border_color.setAlpha(50)
                                    painter.setPen(border_color)
                                    painter.drawRect(9, 9, 202, 302)
                                    poster_rect = QRect(10, 10, 200, 300)
                                    painter.drawPixmap(poster_rect, scaled_pixmap)
                                    painter.end()
                                    self._tooltip_cache[cache_key] = final_pixmap
                                    return final_pixmap
                                self._tooltip_cache[cache_key] = scaled_pixmap
                                return scaled_pixmap
                    except Exception as e:
                        logger.info("포스터 툴팁 로드 실패: %s", e)
                filename = Path(item.sourcePath).name if item.sourcePath else "Unknown"
                return f"파일: {filename}"
        elif role == Qt.AccessibleTextRole:
            if col == 0:
                filename = Path(item.sourcePath).name if item.sourcePath else "Unknown"
                if item.tmdbMatch and item.tmdbMatch.poster_path:
                    return f"{filename} - 포스터 이미지가 있습니다. 마우스를 올리면 포스터를 볼 수 있습니다."
                return f"{filename} - 포스터 이미지가 없습니다."
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return QVariant()

    def get_column_widths(self) -> dict[int, int]:
        """컬럼별 권장 너비 반환"""
        return {(0): 300, (1): 80, (2): 80, (3): 100, (4): 100, (5): 100}

    def get_stretch_columns(self) -> list[int]:
        """확장 가능한 컬럼 인덱스 반환"""
        return [1]
