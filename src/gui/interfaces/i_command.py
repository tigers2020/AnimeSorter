"""
명령 인터페이스

Command 패턴 구현을 위한 인터페이스 정의
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class CommandState(Enum):
    """명령 상태"""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ICommand(ABC):
    """명령 인터페이스"""

    def __init__(self, name: str, description: str = ""):
        """
        명령 초기화

        Args:
            name: 명령 이름
            description: 명령 설명
        """
        self.name = name
        self.description = description
        self.state = CommandState.PENDING
        self.result = None
        self.error = None
        self._parameters = {}

    @abstractmethod
    def execute(self) -> Any:
        """
        명령 실행

        Returns:
            실행 결과
        """

    @abstractmethod
    def can_execute(self) -> bool:
        """
        실행 가능 여부 확인

        Returns:
            실행 가능 여부
        """

    def undo(self) -> Any:
        """
        명령 취소 (기본 구현은 None)

        Returns:
            취소 결과
        """
        return None

    def can_undo(self) -> bool:
        """
        취소 가능 여부 확인

        Returns:
            취소 가능 여부
        """
        return False

    def set_parameter(self, key: str, value: Any) -> None:
        """
        매개변수 설정

        Args:
            key: 매개변수 키
            value: 매개변수 값
        """
        self._parameters[key] = value

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """
        매개변수 가져오기

        Args:
            key: 매개변수 키
            default: 기본값

        Returns:
            매개변수 값
        """
        return self._parameters.get(key, default)

    def reset(self) -> None:
        """명령 상태 초기화"""
        self.state = CommandState.PENDING
        self.result = None
        self.error = None


class ICommandInvoker(ABC):
    """명령 호출자 인터페이스"""

    @abstractmethod
    def execute_command(self, command: ICommand) -> Any:
        """
        명령 실행

        Args:
            command: 실행할 명령

        Returns:
            실행 결과
        """

    @abstractmethod
    def undo_last_command(self) -> Any:
        """
        마지막 명령 취소

        Returns:
            취소 결과
        """

    @abstractmethod
    def get_command_history(self) -> list:
        """
        명령 히스토리 가져오기

        Returns:
            명령 히스토리 리스트
        """
