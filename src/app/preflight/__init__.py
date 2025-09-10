"""
프리플라이트 검사 시스템

파일 조작 전 안전성 검사를 통한 데이터 손실 방지
"""

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
    # Base
    "BasePreflightChecker",
    "PreflightResult",
    "PreflightSeverity",
    "PreflightIssue",
    "IPreflightChecker",
    # Checkers
    "FileConflictChecker",
    "PermissionChecker",
    "DiskSpaceChecker",
    "PathValidityChecker",
    "CircularReferenceChecker",
    "FileLockChecker",
    # Coordinator
    "PreflightCoordinator",
    "IPreflightCoordinator",
    "PreflightCheckResult",
    # Events
    "PreflightStartedEvent",
    "PreflightCompletedEvent",
    "PreflightIssueFoundEvent",
    "PreflightCheckFailedEvent",
    "BatchPreflightStartedEvent",
    "BatchPreflightCompletedEvent",
]
