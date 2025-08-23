"""
타입 안전한 이벤트 시스템

dataclass 기반의 강타입 이벤트 정의와 타입 안전한 EventBus
"""

import logging
import threading
import weakref
from collections import defaultdict
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from PyQt5.QtCore import QObject, pyqtSignal

# 이벤트 타입 변수
TEvent = TypeVar("TEvent", bound="BaseEvent")


@dataclass
class BaseEvent:
    """모든 이벤트의 기본 클래스"""

    source: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """이벤트 생성 후 초기화"""
        if self.source is None:
            import inspect

            frame = inspect.currentframe()
            if frame and frame.f_back:
                self.source = frame.f_back.f_code.co_name


@dataclass
class DirectoryCreatedEvent:
    """디렉토리 생성 이벤트"""

    directory_path: str
    source: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    created_by: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# 약한 참조를 지원하는 딕셔너리
class WeakValueDict(MutableMapping):
    """약한 참조 값을 가지는 딕셔너리"""

    def __init__(self):
        self._data = {}
        self._remove = self._data.__delitem__

    def __getitem__(self, key):
        ref = self._data[key]
        item = ref()
        if item is None:
            del self._data[key]
            raise KeyError(key)
        return item

    def __setitem__(self, key, value):
        self._data[key] = weakref.ref(value, lambda ref, key=key: self._remove(key))

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


@runtime_checkable
class ITypedEventBus(Protocol, Generic[TEvent]):
    """타입 안전한 이벤트 버스 인터페이스"""

    def publish(self, event: TEvent) -> None:
        """타입 안전한 이벤트 발행"""
        ...

    def subscribe(self, event_type: type[TEvent], handler: Callable[[TEvent], None]) -> str:
        """타입 안전한 이벤트 구독"""
        ...

    def unsubscribe(self, subscription_id: str) -> bool:
        """구독 해제"""
        ...

    def unsubscribe_all(self, event_type: type[TEvent] | None = None) -> int:
        """모든 구독 해제"""
        ...


class TypedEventBus(QObject):
    """
    타입 안전한 이벤트 버스 구현체

    - dataclass 기반 강타입 이벤트
    - 약한 참조로 메모리 누수 방지
    - PyQt 시그널 기반 스레드 안전 처리
    """

    # PyQt 시그널로 타입 안전한 이벤트 전달
    event_published = pyqtSignal(object)  # BaseEvent 객체

    def __init__(self, parent=None):
        super().__init__(parent)

        # 구독자 저장소 (이벤트 타입 -> 핸들러 딕셔너리)
        # 약한 참조를 사용하여 메모리 누수 방지
        self._subscribers: dict[type[BaseEvent], WeakValueDict] = defaultdict(WeakValueDict)

        # 강한 참조 구독자 저장소 (수동 정리 필요)
        self._strong_subscribers: dict[type[BaseEvent], dict[str, Callable]] = {}

        # 구독 ID 관리
        self._subscription_counter = 0
        self._subscription_map: dict[str, tuple[type[BaseEvent], str]] = {}

        # 스레드 안전성을 위한 락
        self._lock = threading.RLock()

        # 이벤트 통계 및 히스토리
        self._event_stats: dict[str, int] = defaultdict(int)
        self._event_history: list[BaseEvent] = []
        self._max_history_size = 1000

        # 로거 설정
        self.logger = logging.getLogger(__name__)

        # dispose 상태 추적
        self._disposed = False

        # Qt 시그널 연결
        self.event_published.connect(self._handle_event_in_main_thread)

        self.logger.info("TypedEventBus 초기화 완료")

    def publish(self, event: BaseEvent) -> None:
        """타입 안전한 이벤트 발행"""
        if not isinstance(event, BaseEvent):
            raise TypeError(f"이벤트는 BaseEvent의 하위 클래스여야 합니다: {type(event)}")

        try:
            event_type_name = type(event).__name__
            print(f"🚀 [EventBus] 이벤트 발행 시작: {event_type_name}")

            with self._lock:
                # 이벤트 히스토리 저장
                self._event_history.append(event)
                if len(self._event_history) > self._max_history_size:
                    self._event_history.pop(0)

                # 통계 업데이트
                self._event_stats[event_type_name] += 1

                # 현재 구독자 수 확인
                subscriber_count = 0
                if type(event) in self._subscribers:
                    subscriber_count += len(self._subscribers[type(event)])
                if type(event) in self._strong_subscribers:
                    subscriber_count += len(self._strong_subscribers[type(event)])

                print(f"📊 [EventBus] 구독자 수: {subscriber_count}명")

            # PyQt 시그널로 메인 스레드에서 처리
            print(f"🔔 [EventBus] PyQt 시그널 emit: {event_type_name}")
            self.event_published.emit(event)
            print(f"✅ [EventBus] 시그널 emit 완료: {event_type_name}")

            self.logger.debug(
                f"이벤트 발행: {event_type_name} "
                f"(source: {event.source}, correlation_id: {event.correlation_id})"
            )

        except Exception as e:
            print(f"❌ [EventBus] 이벤트 발행 실패: {type(event).__name__} - {e}")
            self.logger.error(f"이벤트 발행 실패: {type(event).__name__} - {e}")
            raise

    def subscribe(
        self, event_type: type[TEvent], handler: Callable[[TEvent], None], weak_ref: bool = True
    ) -> str:
        """
        타입 안전한 이벤트 구독

        Args:
            event_type: 구독할 이벤트 타입
            handler: 이벤트 핸들러 함수
            weak_ref: 약한 참조 사용 여부 (기본: True)

        Returns:
            구독 ID
        """
        if not issubclass(event_type, BaseEvent):
            raise TypeError(f"이벤트 타입은 BaseEvent의 하위 클래스여야 합니다: {event_type}")

        try:
            with self._lock:
                # 구독 ID 생성
                self._subscription_counter += 1
                subscription_id = f"sub_{self._subscription_counter}"

                # 핸들러 저장
                if weak_ref:
                    # 약한 참조로 저장 (자동 정리)
                    self._subscribers[event_type][subscription_id] = handler
                else:
                    # 강한 참조로 저장 (수동 정리 필요)
                    if event_type not in self._strong_subscribers:
                        self._strong_subscribers[event_type] = {}
                    self._strong_subscribers[event_type][subscription_id] = handler

                # 구독 매핑 저장
                self._subscription_map[subscription_id] = (event_type, subscription_id)

                self.logger.debug(
                    f"이벤트 구독: {event_type.__name__} -> {handler.__name__} "
                    f"(id: {subscription_id}, weak_ref: {weak_ref})"
                )

                return subscription_id

        except Exception as e:
            self.logger.error(f"이벤트 구독 실패: {event_type.__name__} - {e}")
            raise

    def unsubscribe(self, subscription_id: str) -> bool:
        """구독 해제"""
        try:
            with self._lock:
                if subscription_id not in self._subscription_map:
                    self.logger.warning(f"존재하지 않는 구독 ID: {subscription_id}")
                    return False

                event_type, handler_key = self._subscription_map[subscription_id]

                # 약한 참조에서 제거
                if handler_key in self._subscribers[event_type]:
                    del self._subscribers[event_type][handler_key]

                # 강한 참조에서 제거
                if (
                    event_type in self._strong_subscribers
                    and handler_key in self._strong_subscribers[event_type]
                ):
                    del self._strong_subscribers[event_type][handler_key]

                # 구독 매핑에서 제거
                del self._subscription_map[subscription_id]

                self.logger.debug(f"이벤트 구독 해제: {subscription_id}")
                return True

        except Exception as e:
            self.logger.error(f"이벤트 구독 해제 실패: {subscription_id} - {e}")
            return False

    def unsubscribe_all(self, event_type: type[BaseEvent] | None = None) -> int:
        """모든 구독 해제"""
        try:
            with self._lock:
                removed_count = 0

                if event_type:
                    # 특정 이벤트 타입의 구독만 해제
                    if event_type in self._subscribers:
                        removed_count += len(self._subscribers[event_type])
                        self._subscribers[event_type].clear()

                    if event_type in self._strong_subscribers:
                        removed_count += len(self._strong_subscribers[event_type])
                        self._strong_subscribers[event_type].clear()

                    # 구독 매핑 정리
                    to_remove = [
                        sub_id
                        for sub_id, (et, _) in self._subscription_map.items()
                        if et == event_type
                    ]
                    for sub_id in to_remove:
                        del self._subscription_map[sub_id]

                else:
                    # 모든 구독 해제
                    for subscribers_dict in self._subscribers.values():
                        removed_count += len(subscribers_dict)
                        subscribers_dict.clear()

                    for subscribers_dict in self._strong_subscribers.values():
                        removed_count += len(subscribers_dict)
                        subscribers_dict.clear()
                    self._strong_subscribers.clear()

                    self._subscription_map.clear()

                self.logger.debug(f"구독 해제 완료: {removed_count}개")
                return removed_count

        except Exception as e:
            self.logger.error(f"구독 해제 실패: {e}")
            return 0

    def _handle_event_in_main_thread(self, event: BaseEvent) -> None:
        """메인 스레드에서 이벤트 처리"""
        try:
            event_type = type(event)
            handlers = []

            print(f"🔔 [EventBus] 메인 스레드에서 이벤트 처리: {event_type.__name__}")

            with self._lock:
                # 약한 참조 핸들러들 수집
                if event_type in self._subscribers:
                    weak_handlers = list(self._subscribers[event_type].values())
                    handlers.extend(weak_handlers)
                    print(f"🔗 [EventBus] 약한 참조 핸들러: {len(weak_handlers)}개")

                # 강한 참조 핸들러들 수집
                if event_type in self._strong_subscribers:
                    strong_handlers = list(self._strong_subscribers[event_type].values())
                    handlers.extend(strong_handlers)
                    print(f"💪 [EventBus] 강한 참조 핸들러: {len(strong_handlers)}개")

            print(f"🎯 [EventBus] 총 핸들러 수: {len(handlers)}개")

            # 핸들러 실행
            executed_count = 0
            for i, handler in enumerate(handlers):
                try:
                    print(
                        f"📤 [EventBus] 핸들러 {i + 1} 실행 중: {handler.__name__ if hasattr(handler, '__name__') else str(handler)}"
                    )
                    handler(event)
                    executed_count += 1
                    print(f"✅ [EventBus] 핸들러 {i + 1} 실행 완료")
                except Exception as e:
                    print(f"❌ [EventBus] 핸들러 {i + 1} 실행 실패: {e}")
                    self.logger.error(
                        f"이벤트 핸들러 실행 실패: {handler.__name__ if hasattr(handler, '__name__') else str(handler)} "
                        f"for {event_type.__name__} - {e}"
                    )

            print(f"🏁 [EventBus] 이벤트 처리 완료: {executed_count}/{len(handlers)}개 핸들러 실행")

            if not handlers:
                print(f"⚠️ [EventBus] 구독자 없는 이벤트: {event_type.__name__}")
                self.logger.debug(f"구독자 없는 이벤트: {event_type.__name__}")

        except Exception as e:
            print(f"❌ [EventBus] 이벤트 처리 실패: {type(event).__name__} - {e}")
            self.logger.error(f"이벤트 처리 실패: {type(event).__name__} - {e}")

    def get_subscribers_count(self, event_type: type[BaseEvent] | None = None) -> int:
        """구독자 수 반환"""
        with self._lock:
            if event_type:
                count = len(self._subscribers.get(event_type, {}))
                count += len(self._strong_subscribers.get(event_type, {}))
                return count
            total = sum(len(handlers) for handlers in self._subscribers.values())
            total += sum(len(handlers) for handlers in self._strong_subscribers.values())
            return total

    def get_event_types(self) -> list[type[BaseEvent]]:
        """등록된 이벤트 타입 목록 반환"""
        with self._lock:
            types = set(self._subscribers.keys())
            types.update(self._strong_subscribers.keys())
            return list(types)

    def get_event_stats(self) -> dict[str, int]:
        """이벤트 통계 반환"""
        with self._lock:
            return dict(self._event_stats)

    def get_recent_events(self, count: int = 10) -> list[BaseEvent]:
        """최근 이벤트 목록 반환"""
        with self._lock:
            return self._event_history[-count:] if count > 0 else self._event_history.copy()

    def clear_history(self) -> None:
        """이벤트 히스토리 정리"""
        with self._lock:
            self._event_history.clear()
            self._event_stats.clear()
        self.logger.debug("이벤트 히스토리 정리 완료")

    def dispose(self) -> None:
        """EventBus 정리"""
        # 중복 dispose 방지
        if hasattr(self, "_disposed") and self._disposed:
            return

        try:
            # 모든 구독 해제
            removed_count = self.unsubscribe_all()

            # 히스토리 정리
            self.clear_history()

            # dispose 완료 표시
            self._disposed = True

            # 간소화된 로깅 (스패밍 방지)
            self.logger.debug(f"TypedEventBus 정리 완료 - {removed_count}개 구독")

        except Exception as e:
            self.logger.error(f"EventBus 정리 실패: {e}")


# 전역 타입 안전한 EventBus 인스턴스
_global_event_bus: TypedEventBus | None = None
_event_bus_lock = threading.Lock()


def get_event_bus() -> TypedEventBus:
    """전역 타입 안전한 EventBus 가져오기"""
    global _global_event_bus

    if _global_event_bus is None:
        with _event_bus_lock:
            if _global_event_bus is None:
                _global_event_bus = TypedEventBus()

    return _global_event_bus


def set_event_bus(event_bus: TypedEventBus) -> None:
    """전역 EventBus 설정 (테스트용)"""
    global _global_event_bus
    with _event_bus_lock:
        _global_event_bus = event_bus


def reset_event_bus() -> None:
    """전역 EventBus 리셋 (테스트용)"""
    global _global_event_bus
    with _event_bus_lock:
        if _global_event_bus:
            _global_event_bus.dispose()
        _global_event_bus = None
