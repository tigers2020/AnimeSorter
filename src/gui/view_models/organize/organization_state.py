"""
파일 정리 상태 및 기능 관리 - Phase 3.2 뷰모델 분할
Organize ViewModel의 상태 관리 부분을 분리합니다.
"""

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass
from uuid import UUID


@dataclass
class OrganizationState:
    """파일 정리 상태 정보"""

    is_organizing: bool = False
    current_organization_id: UUID | None = None
    organization_mode: str = "simulation"
    total_files_to_process: int = 0
    processed_files_count: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    skipped_operations: int = 0
    organization_progress: int = 0
    current_operation: str = ""
    current_file: str = ""
    create_directories: bool = True
    overwrite_existing: bool = False
    use_hard_links: bool = False
    preserve_timestamps: bool = True
    backup_before_organize: bool = True
    last_error: str | None = None
    error_count: int = 0
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
