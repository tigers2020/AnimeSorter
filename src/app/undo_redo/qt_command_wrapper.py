"""
Qt Command 래퍼

기존 Command 패턴을 QUndoCommand로 래핑하여 QUndoStack과 호환
"""

import logging
from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import QUndoCommand

from ..commands import (BatchFileCommand, CommandResult, CopyFileCommand,
                        CreateDirectoryCommand, DeleteFileCommand, ICommand,
                        MoveFileCommand)


class QtCommandWrapper(QUndoCommand):
    """기본 Qt Command 래퍼"""

    def __init__(self, base_command: ICommand, parent: QUndoCommand | None = None):
        # QUndoCommand에서 표시할 텍스트 설정
        super().__init__(base_command.description, parent)

        self.base_command = base_command
        self.logger = logging.getLogger(f"QtWrapper[{base_command.__class__.__name__}]")

        # 실행 결과
        self._execute_result: CommandResult | None = None
        self._undo_result: CommandResult | None = None
        self._redo_result: CommandResult | None = None

        # 실행 상태
        self._executed = False
        self._undone = False

        self.logger.debug(f"Qt 래퍼 생성: {base_command.description}")

    def redo(self) -> None:
        """실행 또는 재실행"""
        try:
            if not self._executed:
                # 최초 실행
                self.logger.info(f"최초 실행: {self.base_command.description}")
                self._execute_result = self.base_command.execute()
                self._executed = True

                if not self._execute_result.is_success:
                    raise RuntimeError(f"Command 실행 실패: {self._execute_result.error}")

            else:
                # 재실행 (Redo)
                self.logger.info(f"재실행: {self.base_command.description}")

                if not self.base_command.can_redo:
                    raise RuntimeError("재실행할 수 없는 Command입니다")

                self._redo_result = self.base_command.redo()

                if not self._redo_result or not self._redo_result.is_success:
                    error_msg = (
                        self._redo_result.error
                        if self._redo_result and self._redo_result.error
                        else "알 수 없는 오류"
                    )
                    raise RuntimeError(f"Command 재실행 실패: {error_msg}")

            self._undone = False
            self.logger.debug("실행/재실행 성공")

        except Exception as e:
            self.logger.error(f"실행/재실행 실패: {e}")
            raise

    def undo(self) -> None:
        """취소"""
        try:
            if not self._executed:
                raise RuntimeError("실행되지 않은 Command는 취소할 수 없습니다")

            if self._undone:
                raise RuntimeError("이미 취소된 Command입니다")

            self.logger.info(f"취소: {self.base_command.description}")

            if not self.base_command.can_undo:
                raise RuntimeError("취소할 수 없는 Command입니다")

            self._undo_result = self.base_command.undo()

            if not self._undo_result or not self._undo_result.is_success:
                error_msg = (
                    self._undo_result.error
                    if self._undo_result and self._undo_result.error
                    else "알 수 없는 오류"
                )
                raise RuntimeError(f"Command 취소 실패: {error_msg}")

            self._undone = True
            self.logger.debug("취소 성공")

        except Exception as e:
            self.logger.error(f"취소 실패: {e}")
            raise

    @property
    def is_executed(self) -> bool:
        """실행 여부"""
        return self._executed

    @property
    def is_undone(self) -> bool:
        """취소 여부"""
        return self._undone

    @property
    def execute_result(self) -> CommandResult | None:
        """실행 결과"""
        return self._execute_result

    @property
    def undo_result(self) -> CommandResult | None:
        """취소 결과"""
        return self._undo_result

    @property
    def redo_result(self) -> CommandResult | None:
        """재실행 결과"""
        return self._redo_result

    def get_summary(self) -> dict[str, Any]:
        """Command 요약 정보"""
        return {
            "command_type": self.base_command.__class__.__name__,
            "description": self.base_command.description,
            "executed": self._executed,
            "undone": self._undone,
            "can_undo": self.base_command.can_undo,
            "can_redo": self.base_command.can_redo,
            "execute_success": self._execute_result.is_success if self._execute_result else None,
            "undo_success": self._undo_result.is_success if self._undo_result else None,
            "redo_success": self._redo_result.is_success if self._redo_result else None,
        }


class QtMoveFileCommand(QtCommandWrapper):
    """파일 이동 Qt Command"""

    def __init__(
        self,
        source: str | Path,
        destination: str | Path,
        create_dirs: bool = True,
        overwrite: bool = False,
        parent: QUndoCommand | None = None,
    ):
        base_command = MoveFileCommand(source, destination, create_dirs, overwrite)
        super().__init__(base_command, parent)

        # 더 자세한 설명 설정
        self.setText(f"파일 이동: {Path(source).name} → {Path(destination).parent.name}")


class QtCopyFileCommand(QtCommandWrapper):
    """파일 복사 Qt Command"""

    def __init__(
        self,
        source: str | Path,
        destination: str | Path,
        create_dirs: bool = True,
        overwrite: bool = False,
        parent: QUndoCommand | None = None,
    ):
        base_command = CopyFileCommand(source, destination, create_dirs, overwrite)
        super().__init__(base_command, parent)

        self.setText(f"파일 복사: {Path(source).name} → {Path(destination).parent.name}")


class QtDeleteFileCommand(QtCommandWrapper):
    """파일 삭제 Qt Command"""

    def __init__(
        self,
        file_path: str | Path,
        use_trash: bool = True,
        parent: QUndoCommand | None = None,
    ):
        base_command = DeleteFileCommand(file_path, use_trash)
        super().__init__(base_command, parent)

        delete_type = "휴지통으로" if use_trash else "영구"
        self.setText(f"파일 삭제 ({delete_type}): {Path(file_path).name}")


class QtRenameFileCommand(QtCommandWrapper):
    """파일 이름변경 Qt Command"""

    def __init__(self, old_path: str | Path, new_name: str, parent: QUndoCommand | None = None):
        old_path = Path(old_path)
        new_path = old_path.parent / new_name

        base_command = MoveFileCommand(old_path, new_path, create_dirs=False, overwrite=False)
        super().__init__(base_command, parent)

        self.setText(f"파일 이름변경: {old_path.name} → {new_name}")


class QtCreateDirectoryCommand(QtCommandWrapper):
    """디렉토리 생성 Qt Command"""

    def __init__(
        self,
        directory_path: str | Path,
        parents: bool = True,
        parent: QUndoCommand | None = None,
    ):
        base_command = CreateDirectoryCommand(directory_path, parents)
        super().__init__(base_command, parent)

        self.setText(f"디렉토리 생성: {Path(directory_path).name}")


class QtBatchFileCommand(QtCommandWrapper):
    """배치 파일 조작 Qt Command"""

    def __init__(
        self,
        commands: list[ICommand],
        description: str = "",
        parent: QUndoCommand | None = None,
    ):
        base_command = BatchFileCommand(commands, description)
        super().__init__(base_command, parent)

        if not description:
            description = f"배치 작업 ({len(commands)}개)"

        self.setText(description)

    def merge_with(self, other: QUndoCommand) -> bool:
        """
        연속된 배치 작업 병합

        QUndoStack은 연속된 동일한 타입의 작업을 자동으로 병합할 수 있습니다.
        """
        if not isinstance(other, QtBatchFileCommand):
            return False

        # 같은 타입의 배치 작업이고 시간이 가까우면 병합
        base_batch = self.base_command
        other_batch = other.base_command

        if (
            isinstance(base_batch, BatchFileCommand)
            and isinstance(other_batch, BatchFileCommand)
            and other_batch._result
            and base_batch._result
            and other_batch._result.executed_at is not None
            and base_batch._result.executed_at is not None
            and abs(
                (other_batch._result.executed_at - base_batch._result.executed_at).total_seconds()
            )
            < 5
        ):
            # 다른 배치의 Command들을 현재 배치에 추가
            base_batch.commands.extend(other_batch.commands)

            # 설명 업데이트
            total_commands = len(base_batch.commands)
            self.setText(f"배치 작업 ({total_commands}개)")

            self.logger.debug(f"배치 작업 병합: {total_commands}개 Command")
            return True

        return False
