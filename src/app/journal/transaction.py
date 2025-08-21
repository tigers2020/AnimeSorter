"""
저널 트랜잭션

연관된 파일 조작들을 하나의 단위로 관리하는 트랜잭션 시스템
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol
from uuid import UUID, uuid4

from .journal_entry import JournalEntry, JournalEntryStatus


class TransactionStatus(Enum):
    """트랜잭션 상태"""

    ACTIVE = "active"  # 활성 (진행 중)
    COMMITTED = "committed"  # 커밋됨 (성공 완료)
    ROLLED_BACK = "rolled_back"  # 롤백됨 (취소)
    FAILED = "failed"  # 실패
    ABORTED = "aborted"  # 중단됨


class ITransaction(Protocol):
    """트랜잭션 인터페이스"""

    @property
    def transaction_id(self) -> UUID:
        """트랜잭션 고유 ID"""
        ...

    @property
    def status(self) -> TransactionStatus:
        """현재 상태"""
        ...

    def add_entry(self, entry: JournalEntry) -> None:
        """저널 엔트리 추가"""
        ...

    def commit(self) -> bool:
        """트랜잭션 커밋"""
        ...

    def rollback(self) -> bool:
        """트랜잭션 롤백"""
        ...

    def can_rollback(self) -> bool:
        """롤백 가능 여부"""
        ...


@dataclass
class Transaction:
    """트랜잭션 구현"""

    # 기본 식별자
    transaction_id: UUID = field(default_factory=uuid4)
    parent_transaction_id: UUID | None = None

    # 트랜잭션 정보
    name: str = ""
    description: str = ""
    status: TransactionStatus = TransactionStatus.ACTIVE

    # 시간 정보
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # 저널 엔트리들
    entries: list[JournalEntry] = field(default_factory=list)

    # 실행 결과
    success: bool = False
    total_entries: int = 0
    successful_entries: int = 0
    failed_entries: int = 0

    # 롤백 정보
    rollback_point: datetime | None = None
    rollback_reason: str | None = None
    auto_rollback_on_failure: bool = True

    # 메타데이터
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        """초기화 후 처리"""
        self.logger = logging.getLogger(f"Journal.Transaction[{self.transaction_id.hex[:8]}]")

        # 기본 이름 설정
        if not self.name:
            self.name = f"Transaction-{self.transaction_id.hex[:8]}"

    def start(self) -> None:
        """트랜잭션 시작"""
        if self.status != TransactionStatus.ACTIVE:
            raise RuntimeError(f"트랜잭션이 이미 {self.status.value} 상태입니다")

        self.started_at = datetime.now()
        self.rollback_point = self.started_at
        self.logger.info(f"트랜잭션 시작: {self.name}")

    def add_entry(self, entry: JournalEntry) -> None:
        """저널 엔트리 추가"""
        if self.status != TransactionStatus.ACTIVE:
            raise RuntimeError(
                f"비활성 트랜잭션에 엔트리를 추가할 수 없습니다: {self.status.value}"
            )

        # 엔트리에 트랜잭션 ID 설정
        entry.transaction_id = self.transaction_id
        self.entries.append(entry)
        self.total_entries = len(self.entries)

        self.logger.debug(f"저널 엔트리 추가: {entry.entry_type.value} (총 {self.total_entries}개)")

    def remove_entry(self, entry_id: UUID) -> bool:
        """저널 엔트리 제거"""
        if self.status != TransactionStatus.ACTIVE:
            return False

        for i, entry in enumerate(self.entries):
            if entry.entry_id == entry_id:
                self.entries.pop(i)
                self.total_entries = len(self.entries)
                self.logger.debug(f"저널 엔트리 제거: {entry_id}")
                return True

        return False

    def get_entry(self, entry_id: UUID) -> JournalEntry | None:
        """저널 엔트리 조회"""
        for entry in self.entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def get_entries_by_status(self, status: JournalEntryStatus) -> list[JournalEntry]:
        """상태별 엔트리 조회"""
        return [entry for entry in self.entries if entry.status == status]

    def get_completed_entries(self) -> list[JournalEntry]:
        """완료된 엔트리들"""
        return self.get_entries_by_status(JournalEntryStatus.COMPLETED)

    def get_failed_entries(self) -> list[JournalEntry]:
        """실패한 엔트리들"""
        return self.get_entries_by_status(JournalEntryStatus.FAILED)

    def update_statistics(self) -> None:
        """통계 정보 업데이트"""
        self.successful_entries = len(
            [e for e in self.entries if e.status == JournalEntryStatus.COMPLETED and e.success]
        )
        self.failed_entries = len(
            [e for e in self.entries if e.status == JournalEntryStatus.FAILED or not e.success]
        )

        # 전체 성공 여부 판단
        self.success = (
            self.total_entries > 0
            and self.failed_entries == 0
            and self.successful_entries == self.total_entries
        )

    def commit(self) -> bool:
        """트랜잭션 커밋"""
        if self.status != TransactionStatus.ACTIVE:
            self.logger.warning(f"비활성 트랜잭션을 커밋할 수 없습니다: {self.status.value}")
            return False

        self.update_statistics()
        self.completed_at = datetime.now()

        if self.success:
            self.status = TransactionStatus.COMMITTED
            self.logger.info(
                f"트랜잭션 커밋 성공: {self.name} ({self.successful_entries}/{self.total_entries})"
            )
            return True
        # 실패한 엔트리가 있으면 자동 롤백 여부 확인
        if self.auto_rollback_on_failure:
            self.logger.warning(f"실패로 인한 자동 롤백 시작: {self.failed_entries}개 실패")
            return self.rollback("커밋 중 실패 발생")
        self.status = TransactionStatus.FAILED
        self.logger.error(f"트랜잭션 실패: {self.failed_entries}개 엔트리 실패")
        return False

    def rollback(self, reason: str = "") -> bool:
        """트랜잭션 롤백"""
        if self.status not in (TransactionStatus.ACTIVE, TransactionStatus.FAILED):
            self.logger.warning(f"롤백할 수 없는 상태: {self.status.value}")
            return False

        self.rollback_reason = reason or "사용자 요청"
        self.completed_at = datetime.now()

        # 성공한 엔트리들을 역순으로 롤백
        rollback_count = 0
        rollback_failures = 0

        completed_entries = self.get_completed_entries()
        for entry in reversed(completed_entries):
            if entry.can_rollback():
                try:
                    entry.mark_rolled_back()
                    rollback_count += 1
                    self.logger.debug(f"엔트리 롤백: {entry.entry_id}")
                except Exception as e:
                    rollback_failures += 1
                    self.logger.error(f"엔트리 롤백 실패: {entry.entry_id} - {e}")

        self.status = TransactionStatus.ROLLED_BACK
        self.logger.info(f"트랜잭션 롤백 완료: {rollback_count}개 성공, {rollback_failures}개 실패")

        return rollback_failures == 0

    def abort(self, reason: str = "") -> None:
        """트랜잭션 중단"""
        self.rollback_reason = reason or "사용자 중단"
        self.completed_at = datetime.now()
        self.status = TransactionStatus.ABORTED

        self.logger.info(f"트랜잭션 중단: {self.name} - {reason}")

    def can_rollback(self) -> bool:
        """롤백 가능 여부"""
        if self.status not in (TransactionStatus.COMMITTED, TransactionStatus.FAILED):
            return False

        # 롤백 가능한 엔트리가 하나라도 있으면 가능
        return any(entry.can_rollback() for entry in self.entries)

    def get_duration_ms(self) -> float | None:
        """실행 시간 (밀리초)"""
        if not self.started_at or not self.completed_at:
            return None

        return (self.completed_at - self.started_at).total_seconds() * 1000

    def add_tag(self, tag: str) -> None:
        """태그 추가"""
        if tag not in self.tags:
            self.tags.append(tag)

    def set_metadata(self, key: str, value: Any) -> None:
        """메타데이터 설정"""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """메타데이터 조회"""
        return self.metadata.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "transaction_id": str(self.transaction_id),
            "parent_transaction_id": str(self.parent_transaction_id)
            if self.parent_transaction_id
            else None,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "entries": [entry.to_dict() for entry in self.entries],
            "success": self.success,
            "total_entries": self.total_entries,
            "successful_entries": self.successful_entries,
            "failed_entries": self.failed_entries,
            "rollback_point": self.rollback_point.isoformat() if self.rollback_point else None,
            "rollback_reason": self.rollback_reason,
            "auto_rollback_on_failure": self.auto_rollback_on_failure,
            "metadata": self.metadata,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        """딕셔너리에서 복원"""
        # UUID 문자열을 UUID 객체로 변환
        data["transaction_id"] = UUID(data["transaction_id"])
        if data.get("parent_transaction_id"):
            data["parent_transaction_id"] = UUID(data["parent_transaction_id"])

        # Enum 문자열을 Enum 객체로 변환
        data["status"] = TransactionStatus(data["status"])

        # datetime 문자열을 datetime 객체로 변환
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        if data.get("rollback_point"):
            data["rollback_point"] = datetime.fromisoformat(data["rollback_point"])

        # 저널 엔트리들 복원
        entries_data = data.pop("entries", [])
        transaction = cls(**data)

        for entry_data in entries_data:
            entry = JournalEntry.from_dict(entry_data)
            transaction.entries.append(entry)

        transaction.total_entries = len(transaction.entries)
        return transaction

    def __str__(self) -> str:
        """문자열 표현"""
        return f"Transaction({self.name}, {self.status.value}, {self.total_entries} entries)"

    def __repr__(self) -> str:
        """개발자용 표현"""
        return (
            f"Transaction(id={self.transaction_id.hex[:8]}, "
            f"name='{self.name}', status={self.status.value}, "
            f"entries={self.total_entries})"
        )
