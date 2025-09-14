"""
스테이징 모듈

파일 작업을 안전하게 수행하기 위한 스테이징 디렉토리 시스템
Phase 3 요구사항: 모든 파일 조작 전 스테이징 디렉토리에서 준비
"""

import logging

logger = logging.getLogger(__name__)
from .staging_manager import IStagingManager, StagedFile, StagingConfiguration, StagingManager

__all__ = ["StagingManager", "IStagingManager", "StagingConfiguration", "StagedFile"]
