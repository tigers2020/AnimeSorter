"""
통합 이벤트 시스템 - AnimeSorter

기존의 여러 이벤트 시스템들을 통합하여 일관된 패턴을 제공하는 시스템입니다.
- TypedEventBus: 타입 안전한 이벤트 시스템
- GUI EventBus: Qt 기반 GUI 이벤트 시스템
- Application Events: 도메인별 이벤트 정의
- Background Events: 백그라운드 작업 이벤트
"""

import logging
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Protocol, TypeVar, runtime_checkable

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

# 이벤트 타입 변수
TEvent = TypeVar("TEvent", bound="BaseEvent")


class EventPriority(Enum):
    """이벤트 우선순위"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventCategory(Enum):
    """이벤트 카테고리"""

    SYSTEM = "system"
    USER_ACTION = "user_action"
    FILE_OPERATION = "file_operation"
    METADATA = "metadata"
    MEDIA = "media"
    BACKGROUND = "background"
    COMMAND = "command"
    JOURNAL = "journal"
    GUI = "gui"
    PERFORMANCE = "performance"


@dataclass
class BaseEvent:
    """모든 이벤트의 기본 클래스"""

    source: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    category: EventCategory = EventCategory.SYSTEM
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """이벤트 생성 후 초기화"""
        if self.source is None:
            import inspect

            frame = inspect.currentframe()
            if frame and frame.f_back:
                self.source = frame.f_back.f_code.co_name


@dataclass
class EventContext:
    """이벤트 컨텍스트 정보"""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    source_component: Optional[str] = None
    target_component: Optional[str] = None
    additional_context: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IEventHandler(Protocol):
    """이벤트 핸들러 인터페이스"""

    def handle_event(self, event: BaseEvent) -> None:
        """이벤트 처리"""
        ...


class EventHandler(ABC):
    """이벤트 핸들러 기본 클래스"""

    def __init__(self, name: str, priority: int = 0):
        self.name = name
        self.priority = priority
        self.enabled = True

    @abstractmethod
    def can_handle(self, event: BaseEvent) -> bool:
        """이벤트를 처리할 수 있는지 확인"""

    @abstractmethod
    def handle_event(self, event: BaseEvent) -> None:
        """이벤트 처리"""

    def __lt__(self, other):
        """우선순위 기반 정렬"""
        return self.priority > other.priority


class EventFilter:
    """이벤트 필터"""

    def __init__(
        self,
        categories: Optional[list[EventCategory]] = None,
        sources: Optional[list[str]] = None,
        priority_min: Optional[EventPriority] = None,
        priority_max: Optional[EventPriority] = None,
    ):
        self.categories = categories or []
        self.sources = sources or []
        self.priority_min = priority_min
        self.priority_max = priority_max

    def matches(self, event: BaseEvent) -> bool:
        """이벤트가 필터와 일치하는지 확인"""
        # 카테고리 필터
        if self.categories and event.category not in self.categories:
            return False

        # 소스 필터
        if self.sources and event.source not in self.sources:
            return False

        # 우선순위 필터
        if self.priority_min and event.priority.value < self.priority_min.value:
            return False

        if self.priority_max and event.priority.value > self.priority_max.value:
            return False

        return True


class EventSubscription:
    """이벤트 구독 정보"""

    def __init__(
        self,
        subscription_id: str,
        event_type: type,
        handler: Callable[[BaseEvent], None],
        filter: Optional[EventFilter] = None,
        priority: int = 0,
    ):
        self.subscription_id = subscription_id
        self.event_type = event_type
        self.handler = handler
        self.filter = filter
        self.priority = priority
        self.created_at = datetime.now()
        self.last_used = None
        self.usage_count = 0


class UnifiedEventBus(QObject):
    """통합 이벤트 버스"""

    # Qt 시그널
    event_published = pyqtSignal(object)  # BaseEvent 객체
    event_handled = pyqtSignal(str, str)  # event_type, handler_name
    event_failed = pyqtSignal(str, str, str)  # event_type, handler_name, error

    def __init__(self, parent=None):
        super().__init__(parent)

        # 구독자 저장소 (이벤트 타입 -> 구독 리스트)
        self._subscriptions: dict[type, list[EventSubscription]] = defaultdict(list)

        # 핸들러 저장소 (이벤트 타입 -> 핸들러 리스트)
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

        # 스레드 안전성을 위한 락
        self._lock = threading.RLock()

        # 이벤트 히스토리 (디버깅용)
        self._event_history: list[BaseEvent] = []
        self._max_history_size = 1000

        # 이벤트 통계
        self._event_stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # 구독 ID 카운터
        self._subscription_counter = 0

        # Qt 시그널 연결
        self.event_published.connect(self._handle_event_in_main_thread)

        logger.info("UnifiedEventBus 초기화 완료")

    def publish(self, event: BaseEvent) -> bool:
        """이벤트 발행"""
        try:
            with self._lock:
                # 이벤트 히스토리 저장
                self._event_history.append(event)
                if len(self._event_history) > self._max_history_size:
                    self._event_history.pop(0)

                # 통계 업데이트
                event_type_name = event.__class__.__name__
                self._event_stats[event_type_name]["published"] += 1
                self._event_stats[event_type_name]["last_published"] = datetime.now()

            # Qt 시그널로 메인 스레드에서 처리
            self.event_published.emit(event)

            logger.debug(
                f"이벤트 발행: {event.__class__.__name__} (source: {event.source}, priority: {event.priority})"
            )
            return True

        except Exception as e:
            logger.error(f"이벤트 발행 실패: {event.__class__.__name__} - {e}")
            return False

    def subscribe(
        self,
        event_type: type[TEvent],
        handler: Callable[[TEvent], None],
        filter: Optional[EventFilter] = None,
        priority: int = 0,
    ) -> str:
        """이벤트 구독"""
        try:
            subscription_id = f"sub_{self._subscription_counter:06d}"
            self._subscription_counter += 1

            subscription = EventSubscription(
                subscription_id=subscription_id,
                event_type=event_type,
                handler=handler,
                filter=filter,
                priority=priority,
            )

            with self._lock:
                self._subscriptions[event_type].append(subscription)
                # 우선순위 기반 정렬
                self._subscriptions[event_type].sort(key=lambda x: x.priority, reverse=True)

            logger.debug(f"이벤트 구독 등록: {event_type.__name__} -> {subscription_id}")
            return subscription_id

        except Exception as e:
            logger.error(f"이벤트 구독 실패: {event_type.__name__} - {e}")
            return ""

    def unsubscribe(self, subscription_id: str) -> bool:
        """구독 해제"""
        try:
            with self._lock:
                for event_type, subscriptions in self._subscriptions.items():
                    for i, subscription in enumerate(subscriptions):
                        if subscription.subscription_id == subscription_id:
                            subscriptions.pop(i)
                            logger.debug(f"이벤트 구독 해제: {subscription_id}")
                            return True

            logger.warning(f"구독을 찾을 수 없음: {subscription_id}")
            return False

        except Exception as e:
            logger.error(f"구독 해제 실패: {subscription_id} - {e}")
            return False

    def register_handler(self, event_type: type, handler: EventHandler) -> bool:
        """이벤트 핸들러 등록"""
        try:
            with self._lock:
                self._handlers[event_type].append(handler)
                # 우선순위 기반 정렬
                self._handlers[event_type].sort()

            logger.debug(f"이벤트 핸들러 등록: {event_type.__name__} -> {handler.name}")
            return True

        except Exception as e:
            logger.error(f"이벤트 핸들러 등록 실패: {event_type.__name__} -> {handler.name} - {e}")
            return False

    def unregister_handler(self, event_type: type, handler_name: str) -> bool:
        """이벤트 핸들러 등록 해제"""
        try:
            with self._lock:
                handlers = self._handlers[event_type]
                for i, handler in enumerate(handlers):
                    if handler.name == handler_name:
                        handlers.pop(i)
                        logger.debug(
                            f"이벤트 핸들러 등록 해제: {event_type.__name__} -> {handler_name}"
                        )
                        return True

            logger.warning(f"핸들러를 찾을 수 없음: {event_type.__name__} -> {handler_name}")
            return False

        except Exception as e:
            logger.error(
                f"이벤트 핸들러 등록 해제 실패: {event_type.__name__} -> {handler_name} - {e}"
            )
            return False

    def _handle_event_in_main_thread(self, event: BaseEvent) -> None:
        """메인 스레드에서 이벤트 처리"""
        try:
            event_type = type(event)

            # 구독자들에게 이벤트 전달
            self._notify_subscribers(event, event_type)

            # 핸들러들에게 이벤트 전달
            self._notify_handlers(event, event_type)

        except Exception as e:
            logger.error(f"이벤트 처리 실패: {event.__class__.__name__} - {e}")

    def _notify_subscribers(self, event: BaseEvent, event_type: type) -> None:
        """구독자들에게 이벤트 알림"""
        try:
            with self._lock:
                subscriptions = self._subscriptions.get(event_type, [])

            for subscription in subscriptions:
                try:
                    # 필터 확인
                    if subscription.filter and not subscription.filter.matches(event):
                        continue

                    # 핸들러 호출
                    subscription.handler(event)

                    # 사용 통계 업데이트
                    subscription.last_used = datetime.now()
                    subscription.usage_count += 1

                    # Qt 시그널 발생
                    self.event_handled.emit(event_type.__name__, subscription.subscription_id)

                except Exception as e:
                    logger.error(f"구독자 이벤트 처리 실패: {subscription.subscription_id} - {e}")
                    self.event_failed.emit(
                        event_type.__name__, subscription.subscription_id, str(e)
                    )

        except Exception as e:
            logger.error(f"구독자 알림 실패: {e}")

    def _notify_handlers(self, event: BaseEvent, event_type: type) -> None:
        """핸들러들에게 이벤트 알림"""
        try:
            with self._lock:
                handlers = self._handlers.get(event_type, [])

            for handler in handlers:
                try:
                    if not handler.enabled:
                        continue

                    if handler.can_handle(event):
                        handler.handle_event(event)

                        # Qt 시그널 발생
                        self.event_handled.emit(event_type.__name__, handler.name)

                except Exception as e:
                    logger.error(f"핸들러 이벤트 처리 실패: {handler.name} - {e}")
                    self.event_failed.emit(event_type.__name__, handler.name, str(e))

        except Exception as e:
            logger.error(f"핸들러 알림 실패: {e}")

    def get_event_history(
        self, event_type: Optional[type] = None, limit: Optional[int] = None
    ) -> list[BaseEvent]:
        """이벤트 히스토리 조회"""
        try:
            with self._lock:
                if event_type:
                    history = [e for e in self._event_history if isinstance(e, event_type)]
                else:
                    history = self._event_history.copy()

                if limit:
                    history = history[-limit:]

                return history

        except Exception as e:
            logger.error(f"이벤트 히스토리 조회 실패: {e}")
            return []

    def get_event_stats(self, event_type: Optional[str] = None) -> dict[str, Any]:
        """이벤트 통계 조회"""
        try:
            with self._lock:
                if event_type:
                    return self._event_stats.get(event_type, {}).copy()
                else:
                    return {k: v.copy() for k, v in self._event_stats.items()}

        except Exception as e:
            logger.error(f"이벤트 통계 조회 실패: {e}")
            return {}

    def clear_history(self) -> None:
        """이벤트 히스토리 정리"""
        try:
            with self._lock:
                self._event_history.clear()
            logger.info("이벤트 히스토리 정리 완료")
        except Exception as e:
            logger.error(f"이벤트 히스토리 정리 실패: {e}")

    def get_subscription_count(self, event_type: Optional[type] = None) -> int:
        """구독 수 조회"""
        try:
            with self._lock:
                if event_type:
                    return len(self._subscriptions.get(event_type, []))
                else:
                    return sum(len(subs) for subs in self._subscriptions.values())

        except Exception as e:
            logger.error(f"구독 수 조회 실패: {e}")
            return 0


class EventBusManager:
    """이벤트 버스 관리자"""

    def __init__(self):
        self._event_bus = UnifiedEventBus()
        self._legacy_systems = {}
        self._migration_status = {}

    @property
    def event_bus(self) -> UnifiedEventBus:
        """통합 이벤트 버스 반환"""
        return self._event_bus

    def register_legacy_system(self, name: str, system: Any) -> bool:
        """레거시 이벤트 시스템 등록"""
        try:
            self._legacy_systems[name] = system
            logger.info(f"레거시 이벤트 시스템 등록: {name}")
            return True
        except Exception as e:
            logger.error(f"레거시 이벤트 시스템 등록 실패: {name} - {e}")
            return False

    def migrate_legacy_events(self, system_name: str) -> bool:
        """레거시 이벤트 시스템 마이그레이션"""
        try:
            if system_name not in self._legacy_systems:
                logger.warning(f"레거시 시스템을 찾을 수 없음: {system_name}")
                return False

            system = self._legacy_systems[system_name]

            # 시스템별 마이그레이션 로직
            if system_name == "typed_event_bus":
                self._migrate_typed_event_bus(system)
            elif system_name == "gui_event_bus":
                self._migrate_gui_event_bus(system)
            else:
                logger.warning(f"알 수 없는 레거시 시스템: {system_name}")
                return False

            self._migration_status[system_name] = "completed"
            logger.info(f"레거시 이벤트 시스템 마이그레이션 완료: {system_name}")
            return True

        except Exception as e:
            logger.error(f"레거시 이벤트 시스템 마이그레이션 실패: {system_name} - {e}")
            self._migration_status[system_name] = "failed"
            return False

    def _migrate_typed_event_bus(self, system: Any) -> None:
        """TypedEventBus 마이그레이션"""
        try:
            # 기존 구독자들을 통합 이벤트 버스로 마이그레이션
            if hasattr(system, "_subscribers"):
                for event_type, subscribers in system._subscribers.items():
                    for subscriber in subscribers:
                        # 약한 참조 처리
                        if callable(subscriber):
                            self._event_bus.subscribe(event_type, subscriber)

            logger.info("TypedEventBus 마이그레이션 완료")

        except Exception as e:
            logger.error(f"TypedEventBus 마이그레이션 실패: {e}")

    def _migrate_gui_event_bus(self, system: Any) -> None:
        """GUI EventBus 마이그레이션"""
        try:
            # 기존 구독자들을 통합 이벤트 버스로 마이그레이션
            if hasattr(system, "_subscribers"):
                for event_type, subscribers in system._subscribers.items():
                    for subscriber in subscribers:
                        if callable(subscriber):
                            self._event_bus.subscribe(event_type, subscriber)

            logger.info("GUI EventBus 마이그레이션 완료")

        except Exception as e:
            logger.error(f"GUI EventBus 마이그레이션 실패: {e}")

    def get_migration_status(self) -> dict[str, str]:
        """마이그레이션 상태 조회"""
        return self._migration_status.copy()

    def is_fully_migrated(self) -> bool:
        """모든 시스템이 마이그레이션되었는지 확인"""
        return all(status == "completed" for status in self._migration_status.values())


# 전역 인스턴스
event_bus_manager = EventBusManager()
unified_event_bus = event_bus_manager.event_bus


def get_unified_event_bus() -> UnifiedEventBus:
    """통합 이벤트 버스 반환"""
    return unified_event_bus


def get_event_bus_manager() -> EventBusManager:
    """이벤트 버스 관리자 반환"""
    return event_bus_manager
