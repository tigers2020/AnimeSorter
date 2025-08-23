"""
설정 상태 및 기능 관리 - Phase 3.3 뷰모델 분할
Settings ViewModel의 상태 관리 부분을 분리합니다.
"""

from dataclasses import dataclass, field


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
        """저장되지 않은 변경사항이 있을 때의 기능 상태"""
        return cls(
            can_save_settings=True,
            can_reset_settings=True,
            can_import_settings=False,
            can_export_settings=True,
            can_validate_settings=True,
            can_backup_settings=True,
            can_restore_settings=True,
        )

    @classmethod
    def invalid_settings(cls) -> "SettingsCapabilities":
        """설정이 유효하지 않을 때의 기능 상태"""
        return cls(
            can_save_settings=False,
            can_reset_settings=True,
            can_import_settings=True,
            can_export_settings=True,
            can_validate_settings=True,
            can_backup_settings=True,
            can_restore_settings=True,
        )
