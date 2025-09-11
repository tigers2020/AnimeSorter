"""
AnimeSorter 핵심 이벤트 정의

12개 핵심 이벤트 타입과 기본 이벤트 클래스를 정의합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from src.core.unified_event_system import EventCategory, EventPriority


class CoreEventType(Enum):
    """12개 핵심 이벤트 타입"""

    SCAN_STARTED = "scan_started"
    SCAN_PROGRESS = "scan_progress"
    SCAN_COMPLETED = "scan_completed"
    PLAN_CREATED = "plan_created"
    PLAN_VALIDATED = "plan_validated"
    ORGANIZE_STARTED = "organize_started"
    ORGANIZE_CONFLICT = "organize_conflict"
    ORGANIZE_SKIPPED = "organize_skipped"
    ORGANIZE_COMPLETED = "organize_completed"
    USER_ACTION_REQUIRED = "user_action_required"
    ERROR = "error"
    SETTINGS_CHANGED = "settings_changed"


@dataclass
class CoreEvent:
    """통합된 핵심 이벤트"""

    event_type: CoreEventType
    job_id: str = field(default_factory=lambda: str(uuid4()))
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "core_event"
    correlation_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    category: EventCategory = EventCategory.SYSTEM
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """이벤트 생성 후 초기화"""
        if not self.correlation_id:
            self.correlation_id = self.job_id
