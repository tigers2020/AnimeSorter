"""
UI 업데이트 관련 이벤트 정의
"""
from dataclasses import dataclass, field
from typing import Optional

from .events import BaseEvent


@dataclass
class StatusBarUpdateEvent(BaseEvent):
    """상태바 업데이트 이벤트"""

    message: str = ""
    progress: Optional[int] = None  # 0-100
    clear_after: Optional[float] = None  # 초 후 자동 클리어


@dataclass
class ProgressUpdateEvent(BaseEvent):
    """진행률 업데이트 이벤트"""

    current: int = 0
    total: int = 100
    message: Optional[str] = None


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
    cpu_percent: Optional[float] = None


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
    details: Optional[str] = None
    error_type: str = "error"  # error, warning, info


@dataclass
class SuccessMessageEvent(BaseEvent):
    """성공 메시지 이벤트"""

    message: str = ""
    details: Optional[str] = None
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
    subtitle: Optional[str] = None


@dataclass
class MenuStateUpdateEvent(BaseEvent):
    """메뉴 상태 업데이트 이벤트"""

    action_name: str = ""
    enabled: bool = True
    checked: Optional[bool] = None
    text: Optional[str] = None


@dataclass
class ThemeUpdateEvent(BaseEvent):
    """테마 업데이트 이벤트"""

    theme_name: str = "default"
    dark_mode: bool = False
