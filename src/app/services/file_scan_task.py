"""
파일 스캔 백그라운드 작업

FileScanService의 로직을 BaseTask 기반으로 재구현하여
백그라운드에서 실행되도록 합니다.
"""

import logging
import time
from pathlib import Path
from uuid import uuid4

from src.app.application_events import FilesScannedEvent, ScanStatus
from src.app.background_events import TaskPriority
from src.app.background_task import BaseTask, TaskResult
from src.app.events import TypedEventBus


class FileScanTask(BaseTask):
    """파일 스캔 백그라운드 작업"""

    def __init__(
        self,
        event_bus: TypedEventBus,
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

        self.logger = logging.getLogger(f"FileScanTask_{self.task_id[:8]}")

    def execute(self) -> TaskResult:
        """파일 스캔 실행"""
        self.logger.info(f"파일 스캔 시작: {self.directory_path}")

        if not self.directory_path.exists():
            raise FileNotFoundError(f"디렉토리가 존재하지 않습니다: {self.directory_path}")

        if not self.directory_path.is_dir():
            raise NotADirectoryError(f"디렉토리가 아닙니다: {self.directory_path}")

        scanned_files: list[str] = []
        start_time = time.time()

        try:
            # 1단계: 파일 목록 수집
            self.update_progress(10, "파일 목록 수집 중...")
            all_files = self._collect_files()

            if self.is_cancelled():
                return self._create_cancelled_result()

            total_files = len(all_files)
            self.logger.info(f"총 {total_files}개 파일 발견")

            # 2단계: 파일 필터링 및 처리
            self.update_progress(20, "파일 필터링 중...")

            for i, file_path in enumerate(all_files):
                if self.is_cancelled():
                    break

                try:
                    if self._should_include_file(file_path):
                        scanned_files.append(str(file_path))
                        self.increment_processed(1, True)

                    # 진행률 업데이트 (20% ~ 90%)
                    progress = 20 + int((i / total_files) * 70)
                    self.update_progress(progress, f"파일 처리 중... ({i + 1}/{total_files})")

                except Exception as e:
                    self.logger.warning(f"파일 처리 실패: {file_path} - {e}")
                    self.increment_processed(1, False)

            if self.is_cancelled():
                return self._create_cancelled_result()

            # 3단계: 결과 정리
            self.update_progress(95, "결과 정리 중...")

            # FilesScannedEvent 발행 (올바른 매개변수 사용)
            scan_event = FilesScannedEvent(
                scan_id=uuid4(),
                directory_path=self.directory_path,
                found_files=[Path(f) for f in scanned_files],
                scan_duration_seconds=time.time() - start_time,
                status=ScanStatus.COMPLETED,
            )

            self.event_bus.publish(scan_event)
            self.logger.info(f"FilesScannedEvent 발행: {len(scanned_files)}개 파일")

            self.update_progress(100, "스캔 완료")

            # 성공 결과 반환
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

    def _collect_files(self) -> list[Path]:
        """파일 목록 수집"""
        files = []

        try:
            if self.recursive:
                # 재귀적 스캔
                for file_path in self.directory_path.rglob("*"):
                    if self.is_cancelled():
                        break

                    if file_path.is_file():
                        files.append(file_path)
            else:
                # 현재 디렉토리만
                for file_path in self.directory_path.iterdir():
                    if self.is_cancelled():
                        break

                    if file_path.is_file():
                        files.append(file_path)

        except Exception as e:
            self.logger.error(f"파일 목록 수집 실패: {e}")
            raise

        return files

    def _should_include_file(self, file_path: Path) -> bool:
        """파일 포함 여부 확인"""
        try:
            # 확장자 검사
            if file_path.suffix.lower() not in self.extensions:
                return False

            # 파일 크기 검사
            file_size = file_path.stat().st_size
            if file_size < self.min_size_bytes:
                return False

            return not file_size > self.max_size_bytes

        except Exception as e:
            self.logger.warning(f"파일 검사 실패: {file_path} - {e}")
            return False

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
