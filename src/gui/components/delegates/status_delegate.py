"""
상태 델리게이트 클래스 - Phase 2.3 결과 뷰 컴포넌트 분할
상태 컬럼을 위한 특화된 델리게이트로, 상태별 색상과 아이콘을 지원합니다.
"""

import logging

logger = logging.getLogger(__name__)
from typing import Any

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtWidgets import QApplication, QStyle, QStyleOptionViewItem

from src.base_cell_delegate import BaseCellDelegate


class StatusDelegate(BaseCellDelegate):
    """상태 델리게이트 클래스"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_font = QFont()
        self._status_font.setPointSize(9)
        self._status_font.setBold(True)
        self._status_colors = {
            "완료": QColor(0, 128, 0),
            "대기": QColor(128, 128, 128),
            "충돌": QColor(255, 0, 0),
            "중복": QColor(255, 165, 0),
            "미매칭": QColor(128, 0, 128),
            "처리중": QColor(0, 0, 255),
        }
        self._status_backgrounds = {
            "완료": QColor(200, 255, 200),
            "대기": QColor(240, 240, 240),
            "충돌": QColor(255, 200, 200),
            "중복": QColor(255, 255, 200),
            "미매칭": QColor(255, 200, 255),
            "처리중": QColor(200, 200, 255),
        }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Any):
        """셀 그리기 - 상태 특화"""
        self.initStyleOption(option, index)
        status = self._get_status_text(index)
        background_color = self._get_status_background(status)
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, background_color)
        if status:
            text_color = self._get_status_color(status)
            painter.setPen(text_color)
            painter.setFont(self._status_font)
            text_rect = option.rect.adjusted(4, 2, -4, -2)
            painter.drawText(text_rect, Qt.AlignCenter, status)

    def sizeHint(self, option: QStyleOptionViewItem, index: Any) -> QSize:
        """셀 크기 힌트 반환 - 상태 특화"""
        status = self._get_status_text(index)
        if status:
            font_metrics = QApplication.fontMetrics()
            text_width = font_metrics.horizontalAdvance(status) + 8
            text_height = font_metrics.height() + 4
            return QSize(max(text_width, 80), text_height)
        return QSize(80, 20)

    def _get_status_text(self, index: Any) -> str:
        """상태 텍스트 반환"""
        if hasattr(index, "data"):
            status_data = index.data(Qt.DisplayRole)
            if status_data is not None:
                return str(status_data)
        return ""

    def _get_status_color(self, status: str) -> QColor:
        """상태별 색상 반환"""
        return self._status_colors.get(status, QColor(0, 0, 0))

    def _get_status_background(self, status: str) -> QColor:
        """상태별 배경색 반환"""
        return self._status_backgrounds.get(status, QColor(255, 255, 255))

    def _get_tooltip_text(self, index: Any) -> str:
        """툴팁 텍스트 반환 - 상태 특화"""
        if hasattr(index, "data"):
            tooltip_data = index.data(Qt.ToolTipRole)
            if tooltip_data:
                return str(tooltip_data)
            status = self._get_status_text(index)
            if status:
                status_descriptions = {
                    "완료": "파일 정리가 완료되었습니다",
                    "대기": "파일 정리를 기다리고 있습니다",
                    "충돌": "파일 정리 중 충돌이 발생했습니다",
                    "중복": "중복된 파일이 발견되었습니다",
                    "미매칭": "메타데이터와 매칭되지 않았습니다",
                    "처리중": "파일 정리를 진행 중입니다",
                }
                description = status_descriptions.get(status, f"상태: {status}")
                return f"상태: {status}\n{description}"
        return ""
