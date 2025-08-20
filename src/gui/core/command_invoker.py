"""
명령 호출자 구현체

Command 패턴의 호출자 역할을 수행하는 클래스
"""

import logging
from typing import Any

from ..interfaces.i_command import CommandState, ICommand, ICommandInvoker


class CommandInvoker(ICommandInvoker):
    """
    명령 호출자 구현체

    명령 실행, 취소, 히스토리 관리 기능 제공
    """

    def __init__(self, max_history_size: int = 100):
        """
        초기화

        Args:
            max_history_size: 최대 히스토리 크기
        """
        self._command_history: list[ICommand] = []
        self._max_history_size = max_history_size
        self._current_position = -1
        self.logger = logging.getLogger(__name__)

        self.logger.info("CommandInvoker 초기화 완료")

    def execute_command(self, command: ICommand) -> Any:
        """
        명령 실행

        Args:
            command: 실행할 명령

        Returns:
            실행 결과

        Raises:
            RuntimeError: 명령 실행 불가능한 경우
        """
        try:
            # 실행 가능 여부 확인
            if not command.can_execute():
                raise RuntimeError(f"명령 실행 불가: {command.name}")

            self.logger.info(f"명령 실행 시작: {command.name}")

            # 명령 상태 업데이트
            command.state = CommandState.EXECUTING

            try:
                # 명령 실행
                result = command.execute()

                # 성공 시 상태 업데이트
                command.state = CommandState.COMPLETED
                command.result = result

                # 히스토리에 추가
                self._add_to_history(command)

                self.logger.info(f"명령 실행 완료: {command.name}")
                return result

            except Exception as e:
                # 실패 시 상태 업데이트
                command.state = CommandState.FAILED
                command.error = str(e)
                self.logger.error(f"명령 실행 실패: {command.name} - {e}")
                raise

        except Exception as e:
            self.logger.error(f"명령 실행 중 오류: {command.name} - {e}")
            raise

    def undo_last_command(self) -> Any:
        """
        마지막 명령 취소

        Returns:
            취소 결과

        Raises:
            RuntimeError: 취소할 명령이 없거나 취소 불가능한 경우
        """
        if self._current_position < 0:
            raise RuntimeError("취소할 명령이 없습니다")

        command = self._command_history[self._current_position]

        if not command.can_undo():
            raise RuntimeError(f"명령 취소 불가: {command.name}")

        try:
            self.logger.info(f"명령 취소 시작: {command.name}")

            result = command.undo()
            self._current_position -= 1

            self.logger.info(f"명령 취소 완료: {command.name}")
            return result

        except Exception as e:
            self.logger.error(f"명령 취소 실패: {command.name} - {e}")
            raise

    def redo_command(self) -> Any:
        """
        다시 실행

        Returns:
            실행 결과

        Raises:
            RuntimeError: 다시 실행할 명령이 없는 경우
        """
        if self._current_position + 1 >= len(self._command_history):
            raise RuntimeError("다시 실행할 명령이 없습니다")

        self._current_position += 1
        command = self._command_history[self._current_position]

        try:
            self.logger.info(f"명령 재실행 시작: {command.name}")

            command.reset()
            result = command.execute()
            command.state = CommandState.COMPLETED
            command.result = result

            self.logger.info(f"명령 재실행 완료: {command.name}")
            return result

        except Exception as e:
            command.state = CommandState.FAILED
            command.error = str(e)
            self.logger.error(f"명령 재실행 실패: {command.name} - {e}")
            raise

    def get_command_history(self) -> list[ICommand]:
        """
        명령 히스토리 가져오기

        Returns:
            명령 히스토리 리스트 (복사본)
        """
        return self._command_history.copy()

    def clear_history(self) -> None:
        """명령 히스토리 정리"""
        self._command_history.clear()
        self._current_position = -1
        self.logger.info("명령 히스토리 정리 완료")

    def can_undo(self) -> bool:
        """취소 가능 여부 확인"""
        if self._current_position < 0:
            return False
        command = self._command_history[self._current_position]
        return command.can_undo()

    def can_redo(self) -> bool:
        """재실행 가능 여부 확인"""
        return self._current_position + 1 < len(self._command_history)

    def get_current_command(self) -> ICommand | None:
        """현재 명령 가져오기"""
        if self._current_position < 0:
            return None
        return self._command_history[self._current_position]

    def get_next_command(self) -> ICommand | None:
        """다음 명령 가져오기"""
        if self._current_position + 1 >= len(self._command_history):
            return None
        return self._command_history[self._current_position + 1]

    def _add_to_history(self, command: ICommand) -> None:
        """히스토리에 명령 추가"""
        # 현재 위치 이후의 명령들 제거 (새로운 분기 생성)
        if self._current_position + 1 < len(self._command_history):
            self._command_history = self._command_history[: self._current_position + 1]

        # 새 명령 추가
        self._command_history.append(command)
        self._current_position += 1

        # 히스토리 크기 제한
        if len(self._command_history) > self._max_history_size:
            removed_count = len(self._command_history) - self._max_history_size
            self._command_history = self._command_history[removed_count:]
            self._current_position -= removed_count

    def get_stats(self) -> dict:
        """통계 정보 반환"""
        completed_count = sum(
            1 for cmd in self._command_history if cmd.state == CommandState.COMPLETED
        )
        failed_count = sum(1 for cmd in self._command_history if cmd.state == CommandState.FAILED)

        return {
            "total_commands": len(self._command_history),
            "completed_commands": completed_count,
            "failed_commands": failed_count,
            "current_position": self._current_position,
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo(),
        }
