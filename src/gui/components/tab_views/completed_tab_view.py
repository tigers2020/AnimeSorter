"""
완료 탭 뷰 클래스 - 완료된 파일 그룹을 표시하는 탭
"""

from .base_tab_view import BaseTabView


class CompletedTabView(BaseTabView):
    """완료 탭 뷰 클래스"""

    def __init__(self, parent=None):
        super().__init__("✅ 완료", "📋 완료된 애니메이션 그룹", parent)
