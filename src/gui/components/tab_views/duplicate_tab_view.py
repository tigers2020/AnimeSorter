"""
중복 탭 뷰 클래스 - 중복 파일 그룹을 표시하는 탭
"""

from .base_tab_view import BaseTabView


class DuplicateTabView(BaseTabView):
    """중복 탭 뷰 클래스"""

    def __init__(self, parent=None):
        super().__init__("🔄 중복", "📋 중복 애니메이션 그룹", parent)
