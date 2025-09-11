"""
백그라운드 작업 기본 클래스

이 모듈은 백그라운드에서 실행되는 작업들의 기본 구조를 정의합니다.
QRunnable을 기반으로 하여 QThreadPool에서 실행될 수 있습니다.
"""

import logging

logger = logging.getLogger(__name__)
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal

from src.core.events.event_publisher import event_publisher


class TaskPriority(Enum):
    """백그라운드 작업 우선순위"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """백그라운드 작업 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """백그라운드 작업 결과"""

    task_id: str
    status: TaskStatus
    success: bool = False
    result_data: Any = None
    error_message: str = ""
    error_details: str = ""
    items_processed: int = 0
    success_count: int = 0
    error_count: int = 0
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskSignals(QObject):
    """백그라운드 작업 시그널 (Qt 스레드 간 통신용)"""

    started = pyqtSignal(str)
    progress = pyqtSignal(str, int, str)
    completed = pyqtSignal(str, object)
    failed = pyqtSignal(str, str, str)
    cancelled = pyqtSignal(str, str)


class BaseTask(QRunnable):
    """백그라운드 작업 기본 클래스

    QRunnable을 상속받아 QThreadPool에서 실행될 수 있습니다.
    EventBus를 통해 작업 상태를 UI에 전달합니다.
    """

    def __init__(
        self,
        event_bus=None,
        task_name: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__()
        self.task_id = str(uuid4())
        self.task_name = task_name or self.__class__.__name__
        self.task_type = self.__class__.__name__
        self.priority = priority
        self.metadata = metadata or {}
        self.event_bus = event_bus or get_event_bus()
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{self.task_id[:8]}")
        self._status = TaskStatus.PENDING
        self._cancelled = False
        self._start_time: float | None = None
        self._items_processed = 0
        self._success_count = 0
        self._error_count = 0
        self.signals = TaskSignals()
        self._connect_signals()
        self.logger.debug(f"백그라운드 작업 생성: {self.task_name} (ID: {self.task_id})")

    def _connect_signals(self) -> None:
        """Qt 시그널을 EventBus에 연결"""
        self.signals.started.connect(self._on_started_signal)
        self.signals.progress.connect(self._on_progress_signal)
        self.signals.completed.connect(self._on_completed_signal)
        self.signals.failed.connect(self._on_failed_signal)
        self.signals.cancelled.connect(self._on_cancelled_signal)

    def _on_started_signal(self, task_id: str) -> None:
        """작업 시작 시그널 처리"""
        # 백그라운드 작업 시작은 로그로만 처리 (이벤트 시스템에서 제외)
        logger.info(f"🚀 백그라운드 작업 시작: {self.task_name} (ID: {task_id})")

    def _on_progress_signal(self, task_id: str, progress_percent: int, current_step: str) -> None:
        """진행률 시그널 처리"""
        elapsed_time = time.time() - (self._start_time or time.time())
        # 백그라운드 작업 진행률은 로그로만 처리 (이벤트 시스템에서 제외)
        logger.debug(f"📊 백그라운드 작업 진행률: {progress_percent}% - {current_step}")

    def _on_completed_signal(self, task_id: str, result: TaskResult) -> None:
        """작업 완료 시그널 처리"""
        # 백그라운드 작업 완료는 로그로만 처리 (이벤트 시스템에서 제외)
        logger.info(
            f"✅ 백그라운드 작업 완료: {self.task_name} (소요시간: {result.duration:.2f}초)"
        )

    def _on_failed_signal(self, task_id: str, error_message: str, error_details: str) -> None:
        """작업 실패 시그널 처리"""
        elapsed_time = time.time() - (self._start_time or time.time())
        # 백그라운드 작업 실패는 오류 이벤트로 발행
        event_publisher.publish_error(
            error_id=task_id,
            error_type="unknown_error",
            message=f"백그라운드 작업 실패: {error_message}",
            details=error_details,
            where="background_task",
        )

    def _on_cancelled_signal(self, task_id: str, reason: str) -> None:
        """작업 취소 시그널 처리"""
        elapsed_time = time.time() - (self._start_time or time.time())
        # 백그라운드 작업 취소는 로그로만 처리 (이벤트 시스템에서 제외)
        logger.info(f"🚫 백그라운드 작업 취소: {self.task_name} - {reason}")

    def run(self) -> None:
        """QRunnable.run() 구현 - 실제 작업 실행"""
        self._start_time = time.time()
        self._status = TaskStatus.RUNNING
        try:
            self.logger.info(f"백그라운드 작업 시작: {self.task_name}")
            self.signals.started.emit(self.task_id)
            result = self.execute()
            if self._cancelled:
                self._status = TaskStatus.CANCELLED
                self.signals.cancelled.emit(self.task_id, "사용자 요청")
                self.logger.info(f"백그라운드 작업 취소됨: {self.task_name}")
            else:
                self._status = TaskStatus.COMPLETED
                result.duration = time.time() - self._start_time
                result.items_processed = self._items_processed
                result.success_count = self._success_count
                result.error_count = self._error_count
                self.signals.completed.emit(self.task_id, result)
                self.logger.info(
                    f"백그라운드 작업 완료: {self.task_name} (소요시간: {result.duration:.2f}초)"
                )
        except Exception as e:
            self._status = TaskStatus.FAILED
            error_message = str(e)
            error_details = traceback.format_exc()
            self.signals.failed.emit(self.task_id, error_message, error_details)
            self.logger.error(f"백그라운드 작업 실패: {self.task_name} - {error_message}")
            self.logger.debug(f"상세 오류:\n{error_details}")

    def execute(self) -> TaskResult:
        """실제 작업 로직 구현 (서브클래스에서 구현)"""
        raise NotImplementedError("서브클래스에서 execute 메서드를 구현해야 합니다")

    def cancel(self, reason: str = "사용자 요청") -> None:
        """작업 취소 요청"""
        self._cancelled = True
        self.logger.info(f"작업 취소 요청: {self.task_name} - {reason}")

    def is_cancelled(self) -> bool:
        """취소 여부 확인"""
        return self._cancelled

    def update_progress(self, progress_percent: int, current_step: str = "") -> None:
        """진행률 업데이트"""
        if not self._cancelled:
            self.signals.progress.emit(self.task_id, progress_percent, current_step)

    def increment_processed(self, count: int = 1, success: bool = True) -> None:
        """처리된 항목 수 증가"""
        self._items_processed += count
        if success:
            self._success_count += count
        else:
            self._error_count += count

    @property
    def status(self) -> TaskStatus:
        """현재 작업 상태"""
        return self._status
