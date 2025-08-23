"""
기본 그룹 모델 클래스 - Phase 2.2 결과 뷰 컴포넌트 분할
탭별 모델의 공통 기능을 제공하는 기본 클래스입니다.
"""

from typing import Any, Optional

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QColor, QFont


class BaseGroupModel(QAbstractTableModel):
    """기본 그룹 모델 클래스"""

    # 컬럼 헤더 정의
    COLUMNS = ["제목", "최종 이동 경로", "시즌", "에피소드 수", "최고 해상도", "상태"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[dict[str, Any]] = []
        self._filtered_data: list[dict[str, Any]] = []
        self._current_filter: str = ""

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """행 수 반환"""
        if parent.isValid():
            return 0
        return len(self._filtered_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """컬럼 수 반환"""
        if parent.isValid():
            return 0
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """데이터 반환"""
        if not index.isValid():
            return None

        if index.row() >= len(self._filtered_data):
            return None

        row_data = self._filtered_data[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            return self._get_display_data(row_data, column)
        if role == Qt.ToolTipRole:
            return self._get_tooltip_data(row_data, column)
        if role == Qt.FontRole:
            return self._get_font_role(row_data, column)
        if role == Qt.BackgroundRole:
            return self._get_background_role(row_data, column)
        if role == Qt.ForegroundRole:
            return self._get_foreground_role(row_data, column)

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Any:
        """헤더 데이터 반환"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(section + 1)
        return None

    def _get_display_data(self, row_data: dict[str, Any], column: int) -> str:
        """표시 데이터 반환"""
        if column == 0:  # 제목
            return row_data.get("title", "제목 없음")
        if column == 1:  # 최종 이동 경로
            return row_data.get("final_path", "경로 없음")
        if column == 2:  # 시즌
            return str(row_data.get("season", "N/A"))
        if column == 3:  # 에피소드 수
            return str(row_data.get("episode_count", 0))
        if column == 4:  # 최고 해상도
            return row_data.get("max_resolution", "N/A")
        if column == 5:  # 상태
            return row_data.get("status", "알 수 없음")
        return ""

    def _get_tooltip_data(self, row_data: dict[str, Any], column: int) -> str:
        """툴팁 데이터 반환"""
        if column == 0:  # 제목
            return f"제목: {row_data.get('title', '제목 없음')}\n원제: {row_data.get('original_title', 'N/A')}"
        elif column == 1:  # 최종 이동 경로
            return f"최종 이동 경로: {row_data.get('final_path', '경로 없음')}"
        elif column == 2:  # 시즌
            return f"시즌: {row_data.get('season', 'N/A')}"
        elif column == 3:  # 에피소드 수
            return f"에피소드 수: {row_data.get('episode_count', 0)}"
        elif column == 4:  # 최고 해상도
            return f"최고 해상도: {row_data.get('max_resolution', 'N/A')}"
        elif column == 5:  # 상태
            return f"상태: {row_data.get('status', '알 수 없음')}"
        return ""

    def _get_font_role(self, row_data: dict[str, Any], column: int) -> QFont:
        """폰트 역할 반환"""
        font = QFont()
        if column == 0:  # 제목은 굵게
            font.setBold(True)
        return font

    def _get_background_role(self, row_data: dict[str, Any], column: int) -> Optional[QColor]:
        """배경색 역할 반환"""
        # 상태에 따른 배경색 설정
        status = row_data.get("status", "")
        if status == "완료":
            return QColor(200, 255, 200)  # 연한 초록
        if status == "충돌":
            return QColor(255, 200, 200)  # 연한 빨강
        if status == "중복":
            return QColor(255, 255, 200)  # 연한 노랑
        return None

    def _get_foreground_role(self, row_data: dict[str, Any], column: int) -> Optional[QColor]:
        """전경색 역할 반환"""
        # 상태에 따른 전경색 설정
        status = row_data.get("status", "")
        if status == "완료":
            return QColor(0, 100, 0)  # 진한 초록
        if status == "충돌":
            return QColor(100, 0, 0)  # 진한 빨강
        if status == "중복":
            return QColor(100, 100, 0)  # 진한 노랑
        return None

    def set_data(self, data: list[dict[str, Any]]):
        """데이터 설정"""
        self.beginResetModel()
        self._data = data.copy()
        self._filtered_data = data.copy()
        self.endResetModel()

    def add_data(self, item: dict[str, Any]):
        """데이터 추가"""
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append(item)
        if self._matches_filter(item):
            self._filtered_data.append(item)
        self.endInsertRows()

    def remove_data(self, index: int):
        """데이터 제거"""
        if 0 <= index < len(self._data):
            self.beginRemoveRows(QModelIndex(), index, index)
            item = self._data.pop(index)
            if item in self._filtered_data:
                filtered_index = self._filtered_data.index(item)
                self._filtered_data.pop(filtered_index)
            self.endRemoveRows()

    def clear_data(self):
        """데이터 초기화"""
        self.beginResetModel()
        self._data.clear()
        self._filtered_data.clear()
        self.endResetModel()

    def filter_data(self, filter_text: str):
        """데이터 필터링"""
        self.beginResetModel()
        self._current_filter = filter_text.lower()
        if not filter_text:
            self._filtered_data = self._data.copy()
        else:
            self._filtered_data = [item for item in self._data if self._matches_filter(item)]
        self.endResetModel()

    def _matches_filter(self, item: dict[str, Any]) -> bool:
        """필터 조건 확인"""
        if not self._current_filter:
            return True

        # 제목과 경로에서 검색
        title = item.get("title", "").lower()
        path = item.get("final_path", "").lower()
        return self._current_filter in title or self._current_filter in path

    def get_row_data(self, row: int) -> Optional[dict[str, Any]]:
        """행 데이터 반환"""
        if 0 <= row < len(self._filtered_data):
            return self._filtered_data[row]
        return None

    def get_all_data(self) -> list[dict[str, Any]]:
        """모든 데이터 반환"""
        return self._data.copy()

    def get_filtered_data(self) -> list[dict[str, Any]]:
        """필터링된 데이터 반환"""
        return self._filtered_data.copy()
