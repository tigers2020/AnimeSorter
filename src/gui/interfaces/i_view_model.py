"""
뷰모델 인터페이스

MVVM 패턴의 뷰모델 표준 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable
from PyQt5.QtCore import QObject, pyqtSignal
from .i_event_bus import IEventBus, Event


class IViewModel:
    """뷰모델 기본 인터페이스"""
    
    # 공통 시그널
    property_changed = pyqtSignal(str, object)  # (property_name, new_value)
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, event_bus: IEventBus = None, parent=None):
        """
        뷰모델 초기화
        
        Args:
            event_bus: 이벤트 버스 인스턴스
            parent: 부모 QObject
        """
        self.event_bus = event_bus
        self._properties = {}
        self._property_validators = {}
        self._is_initialized = False
    
    @abstractmethod
    def initialize(self) -> None:
        """뷰모델 초기화"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """리소스 정리"""
        pass
    
    def get_property(self, name: str, default: Any = None) -> Any:
        """
        속성 값 가져오기
        
        Args:
            name: 속성 이름
            default: 기본값
            
        Returns:
            속성 값
        """
        return self._properties.get(name, default)
    
    def set_property(self, name: str, value: Any, validate: bool = True) -> bool:
        """
        속성 값 설정
        
        Args:
            name: 속성 이름
            value: 새 값
            validate: 유효성 검사 여부
            
        Returns:
            설정 성공 여부
        """
        if validate and name in self._property_validators:
            validator = self._property_validators[name]
            if not validator(value):
                self.error_occurred.emit(f"Invalid value for property '{name}': {value}")
                return False
        
        old_value = self._properties.get(name)
        if old_value != value:
            self._properties[name] = value
            self.property_changed.emit(name, value)
            self.on_property_changed(name, value, old_value)
        
        return True
    
    def register_validator(self, property_name: str, validator: Callable[[Any], bool]) -> None:
        """
        속성 유효성 검사기 등록
        
        Args:
            property_name: 속성 이름
            validator: 유효성 검사 함수
        """
        self._property_validators[property_name] = validator
    
    def on_property_changed(self, name: str, new_value: Any, old_value: Any) -> None:
        """
        속성 변경 시 호출되는 메서드 (오버라이드 가능)
        
        Args:
            name: 속성 이름
            new_value: 새 값
            old_value: 이전 값
        """
        pass
    
    def handle_event(self, event: Event) -> None:
        """
        이벤트 처리 (기본 구현)
        
        Args:
            event: 처리할 이벤트
        """
        pass
    
    @property
    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        return self._is_initialized
