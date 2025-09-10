"""
Command 관련 이벤트 정의

Command 실행, 취소, 실패 등의 상태 변화를 EventBus로 전파
"""

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from src.app.commands.base_command import CommandResult
from src.app.events import BaseEvent


@dataclass
class CommandExecutedEvent(BaseEvent):
    """Command 실행 완료 이벤트"""

    command_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    command_type: str = ""
    description: str = ""
    result: CommandResult | None = None
    affected_files: list[Path] = field(default_factory=list)
    execution_time_ms: float = 0.0


@dataclass
class CommandUndoneEvent(BaseEvent):
    """Command 취소 완료 이벤트"""

    command_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    command_type: str = ""
    description: str = ""
    result: CommandResult | None = None
    undo_time_ms: float = 0.0


@dataclass
class CommandRedoneEvent(BaseEvent):
    """Command 재실행 완료 이벤트"""

    command_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    command_type: str = ""
    description: str = ""
    result: CommandResult | None = None
    redo_time_ms: float = 0.0


@dataclass
class CommandFailedEvent(BaseEvent):
    """Command 실행 실패 이벤트"""

    command_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    command_type: str = ""
    description: str = ""
    error_type: str = ""
    error_message: str = ""
    error_details: str | None = None


@dataclass
class BatchCommandStartedEvent(BaseEvent):
    """배치 Command 시작 이벤트"""

    batch_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    command_count: int = 0
    description: str = ""
    estimated_duration_ms: float | None = None


@dataclass
class BatchCommandProgressEvent(BaseEvent):
    """배치 Command 진행 상황 이벤트"""

    batch_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    completed_count: int = 0
    total_count: int = 0
    current_command_description: str = ""
    progress_percentage: float = 0.0


@dataclass
class BatchCommandCompletedEvent(BaseEvent):
    """배치 Command 완료 이벤트"""

    batch_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    success_count: int = 0
    failed_count: int = 0
    total_execution_time_ms: float = 0.0
    failed_commands: list[UUID] = field(default_factory=list)


@dataclass
class CommandValidationFailedEvent(BaseEvent):
    """Command 유효성 검사 실패 이벤트"""

    command_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    command_type: str = ""
    description: str = ""
    validation_errors: list[str] = field(default_factory=list)


@dataclass
class CommandQueueUpdatedEvent(BaseEvent):
    """Command 큐 상태 업데이트 이벤트"""

    queue_size: int = 0
    pending_commands: int = 0
    executing_commands: int = 0
    can_undo_count: int = 0
    can_redo_count: int = 0
