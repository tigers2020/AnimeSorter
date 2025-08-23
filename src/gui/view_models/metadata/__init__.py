"""
Metadata ViewModel 패키지 - Phase 3.5 뷰모델 분할
메타데이터 관리의 복잡한 ViewModel을 기능별로 분리하여 관리합니다.
"""

from .metadata_state import MetadataCapabilities, MetadataState
from .metadata_view_model import MetadataViewModel

__all__ = [
    "MetadataState",
    "MetadataCapabilities",
    "MetadataViewModel",
]
