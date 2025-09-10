"""
AnimeSorter 이벤트 시스템

이벤트 기반 아키텍처를 위한 핵심 이벤트 정의와 타입 안전한 이벤트 버스 인터페이스를 제공합니다.
"""

import logging

logger = logging.getLogger(__name__)
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

TEvent = TypeVar("TEvent", bound="BaseEvent")


class EventPriority(Enum):
    """이벤트 우선순위"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventCategory(Enum):
    """이벤트 카테고리"""

    APPLICATION = "application"
    UI = "ui"
    FILE_OPERATION = "file_operation"
    TMDB = "tmdb"
    BACKGROUND = "background"
    SYSTEM = "system"


@dataclass
class BaseEvent:
    """모든 이벤트의 기본 클래스"""

    event_id: str = field(
        default_factory=lambda: f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    )
    correlation_id: str | None = None
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    category: EventCategory = EventCategory.APPLICATION
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """이벤트 초기화 후 처리"""
        if not self.correlation_id:
            self.correlation_id = self.event_id


@runtime_checkable
class IEventBus(Protocol, Generic[TEvent]):
    """이벤트 버스 인터페이스"""

    def publish(self, event: TEvent) -> None:
        """이벤트 발행"""
        ...

    def subscribe(self, event_type: type[TEvent], handler: Callable[[TEvent], None]) -> str:
        """이벤트 구독"""
        ...

    def unsubscribe(self, subscription_id: str) -> bool:
        """구독 해제"""
        ...

    def unsubscribe_all(self, event_type: type[TEvent] | None = None) -> int:
        """모든 구독 해제"""
        ...


_global_event_bus = None
_event_bus_lock = threading.Lock()


def get_event_bus():
    """전역 이벤트 버스 가져오기 (UnifiedEventBus 호환성 래퍼 사용)"""
    from src.core.unified_event_system import (TypedEventBusCompatibility,
                                               get_unified_event_bus)

    unified_bus = get_unified_event_bus()
    return TypedEventBusCompatibility(unified_bus)


def set_event_bus(event_bus) -> None:
    """전역 EventBus 설정 (테스트용)"""
    global _global_event_bus
    _global_event_bus = event_bus
