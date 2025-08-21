"""
백그라운드 작업 관련 이벤트 정의

이 모듈은 백그라운드 작업의 상태 변화를 나타내는 이벤트들을 정의합니다.
QThread/QRunnable 기반 비동기 작업과 UI 간의 통신에 사용됩니다.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from app.events import BaseEvent


class TaskStatus(Enum):
    """백그라운드 작업 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """작업 우선순위"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskStartedEvent(BaseEvent):
    """백그라운드 작업 시작 이벤트"""

    task_id: str = field(default_factory=lambda: str(uuid4()))
    task_type: str = ""
    task_name: str = ""
    estimated_duration: float | None = None  # 초 단위 예상 소요시간
    priority: TaskPriority = TaskPriority.NORMAL
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskProgressEvent(BaseEvent):
    """백그라운드 작업 진행률 이벤트"""

    task_id: str = ""
    progress_percent: int = 0  # 0-100
    current_step: str = ""
    items_processed: int = 0
    total_items: int = 0
    elapsed_time: float = 0.0  # 초 단위 경과시간
    estimated_remaining: float | None = None  # 초 단위 예상 남은시간
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskCompletedEvent(BaseEvent):
    """백그라운드 작업 완료 이벤트"""

    task_id: str = ""
    task_type: str = ""
    task_name: str = ""
    duration: float = 0.0  # 초 단위 실제 소요시간
    result_data: Any = None
    items_processed: int = 0
    success_count: int = 0
    error_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskFailedEvent(BaseEvent):
    """백그라운드 작업 실패 이벤트"""

    task_id: str = ""
    task_type: str = ""
    task_name: str = ""
    error_message: str = ""
    error_details: str = ""
    error_type: str = "UnknownError"
    duration: float = 0.0  # 실패까지 소요시간
    items_processed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskCancelledEvent(BaseEvent):
    """백그라운드 작업 취소 이벤트"""

    task_id: str = ""
    task_type: str = ""
    task_name: str = ""
    reason: str = "사용자 요청"
    duration: float = 0.0  # 취소까지 소요시간
    items_processed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskQueueStatusEvent(BaseEvent):
    """작업 큐 상태 이벤트"""

    total_tasks: int = 0
    running_tasks: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    queue_size: int = 0
    max_concurrent_tasks: int = 4
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskRetryEvent(BaseEvent):
    """백그라운드 작업 재시도 이벤트"""

    task_id: str = ""
    task_type: str = ""
    task_name: str = ""
    retry_count: int = 0
    max_retries: int = 3
    last_error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
