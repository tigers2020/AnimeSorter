"""
모놀리식 파일 리팩토링 전략 - AnimeSorter

분석된 모놀리식 파일들을 체계적으로 리팩토링하기 위한 전략과 계획을 제공합니다.
- 리팩토링 우선순위 설정
- 책임 분리 전략
- 단계별 실행 계획
- 품질 지표 및 검증 방법
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RefactoringPriority(Enum):
    """리팩토링 우선순위"""

    CRITICAL = 1  # 즉시 리팩토링 필요 (심각한 문제)
    HIGH = 2  # 높은 우선순위 (주요 개선 효과)
    MEDIUM = 3  # 중간 우선순위 (점진적 개선)
    LOW = 4  # 낮은 우선순위 (향후 고려)


class RefactoringType(Enum):
    """리팩토링 유형"""

    EXTRACT_CLASS = "extract_class"  # 클래스 추출
    EXTRACT_METHOD = "extract_method"  # 메서드 추출
    EXTRACT_MODULE = "extract_module"  # 모듈 추출
    SPLIT_FILE = "split_file"  # 파일 분할
    MOVE_METHOD = "move_method"  # 메서드 이동
    MOVE_CLASS = "move_class"  # 클래스 이동
    SIMPLIFY_METHOD = "simplify_method"  # 메서드 단순화
    REMOVE_DUPLICATION = "remove_duplication"  # 중복 제거


class ResponsibilityType(Enum):
    """책임 유형"""

    UI_RENDERING = "ui_rendering"  # UI 렌더링
    BUSINESS_LOGIC = "business_logic"  # 비즈니스 로직
    DATA_MANAGEMENT = "data_management"  # 데이터 관리
    EVENT_HANDLING = "event_handling"  # 이벤트 처리
    CONFIGURATION = "configuration"  # 설정 관리
    VALIDATION = "validation"  # 검증 로직
    UTILITY = "utility"  # 유틸리티 함수
    INTEGRATION = "integration"  # 외부 시스템 통합


@dataclass
class RefactoringTarget:
    """리팩토링 대상 파일 정보"""

    file_path: Path
    current_size_kb: int
    line_count: int
    priority: RefactoringPriority
    refactoring_types: list[RefactoringType]
    responsibilities: list[ResponsibilityType]
    estimated_effort: int  # 예상 작업 시간 (시간)
    dependencies: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    benefits: list[str] = field(default_factory=list)


@dataclass
class RefactoringPlan:
    """리팩토링 실행 계획"""

    phase: int
    name: str
    description: str
    targets: list[RefactoringTarget]
    prerequisites: list[str] = field(default_factory=list)
    estimated_duration: int = 0  # 예상 소요 시간 (시간)
    success_criteria: list[str] = field(default_factory=list)


class RefactoringStrategy:
    """모놀리식 파일 리팩토링 전략"""

    def __init__(self):
        self.targets: list[RefactoringTarget] = []
        self.plans: list[RefactoringPlan] = []
        self.completed_targets: set[str] = set()

    def analyze_file(self, file_path: Path) -> RefactoringTarget:
        """파일 분석하여 리팩토링 대상으로 등록"""
        try:
            # 파일 크기 및 라인 수 확인
            size_kb = file_path.stat().st_size // 1024
            line_count = self._count_lines(file_path)

            # 우선순위 결정
            priority = self._determine_priority(size_kb, line_count)

            # 리팩토링 유형 결정
            refactoring_types = self._determine_refactoring_types(file_path, size_kb, line_count)

            # 책임 유형 분석
            responsibilities = self._analyze_responsibilities(file_path)

            # 예상 작업 시간 추정
            estimated_effort = self._estimate_effort(size_kb, line_count, len(refactoring_types))

            # 의존성 및 리스크 분석
            dependencies, risks = self._analyze_dependencies_and_risks(file_path)

            # 개선 효과 분석
            benefits = self._analyze_benefits(file_path, refactoring_types)

            target = RefactoringTarget(
                file_path=file_path,
                current_size_kb=size_kb,
                line_count=line_count,
                priority=priority,
                refactoring_types=refactoring_types,
                responsibilities=responsibilities,
                estimated_effort=estimated_effort,
                dependencies=dependencies,
                risks=risks,
                benefits=benefits,
            )

            self.targets.append(target)
            logger.info(f"리팩토링 대상 등록: {file_path.name} (우선순위: {priority.value})")

            return target

        except Exception as e:
            logger.error(f"파일 분석 실패 {file_path}: {e}")
            raise

    def create_refactoring_plans(self) -> list[RefactoringPlan]:
        """리팩토링 실행 계획 생성"""
        # 우선순위별로 정렬
        sorted_targets = sorted(self.targets, key=lambda x: x.priority.value)

        # Phase 1: 핵심 GUI 컴포넌트 분리
        phase1_targets = [
            t
            for t in sorted_targets
            if t.priority in [RefactoringPriority.CRITICAL, RefactoringPriority.HIGH]
        ]
        phase1_plan = RefactoringPlan(
            phase=1,
            name="핵심 GUI 컴포넌트 분리",
            description="가장 큰 모놀리식 파일들을 우선적으로 분리하여 기본 구조 개선",
            targets=phase1_targets[:3],  # 상위 3개만
            estimated_duration=sum(t.estimated_effort for t in phase1_targets[:3]),
            success_criteria=[
                "main_window.py가 300줄 이하로 축소",
                "results_view.py가 200줄 이하로 축소",
                "각 컴포넌트가 단일 책임을 가지도록 분리",
            ],
        )

        # Phase 2: 비즈니스 로직 분리
        phase2_targets = [t for t in sorted_targets if t.priority == RefactoringPriority.MEDIUM]
        phase2_plan = RefactoringPlan(
            phase=2,
            name="비즈니스 로직 분리",
            description="비즈니스 로직과 UI 로직을 명확히 분리",
            targets=phase2_targets[:5],
            prerequisites=["Phase 1 완료"],
            estimated_duration=sum(t.estimated_effort for t in phase2_targets[:5]),
            success_criteria=[
                "UI와 비즈니스 로직이 명확히 분리됨",
                "각 서비스 클래스가 단일 책임을 가짐",
                "테스트 가능성이 향상됨",
            ],
        )

        # Phase 3: 유틸리티 및 헬퍼 분리
        phase3_targets = [t for t in sorted_targets if t.priority == RefactoringPriority.LOW]
        phase3_plan = RefactoringPlan(
            phase=3,
            name="유틸리티 및 헬퍼 분리",
            description="공통 유틸리티 함수들을 별도 모듈로 분리",
            targets=phase3_targets[:3],
            prerequisites=["Phase 1 완료", "Phase 2 완료"],
            estimated_duration=sum(t.estimated_effort for t in phase3_targets[:3]),
            success_criteria=[
                "공통 유틸리티가 재사용 가능한 모듈로 분리됨",
                "코드 중복이 제거됨",
                "유지보수성이 향상됨",
            ],
        )

        self.plans = [phase1_plan, phase2_plan, phase3_plan]
        return self.plans

    def get_next_target(self) -> Optional[RefactoringTarget]:
        """다음 리팩토링 대상 반환"""
        for target in self.targets:
            if target.file_path.name not in self.completed_targets:
                return target
        return None

    def mark_completed(self, file_name: str):
        """리팩토링 완료 표시"""
        self.completed_targets.add(file_name)
        logger.info(f"리팩토링 완료: {file_name}")

    def get_progress(self) -> dict[str, Any]:
        """진행 상황 반환"""
        total = len(self.targets)
        completed = len(self.completed_targets)
        progress_percent = (completed / total * 100) if total > 0 else 0

        return {
            "total_targets": total,
            "completed_targets": completed,
            "progress_percent": progress_percent,
            "remaining_targets": total - completed,
            "estimated_remaining_effort": sum(
                t.estimated_effort
                for t in self.targets
                if t.file_path.name not in self.completed_targets
            ),
        }

    def _count_lines(self, file_path: Path) -> int:
        """파일의 라인 수 계산"""
        try:
            with open(file_path, encoding="utf-8") as f:
                return len(f.readlines())
        except Exception:
            return 0

    def _determine_priority(self, size_kb: int, line_count: int) -> RefactoringPriority:
        """우선순위 결정"""
        if size_kb > 50 or line_count > 1000:
            return RefactoringPriority.CRITICAL
        elif size_kb > 30 or line_count > 500:
            return RefactoringPriority.HIGH
        elif size_kb > 20 or line_count > 300:
            return RefactoringPriority.MEDIUM
        else:
            return RefactoringPriority.LOW

    def _determine_refactoring_types(
        self, file_path: Path, size_kb: int, line_count: int
    ) -> list[RefactoringType]:
        """리팩토링 유형 결정"""
        types = []

        if size_kb > 40:
            types.append(RefactoringType.SPLIT_FILE)
            types.append(RefactoringType.EXTRACT_CLASS)

        if line_count > 500:
            types.append(RefactoringType.EXTRACT_METHOD)
            types.append(RefactoringType.EXTRACT_MODULE)

        if "manager" in file_path.name.lower() or "service" in file_path.name.lower():
            types.append(RefactoringType.MOVE_CLASS)

        return types

    def _analyze_responsibilities(self, file_path: Path) -> list[ResponsibilityType]:
        """책임 유형 분석"""
        responsibilities = []

        # 파일명 기반 기본 책임 추정
        if "ui" in file_path.name.lower() or "view" in file_path.name.lower():
            responsibilities.append(ResponsibilityType.UI_RENDERING)

        if "manager" in file_path.name.lower():
            responsibilities.append(ResponsibilityType.BUSINESS_LOGIC)
            responsibilities.append(ResponsibilityType.DATA_MANAGEMENT)

        if "service" in file_path.name.lower():
            responsibilities.append(ResponsibilityType.BUSINESS_LOGIC)
            responsibilities.append(ResponsibilityType.INTEGRATION)

        if "handler" in file_path.name.lower():
            responsibilities.append(ResponsibilityType.EVENT_HANDLING)

        if "config" in file_path.name.lower() or "settings" in file_path.name.lower():
            responsibilities.append(ResponsibilityType.CONFIGURATION)

        return responsibilities

    def _estimate_effort(self, size_kb: int, line_count: int, refactoring_count: int) -> int:
        """예상 작업 시간 추정 (시간 단위)"""
        base_effort = max(size_kb // 10, line_count // 100)
        complexity_multiplier = 1 + (refactoring_count * 0.5)
        return int(base_effort * complexity_multiplier)

    def _analyze_dependencies_and_risks(self, file_path: Path) -> tuple[list[str], list[str]]:
        """의존성 및 리스크 분석"""
        dependencies = []
        risks = []

        # 기본 의존성 (파일명 기반)
        if "main_window" in file_path.name.lower():
            dependencies.extend(["theme_manager", "anime_data_manager", "settings_manager"])
            risks.extend(["UI 깨짐", "기능 손실", "테마 적용 오류"])

        if "results_view" in file_path.name.lower():
            dependencies.extend(["table_models", "cell_delegates"])
            risks.extend(["데이터 표시 오류", "테이블 기능 손실"])

        return dependencies, risks

    def _analyze_benefits(
        self, file_path: Path, refactoring_types: list[RefactoringType]
    ) -> list[str]:
        """개선 효과 분석"""
        benefits = []

        if RefactoringType.SPLIT_FILE in refactoring_types:
            benefits.extend(["가독성 향상", "유지보수성 개선", "테스트 용이성"])

        if RefactoringType.EXTRACT_CLASS in refactoring_types:
            benefits.extend(["단일 책임 원칙 준수", "재사용성 향상", "확장성 개선"])

        if RefactoringType.EXTRACT_METHOD in refactoring_types:
            benefits.extend(["코드 가독성 향상", "테스트 용이성", "중복 제거"])

        return benefits


# 전역 리팩토링 전략 인스턴스
refactoring_strategy = RefactoringStrategy()


def get_refactoring_strategy() -> RefactoringStrategy:
    """리팩토링 전략 인스턴스 반환"""
    return refactoring_strategy
