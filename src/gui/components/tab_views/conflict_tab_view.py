"""
충돌 탭 뷰 클래스 - 충돌 파일 그룹을 표시하는 탭
"""

from src.base_tab_view import BaseTabView


class ConflictTabView(BaseTabView):
    """충돌 탭 뷰 클래스"""

    def __init__(self, parent=None):
        super().__init__("⚠️ 충돌", "📋 충돌 애니메이션 그룹", parent)
