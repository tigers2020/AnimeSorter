"""
프리플라이트 검사 시스템

파일 조작 전 안전성 검사를 통한 데이터 손실 방지
"""

import logging

logger = logging.getLogger(__name__)
from .base_checker import (BasePreflightChecker, IPreflightChecker,
                           PreflightIssue, PreflightResult, PreflightSeverity)
from .file_checkers import (CircularReferenceChecker, DiskSpaceChecker,
                            FileConflictChecker, FileLockChecker,
                            PathValidityChecker, PermissionChecker)
from .preflight_coordinator import (IPreflightCoordinator,
                                    PreflightCheckResult, PreflightCoordinator)
from .preflight_events import (BatchPreflightCompletedEvent,
                               BatchPreflightStartedEvent,
                               PreflightCheckFailedEvent,
                               PreflightCompletedEvent,
                               PreflightIssueFoundEvent, PreflightStartedEvent)

__all__ = [
    "BasePreflightChecker",
    "PreflightResult",
    "PreflightSeverity",
    "PreflightIssue",
    "IPreflightChecker",
    "FileConflictChecker",
    "PermissionChecker",
    "DiskSpaceChecker",
    "PathValidityChecker",
    "CircularReferenceChecker",
    "FileLockChecker",
    "PreflightCoordinator",
    "IPreflightCoordinator",
    "PreflightCheckResult",
    "PreflightStartedEvent",
    "PreflightCompletedEvent",
    "PreflightIssueFoundEvent",
    "PreflightCheckFailedEvent",
    "BatchPreflightStartedEvent",
    "BatchPreflightCompletedEvent",
]
