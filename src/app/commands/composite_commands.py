"""
복합 Command 구현

Phase 3: 여러 개의 단일 Command를 묶어서 원자적 작업으로 수행
스테이징 디렉토리와 JSONL 저널링을 통합하여 안전한 복합 작업 제공
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.app.journal import JournalEntryType
from src.app.commands.base_command import BaseCommand, CommandResult
from src.app.commands.file_commands import (CopyFileCommand, CreateDirectoryCommand,
                                         DeleteFileCommand, MoveFileCommand,
                                         RenameFileCommand)


@dataclass
class BatchOperationConfig:
    """배치 작업 설정"""

    # 실행 설정
    continue_on_error: bool = False
    max_parallel_operations: int = 1
    retry_failed_operations: bool = True
    max_retry_attempts: int = 3

    # 스테이징 설정
    stage_all_files_first: bool = True
    cleanup_staging_on_failure: bool = True

    # 저널링 설정
    create_individual_entries: bool = True
    create_summary_entry: bool = True

    # 진행 상황 추적
    progress_callback: Callable[[int, int, str], None] | None = None
    status_callback: Callable[[str, str], None] | None = None


class BatchFileOperationCommand(BaseCommand):
    """배치 파일 작업을 위한 복합 Command"""

    def __init__(
        self,
        operations: list[dict[str, Any]],
        config: BatchOperationConfig | None = None,
        description: str = "",
    ):
        super().__init__(description or "배치 파일 작업")

        self.operations = operations
        self.config = config or BatchOperationConfig()

        # 실행 상태
        self._executed_commands: list[BaseCommand] = []
        self._failed_operations: list[dict[str, Any]] = []
        self._successful_operations: list[dict[str, Any]] = []

        # 진행 상황
        self._total_operations = len(operations)
        self._completed_operations = 0
        self._current_operation = ""

        self.logger.info(f"배치 파일 작업 Command 생성: {self._total_operations}개 작업")

    def _get_default_description(self) -> str:
        return f"배치 파일 작업 ({self._total_operations}개 작업)"

    def _get_staging_paths(self) -> list[tuple[Path, str]]:
        """모든 작업의 스테이징 대상 경로 수집"""
        if not self.config.stage_all_files_first:
            return []

        staging_paths = []
        for operation in self.operations:
            try:
                source_path = Path(operation.get("source_path", ""))
                operation_type = operation.get("operation_type", "unknown")

                if source_path.exists():
                    staging_paths.append((source_path, operation_type))

            except Exception as e:
                self.logger.warning(f"스테이징 경로 수집 실패: {operation} - {e}")
                continue

        return staging_paths

    def _get_journal_info(self) -> tuple[JournalEntryType, Any] | None:
        """저널 정보 (배치 작업용)"""
        from src.app.journal import JournalEntryType

        # 배치 작업 요약 정보
        summary_details = {
            "total_operations": self._total_operations,
            "operation_types": list(
                {op.get("operation_type", "unknown") for op in self.operations}
            ),
            "batch_id": str(self.command_id),
            "batch_description": self.description,
        }

        return JournalEntryType.BATCH_OPERATION, summary_details

    def _execute_impl(self) -> None:
        """배치 작업 실행"""
        self.logger.info(f"배치 작업 시작: {self._total_operations}개 작업")

        # 진행 상황 초기화
        self._completed_operations = 0
        self._failed_operations.clear()
        self._successful_operations.clear()

        # 상태 콜백 호출
        if self.config.status_callback:
            self.config.status_callback(
                "started", f"배치 작업 시작: {self._total_operations}개 작업"
            )

        try:
            # 각 작업을 순차적으로 실행
            for i, operation in enumerate(self.operations):
                try:
                    self._current_operation = f"작업 {i + 1}/{self._total_operations}: {operation.get('operation_type', 'unknown')}"

                    # 진행 상황 콜백 호출
                    if self.config.progress_callback:
                        self.config.progress_callback(
                            i, self._total_operations, self._current_operation
                        )

                    # 개별 Command 생성 및 실행
                    command = self._create_command_for_operation(operation)
                    if command:
                        # 스테이징 및 저널링 매니저 설정
                        if self._staging_manager:
                            command.set_staging_manager(self._staging_manager)
                        if self._journal_manager:
                            command.set_journal_manager(self._journal_manager)

                        # Command 실행
                        result = command.execute()
                        self._executed_commands.append(command)

                        if result.is_success:
                            self._successful_operations.append(operation)
                            self._integrate_command_result(result)
                            self.logger.debug(
                                f"작업 성공: {operation.get('operation_type', 'unknown')}"
                            )
                        else:
                            self._failed_operations.append(operation)
                            error_msg = result.error.message if result.error else "알 수 없는 오류"
                            self.logger.warning(
                                f"작업 실패: {operation.get('operation_type', 'unknown')} - {error_msg}"
                            )

                            if not self.config.continue_on_error:
                                raise RuntimeError(f"작업 실패로 중단: {error_msg}")
                    else:
                        self.logger.warning(f"작업을 위한 Command 생성 실패: {operation}")
                        self._failed_operations.append(operation)

                except Exception as e:
                    self.logger.error(f"작업 실행 중 오류: {operation} - {e}")
                    self._failed_operations.append(operation)

                    if not self.config.continue_on_error:
                        raise

                finally:
                    self._completed_operations += 1

            # 최종 결과 설정
            self._set_batch_result()

            # 성공 콜백 호출
            if self.config.status_callback:
                self.config.status_callback(
                    "completed",
                    f"배치 작업 완료: {len(self._successful_operations)}개 성공, {len(self._failed_operations)}개 실패",
                )

            self.logger.info(
                f"배치 작업 완료: {len(self._successful_operations)}개 성공, {len(self._failed_operations)}개 실패"
            )

        except Exception as e:
            # 실패 시 스테이징 정리
            if self.config.cleanup_staging_on_failure:
                self._cleanup_staging_on_failure()

            # 실패 콜백 호출
            if self.config.status_callback:
                self.config.status_callback("failed", f"배치 작업 실패: {e}")

            raise

    def _create_command_for_operation(self, operation: dict[str, Any]) -> BaseCommand | None:
        """작업에 맞는 Command 생성"""
        try:
            operation_type = operation.get("operation_type", "")
            source_path = Path(operation.get("source_path", ""))
            destination_path = operation.get("destination_path")

            if operation_type == "move":
                return MoveFileCommand(
                    source=source_path,
                    destination=Path(destination_path) if destination_path else source_path,
                )

            if operation_type == "copy":
                return CopyFileCommand(
                    source=source_path,
                    destination=Path(destination_path) if destination_path else source_path,
                )

            if operation_type == "delete":
                return DeleteFileCommand(file_path=source_path)

            if operation_type == "rename":
                new_name = operation.get("new_name", "")
                if new_name:
                    return RenameFileCommand(
                        file_path=source_path,
                        new_name=new_name,
                    )

                elif operation_type == "create_directory":
                    return CreateDirectoryCommand(directory_path=source_path)

            else:
                self.logger.warning(f"지원하지 않는 작업 타입: {operation_type}")
                return None

        except Exception as e:
            self.logger.error(f"Command 생성 실패: {operation} - {e}")
            return None

    def _integrate_command_result(self, result: CommandResult):
        """Command 결과를 배치 결과에 통합"""
        if not self._result:
            return

        # 파일 목록 통합
        self._result.affected_files.extend(result.affected_files)
        self._result.created_files.extend(result.created_files)
        self._result.deleted_files.extend(result.deleted_files)
        self._result.modified_files.extend(result.modified_files)

        # Phase 3: 스테이징 정보 통합
        if hasattr(result, "staged_files") and result.staged_files:
            self._result.staged_files.extend(result.staged_files)

        # 스테이징 디렉토리 설정 (첫 번째 결과에서)
        if (
            not self._result.staging_directory
            and hasattr(result, "staging_directory")
            and result.staging_directory
        ):
            self._result.staging_directory = result.staging_directory

    def _set_batch_result(self):
        """배치 작업 결과 설정"""
        if not self._result:
            return

        # 메타데이터 설정
        self._result.metadata.update(
            {
                "batch_total_operations": self._total_operations,
                "batch_successful_operations": len(self._successful_operations),
                "batch_failed_operations": len(self._failed_operations),
                "batch_success_rate": (
                    len(self._successful_operations) / self._total_operations
                    if self._total_operations > 0
                    else 0
                ),
                "batch_failed_operations_details": self._failed_operations,
                "batch_execution_mode": (
                    "continue_on_error" if self.config.continue_on_error else "stop_on_error"
                ),
            }
        )

    def _cleanup_staging_on_failure(self):
        """실패 시 스테이징 정리"""
        try:
            if not self._staging_manager:
                return

            # 실행된 Command들의 스테이징 파일 정리
            for command in self._executed_commands:
                if hasattr(command, "result") and command.result:
                    result = command.result
                    if hasattr(result, "staged_files") and result.staged_files:
                        for staged_file in result.staged_files:
                            try:
                                if staged_file.staging_path.exists():
                                    if staged_file.staging_path.is_file():
                                        staged_file.staging_path.unlink()
                                    elif staged_file.staging_path.is_dir():
                                        import shutil

                                        shutil.rmtree(staged_file.staging_path)
                            except Exception as e:
                                self.logger.warning(
                                    f"스테이징 파일 정리 실패: {staged_file.staging_path} - {e}"
                                )

            self.logger.info("실패 시 스테이징 파일 정리 완료")

        except Exception as e:
            self.logger.error(f"스테이징 정리 중 오류: {e}")

    def _undo_impl(self) -> None:
        """배치 작업 취소 (역순으로 실행된 Command들 취소)"""
        self.logger.info("배치 작업 취소 시작")

        try:
            for command in reversed(self._executed_commands):
                if command.can_undo:
                    command.undo()
                    self.logger.debug(f"Command 취소 완료: {command.description}")
                else:
                    self.logger.warning(f"취소할 수 없는 Command: {command.description}")

            self.logger.info("배치 작업 취소 완료")

        except Exception as e:
            self.logger.error(f"배치 작업 취소 중 오류: {e}")
            raise

    def validate(self) -> bool:
        """배치 작업 유효성 검사"""
        try:
            # 기본 검사
            if not self.operations:
                self.logger.error("작업 목록이 비어있습니다")
                return False

            # 각 작업의 기본 유효성 검사
            for i, operation in enumerate(self.operations):
                if not self._validate_operation(operation):
                    self.logger.error(f"작업 {i + 1} 유효성 검사 실패: {operation}")
                    return False

            self.logger.debug("배치 작업 유효성 검사 통과")
            return True

        except Exception as e:
            self.logger.error(f"배치 작업 유효성 검사 중 오류: {e}")
            return False

    def _validate_operation(self, operation: dict[str, Any]) -> bool:
        """개별 작업 유효성 검사"""
        try:
            # 필수 필드 확인
            if "operation_type" not in operation:
                return False

            if "source_path" not in operation:
                return False

            # 작업 타입별 추가 검사
            operation_type = operation["operation_type"]
            source_path = Path(operation["source_path"])

            if operation_type in ["move", "copy"] and "destination_path" not in operation:
                return False

            if operation_type == "rename" and "new_name" not in operation:
                return False

            # 경로 유효성 검사
            if not source_path.exists():
                self.logger.warning(f"소스 경로가 존재하지 않음: {source_path}")
                # 경고만 하고 계속 진행 (실제 실행 시 처리)

            return True

        except Exception as e:
            self.logger.error(f"작업 유효성 검사 실패: {operation} - {e}")
            return False

    def get_progress(self) -> dict[str, Any]:
        """진행 상황 반환"""
        return {
            "total_operations": self._total_operations,
            "completed_operations": self._completed_operations,
            "successful_operations": len(self._successful_operations),
            "failed_operations": len(self._failed_operations),
            "current_operation": self._current_operation,
            "progress_percentage": (
                (self._completed_operations / self._total_operations * 100)
                if self._total_operations > 0
                else 0
            ),
        }


class ConditionalCommand(BaseCommand):
    """조건부 실행을 위한 복합 Command"""

    def __init__(
        self,
        condition_command: BaseCommand,
        success_command: BaseCommand,
        failure_command: BaseCommand | None = None,
        description: str = "",
    ):
        super().__init__(description or "조건부 실행")

        self.condition_command = condition_command
        self.success_command = success_command
        self.failure_command = failure_command

        self._condition_result: bool | None = None
        self._executed_command: BaseCommand | None = None

        self.logger.info("조건부 실행 Command 생성")

    def _get_default_description(self) -> str:
        return f"조건부 실행: {self.condition_command.description}"

    def _get_staging_paths(self) -> list[tuple[Path, str]]:
        """조건부 Command의 스테이징 경로 수집"""
        staging_paths = []

        # 조건 Command의 스테이징 경로
        if hasattr(self.condition_command, "_get_staging_paths"):
            staging_paths.extend(self.condition_command._get_staging_paths())

        # 성공/실패 Command의 스테이징 경로 (미리 수집)
        if hasattr(self.success_command, "_get_staging_paths"):
            staging_paths.extend(self.success_command._get_staging_paths())

        if self.failure_command and hasattr(self.failure_command, "_get_staging_paths"):
            staging_paths.extend(self.failure_command._get_staging_paths())

        return staging_paths

    def _execute_impl(self) -> None:
        """조건부 실행"""
        self.logger.info("조건부 실행 시작")

        try:
            # 1. 조건 Command 실행
            self.logger.debug("조건 Command 실행")
            condition_result = self.condition_command.execute()

            if not condition_result.is_success:
                raise RuntimeError(f"조건 Command 실행 실패: {condition_result.error}")

            # 2. 조건 결과 확인
            self._condition_result = self._evaluate_condition(condition_result)
            self.logger.info(f"조건 평가 결과: {self._condition_result}")

            # 3. 적절한 Command 실행
            if self._condition_result:
                self.logger.debug("성공 Command 실행")
                self._executed_command = self.success_command
                result = self.success_command.execute()
            else:
                if self.failure_command:
                    self.logger.debug("실패 Command 실행")
                    self._executed_command = self.failure_command
                    result = self.failure_command.execute()
                else:
                    self.logger.debug("실패 시 아무 작업도 수행하지 않음")
                    return

            # 4. 결과 통합
            if result and result.is_success:
                self._integrate_command_result(result)
                self.logger.info("조건부 실행 완료")
            else:
                error_msg = result.error.message if result and result.error else "알 수 없는 오류"
                raise RuntimeError(f"실행 Command 실패: {error_msg}")

        except Exception as e:
            self.logger.error(f"조건부 실행 중 오류: {e}")
            raise

    def _evaluate_condition(self, condition_result: CommandResult) -> bool:
        """조건 결과 평가"""
        # 기본적으로 Command가 성공하면 True
        if condition_result.is_success:
            return True

        # 메타데이터에 조건 평가 로직이 있으면 사용
        condition_logic = condition_result.metadata.get("condition_logic", "")
        if condition_logic == "file_exists":
            return len(condition_result.affected_files) > 0
        if condition_logic == "file_count":
            expected_count = condition_result.metadata.get("expected_count", 0)
            return len(condition_result.affected_files) == expected_count
        if condition_logic == "file_size":
            min_size = condition_result.metadata.get("min_size", 0)
            return any(
                f.stat().st_size >= min_size for f in condition_result.affected_files if f.exists()
            )

        # 기본값
        return False

    def _integrate_command_result(self, result: CommandResult):
        """실행된 Command의 결과를 통합"""
        if not self._result:
            return

        # 파일 목록 통합
        self._result.affected_files.extend(result.affected_files)
        self._result.created_files.extend(result.created_files)
        self._result.deleted_files.extend(result.deleted_files)
        self._result.modified_files.extend(result.modified_files)

        # Phase 3: 스테이징 정보 통합
        if hasattr(result, "staged_files") and result.staged_files:
            self._result.staged_files.extend(result.staged_files)

        # 스테이징 디렉토리 설정
        if (
            not self._result.staging_directory
            and hasattr(result, "staging_directory")
            and result.staging_directory
        ):
            self._result.staging_directory = result.staging_directory

        # 메타데이터 통합
        self._result.metadata.update(
            {
                "condition_result": self._condition_result,
                "executed_command_type": "success" if self._condition_result else "failure",
                "condition_command_id": str(self.condition_command.command_id),
            }
        )

    def _undo_impl(self) -> None:
        """조건부 실행 취소"""
        self.logger.info("조건부 실행 취소 시작")

        try:
            # 실행된 Command 취소
            if self._executed_command and self._executed_command.can_undo:
                self._executed_command.undo()
                self.logger.debug(f"실행 Command 취소 완료: {self._executed_command.description}")

            # 조건 Command 취소
            if self.condition_command.can_undo:
                self.condition_command.undo()
                self.logger.debug("조건 Command 취소 완료")

            self.logger.info("조건부 실행 취소 완료")

        except Exception as e:
            self.logger.error(f"조건부 실행 취소 중 오류: {e}")
            raise

    def validate(self) -> bool:
        """조건부 실행 유효성 검사"""
        try:
            # 기본 Command들 유효성 검사
            if not self.condition_command.validate():
                return False

            if not self.success_command.validate():
                return False

            return not (self.failure_command and not self.failure_command.validate())

        except Exception as e:
            self.logger.error(f"조건부 실행 유효성 검사 중 오류: {e}")
            return False
