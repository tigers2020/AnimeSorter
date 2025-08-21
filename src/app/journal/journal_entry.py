"""
저널 엔트리

개별 파일 조작을 기록하는 기본 단위
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4


class JournalEntryType(Enum):
    """저널 엔트리 타입"""

    FILE_MOVE = "file_move"
    FILE_COPY = "file_copy"
    FILE_DELETE = "file_delete"
    FILE_RENAME = "file_rename"
    DIRECTORY_CREATE = "directory_create"
    DIRECTORY_DELETE = "directory_delete"
    BATCH_OPERATION = "batch_operation"
    ROLLBACK_OPERATION = "rollback_operation"


class JournalEntryStatus(Enum):
    """저널 엔트리 상태"""

    PENDING = "pending"  # 실행 대기
    IN_PROGRESS = "in_progress"  # 실행 중
    COMPLETED = "completed"  # 성공 완료
    FAILED = "failed"  # 실행 실패
    ROLLED_BACK = "rolled_back"  # 롤백됨
    SKIPPED = "skipped"  # 건너뜀


@dataclass
class FileOperationDetails:
    """파일 조작 상세 정보"""

    # 기본 정보
    operation_type: str
    source_path: Path | None = None
    destination_path: Path | None = None

    # 파일 메타데이터
    file_size: int | None = None
    file_hash: str | None = None
    file_permissions: str | None = None
    file_modified_time: datetime | None = None

    # 조작 옵션
    overwrite: bool = False
    create_dirs: bool = False
    use_trash: bool = True

    # 백업 정보
    backup_path: Path | None = None
    backup_created: bool = False

    # 추가 메타데이터
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환 (직렬화용)"""
        data = asdict(self)

        # Path 객체를 문자열로 변환
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
            elif key == "file_modified_time" and isinstance(value, datetime):
                data[key] = value.isoformat()

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileOperationDetails":
        """딕셔너리에서 복원"""
        # Path 문자열을 Path 객체로 변환
        if data.get("source_path"):
            data["source_path"] = Path(data["source_path"])
        if data.get("destination_path"):
            data["destination_path"] = Path(data["destination_path"])
        if data.get("backup_path"):
            data["backup_path"] = Path(data["backup_path"])

        # datetime 문자열을 datetime 객체로 변환
        if data.get("file_modified_time"):
            data["file_modified_time"] = datetime.fromisoformat(data["file_modified_time"])

        return cls(**data)


class IJournalEntry(Protocol):
    """저널 엔트리 인터페이스"""

    @property
    def entry_id(self) -> UUID:
        """엔트리 고유 ID"""
        ...

    @property
    def transaction_id(self) -> UUID | None:
        """소속 트랜잭션 ID"""
        ...

    @property
    def entry_type(self) -> JournalEntryType:
        """엔트리 타입"""
        ...

    @property
    def status(self) -> JournalEntryStatus:
        """현재 상태"""
        ...

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        ...

    def can_rollback(self) -> bool:
        """롤백 가능 여부"""
        ...


@dataclass
class JournalEntry:
    """저널 엔트리 구현"""

    # 기본 식별자
    entry_id: UUID = field(default_factory=uuid4)
    transaction_id: UUID | None = None
    command_id: UUID | None = None

    # 엔트리 정보
    entry_type: JournalEntryType = JournalEntryType.FILE_MOVE
    status: JournalEntryStatus = JournalEntryStatus.PENDING

    # 시간 정보
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # 조작 상세 정보
    operation_details: FileOperationDetails | None = None

    # 실행 결과
    success: bool = False
    error_message: str | None = None
    execution_time_ms: float | None = None

    # 롤백 정보
    rollback_data: dict[str, Any] = field(default_factory=dict)
    can_rollback_flag: bool = True
    rollback_instructions: list[str] = field(default_factory=list)

    # 메타데이터
    user_info: dict[str, str] = field(default_factory=dict)
    system_info: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        """초기화 후 처리"""
        self.logger = logging.getLogger(f"Journal.Entry[{self.entry_id.hex[:8]}]")

        # 시스템 정보 자동 수집
        if not self.system_info:
            import os
            import platform

            self.system_info = {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "user": os.getenv("USERNAME", "unknown"),
                "hostname": platform.node(),
            }

    def start_execution(self) -> None:
        """실행 시작"""
        self.status = JournalEntryStatus.IN_PROGRESS
        self.started_at = datetime.now()
        self.logger.info(f"저널 엔트리 실행 시작: {self.entry_type.value}")

    def complete_execution(self, success: bool, error_message: str | None = None) -> None:
        """실행 완료"""
        self.completed_at = datetime.now()
        self.success = success
        self.error_message = error_message

        if self.started_at:
            self.execution_time_ms = (self.completed_at - self.started_at).total_seconds() * 1000

        self.status = JournalEntryStatus.COMPLETED if success else JournalEntryStatus.FAILED

        result = "성공" if success else f"실패 ({error_message})"
        self.logger.info(f"저널 엔트리 실행 완료: {result}")

    def mark_rolled_back(self) -> None:
        """롤백으로 표시"""
        self.status = JournalEntryStatus.ROLLED_BACK
        self.logger.info("저널 엔트리가 롤백되었습니다")

    def can_rollback(self) -> bool:
        """롤백 가능 여부"""
        return (
            self.can_rollback_flag and self.status == JournalEntryStatus.COMPLETED and self.success
        )

    def add_rollback_instruction(self, instruction: str) -> None:
        """롤백 지시사항 추가"""
        self.rollback_instructions.append(instruction)
        self.logger.debug(f"롤백 지시사항 추가: {instruction}")

    def set_rollback_data(self, key: str, value: Any) -> None:
        """롤백 데이터 설정"""
        self.rollback_data[key] = value
        self.logger.debug(f"롤백 데이터 설정: {key}")

    def get_rollback_data(self, key: str, default: Any = None) -> Any:
        """롤백 데이터 조회"""
        return self.rollback_data.get(key, default)

    def add_tag(self, tag: str) -> None:
        """태그 추가"""
        if tag not in self.tags:
            self.tags.append(tag)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환 (직렬화용)"""
        return {
            "entry_id": str(self.entry_id),
            "transaction_id": str(self.transaction_id) if self.transaction_id else None,
            "command_id": str(self.command_id) if self.command_id else None,
            "entry_type": self.entry_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "operation_details": self.operation_details.to_dict()
            if self.operation_details
            else None,
            "success": self.success,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "rollback_data": self.rollback_data,
            "can_rollback_flag": self.can_rollback_flag,
            "rollback_instructions": self.rollback_instructions,
            "user_info": self.user_info,
            "system_info": self.system_info,
            "tags": self.tags,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JournalEntry":
        """딕셔너리에서 복원"""
        # UUID 문자열을 UUID 객체로 변환
        data["entry_id"] = UUID(data["entry_id"])
        if data.get("transaction_id"):
            data["transaction_id"] = UUID(data["transaction_id"])
        if data.get("command_id"):
            data["command_id"] = UUID(data["command_id"])

        # Enum 문자열을 Enum 객체로 변환
        data["entry_type"] = JournalEntryType(data["entry_type"])
        data["status"] = JournalEntryStatus(data["status"])

        # datetime 문자열을 datetime 객체로 변환
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])

        # FileOperationDetails 복원
        if data.get("operation_details"):
            data["operation_details"] = FileOperationDetails.from_dict(data["operation_details"])

        return cls(**data)

    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "JournalEntry":
        """JSON 문자열에서 복원"""
        data = json.loads(json_str)
        return cls.from_dict(data)
