"""
테마 관리 시스템 (Phase 9.2)
다크/라이트 테마 자동 대응을 위한 팔레트 기반 색상 시스템
"""

import logging
import os

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication

# 로거 설정
logger = logging.getLogger(__name__)


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
        logger.info(
            f"테마 관리자 초기화: 시스템 테마={self.system_theme}, 현재 테마={self.current_theme}"
        )
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
                        detected_theme = "light" if value == 1 else "dark"
                        logger.info(f"Windows 시스템 테마 감지: {detected_theme}")
                        return detected_theme
                except Exception as e:
                    logger.warning(f"Windows 테마 감지 실패: {e}")

            # macOS 시스템 테마 감지
            elif os.name == "posix" and os.uname().sysname == "Darwin":
                try:
                    result = os.popen("defaults read -g AppleInterfaceStyle").read().strip()
                    detected_theme = "dark" if result == "Dark" else "light"
                    logger.info(f"macOS 시스템 테마 감지: {detected_theme}")
                    return detected_theme
                except Exception as e:
                    logger.warning(f"macOS 테마 감지 실패: {e}")

            # Linux 시스템 테마 감지
            elif os.name == "posix":
                try:
                    gtk_theme = os.environ.get("GTK_THEME", "").lower()
                    if "dark" in gtk_theme:
                        logger.info("Linux 시스템 테마 감지: dark")
                        return "dark"
                    if "light" in gtk_theme:
                        logger.info("Linux 시스템 테마 감지: light")
                        return "light"
                except Exception as e:
                    logger.warning(f"Linux 테마 감지 실패: {e}")

        except Exception as e:
            logger.error(f"시스템 테마 감지 중 오류: {e}")

        # 기본값: 라이트 테마
        logger.info("시스템 테마 감지 실패, 기본값 사용: light")
        return "light"

    def _setup_theme_detection(self):
        """시스템 테마 변경 감지 설정 (Phase 9.2)"""
        # 주기적으로 시스템 테마 확인 (5초마다)
        self.theme_check_timer = QTimer(self)
        self.theme_check_timer.timeout.connect(self._check_system_theme_change)
        self.theme_check_timer.start(5000)  # 5초마다 체크
        logger.info("시스템 테마 변경 감지 타이머 시작 (5초 간격)")

    def _check_system_theme_change(self):
        """시스템 테마 변경 확인 (Phase 9.2)"""
        new_system_theme = self._detect_system_theme()
        if new_system_theme != self.system_theme:
            logger.info(f"시스템 테마 변경 감지: {self.system_theme} → {new_system_theme}")
            self.system_theme = new_system_theme
            if self.current_theme == "auto":
                logger.info("자동 테마 모드에서 시스템 테마 변경에 따라 테마 재적용")
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

        logger.info("테마별 색상 팔레트 정의 완료")

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
            logger.error(f"지원하지 않는 테마: {theme}")
            return False

        logger.info(f"테마 적용 시작: {theme} (시스템 테마: {self.system_theme})")
        self.current_theme = theme

        # 고대비 모드가 활성화되어 있으면 테마 적용을 건너뜀
        if hasattr(self.parent(), "accessibility_manager"):
            accessibility_manager = self.parent().accessibility_manager
            if (
                hasattr(accessibility_manager, "high_contrast_mode")
                and accessibility_manager.high_contrast_mode
            ):
                logger.info("🔧 고대비 모드가 활성화되어 있어 테마 적용을 건너뜀")
                return False

        # 테마에 따른 팔레트 선택
        if theme == "auto":
            palette = self.dark_palette if self.system_theme == "dark" else self.light_palette
            effective_theme = "dark" if self.system_theme == "dark" else "light"
        elif theme == "dark":
            palette = self.dark_palette
            effective_theme = "dark"
        else:  # light
            palette = self.light_palette
            effective_theme = "light"

        logger.info(f"선택된 팔레트: {effective_theme} 테마")

        # 애플리케이션에 팔레트 적용
        app = QApplication.instance()
        if app:
            app.setPalette(palette)
            logger.info("애플리케이션 팔레트 적용 완료")

            # Phase 9.2: 테마별 스타일 시트 적용
            self._apply_theme_stylesheet(effective_theme)

            # 시그널 발생
            self.theme_changed.emit(theme)
            self.palette_updated.emit(palette)

            logger.info(f"✅ 테마 '{theme}' 적용 완료 (실제 적용: {effective_theme})")
            return True

        logger.error("QApplication 인스턴스를 찾을 수 없음")
        return False

    def _apply_theme_stylesheet(self, theme: str):
        """테마별 스타일시트 적용 (Phase 9.2)"""
        app = QApplication.instance()
        if not app:
            logger.error("QApplication 인스턴스를 찾을 수 없음")
            return

        logger.info(f"스타일시트 적용 시작: {theme} 테마")

        # 기본 스타일시트 제거 - 테마 시스템에서 관리

        if theme == "dark":
            # 다크 테마 - 스타일은 테마 시스템에서 관리
            logger.info("다크 테마 스타일시트 적용 완료")

        elif theme == "light":
            # 라이트 테마 - 스타일은 테마 시스템에서 관리
            logger.info("라이트 테마 스타일시트 적용 완료")

    def toggle_theme(self):
        """테마 토글 (라이트 ↔ 다크)"""
        if self.current_theme == "auto":
            # 자동 모드에서는 시스템 테마와 반대로 설정
            new_theme = "light" if self.system_theme == "dark" else "dark"
        else:
            # 수동 모드에서는 라이트 ↔ 다크 토글
            new_theme = "dark" if self.current_theme == "light" else "light"

        logger.info(f"테마 토글: {self.current_theme} → {new_theme}")
        self.apply_theme(new_theme)

    def reset_to_auto(self):
        """자동 테마 모드로 복원"""
        logger.info("테마를 자동 모드로 복원")
        self.apply_theme("auto")
