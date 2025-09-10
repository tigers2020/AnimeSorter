"""
프리플라이트 검사 관련 이벤트

검사 시작, 완료, 문제 발견 등의 이벤트 정의
"""

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from src.app.events import BaseEvent
from src.app.preflight.base_checker import PreflightIssue
from src.app.preflight.preflight_coordinator import PreflightCheckResult


@dataclass
class PreflightStartedEvent(BaseEvent):
    """프리플라이트 검사 시작 이벤트"""

    check_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    operation_type: str = ""
    source_path: Path | None = None
    destination_path: Path | None = None
    total_operations: int = 0
    enabled_checkers: list[str] = field(default_factory=list)


@dataclass
class PreflightCompletedEvent(BaseEvent):
    """프리플라이트 검사 완료 이벤트"""

    check_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    result: PreflightCheckResult | None = None
    success: bool = True
    total_issues: int = 0
    blocking_issues: int = 0
    warning_issues: int = 0
    check_duration_ms: float = 0.0


@dataclass
class PreflightIssueFoundEvent(BaseEvent):
    """프리플라이트 검사에서 문제 발견 이벤트"""

    check_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    checker_name: str = ""
    issue: PreflightIssue | None = None
    severity: str = ""
    title: str = ""
    description: str = ""
    affected_files: list[Path] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class PreflightCheckFailedEvent(BaseEvent):
    """프리플라이트 검사 실패 이벤트"""

    check_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    checker_name: str = ""
    error_type: str = ""
    error_message: str = ""
    source_path: Path | None = None
    destination_path: Path | None = None


@dataclass
class BatchPreflightStartedEvent(BaseEvent):
    """배치 프리플라이트 검사 시작 이벤트"""

    batch_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    total_operations: int = 0
    operation_summary: str = ""
    enabled_checkers: list[str] = field(default_factory=list)
    estimated_duration_ms: float | None = None


@dataclass
class BatchPreflightProgressEvent(BaseEvent):
    """배치 프리플라이트 검사 진행 상황 이벤트"""

    batch_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    completed_checkers: int = 0
    total_checkers: int = 0
    current_checker: str = ""
    progress_percentage: float = 0.0
    issues_found_so_far: int = 0


@dataclass
class BatchPreflightCompletedEvent(BaseEvent):
    """배치 프리플라이트 검사 완료 이벤트"""

    batch_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    result: PreflightCheckResult | None = None
    success: bool = True
    total_operations: int = 0
    total_issues: int = 0
    blocking_issues: int = 0
    warning_issues: int = 0
    total_duration_ms: float = 0.0
    can_proceed: bool = False


@dataclass
class PreflightUserDecisionEvent(BaseEvent):
    """프리플라이트 검사 후 사용자 결정 이벤트"""

    check_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))
    decision: str = ""
    proceed_with_warnings: bool = False
    ignored_warnings: list[str] = field(default_factory=list)
    user_notes: str = ""


@dataclass
class PreflightSettingsChangedEvent(BaseEvent):
    """프리플라이트 검사 설정 변경 이벤트"""

    enabled_checkers: list[str] = field(default_factory=list)
    disabled_checkers: list[str] = field(default_factory=list)
    severity_overrides: dict = field(default_factory=dict)
    auto_proceed_on_warnings: bool = False
