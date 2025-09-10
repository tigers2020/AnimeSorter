"""
프리플라이트 검사 코디네이터

여러 검사기를 조정하고 전체 검사 결과를 통합 관리
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from src.app.preflight.base_checker import (IPreflightChecker, PreflightIssue,
                                            PreflightResult, PreflightSeverity)
from src.app.preflight.file_checkers import (CircularReferenceChecker,
                                             DiskSpaceChecker,
                                             FileConflictChecker,
                                             FileLockChecker,
                                             PathValidityChecker,
                                             PermissionChecker)


@dataclass
class PreflightCheckResult:
    """전체 프리플라이트 검사 결과"""

    check_id: UUID = field(default_factory=uuid4)

    # 검사 결과 통합
    success: bool = True
    checker_results: dict[str, PreflightResult] = field(default_factory=dict)

    # 검사 대상
    total_operations: int = 0
    checked_files: list[Path] = field(default_factory=list)

    # 성능 메트릭
    total_check_duration_ms: float = 0.0

    @property
    def all_issues(self) -> list[PreflightIssue]:
        """모든 검사기의 문제점들"""
        issues = []
        for result in self.checker_results.values():
            issues.extend(result.issues)
        return issues

    @property
    def blocking_issues(self) -> list[PreflightIssue]:
        """진행을 차단하는 문제들"""
        return [issue for issue in self.all_issues if issue.is_blocking]

    @property
    def warning_issues(self) -> list[PreflightIssue]:
        """경고 문제들"""
        return [issue for issue in self.all_issues if issue.severity == PreflightSeverity.WARNING]

    @property
    def info_issues(self) -> list[PreflightIssue]:
        """정보성 문제들"""
        return [issue for issue in self.all_issues if issue.severity == PreflightSeverity.INFO]

    @property
    def has_blocking_issues(self) -> bool:
        """차단 문제가 있는지"""
        return len(self.blocking_issues) > 0

    @property
    def can_proceed_with_warnings(self) -> bool:
        """경고와 함께 진행 가능한지"""
        return not self.has_blocking_issues

    @property
    def summary(self) -> str:
        """검사 결과 요약"""
        if self.success and not self.all_issues:
            return "모든 검사 통과"

        parts = []
        if self.blocking_issues:
            parts.append(f"차단 문제 {len(self.blocking_issues)}개")
        if self.warning_issues:
            parts.append(f"경고 {len(self.warning_issues)}개")
        if self.info_issues:
            parts.append(f"정보 {len(self.info_issues)}개")

        return ", ".join(parts)


class IPreflightCoordinator(Protocol):
    """프리플라이트 코디네이터 인터페이스"""

    def check_operation(
        self, source_path: Path, destination_path: Path | None = None
    ) -> PreflightCheckResult:
        """단일 작업 검사"""
        ...

    def check_batch_operations(
        self, operations: list[tuple[Path, Path | None]]
    ) -> PreflightCheckResult:
        """배치 작업 검사"""
        ...

    def add_checker(self, checker: IPreflightChecker) -> None:
        """검사기 추가"""
        ...

    def remove_checker(self, checker_name: str) -> bool:
        """검사기 제거"""
        ...

    def get_enabled_checkers(self) -> list[str]:
        """활성화된 검사기 목록"""
        ...


class PreflightCoordinator:
    """프리플라이트 검사 코디네이터"""

    def __init__(self, enable_default_checkers: bool = True):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 검사기 관리
        self._checkers: dict[str, IPreflightChecker] = {}
        self._enabled_checkers: dict[str, bool] = {}

        # 기본 검사기 등록
        if enable_default_checkers:
            self._register_default_checkers()

    def _register_default_checkers(self) -> None:
        """기본 검사기들 등록"""
        default_checkers = [
            FileConflictChecker(),
            PermissionChecker(),
            DiskSpaceChecker(),
            PathValidityChecker(),
            CircularReferenceChecker(),
            FileLockChecker(),
        ]

        for checker in default_checkers:
            self.add_checker(checker)

        self.logger.info(f"기본 검사기 {len(default_checkers)}개 등록 완료")

    def add_checker(self, checker: IPreflightChecker) -> None:
        """검사기 추가"""
        self._checkers[checker.name] = checker
        self._enabled_checkers[checker.name] = True
        self.logger.debug(f"검사기 추가: {checker.name}")

    def remove_checker(self, checker_name: str) -> bool:
        """검사기 제거"""
        if checker_name in self._checkers:
            del self._checkers[checker_name]
            del self._enabled_checkers[checker_name]
            self.logger.debug(f"검사기 제거: {checker_name}")
            return True
        return False

    def enable_checker(self, checker_name: str, enabled: bool = True) -> bool:
        """검사기 활성화/비활성화"""
        if checker_name in self._enabled_checkers:
            self._enabled_checkers[checker_name] = enabled
            self.logger.debug(f"검사기 {'활성화' if enabled else '비활성화'}: {checker_name}")
            return True
        return False

    def get_enabled_checkers(self) -> list[str]:
        """활성화된 검사기 목록"""
        return [name for name, enabled in self._enabled_checkers.items() if enabled]

    def check_operation(
        self, source_path: Path, destination_path: Path | None = None
    ) -> PreflightCheckResult:
        """단일 작업 검사"""
        self.logger.info(f"프리플라이트 검사 시작: {source_path} -> {destination_path}")

        result = PreflightCheckResult()
        result.total_operations = 1
        result.checked_files = [source_path]
        if destination_path:
            result.checked_files.append(destination_path)

        import time

        start_time = time.time()

        try:
            # 각 검사기별로 검사 수행
            for checker_name in self.get_enabled_checkers():
                checker = self._checkers[checker_name]

                try:
                    # 검사기 적용 가능성 확인
                    if not checker.is_applicable(source_path, destination_path):
                        self.logger.debug(f"검사기 적용 불가: {checker_name}")
                        continue

                    # 검사 수행
                    checker_result = checker.check(source_path, destination_path)
                    result.checker_results[checker_name] = checker_result

                    # 차단 문제가 있으면 전체 실패
                    if checker_result.has_blocking_issues:
                        result.success = False

                    self.logger.debug(
                        f"검사기 완료: {checker_name} - 문제 {len(checker_result.issues)}개"
                    )

                except Exception as e:
                    self.logger.error(f"검사기 실행 실패: {checker_name} - {e}")

                    # 검사기 실패를 치명적 문제로 처리
                    error_result = PreflightResult(checker_name=checker_name)
                    error_result.add_issue(
                        PreflightIssue(
                            checker_name=checker_name,
                            severity=PreflightSeverity.CRITICAL,
                            title="검사기 실행 실패",
                            description=f"프리플라이트 검사기가 실패했습니다: {e}",
                            affected_files=[source_path],
                            suggestions=["시스템 상태를 확인하고 다시 시도해주세요."],
                        )
                    )
                    result.checker_results[checker_name] = error_result
                    result.success = False

            # 검사 시간 기록
            end_time = time.time()
            result.total_check_duration_ms = (end_time - start_time) * 1000

            # 결과 로깅
            issue_count = len(result.all_issues)
            blocking_count = len(result.blocking_issues)

            if result.success:
                if issue_count == 0:
                    self.logger.info("프리플라이트 검사 완료: 문제 없음")
                else:
                    self.logger.info(f"프리플라이트 검사 완료: 경고 {issue_count}개 (차단 없음)")
            else:
                self.logger.warning(f"프리플라이트 검사 실패: 차단 문제 {blocking_count}개")

        except Exception as e:
            self.logger.error(f"프리플라이트 검사 중 예외: {e}")
            result.success = False

            # 전체 검사 실패를 치명적 문제로 처리
            error_result = PreflightResult(checker_name="coordinator")
            error_result.add_issue(
                PreflightIssue(
                    checker_name="coordinator",
                    severity=PreflightSeverity.CRITICAL,
                    title="검사 시스템 실패",
                    description=f"프리플라이트 검사 시스템에서 오류가 발생했습니다: {e}",
                    affected_files=[source_path],
                    suggestions=["시스템을 재시작하고 다시 시도해주세요."],
                )
            )
            result.checker_results["coordinator"] = error_result

        return result

    def check_batch_operations(
        self, operations: list[tuple[Path, Path | None]]
    ) -> PreflightCheckResult:
        """배치 작업 검사"""
        self.logger.info(f"배치 프리플라이트 검사 시작: {len(operations)}개 작업")

        result = PreflightCheckResult()
        result.total_operations = len(operations)

        # 모든 파일 수집
        for source, dest in operations:
            result.checked_files.append(source)
            if dest:
                result.checked_files.append(dest)

        import time

        start_time = time.time()

        try:
            # 각 검사기별로 배치 검사 수행
            for checker_name in self.get_enabled_checkers():
                checker = self._checkers[checker_name]

                try:
                    # 적용 가능한 작업만 필터링
                    applicable_operations = [
                        (source, dest)
                        for source, dest in operations
                        if checker.is_applicable(source, dest)
                    ]

                    if not applicable_operations:
                        self.logger.debug(f"배치 검사기 적용 불가: {checker_name}")
                        continue

                    # 배치 검사 수행
                    checker_result = checker.check_batch(applicable_operations)
                    result.checker_results[checker_name] = checker_result

                    # 차단 문제가 있으면 전체 실패
                    if checker_result.has_blocking_issues:
                        result.success = False

                    self.logger.debug(
                        f"배치 검사기 완료: {checker_name} - 문제 {len(checker_result.issues)}개"
                    )

                except Exception as e:
                    self.logger.error(f"배치 검사기 실행 실패: {checker_name} - {e}")

                    # 검사기 실패를 치명적 문제로 처리
                    error_result = PreflightResult(checker_name=f"{checker_name}_batch")
                    error_result.add_issue(
                        PreflightIssue(
                            checker_name=checker_name,
                            severity=PreflightSeverity.CRITICAL,
                            title="배치 검사기 실행 실패",
                            description=f"배치 프리플라이트 검사기가 실패했습니다: {e}",
                            suggestions=[
                                "개별 작업으로 나누어 시도하거나 시스템 상태를 확인해주세요."
                            ],
                        )
                    )
                    result.checker_results[f"{checker_name}_batch"] = error_result
                    result.success = False

            # 검사 시간 기록
            end_time = time.time()
            result.total_check_duration_ms = (end_time - start_time) * 1000

            # 결과 로깅
            issue_count = len(result.all_issues)
            blocking_count = len(result.blocking_issues)

            if result.success:
                if issue_count == 0:
                    self.logger.info(
                        f"배치 프리플라이트 검사 완료: {len(operations)}개 작업, 문제 없음"
                    )
                else:
                    self.logger.info(
                        f"배치 프리플라이트 검사 완료: {len(operations)}개 작업, "
                        f"경고 {issue_count}개 (차단 없음)"
                    )
            else:
                self.logger.warning(
                    f"배치 프리플라이트 검사 실패: {len(operations)}개 작업, "
                    f"차단 문제 {blocking_count}개"
                )

        except Exception as e:
            self.logger.error(f"배치 프리플라이트 검사 중 예외: {e}")
            result.success = False

            # 전체 검사 실패를 치명적 문제로 처리
            error_result = PreflightResult(checker_name="batch_coordinator")
            error_result.add_issue(
                PreflightIssue(
                    checker_name="batch_coordinator",
                    severity=PreflightSeverity.CRITICAL,
                    title="배치 검사 시스템 실패",
                    description=f"배치 프리플라이트 검사 시스템에서 오류가 발생했습니다: {e}",
                    suggestions=["개별 작업으로 나누어 시도하거나 시스템을 재시작해주세요."],
                )
            )
            result.checker_results["batch_coordinator"] = error_result

        return result

    def get_checker_info(self) -> dict[str, dict[str, Any]]:
        """등록된 검사기 정보 조회"""
        info = {}
        for name, checker in self._checkers.items():
            info[name] = {
                "name": checker.name,
                "description": checker.description,
                "enabled": self._enabled_checkers.get(name, False),
            }
        return info
