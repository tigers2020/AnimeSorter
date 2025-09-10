"""
백그라운드 작업 서비스

이 모듈은 QThreadPool을 사용하여 백그라운드 작업들을 관리합니다.
작업 큐, 우선순위, 동시 실행 수 등을 제어합니다.
"""

import logging

logger = logging.getLogger(__name__)
from collections import deque
from typing import Protocol

from PyQt5.QtCore import QObject, QThreadPool, QTimer

from src.app.background_events import TaskQueueStatusEvent
from src.app.background_task import BaseTask, TaskStatus
from src.app.events import TypedEventBus


class IBackgroundTaskService(Protocol):
    """백그라운드 작업 서비스 인터페이스"""

    def submit_task(self, task: BaseTask) -> str:
        """작업 제출"""
        ...

    def cancel_task(self, task_id: str, reason: str = "사용자 요청") -> bool:
        """작업 취소"""
        ...

    def cancel_all_tasks(self, reason: str = "사용자 요청") -> int:
        """모든 작업 취소"""
        ...

    def get_task_status(self, task_id: str) -> TaskStatus | None:
        """작업 상태 조회"""
        ...

    def get_queue_status(self) -> dict[str, int]:
        """큐 상태 조회"""
        ...

    def set_max_concurrent_tasks(self, max_tasks: int) -> None:
        """최대 동시 실행 작업 수 설정"""
        ...

    def dispose(self) -> None:
        """서비스 정리"""
        ...


class BackgroundTaskService(QObject):
    """백그라운드 작업 서비스 구현"""

    def __init__(
        self,
        event_bus: TypedEventBus,
        max_concurrent_tasks: int = 4,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.event_bus = event_bus
        self.thread_pool = QThreadPool.globalInstance()
        if self.thread_pool is None:
            self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(max_concurrent_tasks)
        self.tasks: dict[str, BaseTask] = {}
        self.task_statuses: dict[str, TaskStatus] = {}
        self.pending_queue: deque[BaseTask] = deque()
        self.total_submitted = 0
        self.total_completed = 0
        self.total_failed = 0
        self.total_cancelled = 0
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._publish_queue_status)
        self._disposed = False
        self.logger.info(
            f"BackgroundTaskService 초기화 완료 (최대 동시 작업: {max_concurrent_tasks})"
        )

    def submit_task(self, task: BaseTask) -> str:
        """작업 제출"""
        if self._disposed:
            raise RuntimeError("BackgroundTaskService가 이미 정리되었습니다")
        task_id = task.task_id
        self.tasks[task_id] = task
        self.task_statuses[task_id] = TaskStatus.PENDING
        self.total_submitted += 1
        self._add_to_priority_queue(task)
        self.logger.info(f"작업 제출됨: {task.task_name} (ID: {task_id})")
        self._process_queue()
        return task_id

    def _add_to_priority_queue(self, task: BaseTask) -> None:
        """우선순위별 큐에 작업 추가"""
        inserted = False
        for i, existing_task in enumerate(self.pending_queue):
            if task.priority.value > existing_task.priority.value:
                self.pending_queue.insert(i, task)
                inserted = True
                break
        if not inserted:
            self.pending_queue.append(task)

    def _process_queue(self) -> None:
        """대기 중인 작업을 스레드풀에 제출"""
        if self.thread_pool is None:
            return
        while (
            self.pending_queue
            and self.thread_pool.activeThreadCount() < self.thread_pool.maxThreadCount()
        ):
            task = self.pending_queue.popleft()
            if not task.is_cancelled():
                self.task_statuses[task.task_id] = TaskStatus.RUNNING
                self.thread_pool.start(task)
                self.logger.debug(f"작업 실행 시작: {task.task_name} (ID: {task.task_id})")

    def cancel_task(self, task_id: str, reason: str = "사용자 요청") -> bool:
        """작업 취소"""
        if task_id not in self.tasks:
            self.logger.warning(f"존재하지 않는 작업 ID: {task_id}")
            return False
        task = self.tasks[task_id]
        current_status = self.task_statuses.get(task_id, TaskStatus.PENDING)
        if current_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.logger.warning(f"이미 완료된 작업은 취소할 수 없습니다: {task_id}")
            return False
        task.cancel(reason)
        self.task_statuses[task_id] = TaskStatus.CANCELLED
        self.total_cancelled += 1
        try:
            self.pending_queue.remove(task)
            self.logger.debug(f"대기 큐에서 작업 제거: {task_id}")
        except ValueError:
            pass
        self.logger.info(f"작업 취소됨: {task.task_name} (ID: {task_id}) - {reason}")
        return True

    def cancel_all_tasks(self, reason: str = "사용자 요청") -> int:
        """모든 작업 취소"""
        cancelled_count = 0
        for task_id, _task in self.tasks.items():
            if self.task_statuses.get(task_id) in [
                TaskStatus.PENDING,
                TaskStatus.RUNNING,
            ] and self.cancel_task(task_id, reason):
                cancelled_count += 1
        self.pending_queue.clear()
        self.logger.info(f"모든 작업 취소 완료: {cancelled_count}개 작업")
        return cancelled_count

    def get_task_status(self, task_id: str) -> TaskStatus | None:
        """작업 상태 조회"""
        return self.task_statuses.get(task_id)

    def get_queue_status(self) -> dict[str, int]:
        """큐 상태 조회"""
        running_count = sum(
            1 for status in self.task_statuses.values() if status == TaskStatus.RUNNING
        )
        pending_count = len(self.pending_queue)
        completed_count = self.total_completed
        failed_count = self.total_failed
        if self.thread_pool is None:
            return {
                "total_tasks": self.total_submitted,
                "running_tasks": running_count,
                "pending_tasks": pending_count,
                "completed_tasks": completed_count,
                "failed_tasks": failed_count,
                "cancelled_tasks": self.total_cancelled,
                "queue_size": pending_count,
                "max_concurrent_tasks": 0,
                "active_threads": 0,
            }
        return {
            "total_tasks": self.total_submitted,
            "running_tasks": running_count,
            "pending_tasks": pending_count,
            "completed_tasks": completed_count,
            "failed_tasks": failed_count,
            "cancelled_tasks": self.total_cancelled,
            "queue_size": pending_count,
            "max_concurrent_tasks": self.thread_pool.maxThreadCount(),
            "active_threads": self.thread_pool.activeThreadCount(),
        }

    def set_max_concurrent_tasks(self, max_tasks: int) -> None:
        """최대 동시 실행 작업 수 설정"""
        if max_tasks < 1:
            raise ValueError("최대 동시 작업 수는 1 이상이어야 합니다")
        if self.thread_pool is None:
            return
        old_count = self.thread_pool.maxThreadCount()
        self.thread_pool.setMaxThreadCount(max_tasks)
        self.logger.info(f"최대 동시 작업 수 변경: {old_count} → {max_tasks}")
        if max_tasks > old_count:
            self._process_queue()

    def enable_status_updates(self, enabled: bool = True, interval_ms: int = 5000) -> None:
        """상태 업데이트 활성화/비활성화"""
        if enabled:
            if not self.status_timer.isActive():
                self.status_timer.start(interval_ms)
                self.logger.info(f"작업 큐 상태 업데이트 활성화됨 ({interval_ms}ms 간격)")
        elif self.status_timer.isActive():
            self.status_timer.stop()
            self.logger.info("작업 큐 상태 업데이트 비활성화됨")

    def _publish_queue_status(self) -> None:
        """큐 상태를 EventBus로 발행"""
        if self._disposed:
            return
        status = self.get_queue_status()
        try:
            self.event_bus.publish(
                TaskQueueStatusEvent(
                    total_tasks=status["total_tasks"],
                    running_tasks=status["running_tasks"],
                    pending_tasks=status["pending_tasks"],
                    completed_tasks=status["completed_tasks"],
                    failed_tasks=status["failed_tasks"],
                    queue_size=status["queue_size"],
                    max_concurrent_tasks=status["max_concurrent_tasks"],
                )
            )
        except Exception as e:
            self.logger.error(f"큐 상태 발행 실패: {e}")

    def _cleanup_completed_tasks(self) -> None:
        """완료된 작업들 정리 (메모리 절약)"""
        completed_task_ids = []
        for task_id, status in self.task_statuses.items():
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                completed_task_ids.append(task_id)
        if len(completed_task_ids) > 100:
            for task_id in completed_task_ids[:-100]:
                del self.tasks[task_id]
                del self.task_statuses[task_id]

    def dispose(self) -> None:
        """서비스 정리"""
        if self._disposed:
            return
        self.logger.info("BackgroundTaskService 정리 시작")
        self.status_timer.stop()
        cancelled_count = self.cancel_all_tasks("서비스 종료")
        if self.thread_pool is not None and not self.thread_pool.waitForDone(5000):
            self.logger.warning("QThreadPool 정리 타임아웃 (5초)")
        self.tasks.clear()
        self.task_statuses.clear()
        self.pending_queue.clear()
        self._disposed = True
        self.logger.info(f"BackgroundTaskService 정리 완료 (취소된 작업: {cancelled_count}개)")
