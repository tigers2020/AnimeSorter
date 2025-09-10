"""
테마 컨트롤러 - MainWindow에서 테마 관리 기능을 분리

MainWindow의 테마 관련 책임을 담당하는 전용 클래스입니다.
- 테마 적용 및 전환
- 시스템 테마 감지
- 테마 변경 시그널 처리
- 테마 모니터링
"""

import logging

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication

from src.gui.components.managers.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class ThemeController(QObject):
    """테마 관리 전용 컨트롤러"""

    theme_applied = pyqtSignal(str)
    theme_detection_failed = pyqtSignal(str)
    system_theme_changed = pyqtSignal(str)

    def __init__(self, theme_manager: ThemeManager, settings_manager=None):
        super().__init__()
        self.theme_manager = theme_manager
        self.settings_manager = settings_manager
        self.current_theme = "light"
        self.theme_monitor_widget = None
        logger.info("ThemeController 초기화 완료")

    def apply_theme(self, theme_name: str | None = None, main_window=None) -> bool:
        """테마를 적용합니다"""
        try:
            if theme_name is None:
                saved_theme = self._get_saved_theme()
                theme_name = saved_theme
            if theme_name == "auto":
                theme_name = self._detect_system_theme()
            logger.info(f"테마 적용 시작: {theme_name}")
            if self.theme_manager.switch_theme(theme_name):
                self.current_theme = theme_name
                if main_window:
                    self._set_theme_object_name(main_window, theme_name)
                self.theme_applied.emit(theme_name)
                logger.info(f"✅ 테마 적용 완료: {theme_name}")
                return True
            logger.error(f"❌ 테마 적용 실패: {theme_name}")
            return False
        except Exception as e:
            logger.error(f"❌ 테마 적용 중 오류 발생: {e}")
            return self._apply_fallback_theme(main_window)

    def _get_saved_theme(self) -> str:
        """저장된 테마 설정을 가져옵니다"""
        try:
            if self.settings_manager and hasattr(self.settings_manager, "config"):
                theme_prefs = getattr(
                    self.settings_manager.config.user_preferences, "theme_preferences", {}
                )
                if isinstance(theme_prefs, dict):
                    return theme_prefs.get("theme", "light")
                return getattr(theme_prefs, "theme", "light")
            return "light"
        except Exception as e:
            logger.warning(f"저장된 테마 설정 조회 실패: {e}")
            return "light"

    def _detect_system_theme(self) -> str:
        """시스템 테마를 감지합니다"""
        try:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                background_color = palette.color(QPalette.Window)
                brightness = (
                    background_color.red() * 299
                    + background_color.green() * 587
                    + background_color.blue() * 114
                ) / 1000
                detected_theme = "dark" if brightness < 128 else "light"
                logger.info(f"시스템 테마 감지: {detected_theme} (밝기: {brightness:.1f})")
                if detected_theme != self.current_theme:
                    self.system_theme_changed.emit(detected_theme)
                return detected_theme
            return "light"
        except Exception as e:
            logger.warning(f"⚠️ 시스템 테마 감지 실패: {e}")
            self.theme_detection_failed.emit(str(e))
            return "light"

    def _apply_fallback_theme(self, main_window=None) -> bool:
        """기본 테마로 복구"""
        try:
            logger.info("🔄 기본 라이트 테마로 복구 시도")
            if self.theme_manager.switch_theme("light"):
                self.current_theme = "light"
                if main_window:
                    self._set_theme_object_name(main_window, "light")
                self.theme_applied.emit("light")
                logger.info("✅ 기본 테마 복구 성공")
                return True
            logger.error("❌ 기본 테마 복구 실패")
            return False
        except Exception as e:
            logger.error(f"❌ 기본 테마 복구 중 오류: {e}")
            return False

    def switch_theme(self, theme_name: str) -> bool:
        """테마를 전환합니다"""
        return self.apply_theme(theme_name)

    def get_available_themes(self) -> list[str]:
        """사용 가능한 테마 목록을 반환합니다"""
        try:
            return self.theme_manager.get_available_themes()
        except Exception as e:
            logger.error(f"사용 가능한 테마 목록 조회 실패: {e}")
            return ["light", "dark"]

    def _set_theme_object_name(self, main_window, theme_name: str) -> None:
        """테마별로 루트 위젯의 objectName을 설정합니다"""
        try:
            if theme_name == "dark":
                main_window.setObjectName("AppDark")
            elif theme_name == "high-contrast":
                main_window.setObjectName("AppHighContrast")
            else:
                main_window.setObjectName("")
            logger.info(
                f"🎨 테마 objectName 설정: {theme_name} → {main_window.objectName() or 'Light'}"
            )
            self._notify_theme_change_to_children(main_window, theme_name)
        except Exception as e:
            logger.error(f"❌ 테마 objectName 설정 실패: {e}")

    def _notify_theme_change_to_children(self, main_window, theme_name: str) -> None:
        """하위 위젯들에게 테마 변경을 알립니다"""
        try:
            from PyQt5.QtWidgets import QWidget

            for child in main_window.findChildren(QWidget):
                if hasattr(child, "on_theme_changed"):
                    child.on_theme_changed(theme_name)
        except Exception as e:
            logger.error(f"❌ 하위 위젯 테마 변경 알림 실패: {e}")

    def get_current_theme(self) -> str:
        """현재 적용된 테마를 반환합니다"""
        return self.current_theme

    def is_dark_theme(self) -> bool:
        """현재 다크 테마인지 확인"""
        return self.current_theme == "dark"

    def is_light_theme(self) -> bool:
        """현재 라이트 테마인지 확인"""
        return self.current_theme == "light"

    def is_auto_theme(self) -> bool:
        """자동 테마 모드인지 확인"""
        try:
            if self.settings_manager:
                theme = getattr(
                    self.settings_manager.config.user_preferences.theme_preferences,
                    "theme",
                    "light",
                )
                return theme == "auto"
            return False
        except Exception:
            return False

    def set_theme_object_name(self, widget, theme_name: str) -> None:
        """위젯의 테마별 objectName을 설정합니다"""
        try:
            if widget:
                widget.setObjectName(f"theme_{theme_name}")
                logger.debug(f"위젯 테마 objectName 설정: {theme_name}")
        except Exception as e:
            logger.warning(f"위젯 테마 objectName 설정 실패: {e}")

    def notify_theme_change_to_children(self, parent_widget, theme_name: str) -> None:
        """자식 위젯들에게 테마 변경을 알립니다"""
        try:
            if not parent_widget:
                return
            for child in parent_widget.findChildren(QObject):
                if hasattr(child, "setObjectName"):
                    self.set_theme_object_name(child, theme_name)
            logger.debug(f"자식 위젯 테마 변경 알림 완료: {theme_name}")
        except Exception as e:
            logger.warning(f"자식 위젯 테마 변경 알림 실패: {e}")

    def setup_theme_monitor(self, parent_widget=None):
        """테마 모니터링 위젯을 설정합니다"""
        try:
            if parent_widget and not self.theme_monitor_widget:
                logger.info("테마 모니터링 위젯 설정 완료")
        except Exception as e:
            logger.warning(f"테마 모니터링 위젯 설정 실패: {e}")

    def cleanup(self):
        """리소스 정리"""
        try:
            self.theme_monitor_widget = None
            logger.info("ThemeController 정리 완료")
        except Exception as e:
            logger.error(f"ThemeController 정리 실패: {e}")

    def __str__(self) -> str:
        return f"ThemeController(current_theme={self.current_theme})"

    def __repr__(self) -> str:
        return f"ThemeController(theme_manager={self.theme_manager}, current_theme='{self.current_theme}')"
