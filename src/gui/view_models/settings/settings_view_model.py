"""
Settings ViewModel - Phase 3.3 뷰모델 분할
애플리케이션 설정 관리의 ViewModel 로직을 담당합니다.
"""

import logging
from typing import Any

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from src.app import (IUIUpdateService, SettingsChangedEvent,
                     SettingsExportEvent, SettingsImportEvent,
                     SettingsResetEvent, SettingsSavedEvent,
                     StatusBarUpdateEvent, SuccessMessageEvent, TypedEventBus,
                     get_event_bus, get_service)
from src.core.unified_config import unified_config_manager

from .settings_state import SettingsCapabilities, SettingsState


class SettingsViewModel(QObject):
    """설정 관리 ViewModel"""

    # 시그널
    state_changed = pyqtSignal()
    capabilities_changed = pyqtSignal()
    settings_loaded = pyqtSignal()
    settings_saved = pyqtSignal()
    settings_imported = pyqtSignal()
    settings_exported = pyqtSignal()
    settings_reset = pyqtSignal()
    validation_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    success_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # 상태 초기화
        self._state = SettingsState()
        self._capabilities = SettingsCapabilities()

        # 서비스 및 이벤트 버스
        self.event_bus: TypedEventBus = get_event_bus()
        self.settings_manager = unified_config_manager
        self.ui_update_service: IUIUpdateService = get_service(IUIUpdateService)

        # 이벤트 연결
        self._connect_events()

    def _connect_events(self):
        """이벤트 연결 설정"""
        # 설정 관련 이벤트
        self.event_bus.subscribe(SettingsChangedEvent, self._on_settings_changed)
        self.event_bus.subscribe(SettingsSavedEvent, self._on_settings_saved)
        self.event_bus.subscribe(SettingsImportEvent, self._on_settings_imported)
        self.event_bus.subscribe(SettingsExportEvent, self._on_settings_exported)
        self.event_bus.subscribe(SettingsResetEvent, self._on_settings_reset)

        # UI 이벤트
        self.event_bus.subscribe(StatusBarUpdateEvent, self._on_status_bar_update)
        self.event_bus.subscribe(SuccessMessageEvent, self._on_success_message)

    # 상태 속성들
    @pyqtProperty(bool, notify=state_changed)
    def has_unsaved_changes(self) -> bool:
        return self._state.has_unsaved_changes

    @pyqtProperty(bool, notify=state_changed)
    def is_loading_settings(self) -> bool:
        return self._state.is_loading_settings

    @pyqtProperty(bool, notify=state_changed)
    def is_saving_settings(self) -> bool:
        return self._state.is_saving_settings

    @pyqtProperty(bool, notify=state_changed)
    def scan_settings_changed(self) -> bool:
        return self._state.scan_settings_changed

    @pyqtProperty(bool, notify=state_changed)
    def organize_settings_changed(self) -> bool:
        return self._state.organize_settings_changed

    @pyqtProperty(bool, notify=state_changed)
    def metadata_settings_changed(self) -> bool:
        return self._state.metadata_settings_changed

    @pyqtProperty(bool, notify=state_changed)
    def ui_settings_changed(self) -> bool:
        return self._state.ui_settings_changed

    @pyqtProperty(bool, notify=state_changed)
    def safety_settings_changed(self) -> bool:
        return self._state.safety_settings_changed

    @pyqtProperty(bool, notify=state_changed)
    def settings_valid(self) -> bool:
        return self._state.settings_valid

    @pyqtProperty(list, notify=state_changed)
    def validation_errors(self) -> list[str]:
        return self._state.validation_errors

    @pyqtProperty(str, notify=state_changed)
    def last_saved(self) -> str:
        return self._state.last_saved or ""

    @pyqtProperty(str, notify=state_changed)
    def last_loaded(self) -> str:
        return self._state.last_loaded or ""

    @pyqtProperty(str, notify=state_changed)
    def current_settings_file(self) -> str:
        return self._state.current_settings_file or ""

    @pyqtProperty(str, notify=state_changed)
    def backup_settings_file(self) -> str:
        return self._state.backup_settings_file or ""

    # UI 기능 속성들
    @pyqtProperty(bool, notify=capabilities_changed)
    def can_save_settings(self) -> bool:
        return self._capabilities.can_save_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_reset_settings(self) -> bool:
        return self._capabilities.can_reset_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_import_settings(self) -> bool:
        return self._capabilities.can_import_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_export_settings(self) -> bool:
        return self._capabilities.can_export_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_validate_settings(self) -> bool:
        return self._capabilities.can_validate_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_backup_settings(self) -> bool:
        return self._capabilities.can_backup_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_restore_settings(self) -> bool:
        return self._capabilities.can_restore_settings

    # 이벤트 핸들러들
    def _on_settings_changed(self, event: SettingsChangedEvent):
        """설정 변경 이벤트 처리"""
        self._state.has_unsaved_changes = True

        # 카테고리별 변경 상태 업데이트
        if event.category == "scan":
            self._state.scan_settings_changed = True
        elif event.category == "organize":
            self._state.organize_settings_changed = True
        elif event.category == "metadata":
            self._state.metadata_settings_changed = True
        elif event.category == "ui":
            self._state.ui_settings_changed = True
        elif event.category == "safety":
            self._state.safety_settings_changed = True

        self._update_capabilities()
        self.state_changed.emit()

    def _on_settings_saved(self, event: SettingsSavedEvent):
        """설정 저장 이벤트 처리"""
        self._state.has_unsaved_changes = False
        self._state.is_saving_settings = False
        self._state.last_saved = event.timestamp

        # 모든 변경 상태 초기화
        self._state.scan_settings_changed = False
        self._state.organize_settings_changed = False
        self._state.metadata_settings_changed = False
        self._state.ui_settings_changed = False
        self._state.safety_settings_changed = False

        self._update_capabilities()
        self.state_changed.emit()
        self.settings_saved.emit()

    def _on_settings_imported(self, event: SettingsImportEvent):
        """설정 가져오기 이벤트 처리"""
        self._state.is_loading_settings = False
        self._state.last_loaded = event.timestamp
        self._state.current_settings_file = event.file_path
        self._state.has_unsaved_changes = False

        # 모든 변경 상태 초기화
        self._state.scan_settings_changed = False
        self._state.organize_settings_changed = False
        self._state.metadata_settings_changed = False
        self._state.ui_settings_changed = False
        self._state.safety_settings_changed = False

        self._update_capabilities()
        self.state_changed.emit()
        self.settings_imported.emit()

    def _on_settings_exported(self, event: SettingsExportEvent):
        """설정 내보내기 이벤트 처리"""
        self._state.is_saving_settings = False
        self.settings_exported.emit()

    def _on_settings_reset(self, event: SettingsResetEvent):
        """설정 초기화 이벤트 처리"""
        self._state.has_unsaved_changes = False
        self._state.settings_valid = True
        self._state.validation_errors.clear()

        # 모든 변경 상태 초기화
        self._state.scan_settings_changed = False
        self._state.organize_settings_changed = False
        self._state.metadata_settings_changed = False
        self._state.ui_settings_changed = False
        self._state.safety_settings_changed = False

        self._update_capabilities()
        self.state_changed.emit()
        self.settings_reset.emit()

    def _on_status_bar_update(self, event: StatusBarUpdateEvent):
        """상태바 업데이트 이벤트 처리"""
        # 상태바 메시지는 View에서 직접 처리

    def _on_success_message(self, event: SuccessMessageEvent):
        """성공 메시지 이벤트 처리"""
        self.success_occurred.emit(event.message)

    def _update_capabilities(self):
        """UI 기능 상태 업데이트"""
        old_capabilities = self._capabilities

        if self._state.is_loading_settings:
            self._capabilities = SettingsCapabilities.loading()
        elif self._state.is_saving_settings:
            self._capabilities = SettingsCapabilities.saving()
        elif self._state.has_unsaved_changes:
            self._capabilities = SettingsCapabilities.has_unsaved_changes()
        elif not self._state.settings_valid:
            self._capabilities = SettingsCapabilities.invalid_settings()
        else:
            self._capabilities = SettingsCapabilities()

        if old_capabilities != self._capabilities:
            self.capabilities_changed.emit()

    # 공개 메서드들
    def load_settings(self, file_path: str = None):
        """설정 로드"""
        if not self.can_import_settings:
            self.logger.warning("설정을 로드할 수 없습니다")
            return

        try:
            self._state.is_loading_settings = True
            self._update_capabilities()
            self.state_changed.emit()

            if file_path:
                self.settings_manager.load_settings(file_path)
            else:
                self.settings_manager.load_settings()

        except Exception as e:
            self.logger.error(f"설정 로드 실패: {e}")
            self._state.is_loading_settings = False
            self._update_capabilities()
            self.state_changed.emit()
            self.error_occurred.emit(f"설정 로드 실패: {e}")

    def save_settings(self, file_path: str = None):
        """설정 저장"""
        if not self.can_save_settings:
            self.logger.warning("설정을 저장할 수 없습니다")
            return

        try:
            self._state.is_saving_settings = True
            self._update_capabilities()
            self.state_changed.emit()

            if file_path:
                self.settings_manager.save_settings(file_path)
            else:
                self.settings_manager.save_settings()

        except Exception as e:
            self.logger.error(f"설정 저장 실패: {e}")
            self._state.is_saving_settings = False
            self._update_capabilities()
            self.state_changed.emit()
            self.error_occurred.emit(f"설정 저장 실패: {e}")

    def import_settings(self, file_path: str):
        """설정 가져오기"""
        if not self.can_import_settings:
            self.logger.warning("설정을 가져올 수 없습니다")
            return

        try:
            self._state.is_loading_settings = True
            self._update_capabilities()
            self.state_changed.emit()

            self.settings_manager.import_settings(file_path)

        except Exception as e:
            self.logger.error(f"설정 가져오기 실패: {e}")
            self._state.is_loading_settings = False
            self._update_capabilities()
            self.state_changed.emit()
            self.error_occurred.emit(f"설정 가져오기 실패: {e}")

    def export_settings(self, file_path: str):
        """설정 내보내기"""
        if not self.can_export_settings:
            self.logger.warning("설정을 내보낼 수 없습니다")
            return

        try:
            self._state.is_saving_settings = True
            self._update_capabilities()
            self.state_changed.emit()

            self.settings_manager.export_settings(file_path)

        except Exception as e:
            self.logger.error(f"설정 내보내기 실패: {e}")
            self._state.is_saving_settings = False
            self._update_capabilities()
            self.state_changed.emit()
            self.error_occurred.emit(f"설정 내보내기 실패: {e}")

    def reset_settings(self):
        """설정 초기화"""
        if not self.can_reset_settings:
            self.logger.warning("설정을 초기화할 수 없습니다")
            return

        try:
            self.settings_manager.reset_settings()
        except Exception as e:
            self.logger.error(f"설정 초기화 실패: {e}")
            self.error_occurred.emit(f"설정 초기화 실패: {e}")

    def validate_settings(self):
        """설정 유효성 검사"""
        if not self.can_validate_settings:
            self.logger.warning("설정 유효성을 검사할 수 없습니다")
            return

        try:
            validation_result = self.settings_manager.validate_settings()
            self._state.settings_valid = validation_result.is_valid
            self._state.validation_errors = validation_result.errors

            self.state_changed.emit()
            self.validation_changed.emit(validation_result.is_valid)

            if not validation_result.is_valid:
                self.error_occurred.emit("설정에 오류가 있습니다")
            else:
                self.success_occurred.emit("설정이 유효합니다")

        except Exception as e:
            self.logger.error(f"설정 유효성 검사 실패: {e}")
            self.error_occurred.emit(f"설정 유효성 검사 실패: {e}")

    def backup_settings(self):
        """설정 백업"""
        if not self.can_backup_settings:
            self.logger.warning("설정을 백업할 수 없습니다")
            return

        try:
            backup_path = self.settings_manager.backup_settings()
            self._state.backup_settings_file = backup_path
            self.state_changed.emit()
            self.success_occurred.emit(f"설정이 백업되었습니다: {backup_path}")

        except Exception as e:
            self.logger.error(f"설정 백업 실패: {e}")
            self.error_occurred.emit(f"설정 백업 실패: {e}")

    def restore_settings(self, backup_path: str):
        """설정 복원"""
        if not self.can_restore_settings:
            self.logger.warning("설정을 복원할 수 없습니다")
            return

        try:
            self.settings_manager.restore_settings(backup_path)
            self.success_occurred.emit("설정이 복원되었습니다")

        except Exception as e:
            self.logger.error(f"설정 복원 실패: {e}")
            self.error_occurred.emit(f"설정 복원 실패: {e}")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """설정 값 가져오기"""
        try:
            # unified_config_manager 구조에 맞게 설정 값 가져오기
            if hasattr(self.settings_manager, "config"):
                # unified_config_manager 사용
                config = self.settings_manager.config
                if key == "destination_root":
                    return getattr(config.application, "destination_root", default)
                if key == "theme":
                    return getattr(config.user_preferences.theme_preferences, "theme", default)
                if key == "language":
                    return getattr(config.user_preferences, "language", default)
                if key == "font_family":
                    return getattr(config.user_preferences, "font_family", default)
                if key == "font_size":
                    return getattr(config.user_preferences, "font_size", default)
                if key == "ui_style":
                    return getattr(config.user_preferences, "ui_style", default)
                return default
        except Exception as e:
            self.logger.error(f"설정 값 가져오기 실패: {e}")
            return default

    def set_setting(self, key: str, value: Any):
        """설정 값 설정"""
        try:
            self.settings_manager.set_setting(key, value)
        except Exception as e:
            self.logger.error(f"설정 값 설정 실패: {e}")
            self.error_occurred.emit(f"설정 값 설정 실패: {e}")

    def get_all_settings(self) -> dict[str, Any]:
        """모든 설정 가져오기"""
        try:
            return self.settings_manager.get_all_settings()
        except Exception as e:
            self.logger.error(f"모든 설정 가져오기 실패: {e}")
            return {}
