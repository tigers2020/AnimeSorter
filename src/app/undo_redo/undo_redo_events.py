"""
Undo/Redo 시스템 이벤트

Undo/Redo 작업과 관련된 모든 이벤트 정의
"""

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

    # 스택 상태
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

    # 스택 상태
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

    # 변경 종류
    change_type: str = "unknown"  # "push", "undo", "redo", "clear", "clean"

    # 성능 메트릭
    stack_size_kb: float = 0.0
    memory_usage_mb: float = 0.0


@dataclass
class UndoRedoEnabledEvent(BaseEvent):
    """Undo/Redo 활성화 상태 변경 이벤트"""

    undo_enabled: bool = False
    redo_enabled: bool = False
    undo_text: str = ""
    redo_text: str = ""

    # UI 업데이트 힌트
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

    # Command 세부 정보
    command_id: str = ""
    merge_attempted: bool = False
    merge_successful: bool = False

    # 성능 정보
    push_time_ms: float = 0.0
    stack_limit_reached: bool = False


@dataclass
class StackClearedEvent(BaseEvent):
    """스택 초기화 이벤트"""

    cleared_count: int = 0
    reason: str = ""  # "manual", "automatic", "limit_reached", "error"

    # 정리 전 상태
    previous_stack_count: int = 0
    previous_current_index: int = 0

    # 메모리 정보
    freed_memory_kb: float = 0.0


@dataclass
class UndoRedoErrorEvent(BaseEvent):
    """Undo/Redo 오류 이벤트"""

    error_type: str = ""  # "execution_error", "undo_error", "redo_error", "stack_error"
    error_message: str = ""
    command_text: str = ""
    command_type: str = ""

    # 오류 컨텍스트
    stack_count: int = 0
    current_index: int = 0
    operation_attempted: str = ""  # "undo", "redo", "push", "clear"

    # 복구 정보
    recovery_possible: bool = False
    recovery_suggestion: str = ""

    # 기술적 세부사항
    exception_type: str = ""
    stack_trace: str = ""


@dataclass
class UndoRedoPerformanceEvent(BaseEvent):
    """Undo/Redo 성능 메트릭 이벤트"""

    operation_type: str = ""  # "undo", "redo", "push"
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0

    # 통계
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_execution_time_ms: float = 0.0

    # 스택 메트릭
    stack_depth: int = 0
    stack_memory_mb: float = 0.0

    # 성능 경고
    is_slow_operation: bool = False
    is_memory_intensive: bool = False
    performance_warning: str = ""


@dataclass
class UndoRedoStateSnapshotEvent(BaseEvent):
    """Undo/Redo 상태 스냅샷 이벤트"""

    # 현재 상태
    can_undo: bool = False
    can_redo: bool = False
    stack_count: int = 0
    current_index: int = 0
    is_clean: bool = True

    # 히스토리
    command_history: list[str] = field(default_factory=list)
    undo_history: list[str] = field(default_factory=list)
    redo_history: list[str] = field(default_factory=list)

    # 통계
    total_commands_executed: int = 0
    total_undos: int = 0
    total_redos: int = 0
    success_rate: float = 100.0

    # 세션 정보
    session_duration_minutes: int = 0
    most_used_command_type: str = ""

    # 메모리 사용량
    total_memory_mb: float = 0.0
    average_command_size_kb: float = 0.0


@dataclass
class UndoRedoBatchOperationEvent(BaseEvent):
    """배치 Undo/Redo 작업 이벤트"""

    operation_type: str = ""  # "batch_undo", "batch_redo", "batch_clear"
    total_operations: int = 0
    completed_operations: int = 0
    failed_operations: int = 0

    # 진행 상황
    progress_percentage: float = 0.0
    estimated_remaining_ms: float = 0.0
    current_operation: str = ""

    # 배치 상태
    batch_status: str = ""  # "started", "in_progress", "completed", "failed", "cancelled"

    # 결과
    total_execution_time_ms: float = 0.0
    successful_files: list[str] = field(default_factory=list)
    failed_files: list[str] = field(default_factory=list)

    # 오류 정보
    error_messages: list[str] = field(default_factory=list)
    recovery_actions: list[str] = field(default_factory=list)


@dataclass
class UndoRedoUIUpdateEvent(BaseEvent):
    """Undo/Redo UI 업데이트 이벤트"""

    # 업데이트 대상
    update_menus: bool = True
    update_toolbar: bool = True
    update_status_bar: bool = True
    update_shortcuts: bool = False

    # 메뉴 정보
    undo_menu_text: str = ""
    redo_menu_text: str = ""
    undo_menu_enabled: bool = False
    redo_menu_enabled: bool = False

    # 툴바 정보
    undo_button_enabled: bool = False
    redo_button_enabled: bool = False
    undo_tooltip: str = ""
    redo_tooltip: str = ""

    # 상태바 정보
    status_message: str = ""
    show_progress: bool = False
    progress_value: int = 0

    # 애니메이션 힌트
    animate_changes: bool = True
    highlight_changes: bool = False

    # 사용자 피드백
    show_notification: bool = False
    notification_message: str = ""
    notification_type: str = "info"  # "info", "success", "warning", "error"


@dataclass
class UndoRedoConfigurationChangedEvent(BaseEvent):
    """Undo/Redo 설정 변경 이벤트"""

    setting_name: str = ""
    old_value: Any = None
    new_value: Any = None

    # 설정 카테고리
    category: str = ""  # "stack", "ui", "performance", "logging"

    # 영향 범위
    requires_restart: bool = False
    affects_current_stack: bool = False
    affects_ui: bool = True

    # 변경 이유
    change_reason: str = ""  # "user", "automatic", "performance", "error_recovery"

    # 검증 결과
    validation_passed: bool = True
    validation_warnings: list[str] = field(default_factory=list)
