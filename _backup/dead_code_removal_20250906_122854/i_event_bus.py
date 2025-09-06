"""
이벤트 버스 인터페이스

컴포넌트 간 느슨한 결합을 위한 이벤트 기반 통신 인터페이스
"""

from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Event:
    """이벤트 데이터 클래스"""

    type: str
    data: Any = None
    source: str = None
    target: str = None


class IEventBus:
    """이벤트 버스 인터페이스"""

    @abstractmethod
    def publish(
        self, event_type: str, data: Any = None, source: str = None, target: str = None
    ) -> None:
        """
        이벤트 발행

        Args:
            event_type: 이벤트 타입
            data: 이벤트 데이터
            source: 이벤트 발행자
            target: 특정 대상 (None이면 모든 구독자)
        """

    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """
        이벤트 구독

        Args:
            event_type: 구독할 이벤트 타입
            handler: 이벤트 핸들러 함수
        """

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """
        이벤트 구독 해제

        Args:
            event_type: 구독 해제할 이벤트 타입
            handler: 해제할 핸들러 함수
        """

    @abstractmethod
    def clear_subscribers(self, event_type: str = None) -> None:
        """
        구독자 정리

        Args:
            event_type: 특정 이벤트 타입 (None이면 모든 구독자)
        """
