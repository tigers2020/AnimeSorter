"""
파일 정리 상태 및 기능 관리 - Phase 3.2 뷰모델 분할
Organize ViewModel의 상태 관리 부분을 분리합니다.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class OrganizationState:
    """파일 정리 상태 정보"""

    # 정리 진행 상태
    is_organizing: bool = False
    current_organization_id: UUID | None = None

    # 정리 모드
    organization_mode: str = "simulation"  # simulation, safe, normal, aggressive

    # 정리 결과
    total_files_to_process: int = 0
    processed_files_count: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    skipped_operations: int = 0

    # 진행률
    organization_progress: int = 0
    current_operation: str = ""
    current_file: str = ""

    # 정리 설정
    create_directories: bool = True
    overwrite_existing: bool = False
    use_hard_links: bool = False
    preserve_timestamps: bool = True
    backup_before_organize: bool = True

    # 오류 정보
    last_error: str | None = None
    error_count: int = 0

    # 정리 통계
    files_moved: int = 0
    files_renamed: int = 0
    files_deleted: int = 0
    directories_created: int = 0


@dataclass
class OrganizationCapabilities:
    """파일 정리 관련 UI 기능들"""

    can_start_organization: bool = True
    can_stop_organization: bool = False
    can_pause_organization: bool = False
    can_resume_organization: bool = False
    can_preview_organization: bool = True
    can_undo_last_operation: bool = False
    can_redo_last_operation: bool = False
    can_clear_organization_results: bool = False
    can_export_organization_log: bool = False

    @classmethod
    def organizing(cls) -> "OrganizationCapabilities":
        """정리 중일 때의 기능 상태"""
        return cls(
            can_start_organization=False,
            can_stop_organization=True,
            can_pause_organization=True,
            can_resume_organization=False,
            can_preview_organization=False,
            can_undo_last_operation=False,
            can_redo_last_operation=False,
            can_clear_organization_results=False,
            can_export_organization_log=False,
        )

    @classmethod
    def paused(cls) -> "OrganizationCapabilities":
        """정리 일시정지 상태일 때의 기능 상태"""
        return cls(
            can_start_organization=False,
            can_stop_organization=True,
            can_pause_organization=False,
            can_resume_organization=True,
            can_preview_organization=False,
            can_undo_last_operation=True,
            can_redo_last_operation=False,
            can_clear_organization_results=False,
            can_export_organization_log=True,
        )

    @classmethod
    def completed(cls) -> "OrganizationCapabilities":
        """정리 완료 상태일 때의 기능 상태"""
        return cls(
            can_start_organization=True,
            can_stop_organization=False,
            can_pause_organization=False,
            can_resume_organization=False,
            can_preview_organization=False,
            can_undo_last_operation=True,
            can_redo_last_operation=True,
            can_clear_organization_results=True,
            can_export_organization_log=True,
        )
