"""
중단 기능 매니저
"""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from src.app.events import get_event_bus
from src.app.safety_events import (OperationInterruptedEvent,
                                   OperationInterruptRequestedEvent,
                                   OperationResumeRequestedEvent)


@dataclass
class InterruptionRequest:
    """중단 요청"""

    operation_id: UUID = field(default_factory=lambda: uuid4())
    operation_type: str = ""
    reason: str = "user_request"  # user_request, system_error, timeout
    can_interrupt: bool = True
    graceful_shutdown: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    # 중단 처리 콜백
    on_interrupt: Callable[[], bool] | None = None
    on_cleanup: Callable[[], bool] | None = None

    # 중단 조건
    max_wait_time_seconds: float | None = None
    force_interrupt_after_timeout: bool = False


@dataclass
class InterruptionResult:
    """중단 결과"""

    operation_id: UUID = field(default_factory=lambda: uuid4())
    operation_type: str = ""
    interrupt_reason: str = ""
    files_processed: int = 0
    files_remaining: int = 0
    cleanup_successful: bool = True
    error_message: str | None = None
    interrupted_at: datetime = field(default_factory=datetime.now)

    # 중단 처리 정보
    was_graceful: bool = True
    cleanup_time_ms: float = 0.0
    can_resume: bool = False


class IInterruptionManager(Protocol):
    """중단 매니저 인터페이스"""

    def request_interruption(self, request: InterruptionRequest) -> bool:
        """중단 요청"""
        ...

    def can_interrupt_operation(self, operation_id: UUID) -> bool:
        """작업 중단 가능 여부 확인"""
        ...

    def get_active_operations(self) -> list[UUID]:
        """활성 작업 목록"""
        ...

    def resume_operation(self, operation_id: UUID, resume_from_file: Path | None = None) -> bool:
        """작업 재개"""
        ...


class InterruptionManager:
    """중단 매니저"""

    def __init__(self):
        self.event_bus = get_event_bus()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 활성 작업들
        self._active_operations: dict[UUID, dict[str, Any]] = {}

        # 중단 요청들
        self._interruption_requests: dict[UUID, InterruptionRequest] = {}

        # 중단 처리 상태
        self._interruption_in_progress: dict[UUID, bool] = {}

        # 스레드 안전을 위한 락
        self._lock = threading.Lock()

        # 중단 처리 스레드
        self._interruption_thread = None
        self._stop_interruption_thread = threading.Event()

        # 중단 처리 스레드 시작
        self._start_interruption_thread()

    def _start_interruption_thread(self) -> None:
        """중단 처리 스레드 시작"""
        self._interruption_thread = threading.Thread(
            target=self._interruption_worker, daemon=True, name="InterruptionWorker"
        )
        self._interruption_thread.start()
        self.logger.info("중단 처리 스레드 시작됨")

    def _interruption_worker(self) -> None:
        """중단 처리 워커 스레드"""
        while not self._stop_interruption_thread.is_set():
            try:
                # 중단 요청 처리
                with self._lock:
                    requests_to_process = list(self._interruption_requests.items())

                for _operation_id, request in requests_to_process:
                    if self._should_process_interruption(request):
                        self._process_interruption(request)

                # 타임아웃된 중단 요청 처리
                self._process_timeout_interruptions()

                # 잠시 대기
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"중단 처리 워커 오류: {e}")
                time.sleep(1.0)

    def _should_process_interruption(self, request: InterruptionRequest) -> bool:
        """중단 요청 처리 여부 확인"""
        if request.operation_id in self._interruption_in_progress:
            return False

        if request.max_wait_time_seconds:
            elapsed = (datetime.now() - request.created_at).total_seconds()
            if elapsed > request.max_wait_time_seconds:
                return True

        return True

    def _process_interruption(self, request: InterruptionRequest) -> None:
        """중단 처리"""
        operation_id = request.operation_id

        # 중단 처리 중 표시
        self._interruption_in_progress[operation_id] = True

        try:
            # 중단 시작 이벤트 발행
            self.event_bus.publish(
                OperationInterruptRequestedEvent(
                    operation_id=operation_id,
                    operation_type=request.operation_type,
                    reason=request.reason,
                    can_interrupt=request.can_interrupt,
                    graceful_shutdown=request.graceful_shutdown,
                )
            )

            # 중단 처리
            if request.on_interrupt:
                try:
                    success = request.on_interrupt()
                    if not success:
                        self.logger.warning(f"작업 {operation_id} 중단 실패")
                except Exception as e:
                    self.logger.error(f"작업 {operation_id} 중단 중 오류: {e}")
                    success = False
            else:
                success = True

            # 정리 작업
            cleanup_success = True
            if request.on_cleanup:
                try:
                    cleanup_success = request.on_cleanup()
                except Exception as e:
                    self.logger.error(f"작업 {operation_id} 정리 중 오류: {e}")
                    cleanup_success = False

            # 중단 완료 이벤트 발행
            operation_info = self._active_operations.get(operation_id, {})
            files_processed = operation_info.get("files_processed", 0)
            files_remaining = operation_info.get("files_remaining", 0)

            self.event_bus.publish(
                OperationInterruptedEvent(
                    operation_id=operation_id,
                    operation_type=request.operation_type,
                    interrupt_reason=request.reason,
                    files_processed=files_processed,
                    files_remaining=files_remaining,
                    cleanup_successful=cleanup_success,
                )
            )

            # 활성 작업에서 제거
            with self._lock:
                if operation_id in self._active_operations:
                    del self._active_operations[operation_id]
                if operation_id in self._interruption_requests:
                    del self._interruption_requests[operation_id]

            self.logger.info(f"작업 {operation_id} 중단 완료")

        except Exception as e:
            self.logger.error(f"작업 {operation_id} 중단 처리 중 오류: {e}")

            # 오류와 함께 중단 완료 이벤트 발행
            self.event_bus.publish(
                OperationInterruptedEvent(
                    operation_id=operation_id,
                    operation_type=request.operation_type,
                    interrupt_reason=request.reason,
                    files_processed=0,
                    files_remaining=0,
                    cleanup_successful=False,
                    error_message=str(e),
                )
            )

        finally:
            # 중단 처리 중 표시 제거
            if operation_id in self._interruption_in_progress:
                del self._interruption_in_progress[operation_id]

    def _process_timeout_interruptions(self) -> None:
        """타임아웃된 중단 요청 처리"""
        current_time = datetime.now()

        with self._lock:
            timeout_requests = []
            for operation_id, request in self._interruption_requests.items():
                if (
                    request.max_wait_time_seconds
                    and (current_time - request.created_at).total_seconds()
                    > request.max_wait_time_seconds
                ):
                    timeout_requests.append(operation_id)

            for operation_id in timeout_requests:
                request = self._interruption_requests[operation_id]
                if request.force_interrupt_after_timeout:
                    self.logger.warning(f"작업 {operation_id} 타임아웃으로 강제 중단")
                    self._force_interrupt(operation_id)

    def _force_interrupt(self, operation_id: UUID) -> None:
        """강제 중단"""
        # 강제 중단 로직 구현
        # 실제로는 작업을 강제로 종료하는 로직이 필요

    def request_interruption(self, request: InterruptionRequest) -> bool:
        """중단 요청"""
        if not request.can_interrupt:
            self.logger.warning(f"작업 {request.operation_id}는 중단할 수 없습니다")
            return False

        # 중단 요청 추가
        with self._lock:
            self._interruption_requests[request.operation_id] = request

        self.logger.info(f"작업 {request.operation_id} 중단 요청됨")
        return True

    def can_interrupt_operation(self, operation_id: UUID) -> bool:
        """작업 중단 가능 여부 확인"""
        with self._lock:
            if operation_id in self._interruption_in_progress:
                return False

            if operation_id in self._interruption_requests:
                return False

            return operation_id in self._active_operations

    def get_active_operations(self) -> list[UUID]:
        """활성 작업 목록"""
        with self._lock:
            return list(self._active_operations.keys())

    def register_operation(
        self, operation_id: UUID, operation_type: str, total_files: int = 0
    ) -> None:
        """작업 등록"""
        with self._lock:
            self._active_operations[operation_id] = {
                "operation_type": operation_type,
                "total_files": total_files,
                "files_processed": 0,
                "files_remaining": total_files,
                "started_at": datetime.now(),
                "status": "running",
            }

        self.logger.info(f"작업 {operation_id} 등록됨: {operation_type}")

    def update_operation_progress(
        self, operation_id: UUID, files_processed: int, files_remaining: int
    ) -> None:
        """작업 진행률 업데이트"""
        with self._lock:
            if operation_id in self._active_operations:
                self._active_operations[operation_id]["files_processed"] = files_processed
                self._active_operations[operation_id]["files_remaining"] = files_remaining

    def complete_operation(self, operation_id: UUID) -> None:
        """작업 완료"""
        with self._lock:
            if operation_id in self._active_operations:
                self._active_operations[operation_id]["status"] = "completed"
                self._active_operations[operation_id]["completed_at"] = datetime.now()

        self.logger.info(f"작업 {operation_id} 완료됨")

    def resume_operation(self, operation_id: UUID, resume_from_file: Path | None = None) -> bool:
        """작업 재개"""
        if operation_id not in self._active_operations:
            self.logger.warning(f"작업 {operation_id}를 찾을 수 없습니다")
            return False

        # 재개 요청 이벤트 발행
        self.event_bus.publish(
            OperationResumeRequestedEvent(
                operation_id=operation_id,
                operation_type=self._active_operations[operation_id]["operation_type"],
                resume_from_file=resume_from_file,
                skip_processed_files=True,
            )
        )

        # 중단 요청 제거
        with self._lock:
            if operation_id in self._interruption_requests:
                del self._interruption_requests[operation_id]

        self.logger.info(f"작업 {operation_id} 재개 요청됨")
        return True

    def get_operation_info(self, operation_id: UUID) -> dict[str, Any] | None:
        """작업 정보 조회"""
        with self._lock:
            return self._active_operations.get(operation_id)

    def cleanup_old_operations(self, max_age_hours: float = 24.0) -> int:
        """오래된 작업 정보 정리"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        cleaned_count = 0

        with self._lock:
            operations_to_remove = []
            for operation_id, info in self._active_operations.items():
                started_at = info.get("started_at")
                if started_at and started_at.timestamp() < cutoff_time:
                    operations_to_remove.append(operation_id)

            for operation_id in operations_to_remove:
                del self._active_operations[operation_id]
                cleaned_count += 1

        if cleaned_count > 0:
            self.logger.info(f"{cleaned_count}개 오래된 작업 정보 정리됨")

        return cleaned_count

    def shutdown(self) -> None:
        """중단 매니저 종료"""
        self.logger.info("중단 매니저 종료 중...")

        # 중단 처리 스레드 종료
        self._stop_interruption_thread.set()
        if self._interruption_thread and self._interruption_thread.is_alive():
            self._interruption_thread.join(timeout=5.0)

        # 모든 활성 작업 중단
        with self._lock:
            for operation_id in list(self._active_operations.keys()):
                self._force_interrupt(operation_id)

        self.logger.info("중단 매니저 종료 완료")
