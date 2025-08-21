"""
파일 스캔 서비스

MainWindow의 파일 스캔 로직을 분리한 서비스입니다.
백그라운드 작업을 통해 UI를 블로킹하지 않고 스캔을 수행합니다.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID, uuid4

from ..events import TypedEventBus
from .background_task_service import IBackgroundTaskService
from .file_scan_task import FileScanTask


class IFileScanService(ABC):
    """파일 스캔 서비스 인터페이스"""

    @abstractmethod
    def scan_directory(
        self,
        directory_path: Path,
        recursive: bool = True,
        extensions: set[str] | None = None,
        min_file_size: int = 1024 * 1024,  # 1MB
        max_file_size: int = 50 * 1024 * 1024 * 1024,  # 50GB
    ) -> UUID:
        """디렉토리 스캔 시작 (스캔 ID 반환)"""

    @abstractmethod
    def scan_files(
        self,
        file_paths: list[Path],
        extensions: set[str] | None = None,
        min_file_size: int = 1024 * 1024,  # 1MB
        max_file_size: int = 50 * 1024 * 1024 * 1024,  # 50GB
    ) -> UUID:
        """파일 목록 스캔 시작 (스캔 ID 반환)"""

    @abstractmethod
    def cancel_scan(self, scan_id: UUID) -> bool:
        """스캔 취소"""

    @abstractmethod
    def dispose(self) -> None:
        """서비스 정리"""


class FileScanService(IFileScanService):
    """파일 스캔 서비스 구현 (백그라운드 작업 기반)"""

    def __init__(self, event_bus: TypedEventBus, background_task_service: IBackgroundTaskService):
        self.event_bus = event_bus
        self.background_task_service = background_task_service
        self.logger = logging.getLogger(self.__class__.__name__)
        self._active_scans: dict[UUID, UUID] = {}  # scan_id -> background_task_id

        self.logger.info("FileScanService 초기화 완료 (백그라운드 처리)")

    def scan_directory(
        self,
        directory_path: Path,
        recursive: bool = True,
        extensions: set[str] | None = None,
        min_file_size: int = 1024 * 1024,  # 1MB
        max_file_size: int = 50 * 1024 * 1024 * 1024,  # 50GB
    ) -> UUID:
        """디렉토리 스캔 시작 (백그라운드 실행)"""
        scan_id = uuid4()
        self.logger.info(f"백그라운드 디렉토리 스캔 시작: {directory_path} (스캔 ID: {scan_id})")

        # FileScanTask 생성
        scan_task = FileScanTask(
            scan_id=scan_id,
            directory_path=directory_path,
            recursive=recursive,
            extensions=extensions
            or {".mkv", ".mp4", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"},
            min_file_size=min_file_size,
            max_file_size=max_file_size,
            event_bus=self.event_bus,
        )

        # 백그라운드 작업 제출
        background_task_id = self.background_task_service.submit_task(scan_task)
        self._active_scans[scan_id] = background_task_id

        self.logger.info(
            f"디렉토리 스캔 작업 제출됨: {scan_id} (백그라운드 태스크 ID: {background_task_id})"
        )
        return scan_id

    def scan_files(
        self,
        file_paths: list[Path],
        extensions: set[str] | None = None,
        min_file_size: int = 1024 * 1024,  # 1MB
        max_file_size: int = 50 * 1024 * 1024 * 1024,  # 50GB
    ) -> UUID:
        """파일 목록 스캔 시작 (백그라운드 실행)"""
        scan_id = uuid4()
        self.logger.info(
            f"백그라운드 파일 스캔 시작: {len(file_paths)}개 파일 (스캔 ID: {scan_id})"
        )

        # FileScanTask 생성
        scan_task = FileScanTask(
            scan_id=scan_id,
            file_paths=file_paths,
            extensions=extensions
            or {".mkv", ".mp4", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"},
            min_file_size=min_file_size,
            max_file_size=max_file_size,
            event_bus=self.event_bus,
        )

        # 백그라운드 작업 제출
        background_task_id = self.background_task_service.submit_task(scan_task)
        self._active_scans[scan_id] = background_task_id

        self.logger.info(
            f"파일 목록 스캔 작업 제출됨: {scan_id} (백그라운드 태스크 ID: {background_task_id})"
        )
        return scan_id

    def cancel_scan(self, scan_id: UUID) -> bool:
        """스캔 취소"""
        if scan_id not in self._active_scans:
            self.logger.warning(f"취소할 스캔을 찾을 수 없음: {scan_id}")
            return False

        background_task_id = self._active_scans[scan_id]
        success = self.background_task_service.cancel_task(background_task_id)

        if success:
            self.logger.info(
                f"스캔 취소 성공: {scan_id} (백그라운드 태스크 ID: {background_task_id})"
            )
            self._active_scans.pop(scan_id)
        else:
            self.logger.warning(
                f"스캔 취소 실패: {scan_id} (백그라운드 태스크 ID: {background_task_id})"
            )

        return success

    def dispose(self) -> None:
        """서비스 정리"""
        # 모든 활성 스캔 취소
        for scan_id in list(self._active_scans.keys()):
            self.cancel_scan(scan_id)

        self.logger.info("FileScanService 정리 완료")
