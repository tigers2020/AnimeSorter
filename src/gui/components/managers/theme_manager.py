"""
테마 관리 시스템 (Phase 9.2)
다크/라이트 테마 자동 대응을 위한 팔레트 기반 색상 시스템
"""

import logging
import os

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication, QMainWindow

logger = logging.getLogger(__name__)


class ThemeManager(QObject):
    """테마 관리자 - 다크/라이트 테마 자동 대응"""

    theme_changed = pyqtSignal(str)
    palette_updated = pyqtSignal(QPalette)
    icon_theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "auto"
        self.system_theme = self._detect_system_theme()
        self._setup_theme_detection()
        self._define_color_palettes()
        self.theme_templates_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "theme", "templates"
        )
        logger.info(f"테마 관리자 초기화: 시스템 테마={self.system_theme}, 현재 테마={self.current_theme}")
        self.apply_theme(self.current_theme)

    def _detect_system_theme(self) -> str:
        """시스템 테마 감지 (Phase 9.2)"""
        try:
            if os.name == "nt":
                import winreg

                try:
                    with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        "Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
                    ) as key:
                        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                        detected_theme = "light" if value == 1 else "dark"
                        logger.info(f"Windows 시스템 테마 감지: {detected_theme}")
                        return detected_theme
                except Exception as e:
                    logger.warning(f"Windows 테마 감지 실패: {e}")
            elif os.name == "posix" and os.uname().sysname == "Darwin":
                try:
                    import subprocess  # nosec B404 - macOS 시스템 테마 감지를 위해 필요

                    result = subprocess.run(
                        [
                            "defaults",
                            "read",
                            "-g",
                            "AppleInterfaceStyle",
                        ],  # nosec B603/B607 - macOS 시스템 명령어
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    detected_theme = "dark" if result.stdout.strip() == "Dark" else "light"
                    logger.info(f"macOS 시스템 테마 감지: {detected_theme}")
                    return detected_theme
                except Exception as e:
                    logger.warning(f"macOS 테마 감지 실패: {e}")
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
        logger.info("시스템 테마 감지 실패, 기본값 사용: light")
        return "light"

    def _setup_theme_detection(self):
        """시스템 테마 변경 감지 설정 (Phase 9.2)"""
        self.theme_check_timer = QTimer(self)
        self.theme_check_timer.timeout.connect(self._check_system_theme_change)
        self.theme_check_timer.start(5000)
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

    def _read_qss_file(self, qss_path: str) -> str:
        """QSS 파일 읽기 헬퍼 메서드"""
        try:
            if os.path.exists(qss_path):
                with open(qss_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    logger.info(f"QSS 파일 로드 성공: {qss_path} ({len(content)} 문자)")
                    return content
            else:
                logger.warning(f"QSS 파일을 찾을 수 없음: {qss_path}")
                return ""
        except Exception as e:
            logger.error(f"QSS 파일 읽기 실패: {qss_path}, 오류: {e}")
            return ""

    def _load_theme_templates(self, theme: str) -> str:
        """기존 테마 시스템의 템플릿 파일들을 로드하여 결합"""
        try:
            # 테마별 유틸리티 파일만 로드 (가장 기본적인 스타일)
            utility_file = os.path.join(self.theme_templates_path, "utilities", f"{theme}.qss")
            if os.path.exists(utility_file):
                utility_content = self._read_qss_file(utility_file)
                if utility_content:
                    logger.info(f"테마 템플릿 로드 완료: {theme} ({len(utility_content)} 문자)")
                    return utility_content

            logger.warning(f"테마 유틸리티 파일을 찾을 수 없음: {utility_file}")
            return ""

        except Exception as e:
            logger.error(f"테마 템플릿 로드 실패: {e}")
            return ""

    def get_available_themes(self) -> list[str]:
        """사용 가능한 테마 목록 반환"""
        return ["auto", "light", "dark"]

    def get_current_theme(self) -> str:
        """현재 테마 반환"""
        return self.current_theme

    def get_system_theme(self) -> str:
        """시스템 테마 반환"""
        return self.system_theme

    def apply_theme(self, theme: str) -> bool:
        """테마 적용 (Phase 9.2)"""
        if theme not in self.get_available_themes():
            logger.error(f"지원하지 않는 테마: {theme}")
            return False
        logger.info(f"테마 적용 시작: {theme} (시스템 테마: {self.system_theme})")
        self.current_theme = theme
        if hasattr(self.parent(), "accessibility_manager"):
            accessibility_manager = self.parent().accessibility_manager
            if (
                hasattr(accessibility_manager, "high_contrast_mode")
                and accessibility_manager.high_contrast_mode
            ):
                logger.info("🔧 고대비 모드가 활성화되어 있어 테마 적용을 건너뜀")
                return False
        if theme == "auto":
            palette = self.dark_palette if self.system_theme == "dark" else self.light_palette
            effective_theme = "dark" if self.system_theme == "dark" else "light"
        elif theme == "dark":
            palette = self.dark_palette
            effective_theme = "dark"
        else:
            palette = self.light_palette
            effective_theme = "light"
        logger.info(f"선택된 팔레트: {effective_theme} 테마")
        app = QApplication.instance()
        if app:
            app.setPalette(palette)
            logger.info("애플리케이션 팔레트 적용 완료")
            self._apply_theme_stylesheet(effective_theme)
            self.theme_changed.emit(theme)
            self.palette_updated.emit(palette)
            self.icon_theme_changed.emit(effective_theme)
            logger.info(f"✅ 테마 '{theme}' 적용 완료 (실제 적용: {effective_theme})")
            return True
        logger.error("QApplication 인스턴스를 찾을 수 없음")
        return False

    def switch_theme(self, theme: str) -> bool:
        """테마 전환 (apply_theme의 별칭)"""
        return self.apply_theme(theme)

    def _apply_theme_stylesheet(self, theme: str):
        """테마별 스타일시트 적용 (Phase 9.2)"""
        app = QApplication.instance()
        if not app:
            logger.error("QApplication 인스턴스를 찾을 수 없음")
            return
        logger.info(f"스타일시트 적용 시작: {theme} 테마")
        app.setStyleSheet("")

        # 기존 테마 시스템의 템플릿 파일들 로드
        theme_qss_content = self._load_theme_templates(theme)

        if theme_qss_content:
            # 기존 테마 시스템의 QSS 적용
            app.setStyleSheet(theme_qss_content)

            # 메인 윈도우에 테마별 objectName 설정
            self._set_theme_object_name(theme)

            logger.info(f"{theme} 테마 스타일시트 적용 완료 (기존 테마 시스템 사용)")
        else:
            # 폴백: 기본 스타일시트 적용
            logger.warning(f"테마 템플릿을 로드할 수 없어 기본 스타일을 적용합니다: {theme}")
            if theme == "dark":
                app.setStyleSheet("QWidget { background-color: #353535; color: #ffffff; }")
            else:
                app.setStyleSheet("QWidget { background-color: #f0f0f0; color: #000000; }")

    def _set_theme_object_name(self, theme: str):
        """메인 윈도우에 테마별 objectName 설정"""
        try:
            app = QApplication.instance()
            if app:
                # 모든 윈도우를 찾아서 objectName 설정
                for widget in app.allWidgets():
                    if isinstance(widget, QMainWindow) and hasattr(widget, "setObjectName"):
                        if theme == "dark":
                            widget.setObjectName("AppDark")
                        else:
                            widget.setObjectName("AppLight")
                        logger.info(f"메인 윈도우 objectName 설정: App{theme.capitalize()}")
                        break
        except Exception as e:
            logger.warning(f"메인 윈도우 objectName 설정 실패: {e}")

    def toggle_theme(self):
        """테마 토글 (라이트 ↔ 다크)"""
        if self.current_theme == "auto":
            new_theme = "light" if self.system_theme == "dark" else "dark"
        else:
            new_theme = "dark" if self.current_theme == "light" else "light"
        logger.info(f"테마 토글: {self.current_theme} → {new_theme}")
        self.apply_theme(new_theme)

    def reset_to_auto(self):
        """자동 테마 모드로 복원"""
        logger.info("테마를 자동 모드로 복원")
        self.apply_theme("auto")
