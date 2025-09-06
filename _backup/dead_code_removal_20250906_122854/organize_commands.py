"""
파일 정리 관련 명령들

파일 정리 시작, 취소 등의 명령을 포함합니다.
"""

from .base_command import BaseCommand, CommandResult


class StartOrganizeCommand(BaseCommand):
    """파일 정리 시작 명령"""

    def __init__(self, event_bus, target_directory: str, selected_groups: list[str] = None):
        super().__init__(event_bus, "파일 정리 시작")
        self.target_directory = target_directory
        self.selected_groups = selected_groups or []
        self._previous_state = None

    def _execute_impl(self) -> CommandResult:
        """파일 정리 시작"""
        try:
            # 이벤트 버스에 파일 정리 시작 알림
            if self.event_bus:
                self.event_bus.publish(
                    "start_file_organization",
                    {
                        "target_directory": self.target_directory,
                        "selected_groups": self.selected_groups,
                    },
                )

            return CommandResult(success=True, message="파일 정리를 시작합니다.")

        except Exception as e:
            return CommandResult(success=False, message=f"파일 정리 시작 실패: {str(e)}", error=e)

    def can_execute(self) -> bool:
        """명령 실행 가능 여부 확인"""
        return bool(self.target_directory)  # 대상 디렉토리가 지정되어야 함

    def _save_state_for_undo(self):
        """실행 취소를 위한 상태 저장"""
        # 파일 정리 시작은 실행 취소 불가능
        self._can_undo = False
        self._undo_data = None


class CancelOrganizeCommand(BaseCommand):
    """파일 정리 취소 명령"""

    def __init__(self, event_bus):
        super().__init__(event_bus, "파일 정리 취소")

    def _execute_impl(self) -> CommandResult:
        """파일 정리 취소"""
        try:
            # 이벤트 버스에 파일 정리 취소 알림
            if self.event_bus:
                self.event_bus.publish("cancel_file_organization", None)

            return CommandResult(success=True, message="파일 정리를 취소합니다.")

        except Exception as e:
            return CommandResult(success=False, message=f"파일 정리 취소 실패: {str(e)}", error=e)

    def can_execute(self) -> bool:
        """명령 실행 가능 여부 확인"""
        return True  # 파일 정리 취소는 항상 가능

    def _save_state_for_undo(self):
        """실행 취소를 위한 상태 저장"""
        # 파일 정리 취소는 실행 취소 불가능
        self._can_undo = False
        self._undo_data = None
