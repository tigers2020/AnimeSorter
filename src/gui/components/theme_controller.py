"""
테마 컨트롤러 - MainWindow에서 테마 관리 기능을 분리

MainWindow의 테마 관련 책임을 담당하는 전용 클래스입니다.
- 테마 적용 및 전환
- 시스템 테마 감지
- 테마 변경 시그널 처리
- 테마 모니터링
"""

import logging
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication

from .theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class ThemeController(QObject):
    """테마 관리 전용 컨트롤러"""

    # 시그널 정의
    theme_applied = pyqtSignal(str)  # 테마 적용 완료
    theme_detection_failed = pyqtSignal(str)  # 테마 감지 실패
    system_theme_changed = pyqtSignal(str)  # 시스템 테마 변경

    def __init__(self, theme_manager: ThemeManager, settings_manager=None):
        super().__init__()
        self.theme_manager = theme_manager
        self.settings_manager = settings_manager
        self.current_theme = "light"
        self.theme_monitor_widget = None

        logger.info("ThemeController 초기화 완료")

    def apply_theme(self, theme_name: Optional[str] = None, main_window=None) -> bool:
        """테마를 적용합니다"""
        try:
            # 설정에서 저장된 테마 가져오기
            if theme_name is None:
                saved_theme = self._get_saved_theme()
                theme_name = saved_theme

            # auto 테마인 경우 시스템 테마 감지
            if theme_name == "auto":
                theme_name = self._detect_system_theme()

            logger.info(f"테마 적용 시작: {theme_name}")

            # 테마 전환
            if self.theme_manager.switch_theme(theme_name):
                self.current_theme = theme_name

                # MainWindow가 제공된 경우 objectName 설정
                if main_window:
                    self._set_theme_object_name(main_window, theme_name)

                self.theme_applied.emit(theme_name)
                logger.info(f"✅ 테마 적용 완료: {theme_name}")
                return True
            else:
                logger.error(f"❌ 테마 적용 실패: {theme_name}")
                return False

        except Exception as e:
            logger.error(f"❌ 테마 적용 중 오류 발생: {e}")
            # 오류 발생 시 기본 라이트 테마 적용
            return self._apply_fallback_theme(main_window)

    def _get_saved_theme(self) -> str:
        """저장된 테마 설정을 가져옵니다"""
        try:
            if self.settings_manager:
                return self.settings_manager.get_setting("theme", "light")
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

                # 배경색의 밝기를 기준으로 다크/라이트 테마 판단
                brightness = (
                    background_color.red() * 299
                    + background_color.green() * 587
                    + background_color.blue() * 114
                ) / 1000

                detected_theme = "dark" if brightness < 128 else "light"
                logger.info(f"시스템 테마 감지: {detected_theme} (밝기: {brightness:.1f})")

                # 시스템 테마 변경 시그널 발생
                if detected_theme != self.current_theme:
                    self.system_theme_changed.emit(detected_theme)

                return detected_theme

            return "light"  # 기본값

        except Exception as e:
            logger.warning(f"⚠️ 시스템 테마 감지 실패: {e}")
            self.theme_detection_failed.emit(str(e))
            return "light"  # 기본값

    def _apply_fallback_theme(self, main_window=None) -> bool:
        """기본 테마로 복구"""
        try:
            logger.info("🔄 기본 라이트 테마로 복구 시도")
            if self.theme_manager.switch_theme("light"):
                self.current_theme = "light"

                # MainWindow가 제공된 경우 objectName 설정
                if main_window:
                    self._set_theme_object_name(main_window, "light")

                self.theme_applied.emit("light")
                logger.info("✅ 기본 테마 복구 성공")
                return True
            else:
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
                # Light theme (default)
                main_window.setObjectName("")

            logger.info(
                f"🎨 테마 objectName 설정: {theme_name} → {main_window.objectName() or 'Light'}"
            )

            # 하위 위젯들도 테마 변경 알림
            self._notify_theme_change_to_children(main_window, theme_name)

        except Exception as e:
            logger.error(f"❌ 테마 objectName 설정 실패: {e}")

    def _notify_theme_change_to_children(self, main_window, theme_name: str) -> None:
        """하위 위젯들에게 테마 변경을 알립니다"""
        try:
            from PyQt5.QtWidgets import QWidget

            # 모든 하위 위젯을 찾아서 테마 변경 알림
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
                return self.settings_manager.get_setting("theme", "light") == "auto"
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

            # 자식 위젯들의 테마 objectName 업데이트
            for child in parent_widget.findChildren(QObject):
                if hasattr(child, "setObjectName"):
                    self.set_theme_object_name(child, theme_name)

            logger.debug(f"자식 위젯 테마 변경 알림 완료: {theme_name}")

        except Exception as e:
            logger.warning(f"자식 위젯 테마 변경 알림 실패: {e}")

    def setup_theme_monitor(self, parent_widget=None):
        """테마 모니터링 위젯을 설정합니다"""
        try:
            # 테마 모니터링 위젯 생성 (필요시)
            if parent_widget and not self.theme_monitor_widget:
                # 여기에 테마 모니터링 위젯 생성 로직 추가
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
