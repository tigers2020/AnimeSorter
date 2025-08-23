"""
미매칭 탭 뷰 클래스 - Phase 2.1 결과 뷰 컴포넌트 분할
미매칭 탭의 UI와 로직을 담당하는 독립적인 클래스입니다.
"""

from .base_tab_view import BaseTabView


class UnmatchedTabView(BaseTabView):
    """미매칭 탭 뷰 클래스"""

    def __init__(self, parent=None):
        super().__init__("⚠️ 미매칭", "📋 애니메이션 그룹", parent)
