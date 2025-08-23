"""
파일 스캔 상태 및 기능 관리 - Phase 3.6 뷰모델 분할
Scan ViewModel의 상태 관리 부분을 분리합니다.
"""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class ScanState:
    """파일 스캔 상태 정보"""

    # 스캔 진행 상태
    is_scanning: bool = False
    current_scan_id: UUID | None = None
    scanned_directory: str = ""

    # 스캔 설정
    recursive_scan: bool = True
    supported_extensions: set[str] = field(
        default_factory=lambda: {".mkv", ".mp4", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"}
    )
    min_file_size: int = 1024 * 1024  # 1MB
    max_file_size: int = 50 * 1024 * 1024 * 1024  # 50GB
    include_hidden_files: bool = False

    # 스캔 결과
    total_files_found: int = 0
    total_directories_scanned: int = 0
    files_by_extension: dict = field(default_factory=dict)
    files_by_size_range: dict = field(default_factory=dict)

    # 진행률
    scan_progress: int = 0
    current_operation: str = ""
    current_file: str = ""
    current_directory: str = ""

    # 오류 정보
    last_error: str | None = None
    error_count: int = 0
    skipped_files: int = 0
    access_denied_files: int = 0

    # 스캔 통계
    total_size_scanned: int = 0
    average_file_size: float = 0.0
    largest_file_size: int = 0
    smallest_file_size: int = 0


@dataclass
class ScanCapabilities:
    """파일 스캔 관련 UI 기능들"""

    can_start_scan: bool = True
    can_stop_scan: bool = False
    can_pause_scan: bool = False
    can_resume_scan: bool = False
    can_clear_scan_results: bool = False
    can_export_scan_results: bool = False
    can_save_scan_configuration: bool = True
    can_load_scan_configuration: bool = True

    @classmethod
    def scanning(cls) -> "ScanCapabilities":
        """스캔 중일 때의 기능 상태"""
        return cls(
            can_start_scan=False,
            can_stop_scan=True,
            can_pause_scan=True,
            can_resume_scan=False,
            can_clear_scan_results=False,
            can_export_scan_results=False,
            can_save_scan_configuration=False,
            can_load_scan_configuration=False,
        )

    @classmethod
    def paused(cls) -> "ScanCapabilities":
        """스캔 일시정지 상태일 때의 기능 상태"""
        return cls(
            can_start_scan=False,
            can_stop_scan=True,
            can_pause_scan=False,
            can_resume_scan=True,
            can_clear_scan_results=False,
            can_export_scan_results=False,
            can_save_scan_configuration=False,
            can_load_scan_configuration=False,
        )

    @classmethod
    def completed(cls) -> "ScanCapabilities":
        """스캔 완료 상태일 때의 기능 상태"""
        return cls(
            can_start_scan=True,
            can_stop_scan=False,
            can_pause_scan=False,
            can_resume_scan=False,
            can_clear_scan_results=True,
            can_export_scan_results=True,
            can_save_scan_configuration=True,
            can_load_scan_configuration=True,
        )
