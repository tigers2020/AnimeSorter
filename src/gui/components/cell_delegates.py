"""
셀 표현 Delegate 시스템 (Phase 11.1)
테이블 셀의 시각적 표현을 개선하여 상태별 색상, 아이콘, 진행률 바 등을 구현
"""


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
                # 테마 변경 시그널 연결
                main_window = app.activeWindow()
                if main_window and hasattr(main_window, "theme_manager"):
                    main_window.theme_manager.theme_changed.connect(self._on_theme_changed)

                # 접근성 모드 변경 시그널 연결
                if main_window and hasattr(main_window, "accessibility_manager"):
                    main_window.accessibility_manager.high_contrast_changed.connect(
                        self._on_theme_changed
                    )
        except Exception:
            pass

    def _on_theme_changed(self, *args):
        """테마 변경 시 호출 - 색상 팔레트 업데이트"""
        self._theme_colors = self._get_theme_colors()
        # 테이블 뷰 새로고침 트리거
        if self.parent():
            self.parent().viewport().update()

    def _get_theme_colors(self) -> dict[str, QColor]:
        """현재 테마에 따른 색상 팔레트 반환 - 강화된 테마 호환성"""
        app = QApplication.instance()
        if not app:
            return self._get_default_colors()

        # 테마 관리자에서 현재 테마 확인
        current_theme = "auto"
        system_theme = "light"

        try:
            # 메인 윈도우에서 테마 관리자 접근
            main_window = app.activeWindow()
            if main_window and hasattr(main_window, "theme_manager"):
                current_theme = main_window.theme_manager.get_current_theme()
                system_theme = main_window.theme_manager.get_system_theme()
        except Exception:
            pass

        # 실제 적용된 테마 결정
        effective_theme = system_theme if current_theme == "auto" else current_theme

        # 실제 팔레트를 통한 추가 검증 (auto 테마의 경우)
        if current_theme == "auto":
            palette = app.palette()
            window_color = palette.color(QPalette.Window)
            # 실제 윈도우 색상의 밝기를 기준으로 다시 판단
            effective_theme = "dark" if window_color.lightness() < 128 else "light"

        # 고대비 모드 확인
        is_high_contrast = False
        try:
            if main_window and hasattr(main_window, "accessibility_manager"):
                is_high_contrast = main_window.accessibility_manager.high_contrast_mode
        except Exception:
            pass

        if is_high_contrast:
            # 고대비 모드 색상 팔레트
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
            # 다크 테마 색상 팔레트 (WCAG AA 기준 준수 - 더 높은 대비)
            return {
                "background": QColor(25, 25, 25),
                "text": QColor(255, 255, 255),
                "border": QColor(100, 100, 100),
                "highlight": QColor(42, 130, 218),
                "success": QColor(76, 175, 80),
                "warning": QColor(255, 193, 7),
                "error": QColor(244, 67, 54),
                "info": QColor(33, 150, 243),
                "muted": QColor(200, 200, 200),  # 더 밝게 조정하여 가독성 향상
                "alternate": QColor(53, 53, 53),
            }
        else:
            # 라이트 테마 색상 팔레트 (WCAG AA 기준 준수)
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
        # QRect를 QRectF로 변환
        rectf = QRectF(rect)
        path.addRoundedRect(rectf, radius, radius)
        painter.fillPath(path, QBrush(color))

    def _get_text_color_for_background(self, background_color: QColor) -> QColor:
        """배경색에 대비되는 텍스트 색상 반환 (WCAG AA/AAA 기준 준수)"""

        # WCAG AA 기준 (4.5:1) 색상 대비 계산
        def luminance(color: QColor) -> float:
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0

            def adjust(c):
                return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)

            return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

        # 더 강화된 대비 색상 옵션들
        very_dark_text = QColor(0, 0, 0)  # 순수 검은색
        dark_text = QColor(33, 33, 33)  # 부드러운 검은색
        light_text = QColor(255, 255, 255)  # 순수 흰색
        very_light_text = QColor(240, 240, 240)  # 부드러운 흰색

        # 각 옵션의 대비비 계산
        very_dark_contrast = self._calculate_contrast_ratio(background_color, very_dark_text)
        dark_contrast = self._calculate_contrast_ratio(background_color, dark_text)
        light_contrast = self._calculate_contrast_ratio(background_color, light_text)
        very_light_contrast = self._calculate_contrast_ratio(background_color, very_light_text)

        # 가장 높은 대비비를 가진 색상 선택 (WCAG AA 기준 우선 고려)
        contrast_options = [
            (very_dark_contrast, very_dark_text),
            (dark_contrast, dark_text),
            (light_contrast, light_text),
            (very_light_contrast, very_light_text),
        ]

        # WCAG AA 기준 (4.5:1) 이상인 옵션 중 가장 대비가 높은 것 선택
        valid_options = [(ratio, color) for ratio, color in contrast_options if ratio >= 4.5]

        if valid_options:
            # 유효한 옵션 중 가장 대비가 높은 것
            best_ratio, best_color = max(valid_options, key=lambda x: x[0])
            return best_color

        # WCAG 기준을 만족하지 않으면 전체 옵션 중 가장 대비가 높은 것
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
        # 기본 설정
        painter.save()

        # 배경 지우기
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, option.palette.base())

        # 데이터 가져오기
        status_text = index.data(Qt.DisplayRole)
        if not status_text:
            painter.restore()
            return

        # 상태별 색상 결정
        status_color = self._status_colors.get(status_text, self._theme_colors["muted"])

        # 상태 칩 그리기
        chip_rect = QRect(option.rect)
        chip_rect.setLeft(chip_rect.left() + 4)
        chip_rect.setRight(chip_rect.right() - 4)
        chip_rect.setTop(chip_rect.top() + 2)
        chip_rect.setBottom(chip_rect.bottom() - 2)

        # 둥근 모서리 상태 칩
        self._draw_rounded_rect(painter, chip_rect, status_color)

        # 텍스트 색상 결정 (WCAG AA 기준 준수)
        text_color = self._get_text_color_for_background(status_color)

        # 텍스트 그리기
        painter.setPen(QPen(text_color))
        painter.setFont(option.font)

        # 텍스트 중앙 정렬
        text_rect = chip_rect
        painter.drawText(text_rect, Qt.AlignCenter, status_text)

        # 접근성 정보 설정
        self._set_accessibility_info(option, index, status_text, status_color)

        painter.restore()

    def _set_accessibility_info(
        self, option: QStyleOptionViewItem, index, status_text: str, status_color: QColor
    ):
        """접근성 정보 설정"""
        try:
            # 접근 가능한 이름과 설명 설정
            accessible_name = f"상태: {status_text}"
            accessible_description = f"현재 상태는 {status_text}입니다. 색상은 {self._get_color_description(status_color)}입니다."

            # 테이블 뷰에 접근성 정보 전달
            if hasattr(option, "index") and option.index.isValid():
                # 접근성 역할에 정보 저장
                option.index.model().setData(option.index, accessible_name, Qt.AccessibleTextRole)
                option.index.model().setData(
                    option.index, accessible_description, Qt.AccessibleDescriptionRole
                )
        except:
            pass

    def _get_color_description(self, color: QColor) -> str:
        """색상을 설명하는 텍스트 반환"""
        if color == self._theme_colors["success"]:
            return "성공을 나타내는 녹색"
        elif color == self._theme_colors["warning"]:
            return "주의를 나타내는 노란색"
        elif color == self._theme_colors["error"]:
            return "오류를 나타내는 빨간색"
        elif color == self._theme_colors["info"]:
            return "정보를 나타내는 파란색"
        elif color == self._theme_colors["highlight"]:
            return "강조를 나타내는 파란색"
        else:
            return "기본 색상"

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        """상태 칩 크기 계산"""
        status_text = index.data(Qt.DisplayRole)
        if not status_text:
            return QSize(60, 24)

        # 텍스트 길이에 따른 동적 크기 계산
        font_metrics = QFontMetrics(option.font)
        text_width = font_metrics.horizontalAdvance(status_text)

        # 최소/최대 크기 제한
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

        # 데이터 가져오기
        value = index.data(Qt.DisplayRole)
        if value is None:
            painter.restore()
            return

        try:
            # 숫자로 변환
            if isinstance(value, str):
                # "12/26" 형태의 문자열 처리
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

        # 진행률에 따른 색상 결정
        if progress < 0.3:
            background_color = self._progress_colors["low"]
        elif progress < 0.7:
            background_color = self._progress_colors["medium"]
        else:
            background_color = self._progress_colors["high"]

        # 선택 상태일 때는 하이라이트 색상 사용
        if option.state & QStyle.State_Selected:
            background_color = option.palette.highlight().color()

        # 솔리드 배경 그리기
        painter.fillRect(option.rect, background_color)

        # 텍스트 색상 결정 (배경에 대비되는 색상)
        text_color = self._get_text_color_for_background(background_color)

        # 텍스트 그리기
        painter.setPen(QPen(text_color))
        painter.setFont(option.font)

        # 텍스트 중앙 정렬
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

        # 배경 색상 결정
        if option.state & QStyle.State_Selected:
            background_color = option.palette.highlight().color()
            painter.fillRect(option.rect, background_color)
        else:
            background_color = option.palette.base().color()
            painter.fillRect(option.rect, background_color)

        # 데이터 가져오기
        icon_data = index.data(Qt.DecorationRole)
        if not icon_data:
            icon_data = self._default_icon

        # 포스터 이미지인 경우 셀 크기에 맞게 조정
        if isinstance(icon_data, (QPixmap, QIcon)) and index.column() == 0:  # 포스터 컬럼
            # 셀 크기에 여백을 제외한 크기로 설정
            cell_width = option.rect.width() - 20  # 좌우 여백 10px씩
            cell_height = option.rect.height() - 20  # 상하 여백 10px씩

            # 포스터 비율 유지하면서 셀에 맞게 조정
            if isinstance(icon_data, QPixmap):
                scaled_pixmap = icon_data.scaled(
                    cell_width, cell_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                # 중앙 정렬
                x = option.rect.x() + (option.rect.width() - scaled_pixmap.width()) // 2
                y = option.rect.y() + (option.rect.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)
            else:  # QIcon
                icon_rect = QRect(
                    option.rect.x() + 10, option.rect.y() + 10, cell_width, cell_height
                )
                icon_data.paint(painter, icon_rect)
        else:
            # 일반 아이콘은 기존 방식 사용
            icon_rect = QRect(option.rect)
            icon_rect.moveCenter(option.rect.center())
            icon_rect.setSize(self._icon_size)

            # 배경에 적합한 텍스트 색상 계산
            text_color = self._get_text_color_for_background(background_color)

            # 이모지 또는 아이콘 그리기
            if isinstance(icon_data, str) and len(icon_data) <= 4:  # 이모지
                painter.setFont(QFont("Segoe UI Emoji", 20))
                painter.setPen(QPen(text_color))
                painter.drawText(icon_rect, Qt.AlignCenter, icon_data)
            elif isinstance(icon_data, QPixmap | QIcon):  # 실제 아이콘
                if isinstance(icon_data, QIcon):
                    icon_data.paint(painter, icon_rect)
                else:
                    painter.drawPixmap(icon_rect, icon_data)
            else:  # 기본 아이콘
                painter.setFont(QFont("Segoe UI Emoji", 20))
                # 기본 아이콘은 muted 색상 대신 적절한 대비 색상 사용
                muted_color = self._theme_colors["muted"]
                if self._calculate_contrast_ratio(background_color, muted_color) < 4.5:
                    # 대비가 낮으면 더 대비가 높은 색상 사용
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

        # 배경 색상 결정
        if option.state & QStyle.State_Selected:
            background_color = option.palette.highlight().color()
            painter.fillRect(option.rect, background_color)
        else:
            background_color = option.palette.base().color()
            painter.fillRect(option.rect, background_color)

        # 데이터 가져오기
        text = index.data(Qt.DisplayRole)
        if not text:
            painter.restore()
            return

        # 텍스트 길이 확인
        if len(text) <= self._max_preview_length:
            # 짧은 텍스트는 그대로 표시
            display_text = text
        else:
            # 긴 텍스트는 미리보기 + 화살표
            preview = text[: self._max_preview_length].rstrip()
            display_text = preview + self._ellipsis

        # 배경에 적합한 텍스트 색상 계산 (WCAG AA 기준)
        text_color = self._get_text_color_for_background(background_color)

        # 텍스트 그리기
        painter.setPen(QPen(text_color))
        painter.setFont(option.font)

        # 텍스트 정렬 (왼쪽 정렬)
        text_rect = QRect(option.rect)
        text_rect.setLeft(text_rect.left() + 4)
        text_rect.setRight(text_rect.right() - 4)

        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, display_text)

        # 툴팁 설정 (전체 텍스트 표시)
        if len(text) > self._max_preview_length:
            # 모델에 툴팁 데이터 설정
            try:
                if hasattr(option, "index") and option.index.isValid():
                    option.index.model().setData(option.index, text, Qt.ToolTipRole)
            except Exception:
                pass

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        """텍스트 크기 계산"""
        text = index.data(Qt.DisplayRole)
        if not text:
            return QSize(100, 24)

        # 텍스트 길이에 따른 동적 크기 계산
        font_metrics = QFontMetrics(option.font)
        text_width = font_metrics.horizontalAdvance(
            text[: self._max_preview_length] + self._ellipsis
        )

        # 최소/최대 크기 제한
        width = max(100, min(300, text_width + 20))
        height = 24

        return QSize(width, height)
