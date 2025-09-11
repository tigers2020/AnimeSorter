"""
GUI 어댑터 모듈

CoreBus와 Qt Signal/Slot 간의 브릿지 역할을 하는 어댑터들을 제공합니다.
"""

from .qt_event_adapter import QtEventAdapter

__all__ = ["QtEventAdapter"]
