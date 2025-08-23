"""
공통 타입 정의 모듈

여러 모듈에서 공통으로 사용되는 타입들을 정의합니다.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FileOperationResult:
    """파일 작업 결과"""

    success: bool
    source_path: str
    destination_path: Optional[str] = None
    error_message: Optional[str] = None
    operation_type: str = ""  # copy, move, rename
    file_size: Optional[int] = None
    processing_time: Optional[float] = None
    backup_path: Optional[str] = None  # 백업 파일 경로

    @property
    def error(self) -> Optional[str]:
        """error_message 별칭 (테스트 호환성)"""
        return self.error_message

    @property
    def message(self) -> str:
        """상태 메시지 (테스트 호환성)"""
        if self.success:
            return f"작업 성공: {self.operation_type}"
        return f"작업 실패: {self.error_message or '알 수 없는 오류'}"


@dataclass
class FileValidationResult:
    """파일 검증 결과"""

    is_valid: bool
    file_path: str
    error_message: Optional[str] = None
    validation_type: str = ""  # path, permissions, disk_space, etc.


@dataclass
class FileBackupResult:
    """파일 백업 결과"""

    success: bool
    original_path: str
    backup_path: Optional[str] = None
    error_message: Optional[str] = None
    backup_size: Optional[int] = None
    backup_timestamp: Optional[str] = None


@dataclass
class FileNamingResult:
    """파일명 생성 결과"""

    success: bool
    original_name: str
    new_name: Optional[str] = None
    destination_path: Optional[str] = None
    error_message: Optional[str] = None
    naming_scheme: str = ""
