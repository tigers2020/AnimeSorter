"""
파일 스캔 서비스

MainWindow의 파일 스캔 로직을 분리한 서비스입니다.
백그라운드 작업을 통해 UI를 블로킹하지 않고 스캔을 수행합니다.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from ..background_events import TaskPriority
from ..events import TypedEventBus
from .background_task_service import IBackgroundTaskService
from .file_scan_task import FileScanTask


class IFileScanService(ABC):
    """파일 스캔 서비스 인터페이스"""

    @abstractmethod
    def scan_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        extensions: Optional[set[str]] = None,
        min_size_mb: float = 1.0,
        max_size_gb: float = 50.0,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """디렉토리 스캔 시작 (작업 ID 반환)"""

    @abstractmethod
    def cancel_scan(self, task_id: Optional[str] = None) -> bool:
        """스캔 취소"""

    @abstractmethod
    def dispose(self) -> None:
        """서비스 정리"""


class FileScanService:
    """파일 스캔 서비스 구현 (백그라운드 작업 기반)"""

    def __init__(self, event_bus: TypedEventBus, background_task_service: IBackgroundTaskService):
        self.event_bus = event_bus
        self.background_task_service = background_task_service
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_task_id: Optional[str] = None

        self.logger.info("FileScanService 초기화 완료 (백그라운드 처리)")

    def scan_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        extensions: Optional[set[str]] = None,
        min_size_mb: float = 1.0,
        max_size_gb: float = 50.0,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """디렉토리 스캔 시작 (백그라운드 실행)"""
        self.logger.info(f"백그라운드 파일 스캔 시작: {directory_path}")

        # FileScanTask 생성
        scan_task = FileScanTask(
            event_bus=self.event_bus,
            directory_path=directory_path,
            recursive=recursive,
            extensions=extensions,
            min_size_mb=min_size_mb,
            max_size_gb=max_size_gb,
            priority=priority,
        )

        # 백그라운드 작업 제출
        task_id = self.background_task_service.submit_task(scan_task)
        self.current_task_id = task_id

        self.logger.info(f"파일 스캔 작업 제출됨: {task_id}")
        return task_id

    def cancel_scan(self, task_id: Optional[str] = None) -> bool:
        """스캔 취소"""
        target_id = task_id or self.current_task_id

        if not target_id:
            self.logger.warning("취소할 스캔 작업이 없습니다")
            return False

        success = self.background_task_service.cancel_task(target_id, "사용자 요청")

        if success:
            self.logger.info(f"스캔 작업 취소됨: {target_id}")
            if target_id == self.current_task_id:
                self.current_task_id = None
        else:
            self.logger.warning(f"스캔 작업 취소 실패: {target_id}")

        return success

    def dispose(self) -> None:
        """서비스 정리"""
        if self.current_task_id:
            self.cancel_scan()

        self.logger.info("FileScanService 정리 완료")
