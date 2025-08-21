"""
UI 업데이트 관련 이벤트 정의
"""

from dataclasses import dataclass, field

from .events import BaseEvent


@dataclass
class StatusBarUpdateEvent(BaseEvent):
    """상태바 업데이트 이벤트"""

    message: str = ""
    progress: int | None = None  # 0-100
    clear_after: float | None = None  # 초 후 자동 클리어


@dataclass
class ProgressUpdateEvent(BaseEvent):
    """진행률 업데이트 이벤트"""

    current: int = 0
    total: int = 100
    message: str | None = None


@dataclass
class FileCountUpdateEvent(BaseEvent):
    """파일 수 업데이트 이벤트"""

    count: int = 0
    processed: int = 0
    failed: int = 0


@dataclass
class MemoryUsageUpdateEvent(BaseEvent):
    """메모리 사용량 업데이트 이벤트"""

    memory_mb: float = 0.0
    cpu_percent: float | None = None


@dataclass
class UIStateUpdateEvent(BaseEvent):
    """UI 상태 업데이트 이벤트"""

    has_data: bool = False
    is_processing: bool = False
    has_selection: bool = False
    has_tmdb_matches: bool = False
    can_organize: bool = False


@dataclass
class ErrorMessageEvent(BaseEvent):
    """오류 메시지 이벤트"""

    message: str = ""
    details: str | None = None
    error_type: str = "error"  # error, warning, info


@dataclass
class SuccessMessageEvent(BaseEvent):
    """성공 메시지 이벤트"""

    message: str = ""
    details: str | None = None
    auto_clear: bool = True


@dataclass
class TableDataUpdateEvent(BaseEvent):
    """테이블 데이터 업데이트 이벤트"""

    table_name: str = ""  # "file_list", "detail_list" 등
    data: list = field(default_factory=list)
    selection_changed: bool = False


@dataclass
class WindowTitleUpdateEvent(BaseEvent):
    """윈도우 타이틀 업데이트 이벤트"""

    title: str = ""
    subtitle: str | None = None


@dataclass
class MenuStateUpdateEvent(BaseEvent):
    """메뉴 상태 업데이트 이벤트"""

    action_name: str = ""
    enabled: bool = True
    checked: bool | None = None
    text: str | None = None


@dataclass
class ThemeUpdateEvent(BaseEvent):
    """테마 업데이트 이벤트"""

    theme_name: str = "default"
    dark_mode: bool = False


@dataclass
class SettingsChangedEvent(BaseEvent):
    """설정 변경 이벤트"""

    setting_name: str = ""
    old_value: str | None = None
    new_value: str | None = None
    category: str = "general"  # general, ui, file_operations, tmdb 등


@dataclass
class SettingsSavedEvent(BaseEvent):
    """설정 저장 완료 이벤트"""

    settings_file_path: str = ""
    total_settings_saved: int = 0
    save_duration_seconds: float = 0.0
    backup_created: bool = False


@dataclass
class SettingsResetEvent(BaseEvent):
    """설정 초기화 완료 이벤트"""

    reset_to_defaults: bool = True
    backup_created: bool = False
    reset_duration_seconds: float = 0.0


@dataclass
class SettingsImportEvent(BaseEvent):
    """설정 가져오기 완료 이벤트"""

    import_file_path: str = ""
    imported_settings_count: int = 0
    import_duration_seconds: float = 0.0
    backup_created: bool = False


@dataclass
class SettingsExportEvent(BaseEvent):
    """설정 내보내기 완료 이벤트"""

    export_file_path: str = ""
    exported_settings_count: int = 0
    export_duration_seconds: float = 0.0
    include_sensitive_data: bool = False
