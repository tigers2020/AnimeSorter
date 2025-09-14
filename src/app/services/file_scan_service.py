import logging
from abc import ABC, abstractmethod
from pathlib import Path

from src.core.constants import DEFAULT_VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)


class IFileScanService(ABC):
    """파일 스캔 서비스 인터페이스"""

    @abstractmethod
    def scan_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        extensions: set[str] | None = None,
        min_file_size: int = 0,
        max_file_size: int = 0,
    ) -> list[str]:
        """디렉토리를 스캔하여 파일 목록을 반환"""
        pass


class FileScanService(IFileScanService):
    """파일 스캔 서비스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def scan_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        extensions: set[str] | None = None,
        min_file_size: int = 0,
        max_file_size: int = 0,
    ) -> list[str]:
        """디렉토리를 스캔하여 파일 목록을 반환"""
        try:
            self.logger.info(f"디렉토리 스캔 시작: {directory_path}")

            directory = Path(directory_path)
            if not directory.exists():
                self.logger.error(f"디렉토리가 존재하지 않습니다: {directory_path}")
                return []

            # 지원하는 비디오 파일 확장자 (기본값)
            if extensions is None:
                extensions = DEFAULT_VIDEO_EXTENSIONS

            files = []
            pattern = "**/*" if recursive else "*"

            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    file_ext = file_path.suffix.lower()
                    if file_ext in extensions:
                        # 파일 크기 확인
                        try:
                            file_size = file_path.stat().st_size
                            if file_size >= min_file_size and (
                                max_file_size == 0 or file_size <= max_file_size
                            ):
                                files.append(str(file_path))
                        except OSError:
                            # 파일 크기를 가져올 수 없는 경우 무시
                            pass

            self.logger.info(f"스캔 완료: {len(files)}개 파일 발견")
            return files

        except Exception as e:
            self.logger.error(f"디렉토리 스캔 중 오류 발생: {e}")
            return []
