"""
기본 셀 델리게이트 클래스 - Phase 2.3 결과 뷰 컴포넌트 분할
탭별 델리게이트의 공통 기능을 제공하는 기본 클래스입니다.
"""

import logging

logger = logging.getLogger(__name__)
from typing import Any

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem


class BaseCellDelegate(QStyledItemDelegate):
    """기본 셀 델리게이트 클래스"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._default_font = QFont()
        self._default_font.setPointSize(9)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Any):
        """셀 그리기"""
        self.initStyleOption(option, index)
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())
        text = self._get_display_text(index)
        if text:
            painter.setPen(option.palette.text().color())
            painter.setFont(self._default_font)
            text_rect = option.rect.adjusted(4, 2, -4, -2)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

    def sizeHint(self, option: QStyleOptionViewItem, index: Any) -> QSize:
        """셀 크기 힌트 반환"""
        text = self._get_display_text(index)
        if text:
            font_metrics = QApplication.fontMetrics()
            text_width = font_metrics.horizontalAdvance(text) + 8
            text_height = font_metrics.height() + 4
            return QSize(max(text_width, 100), text_height)
        return QSize(100, 20)

    def _get_display_text(self, index: Any) -> str:
        """표시할 텍스트 반환"""
        if hasattr(index, "data"):
            data = index.data(Qt.DisplayRole)
            if data is not None:
                return str(data)
        return ""

    def _get_tooltip_text(self, index: Any) -> str:
        """툴팁 텍스트 반환"""
        if hasattr(index, "data"):
            data = index.data(Qt.ToolTipRole)
            if data is not None:
                return str(data)
        return ""

    def _get_background_color(self, index: Any) -> QColor | None:
        """배경색 반환"""
        if hasattr(index, "data"):
            data = index.data(Qt.BackgroundRole)
            if isinstance(data, QColor):
                return data
        return None

    def _get_foreground_color(self, index: Any) -> QColor | None:
        """전경색 반환"""
        if hasattr(index, "data"):
            data = index.data(Qt.ForegroundRole)
            if isinstance(data, QColor):
                return data
        return None

    def _get_font(self, index: Any) -> QFont | None:
        """폰트 반환"""
        if hasattr(index, "data"):
            data = index.data(Qt.FontRole)
            if isinstance(data, QFont):
                return data
        return None
