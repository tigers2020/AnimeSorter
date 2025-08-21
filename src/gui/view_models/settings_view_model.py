"""
SettingsViewModel - 애플리케이션 설정 관리에 특화된 ViewModel

Phase 2 MVVM 아키텍처의 일부로, 애플리케이션 설정 및 구성 관리 기능을 담당합니다.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from app import (
    ISettingsManager,
    IUIUpdateService,
    SettingsChangedEvent,
    SettingsExportEvent,
    SettingsImportEvent,
    # 서비스
    SettingsResetEvent,
    SettingsSavedEvent,
    # UI 이벤트
    StatusBarUpdateEvent,
    SuccessMessageEvent,
    # 인프라
    TypedEventBus,
    get_event_bus,
    get_service,
)


@dataclass
class SettingsState:
    """설정 상태 정보"""

    # 설정 변경 상태
    has_unsaved_changes: bool = False
    is_loading_settings: bool = False
    is_saving_settings: bool = False

    # 설정 카테고리별 변경 상태
    scan_settings_changed: bool = False
    organize_settings_changed: bool = False
    metadata_settings_changed: bool = False
    ui_settings_changed: bool = False
    safety_settings_changed: bool = False

    # 설정 유효성
    settings_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)

    # 마지막 저장/로드 시간
    last_saved: str | None = None
    last_loaded: str | None = None

    # 설정 파일 경로
    current_settings_file: str | None = None
    backup_settings_file: str | None = None


@dataclass
class SettingsCapabilities:
    """설정 관련 UI 기능들"""

    can_save_settings: bool = True
    can_reset_settings: bool = True
    can_import_settings: bool = True
    can_export_settings: bool = True
    can_validate_settings: bool = True
    can_backup_settings: bool = True
    can_restore_settings: bool = True

    @classmethod
    def loading(cls) -> "SettingsCapabilities":
        """설정 로딩 중일 때의 기능 상태"""
        return cls(
            can_save_settings=False,
            can_reset_settings=False,
            can_import_settings=False,
            can_export_settings=False,
            can_validate_settings=False,
            can_backup_settings=False,
            can_restore_settings=False,
        )

    @classmethod
    def saving(cls) -> "SettingsCapabilities":
        """설정 저장 중일 때의 기능 상태"""
        return cls(
            can_save_settings=False,
            can_reset_settings=False,
            can_import_settings=False,
            can_export_settings=False,
            can_validate_settings=False,
            can_backup_settings=False,
            can_restore_settings=False,
        )

    @classmethod
    def has_unsaved_changes(cls) -> "SettingsCapabilities":
        """저장되지 않은 변경사항이 있을 때의 기능"""
        return cls(
            can_save_settings=True,
            can_reset_settings=True,
            can_import_settings=False,
            can_export_settings=True,
            can_validate_settings=True,
            can_backup_settings=True,
            can_restore_settings=True,
        )


class SettingsViewModel(QObject):
    """애플리케이션 설정 관리 전용 ViewModel"""

    # 시그널 정의
    state_changed = pyqtSignal()
    capabilities_changed = pyqtSignal()
    settings_changed = pyqtSignal(str)  # category
    settings_validated = pyqtSignal(bool, list)  # is_valid, errors
    settings_saved = pyqtSignal()
    settings_loaded = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # 로깅 설정
        self.logger = logging.getLogger(__name__)

        # 상태 초기화
        self._settings_state = SettingsState()
        self._settings_capabilities = SettingsCapabilities()

        # 서비스 연결
        self._event_bus: TypedEventBus | None = None
        self._settings_manager: ISettingsManager | None = None
        self._ui_update_service: IUIUpdateService | None = None

        # 설정 값들 (실제 설정과 동기화)
        self._scan_settings: dict[str, Any] = {}
        self._organize_settings: dict[str, Any] = {}
        self._metadata_settings: dict[str, Any] = {}
        self._ui_settings: dict[str, Any] = {}
        self._safety_settings: dict[str, Any] = {}

        # 초기화
        self._setup_services()
        self._setup_event_subscriptions()
        self._load_current_settings()

        self.logger.info("SettingsViewModel 초기화 완료")

    def _setup_services(self):
        """필요한 서비스들을 설정"""
        try:
            self._event_bus = get_event_bus()
            self._settings_manager = get_service(ISettingsManager)
            self._ui_update_service = get_service(IUIUpdateService)

            self.logger.info("SettingsViewModel 서비스 연결 완료")
        except Exception as e:
            self.logger.error(f"SettingsViewModel 서비스 연결 실패: {e}")

    def _setup_event_subscriptions(self):
        """이벤트 구독 설정"""
        if not self._event_bus:
            return

        try:
            # 설정 관련 이벤트 구독
            self._event_bus.subscribe(
                SettingsChangedEvent, self._on_settings_changed, weak_ref=False
            )
            self._event_bus.subscribe(SettingsSavedEvent, self._on_settings_saved, weak_ref=False)
            self._event_bus.subscribe(SettingsResetEvent, self._on_settings_reset, weak_ref=False)
            self._event_bus.subscribe(SettingsImportEvent, self._on_settings_import, weak_ref=False)
            self._event_bus.subscribe(SettingsExportEvent, self._on_settings_export, weak_ref=False)

            self.logger.info("SettingsViewModel 이벤트 구독 설정 완료")
        except Exception as e:
            self.logger.error(f"SettingsViewModel 이벤트 구독 설정 실패: {e}")

    def _load_current_settings(self):
        """현재 설정 로드"""
        try:
            if not self._settings_manager:
                return

            # 각 카테고리별 설정 로드
            self._scan_settings = self._settings_manager.get_scan_settings()
            self._organize_settings = self._settings_manager.get_organize_settings()
            self._metadata_settings = self._settings_manager.get_metadata_settings()
            self._ui_settings = self._settings_manager.get_ui_settings()
            self._safety_settings = self._settings_manager.get_safety_settings()

            self.logger.info("현재 설정 로드 완료")

        except Exception as e:
            self.logger.error(f"현재 설정 로드 중 오류 발생: {e}")

    # 설정 상태 프로퍼티들
    @pyqtProperty(bool, notify=state_changed)
    def has_unsaved_changes(self) -> bool:
        """저장되지 않은 변경사항이 있는지 여부"""
        return self._settings_state.has_unsaved_changes

    @pyqtProperty(bool, notify=state_changed)
    def is_loading_settings(self) -> bool:
        """설정 로딩 중인지 여부"""
        return self._settings_state.is_loading_settings

    @pyqtProperty(bool, notify=state_changed)
    def is_saving_settings(self) -> bool:
        """설정 저장 중인지 여부"""
        return self._settings_state.is_saving_settings

    @pyqtProperty(bool, notify=state_changed)
    def settings_valid(self) -> bool:
        """설정이 유효한지 여부"""
        return self._settings_state.settings_valid

    @pyqtProperty(str, notify=state_changed)
    def last_saved(self) -> str:
        """마지막 저장 시간"""
        return self._settings_state.last_saved or ""

    @pyqtProperty(str, notify=state_changed)
    def last_loaded(self) -> str:
        """마지막 로드 시간"""
        return self._settings_state.last_loaded or ""

    # 설정 기능 프로퍼티들
    @pyqtProperty(bool, notify=capabilities_changed)
    def can_save_settings(self) -> bool:
        """설정 저장 가능 여부"""
        return self._settings_capabilities.can_save_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_reset_settings(self) -> bool:
        """설정 초기화 가능 여부"""
        return self._settings_capabilities.can_reset_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_import_settings(self) -> bool:
        """설정 가져오기 가능 여부"""
        return self._settings_capabilities.can_import_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_export_settings(self) -> bool:
        """설정 내보내기 가능 여부"""
        return self._settings_capabilities.can_export_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_validate_settings(self) -> bool:
        """설정 검증 가능 여부"""
        return self._settings_capabilities.can_validate_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_backup_settings(self) -> bool:
        """설정 백업 가능 여부"""
        return self._settings_capabilities.can_backup_settings

    @pyqtProperty(bool, notify=capabilities_changed)
    def can_restore_settings(self) -> bool:
        """설정 복원 가능 여부"""
        return self._settings_capabilities.can_restore_settings

    # 스캔 설정 프로퍼티들
    @pyqtProperty(bool, notify=settings_changed)
    def scan_include_subdirectories(self) -> bool:
        """스캔 시 하위 디렉토리 포함 여부"""
        return self._scan_settings.get("include_subdirectories", True)

    @scan_include_subdirectories.setter
    def scan_include_subdirectories(self, value: bool):
        """스캔 시 하위 디렉토리 포함 여부 설정"""
        if self._scan_settings.get("include_subdirectories") != value:
            self._scan_settings["include_subdirectories"] = value
            self._mark_settings_changed("scan")

    @pyqtProperty(bool, notify=settings_changed)
    def scan_hidden_files(self) -> bool:
        """스캔 시 숨김 파일 포함 여부"""
        return self._scan_settings.get("scan_hidden_files", False)

    @scan_hidden_files.setter
    def scan_hidden_files(self, value: bool):
        """스캔 시 숨김 파일 포함 여부 설정"""
        if self._scan_settings.get("scan_hidden_files") != value:
            self._scan_settings["scan_hidden_files"] = value
            self._mark_settings_changed("scan")

    @pyqtProperty(int, notify=settings_changed)
    def scan_max_file_size_mb(self) -> int:
        """스캔 시 최대 파일 크기 (MB)"""
        return self._scan_settings.get("max_file_size_mb", 10000)

    @scan_max_file_size_mb.setter
    def scan_max_file_size_mb(self, value: int):
        """스캔 시 최대 파일 크기 설정 (MB)"""
        if self._scan_settings.get("max_file_size_mb") != value:
            self._scan_settings["max_file_size_mb"] = value
            self._mark_settings_changed("scan")

    # 정리 설정 프로퍼티들
    @pyqtProperty(str, notify=settings_changed)
    def organize_default_mode(self) -> str:
        """기본 정리 모드"""
        return self._organize_settings.get("default_mode", "simulation")

    @organize_default_mode.setter
    def organize_default_mode(self, value: str):
        """기본 정리 모드 설정"""
        if self._organize_settings.get("default_mode") != value:
            self._organize_settings["default_mode"] = value
            self._mark_settings_changed("organize")

    @pyqtProperty(bool, notify=settings_changed)
    def organize_create_directories(self) -> bool:
        """정리 시 디렉토리 생성 여부"""
        return self._organize_settings.get("create_directories", True)

    @organize_create_directories.setter
    def organize_create_directories(self, value: bool):
        """정리 시 디렉토리 생성 여부 설정"""
        if self._organize_settings.get("create_directories") != value:
            self._organize_settings["create_directories"] = value
            self._mark_settings_changed("organize")

    @pyqtProperty(bool, notify=settings_changed)
    def organize_backup_before_organize(self) -> bool:
        """정리 전 백업 여부"""
        return self._organize_settings.get("backup_before_organize", True)

    @organize_backup_before_organize.setter
    def organize_backup_before_organize(self, value: bool):
        """정리 전 백업 여부 설정"""
        if self._organize_settings.get("backup_before_organize") != value:
            self._organize_settings["backup_before_organize"] = value
            self._mark_settings_changed("organize")

    # 메타데이터 설정 프로퍼티들
    @pyqtProperty(bool, notify=settings_changed)
    def metadata_auto_sync(self) -> bool:
        """메타데이터 자동 동기화 여부"""
        return self._metadata_settings.get("auto_sync", False)

    @metadata_auto_sync.setter
    def metadata_auto_sync(self, value: bool):
        """메타데이터 자동 동기화 여부 설정"""
        if self._metadata_settings.get("auto_sync") != value:
            self._metadata_settings["auto_sync"] = value
            self._mark_settings_changed("metadata")

    @pyqtProperty(bool, notify=settings_changed)
    def metadata_auto_tmdb_search(self) -> bool:
        """메타데이터 자동 TMDB 검색 여부"""
        return self._metadata_settings.get("auto_tmdb_search", False)

    @metadata_auto_tmdb_search.setter
    def metadata_auto_tmdb_search(self, value: bool):
        """메타데이터 자동 TMDB 검색 여부 설정"""
        if self._metadata_settings.get("auto_tmdb_search") != value:
            self._metadata_settings["auto_tmdb_search"] = value
            self._mark_settings_changed("metadata")

    @pyqtProperty(int, notify=settings_changed)
    def metadata_quality_threshold(self) -> int:
        """메타데이터 품질 임계값 (0-100)"""
        return self._metadata_settings.get("quality_threshold", 70)

    @metadata_quality_threshold.setter
    def metadata_quality_threshold(self, value: int):
        """메타데이터 품질 임계값 설정 (0-100)"""
        if self._metadata_settings.get("quality_threshold") != value:
            self._metadata_settings["quality_threshold"] = value
            self._mark_settings_changed("metadata")

    # UI 설정 프로퍼티들
    @pyqtProperty(bool, notify=settings_changed)
    def ui_show_toolbar(self) -> bool:
        """툴바 표시 여부"""
        return self._ui_settings.get("show_toolbar", True)

    @ui_show_toolbar.setter
    def ui_show_toolbar(self, value: bool):
        """툴바 표시 여부 설정"""
        if self._ui_settings.get("show_toolbar") != value:
            self._ui_settings["show_toolbar"] = value
            self._mark_settings_changed("ui")

    @pyqtProperty(bool, notify=settings_changed)
    def ui_show_statusbar(self) -> bool:
        """상태바 표시 여부"""
        return self._ui_settings.get("show_statusbar", True)

    @ui_show_statusbar.setter
    def ui_show_statusbar(self, value: bool):
        """상태바 표시 여부 설정"""
        if self._ui_settings.get("show_statusbar") != value:
            self._ui_settings["show_statusbar"] = value
            self._mark_settings_changed("ui")

    @pyqtProperty(str, notify=settings_changed)
    def ui_theme(self) -> str:
        """UI 테마"""
        return self._ui_settings.get("theme", "default")

    @ui_theme.setter
    def ui_theme(self, value: str):
        """UI 테마 설정"""
        if self._ui_settings.get("theme") != value:
            self._ui_settings["theme"] = value
            self._mark_settings_changed("ui")

    # 안전 설정 프로퍼티들
    @pyqtProperty(str, notify=settings_changed)
    def safety_default_mode(self) -> str:
        """기본 안전 모드"""
        return self._safety_settings.get("default_mode", "normal")

    @safety_default_mode.setter
    def safety_default_mode(self, value: str):
        """기본 안전 모드 설정"""
        if self._safety_settings.get("default_mode") != value:
            self._safety_settings["default_mode"] = value
            self._mark_settings_changed("safety")

    @pyqtProperty(bool, notify=settings_changed)
    def safety_auto_backup(self) -> bool:
        """자동 백업 여부"""
        return self._safety_settings.get("auto_backup", True)

    @safety_auto_backup.setter
    def safety_auto_backup(self, value: bool):
        """자동 백업 여부 설정"""
        if self._safety_settings.get("auto_backup") != value:
            self._safety_settings["auto_backup"] = value
            self._mark_settings_changed("safety")

    @pyqtProperty(bool, notify=settings_changed)
    def safety_confirm_dangerous_operations(self) -> bool:
        """위험한 작업 확인 여부"""
        return self._safety_settings.get("confirm_dangerous_operations", True)

    @safety_confirm_dangerous_operations.setter
    def safety_confirm_dangerous_operations(self, value: bool):
        """위험한 작업 확인 여부 설정"""
        if self._safety_settings.get("confirm_dangerous_operations") != value:
            self._safety_settings["confirm_dangerous_operations"] = value
            self._mark_settings_changed("safety")

    # 공개 메서드들
    def save_settings(self) -> bool:
        """설정 저장"""
        try:
            if not self._settings_manager:
                self.logger.error("SettingsManager가 연결되지 않았습니다")
                return False

            if not self._settings_state.has_unsaved_changes:
                self.logger.info("저장할 변경사항이 없습니다")
                return True

            self._settings_state.is_saving_settings = True
            self._update_capabilities(SettingsCapabilities.saving())
            self.state_changed.emit()

            # 각 카테고리별 설정 저장
            success = True
            success &= self._settings_manager.update_scan_settings(self._scan_settings)
            success &= self._settings_manager.update_organize_settings(self._organize_settings)
            success &= self._settings_manager.update_metadata_settings(self._metadata_settings)
            success &= self._settings_manager.update_ui_settings(self._ui_settings)
            success &= self._settings_manager.update_safety_settings(self._safety_settings)

            if success:
                self._settings_state.has_unsaved_changes = False
                self._settings_state.last_saved = self._get_current_timestamp()
                self.logger.info("설정 저장 완료")

                # 설정 저장 이벤트 발행
                if self._event_bus:
                    self._event_bus.publish(SettingsSavedEvent())

                self.settings_saved.emit()
            else:
                self.logger.error("설정 저장 실패")

            self._settings_state.is_saving_settings = False
            self._update_capabilities(SettingsCapabilities())
            self.state_changed.emit()

            return success

        except Exception as e:
            self.logger.error(f"설정 저장 중 오류 발생: {e}")
            self._settings_state.is_saving_settings = False
            self._update_capabilities(SettingsCapabilities())
            self.state_changed.emit()
            return False

    def reset_settings(self, category: str | None = None) -> bool:
        """설정 초기화"""
        try:
            if not self._settings_manager:
                return False

            if category:
                # 특정 카테고리만 초기화
                if category == "scan":
                    self._scan_settings = self._settings_manager.get_default_scan_settings()
                elif category == "organize":
                    self._organize_settings = self._settings_manager.get_default_organize_settings()
                elif category == "metadata":
                    self._metadata_settings = self._settings_manager.get_default_metadata_settings()
                elif category == "ui":
                    self._ui_settings = self._settings_manager.get_default_ui_settings()
                elif category == "safety":
                    self._safety_settings = self._settings_manager.get_default_safety_settings()

                self._mark_settings_changed(category)
                self.logger.info(f"{category} 설정 초기화 완료")
            else:
                # 모든 설정 초기화
                self._scan_settings = self._settings_manager.get_default_scan_settings()
                self._organize_settings = self._settings_manager.get_default_organize_settings()
                self._metadata_settings = self._settings_manager.get_default_metadata_settings()
                self._ui_settings = self._settings_manager.get_default_ui_settings()
                self._safety_settings = self._settings_manager.get_default_safety_settings()

                self._mark_all_settings_changed()
                self.logger.info("모든 설정 초기화 완료")

            return True

        except Exception as e:
            self.logger.error(f"설정 초기화 중 오류 발생: {e}")
            return False

    def import_settings(self, file_path: str) -> bool:
        """설정 가져오기"""
        try:
            if not self._settings_manager:
                return False

            success = self._settings_manager.import_settings(file_path)

            if success:
                # 가져온 설정으로 현재 설정 업데이트
                self._load_current_settings()
                self._mark_all_settings_changed()

                self.logger.info(f"설정 가져오기 완료: {file_path}")
                return True
            self.logger.error(f"설정 가져오기 실패: {file_path}")
            return False

        except Exception as e:
            self.logger.error(f"설정 가져오기 중 오류 발생: {e}")
            return False

    def export_settings(self, file_path: str) -> bool:
        """설정 내보내기"""
        try:
            if not self._settings_manager:
                return False

            success = self._settings_manager.export_settings(file_path)

            if success:
                self.logger.info(f"설정 내보내기 완료: {file_path}")
                return True
            self.logger.error(f"설정 내보내기 실패: {file_path}")
            return False

        except Exception as e:
            self.logger.error(f"설정 내보내기 중 오류 발생: {e}")
            return False

    def validate_settings(self) -> bool:
        """설정 검증"""
        try:
            if not self._settings_manager:
                return False

            validation_result = self._settings_manager.validate_settings()

            if validation_result:
                is_valid = validation_result.get("is_valid", False)
                errors = validation_result.get("errors", [])

                self._settings_state.settings_valid = is_valid
                self._settings_state.validation_errors = errors

                # 설정 검증 시그널 발생
                self.settings_validated.emit(is_valid, errors)

                if is_valid:
                    self.logger.info("설정 검증 완료: 유효함")
                else:
                    self.logger.warning(f"설정 검증 완료: {len(errors)}개 오류 발견")

                return is_valid
            self.logger.error("설정 검증 실패")
            return False

        except Exception as e:
            self.logger.error(f"설정 검증 중 오류 발생: {e}")
            return False

    def backup_settings(self) -> bool:
        """설정 백업"""
        try:
            if not self._settings_manager:
                return False

            success = self._settings_manager.backup_settings()

            if success:
                self.logger.info("설정 백업 완료")
                return True
            self.logger.error("설정 백업 실패")
            return False

        except Exception as e:
            self.logger.error(f"설정 백업 중 오류 발생: {e}")
            return False

    def restore_settings(self, backup_file: str) -> bool:
        """설정 복원"""
        try:
            if not self._settings_manager:
                return False

            success = self._settings_manager.restore_settings(backup_file)

            if success:
                # 복원된 설정으로 현재 설정 업데이트
                self._load_current_settings()
                self._mark_all_settings_changed()

                self.logger.info(f"설정 복원 완료: {backup_file}")
                return True
            self.logger.error(f"설정 복원 실패: {backup_file}")
            return False

        except Exception as e:
            self.logger.error(f"설정 복원 중 오류 발생: {e}")
            return False

    # 이벤트 핸들러들
    def _on_settings_changed(self, event: SettingsChangedEvent):
        """설정 변경 이벤트 처리"""
        try:
            # 설정 변경 상태 업데이트
            self._mark_settings_changed(event.category)

            # UI 업데이트 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(
                    StatusBarUpdateEvent(message=f"{event.category} 설정이 변경되었습니다")
                )

        except Exception as e:
            self.logger.error(f"설정 변경 이벤트 처리 중 오류 발생: {e}")

    def _on_settings_saved(self, event: SettingsSavedEvent):
        """설정 저장 이벤트 처리"""
        try:
            # 설정 저장 상태 업데이트
            self._settings_state.has_unsaved_changes = False
            self._settings_state.last_saved = self._get_current_timestamp()

            # UI 업데이트 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(SuccessMessageEvent(message="설정이 저장되었습니다"))

            # 상태 변경 시그널 발생
            self.state_changed.emit()

        except Exception as e:
            self.logger.error(f"설정 저장 이벤트 처리 중 오류 발생: {e}")

    def _on_settings_reset(self, event: SettingsResetEvent):
        """설정 초기화 이벤트 처리"""
        try:
            # 설정 초기화 상태 업데이트
            self._mark_all_settings_changed()

            # UI 업데이트 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(StatusBarUpdateEvent(message="설정이 초기화되었습니다"))

        except Exception as e:
            self.logger.error(f"설정 초기화 이벤트 처리 중 오류 발생: {e}")

    def _on_settings_import(self, event: SettingsImportEvent):
        """설정 가져오기 이벤트 처리"""
        try:
            # 설정 가져오기 상태 업데이트
            self._mark_all_settings_changed()

            # UI 업데이트 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(SuccessMessageEvent(message="설정을 가져왔습니다"))

        except Exception as e:
            self.logger.error(f"설정 가져오기 이벤트 처리 중 오류 발생: {e}")

    def _on_settings_export(self, event: SettingsExportEvent):
        """설정 내보내기 이벤트 처리"""
        try:
            # UI 업데이트 이벤트 발행
            if self._event_bus:
                self._event_bus.publish(SuccessMessageEvent(message="설정을 내보냈습니다"))

        except Exception as e:
            self.logger.error(f"설정 내보내기 이벤트 처리 중 오류 발생: {e}")

    # 내부 헬퍼 메서드들
    def _mark_settings_changed(self, category: str):
        """특정 카테고리 설정 변경 표시"""
        if category == "scan":
            self._settings_state.scan_settings_changed = True
        elif category == "organize":
            self._settings_state.organize_settings_changed = True
        elif category == "metadata":
            self._settings_state.metadata_settings_changed = True
        elif category == "ui":
            self._settings_state.ui_settings_changed = True
        elif category == "safety":
            self._settings_state.safety_settings_changed = True

        self._settings_state.has_unsaved_changes = True
        self._update_capabilities(SettingsCapabilities.has_unsaved_changes())

        # 설정 변경 시그널 발생
        self.settings_changed.emit(category)
        self.state_changed.emit()

    def _mark_all_settings_changed(self):
        """모든 설정 변경 표시"""
        self._settings_state.scan_settings_changed = True
        self._settings_state.organize_settings_changed = True
        self._settings_state.metadata_settings_changed = True
        self._settings_state.ui_settings_changed = True
        self._settings_state.safety_settings_changed = True

        self._settings_state.has_unsaved_changes = True
        self._update_capabilities(SettingsCapabilities.has_unsaved_changes())

        # 상태 변경 시그널 발생
        self.state_changed.emit()

    def _update_capabilities(self, new_capabilities: SettingsCapabilities):
        """UI 기능 상태 업데이트"""
        if self._settings_capabilities != new_capabilities:
            self._settings_capabilities = new_capabilities
            self.capabilities_changed.emit()

    def _get_current_timestamp(self) -> str:
        """현재 타임스탬프 문자열 반환"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_settings_summary(self) -> dict[str, Any]:
        """설정 요약 정보 반환"""
        return {
            "has_unsaved_changes": self._settings_state.has_unsaved_changes,
            "is_loading_settings": self._settings_state.is_loading_settings,
            "is_saving_settings": self._settings_state.is_saving_settings,
            "scan_settings_changed": self._settings_state.scan_settings_changed,
            "organize_settings_changed": self._settings_state.organize_settings_changed,
            "metadata_settings_changed": self._settings_state.metadata_settings_changed,
            "ui_settings_changed": self._settings_state.ui_settings_changed,
            "safety_settings_changed": self._settings_state.safety_settings_changed,
            "settings_valid": self._settings_state.settings_valid,
            "validation_errors": self._settings_state.validation_errors,
            "last_saved": self._settings_state.last_saved,
            "last_loaded": self._settings_state.last_loaded,
            "current_settings_file": self._settings_state.current_settings_file,
            "backup_settings_file": self._settings_state.backup_settings_file,
        }
