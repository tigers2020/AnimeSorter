"""
테이블 모델 및 필터 프록시
파싱된 애니메이션 아이템을 테이블에 표시하고 필터링하는 기능을 제공합니다.
"""

import re
from pathlib import Path
from typing import Any

from managers.anime_data_manager import ParsedItem
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QRect, Qt, QVariant
from PyQt5.QtGui import QFont, QFontMetrics, QPainter, QPixmap


class GroupedListModel(QAbstractTableModel):
    """그룹화된 애니메이션 목록을 표시하는 모델"""

    headers = ["제목", "최종 이동 경로", "시즌", "에피소드 수", "최고 해상도", "상태"]

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
        self._group_list = []  # 그룹 리스트 (순서 유지)
        self._max_title_width = 0  # 최대 제목 너비 (동적 계산용)
        self._tooltip_cache: dict[str, Any] = {}  # 툴팁 이미지 캐시
        self._update_group_list()

    def set_grouped_items(self, grouped_items: dict[str, list]):
        """그룹화된 아이템 설정 (Phase 9.1: 성능 최적화)"""
        # Phase 9.1: 대용량 데이터 처리 최적화
        if len(grouped_items) > 1000:  # 대용량 데이터 감지
            # 정렬을 일시 해제하여 성능 향상
            self.beginResetModel()
            self.grouped_items = grouped_items
            self._update_group_list()
            self.endResetModel()
        else:
            # 소량 데이터는 기존 방식 사용
            self.beginResetModel()
            self.grouped_items = grouped_items
            self._update_group_list()
            self.endResetModel()

    def _update_group_list(self):
        """그룹 리스트 업데이트"""
        self._group_list = []
        self._max_title_width = 0  # 최대 제목 너비 초기화

        for group_key, items in self.grouped_items.items():
            if not items:
                continue

            # 그룹 정보 생성
            representative = items[0]

            # 에피소드 범위 계산
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

            # 해상도별 분포 (더 정확한 해상도 정보 사용)
            resolutions = {}
            for item in items:
                res = item.resolution or "Unknown"
                if res != "Unknown":
                    # 해상도 정규화 (예: 1080p, 720p 등)
                    if "1080" in res or "1920" in res:
                        res = "1080p"
                    elif "720" in res or "1280" in res:
                        res = "720p"
                    elif "480" in res or "854" in res:
                        res = "480p"
                    elif "080" in res:  # 080p는 1080p로 수정
                        res = "1080p"
                resolutions[res] = resolutions.get(res, 0) + 1

            # 가장 높은 해상도 선택 (우선순위: 1080p > 720p > 480p > Unknown)
            resolution_priority = {"1080p": 4, "720p": 3, "480p": 2, "Unknown": 1}
            best_resolution = (
                max(resolutions.items(), key=lambda x: (resolution_priority.get(x[0], 0), x[1]))[0]
                if resolutions
                else "Unknown"
            )

            # 그룹 상태 (TMDB 매치가 있으면 우선, 그 다음 기존 로직)
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

            # Phase 9.1: 성능 최적화를 위한 배치 처리
            self._batch_process_group(
                group_key, representative, episode_info, best_resolution, group_status
            )

        # Phase 9.1: 성능 최적화를 위한 배치 처리 완료 후 정렬
        # 제목, 시즌, 에피소드 순으로 정렬
        self._group_list.sort(key=lambda x: (x["title"].lower(), x["season"], x["episode_info"]))

        # 최대 제목 너비 계산 (동적 너비 조정용)
        self._calculate_max_title_width()

    def _batch_process_group(
        self,
        group_key: str,
        representative: ParsedItem,
        episode_info: str,
        best_resolution: str,
        group_status: str,
    ):
        """그룹 정보를 배치로 처리하여 성능 향상 (Phase 9.1)"""
        # 최종 이동 경로 계산
        final_path = self._calculate_final_path(representative, self.grouped_items[group_key])

        # 제목 결정 (TMDB 매치가 있으면 TMDB 제목, 없으면 원본 제목)
        title = representative.title or representative.detectedTitle or "Unknown"
        if representative.tmdbMatch and representative.tmdbMatch.name:
            title = representative.tmdbMatch.name

        # 그룹 정보를 한 번에 생성하여 메모리 효율성 향상
        group_info = {
            "key": group_key,
            "title": title,
            "season": representative.season or 1,
            "episode_info": episode_info,
            "file_count": len(self.grouped_items[group_key]),
            "best_resolution": best_resolution,
            "status": group_status,
            "items": self.grouped_items[group_key],
            "tmdb_match": representative.tmdbMatch,
            "tmdb_anime": representative.tmdbMatch,  # TMDB 애니메이션 정보
            "final_path": final_path,  # 최종 이동 경로
        }

        self._group_list.append(group_info)

        # 최대 제목 너비 계산 (성능 최적화)
        title_width = len(title)
        if title_width > self._max_title_width:
            self._max_title_width = title_width

    def _calculate_final_path(self, representative, items):
        """최종 이동 경로 계산"""
        try:
            # 기본 대상 폴더 (실제로는 설정에서 가져와야 함)
            base_destination = self.destination_directory

            # 제목 결정 (TMDB 매치가 있으면 TMDB 제목, 없으면 원본 제목)
            if representative.tmdbMatch and representative.tmdbMatch.name:
                raw_title = representative.tmdbMatch.name
            else:
                raw_title = representative.title or representative.detectedTitle or "Unknown"

            # 특수문자 제거 및 정제 (알파벳, 숫자, 한글, 공백만 허용)
            safe_title = re.sub(r"[^a-zA-Z0-9가-힣\s]", "", raw_title)
            # 연속된 공백을 하나로 치환
            safe_title = re.sub(r"\s+", " ", safe_title)
            # 앞뒤 공백 제거
            safe_title = safe_title.strip()

            if not safe_title:
                safe_title = "Unknown"

            # 시즌 정보
            season = representative.season or 1
            season_folder = f"Season{season:02d}"

            # 파일명들 (원본 파일명들)
            file_names = []
            for item in items:
                if hasattr(item, "filename") and item.filename:
                    file_names.append(item.filename)
                elif hasattr(item, "sourcePath") and item.sourcePath:
                    file_names.append(Path(item.sourcePath).name)

            # 파일명이 있으면 첫 번째 파일명 표시, 없으면 "original_file_names"
            if file_names:
                file_name_display = file_names[0]
                if len(file_names) > 1:
                    file_name_display += f" (+{len(file_names) - 1}개)"
            else:
                file_name_display = "original_file_names"

            # 최종 경로 구성
            return f"{base_destination}/{safe_title}/{season_folder}/{file_name_display}"

        except Exception as e:
            print(f"⚠️ 최종 경로 계산 실패: {e}")
            return "경로 계산 오류"

    def _calculate_max_title_width(self):
        """최대 제목 너비 계산"""
        try:
            # 기본 폰트 메트릭스 사용
            font_metrics = QFontMetrics(
                self.parent().font() if self.parent() else QFontMetrics(QFont())
            )

            max_width = 0
            for group_info in self._group_list:
                title = group_info.get("title", "")
                if title:
                    width = font_metrics.horizontalAdvance(title)
                    max_width = max(max_width, width)

            # 좌우 패딩 추가 (각각 20px)
            self._max_title_width = max_width + 40 if max_width > 0 else 300
        except Exception as e:
            print(f"제목 너비 계산 실패: {e}")
            self._max_title_width = 300  # 기본값

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
            if col == 0:  # 제목 - TMDB 매치가 있으면 TMDB 제목 우선 사용
                if group_info.get("tmdb_match") and group_info["tmdb_match"].name:
                    return group_info["tmdb_match"].name  # TMDB 한글 제목
                return group_info.get("title", "Unknown")
            if col == 1:  # 최종 이동 경로
                return group_info.get("final_path", "N/A")
            if col == 2:  # 시즌
                season = group_info.get("season")
                return f"S{season:02d}" if season is not None else "-"
            if col == 3:  # 에피소드 수
                return str(group_info.get("file_count", 0))
            if col == 4:  # 최고 해상도
                return group_info.get("best_resolution", "-")
            if col == 5:  # 상태
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
            if col == 0:  # 제목 컬럼에 포스터 툴팁 표시
                if (
                    group_info.get("tmdb_match")
                    and group_info["tmdb_match"].poster_path
                    and self.tmdb_client
                ):
                    # 캐시 키 생성
                    poster_path = group_info["tmdb_match"].poster_path
                    cache_key = f"tooltip_{poster_path}"

                    # 캐시에서 확인
                    if cache_key in self._tooltip_cache:
                        return self._tooltip_cache[cache_key]

                    try:
                        poster_path = self.tmdb_client.get_poster_path(
                            group_info["tmdb_match"].poster_path, "w185"
                        )

                        if poster_path and Path(poster_path).exists():
                            pixmap = QPixmap(poster_path)
                            if not pixmap.isNull():
                                # 툴팁용 포스터 크기 조정 (200x300 픽셀)
                                scaled_pixmap = pixmap.scaled(
                                    200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation
                                )

                                # 테마에 맞는 배경과 테두리 추가
                                from PyQt5.QtWidgets import QApplication

                                app = QApplication.instance()
                                if app:
                                    palette = app.palette()
                                    background_color = palette.color(palette.ToolTipBase)

                                    # 배경이 있는 새로운 픽스맵 생성
                                    final_pixmap = QPixmap(220, 320)  # 여백 포함
                                    final_pixmap.fill(background_color)

                                    # 포스터를 중앙에 배치
                                    painter = QPainter(final_pixmap)
                                    painter.setRenderHint(QPainter.Antialiasing)

                                    # 테두리 그리기
                                    border_color = palette.color(palette.ToolTipText)
                                    border_color.setAlpha(50)  # 반투명
                                    painter.setPen(border_color)
                                    painter.drawRect(9, 9, 202, 302)

                                    # 포스터 그리기
                                    poster_rect = QRect(10, 10, 200, 300)
                                    painter.drawPixmap(poster_rect, scaled_pixmap)
                                    painter.end()

                                    # 캐시에 저장
                                    self._tooltip_cache[cache_key] = final_pixmap
                                    return final_pixmap

                                # 캐시에 저장
                                self._tooltip_cache[cache_key] = scaled_pixmap
                                return scaled_pixmap
                    except Exception as e:
                        print(f"포스터 툴팁 로드 실패: {e}")

                # 포스터가 없으면 제목 정보만 표시
                title = group_info.get("title", "Unknown")
                if group_info.get("tmdb_match") and group_info["tmdb_match"].name:
                    title = group_info["tmdb_match"].name
                return f"제목: {title}"

        elif role == Qt.AccessibleTextRole:
            if col == 0:  # 제목 컬럼의 접근성 텍스트
                title = group_info.get("title", "Unknown")
                if group_info.get("tmdb_match") and group_info["tmdb_match"].name:
                    title = group_info["tmdb_match"].name

                # 포스터 정보 추가
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
            0: self._max_title_width,  # 제목 (동적 너비)
            1: 250,  # 최종 이동 경로
            2: 80,  # 시즌
            3: 100,  # 에피소드 수
            4: 100,  # 최고 해상도
            5: 100,  # 상태
        }

    def get_stretch_columns(self) -> list[int]:
        """확장 가능한 컬럼 인덱스 반환"""
        return [1]  # 제목 컬럼만 확장 가능


class DetailFileModel(QAbstractTableModel):
    """그룹 내 상세 파일 목록을 표시하는 모델"""

    headers = ["파일명", "시즌", "에피소드", "해상도", "코덱", "상태"]

    def __init__(self, items: list[ParsedItem] = None, tmdb_client=None):
        super().__init__()
        self.items = items or []
        self.tmdb_client = tmdb_client
        self._tooltip_cache: dict[str, Any] = {}  # 툴팁 이미지 캐시

    def set_items(self, items: list[ParsedItem]):
        """아이템 목록 설정 및 테이블 새로고침"""
        self.beginResetModel()
        self.items = items
        self.endResetModel()

    def set_files(self, files: list[ParsedItem]):
        """파일 목록 설정 (Phase 9.1: 성능 최적화)"""
        # Phase 9.1: 대용량 데이터 처리 최적화
        if len(files) > 1000:  # 대용량 데이터 감지
            # 정렬을 일시 해제하여 성능 향상
            self.beginResetModel()
            self.files = files
            self.endResetModel()
        else:
            # 소량 데이터는 기존 방식 사용
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
            if col == 0:  # 파일명
                return Path(item.sourcePath).name if item.sourcePath else "—"
            if col == 1:  # 시즌
                return f"S{item.season:02d}" if item.season is not None else "-"
            if col == 2:  # 에피소드
                return f"E{item.episode:02d}" if item.episode is not None else "-"
            if col == 3:  # 해상도
                return item.resolution or "-"
            if col == 4:  # 코덱
                return item.codec or "-"
            if col == 5:  # 상태
                status_map = {
                    "parsed": "✅ 완료",
                    "needs_review": "⚠️ 검토필요",
                    "error": "❌ 오류",
                    "skipped": "⏭️ 건너뛰기",
                    "pending": "⏳ 대기중",
                }
                return status_map.get(item.status, item.status)

        elif role == Qt.ToolTipRole:
            if col == 0:  # 파일명 컬럼에 포스터 툴팁 표시
                if item.tmdbMatch and item.tmdbMatch.poster_path and self.tmdb_client:
                    # 캐시 키 생성
                    poster_path = item.tmdbMatch.poster_path
                    cache_key = f"tooltip_{poster_path}"

                    # 캐시에서 확인
                    if cache_key in self._tooltip_cache:
                        return self._tooltip_cache[cache_key]

                    try:
                        poster_path = self.tmdb_client.get_poster_path(
                            item.tmdbMatch.poster_path, "w185"
                        )

                        if poster_path and Path(poster_path).exists():
                            pixmap = QPixmap(poster_path)
                            if not pixmap.isNull():
                                # 툴팁용 포스터 크기 조정 (200x300 픽셀)
                                scaled_pixmap = pixmap.scaled(
                                    200, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation
                                )

                                # 테마에 맞는 배경과 테두리 추가
                                from PyQt5.QtWidgets import QApplication

                                app = QApplication.instance()
                                if app:
                                    palette = app.palette()
                                    background_color = palette.color(palette.ToolTipBase)

                                    # 배경이 있는 새로운 픽스맵 생성
                                    final_pixmap = QPixmap(220, 320)  # 여백 포함
                                    final_pixmap.fill(background_color)

                                    # 포스터를 중앙에 배치
                                    painter = QPainter(final_pixmap)
                                    painter.setRenderHint(QPainter.Antialiasing)

                                    # 테두리 그리기
                                    border_color = palette.color(palette.ToolTipText)
                                    border_color.setAlpha(50)  # 반투명
                                    painter.setPen(border_color)
                                    painter.drawRect(9, 9, 202, 302)

                                    # 포스터 그리기
                                    poster_rect = QRect(10, 10, 200, 300)
                                    painter.drawPixmap(poster_rect, scaled_pixmap)
                                    painter.end()

                                    # 캐시에 저장
                                    self._tooltip_cache[cache_key] = final_pixmap
                                    return final_pixmap

                                # 캐시에 저장
                                self._tooltip_cache[cache_key] = scaled_pixmap
                                return scaled_pixmap
                    except Exception as e:
                        print(f"포스터 툴팁 로드 실패: {e}")

                # 포스터가 없으면 파일 정보만 표시
                filename = Path(item.sourcePath).name if item.sourcePath else "Unknown"
                return f"파일: {filename}"

        elif role == Qt.AccessibleTextRole:
            if col == 0:  # 파일명 컬럼의 접근성 텍스트
                filename = Path(item.sourcePath).name if item.sourcePath else "Unknown"

                # 포스터 정보 추가
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
        return {
            0: 300,  # 파일명
            1: 80,  # 시즌
            2: 80,  # 에피소드
            3: 100,  # 해상도
            4: 100,  # 코덱
            5: 100,  # 상태
        }

    def get_stretch_columns(self) -> list[int]:
        """확장 가능한 컬럼 인덱스 반환"""
        return [1]  # 파일명 컬럼만 확장 가능
