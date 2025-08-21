"""
Command 패턴 기본 구현

안전한 파일 조작을 위한 Command 인터페이스와 기본 클래스
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Protocol
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from ..journal import FileOperationDetails, IJournalManager, JournalEntry, JournalEntryType
    from ..preflight import IPreflightCoordinator, PreflightCheckResult
    from ..staging import IStagingManager, StagedFile


class CommandStatus(Enum):
    """Command 실행 상태"""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    UNDONE = "undone"
    CANCELLED = "cancelled"


@dataclass
class CommandError:
    """Command 실행 중 발생한 오류"""

    error_type: str
    message: str
    details: str | None = None
    exception: Exception | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CommandResult:
    """Command 실행 결과 (Phase 3: 스테이징 + JSONL 저널링 통합)"""

    command_id: UUID
    status: CommandStatus
    executed_at: datetime | None = None
    completed_at: datetime | None = None
    execution_time_ms: float | None = None

    # 결과 데이터
    affected_files: list[Path] = field(default_factory=list)
    created_files: list[Path] = field(default_factory=list)
    deleted_files: list[Path] = field(default_factory=list)
    modified_files: list[Path] = field(default_factory=list)

    # Phase 3: 스테이징 정보
    staged_files: list["StagedFile"] = field(default_factory=list)
    staging_directory: Path | None = None

    # 오류 정보
    error: CommandError | None = None

    # 메타데이터
    metadata: dict[str, Any] = field(default_factory=dict)

    # 프리플라이트 검사 결과
    preflight_result: Optional["PreflightCheckResult"] = None

    # 저널 엔트리 ID
    journal_entry_id: UUID | None = None

    @property
    def is_success(self) -> bool:
        """실행 성공 여부"""
        return self.status in (CommandStatus.COMPLETED, CommandStatus.UNDONE)

    @property
    def is_failed(self) -> bool:
        """실행 실패 여부"""
        return self.status == CommandStatus.FAILED

    @property
    def can_undo(self) -> bool:
        """취소 가능 여부"""
        return self.status in (CommandStatus.COMPLETED, CommandStatus.UNDONE)


class ICommand(Protocol):
    """Command 인터페이스"""

    @property
    def command_id(self) -> UUID:
        """Command 고유 ID"""
        ...

    @property
    def description(self) -> str:
        """Command 설명 (UI 표시용)"""
        ...

    @property
    def can_undo(self) -> bool:
        """취소 가능 여부"""
        ...

    def execute(self) -> CommandResult:
        """Command 실행"""
        ...

    def undo(self) -> CommandResult:
        """Command 취소"""
        ...

    def validate(self) -> bool:
        """실행 전 유효성 검사"""
        ...


class BaseCommand(ABC):
    """Command 기본 클래스"""

    def __init__(
        self,
        description: str = "",
        skip_preflight: bool = False,
        enable_journaling: bool = True,
        enable_staging: bool = True,
    ):
        self._command_id: UUID = uuid4()
        self._description = description
        self.skip_preflight = skip_preflight
        self.enable_journaling = enable_journaling
        self.enable_staging = enable_staging  # Phase 3: 스테이징 활성화
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{self._command_id.hex[:8]}]")

        # 실행 상태
        self._result: CommandResult | None = None
        self._undo_data: dict[str, Any] = {}
        self._preflight_coordinator: IPreflightCoordinator | None = None
        self._journal_manager: IJournalManager | None = None
        self._staging_manager: IStagingManager | None = None  # Phase 3: 스테이징 매니저
        self._journal_entry: JournalEntry | None = None

    @property
    def command_id(self) -> UUID:
        return self._command_id

    @property
    def description(self) -> str:
        return self._description or self._get_default_description()

    @property
    def result(self) -> CommandResult | None:
        return self._result

    @property
    def can_undo(self) -> bool:
        """기본적으로 성공한 Command는 취소 가능"""
        return self._result is not None and self._result.is_success and self._supports_undo()

    @property
    def can_redo(self) -> bool:
        """재실행 가능 여부 (취소가 가능하면 재실행도 가능)"""
        return self.can_undo

    def set_preflight_coordinator(self, coordinator: "IPreflightCoordinator") -> None:
        """프리플라이트 코디네이터 설정"""
        self._preflight_coordinator = coordinator

    def set_journal_manager(self, journal_manager: "IJournalManager") -> None:
        """저널 매니저 설정"""
        self._journal_manager = journal_manager

    def set_staging_manager(self, staging_manager: "IStagingManager") -> None:
        """스테이징 매니저 설정 (Phase 3)"""
        self._staging_manager = staging_manager

    def run_preflight_check(self) -> Optional["PreflightCheckResult"]:
        """프리플라이트 검사 실행"""
        if self.skip_preflight or not self._preflight_coordinator:
            return None

        # 하위 클래스에서 구현한 검사 대상 경로 가져오기
        paths = self._get_preflight_paths()
        if not paths:
            return None

        source_path, destination_path = paths
        return self._preflight_coordinator.check_operation(source_path, destination_path)

    def create_journal_entry(self) -> Optional["JournalEntry"]:
        """저널 엔트리 생성"""
        if not self.enable_journaling or not self._journal_manager:
            return None

        from ..journal import JournalEntry

        # 하위 클래스에서 구현한 저널 정보 가져오기
        journal_info = self._get_journal_info()
        if not journal_info:
            return None

        entry_type, operation_details = journal_info

        return JournalEntry(
            command_id=self._command_id, entry_type=entry_type, operation_details=operation_details
        )

    def execute(self) -> CommandResult:
        """Command 실행"""
        self.logger.info(f"실행 시작: {self.description}")

        # 결과 객체 초기화
        self._result = CommandResult(
            command_id=self._command_id, status=CommandStatus.PENDING, executed_at=datetime.now()
        )

        # 저널 엔트리 생성 (실행 전에 미리 생성)
        if self.enable_journaling and self._journal_manager:
            self.logger.debug("저널 엔트리 생성")
            self._journal_entry = self.create_journal_entry()
            if self._journal_entry:
                self._journal_entry.start_execution()
                self._journal_manager.add_entry(self._journal_entry)
                self._result.journal_entry_id = self._journal_entry.entry_id

        try:
            # 프리플라이트 검사
            if not self.skip_preflight and self._preflight_coordinator:
                self.logger.debug("프리플라이트 검사 시작")
                preflight_result = self.run_preflight_check()

                if preflight_result:
                    self._result.preflight_result = preflight_result

                    # 차단 문제가 있으면 실행 중단
                    if preflight_result.has_blocking_issues:
                        blocking_count = len(preflight_result.blocking_issues)
                        raise ValueError(
                            f"프리플라이트 검사 실패: 차단 문제 {blocking_count}개 발견"
                        )

                    # 경고가 있으면 로그 출력
                    if preflight_result.warning_issues:
                        warning_count = len(preflight_result.warning_issues)
                        self.logger.warning(f"프리플라이트 경고 {warning_count}개와 함께 진행")

            # 기본 유효성 검사
            if not self.validate():
                raise ValueError("Command 유효성 검사 실패")

            # Phase 3: 스테이징 디렉토리에서 파일 준비
            if self.enable_staging and self._staging_manager:
                self.logger.debug("스테이징 디렉토리에서 파일 준비")
                staged_files = self._stage_files_for_operation()
                if staged_files:
                    self._result.staged_files = staged_files
                    self._result.staging_directory = self._staging_manager.get_staging_directory()
                    self.logger.info(f"파일 {len(staged_files)}개 스테이징 완료")

            # 실행 상태로 변경
            self._result.status = CommandStatus.EXECUTING

            # 실제 실행
            execution_start = datetime.now()
            self._execute_impl()
            execution_end = datetime.now()

            # 성공 처리
            self._result.status = CommandStatus.COMPLETED
            self._result.completed_at = execution_end
            self._result.execution_time_ms = (
                execution_end - execution_start
            ).total_seconds() * 1000

            # 저널 엔트리 완료 처리
            if self._journal_entry:
                self._journal_entry.complete_execution(True)
                self._update_journal_entry_rollback_data()

            self.logger.info(
                f"실행 완료: {self.description} ({self._result.execution_time_ms:.1f}ms)"
            )

        except Exception as e:
            # 실패 처리
            self._result.status = CommandStatus.FAILED
            self._result.error = CommandError(
                error_type=type(e).__name__, message=str(e), exception=e
            )
            self._result.completed_at = datetime.now()

            # 저널 엔트리 실패 처리
            if self._journal_entry:
                self._journal_entry.complete_execution(False, str(e))

            self.logger.error(f"실행 실패: {self.description} - {e}")

        return self._result

    def undo(self) -> CommandResult:
        """Command 취소"""
        if not self.can_undo:
            raise RuntimeError(f"Command {self._command_id}는 취소할 수 없습니다")

        self.logger.info(f"취소 시작: {self.description}")

        # 취소 결과를 위한 새로운 CommandResult 생성
        undo_result = CommandResult(
            command_id=self._command_id, status=CommandStatus.PENDING, executed_at=datetime.now()
        )

        try:
            # 취소 실행
            undo_start = datetime.now()
            self._undo_impl()
            undo_end = datetime.now()

            # 성공 상태 업데이트
            undo_result.status = CommandStatus.UNDONE
            undo_result.completed_at = undo_end
            undo_result.execution_time_ms = (undo_end - undo_start).total_seconds() * 1000

            # 원본 결과 상태도 업데이트
            if self._result:
                self._result.status = CommandStatus.UNDONE

            self.logger.info(
                f"취소 완료: {self.description} ({undo_result.execution_time_ms:.1f}ms)"
            )

        except Exception as e:
            # 취소 실패 상태 업데이트
            undo_result.status = CommandStatus.FAILED
            undo_result.error = CommandError(
                error_type=type(e).__name__, message=str(e), exception=e
            )
            undo_result.completed_at = datetime.now()

            self.logger.error(f"취소 실패: {self.description} - {e}")

        return undo_result

    def redo(self) -> CommandResult:
        """Command 재실행 (취소 후 다시 실행)"""
        if not self.can_redo:
            raise RuntimeError(f"Command {self._command_id}는 재실행할 수 없습니다")

        # 재실행은 기본적으로 execute()와 동일
        return self.execute()

    def validate(self) -> bool:
        """실행 전 유효성 검사 - 하위 클래스에서 구현"""
        return True

    # === 추상 메서드 ===

    @abstractmethod
    def _execute_impl(self) -> None:
        """실제 Command 실행 로직 - 하위 클래스에서 구현"""

    @abstractmethod
    def _get_default_description(self) -> str:
        """기본 Command 설명 - 하위 클래스에서 구현"""

    def _get_preflight_paths(self) -> tuple[Path, Path | None] | None:
        """프리플라이트 검사할 경로 반환 - 하위 클래스에서 오버라이드"""
        return None

    def _get_journal_info(self) -> tuple["JournalEntryType", "FileOperationDetails"] | None:
        """저널 정보 반환 - 하위 클래스에서 오버라이드"""
        return None

    def _update_journal_entry_rollback_data(self) -> None:
        """저널 엔트리에 롤백 데이터 업데이트 - 하위 클래스에서 오버라이드"""
        if not self._journal_entry:
            return

        # 기본 롤백 데이터 설정
        for key, value in self._undo_data.items():
            if isinstance(value, Path):
                self._journal_entry.set_rollback_data(key, str(value))
            else:
                self._journal_entry.set_rollback_data(key, value)

    # === 오버라이드 가능한 메서드 ===

    def _supports_undo(self) -> bool:
        """취소 지원 여부 - 하위 클래스에서 오버라이드"""
        return True

    def _undo_impl(self) -> None:
        """취소 구현 - 하위 클래스에서 오버라이드"""
        raise NotImplementedError("이 Command는 취소를 지원하지 않습니다")

    # === 헬퍼 메서드 ===

    def _store_undo_data(self, key: str, value: Any) -> None:
        """취소용 데이터 저장"""
        self._undo_data[key] = value

    def _get_undo_data(self, key: str, default: Any = None) -> Any:
        """취소용 데이터 조회"""
        return self._undo_data.get(key, default)

    def _add_affected_file(self, file_path: str | Path) -> None:
        """영향받은 파일 추가"""
        if self._result:
            self._result.affected_files.append(Path(file_path))

    def _add_created_file(self, file_path: str | Path) -> None:
        """생성된 파일 추가"""
        if self._result:
            self._result.created_files.append(Path(file_path))

    def _add_deleted_file(self, file_path: str | Path) -> None:
        """삭제된 파일 추가"""
        if self._result:
            self._result.deleted_files.append(Path(file_path))

    def _add_modified_file(self, file_path: str | Path) -> None:
        """수정된 파일 추가"""
        if self._result:
            self._result.modified_files.append(Path(file_path))

    def _set_metadata(self, key: str, value: Any) -> None:
        """메타데이터 설정"""
        if self._result:
            self._result.metadata[key] = value

    # === Phase 3: 스테이징 관련 메서드 ===

    def _stage_files_for_operation(self) -> list["StagedFile"]:
        """작업을 위한 파일 스테이징 (Phase 3, 기본 구현)"""
        if not self.enable_staging or not self._staging_manager:
            return []

        try:
            # 하위 클래스에서 구현한 스테이징 대상 경로 가져오기
            staging_paths = self._get_staging_paths()
            if not staging_paths:
                return []

            staged_files = []
            for source_path, operation_type in staging_paths:
                try:
                    if source_path.is_file():
                        staged_file = self._staging_manager.stage_file(source_path, operation_type)
                    elif source_path.is_dir():
                        staged_file = self._staging_manager.stage_directory(
                            source_path, operation_type
                        )
                    else:
                        continue

                    staged_files.append(staged_file)

                except Exception as e:
                    self.logger.warning(f"파일 스테이징 실패: {source_path} - {e}")
                    continue

            return staged_files

        except Exception as e:
            self.logger.error(f"파일 스테이징 중 오류: {e}")
            return []

    def _get_staging_paths(self) -> list[tuple[Path, str]]:
        """스테이징 대상 경로와 작업 타입 (하위 클래스에서 구현, 기본값은 빈 리스트)"""
        return []


class CompositeCommand(BaseCommand):
    """여러 Command를 하나로 묶는 복합 Command"""

    def __init__(self, commands: list[ICommand], description: str = ""):
        super().__init__(description)
        self.commands = commands
        self._executed_commands: list[ICommand] = []

    def set_staging_manager(self, staging_manager: "IStagingManager") -> None:
        """모든 하위 Command에 스테이징 매니저 설정"""
        super().set_staging_manager(staging_manager)
        for command in self.commands:
            if hasattr(command, "set_staging_manager"):
                command.set_staging_manager(staging_manager)

    def _get_default_description(self) -> str:
        return f"복합 작업 ({len(self.commands)}개 Command)"

    def _execute_impl(self) -> None:
        """모든 하위 Command 순차 실행"""
        for command in self.commands:
            result = command.execute()
            self._executed_commands.append(command)

            # 하나라도 실패하면 중단
            if not result.is_success:
                raise RuntimeError(f"하위 Command 실패: {command.description}")

            # 결과 통합
            if self._result:
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

    def _undo_impl(self) -> None:
        """실행된 Command들을 역순으로 취소"""
        for command in reversed(self._executed_commands):
            if command.can_undo:
                command.undo()

    def validate(self) -> bool:
        """모든 하위 Command 유효성 검사"""
        return all(command.validate() for command in self.commands)
