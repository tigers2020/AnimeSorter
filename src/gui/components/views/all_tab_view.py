"""
전체 탭 뷰 클래스 - 모든 파일 그룹을 표시하는 탭
"""

import logging

logger = logging.getLogger(__name__)
from src.base_tab_view import BaseTabView


class AllTabView(BaseTabView):
    """전체 탭 뷰 클래스"""

    def __init__(self, parent=None):
        super().__init__("📁 전체", "📋 모든 애니메이션 그룹", parent)
