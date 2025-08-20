"""
GUI 인터페이스 모듈

컴포넌트 간 표준 인터페이스 정의
"""

from .i_event_bus import IEventBus
from .i_controller import IController
from .i_service import IService
from .i_view_model import IViewModel
from .i_command import ICommand

__all__ = [
    'IEventBus',
    'IController', 
    'IService',
    'IViewModel',
    'ICommand'
]
