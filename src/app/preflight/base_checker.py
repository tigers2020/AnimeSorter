"""
프리플라이트 검사 기본 클래스

파일 조작 전 안전성 검사를 위한 기본 인터페이스와 구현
"""

import logging

logger = logging.getLogger(__name__)
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4


class PreflightSeverity(Enum):
    """프리플라이트 검사 문제의 심각도"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PreflightIssue:
    """프리플라이트 검사에서 발견된 문제"""

    checker_name: str
    severity: PreflightSeverity
    title: str
    description: str
    affected_files: list[Path] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_blocking(self) -> bool:
        """진행을 차단해야 하는 문제인지"""
        return self.severity in (PreflightSeverity.ERROR, PreflightSeverity.CRITICAL)

    @property
    def can_proceed_with_warning(self) -> bool:
        """경고와 함께 진행 가능한지"""
        return self.severity in (PreflightSeverity.INFO, PreflightSeverity.WARNING)


@dataclass
class PreflightResult:
    """프리플라이트 검사 결과"""

    checker_name: str
    check_id: UUID = field(default_factory=uuid4)
    success: bool = True
    issues: list[PreflightIssue] = field(default_factory=list)
    checked_files: list[Path] = field(default_factory=list)
    check_duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_blocking_issues(self) -> bool:
        """진행을 차단하는 문제가 있는지"""
        return any(issue.is_blocking for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        """경고가 있는지"""
        return any(issue.severity == PreflightSeverity.WARNING for issue in self.issues)

    @property
    def blocking_issues(self) -> list[PreflightIssue]:
        """진행을 차단하는 문제들"""
        return [issue for issue in self.issues if issue.is_blocking]

    @property
    def warning_issues(self) -> list[PreflightIssue]:
        """경고 문제들"""
        return [issue for issue in self.issues if issue.severity == PreflightSeverity.WARNING]

    def add_issue(self, issue: PreflightIssue) -> None:
        """문제 추가"""
        self.issues.append(issue)
        if issue.is_blocking:
            self.success = False


class IPreflightChecker(Protocol):
    """프리플라이트 검사기 인터페이스"""

    @property
    def name(self) -> str:
        """검사기 이름"""
        ...

    @property
    def description(self) -> str:
        """검사기 설명"""
        ...

    def check(self, source_path: Path, destination_path: Path | None = None) -> PreflightResult:
        """단일 파일/디렉토리 검사"""
        ...

    def check_batch(self, operations: list[tuple[Path, Path | None]]) -> PreflightResult:
        """배치 작업 검사"""
        ...

    def is_applicable(self, source_path: Path, destination_path: Path | None = None) -> bool:
        """이 검사기가 적용 가능한 작업인지"""
        ...


class BasePreflightChecker(ABC):
    """프리플라이트 검사기 기본 클래스"""

    def __init__(self, name: str = "", description: str = ""):
        self._name = name or self._get_default_name()
        self._description = description or self._get_default_description()
        self.logger = logging.getLogger(f"Preflight.{self._name}")

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def check(self, source_path: Path, destination_path: Path | None = None) -> PreflightResult:
        """단일 파일/디렉토리 검사"""
        self.logger.debug(f"검사 시작: {source_path} -> {destination_path}")
        result = PreflightResult(checker_name=self.name)
        result.checked_files = [source_path]
        if destination_path:
            result.checked_files.append(destination_path)
        try:
            import time

            start_time = time.time()
            if not self.is_applicable(source_path, destination_path):
                self.logger.debug(f"검사 적용 불가: {self.name}")
                result.metadata["skipped"] = "not_applicable"
                return result
            self._check_impl(source_path, destination_path, result)
            end_time = time.time()
            result.check_duration_ms = (end_time - start_time) * 1000
            self.logger.debug(f"검사 완료: {self.name} ({result.check_duration_ms:.1f}ms)")
        except Exception as e:
            self.logger.error(f"검사 중 오류: {self.name} - {e}")
            result.add_issue(
                PreflightIssue(
                    checker_name=self.name,
                    severity=PreflightSeverity.CRITICAL,
                    title="검사 실행 실패",
                    description=f"프리플라이트 검사 중 오류가 발생했습니다: {e}",
                    affected_files=[source_path],
                    suggestions=["시스템 상태를 확인하고 다시 시도해주세요."],
                )
            )
        return result

    def check_batch(self, operations: list[tuple[Path, Path | None]]) -> PreflightResult:
        """배치 작업 검사"""
        self.logger.debug(f"배치 검사 시작: {len(operations)}개 작업")
        result = PreflightResult(checker_name=f"{self.name}_batch")
        for source, dest in operations:
            result.checked_files.append(source)
            if dest:
                result.checked_files.append(dest)
        try:
            import time

            start_time = time.time()
            if hasattr(self, "_check_batch_impl"):
                self._check_batch_impl(operations, result)
            else:
                for source, dest in operations:
                    if self.is_applicable(source, dest):
                        single_result = self.check(source, dest)
                        result.issues.extend(single_result.issues)
                        if single_result.has_blocking_issues:
                            result.success = False
            end_time = time.time()
            result.check_duration_ms = (end_time - start_time) * 1000
            self.logger.debug(f"배치 검사 완료: {self.name} ({result.check_duration_ms:.1f}ms)")
        except Exception as e:
            self.logger.error(f"배치 검사 중 오류: {self.name} - {e}")
            result.add_issue(
                PreflightIssue(
                    checker_name=self.name,
                    severity=PreflightSeverity.CRITICAL,
                    title="배치 검사 실행 실패",
                    description=f"배치 프리플라이트 검사 중 오류가 발생했습니다: {e}",
                    suggestions=["작업을 개별적으로 수행하거나 시스템 상태를 확인해주세요."],
                )
            )
        return result

    def is_applicable(self, source_path: Path, destination_path: Path | None = None) -> bool:
        """이 검사기가 적용 가능한 작업인지 - 하위 클래스에서 오버라이드"""
        return True

    @abstractmethod
    def _check_impl(
        self, source_path: Path, destination_path: Path | None, result: PreflightResult
    ) -> None:
        """실제 검사 로직 - 하위 클래스에서 구현"""

    @abstractmethod
    def _get_default_name(self) -> str:
        """기본 검사기 이름 - 하위 클래스에서 구현"""

    @abstractmethod
    def _get_default_description(self) -> str:
        """기본 검사기 설명 - 하위 클래스에서 구현"""

    def _add_info(
        self,
        result: PreflightResult,
        title: str,
        description: str,
        files: list[Path] = None,
        suggestions: list[str] = None,
    ) -> None:
        """정보성 문제 추가"""
        result.add_issue(
            PreflightIssue(
                checker_name=self.name,
                severity=PreflightSeverity.INFO,
                title=title,
                description=description,
                affected_files=files or [],
                suggestions=suggestions or [],
            )
        )

    def _add_warning(
        self,
        result: PreflightResult,
        title: str,
        description: str,
        files: list[Path] = None,
        suggestions: list[str] = None,
    ) -> None:
        """경고 문제 추가"""
        result.add_issue(
            PreflightIssue(
                checker_name=self.name,
                severity=PreflightSeverity.WARNING,
                title=title,
                description=description,
                affected_files=files or [],
                suggestions=suggestions or [],
            )
        )

    def _add_error(
        self,
        result: PreflightResult,
        title: str,
        description: str,
        files: list[Path] = None,
        suggestions: list[str] = None,
    ) -> None:
        """오류 문제 추가"""
        result.add_issue(
            PreflightIssue(
                checker_name=self.name,
                severity=PreflightSeverity.ERROR,
                title=title,
                description=description,
                affected_files=files or [],
                suggestions=suggestions or [],
            )
        )

    def _add_critical(
        self,
        result: PreflightResult,
        title: str,
        description: str,
        files: list[Path] = None,
        suggestions: list[str] = None,
    ) -> None:
        """치명적 문제 추가"""
        result.add_issue(
            PreflightIssue(
                checker_name=self.name,
                severity=PreflightSeverity.CRITICAL,
                title=title,
                description=description,
                affected_files=files or [],
                suggestions=suggestions or [],
            )
        )
