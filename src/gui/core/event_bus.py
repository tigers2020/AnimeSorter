"""
이벤트 버스 구현체

컴포넌트 간 이벤트 기반 통신을 위한 중앙 허브
"""

import logging
import threading
from typing import Any, Callable, Dict, List, Set
from collections import defaultdict
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from ..interfaces.i_event_bus import IEventBus, Event


class EventBus(QObject, IEventBus):
    """
    이벤트 버스 구현체
    
    스레드 안전한 이벤트 발행/구독 시스템 제공
    """
    
    # Qt 시그널로 이벤트 전달 (메인 스레드에서 안전하게 처리)
    event_published = pyqtSignal(object)  # Event 객체
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 구독자 저장소 (이벤트 타입 -> 핸들러 리스트)
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = defaultdict(list)
        
        # 스레드 안전성을 위한 락
        self._lock = threading.RLock()
        
        # 이벤트 히스토리 (디버깅용)
        self._event_history: List[Event] = []
        self._max_history_size = 1000
        
        # 이벤트 통계
        self._event_stats: Dict[str, int] = defaultdict(int)
        
        # 로거 설정
        self.logger = logging.getLogger(__name__)
        
        # Qt 시그널 연결
        self.event_published.connect(self._handle_event_in_main_thread)
        
        # 지연 이벤트 처리를 위한 타이머
        self._delayed_events: List[tuple] = []  # (event, delay_ms)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_delayed_events)
        self._timer.start(10)  # 10ms마다 체크
        
        self.logger.info("EventBus 초기화 완료")
    
    def publish(self, event_type: str, data: Any = None, source: str = None, target: str = None) -> None:
        """이벤트 발행"""
        try:
            event = Event(
                type=event_type,
                data=data,
                source=source,
                target=target
            )
            
            with self._lock:
                # 이벤트 히스토리 저장
                self._event_history.append(event)
                if len(self._event_history) > self._max_history_size:
                    self._event_history.pop(0)
                
                # 통계 업데이트
                self._event_stats[event_type] += 1
            
            # Qt 시그널로 메인 스레드에서 처리
            self.event_published.emit(event)
            
            self.logger.debug(f"이벤트 발행: {event_type} (source: {source}, target: {target})")
            
        except Exception as e:
            self.logger.error(f"이벤트 발행 실패: {event_type} - {e}")
    
    def publish_delayed(self, event_type: str, delay_ms: int, data: Any = None, 
                       source: str = None, target: str = None) -> None:
        """지연 이벤트 발행"""
        event = Event(
            type=event_type,
            data=data,
            source=source,
            target=target
        )
        
        import time
        trigger_time = time.time() * 1000 + delay_ms
        
        with self._lock:
            self._delayed_events.append((event, trigger_time))
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """이벤트 구독"""
        try:
            with self._lock:
                if handler not in self._subscribers[event_type]:
                    self._subscribers[event_type].append(handler)
                    self.logger.debug(f"이벤트 구독: {event_type} - {handler.__name__}")
                else:
                    self.logger.warning(f"이미 구독된 핸들러: {event_type} - {handler.__name__}")
        except Exception as e:
            self.logger.error(f"이벤트 구독 실패: {event_type} - {e}")
    
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """이벤트 구독 해제"""
        try:
            with self._lock:
                if handler in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(handler)
                    self.logger.debug(f"이벤트 구독 해제: {event_type} - {handler.__name__}")
                else:
                    self.logger.warning(f"구독되지 않은 핸들러: {event_type} - {handler.__name__}")
        except Exception as e:
            self.logger.error(f"이벤트 구독 해제 실패: {event_type} - {e}")
    
    def clear_subscribers(self, event_type: str = None) -> None:
        """구독자 정리"""
        try:
            with self._lock:
                if event_type:
                    if event_type in self._subscribers:
                        count = len(self._subscribers[event_type])
                        self._subscribers[event_type].clear()
                        self.logger.info(f"이벤트 구독자 정리: {event_type} ({count}개)")
                else:
                    total_count = sum(len(handlers) for handlers in self._subscribers.values())
                    self._subscribers.clear()
                    self.logger.info(f"모든 이벤트 구독자 정리 ({total_count}개)")
        except Exception as e:
            self.logger.error(f"구독자 정리 실패: {e}")
    
    def _handle_event_in_main_thread(self, event: Event) -> None:
        """메인 스레드에서 이벤트 처리"""
        try:
            with self._lock:
                handlers = self._subscribers.get(event.type, []).copy()
            
            # 타겟이 지정된 경우 필터링
            if event.target:
                handlers = [h for h in handlers if getattr(h, '__self__', None) and 
                           getattr(h.__self__, 'name', '') == event.target]
            
            # 핸들러 실행
            for handler in handlers:
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(f"이벤트 핸들러 실행 실패: {handler.__name__} - {e}")
            
            if not handlers:
                self.logger.debug(f"구독자 없는 이벤트: {event.type}")
                
        except Exception as e:
            self.logger.error(f"이벤트 처리 실패: {event.type} - {e}")
    
    def _process_delayed_events(self) -> None:
        """지연된 이벤트 처리"""
        if not self._delayed_events:
            return
        
        import time
        current_time = time.time() * 1000
        
        with self._lock:
            ready_events = []
            remaining_events = []
            
            for event, trigger_time in self._delayed_events:
                if current_time >= trigger_time:
                    ready_events.append(event)
                else:
                    remaining_events.append((event, trigger_time))
            
            self._delayed_events = remaining_events
        
        # 준비된 이벤트 발행
        for event in ready_events:
            self.event_published.emit(event)
    
    def get_subscribers_count(self, event_type: str = None) -> int:
        """구독자 수 반환"""
        with self._lock:
            if event_type:
                return len(self._subscribers.get(event_type, []))
            else:
                return sum(len(handlers) for handlers in self._subscribers.values())
    
    def get_event_types(self) -> List[str]:
        """등록된 이벤트 타입 목록 반환"""
        with self._lock:
            return list(self._subscribers.keys())
    
    def get_event_stats(self) -> Dict[str, int]:
        """이벤트 통계 반환"""
        with self._lock:
            return dict(self._event_stats)
    
    def get_recent_events(self, count: int = 10) -> List[Event]:
        """최근 이벤트 목록 반환"""
        with self._lock:
            return self._event_history[-count:] if count > 0 else self._event_history.copy()
    
    def clear_history(self) -> None:
        """이벤트 히스토리 정리"""
        with self._lock:
            self._event_history.clear()
            self._event_stats.clear()
        self.logger.info("이벤트 히스토리 정리 완료")
