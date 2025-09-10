"""
Undo/Redo 시스템 이벤트

Undo/Redo 작업과 관련된 모든 이벤트 정의
"""

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from typing import Any

from src.app.events import BaseEvent


@dataclass
class UndoExecutedEvent(BaseEvent):
    """취소 실행 이벤트"""

    command_text: str = ""
    command_type: str = ""
    success: bool = True
    execution_time_ms: float = 0.0
    error_message: str | None = None
    affected_files: list[str] = field(default_factory=list)
    stack_count: int = 0
    current_index: int = 0
    can_undo: bool = False
    can_redo: bool = True


@dataclass
class RedoExecutedEvent(BaseEvent):
    """재실행 이벤트"""

    command_text: str = ""
    command_type: str = ""
    success: bool = True
    execution_time_ms: float = 0.0
    error_message: str | None = None
    affected_files: list[str] = field(default_factory=list)
    stack_count: int = 0
    current_index: int = 0
    can_undo: bool = True
    can_redo: bool = False


@dataclass
class UndoRedoStackChangedEvent(BaseEvent):
    """Undo/Redo 스택 변경 이벤트"""

    can_undo: bool = False
    can_redo: bool = False
    undo_text: str = ""
    redo_text: str = ""
    stack_count: int = 0
    current_index: int = 0
    is_clean: bool = True
    change_type: str = "unknown"
    stack_size_kb: float = 0.0
    memory_usage_mb: float = 0.0


@dataclass
class UndoRedoEnabledEvent(BaseEvent):
    """Undo/Redo 활성화 상태 변경 이벤트"""

    undo_enabled: bool = False
    redo_enabled: bool = False
    undo_text: str = ""
    redo_text: str = ""
    update_menus: bool = True
    update_toolbar: bool = True
    update_shortcuts: bool = True
    update_tooltips: bool = True


@dataclass
class CommandPushedToStackEvent(BaseEvent):
    """Command가 스택에 추가된 이벤트"""

    command_text: str = ""
    command_type: str = ""
    stack_count: int = 0
    can_undo: bool = True
    command_id: str = ""
    merge_attempted: bool = False
    merge_successful: bool = False
    push_time_ms: float = 0.0
    stack_limit_reached: bool = False


@dataclass
class StackClearedEvent(BaseEvent):
    """스택 초기화 이벤트"""

    cleared_count: int = 0
    reason: str = ""
    previous_stack_count: int = 0
    previous_current_index: int = 0
    freed_memory_kb: float = 0.0


@dataclass
class UndoRedoErrorEvent(BaseEvent):
    """Undo/Redo 오류 이벤트"""

    error_type: str = ""
    error_message: str = ""
    command_text: str = ""
    command_type: str = ""
    stack_count: int = 0
    current_index: int = 0
    operation_attempted: str = ""
    recovery_possible: bool = False
    recovery_suggestion: str = ""
    exception_type: str = ""
    stack_trace: str = ""


@dataclass
class UndoRedoPerformanceEvent(BaseEvent):
    """Undo/Redo 성능 메트릭 이벤트"""

    operation_type: str = ""
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_execution_time_ms: float = 0.0
    stack_depth: int = 0
    stack_memory_mb: float = 0.0
    is_slow_operation: bool = False
    is_memory_intensive: bool = False
    performance_warning: str = ""


@dataclass
class UndoRedoStateSnapshotEvent(BaseEvent):
    """Undo/Redo 상태 스냅샷 이벤트"""

    can_undo: bool = False
    can_redo: bool = False
    stack_count: int = 0
    current_index: int = 0
    is_clean: bool = True
    command_history: list[str] = field(default_factory=list)
    undo_history: list[str] = field(default_factory=list)
    redo_history: list[str] = field(default_factory=list)
    total_commands_executed: int = 0
    total_undos: int = 0
    total_redos: int = 0
    success_rate: float = 100.0
    session_duration_minutes: int = 0
    most_used_command_type: str = ""
    total_memory_mb: float = 0.0
    average_command_size_kb: float = 0.0


@dataclass
class UndoRedoBatchOperationEvent(BaseEvent):
    """배치 Undo/Redo 작업 이벤트"""

    operation_type: str = ""
    total_operations: int = 0
    completed_operations: int = 0
    failed_operations: int = 0
    progress_percentage: float = 0.0
    estimated_remaining_ms: float = 0.0
    current_operation: str = ""
    batch_status: str = ""
    total_execution_time_ms: float = 0.0
    successful_files: list[str] = field(default_factory=list)
    failed_files: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)
    recovery_actions: list[str] = field(default_factory=list)


@dataclass
class UndoRedoUIUpdateEvent(BaseEvent):
    """Undo/Redo UI 업데이트 이벤트"""

    update_menus: bool = True
    update_toolbar: bool = True
    update_status_bar: bool = True
    update_shortcuts: bool = False
    undo_menu_text: str = ""
    redo_menu_text: str = ""
    undo_menu_enabled: bool = False
    redo_menu_enabled: bool = False
    undo_button_enabled: bool = False
    redo_button_enabled: bool = False
    undo_tooltip: str = ""
    redo_tooltip: str = ""
    status_message: str = ""
    show_progress: bool = False
    progress_value: int = 0
    animate_changes: bool = True
    highlight_changes: bool = False
    show_notification: bool = False
    notification_message: str = ""
    notification_type: str = "info"


@dataclass
class UndoRedoConfigurationChangedEvent(BaseEvent):
    """Undo/Redo 설정 변경 이벤트"""

    setting_name: str = ""
    old_value: Any = None
    new_value: Any = None
    category: str = ""
    requires_restart: bool = False
    affects_current_stack: bool = False
    affects_ui: bool = True
    change_reason: str = ""
    validation_passed: bool = True
    validation_warnings: list[str] = field(default_factory=list)
