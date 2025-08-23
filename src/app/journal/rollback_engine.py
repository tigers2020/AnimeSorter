"""
롤백 엔진

실제 파일 시스템에서 작업을 되돌리는 롤백 시스템
"""

import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol
from uuid import UUID, uuid4

from .journal_entry import JournalEntry, JournalEntryType
from .transaction import Transaction, TransactionStatus


class RollbackStrategy(Enum):
    """롤백 전략"""

    CONSERVATIVE = "conservative"  # 안전한 롤백 (백업 활용)
    AGGRESSIVE = "aggressive"  # 강제 롤백 (데이터 손실 가능)
    DRY_RUN = "dry_run"  # 시뮬레이션만
    INTERACTIVE = "interactive"  # 사용자 확인 필요


@dataclass
class RollbackResult:
    """롤백 결과"""

    rollback_id: UUID = field(default_factory=uuid4)
    strategy: RollbackStrategy = RollbackStrategy.CONSERVATIVE

    # 대상 정보
    target_transaction_id: UUID | None = None
    target_entry_ids: list[UUID] = field(default_factory=list)

    # 실행 결과
    success: bool = False
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    skipped_operations: int = 0

    # 시간 정보
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # 상세 결과
    operation_results: list[dict[str, Any]] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # 복구 정보
    recovery_instructions: list[str] = field(default_factory=list)

    @property
    def duration_ms(self) -> float | None:
        """실행 시간 (밀리초)"""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds() * 1000

    def add_operation_result(
        self, entry_id: UUID, operation: str, success: bool, details: str = "", error: str = ""
    ) -> None:
        """작업 결과 추가"""
        self.operation_results.append(
            {
                "entry_id": str(entry_id),
                "operation": operation,
                "success": success,
                "details": details,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        )

        if success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1

    def add_error(self, message: str) -> None:
        """오류 메시지 추가"""
        self.error_messages.append(message)

    def add_warning(self, message: str) -> None:
        """경고 메시지 추가"""
        self.warnings.append(message)

    def add_recovery_instruction(self, instruction: str) -> None:
        """복구 지시사항 추가"""
        self.recovery_instructions.append(instruction)


class IRollbackEngine(Protocol):
    """롤백 엔진 인터페이스"""

    def rollback_transaction(
        self, transaction: Transaction, strategy: RollbackStrategy = RollbackStrategy.CONSERVATIVE
    ) -> RollbackResult:
        """트랜잭션 롤백"""
        ...

    def rollback_entry(
        self, entry: JournalEntry, strategy: RollbackStrategy = RollbackStrategy.CONSERVATIVE
    ) -> RollbackResult:
        """개별 엔트리 롤백"""
        ...

    def can_rollback_entry(self, entry: JournalEntry) -> bool:
        """엔트리 롤백 가능 여부"""
        ...


class RollbackEngine:
    """롤백 엔진 구현"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 롤백 핸들러 매핑
        self._rollback_handlers = {
            JournalEntryType.FILE_MOVE: self._rollback_file_move,
            JournalEntryType.FILE_COPY: self._rollback_file_copy,
            JournalEntryType.FILE_DELETE: self._rollback_file_delete,
            JournalEntryType.FILE_RENAME: self._rollback_file_rename,
            JournalEntryType.DIRECTORY_CREATE: self._rollback_directory_create,
            JournalEntryType.DIRECTORY_DELETE: self._rollback_directory_delete,
        }

    def rollback_transaction(
        self, transaction: Transaction, strategy: RollbackStrategy = RollbackStrategy.CONSERVATIVE
    ) -> RollbackResult:
        """트랜잭션 롤백"""
        self.logger.info(f"트랜잭션 롤백 시작: {transaction.name} (전략: {strategy.value})")

        result = RollbackResult(
            strategy=strategy,
            target_transaction_id=transaction.transaction_id,
            started_at=datetime.now(),
        )

        try:
            # 롤백 가능한 엔트리들 수집 (역순)
            rollbackable_entries = [
                entry for entry in reversed(transaction.entries) if entry.can_rollback()
            ]

            result.total_operations = len(rollbackable_entries)
            result.target_entry_ids = [entry.entry_id for entry in rollbackable_entries]

            if not rollbackable_entries:
                result.add_warning("롤백할 수 있는 엔트리가 없습니다")
                result.success = True
                return result

            # DRY RUN 전략인 경우 시뮬레이션만
            if strategy == RollbackStrategy.DRY_RUN:
                return self._simulate_rollback(rollbackable_entries, result)

            # 각 엔트리 롤백 실행
            for entry in rollbackable_entries:
                try:
                    if self._rollback_single_entry(entry, strategy, result):
                        entry.mark_rolled_back()
                        self.logger.debug(f"엔트리 롤백 성공: {entry.entry_id}")
                    else:
                        self.logger.warning(f"엔트리 롤백 실패: {entry.entry_id}")

                        # 보수적 전략에서는 실패 시 중단
                        if strategy == RollbackStrategy.CONSERVATIVE:
                            result.add_error("보수적 전략으로 인해 롤백 중단")
                            break

                except Exception as e:
                    self.logger.error(f"엔트리 롤백 중 예외: {entry.entry_id} - {e}")
                    result.add_operation_result(
                        entry.entry_id, "rollback", False, error=f"예외 발생: {e}"
                    )

                    if strategy == RollbackStrategy.CONSERVATIVE:
                        break

            # 결과 판정
            result.success = result.failed_operations == 0 and result.successful_operations > 0

            if result.success:
                transaction.status = TransactionStatus.ROLLED_BACK
                self.logger.info(f"트랜잭션 롤백 성공: {result.successful_operations}개 작업")
            else:
                self.logger.error(f"트랜잭션 롤백 실패: {result.failed_operations}개 실패")
                result.add_recovery_instruction("수동으로 파일 상태를 확인하고 필요시 복구하세요")

        except Exception as e:
            self.logger.error(f"트랜잭션 롤백 중 예외: {e}")
            result.add_error(f"롤백 엔진 오류: {e}")
            result.success = False

        finally:
            result.completed_at = datetime.now()

        return result

    def rollback_entry(
        self, entry: JournalEntry, strategy: RollbackStrategy = RollbackStrategy.CONSERVATIVE
    ) -> RollbackResult:
        """개별 엔트리 롤백"""
        self.logger.info(f"엔트리 롤백 시작: {entry.entry_type.value}")

        result = RollbackResult(
            strategy=strategy,
            target_entry_ids=[entry.entry_id],
            total_operations=1,
            started_at=datetime.now(),
        )

        try:
            if not entry.can_rollback():
                result.add_error("롤백할 수 없는 엔트리입니다")
                result.skipped_operations = 1
                result.success = False
                return result

            if strategy == RollbackStrategy.DRY_RUN:
                return self._simulate_rollback([entry], result)

            # 롤백 실행
            success = self._rollback_single_entry(entry, strategy, result)

            if success:
                entry.mark_rolled_back()
                result.success = True
                self.logger.info("엔트리 롤백 성공")
            else:
                result.success = False
                self.logger.error("엔트리 롤백 실패")

        except Exception as e:
            self.logger.error(f"엔트리 롤백 중 예외: {e}")
            result.add_error(f"롤백 엔진 오류: {e}")
            result.success = False

        finally:
            result.completed_at = datetime.now()

        return result

    def can_rollback_entry(self, entry: JournalEntry) -> bool:
        """엔트리 롤백 가능 여부"""
        if not entry.can_rollback():
            return False

        # 타입별 롤백 가능성 확인
        if entry.entry_type not in self._rollback_handlers:
            return False

        # 필요한 롤백 데이터가 있는지 확인
        return entry.operation_details is not None

    def _rollback_single_entry(
        self, entry: JournalEntry, strategy: RollbackStrategy, result: RollbackResult
    ) -> bool:
        """단일 엔트리 롤백"""
        if entry.entry_type not in self._rollback_handlers:
            result.add_operation_result(
                entry.entry_id,
                "rollback",
                False,
                error=f"지원하지 않는 엔트리 타입: {entry.entry_type.value}",
            )
            return False

        handler = self._rollback_handlers[entry.entry_type]

        try:
            return handler(entry, strategy, result)
        except Exception as e:
            result.add_operation_result(
                entry.entry_id, "rollback", False, error=f"롤백 핸들러 오류: {e}"
            )
            return False

    def _rollback_file_move(
        self, entry: JournalEntry, strategy: RollbackStrategy, result: RollbackResult
    ) -> bool:
        """파일 이동 롤백"""
        details = entry.operation_details
        if not details or not details.source_path or not details.destination_path:
            result.add_operation_result(
                entry.entry_id, "rollback_move", False, error="이동 정보가 불완전합니다"
            )
            return False

        source = details.source_path
        destination = details.destination_path

        try:
            # 대상 파일이 존재하는지 확인
            if not destination.exists():
                result.add_operation_result(
                    entry.entry_id,
                    "rollback_move",
                    False,
                    error=f"이동된 파일을 찾을 수 없습니다: {destination}",
                )
                return False

            # 원본 위치로 이동
            if source.exists() and strategy == RollbackStrategy.CONSERVATIVE:
                result.add_operation_result(
                    entry.entry_id,
                    "rollback_move",
                    False,
                    error=f"원본 위치에 이미 파일이 존재합니다: {source}",
                )
                return False

            # 백업이 있으면 복구
            if details.backup_path and details.backup_path.exists():
                shutil.move(str(details.backup_path), str(source))
                result.add_operation_result(
                    entry.entry_id,
                    "rollback_move",
                    True,
                    details=f"백업에서 복구: {details.backup_path} -> {source}",
                )

            # 파일을 원래 위치로 이동
            shutil.move(str(destination), str(source))

            result.add_operation_result(
                entry.entry_id,
                "rollback_move",
                True,
                details=f"파일 이동 롤백: {destination} -> {source}",
            )
            return True

        except Exception as e:
            result.add_operation_result(
                entry.entry_id, "rollback_move", False, error=f"파일 이동 롤백 실패: {e}"
            )
            return False

    def _rollback_file_copy(
        self, entry: JournalEntry, strategy: RollbackStrategy, result: RollbackResult
    ) -> bool:
        """파일 복사 롤백"""
        details = entry.operation_details
        if not details or not details.destination_path:
            result.add_operation_result(
                entry.entry_id, "rollback_copy", False, error="복사 정보가 불완전합니다"
            )
            return False

        destination = details.destination_path

        try:
            # 복사된 파일 삭제
            if destination.exists():
                if destination.is_file():
                    destination.unlink()
                elif destination.is_dir():
                    shutil.rmtree(destination)

                result.add_operation_result(
                    entry.entry_id,
                    "rollback_copy",
                    True,
                    details=f"복사된 파일 삭제: {destination}",
                )
            else:
                result.add_operation_result(
                    entry.entry_id,
                    "rollback_copy",
                    True,
                    details=f"복사된 파일이 이미 없음: {destination}",
                )

            # 백업 복구
            if details.backup_path and details.backup_path.exists():
                if details.backup_path.is_file():
                    shutil.copy2(str(details.backup_path), str(destination))
                elif details.backup_path.is_dir():
                    shutil.copytree(str(details.backup_path), str(destination))

                result.add_operation_result(
                    entry.entry_id,
                    "restore_backup",
                    True,
                    details=f"백업 복구: {details.backup_path} -> {destination}",
                )

            return True

        except Exception as e:
            result.add_operation_result(
                entry.entry_id, "rollback_copy", False, error=f"파일 복사 롤백 실패: {e}"
            )
            return False

    def _rollback_file_delete(
        self, entry: JournalEntry, strategy: RollbackStrategy, result: RollbackResult
    ) -> bool:
        """파일 삭제 롤백"""
        details = entry.operation_details
        if not details or not details.source_path:
            result.add_operation_result(
                entry.entry_id, "rollback_delete", False, error="삭제 정보가 불완전합니다"
            )
            return False

        source = details.source_path
        backup_path = details.backup_path

        try:
            # 백업에서 복구
            if backup_path and backup_path.exists():
                if backup_path.is_file():
                    shutil.copy2(str(backup_path), str(source))
                elif backup_path.is_dir():
                    shutil.copytree(str(backup_path), str(source))

                result.add_operation_result(
                    entry.entry_id,
                    "rollback_delete",
                    True,
                    details=f"백업에서 파일 복구: {backup_path} -> {source}",
                )
                return True
            result.add_operation_result(
                entry.entry_id,
                "rollback_delete",
                False,
                error="백업 파일을 찾을 수 없어 복구 불가능",
            )
            result.add_recovery_instruction(f"수동으로 파일을 복구해야 합니다: {source}")
            return False

        except Exception as e:
            result.add_operation_result(
                entry.entry_id, "rollback_delete", False, error=f"파일 삭제 롤백 실패: {e}"
            )
            return False

    def _rollback_file_rename(
        self, entry: JournalEntry, strategy: RollbackStrategy, result: RollbackResult
    ) -> bool:
        """파일 이름변경 롤백"""
        details = entry.operation_details
        if not details or not details.source_path or not details.destination_path:
            result.add_operation_result(
                entry.entry_id, "rollback_rename", False, error="이름변경 정보가 불완전합니다"
            )
            return False

        # 파일 이름변경은 이동과 동일한 로직
        return self._rollback_file_move(entry, strategy, result)

    def _rollback_directory_create(
        self, entry: JournalEntry, strategy: RollbackStrategy, result: RollbackResult
    ) -> bool:
        """디렉토리 생성 롤백"""
        details = entry.operation_details
        if not details or not details.source_path:
            result.add_operation_result(
                entry.entry_id,
                "rollback_create_dir",
                False,
                error="디렉토리 생성 정보가 불완전합니다",
            )
            return False

        directory = details.source_path

        try:
            if directory.exists() and directory.is_dir():
                # 디렉토리가 비어있는지 확인
                if list(directory.iterdir()):
                    if strategy == RollbackStrategy.CONSERVATIVE:
                        result.add_operation_result(
                            entry.entry_id,
                            "rollback_create_dir",
                            False,
                            error="디렉토리가 비어있지 않아 안전하게 삭제할 수 없습니다",
                        )
                        return False
                    result.add_warning(f"비어있지 않은 디렉토리를 강제 삭제: {directory}")

                shutil.rmtree(directory)
                result.add_operation_result(
                    entry.entry_id,
                    "rollback_create_dir",
                    True,
                    details=f"생성된 디렉토리 삭제: {directory}",
                )
                return True
            result.add_operation_result(
                entry.entry_id,
                "rollback_create_dir",
                True,
                details=f"디렉토리가 이미 없음: {directory}",
            )
            return True

        except Exception as e:
            result.add_operation_result(
                entry.entry_id, "rollback_create_dir", False, error=f"디렉토리 생성 롤백 실패: {e}"
            )
            return False

    def _rollback_directory_delete(
        self, entry: JournalEntry, strategy: RollbackStrategy, result: RollbackResult
    ) -> bool:
        """디렉토리 삭제 롤백"""
        # 디렉토리 삭제 롤백은 파일 삭제와 유사하지만 더 복잡
        return self._rollback_file_delete(entry, strategy, result)

    def _simulate_rollback(
        self, entries: list[JournalEntry], result: RollbackResult
    ) -> RollbackResult:
        """롤백 시뮬레이션"""
        self.logger.info("롤백 시뮬레이션 시작")

        for entry in entries:
            operation_name = f"simulate_{entry.entry_type.value}"

            if self.can_rollback_entry(entry):
                result.add_operation_result(
                    entry.entry_id, operation_name, True, details="시뮬레이션: 롤백 가능"
                )
            else:
                result.add_operation_result(
                    entry.entry_id, operation_name, False, details="시뮬레이션: 롤백 불가능"
                )

        result.success = True
        result.add_warning("시뮬레이션 모드: 실제 롤백은 수행되지 않았습니다")

        return result
