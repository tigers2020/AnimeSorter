"""
테마 관리 시스템 (Phase 9.2)
다크/라이트 테마 자동 대응을 위한 팔레트 기반 색상 시스템
"""

import os

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication


class ThemeManager(QObject):
    """테마 관리자 - 다크/라이트 테마 자동 대응"""

    theme_changed = pyqtSignal(str)  # 테마 변경 시그널
    palette_updated = pyqtSignal(QPalette)  # 팔레트 업데이트 시그널

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "auto"  # auto, light, dark
        self.system_theme = self._detect_system_theme()
        self._setup_theme_detection()

        # Phase 9.2: 테마별 색상 팔레트 정의
        self._define_color_palettes()

        # 초기 테마 적용
        self.apply_theme(self.current_theme)

    def _detect_system_theme(self) -> str:
        """시스템 테마 감지 (Phase 9.2)"""
        try:
            # Windows 시스템 테마 감지
            if os.name == "nt":
                import winreg

                try:
                    with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                    ) as key:
                        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                        return "light" if value == 1 else "dark"
                except:
                    pass

            # macOS 시스템 테마 감지
            elif os.name == "posix" and os.uname().sysname == "Darwin":
                try:
                    result = os.popen("defaults read -g AppleInterfaceStyle").read().strip()
                    return "dark" if result == "Dark" else "light"
                except:
                    pass

            # Linux 시스템 테마 감지
            elif os.name == "posix":
                try:
                    gtk_theme = os.environ.get("GTK_THEME", "").lower()
                    if "dark" in gtk_theme:
                        return "dark"
                    elif "light" in gtk_theme:
                        return "light"
                except:
                    pass

        except Exception:
            pass

        # 기본값: 라이트 테마
        return "light"

    def _setup_theme_detection(self):
        """시스템 테마 변경 감지 설정 (Phase 9.2)"""
        # 주기적으로 시스템 테마 확인 (5초마다)
        self.theme_check_timer = QTimer(self)
        self.theme_check_timer.timeout.connect(self._check_system_theme_change)
        self.theme_check_timer.start(5000)  # 5초마다 체크

    def _check_system_theme_change(self):
        """시스템 테마 변경 확인 (Phase 9.2)"""
        new_system_theme = self._detect_system_theme()
        if new_system_theme != self.system_theme:
            self.system_theme = new_system_theme
            if self.current_theme == "auto":
                self.apply_theme("auto")

    def _define_color_palettes(self):
        """테마별 색상 팔레트 정의 (Phase 9.2)"""
        # 라이트 테마 색상
        self.light_palette = QPalette()
        self.light_palette.setColor(QPalette.Window, QColor(240, 240, 240))
        self.light_palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
        self.light_palette.setColor(QPalette.Base, QColor(255, 255, 255))
        self.light_palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
        self.light_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        self.light_palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        self.light_palette.setColor(QPalette.Text, QColor(0, 0, 0))
        self.light_palette.setColor(QPalette.Button, QColor(240, 240, 240))
        self.light_palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
        self.light_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        self.light_palette.setColor(QPalette.Link, QColor(0, 0, 255))
        self.light_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        self.light_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        # 다크 테마 색상
        self.dark_palette = QPalette()
        self.dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        self.dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        self.dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        self.dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        self.dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        self.dark_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        self.dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
        self.dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        self.dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        self.dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        self.dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        self.dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        self.dark_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

    def get_available_themes(self) -> list[str]:
        """사용 가능한 테마 목록 반환"""
        return ["auto", "light", "dark"]

    def get_current_theme(self) -> str:
        """현재 테마 반환"""
        return self.current_theme

    def get_system_theme(self) -> str:
        """시스템 테마 반환"""
        return self.system_theme

    def apply_theme(self, theme: str):
        """테마 적용 (Phase 9.2)"""
        if theme not in self.get_available_themes():
            return False

        self.current_theme = theme

        # 고대비 모드가 활성화되어 있으면 테마 적용을 건너뜀
        if hasattr(self.parent(), "accessibility_manager"):
            accessibility_manager = self.parent().accessibility_manager
            if (
                hasattr(accessibility_manager, "high_contrast_mode")
                and accessibility_manager.high_contrast_mode
            ):
                print("🔧 고대비 모드가 활성화되어 있어 테마 적용을 건너뜀")
                return False

        # 테마에 따른 팔레트 선택
        if theme == "auto":
            palette = self.dark_palette if self.system_theme == "dark" else self.light_palette
        elif theme == "dark":
            palette = self.dark_palette
        else:  # light
            palette = self.light_palette

        # 애플리케이션에 팔레트 적용
        app = QApplication.instance()
        if app:
            app.setPalette(palette)

            # Phase 9.2: 테마별 스타일 시트 적용
            self._apply_theme_stylesheet(theme)

            # 시그널 발생
            self.theme_changed.emit(theme)
            self.palette_updated.emit(palette)

            return True

        return False

    def _apply_theme_stylesheet(self, theme: str):
        """테마별 스타일시트 적용 (Phase 9.2)"""
        app = QApplication.instance()
        if not app:
            return

        # 기본 스타일시트 제거
        app.setStyleSheet("")

        if theme == "dark" or (theme == "auto" and self.system_theme == "dark"):
            # 다크 테마 스타일시트
            dark_stylesheet = """
            QMainWindow {
                background-color: #353535;
                color: #ffffff;
            }

            QTableView {
                background-color: #2a2a2a;
                color: #f0f0f0;
                gridline-color: #505050;
                alternate-background-color: #333333;
            }

            QTableView::item:selected {
                background-color: #2a82da;
                color: #ffffff;
            }

            QHeaderView::section {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
            }

            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #353535;
            }

            QTabBar::tab {
                background-color: #404040;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
            }

            QTabBar::tab:selected {
                background-color: #2a82da;
                color: #ffffff;
            }

            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 6px 12px;
                border-radius: 4px;
            }

            QPushButton:hover {
                background-color: #505050;
            }

            QPushButton:pressed {
                background-color: #2a82da;
            }

            QLineEdit {
                background-color: #2a2a2a;
                color: #f0f0f0;
                border: 1px solid #555555;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox {
                background-color: #2a2a2a;
                color: #f0f0f0;
                border: 1px solid #555555;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox::drop-down {
                border: none;
                width: 20px;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
            }

            QMenuBar {
                background-color: #2a2a2a;
                color: #ffffff;
                border-bottom: 1px solid #555555;
            }

            QMenuBar::item {
                background-color: transparent;
                padding: 6px 12px;
                margin: 2px;
                border-radius: 4px;
            }

            QMenuBar::item:selected {
                background-color: #404040;
            }

            QMenuBar::item:pressed {
                background-color: #2a82da;
            }

            QMenu {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 4px;
            }

            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }

            QMenu::item:selected {
                background-color: #404040;
            }

            QMenu::separator {
                height: 1px;
                background-color: #555555;
                margin: 4px 0px;
            }

            QGroupBox {
                background-color: #404040;
                color: #f0f0f0;
                border: 2px solid #606060;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }

            QLabel {
                color: #f0f0f0;
            }

            QDockWidget {
                background-color: #353535;
                color: #f0f0f0;
            }

            QDockWidget::title {
                background-color: #404040;
                color: #f0f0f0;
                text-align: center;
                padding: 6px;
            }
            """
            app.setStyleSheet(dark_stylesheet)

        elif theme == "light" or (theme == "auto" and self.system_theme == "light"):
            # 라이트 테마 스타일시트
            light_stylesheet = """
            QMainWindow {
                background-color: #f0f0f0;
                color: #000000;
            }

            QTableView {
                background-color: #ffffff;
                color: #000000;
                gridline-color: #d0d0d0;
                alternate-background-color: #f5f5f5;
            }

            QTableView::item:selected {
                background-color: #2a82da;
                color: #ffffff;
            }

            QHeaderView::section {
                background-color: #e0e0e0;
                color: #000000;
                border: 1px solid #c0c0c0;
            }

            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: #f0f0f0;
            }

            QTabBar::tab {
                background-color: #e0e0e0;
                color: #000000;
                padding: 8px 16px;
                margin-right: 2px;
            }

            QTabBar::tab:selected {
                background-color: #2a82da;
                color: #ffffff;
            }

            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 1px solid #c0c0c0;
                padding: 6px 12px;
                border-radius: 4px;
            }

            QPushButton:hover {
                background-color: #d0d0d0;
            }

            QPushButton:pressed {
                background-color: #2a82da;
                color: #ffffff;
            }

            QLineEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #c0c0c0;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #c0c0c0;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox::drop-down {
                border: none;
                width: 20px;
            }

            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #000000;
            }

            QMenuBar {
                background-color: #f0f0f0;
                color: #000000;
                border-bottom: 1px solid #c0c0c0;
            }

            QMenuBar::item {
                background-color: transparent;
                padding: 6px 12px;
                margin: 2px;
                border-radius: 4px;
            }

            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }

            QMenuBar::item:pressed {
                background-color: #2a82da;
                color: #ffffff;
            }

            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #c0c0c0;
                padding: 4px;
            }

            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }

            QMenu::item:selected {
                background-color: #e0e0e0;
            }

            QMenu::separator {
                height: 1px;
                background-color: #c0c0c0;
                margin: 4px 0px;
            }
            """
            app.setStyleSheet(light_stylesheet)

    def toggle_theme(self):
        """테마 토글 (라이트 ↔ 다크)"""
        if self.current_theme == "auto":
            # 자동 모드에서는 시스템 테마와 반대로 설정
            new_theme = "light" if self.system_theme == "dark" else "dark"
        else:
            # 수동 모드에서는 라이트 ↔ 다크 토글
            new_theme = "dark" if self.current_theme == "light" else "light"

        self.apply_theme(new_theme)

    def reset_to_auto(self):
        """자동 테마 모드로 복원"""
        self.apply_theme("auto")
