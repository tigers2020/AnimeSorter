"""
탭 델리게이트 컴포넌트 패키지 - Phase 2.3 결과 뷰 컴포넌트 분할
각 탭을 위한 독립적인 델리게이트 클래스들을 제공합니다.
"""

from .base_cell_delegate import BaseCellDelegate
from .status_delegate import StatusDelegate
from .text_preview_delegate import TextPreviewDelegate

__all__ = [
    "BaseCellDelegate",
    "TextPreviewDelegate",
    "StatusDelegate",
]
