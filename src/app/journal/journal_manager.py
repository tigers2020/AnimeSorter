"""
저널 매니저

전체 저널 시스템을 관리하는 핵심 컴포넌트
Phase 3 요구사항: JSONL 형식 + 스테이징 디렉토리 시스템
"""

import json
import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from .journal_entry import JournalEntry, JournalEntryStatus, JournalEntryType
from .transaction import Transaction, TransactionStatus


@dataclass
class JournalConfiguration:
    """저널 시스템 설정"""

    # 저장 설정
    journal_directory: Path = field(default_factory=lambda: Path(".animesorter_journal"))
    staging_directory: Path = field(default_factory=lambda: Path(".animesorter_staging"))
    auto_save: bool = True
    save_interval_seconds: int = 60

    # JSONL 설정
    use_jsonl_format: bool = True  # Phase 3: JSONL 형식 사용
    jsonl_max_entries_per_file: int = 1000  # JSONL 파일당 최대 엔트리 수
    jsonl_rotation_enabled: bool = True  # JSONL 파일 로테이션

    # 성능 설정
    max_memory_entries: int = 10000
    batch_size: int = 100
    async_processing: bool = True
    max_worker_threads: int = 4

    # 정리 설정
    auto_cleanup: bool = True
    cleanup_interval_days: int = 30
    max_journal_size_mb: int = 500
    keep_successful_entries_days: int = 7
    keep_failed_entries_days: int = 30

    # 압축 및 아카이브
    compress_old_entries: bool = True
    archive_old_transactions: bool = True

    # 로깅 설정
    log_level: str = "INFO"
    detailed_logging: bool = False


class IJournalManager(Protocol):
    """저널 매니저 인터페이스"""

    def create_transaction(self, name: str = "", description: str = "") -> Transaction:
        """새 트랜잭션 생성"""
        ...

    def add_entry(self, entry: JournalEntry, transaction_id: UUID | None = None) -> None:
        """저널 엔트리 추가"""
        ...

    def commit_transaction(self, transaction_id: UUID) -> bool:
        """트랜잭션 커밋"""
        ...

    def rollback_transaction(self, transaction_id: UUID, reason: str = "") -> bool:
        """트랜잭션 롤백"""
        ...

    def save_journal(self) -> bool:
        """저널 저장"""
        ...

    def load_journal(self) -> bool:
        """저널 로드"""
        ...

    def get_staging_directory(self) -> Path:
        """스테이징 디렉토리 반환"""
        ...

    def stage_file_operation(self, source_path: Path, operation_type: str) -> Path:
        """파일 작업을 스테이징 디렉토리에 준비"""
        ...


class JournalManager:
    """저널 매니저 구현"""

    def __init__(self, config: JournalConfiguration | None = None):
        self.config = config or JournalConfiguration()
        self.logger = logging.getLogger(self.__class__.__name__)

        # 저장소
        self._transactions: dict[UUID, Transaction] = {}
        self._entries: dict[UUID, JournalEntry] = {}
        self._active_transaction: Transaction | None = None

        # 스레드 안전성
        self._lock = threading.RLock()
        self._executor: ThreadPoolExecutor | None = None

        # 상태 관리
        self._is_initialized = False
        self._is_saving = False
        self._last_save_time: datetime | None = None
        self._last_cleanup_time: datetime | None = None

        # JSONL 관련
        self._current_jsonl_file: Path | None = None
        self._current_jsonl_entries_count: int = 0

        # 이벤트 핸들러
        self._event_handlers: dict[str, list[Callable]] = {}

        # 초기화
        self._initialize_directories()
        self._initialize_jsonl_file()
        self._complete_initialization()

    def _initialize_directories(self):
        """필요한 디렉토리들 초기화"""
        try:
            # 저널 디렉토리 생성
            self.config.journal_directory.mkdir(parents=True, exist_ok=True)

            # 스테이징 디렉토리 생성 (Phase 3)
            self.config.staging_directory.mkdir(parents=True, exist_ok=True)

            # JSONL 파일들을 위한 디렉토리
            jsonl_dir = self.config.journal_directory / "jsonl"
            jsonl_dir.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"저널 디렉토리 초기화 완료: {self.config.journal_directory}")
            self.logger.info(f"스테이징 디렉토리 초기화 완료: {self.config.staging_directory}")

        except Exception as e:
            self.logger.error(f"디렉토리 초기화 실패: {e}")

    def _initialize_jsonl_file(self):
        """JSONL 파일 초기화"""
        if not self.config.use_jsonl_format:
            return

        try:
            # 현재 JSONL 파일 경로 설정
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._current_jsonl_file = (
                self.config.journal_directory / "jsonl" / f"journal_{timestamp}.jsonl"
            )
            self._current_jsonl_entries_count = 0

            # 파일 생성
            self._current_jsonl_file.touch()
            self.logger.info(f"JSONL 파일 초기화: {self._current_jsonl_file}")

        except Exception as e:
            self.logger.error(f"JSONL 파일 초기화 실패: {e}")

    def _complete_initialization(self):
        """초기화 완료"""
        try:
            # 스레드풀 초기화
            if self.config.async_processing:
                self._executor = ThreadPoolExecutor(
                    max_workers=self.config.max_worker_threads, thread_name_prefix="Journal"
                )

            # 기존 저널 로드
            self.load_journal()

            self._is_initialized = True
            self.logger.info("저널 매니저 초기화 완료")

        except Exception as e:
            self.logger.error(f"저널 매니저 초기화 실패: {e}")
            raise

    def _rotate_jsonl_file(self):
        """JSONL 파일 로테이션"""
        if not self.config.jsonl_rotation_enabled:
            return

        if self._current_jsonl_entries_count >= self.config.jsonl_max_entries_per_file:
            try:
                # 새 JSONL 파일 생성
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_file = self.config.journal_directory / "jsonl" / f"journal_{timestamp}.jsonl"

                # 기존 파일 닫기
                self._current_jsonl_file = new_file
                self._current_jsonl_entries_count = 0

                # 새 파일 생성
                new_file.touch()
                self.logger.info(f"JSONL 파일 로테이션: {new_file}")

            except Exception as e:
                self.logger.error(f"JSONL 파일 로테이션 실패: {e}")

    def get_staging_directory(self) -> Path:
        """스테이징 디렉토리 반환"""
        return self.config.staging_directory

    def stage_file_operation(self, source_path: Path, operation_type: str) -> Path:
        """파일 작업을 스테이징 디렉토리에 준비"""
        try:
            if not source_path.exists():
                raise FileNotFoundError(f"소스 파일을 찾을 수 없습니다: {source_path}")

            # 스테이징 디렉토리 내 고유 경로 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid4())[:8]
            staging_name = f"{timestamp}_{unique_id}_{source_path.name}"
            staging_path = self.config.staging_directory / staging_name

            # 파일 복사 (안전한 작업을 위해)
            import shutil

            if source_path.is_file():
                shutil.copy2(source_path, staging_path)
            elif source_path.is_dir():
                shutil.copytree(source_path, staging_path)

            self.logger.info(f"파일 스테이징 완료: {source_path} -> {staging_path}")
            return staging_path

        except Exception as e:
            self.logger.error(f"파일 스테이징 실패: {e}")
            raise

    def _save_entry_to_jsonl(self, entry: JournalEntry):
        """엔트리를 JSONL 파일에 저장"""
        if not self.config.use_jsonl_format or not self._current_jsonl_file:
            return

        try:
            # JSONL 형식으로 엔트리 저장
            entry_data = entry.to_dict()
            entry_line = json.dumps(entry_data, ensure_ascii=False, separators=(",", ":"))

            with self._current_jsonl_file.open("a", encoding="utf-8") as f:
                f.write(entry_line + "\n")

            self._current_jsonl_entries_count += 1

            # 파일 로테이션 확인
            self._rotate_jsonl_file()

        except Exception as e:
            self.logger.error(f"JSONL 엔트리 저장 실패: {e}")

    def add_entry(self, entry: JournalEntry, transaction_id: UUID | None = None) -> None:
        """저널 엔트리 추가"""
        with self._lock:
            try:
                # 트랜잭션 ID 설정
                if transaction_id:
                    entry.transaction_id = transaction_id
                elif self._active_transaction:
                    entry.transaction_id = self._active_transaction.transaction_id

                # 엔트리 저장
                self._entries[entry.entry_id] = entry

                # 트랜잭션에 엔트리 추가
                if entry.transaction_id and entry.transaction_id in self._transactions:
                    self._transactions[entry.transaction_id].add_entry(entry)

                # JSONL 파일에 즉시 저장 (Phase 3: 실시간 저장)
                if self.config.use_jsonl_format:
                    self._save_entry_to_jsonl(entry)

                # 이벤트 발행
                self._trigger_event("entry_created", entry)

                self.logger.debug(f"저널 엔트리 추가: {entry.entry_id}")

            except Exception as e:
                self.logger.error(f"저널 엔트리 추가 실패: {e}")
                raise

    def create_transaction(self, name: str = "", description: str = "") -> Transaction:
        """새 트랜잭션 생성"""
        with self._lock:
            transaction = Transaction(
                name=name or f"Transaction-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                description=description,
            )

            self._transactions[transaction.transaction_id] = transaction
            self._active_transaction = transaction

            self.logger.info(f"트랜잭션 생성: {transaction.name}")
            self._trigger_event("transaction_created", transaction)

            return transaction

    def get_active_transaction(self) -> Transaction | None:
        """현재 활성 트랜잭션 조회"""
        return self._active_transaction

    def set_active_transaction(self, transaction_id: UUID) -> bool:
        """활성 트랜잭션 설정"""
        with self._lock:
            transaction = self._transactions.get(transaction_id)
            if transaction and transaction.status == TransactionStatus.ACTIVE:
                self._active_transaction = transaction
                return True
            return False

    def get_transaction(self, transaction_id: UUID) -> Transaction | None:
        """트랜잭션 조회"""
        return self._transactions.get(transaction_id)

    def get_entry(self, entry_id: UUID) -> JournalEntry | None:
        """저널 엔트리 조회"""
        return self._entries.get(entry_id)

    def commit_transaction(self, transaction_id: UUID) -> bool:
        """트랜잭션 커밋"""
        with self._lock:
            transaction = self._transactions.get(transaction_id)
            if not transaction:
                self.logger.warning(f"트랜잭션을 찾을 수 없습니다: {transaction_id}")
                return False

            success = transaction.commit()

            if success:
                self.logger.info(f"트랜잭션 커밋 성공: {transaction.name}")
                self._trigger_event("transaction_committed", transaction)
            else:
                self.logger.error(f"트랜잭션 커밋 실패: {transaction.name}")

            # 활성 트랜잭션이면 해제
            if (
                self._active_transaction
                and self._active_transaction.transaction_id == transaction_id
            ):
                self._active_transaction = None

            # 자동 저장
            if self.config.auto_save:
                self._schedule_auto_save()

            return success

    def rollback_transaction(self, transaction_id: UUID, reason: str = "") -> bool:
        """트랜잭션 롤백"""
        with self._lock:
            transaction = self._transactions.get(transaction_id)
            if not transaction:
                self.logger.warning(f"트랜잭션을 찾을 수 없습니다: {transaction_id}")
                return False

            success = transaction.rollback(reason)

            if success:
                self.logger.info(f"트랜잭션 롤백 성공: {transaction.name}")
                self._trigger_event("transaction_rolled_back", transaction)
            else:
                self.logger.error(f"트랜잭션 롤백 실패: {transaction.name}")

            # 활성 트랜잭션이면 해제
            if (
                self._active_transaction
                and self._active_transaction.transaction_id == transaction_id
            ):
                self._active_transaction = None

            # 자동 저장
            if self.config.auto_save:
                self._schedule_auto_save()

            return success

    def get_transactions_by_status(self, status: TransactionStatus) -> list[Transaction]:
        """상태별 트랜잭션 조회"""
        return [t for t in self._transactions.values() if t.status == status]

    def get_entries_by_type(self, entry_type: JournalEntryType) -> list[JournalEntry]:
        """타입별 엔트리 조회"""
        return [e for e in self._entries.values() if e.entry_type == entry_type]

    def get_recent_entries(self, hours: int = 24) -> list[JournalEntry]:
        """최근 엔트리 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [e for e in self._entries.values() if e.created_at >= cutoff_time]

    def save_journal(self) -> bool:
        """저널 저장 (Phase 3: JSONL 형식 지원)"""
        if self._is_saving:
            return True  # 이미 저장 중

        try:
            self._is_saving = True

            if self.config.use_jsonl_format:
                # JSONL 형식으로 저장 (이미 실시간으로 저장됨)
                self.logger.info("JSONL 형식으로 실시간 저장 중 - 별도 저장 불필요")
                return True
            # 기존 JSON 형식으로 저장
            journal_file = self.config.journal_directory / "journal.json"
            backup_file = self.config.journal_directory / "journal.backup.json"

            # 백업 생성
            if journal_file.exists():
                if backup_file.exists():
                    backup_file.unlink()  # 기존 백업 파일 삭제
                journal_file.rename(backup_file)

            # 저널 데이터 구성
            journal_data = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "config": {
                    "journal_directory": str(self.config.journal_directory),
                    "auto_save": self.config.auto_save,
                    "max_memory_entries": self.config.max_memory_entries,
                },
                "transactions": [t.to_dict() for t in self._transactions.values()],
                "standalone_entries": [
                    e.to_dict() for e in self._entries.values() if e.transaction_id is None
                ],
                "statistics": self._get_statistics(),
            }

            # JSON 저장
            with journal_file.open("w", encoding="utf-8") as f:
                json.dump(journal_data, f, ensure_ascii=False, indent=2)

            self._last_save_time = datetime.now()
            self.logger.info(f"저널 저장 완료: {journal_file}")
            self._trigger_event("journal_saved", journal_file)

            return True

        except Exception as e:
            self.logger.error(f"저널 저장 실패: {e}")
            return False

        finally:
            self._is_saving = False

    def load_journal(self) -> bool:
        """저널 로드 (Phase 3: JSONL 형식 지원)"""
        if self.config.use_jsonl_format:
            return self._load_journal_from_jsonl()
        return self._load_journal_from_json()

    def _load_journal_from_jsonl(self) -> bool:
        """JSONL 파일에서 저널 로드"""
        try:
            jsonl_dir = self.config.journal_directory / "jsonl"
            if not jsonl_dir.exists():
                self.logger.info("JSONL 디렉토리가 없습니다. 새로 시작합니다.")
                return True

            # JSONL 파일들 찾기
            jsonl_files = sorted(jsonl_dir.glob("journal_*.jsonl"))
            if not jsonl_files:
                self.logger.info("JSONL 파일이 없습니다. 새로 시작합니다.")
                return True

            loaded_entries = 0
            loaded_transactions = 0

            for jsonl_file in jsonl_files:
                try:
                    with jsonl_file.open(encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue

                            try:
                                entry_data = json.loads(line)

                                # JournalEntry인지 Transaction인지 확인
                                if "transaction_id" in entry_data:
                                    # JournalEntry
                                    entry = JournalEntry.from_dict(entry_data)
                                    self._entries[entry.entry_id] = entry
                                    loaded_entries += 1
                                elif "entries" in entry_data:
                                    # Transaction
                                    transaction = Transaction.from_dict(entry_data)
                                    self._transactions[transaction.transaction_id] = transaction
                                    loaded_transactions += 1

                                    # 트랜잭션의 엔트리들도 인덱스에 추가
                                    for entry in transaction.entries:
                                        self._entries[entry.entry_id] = entry
                                        loaded_entries += 1

                            except json.JSONDecodeError as e:
                                self.logger.warning(
                                    f"JSONL 파싱 오류 ({jsonl_file}:{line_num}): {e}"
                                )
                                continue

                except Exception as e:
                    self.logger.warning(f"JSONL 파일 읽기 실패 ({jsonl_file}): {e}")
                    continue

            self.logger.info(
                f"JSONL 저널 로드 완료: 트랜잭션 {loaded_transactions}개, 엔트리 {loaded_entries}개"
            )
            self._trigger_event("journal_loaded", {"format": "jsonl", "files": len(jsonl_files)})

            return True

        except Exception as e:
            self.logger.error(f"JSONL 저널 로드 실패: {e}")
            return False

    def _load_journal_from_json(self) -> bool:
        """기존 JSON 파일에서 저널 로드"""
        journal_file = self.config.journal_directory / "journal.json"

        if not journal_file.exists():
            self.logger.info("저널 파일이 없습니다. 새로 시작합니다.")
            return True

        try:
            with journal_file.open(encoding="utf-8") as f:
                journal_data = json.load(f)

            # 트랜잭션 로드
            for transaction_data in journal_data.get("transactions", []):
                transaction = Transaction.from_dict(transaction_data)
                self._transactions[transaction.transaction_id] = transaction

                # 엔트리들도 인덱스에 추가
                for entry in transaction.entries:
                    self._entries[entry.entry_id] = entry

            # 독립 엔트리 로드
            for entry_data in journal_data.get("standalone_entries", []):
                entry = JournalEntry.from_dict(entry_data)
                self._entries[entry.entry_id] = entry

            self.logger.info(
                f"JSON 저널 로드 완료: 트랜잭션 {len(self._transactions)}개, "
                f"엔트리 {len(self._entries)}개"
            )
            self._trigger_event("journal_loaded", journal_data)

            return True

        except Exception as e:
            self.logger.error(f"JSON 저널 로드 실패: {e}")
            return False

    def cleanup_old_entries(self, force: bool = False) -> int:
        """오래된 엔트리 정리"""
        if not force and not self.config.auto_cleanup:
            return 0

        now = datetime.now()
        success_cutoff = now - timedelta(days=self.config.keep_successful_entries_days)
        failed_cutoff = now - timedelta(days=self.config.keep_failed_entries_days)

        cleaned_count = 0

        with self._lock:
            # 정리할 엔트리 찾기
            entries_to_remove = []

            for entry in self._entries.values():
                should_remove = False

                if entry.status == JournalEntryStatus.COMPLETED and entry.success:
                    should_remove = entry.created_at < success_cutoff
                elif entry.status == JournalEntryStatus.FAILED:
                    should_remove = entry.created_at < failed_cutoff

                if should_remove:
                    entries_to_remove.append(entry.entry_id)

            # 엔트리 제거
            for entry_id in entries_to_remove:
                if entry_id in self._entries:
                    del self._entries[entry_id]
                    cleaned_count += 1

        self._last_cleanup_time = now
        self.logger.info(f"저널 정리 완료: {cleaned_count}개 엔트리 제거")
        self._trigger_event("cleanup_completed", cleaned_count)

        return cleaned_count

    def _schedule_auto_save(self) -> None:
        """자동 저장 예약"""
        if not self.config.auto_save or self._is_saving:
            return

        # 마지막 저장으로부터 충분한 시간이 지났는지 확인
        if self._last_save_time and datetime.now() - self._last_save_time < timedelta(
            seconds=self.config.save_interval_seconds
        ):
            return

        # 비동기 저장
        if self._executor:
            self._executor.submit(self.save_journal)
        else:
            self.save_journal()

    def _get_statistics(self) -> dict[str, Any]:
        """통계 정보 생성"""
        stats = {
            "total_transactions": len(self._transactions),
            "total_entries": len(self._entries),
            "active_transactions": len(self.get_transactions_by_status(TransactionStatus.ACTIVE)),
            "committed_transactions": len(
                self.get_transactions_by_status(TransactionStatus.COMMITTED)
            ),
            "rolled_back_transactions": len(
                self.get_transactions_by_status(TransactionStatus.ROLLED_BACK)
            ),
            "successful_entries": len([e for e in self._entries.values() if e.success]),
            "failed_entries": len([e for e in self._entries.values() if not e.success]),
            "last_save_time": self._last_save_time.isoformat() if self._last_save_time else None,
            "last_cleanup_time": (
                self._last_cleanup_time.isoformat() if self._last_cleanup_time else None
            ),
        }

        # 타입별 통계
        for entry_type in JournalEntryType:
            count = len(self.get_entries_by_type(entry_type))
            stats[f"entries_{entry_type.value}"] = count

        return stats

    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """이벤트 핸들러 추가"""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)

    def remove_event_handler(self, event_type: str, handler: Callable) -> bool:
        """이벤트 핸들러 제거"""
        if event_type in self._event_handlers and handler in self._event_handlers[event_type]:
            self._event_handlers[event_type].remove(handler)
            return True
        return False

    def _trigger_event(self, event_type: str, data: Any) -> None:
        """이벤트 발생"""
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    self.logger.error(f"이벤트 핸들러 실행 실패: {event_type} - {e}")

    def shutdown(self) -> None:
        """저널 매니저 종료"""
        self.logger.info("저널 매니저 종료 시작")

        # 최종 저장
        if self.config.auto_save:
            self.save_journal()

        # 스레드풀 종료
        if self._executor:
            self._executor.shutdown(wait=True)

        self.logger.info("저널 매니저 종료 완료")

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self

    def __exit__(self, exc_type, _exc_val, _exc_tb):
        """컨텍스트 매니저 종료"""
        self.shutdown()
