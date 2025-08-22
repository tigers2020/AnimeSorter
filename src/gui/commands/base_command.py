"""
기본 명령 클래스

명령 패턴의 기본 구조를 제공하는 추상 클래스
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from gui.interfaces.i_command import ICommand
from gui.interfaces.i_event_bus import IEventBus


@dataclass
class CommandResult:
    """명령 실행 결과"""

    success: bool
    message: str
    data: Any | None = None
    error: Exception | None = None
    execution_time: float | None = None


class BaseCommand(ICommand, ABC):
    """기본 명령 클래스"""

    def __init__(self, event_bus: IEventBus, name: str = None):
        """
        명령 초기화

        Args:
            event_bus: 이벤트 버스 인스턴스
            name: 명령 이름
        """
        self.event_bus = event_bus
        self.name = name or self.__class__.__name__
        self.executed_at: datetime | None = None
        self.execution_time: float | None = None
        self._can_undo = False
        self._undo_data: dict[str, Any] | None = None

    @property
    def can_undo(self) -> bool:
        """실행 취소 가능 여부"""
        return self._can_undo

    @property
    def is_executed(self) -> bool:
        """실행되었는지 확인"""
        return self.executed_at is not None

    def execute(self) -> CommandResult:
        """
        명령 실행

        Returns:
            실행 결과
        """
        start_time = datetime.now()

        try:
            # 실행 전 상태 저장 (실행 취소용)
            self._save_state_for_undo()

            # 실제 실행
            result = self._execute_impl()

            # 실행 시간 기록
            self.executed_at = datetime.now()
            self.execution_time = (self.executed_at - start_time).total_seconds()

            # 결과에 실행 시간 추가
            result.execution_time = self.execution_time

            # 이벤트 버스에 실행 완료 알림
            if self.event_bus:
                self.event_bus.publish(
                    "command_executed",
                    {
                        "command_name": self.name,
                        "success": result.success,
                        "execution_time": self.execution_time,
                    },
                )

            return result

        except Exception as e:
            # 오류 발생 시 실행 취소 데이터 정리
            self._undo_data = None
            self._can_undo = False

            error_result = CommandResult(
                success=False,
                message=f"명령 실행 실패: {str(e)}",
                error=e,
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

            # 이벤트 버스에 오류 알림
            if self.event_bus:
                self.event_bus.publish(
                    "command_failed",
                    {
                        "command_name": self.name,
                        "error": str(e),
                        "execution_time": error_result.execution_time,
                    },
                )

            return error_result

    def undo(self) -> CommandResult:
        """
        명령 실행 취소

        Returns:
            실행 취소 결과
        """
        if not self._can_undo or not self._undo_data:
            return CommandResult(success=False, message="실행 취소할 수 없습니다.")

        try:
            # 실행 취소 구현
            result = self._undo_impl()

            # 실행 취소 후 상태 정리
            self.executed_at = None
            self.execution_time = None
            self._undo_data = None
            self._can_undo = False

            # 이벤트 버스에 실행 취소 알림
            if self.event_bus:
                self.event_bus.publish("command_undone", {"command_name": self.name})

            return result

        except Exception as e:
            return CommandResult(success=False, message=f"실행 취소 실패: {str(e)}", error=e)

    @abstractmethod
    def _execute_impl(self) -> CommandResult:
        """
        실제 명령 실행 구현

        Returns:
            실행 결과
        """

    def _undo_impl(self) -> CommandResult:
        """
        실행 취소 구현 (기본 구현)

        Returns:
            실행 취소 결과
        """
        return CommandResult(success=True, message=f"{self.name} 실행 취소 완료")

    def _save_state_for_undo(self):
        """실행 취소를 위한 상태 저장"""
        # 기본 구현: 실행 취소 불가능
        self._can_undo = False
        self._undo_data = None

    def get_execution_info(self) -> dict[str, Any]:
        """실행 정보 반환"""
        return {
            "name": self.name,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "execution_time": self.execution_time,
            "can_undo": self._can_undo,
            "is_executed": self.is_executed,
        }

    def __str__(self) -> str:
        return f"{self.name} (실행됨: {self.is_executed}, 취소가능: {self.can_undo})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}' executed={self.is_executed}>"
