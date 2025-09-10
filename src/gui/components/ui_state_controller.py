"""
UI 상태 컨트롤러 - MainWindow에서 UI 상태 관리 기능을 분리

MainWindow의 UI 상태 관리 책임을 담당하는 전용 클래스입니다.
- UI 상태 저장 및 복원
- 세션 상태 관리
- 레이아웃 상태 관리
- 접근성 모드 관리
- 언어 설정 관리
"""

import json
import logging
from typing import Any

from PyQt5.QtCore import QObject, QSettings, pyqtSignal
from PyQt5.QtWidgets import QDockWidget, QMainWindow, QStatusBar

logger = logging.getLogger(__name__)


class UIStateController(QObject):
    """UI 상태 관리 전용 컨트롤러"""

    state_saved = pyqtSignal(str)
    state_restored = pyqtSignal(str)
    state_reset = pyqtSignal()
    accessibility_mode_changed = pyqtSignal(bool)
    high_contrast_mode_changed = pyqtSignal(bool)
    language_changed = pyqtSignal(str)

    def __init__(self, main_window: QMainWindow, settings_manager=None):
        super().__init__()
        self.main_window = main_window
        self.settings_manager = settings_manager
        self.settings = QSettings("AnimeSorter", "UIState")
        self.accessibility_mode = False
        self.high_contrast_mode = False
        self.current_language = "ko"
        self.log_dock_visible = False
        self.supported_languages = {"ko": "한국어", "en": "English", "ja": "日本語"}
        logger.info("UIStateController 초기화 완료")

    def save_session_state(self) -> bool:
        """현재 세션 상태를 저장합니다"""
        try:
            state_data = {
                "window_geometry": self._get_window_geometry(),
                "window_state": self._get_window_state(),
                "dock_widgets": self._get_dock_widgets_state(),
                "accessibility_mode": self.accessibility_mode,
                "high_contrast_mode": self.high_contrast_mode,
                "current_language": self.current_language,
                "log_dock_visible": self.log_dock_visible,
                "table_columns": self._get_table_columns_state(),
                "splitter_sizes": self._get_splitter_sizes(),
                "last_directory": self._get_last_directory(),
            }
            if self.settings_manager:
                self.settings_manager.set_setting("ui_session_state", state_data)
            self.settings.setValue("session_state", json.dumps(state_data))
            logger.info("✅ 세션 상태 저장 완료")
            self.state_saved.emit("session")
            return True
        except Exception as e:
            logger.error(f"❌ 세션 상태 저장 실패: {e}")
            return False

    def restore_session_state(self) -> bool:
        """저장된 세션 상태를 복원합니다"""
        try:
            state_json = self.settings.value("session_state", "{}")
            if isinstance(state_json, str):
                state_data = json.loads(state_json)
            else:
                state_data: dict[str, Any] = {}
            if self.settings_manager:
                saved_state = getattr(
                    self.settings_manager.config.user_preferences.gui_state, "ui_session_state", {}
                )
                if saved_state:
                    state_data.update(saved_state)
            if not state_data:
                logger.info("저장된 세션 상태가 없습니다.")
                return True
            self._restore_window_geometry(state_data.get("window_geometry"))
            self._restore_window_state(state_data.get("window_state"))
            self._restore_dock_widgets(state_data.get("dock_widgets"))
            self._restore_accessibility_settings(state_data)
            self._restore_language_settings(state_data)
            self._restore_table_columns(state_data.get("table_columns"))
            self._restore_splitter_sizes(state_data.get("splitter_sizes"))
            logger.info("✅ 세션 상태 복원 완료")
            self.state_restored.emit("session")
            return True
        except Exception as e:
            logger.error(f"❌ 세션 상태 복원 실패: {e}")
            return False

    def reset_state(self) -> bool:
        """UI 상태를 초기화합니다"""
        try:
            self.accessibility_mode = False
            self.high_contrast_mode = False
            self.current_language = "ko"
            self.log_dock_visible = False
            self.settings.remove("session_state")
            if self.settings_manager:
                self.settings_manager.set_setting("ui_session_state", {})
            self._reset_window_state()
            self._reset_dock_widgets()
            self._reset_accessibility_settings()
            logger.info("✅ UI 상태 초기화 완료")
            self.state_reset.emit()
            return True
        except Exception as e:
            logger.error(f"❌ UI 상태 초기화 실패: {e}")
            return False

    def toggle_accessibility_mode(self) -> bool:
        """접근성 모드를 토글합니다"""
        try:
            self.accessibility_mode = not self.accessibility_mode
            if self.accessibility_mode:
                self._enable_accessibility_features()
            else:
                self._disable_accessibility_features()
            if self.settings_manager:
                self.settings_manager.set_setting("accessibility_mode", self.accessibility_mode)
            logger.info(f"접근성 모드 {'활성화' if self.accessibility_mode else '비활성화'}")
            self.accessibility_mode_changed.emit(self.accessibility_mode)
            return True
        except Exception as e:
            logger.error(f"접근성 모드 토글 실패: {e}")
            return False

    def toggle_high_contrast_mode(self) -> bool:
        """고대비 모드를 토글합니다"""
        try:
            self.high_contrast_mode = not self.high_contrast_mode
            if self.high_contrast_mode:
                self._enable_high_contrast_features()
            else:
                self._disable_high_contrast_features()
            if self.settings_manager:
                self.settings_manager.set_setting("high_contrast_mode", self.high_contrast_mode)
            logger.info(f"고대비 모드 {'활성화' if self.high_contrast_mode else '비활성화'}")
            self.high_contrast_mode_changed.emit(self.high_contrast_mode)
            return True
        except Exception as e:
            logger.error(f"고대비 모드 토글 실패: {e}")
            return False

    def change_language(self, language_code: str) -> bool:
        """언어를 변경합니다"""
        try:
            if language_code not in self.supported_languages:
                logger.warning(f"지원하지 않는 언어 코드: {language_code}")
                return False
            old_language = self.current_language
            self.current_language = language_code
            self._apply_language_change(language_code)
            if self.settings_manager:
                self.settings_manager.set_setting("language", language_code)
            logger.info(f"언어 변경: {old_language} -> {language_code}")
            self.language_changed.emit(language_code)
            return True
        except Exception as e:
            logger.error(f"언어 변경 실패: {e}")
            return False

    def get_accessibility_info(self) -> dict[str, Any]:
        """접근성 정보를 반환합니다"""
        return {
            "accessibility_mode": self.accessibility_mode,
            "high_contrast_mode": self.high_contrast_mode,
            "current_language": self.current_language,
            "supported_languages": self.supported_languages,
            "log_dock_visible": self.log_dock_visible,
        }

    def get_current_language(self) -> str:
        """현재 언어를 반환합니다"""
        return self.current_language

    def get_supported_languages(self) -> dict[str, str]:
        """지원하는 언어 목록을 반환합니다"""
        return self.supported_languages.copy()

    def toggle_log_dock(self) -> bool:
        """로그 도킹 위젯을 토글합니다"""
        try:
            self.log_dock_visible = not self.log_dock_visible
            if self.log_dock_visible:
                self.show_log_dock()
            else:
                self.hide_log_dock()
            return True
        except Exception as e:
            logger.error(f"로그 도킹 위젯 토글 실패: {e}")
            return False

    def show_log_dock(self):
        """로그 도킹 위젯을 표시합니다"""
        try:
            for dock in self.main_window.findChildren(QDockWidget):
                if "log" in dock.objectName().lower():
                    dock.show()
                    self.log_dock_visible = True
                    break
            logger.debug("로그 도킹 위젯 표시")
        except Exception as e:
            logger.warning(f"로그 도킹 위젯 표시 실패: {e}")

    def hide_log_dock(self):
        """로그 도킹 위젯을 숨깁니다"""
        try:
            for dock in self.main_window.findChildren(QDockWidget):
                if "log" in dock.objectName().lower():
                    dock.hide()
                    self.log_dock_visible = False
                    break
            logger.debug("로그 도킹 위젯 숨김")
        except Exception as e:
            logger.warning(f"로그 도킹 위젯 숨김 실패: {e}")

    def update_status_bar(self, message: str, progress: int | None = None) -> bool:
        """상태바를 업데이트합니다"""
        try:
            if hasattr(self.main_window, "statusBar"):
                status_bar = self.main_window.statusBar()
                if isinstance(status_bar, QStatusBar):
                    status_bar.showMessage(message)
                    if progress is not None:
                        pass
                    return True
            return False
        except Exception as e:
            logger.error(f"상태바 업데이트 실패: {e}")
            return False

    def update_progress(self, current: int, total: int, message: str = "") -> bool:
        """진행률을 업데이트합니다"""
        try:
            if total > 0:
                progress_percent = int(current / total * 100)
                progress_message = f"{message} ({current}/{total}, {progress_percent}%)"
                return self.update_status_bar(progress_message, progress_percent)
            return self.update_status_bar(message)
        except Exception as e:
            logger.error(f"진행률 업데이트 실패: {e}")
            return False

    def _get_window_geometry(self) -> dict[str, int]:
        """윈도우 지오메트리를 가져옵니다"""
        try:
            geometry = self.main_window.geometry()
            return {
                "x": geometry.x(),
                "y": geometry.y(),
                "width": geometry.width(),
                "height": geometry.height(),
            }
        except Exception:
            return {}

    def _get_window_state(self) -> str:
        """윈도우 상태를 가져옵니다"""
        try:
            state = self.main_window.saveState()
            if hasattr(state, "toBase64"):
                return state.toBase64().data().decode("utf-8")
            if isinstance(state, bytes):
                import base64

                return base64.b64encode(state).decode("utf-8")
            return ""
        except Exception:
            return ""

    def _get_dock_widgets_state(self) -> dict[str, bool]:
        """도킹 위젯들의 상태를 가져옵니다"""
        try:
            dock_states = {}
            for dock in self.main_window.findChildren(QDockWidget):
                dock_states[dock.objectName()] = dock.isVisible()
            return dock_states
        except Exception:
            return {}

    def _get_table_columns_state(self) -> dict[str, Any]:
        """테이블 컬럼 상태를 가져옵니다"""
        try:
            return {}
        except Exception:
            return {}

    def _get_splitter_sizes(self) -> list[int]:
        """스플리터 크기를 가져옵니다"""
        try:
            return []
        except Exception:
            return []

    def _get_last_directory(self) -> str:
        """마지막 사용 디렉토리를 가져옵니다"""
        try:
            if self.settings_manager:
                return getattr(
                    self.settings_manager.config.user_preferences.gui_state, "last_directory", ""
                )
            return ""
        except Exception:
            return ""

    def _restore_window_geometry(self, geometry_data: dict[str, int]):
        """윈도우 지오메트리를 복원합니다"""
        try:
            if geometry_data and len(geometry_data) == 4:
                from PyQt5.QtCore import QRect

                rect = QRect(
                    geometry_data.get("x", 100),
                    geometry_data.get("y", 100),
                    geometry_data.get("width", 800),
                    geometry_data.get("height", 600),
                )
                self.main_window.setGeometry(rect)
        except Exception as e:
            logger.warning(f"윈도우 지오메트리 복원 실패: {e}")

    def _restore_window_state(self, state_data: str):
        """윈도우 상태를 복원합니다"""
        try:
            if state_data:
                import base64

                from PyQt5.QtCore import QByteArray

                state_bytes = base64.b64decode(state_data.encode("utf-8"))
                state_bytearray = QByteArray(state_bytes)
                self.main_window.restoreState(state_bytearray)
        except Exception as e:
            logger.warning(f"윈도우 상태 복원 실패: {e}")

    def _restore_dock_widgets(self, dock_states: dict[str, bool]):
        """도킹 위젯들을 복원합니다"""
        try:
            if not dock_states:
                return
            for dock in self.main_window.findChildren(QDockWidget):
                dock_name = dock.objectName()
                if dock_name in dock_states:
                    if dock_states[dock_name]:
                        dock.show()
                    else:
                        dock.hide()
        except Exception as e:
            logger.warning(f"도킹 위젯 복원 실패: {e}")

    def _restore_accessibility_settings(self, state_data: dict[str, Any]):
        """접근성 설정을 복원합니다"""
        try:
            self.accessibility_mode = state_data.get("accessibility_mode", False)
            self.high_contrast_mode = state_data.get("high_contrast_mode", False)
            if self.accessibility_mode:
                self._enable_accessibility_features()
            if self.high_contrast_mode:
                self._enable_high_contrast_features()
        except Exception as e:
            logger.warning(f"접근성 설정 복원 실패: {e}")

    def _restore_language_settings(self, state_data: dict[str, Any]):
        """언어 설정을 복원합니다"""
        try:
            language = state_data.get("current_language", "ko")
            if language in self.supported_languages:
                self.current_language = language
                self._apply_language_change(language)
        except Exception as e:
            logger.warning(f"언어 설정 복원 실패: {e}")

    def _restore_table_columns(self, columns_state: dict[str, Any]):
        """테이블 컬럼을 복원합니다"""
        try:
            pass
        except Exception as e:
            logger.warning(f"테이블 컬럼 복원 실패: {e}")

    def _restore_splitter_sizes(self, splitter_sizes: list[int]):
        """스플리터 크기를 복원합니다"""
        try:
            pass
        except Exception as e:
            logger.warning(f"스플리터 크기 복원 실패: {e}")

    def _reset_window_state(self):
        """윈도우 상태를 초기화합니다"""
        try:
            self.main_window.resize(800, 600)
            self.main_window.move(100, 100)
        except Exception as e:
            logger.warning(f"윈도우 상태 초기화 실패: {e}")

    def _reset_dock_widgets(self):
        """도킹 위젯들을 초기화합니다"""
        try:
            for dock in self.main_window.findChildren(QDockWidget):
                dock.hide()
        except Exception as e:
            logger.warning(f"도킹 위젯 초기화 실패: {e}")

    def _reset_accessibility_settings(self):
        """접근성 설정을 초기화합니다"""
        try:
            self._disable_accessibility_features()
            self._disable_high_contrast_features()
        except Exception as e:
            logger.warning(f"접근성 설정 초기화 실패: {e}")

    def _enable_accessibility_features(self):
        """접근성 기능을 활성화합니다"""
        try:
            logger.debug("접근성 기능 활성화")
        except Exception as e:
            logger.warning(f"접근성 기능 활성화 실패: {e}")

    def _disable_accessibility_features(self):
        """접근성 기능을 비활성화합니다"""
        try:
            logger.debug("접근성 기능 비활성화")
        except Exception as e:
            logger.warning(f"접근성 기능 비활성화 실패: {e}")

    def _enable_high_contrast_features(self):
        """고대비 기능을 활성화합니다"""
        try:
            logger.debug("고대비 기능 활성화")
        except Exception as e:
            logger.warning(f"고대비 기능 활성화 실패: {e}")

    def _disable_high_contrast_features(self):
        """고대비 기능을 비활성화합니다"""
        try:
            logger.debug("고대비 기능 비활성화")
        except Exception as e:
            logger.warning(f"고대비 기능 비활성화 실패: {e}")

    def _apply_language_change(self, language_code: str):
        """언어 변경을 적용합니다"""
        try:
            logger.debug(f"언어 변경 적용: {language_code}")
        except Exception as e:
            logger.warning(f"언어 변경 적용 실패: {e}")

    def cleanup(self):
        """리소스 정리"""
        try:
            self.save_session_state()
            logger.info("UIStateController 정리 완료")
        except Exception as e:
            logger.error(f"UIStateController 정리 실패: {e}")

    def __str__(self) -> str:
        return f"UIStateController(lang={self.current_language}, accessibility={self.accessibility_mode})"

    def __repr__(self) -> str:
        return (
            f"UIStateController(main_window={self.main_window}, language='{self.current_language}')"
        )
