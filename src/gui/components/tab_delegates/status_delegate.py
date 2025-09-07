"""
상태 델리게이트 클래스 - Phase 2.3 결과 뷰 컴포넌트 분할
상태 컬럼을 위한 특화된 델리게이트로, 상태별 색상과 아이콘을 지원합니다.
"""

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

        # 상태별 색상 정의
        self._status_colors = {
            "완료": QColor(0, 128, 0),  # 진한 초록
            "대기": QColor(128, 128, 128),  # 회색
            "충돌": QColor(255, 0, 0),  # 빨강
            "중복": QColor(255, 165, 0),  # 주황
            "미매칭": QColor(128, 0, 128),  # 보라
            "처리중": QColor(0, 0, 255),  # 파랑
        }

        # 상태별 배경색 정의
        self._status_backgrounds = {
            "완료": QColor(200, 255, 200),  # 연한 초록
            "대기": QColor(240, 240, 240),  # 연한 회색
            "충돌": QColor(255, 200, 200),  # 연한 빨강
            "중복": QColor(255, 255, 200),  # 연한 노랑
            "미매칭": QColor(255, 200, 255),  # 연한 보라
            "처리중": QColor(200, 200, 255),  # 연한 파랑
        }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Any):
        """셀 그리기 - 상태 특화"""
        # 기본 스타일 적용
        self.initStyleOption(option, index)

        # 상태별 배경색 설정
        status = self._get_status_text(index)
        background_color = self._get_status_background(status)

        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, background_color)

        # 상태 텍스트 그리기
        if status:
            # 상태별 색상 설정
            text_color = self._get_status_color(status)
            painter.setPen(text_color)
            painter.setFont(self._status_font)

            # 텍스트 정렬 및 위치 계산
            text_rect = option.rect.adjusted(4, 2, -4, -2)

            # 상태 텍스트를 중앙에 배치
            painter.drawText(text_rect, Qt.AlignCenter, status)

    def sizeHint(self, option: QStyleOptionViewItem, index: Any) -> QSize:
        """셀 크기 힌트 반환 - 상태 특화"""
        status = self._get_status_text(index)
        if status:
            # 상태 텍스트 길이에 따른 크기 계산
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
            # 기본 툴팁 데이터
            tooltip_data = index.data(Qt.ToolTipRole)
            if tooltip_data:
                return str(tooltip_data)

            # 상태 정보로 툴팁 구성
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
