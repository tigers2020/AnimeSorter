"""
메타데이터 상태 및 기능 관리 - Phase 3.5 뷰모델 분할
Metadata ViewModel의 상태 관리 부분을 분리합니다.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class MetadataState:
    """메타데이터 상태 정보"""

    # 메타데이터 검색 상태
    is_searching_metadata: bool = False
    current_search_id: UUID | None = None
    search_query: str = ""

    # 메타데이터 처리 상태
    is_processing_metadata: bool = False
    current_processing_id: UUID | None = None

    # 메타데이터 결과
    total_files_with_metadata: int = 0
    files_without_metadata: int = 0
    metadata_quality_score: float = 0.0

    # 진행률
    metadata_search_progress: int = 0
    metadata_processing_progress: int = 0
    current_operation: str = ""
    current_file: str = ""

    # 메타데이터 소스
    tmdb_enabled: bool = True
    anidb_enabled: bool = False
    myanimelist_enabled: bool = False

    # 오류 정보
    last_error: str | None = None
    error_count: int = 0

    # 메타데이터 통계
    successful_searches: int = 0
    failed_searches: int = 0
    partial_matches: int = 0
    exact_matches: int = 0


@dataclass
class MetadataCapabilities:
    """메타데이터 관련 UI 기능들"""

    can_start_metadata_search: bool = True
    can_stop_metadata_search: bool = False
    can_start_metadata_processing: bool = False
    can_stop_metadata_processing: bool = False
    can_edit_metadata: bool = False
    can_export_metadata: bool = False
    can_import_metadata: bool = True
    can_validate_metadata: bool = False
    can_bulk_edit_metadata: bool = False

    @classmethod
    def searching(cls) -> "MetadataCapabilities":
        """메타데이터 검색 중일 때의 기능 상태"""
        return cls(
            can_start_metadata_search=False,
            can_stop_metadata_search=True,
            can_start_metadata_processing=False,
            can_stop_metadata_processing=False,
            can_edit_metadata=False,
            can_export_metadata=False,
            can_import_metadata=False,
            can_validate_metadata=False,
            can_bulk_edit_metadata=False,
        )

    @classmethod
    def processing(cls) -> "MetadataCapabilities":
        """메타데이터 처리 중일 때의 기능 상태"""
        return cls(
            can_start_metadata_search=False,
            can_stop_metadata_search=False,
            can_start_metadata_processing=False,
            can_stop_metadata_processing=True,
            can_edit_metadata=False,
            can_export_metadata=False,
            can_import_metadata=False,
            can_validate_metadata=False,
            can_bulk_edit_metadata=False,
        )

    @classmethod
    def has_metadata(cls) -> "MetadataCapabilities":
        """메타데이터가 있을 때의 기능 상태"""
        return cls(
            can_start_metadata_search=True,
            can_stop_metadata_search=False,
            can_start_metadata_processing=True,
            can_stop_metadata_processing=False,
            can_edit_metadata=True,
            can_export_metadata=True,
            can_import_metadata=True,
            can_validate_metadata=True,
            can_bulk_edit_metadata=True,
        )
