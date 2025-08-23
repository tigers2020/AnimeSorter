"""
텍스트 프리뷰 델리게이트 클래스 - Phase 2.3 결과 뷰 컴포넌트 분할
제목 컬럼을 위한 특화된 델리게이트로, 포스터 이미지 툴팁을 지원합니다.
"""

from typing import Any

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtWidgets import QApplication, QStyle, QStyleOptionViewItem

from .base_cell_delegate import BaseCellDelegate


class TextPreviewDelegate(BaseCellDelegate):
    """텍스트 프리뷰 델리게이트 클래스"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preview_font = QFont()
        self._preview_font.setPointSize(9)
        self._preview_font.setBold(True)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Any):
        """셀 그리기 - 텍스트 프리뷰 특화"""
        # 기본 스타일 적용
        self.initStyleOption(option, index)

        # 배경 그리기
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())

        # 텍스트 그리기
        text = self._get_display_text(index)
        if text:
            # 선택 상태에 따른 색상 설정
            if option.state & QStyle.State_Selected:
                painter.setPen(option.palette.highlightedText().color())
            else:
                painter.setPen(option.palette.text().color())

            painter.setFont(self._preview_font)

            # 텍스트 정렬 및 위치 계산 (여백 추가)
            text_rect = option.rect.adjusted(8, 2, -8, -2)

            # 텍스트가 길 경우 말줄임표 처리
            elided_text = painter.fontMetrics().elidedText(text, Qt.ElideRight, text_rect.width())

            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_text)

    def sizeHint(self, option: QStyleOptionViewItem, index: Any) -> QSize:
        """셀 크기 힌트 반환 - 텍스트 프리뷰 특화"""
        text = self._get_display_text(index)
        if text:
            # 텍스트 길이에 따른 크기 계산 (여백 추가)
            font_metrics = QApplication.fontMetrics()
            text_width = font_metrics.horizontalAdvance(text) + 16
            text_height = font_metrics.height() + 6

            return QSize(max(text_width, 150), text_height)

        return QSize(150, 22)

    def _get_display_text(self, index: Any) -> str:
        """표시할 텍스트 반환 - 텍스트 프리뷰 특화"""
        if hasattr(index, "data"):
            # 제목 데이터 가져오기
            title_data = index.data(Qt.DisplayRole)
            if title_data is not None:
                title = str(title_data)

                # 원제 정보가 있으면 추가
                original_title = index.data(Qt.UserRole)
                if original_title and original_title != title:
                    return f"{title} ({original_title})"

                return title
        return ""

    def _get_tooltip_text(self, index: Any) -> str:
        """툴팁 텍스트 반환 - 텍스트 프리뷰 특화"""
        if hasattr(index, "data"):
            # 기본 툴팁 데이터
            tooltip_data = index.data(Qt.ToolTipRole)
            if tooltip_data:
                return str(tooltip_data)

            # 제목과 원제 정보로 툴팁 구성
            title = index.data(Qt.DisplayRole)
            original_title = index.data(Qt.UserRole)

            if title and original_title and title != original_title:
                return f"제목: {title}\n원제: {original_title}"
            elif title:
                return f"제목: {title}"

        return ""
