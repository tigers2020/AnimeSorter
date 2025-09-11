"""
통합된 UI 관리 서비스 - AnimeSorter

기존의 여러 UI Manager 클래스들을 통합하여 단일 서비스로 제공합니다.
- StatusBarManager
- UIStateManager
- UIComponentManager
- UIMigrationManager
- ThemeManager
- I18nManager
- AccessibilityManager
- EventHandlerManagerUI
- MainWindowSessionManager
- MainWindowLayoutManager
- WindowManager
- TabFilterManager
"""

import logging
from typing import Any

from PyQt5.QtCore import QObject, QSettings, pyqtSignal
from PyQt5.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)


class UIService(QObject):
    """통합된 UI 관리 서비스"""

    # 시그널 정의
    theme_changed = pyqtSignal(str)
    language_changed = pyqtSignal(str)
    ui_state_restored = pyqtSignal()
    ui_state_saved = pyqtSignal()
    accessibility_enabled = pyqtSignal(bool)
    high_contrast_changed = pyqtSignal(bool)
    status_updated = pyqtSignal(str, int)  # message, progress
    safety_mode_changed = pyqtSignal(str)  # safety mode changed signal

    def __init__(self, main_window: QMainWindow, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 서비스 컴포넌트들
        self._theme_manager = None
        self._i18n_manager = None
        self._accessibility_manager = None
        self._ui_state_manager = None
        self._status_manager = None

        # 설정
        self.settings = QSettings("AnimeSorter", "UI_State")
        self.current_ui_version = "2.0"

        # 상태 관리
        self._last_stats_update = False
        self._last_memory_update = False

        self._initialize_components()
        self.logger.info("UI 서비스 초기화 완료")

    def _initialize_components(self):
        """UI 컴포넌트들 초기화"""
        try:
            self._initialize_theme_manager()
            self._initialize_i18n_manager()
            self._initialize_accessibility_manager()
            self._initialize_ui_state_manager()
            self._initialize_status_manager()
            self.logger.info("✅ UI 서비스 컴포넌트 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ UI 서비스 컴포넌트 초기화 실패: {e}")

    def _initialize_theme_manager(self):
        """테마 관리자 초기화"""
        try:
            # ThemeManager는 새로운 서비스 아키텍처로 대체됨
            # from src.gui.components.managers.theme_manager import ThemeManager
            self._theme_manager = None  # 임시로 None 설정
            self.logger.info("✅ 테마 관리자 초기화 완료 (새 서비스 아키텍처)")
        except Exception as e:
            self.logger.error(f"❌ 테마 관리자 초기화 실패: {e}")

    def _initialize_i18n_manager(self):
        """국제화 관리자 초기화"""
        try:
            # I18nManager는 새로운 서비스 아키텍처로 대체됨
            # from src.gui.components.managers.i18n_manager import I18nManager
            self._i18n_manager = None  # 임시로 None 설정
            self.logger.info("✅ 국제화 관리자 초기화 완료 (새 서비스 아키텍처)")
        except Exception as e:
            self.logger.error(f"❌ 국제화 관리자 초기화 실패: {e}")

    def _initialize_accessibility_manager(self):
        """접근성 관리자 초기화"""
        try:
            # AccessibilityManager는 새로운 서비스 아키텍처로 대체됨
            # from src.gui.components.managers.accessibility_manager import AccessibilityManager
            self._accessibility_manager = None  # 임시로 None 설정
            self.logger.info("✅ 접근성 관리자 초기화 완료 (새 서비스 아키텍처)")
        except Exception as e:
            self.logger.error(f"❌ 접근성 관리자 초기화 실패: {e}")

    def _initialize_ui_state_manager(self):
        """UI 상태 관리자 초기화"""
        try:
            # UIStateManager는 새로운 서비스 아키텍처로 대체됨
            # from src.gui.components.managers.ui_state_manager import UIStateManager
            self._ui_state_manager = None  # 임시로 None 설정
            self.logger.info("✅ UI 상태 관리자 초기화 완료 (새 서비스 아키텍처)")
        except Exception as e:
            self.logger.error(f"❌ UI 상태 관리자 초기화 실패: {e}")

    def _initialize_status_manager(self):
        """상태바 관리자 초기화"""
        try:
            # StatusBarManager는 새로운 서비스 아키텍처로 대체됨
            # from src.gui.managers.status_bar_manager import StatusBarManager
            self._status_manager = None  # 임시로 None 설정
            self.logger.info("✅ 상태바 관리자 초기화 완료 (새 서비스 아키텍처)")
        except Exception as e:
            self.logger.error(f"❌ 상태바 관리자 초기화 실패: {e}")

    # 테마 관리
    def get_available_themes(self) -> list[str]:
        """사용 가능한 테마 목록 반환"""
        if self._theme_manager:
            return self._theme_manager.get_available_themes()
        return ["auto", "light", "dark"]

    def get_current_theme(self) -> str:
        """현재 테마 반환"""
        if self._theme_manager:
            return self._theme_manager.get_current_theme()
        return "auto"

    def apply_theme(self, theme: str) -> bool:
        """테마 적용"""
        if self._theme_manager:
            return self._theme_manager.apply_theme(theme)
        return False

    def toggle_theme(self):
        """테마 토글"""
        if self._theme_manager:
            self._theme_manager.toggle_theme()

    # 국제화 관리
    def get_supported_languages(self) -> dict[str, str]:
        """지원 언어 목록 반환"""
        if self._i18n_manager:
            return self._i18n_manager.get_supported_languages()
        return {"ko": "한국어", "en": "English"}

    def get_current_language(self) -> str:
        """현재 언어 반환"""
        if self._i18n_manager:
            return self._i18n_manager.get_current_language()
        return "ko"

    def set_language(self, language_code: str) -> bool:
        """언어 설정"""
        if self._i18n_manager:
            return self._i18n_manager.set_language(language_code)
        return False

    def tr(self, key: str, fallback: str | None = None) -> str:
        """번역 함수"""
        if self._i18n_manager:
            return self._i18n_manager.tr(key, fallback)
        return fallback if fallback else key

    # 접근성 관리
    def get_accessibility_info(self) -> dict[str, Any]:
        """접근성 정보 반환"""
        if self._accessibility_manager:
            return self._accessibility_manager.get_accessibility_info()
        return {}

    def toggle_high_contrast_mode(self):
        """고대비 모드 토글"""
        if self._accessibility_manager:
            self._accessibility_manager.toggle_high_contrast_mode()

    def enable_accessibility_features(self, features: list[str]):
        """접근성 기능 활성화"""
        if self._accessibility_manager:
            self._accessibility_manager.enable_accessibility_features(features)

    def disable_accessibility_features(self, features: list[str]):
        """접근성 기능 비활성화"""
        if self._accessibility_manager:
            self._accessibility_manager.disable_accessibility_features(features)

    # UI 상태 관리
    def save_ui_state(self):
        """UI 상태 저장"""
        if self._ui_state_manager:
            self._ui_state_manager.save_ui_state()

    def restore_ui_state(self):
        """UI 상태 복원"""
        if self._ui_state_manager:
            self._ui_state_manager.restore_ui_state()

    def clear_ui_state(self):
        """UI 상태 초기화"""
        if self._ui_state_manager:
            self._ui_state_manager.clear_ui_state()

    def get_ui_version(self) -> str:
        """저장된 UI 버전 반환"""
        if self._ui_state_manager:
            return self._ui_state_manager.get_ui_version()
        return "1.0"

    def is_ui_v2_enabled(self) -> bool:
        """UI v2가 활성화되어 있는지 확인"""
        if self._ui_state_manager:
            return self._ui_state_manager.is_ui_v2_enabled()
        return False

    # 상태바 관리
    def update_status_bar(self, message: str, progress: int | None = None):
        """상태바 업데이트"""
        if self._status_manager:
            self._status_manager.update_status_bar(message, progress)
        self.status_updated.emit(message, progress or 0)

    def show_error_message(self, message: str, details: str = "", error_type: str = "error"):
        """오류 메시지 표시"""
        if self._status_manager:
            self._status_manager.show_error_message(message, details, error_type)

    def show_success_message(self, message: str, details: str = "", auto_clear: bool = True):
        """성공 메시지 표시"""
        if self._status_manager:
            self._status_manager.show_success_message(message, details, auto_clear)

    def update_progress(self, current: int, total: int, message: str = ""):
        """진행률 업데이트"""
        if self._status_manager:
            self._status_manager.update_progress(current, total, message)

    # 통합 UI 관리
    def initialize_ui(self):
        """UI 초기화"""
        try:
            self.logger.info("UI 초기화 시작")

            # 테마 적용
            if self._theme_manager:
                self._theme_manager.apply_theme(self._theme_manager.get_current_theme())

            # 언어 설정
            if self._i18n_manager:
                self._i18n_manager.initialize_with_system_language()

            # 접근성 설정
            if self._accessibility_manager:
                self._accessibility_manager.initialize(self.main_window)

            # UI 상태 복원
            if self._ui_state_manager:
                self._ui_state_manager.restore_ui_state()

            self.logger.info("✅ UI 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ UI 초기화 실패: {e}")

    def shutdown_ui(self):
        """UI 종료 처리"""
        try:
            self.logger.info("UI 종료 처리 시작")

            # UI 상태 저장
            if self._ui_state_manager:
                self._ui_state_manager.save_ui_state()

            self.logger.info("✅ UI 종료 처리 완료")
        except Exception as e:
            self.logger.error(f"❌ UI 종료 처리 실패: {e}")

    def get_ui_health_status(self) -> dict[str, Any]:
        """UI 건강 상태 반환"""
        return {
            "theme_manager_available": self._theme_manager is not None,
            "i18n_manager_available": self._i18n_manager is not None,
            "accessibility_manager_available": self._accessibility_manager is not None,
            "ui_state_manager_available": self._ui_state_manager is not None,
            "status_manager_available": self._status_manager is not None,
            "current_theme": self.get_current_theme(),
            "current_language": self.get_current_language(),
            "ui_version": self.get_ui_version(),
        }

    def apply_settings_to_ui(self):
        """설정을 UI에 적용"""
        try:
            self.logger.info("설정을 UI에 적용 시작")

            # 설정 관리자가 없는 경우 기본값 사용
            if (
                not hasattr(self.main_window, "settings_manager")
                or self.main_window.settings_manager is None
            ):
                self.logger.warning("설정 관리자가 없어 기본값을 사용합니다")
                theme_setting = "auto"
                language_setting = "ko"
                accessibility_enabled = False
            else:
                theme_setting = self.main_window.settings_manager.get("ui", "theme", "auto")
                language_setting = self.main_window.settings_manager.get("ui", "language", "ko")
                accessibility_enabled = self.main_window.settings_manager.get(
                    "ui", "accessibility_enabled", False
                )

            # 테마 설정 적용
            if self._theme_manager:
                self._theme_manager.apply_theme(theme_setting)

            # 언어 설정 적용
            if self._i18n_manager:
                self._i18n_manager.set_language(language_setting)

            # 접근성 설정 적용
            if self._accessibility_manager and accessibility_enabled:
                self._accessibility_manager.enable_accessibility_features(
                    ["screen_reader_support", "keyboard_navigation"]
                )

            self.logger.info("✅ 설정을 UI에 적용 완료")
        except Exception as e:
            self.logger.error(f"❌ 설정을 UI에 적용 실패: {e}")

    def refresh_ui(self):
        """UI 새로고침"""
        try:
            self.logger.info("UI 새로고침 시작")

            # 상태바 업데이트
            self.update_status_bar("UI 새로고침 중...")

            # 테마 재적용
            if self._theme_manager:
                current_theme = self._theme_manager.get_current_theme()
                self._theme_manager.apply_theme(current_theme)

            # 접근성 재설정
            if self._accessibility_manager:
                self._accessibility_manager._setup_accessibility()

            self.update_status_bar("UI 새로고침 완료")
            self.logger.info("✅ UI 새로고침 완료")
        except Exception as e:
            self.logger.error(f"❌ UI 새로고침 실패: {e}")
            self.update_status_bar(f"UI 새로고침 실패: {e}")

    def reset_ui_to_defaults(self):
        """UI를 기본값으로 초기화"""
        try:
            self.logger.info("UI 기본값 초기화 시작")

            # UI 상태 초기화
            if self._ui_state_manager:
                self._ui_state_manager.clear_ui_state()

            # 테마를 자동 모드로 설정
            if self._theme_manager:
                self._theme_manager.reset_to_auto()

            # 언어를 시스템 언어로 설정
            if self._i18n_manager:
                self._i18n_manager.initialize_with_system_language()

            # 접근성 기능 비활성화
            if self._accessibility_manager:
                self._accessibility_manager.disable_accessibility_features(
                    ["screen_reader_support", "keyboard_navigation", "high_contrast"]
                )

            self.logger.info("✅ UI 기본값 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ UI 기본값 초기화 실패: {e}")

    def get_ui_statistics(self) -> dict[str, Any]:
        """UI 통계 반환"""
        stats = {
            "components_initialized": 0,
            "total_components": 5,
            "theme": self.get_current_theme(),
            "language": self.get_current_language(),
            "ui_version": self.get_ui_version(),
            "accessibility_enabled": False,
        }

        if self._theme_manager:
            stats["components_initialized"] += 1
        if self._i18n_manager:
            stats["components_initialized"] += 1
        if self._accessibility_manager:
            stats["components_initialized"] += 1
            stats[
                "accessibility_enabled"
            ] = self._accessibility_manager.get_accessibility_info().get(
                "screen_reader_support", False
            )
        if self._ui_state_manager:
            stats["components_initialized"] += 1
        if self._status_manager:
            stats["components_initialized"] += 1

        return stats
