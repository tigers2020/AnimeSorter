"""
파일 스캔 백그라운드 작업

FileScanService의 로직을 BaseTask 기반으로 재구현하여
백그라운드에서 실행되도록 합니다.
리팩토링: 통합된 파일 조직화 서비스를 사용하여 중복 코드 제거
"""

import logging

logger = logging.getLogger(__name__)
import time
from pathlib import Path
from uuid import uuid4

from src.app.background_task import BaseTask, TaskResult
from src.core.event_bus import UnifiedEventBus
from src.core.events import TaskPriority
from src.core.events.event_publisher import event_publisher
from src.core.services.unified_file_organization_service import (
    FileOrganizationConfig, UnifiedFileOrganizationService)


class FileScanTask(BaseTask):
    """파일 스캔 백그라운드 작업"""

    def __init__(
        self,
        event_bus: UnifiedEventBus,
        directory_path: str,
        recursive: bool = True,
        extensions: set[str] | None = None,
        min_size_mb: float = 1.0,
        max_size_gb: float = 50.0,
        priority: TaskPriority = TaskPriority.NORMAL,
    ):
        super().__init__(
            event_bus=event_bus,
            task_name=f"파일 스캔: {Path(directory_path).name}",
            priority=priority,
            metadata={
                "directory_path": directory_path,
                "recursive": recursive,
                "extensions": list(extensions) if extensions else None,
                "min_size_mb": min_size_mb,
                "max_size_gb": max_size_gb,
            },
        )
        self.directory_path = Path(directory_path)
        self.recursive = recursive
        self.extensions = extensions or {
            ".mkv",
            ".mp4",
            ".avi",
            ".wmv",
            ".mov",
            ".flv",
            ".webm",
            ".m4v",
        }
        self.min_size_bytes = int(min_size_mb * 1024 * 1024)
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        config = FileOrganizationConfig(
            safe_mode=True,
            backup_before_operation=False,
            overwrite_existing=False,
            min_file_size=self.min_size_bytes,
        )
        self.unified_service = UnifiedFileOrganizationService(config)
        self.logger = logging.getLogger(f"FileScanTask_{self.task_id[:8]}")

    def execute(self) -> TaskResult:
        """파일 스캔 실행"""
        scan_id = str(uuid4())
        self.logger.info(f"파일 스캔 시작: {self.directory_path} (ID: {scan_id})")

        # 스캔 시작 이벤트 발행
        event_publisher.publish_scan_started(
            scan_id=scan_id,
            directory_path=str(self.directory_path),
            recursive=self.recursive,
            file_extensions=list(self.extensions),
        )

        if not self.directory_path.exists():
            event_publisher.publish_error(
                error_id=scan_id,
                error_type="file_operation_error",
                message=f"디렉토리가 존재하지 않습니다: {self.directory_path}",
                where="scan",
            )
            raise FileNotFoundError(f"디렉토리가 존재하지 않습니다: {self.directory_path}")
        if not self.directory_path.is_dir():
            event_publisher.publish_error(
                error_id=scan_id,
                error_type="file_operation_error",
                message=f"디렉토리가 아닙니다: {self.directory_path}",
                where="scan",
            )
            raise NotADirectoryError(f"디렉토리가 아닙니다: {self.directory_path}")

        scanned_files: list[str] = []
        start_time = time.time()
        try:
            self.update_progress(10, "파일 목록 수집 중...")
            event_publisher.publish_scan_progress(
                scan_id=scan_id,
                processed=0,
                total=0,
                current_step="파일 목록 수집 중",
                progress_percent=10.0,
            )

            # UnifiedFileOrganizationService의 scanner 사용
            scan_result = self.unified_service.scanner.scan_directory(
                self.directory_path,
                recursive=self.recursive,
                file_extensions=self.extensions,
            )
            scanned_files = [str(f) for f in scan_result.files_found]

            if self.is_cancelled():
                return self._create_cancelled_result()

            total_files = len(scanned_files)
            self.logger.info(f"총 {total_files}개 파일 발견")

            # 스캔 진행률 업데이트
            event_publisher.publish_scan_progress(
                scan_id=scan_id,
                processed=total_files,
                total=total_files,
                current_step="스캔 완료",
                progress_percent=95.0,
            )

            self.update_progress(95, "결과 정리 중...")

            if self.is_cancelled():
                return self._create_cancelled_result()

            # 스캔 완료 이벤트 발행
            duration = time.time() - start_time
            event_publisher.publish_scan_completed(
                scan_id=scan_id,
                found_files=scanned_files,
                stats={"total_files": total_files, "duration_seconds": duration},
                duration_seconds=duration,
                status="completed",
            )

            self.logger.info(f"스캔 완료 이벤트 발행: {len(scanned_files)}개 파일")
            self.update_progress(100, "스캔 완료")
            return TaskResult(
                task_id=self.task_id,
                status=self._status,
                success=True,
                result_data={
                    "scanned_files": scanned_files,
                    "total_files_found": len(scanned_files),
                    "directory_path": str(self.directory_path),
                    "scan_duration": time.time() - start_time,
                },
                items_processed=self._items_processed,
                success_count=self._success_count,
                error_count=self._error_count,
            )
        except Exception as e:
            self.logger.error(f"파일 스캔 실패: {e}")
            raise

    def _create_cancelled_result(self) -> TaskResult:
        """취소된 결과 생성"""
        return TaskResult(
            task_id=self.task_id,
            status=self._status,
            success=False,
            error_message="사용자에 의해 취소됨",
            items_processed=self._items_processed,
            success_count=self._success_count,
            error_count=self._error_count,
        )
