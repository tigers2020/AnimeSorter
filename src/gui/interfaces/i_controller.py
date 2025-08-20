"""
컨트롤러 인터페이스

UI 컨트롤러의 표준 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import Any
from .i_event_bus import IEventBus, Event


class IController:
    """컨트롤러 기본 인터페이스"""
    
    def __init__(self, event_bus: IEventBus = None):
        """
        컨트롤러 초기화
        
        Args:
            event_bus: 이벤트 버스 인스턴스
        """
        self.event_bus = event_bus
        self._is_initialized = False
        self._is_active = False
    
    @abstractmethod
    def initialize(self) -> None:
        """컨트롤러 초기화"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """리소스 정리"""
        pass
    
    @abstractmethod
    def handle_event(self, event: Event) -> None:
        """
        이벤트 처리
        
        Args:
            event: 처리할 이벤트
        """
        pass
    
    def activate(self) -> None:
        """컨트롤러 활성화"""
        if not self._is_initialized:
            self.initialize()
            self._is_initialized = True
        self._is_active = True
    
    def deactivate(self) -> None:
        """컨트롤러 비활성화"""
        self._is_active = False
    
    @property
    def is_active(self) -> bool:
        """활성 상태 확인"""
        return self._is_active
    
    @property
    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        return self._is_initialized
