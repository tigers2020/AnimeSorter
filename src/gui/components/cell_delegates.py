"""
셀 표현 Delegate 시스템 (Phase 11.1)
테이블 셀의 시각적 표현을 개선하여 상태별 색상, 아이콘, 진행률 바 등을 구현
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import QRect, QRectF, QSize, Qt
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
from PyQt5.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem


class BaseCellDelegate(QStyledItemDelegate):
    """기본 셀 Delegate 클래스"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_colors = self._get_theme_colors()
        self._setup_theme_connection()

    def _setup_theme_connection(self):
        """테마 변경 시그널 연결"""
        try:
            app = QApplication.instance()
            if app:
                main_window = app.activeWindow()
                if main_window and hasattr(main_window, "theme_manager"):
                    main_window.theme_manager.theme_changed.connect(self._on_theme_changed)
                if main_window and hasattr(main_window, "accessibility_manager"):
                    main_window.accessibility_manager.high_contrast_changed.connect(
                        self._on_theme_changed
                    )
        except (AttributeError, RuntimeError) as e:
            logger.warning(f"테마 연결 설정 실패: {e}")

    def _on_theme_changed(self, *args):
        """테마 변경 시 호출 - 색상 팔레트 업데이트"""
        self._theme_colors = self._get_theme_colors()
        if self.parent():
            self.parent().viewport().update()

    def _get_theme_colors(self) -> dict[str, QColor]:
        """현재 테마에 따른 색상 팔레트 반환 - 강화된 테마 호환성"""
        app = QApplication.instance()
        if not app:
            return self._get_default_colors()
        current_theme = "auto"
        system_theme = "light"
        try:
            main_window = app.activeWindow()
            if main_window and hasattr(main_window, "theme_manager"):
                current_theme = main_window.theme_manager.get_current_theme()
                system_theme = main_window.theme_manager.get_system_theme()
        except (AttributeError, RuntimeError) as e:
            logger.warning(f"시스템 테마 감지 실패: {e}")
        effective_theme = system_theme if current_theme == "auto" else current_theme
        if current_theme == "auto":
            palette = app.palette()
            window_color = palette.color(QPalette.Window)
            effective_theme = "dark" if window_color.lightness() < 128 else "light"
        is_high_contrast = False
        try:
            if main_window and hasattr(main_window, "accessibility_manager"):
                is_high_contrast = main_window.accessibility_manager.high_contrast_mode
        except (AttributeError, RuntimeError) as e:
            logger.warning(f"시스템 테마 감지 실패: {e}")
        if is_high_contrast:
            return {
                "background": QColor(0, 0, 0),
                "text": QColor(255, 255, 255),
                "border": QColor(255, 255, 255),
                "highlight": QColor(255, 255, 0),
                "success": QColor(0, 255, 0),
                "warning": QColor(255, 255, 0),
                "error": QColor(255, 0, 0),
                "info": QColor(0, 255, 255),
                "muted": QColor(128, 128, 128),
            }
        if effective_theme == "dark":
            return {
                "background": QColor(25, 25, 25),
                "text": QColor(255, 255, 255),
                "border": QColor(100, 100, 100),
                "highlight": QColor(42, 130, 218),
                "success": QColor(76, 175, 80),
                "warning": QColor(255, 193, 7),
                "error": QColor(244, 67, 54),
                "info": QColor(33, 150, 243),
                "muted": QColor(200, 200, 200),
                "alternate": QColor(53, 53, 53),
            }
        return {
            "background": QColor(255, 255, 255),
            "text": QColor(33, 33, 33),
            "border": QColor(224, 224, 224),
            "highlight": QColor(42, 130, 218),
            "success": QColor(76, 175, 80),
            "warning": QColor(255, 193, 7),
            "error": QColor(244, 67, 54),
            "info": QColor(33, 150, 243),
            "muted": QColor(158, 158, 158),
            "alternate": QColor(245, 245, 245),
        }

    def _get_default_colors(self) -> dict[str, QColor]:
        """기본 색상 팔레트"""
        return {
            "background": QColor(255, 255, 255),
            "text": QColor(0, 0, 0),
            "border": QColor(200, 200, 200),
            "highlight": QColor(0, 120, 215),
            "success": QColor(0, 128, 0),
            "warning": QColor(255, 140, 0),
            "error": QColor(255, 0, 0),
            "info": QColor(0, 120, 215),
            "muted": QColor(128, 128, 128),
        }

    def _draw_rounded_rect(self, painter: QPainter, rect: QRect, color: QColor, radius: int = 4):
        """둥근 모서리 사각형 그리기"""
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        rectf = QRectF(rect)
        path.addRoundedRect(rectf, radius, radius)
        painter.fillPath(path, QBrush(color))

    def _get_text_color_for_background(self, background_color: QColor) -> QColor:
        """배경색에 대비되는 텍스트 색상 반환 (WCAG AA/AAA 기준 준수)"""

        def luminance(color: QColor) -> float:
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0

            def adjust(c):
                return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)

            return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

        very_dark_text = QColor(0, 0, 0)
        dark_text = QColor(33, 33, 33)
        light_text = QColor(255, 255, 255)
        very_light_text = QColor(240, 240, 240)
        very_dark_contrast = self._calculate_contrast_ratio(background_color, very_dark_text)
        dark_contrast = self._calculate_contrast_ratio(background_color, dark_text)
        light_contrast = self._calculate_contrast_ratio(background_color, light_text)
        very_light_contrast = self._calculate_contrast_ratio(background_color, very_light_text)
        contrast_options = [
            (very_dark_contrast, very_dark_text),
            (dark_contrast, dark_text),
            (light_contrast, light_text),
            (very_light_contrast, very_light_text),
        ]
        valid_options = [(ratio, color) for ratio, color in contrast_options if ratio >= 4.5]
        if valid_options:
            best_ratio, best_color = max(valid_options, key=lambda x: x[0])
            return best_color
        best_ratio, best_color = max(contrast_options, key=lambda x: x[0])
        return best_color

    def _calculate_contrast_ratio(self, color1: QColor, color2: QColor) -> float:
        """두 색상 간의 대비비 계산 (WCAG 기준)"""

        def luminance(color: QColor) -> float:
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0

            def adjust(c):
                return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)

            return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

        lum1 = luminance(color1)
        lum2 = luminance(color2)
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        return (lighter + 0.05) / (darker + 0.05)


class StatusCellDelegate(BaseCellDelegate):
    """상태 표시를 위한 셀 Delegate - 상태 칩 형태"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_colors = {
            "✅ 완료": self._theme_colors["success"],
            "⚠️ 부분": self._theme_colors["warning"],
            "⏳ 대기중": self._theme_colors["info"],
            "❌ 오류": self._theme_colors["error"],
            "🎯 TMDB 매치": self._theme_colors["highlight"],
            "🔍 스캔중": self._theme_colors["info"],
            "📝 처리중": self._theme_colors["warning"],
        }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """상태 칩 그리기"""
        painter.save()
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())
        status_text = index.data(Qt.DisplayRole)
        if not status_text:
            painter.restore()
            return
        status_color = self._status_colors.get(status_text, self._theme_colors["muted"])
        chip_rect = QRect(option.rect)
        chip_rect.setLeft(chip_rect.left() + 4)
        chip_rect.setRight(chip_rect.right() - 4)
        chip_rect.setTop(chip_rect.top() + 2)
        chip_rect.setBottom(chip_rect.bottom() - 2)
        self._draw_rounded_rect(painter, chip_rect, status_color)
        text_color = self._get_text_color_for_background(status_color)
        painter.setPen(QPen(text_color))
        painter.setFont(option.font)
        text_rect = chip_rect
        painter.drawText(text_rect, Qt.AlignCenter, status_text)
        self._set_accessibility_info(option, index, status_text, status_color)
        painter.restore()

    def _set_accessibility_info(
        self, option: QStyleOptionViewItem, index, status_text: str, status_color: QColor
    ):
        """접근성 정보 설정"""
        try:
            accessible_name = f"상태: {status_text}"
            accessible_description = f"현재 상태는 {status_text}입니다. 색상은 {self._get_color_description(status_color)}입니다."
            if hasattr(option, "index") and option.index.isValid():
                option.index.model().setData(option.index, accessible_name, Qt.AccessibleTextRole)
                option.index.model().setData(
                    option.index, accessible_description, Qt.AccessibleDescriptionRole
                )
        except (AttributeError, RuntimeError) as e:
            logger.warning(f"시스템 테마 감지 실패: {e}")

    def _get_color_description(self, color: QColor) -> str:
        """색상을 설명하는 텍스트 반환"""
        if color == self._theme_colors["success"]:
            return "성공을 나타내는 녹색"
        if color == self._theme_colors["warning"]:
            return "주의를 나타내는 노란색"
        if color == self._theme_colors["error"]:
            return "오류를 나타내는 빨간색"
        if color == self._theme_colors["info"]:
            return "정보를 나타내는 파란색"
        if color == self._theme_colors["highlight"]:
            return "강조를 나타내는 파란색"
        return "기본 색상"

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        """상태 칩 크기 계산"""
        status_text = index.data(Qt.DisplayRole)
        if not status_text:
            return QSize(60, 24)
        font_metrics = QFontMetrics(option.font)
        text_width = font_metrics.horizontalAdvance(status_text)
        width = max(60, min(120, text_width + 20))
        height = 24
        return QSize(width, height)


class ProgressCellDelegate(BaseCellDelegate):
    """진행률/에피소드 수 표시를 위한 셀 Delegate - 솔리드 컬러 배경"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress_colors = {
            "low": self._theme_colors["warning"],
            "medium": self._theme_colors["info"],
            "high": self._theme_colors["success"],
        }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """솔리드 컬러 배경과 숫자 표시"""
        painter.save()
        value = index.data(Qt.DisplayRole)
        if value is None:
            painter.restore()
            return
        try:
            if isinstance(value, str):
                if "/" in value:
                    current, total = map(int, value.split("/"))
                    progress = current / total if total > 0 else 0
                    display_text = value
                else:
                    progress = int(value) / 100.0 if int(value) <= 100 else 1.0
                    display_text = str(value)
            else:
                progress = float(value) / 100.0 if float(value) <= 100 else 1.0
                display_text = str(value)
        except (ValueError, TypeError):
            progress = 0.0
            display_text = str(value)
        if progress < 0.3:
            background_color = self._progress_colors["low"]
        elif progress < 0.7:
            background_color = self._progress_colors["medium"]
        else:
            background_color = self._progress_colors["high"]
        if option.state & QStyle.State_Selected:
            background_color = option.palette.highlight().color()
        painter.fillRect(option.rect, background_color)
        text_color = self._get_text_color_for_background(background_color)
        painter.setPen(QPen(text_color))
        painter.setFont(option.font)
        painter.drawText(option.rect, Qt.AlignCenter, display_text)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        """셀 크기 계산"""
        return QSize(80, 28)


class IconCellDelegate(BaseCellDelegate):
    """아이콘/포스터 표시를 위한 셀 Delegate"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon_size = QSize(32, 32)
        self._default_icon = "🎬"

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """아이콘 그리기"""
        painter.save()
        if option.state & QStyle.State_Selected:
            background_color = option.palette.highlight().color()
            painter.fillRect(option.rect, background_color)
        else:
            background_color = option.palette.base().color()
            painter.fillRect(option.rect, background_color)
        icon_data = index.data(Qt.DecorationRole)
        if not icon_data:
            icon_data = self._default_icon
        if isinstance(icon_data, QPixmap | QIcon) and index.column() == 0:
            cell_width = option.rect.width() - 20
            cell_height = option.rect.height() - 20
            if isinstance(icon_data, QPixmap):
                scaled_pixmap = icon_data.scaled(
                    cell_width, cell_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                x = option.rect.x() + (option.rect.width() - scaled_pixmap.width()) // 2
                y = option.rect.y() + (option.rect.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)
            else:
                icon_rect = QRect(
                    option.rect.x() + 10, option.rect.y() + 10, cell_width, cell_height
                )
                icon_data.paint(painter, icon_rect)
        else:
            icon_rect = QRect(option.rect)
            icon_rect.moveCenter(option.rect.center())
            icon_rect.setSize(self._icon_size)
            text_color = self._get_text_color_for_background(background_color)
            if isinstance(icon_data, str) and len(icon_data) <= 4:
                painter.setFont(QFont("Segoe UI Emoji", 20))
                painter.setPen(QPen(text_color))
                painter.drawText(icon_rect, Qt.AlignCenter, icon_data)
            elif isinstance(icon_data, QPixmap | QIcon):
                if isinstance(icon_data, QIcon):
                    icon_data.paint(painter, icon_rect)
                else:
                    painter.drawPixmap(icon_rect, icon_data)
            else:
                painter.setFont(QFont("Segoe UI Emoji", 20))
                muted_color = self._theme_colors["muted"]
                if self._calculate_contrast_ratio(background_color, muted_color) < 4.5:
                    muted_color = text_color
                painter.setPen(QPen(muted_color))
                painter.drawText(icon_rect, Qt.AlignCenter, self._default_icon)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        """아이콘 크기 계산"""
        return QSize(40, 40)


class TextPreviewCellDelegate(BaseCellDelegate):
    """긴 텍스트 미리보기를 위한 셀 Delegate - 화살표 텍스트"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._max_preview_length = 30
        self._ellipsis = " →"

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """미리보기 텍스트 그리기"""
        painter.save()
        if option.state & QStyle.State_Selected:
            background_color = option.palette.highlight().color()
            painter.fillRect(option.rect, background_color)
        else:
            background_color = option.palette.base().color()
            painter.fillRect(option.rect, background_color)
        text = index.data(Qt.DisplayRole)
        if not text:
            painter.restore()
            return
        if len(text) <= self._max_preview_length:
            display_text = text
        else:
            preview = text[: self._max_preview_length].rstrip()
            display_text = preview + self._ellipsis
        text_color = self._get_text_color_for_background(background_color)
        painter.setPen(QPen(text_color))
        painter.setFont(option.font)
        text_rect = QRect(option.rect)
        text_rect.setLeft(text_rect.left() + 4)
        text_rect.setRight(text_rect.right() - 4)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, display_text)
        if len(text) > self._max_preview_length:
            try:
                if hasattr(option, "index") and option.index.isValid():
                    option.index.model().setData(option.index, text, Qt.ToolTipRole)
            except (AttributeError, RuntimeError) as e:
                logger.warning(f"툴팁 설정 실패: {e}")
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        """텍스트 크기 계산"""
        text = index.data(Qt.DisplayRole)
        if not text:
            return QSize(100, 24)
        font_metrics = QFontMetrics(option.font)
        text_width = font_metrics.horizontalAdvance(
            text[: self._max_preview_length] + self._ellipsis
        )
        width = max(100, min(300, text_width + 20))
        height = 24
        return QSize(width, height)
