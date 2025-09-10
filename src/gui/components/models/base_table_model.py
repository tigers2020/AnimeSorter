"""
기본 테이블 모델 클래스 - 중복 코드 제거를 위한 공통 기능 제공
"""

import logging

logger = logging.getLogger(__name__)
from typing import Any

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtGui import QColor, QFont


class BaseTableModel(QAbstractTableModel):
    """기본 테이블 모델 클래스 - 공통 기능 제공"""

    COLUMNS: list[str] = []

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
        if (
            orientation == Qt.Horizontal
            and role == Qt.DisplayRole
            and 0 <= section < len(self.COLUMNS)
        ):
            return self.COLUMNS[section]
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(section + 1)
        return None

    def _get_display_data(self, row_data: dict[str, Any], column: int) -> str:
        """표시 데이터 반환 - 하위 클래스에서 오버라이드"""
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")

    def _get_tooltip_data(self, row_data: dict[str, Any], column: int) -> str:
        """툴팁 데이터 반환 - 하위 클래스에서 오버라이드"""
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")

    def _get_font_role(self, row_data: dict[str, Any], column: int) -> QFont:
        """폰트 역할 반환 - 하위 클래스에서 오버라이드"""
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")

    def _get_background_role(self, row_data: dict[str, Any], column: int) -> QColor:
        """배경 역할 반환 - 하위 클래스에서 오버라이드"""
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")

    def _get_foreground_role(self, row_data: dict[str, Any], column: int) -> QColor:
        """전경 역할 반환 - 하위 클래스에서 오버라이드"""
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")

    def set_data(self, data: list[dict[str, Any]]) -> None:
        """데이터 설정"""
        self.beginResetModel()
        self._data = data
        self._filtered_data = data.copy()
        self.endResetModel()

    def get_data(self) -> list[dict[str, Any]]:
        """데이터 반환"""
        return self._data.copy()

    def get_filtered_data(self) -> list[dict[str, Any]]:
        """필터링된 데이터 반환"""
        return self._filtered_data.copy()

    def set_filter(self, filter_text: str) -> None:
        """필터 설정"""
        self._current_filter = filter_text.lower()
        self._apply_filter()
        self.layoutChanged.emit()

    def _apply_filter(self) -> None:
        """필터 적용 - 하위 클래스에서 오버라이드"""
        if not self._current_filter:
            self._filtered_data = self._data.copy()
        else:
            self._filtered_data = [item for item in self._data if self._matches_filter(item)]

    def _matches_filter(self, item: dict[str, Any]) -> bool:
        """필터 매칭 확인 - 하위 클래스에서 오버라이드"""
        for value in item.values():
            if isinstance(value, str) and self._current_filter in value.lower():
                return True
            if isinstance(value, int | float) and self._current_filter in str(value):
                return True
        return False

    def clear_filter(self) -> None:
        """필터 초기화"""
        self._current_filter = ""
        self._filtered_data = self._data.copy()
        self.layoutChanged.emit()

    def get_current_filter(self) -> str:
        """현재 필터 반환"""
        return self._current_filter

    def add_row(self, row_data: dict[str, Any]) -> None:
        """행 추가"""
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append(row_data)
        if self._matches_filter(row_data):
            self._filtered_data.append(row_data)
        self.endInsertRows()

    def remove_row(self, row: int) -> bool:
        """행 제거"""
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            removed_item = self._data.pop(row)
            if removed_item in self._filtered_data:
                self._filtered_data.remove(removed_item)
            self.endRemoveRows()
            return True
        return False

    def update_row(self, row: int, row_data: dict[str, Any]) -> bool:
        """행 업데이트"""
        if 0 <= row < len(self._data):
            self._data[row] = row_data
            if row < len(self._filtered_data):
                self._filtered_data[row] = row_data
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
            return True
        return False

    def clear_data(self) -> None:
        """데이터 초기화"""
        self.beginResetModel()
        self._data.clear()
        self._filtered_data.clear()
        self._current_filter = ""
        self.endResetModel()

    def get_row_data(self, row: int) -> dict[str, Any] | None:
        """특정 행의 데이터 반환"""
        if 0 <= row < len(self._filtered_data):
            return self._filtered_data[row].copy()
        return None

    def get_column_data(self, column: int) -> list[Any]:
        """특정 컬럼의 데이터 반환"""
        if 0 <= column < self.columnCount():
            return [
                row_data.get(self._get_column_key(column), "") for row_data in self._filtered_data
            ]
        return []

    def _get_column_key(self, column: int) -> str:
        """컬럼 인덱스에 해당하는 키 반환 - 하위 클래스에서 오버라이드"""
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")

    def sort_data(self, column: int, order: Qt.SortOrder) -> None:
        """데이터 정렬"""
        if 0 <= column < self.columnCount():
            reverse = order == Qt.DescendingOrder
            self._filtered_data.sort(key=lambda x: self._get_sort_key(x, column), reverse=reverse)
            self.layoutChanged.emit()

    def _get_sort_key(self, row_data: dict[str, Any], column: int) -> Any:
        """정렬 키 반환 - 하위 클래스에서 오버라이드"""
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")
