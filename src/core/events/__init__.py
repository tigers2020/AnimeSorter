"""
AnimeSorter 핵심 이벤트 시스템

12개 핵심 이벤트로 통합된 이벤트 시스템을 제공합니다.
"""

from .core_events import CoreEvent, CoreEventType
from .payload_schemas import (ErrorPayload, OrganizeCompletedPayload,
                              OrganizeConflictPayload, OrganizeSkippedPayload,
                              OrganizeStartedPayload, PlanCreatedPayload,
                              PlanValidatedPayload, ScanCompletedPayload,
                              ScanProgressPayload, ScanStartedPayload,
                              SettingsChangedPayload,
                              UserActionRequiredPayload)

__all__ = [
    "CoreEvent",
    "CoreEventType",
    "ScanStartedPayload",
    "ScanProgressPayload",
    "ScanCompletedPayload",
    "PlanCreatedPayload",
    "PlanValidatedPayload",
    "OrganizeStartedPayload",
    "OrganizeConflictPayload",
    "OrganizeSkippedPayload",
    "OrganizeCompletedPayload",
    "UserActionRequiredPayload",
    "ErrorPayload",
    "SettingsChangedPayload",
]
