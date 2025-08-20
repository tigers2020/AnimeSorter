"""
서비스 인터페이스

비즈니스 로직 서비스의 표준 인터페이스 정의
"""

from abc import abstractmethod
from typing import Any

from .i_event_bus import IEventBus


class IService:
    """서비스 기본 인터페이스"""

    def __init__(self, event_bus: IEventBus = None):
        """
        서비스 초기화

        Args:
            event_bus: 이벤트 버스 인스턴스
        """
        self.event_bus = event_bus
        self._is_running = False
        self._config = {}

    @abstractmethod
    def start(self) -> None:
        """서비스 시작"""

    @abstractmethod
    def stop(self) -> None:
        """서비스 중지"""

    @property
    def is_running(self) -> bool:
        """실행 상태 확인"""
        return self._is_running

    def configure(self, config: dict[str, Any]) -> None:
        """
        서비스 설정

        Args:
            config: 설정 딕셔너리
        """
        self._config.update(config)

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        설정 값 가져오기

        Args:
            key: 설정 키
            default: 기본값

        Returns:
            설정 값
        """
        return self._config.get(key, default)

    def set_running(self, running: bool) -> None:
        """실행 상태 설정 (보호된 메서드)"""
        self._is_running = running
