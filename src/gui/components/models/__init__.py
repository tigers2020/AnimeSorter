"""
탭 모델 컴포넌트 패키지 - Phase 2.2 결과 뷰 컴포넌트 분할
각 탭을 위한 독립적인 모델 클래스들을 제공합니다.
"""

import logging

logger = logging.getLogger(__name__)
from .base_detail_model import BaseDetailModel
from .base_group_model import BaseGroupModel

__all__ = ["BaseGroupModel", "BaseDetailModel"]
