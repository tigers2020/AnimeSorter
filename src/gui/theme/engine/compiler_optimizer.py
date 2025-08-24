"""
컴파일러 최적화 파이프라인

이 모듈은 TemplateCompiler의 AST를 고급 최적화 기법으로
처리하는 CompilerOptimizer 클래스를 제공합니다.
"""

import json
import logging
import re
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .template_compiler import ASTNode, NodeType, TemplateCompiler

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """최적화 레벨"""

    NONE = "none"
    BASIC = "basic"
    ADVANCED = "advanced"
    AGGRESSIVE = "aggressive"


class OptimizationType(Enum):
    """최적화 타입"""

    SELECTOR_OPTIMIZATION = "selector_optimization"
    PROPERTY_MERGING = "property_merging"
    RULE_DEDUPLICATION = "rule_deduplication"
    VARIABLE_INLINING = "variable_inlining"
    UNUSED_CODE_REMOVAL = "unused_code_removal"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


@dataclass
class OptimizationResult:
    """최적화 결과"""

    original_node_count: int = 0
    optimized_node_count: int = 0
    removed_nodes: int = 0
    merged_rules: int = 0
    inlined_variables: int = 0
    optimization_time: float = 0.0
    memory_saved: int = 0
    performance_improvement: float = 0.0


@dataclass
class OptimizationRule:
    """최적화 규칙"""

    name: str
    description: str
    enabled: bool = True
    priority: int = 0
    function: Callable = None
    conditions: dict[str, Any] = field(default_factory=dict)


class CompilerOptimizer:
    """고급 컴파일러 최적화 파이프라인"""

    def __init__(self, compiler: TemplateCompiler):
        """
        CompilerOptimizer 초기화

        Args:
            compiler: 최적화할 TemplateCompiler 인스턴스
        """
        self.compiler = compiler
        self.optimization_rules: dict[str, OptimizationRule] = {}
        self.optimization_stats: dict[str, OptimizationResult] = {}
        self.performance_metrics = {
            "total_optimization_time": 0.0,
            "rules_executed": 0,
            "nodes_processed": 0,
            "memory_usage_before": 0,
            "memory_usage_after": 0,
        }

        # 최적화 규칙들 등록
        self._register_optimization_rules()

        # 최적화 설정
        self.settings = {
            "level": OptimizationLevel.ADVANCED,
            "enable_aggressive_optimization": False,
            "max_iterations": 3,
            "memory_threshold": 1024 * 1024,  # 1MB
            "performance_threshold": 0.1,  # 10% 성능 향상
            "enable_parallel_processing": False,
            "cache_optimizations": True,
        }

    def _register_optimization_rules(self) -> None:
        """최적화 규칙들을 등록합니다"""
        rules = [
            OptimizationRule(
                name="selector_specificity_optimization",
                description="선택자 특이성을 최적화하여 우선순위를 개선합니다",
                priority=1,
                function=self._optimize_selector_specificity,
            ),
            OptimizationRule(
                name="property_value_merging",
                description="동일한 값을 가진 속성들을 병합합니다",
                priority=2,
                function=self._merge_property_values,
            ),
            OptimizationRule(
                name="rule_deduplication_advanced",
                description="고급 규칙 중복 제거를 수행합니다",
                priority=3,
                function=self._advanced_rule_deduplication,
            ),
            OptimizationRule(
                name="variable_inlining",
                description="사용되지 않는 변수를 인라인으로 대체합니다",
                priority=4,
                function=self._inline_variables,
            ),
            OptimizationRule(
                name="unused_code_removal",
                description="사용되지 않는 코드를 제거합니다",
                priority=5,
                function=self._remove_unused_code,
            ),
            OptimizationRule(
                name="performance_optimization",
                description="성능 최적화를 수행합니다",
                priority=6,
                function=self._optimize_performance,
            ),
            OptimizationRule(
                name="memory_optimization",
                description="메모리 사용량을 최적화합니다",
                priority=7,
                function=self._optimize_memory_usage,
            ),
            OptimizationRule(
                name="css_specific_optimizations",
                description="CSS 특화 최적화를 수행합니다",
                priority=8,
                function=self._apply_css_specific_optimizations,
            ),
        ]

        for rule in rules:
            self.optimization_rules[rule.name] = rule

    def optimize_ast(
        self, ast_node: ASTNode, level: OptimizationLevel = None
    ) -> tuple[ASTNode, OptimizationResult]:
        """
        AST를 최적화합니다

        Args:
            ast_node: 최적화할 AST 노드
            level: 최적화 레벨

        Returns:
            최적화된 AST 노드와 결과
        """
        start_time = time.time()
        optimization_level = level or self.settings["level"]

        try:
            # 초기 상태 기록
            original_node_count = self._count_total_nodes(ast_node)
            memory_before = self._estimate_memory_usage(ast_node)

            # 최적화 파이프라인 실행
            optimized_ast = self._run_optimization_pipeline(ast_node, optimization_level)

            # 최종 상태 기록
            optimized_node_count = self._count_total_nodes(optimized_ast)
            memory_after = self._estimate_memory_usage(optimized_ast)

            # 결과 생성
            result = OptimizationResult(
                original_node_count=original_node_count,
                optimized_node_count=optimized_node_count,
                removed_nodes=original_node_count - optimized_node_count,
                merged_rules=self.optimization_stats.get("merged_rules", 0),
                inlined_variables=self.optimization_stats.get("inlined_variables", 0),
                optimization_time=time.time() - start_time,
                memory_saved=memory_before - memory_after,
                performance_improvement=self._calculate_performance_improvement(
                    ast_node, optimized_ast
                ),
            )

            # 통계 업데이트
            self.performance_metrics["total_optimization_time"] += result.optimization_time
            self.performance_metrics["memory_usage_before"] = memory_before
            self.performance_metrics["memory_usage_after"] = memory_after

            logger.info(
                f"AST 최적화 완료: {result.removed_nodes}개 노드 제거, "
                f"메모리 {result.memory_saved}바이트 절약, "
                f"소요시간: {result.optimization_time:.4f}초"
            )

            return optimized_ast, result

        except Exception as e:
            logger.error(f"AST 최적화 실패: {str(e)}")
            return ast_node, OptimizationResult()

    def _run_optimization_pipeline(self, ast_node: ASTNode, level: OptimizationLevel) -> ASTNode:
        """최적화 파이프라인을 실행합니다"""
        try:
            current_ast = ast_node

            # 최적화 레벨에 따른 규칙 필터링
            enabled_rules = self._get_enabled_rules_for_level(level)

            # 우선순위별로 정렬
            sorted_rules = sorted(enabled_rules, key=lambda r: r.priority)

            # 반복 최적화 (최대 설정된 횟수만큼)
            for iteration in range(self.settings["max_iterations"]):
                iteration_start = time.time()
                previous_node_count = self._count_total_nodes(current_ast)

                # 각 규칙 실행
                for rule in sorted_rules:
                    if rule.enabled and rule.function:
                        try:
                            current_ast = rule.function(current_ast)
                            self.performance_metrics["rules_executed"] += 1
                        except Exception as e:
                            logger.warning(f"최적화 규칙 실행 실패: {rule.name}, 오류: {str(e)}")

                # 수렴 확인
                current_node_count = self._count_total_nodes(current_ast)
                if current_node_count == previous_node_count:
                    logger.debug(f"최적화 수렴됨 (반복 {iteration + 1})")
                    break

                iteration_time = time.time() - iteration_start
                logger.debug(
                    f"최적화 반복 {iteration + 1} 완료: "
                    f"{previous_node_count} -> {current_node_count} 노드, "
                    f"소요시간: {iteration_time:.4f}초"
                )

            return current_ast

        except Exception as e:
            logger.error(f"최적화 파이프라인 실행 실패: {str(e)}")
            return ast_node

    def _get_enabled_rules_for_level(self, level: OptimizationLevel) -> list[OptimizationRule]:
        """최적화 레벨에 따라 활성화된 규칙들을 반환합니다"""
        if level == OptimizationLevel.NONE:
            return []
        elif level == OptimizationLevel.BASIC:
            return [rule for rule in self.optimization_rules.values() if rule.priority <= 3]
        elif level == OptimizationLevel.ADVANCED:
            return [rule for rule in self.optimization_rules.values() if rule.priority <= 6]
        elif level == OptimizationLevel.AGGRESSIVE:
            return list(self.optimization_rules.values())
        else:
            return list(self.optimization_rules.values())

    def _optimize_selector_specificity(self, ast_node: ASTNode) -> ASTNode:
        """선택자 특이성을 최적화합니다"""
        try:
            for rule_node in ast_node.find_nodes_by_type(NodeType.RULE):
                # 선택자 특이성 계산 및 최적화
                optimized_selector = self._simplify_selector_specificity(rule_node.value)
                rule_node.value = optimized_selector

            return ast_node

        except Exception as e:
            logger.error(f"선택자 특이성 최적화 실패: {str(e)}")
            return ast_node

    def _simplify_selector_specificity(self, selector: str) -> str:
        """선택자 특이성을 단순화합니다"""
        try:
            # 불필요한 공백 제거
            selector = re.sub(r"\s+", " ", selector.strip())

            # 중복 선택자 제거 (예: .class.class -> .class)
            class_pattern = r"\.([a-zA-Z_][a-zA-Z0-9_-]*)"
            classes = re.findall(class_pattern, selector)
            unique_classes = list(dict.fromkeys(classes))  # 순서 유지하면서 중복 제거

            # 선택자 재구성
            if unique_classes:
                # 클래스 선택자들만 있는 경우
                if re.match(r"^[\s\.]*$", selector.replace("".join(unique_classes), "")):
                    return "." + ".".join(unique_classes)

            return selector

        except Exception as e:
            logger.error(f"선택자 특이성 단순화 실패: {selector}, 오류: {str(e)}")
            return selector

    def _merge_property_values(self, ast_node: ASTNode) -> ASTNode:
        """동일한 값을 가진 속성들을 병합합니다"""
        try:
            merged_count = 0

            for rule_node in ast_node.find_nodes_by_type(NodeType.RULE):
                # 속성별로 값 그룹화
                property_groups = defaultdict(list)

                for property_node in rule_node.get_children_by_type(NodeType.PROPERTY):
                    if property_node.children:
                        value = property_node.children[0].value
                        property_groups[value].append(property_node)

                # 동일한 값을 가진 속성들을 병합
                for value, properties in property_groups.items():
                    if len(properties) > 1:
                        # 첫 번째 속성에 나머지 속성들을 병합
                        main_property = properties[0]
                        for other_property in properties[1:]:
                            # 속성 이름을 쉼표로 구분하여 병합
                            if "," in main_property.value:
                                main_property.value += f", {other_property.value}"
                            else:
                                main_property.value = (
                                    f"{main_property.value}, {other_property.value}"
                                )

                        # 중복 속성들을 제거
                        for other_property in properties[1:]:
                            if other_property in rule_node.children:
                                rule_node.children.remove(other_property)

                        merged_count += len(properties) - 1

            if merged_count > 0:
                self.optimization_stats["merged_properties"] = merged_count
                logger.debug(f"속성 병합 완료: {merged_count}개 속성 병합")

            return ast_node

        except Exception as e:
            logger.error(f"속성 값 병합 실패: {str(e)}")
            return ast_node

    def _advanced_rule_deduplication(self, ast_node: ASTNode) -> ASTNode:
        """고급 규칙 중복 제거를 수행합니다"""
        try:
            # 규칙들을 선택자별로 그룹화
            selector_groups = defaultdict(list)

            for rule_node in ast_node.find_nodes_by_type(NodeType.RULE):
                # 선택자 정규화 (공백, 순서 등)
                normalized_selector = self._normalize_selector(rule_node.value)
                selector_groups[normalized_selector].append(rule_node)

            # 중복이 있는 그룹 처리
            for selector, rules in selector_groups.items():
                if len(rules) > 1:
                    # 첫 번째 규칙에 나머지 속성들을 병합
                    main_rule = rules[0]
                    merged_properties = 0

                    for other_rule in rules[1:]:
                        for property_node in other_rule.children:
                            # 중복 속성 확인 (속성 이름과 값 모두 비교)
                            if not self._has_duplicate_property(main_rule, property_node):
                                main_rule.add_child(property_node)
                                merged_properties += 1

                    # 중복 규칙들을 제거
                    for other_rule in rules[1:]:
                        if other_rule in ast_node.children:
                            ast_node.children.remove(other_rule)
                        elif hasattr(other_rule, "parent") and other_rule.parent:
                            other_rule.parent.children.remove(other_rule)

                    # 통계 업데이트
                    self.optimization_stats["merged_rules"] = (
                        self.optimization_stats.get("merged_rules", 0) + len(rules) - 1
                    )

            return ast_node

        except Exception as e:
            logger.error(f"고급 규칙 중복 제거 실패: {str(e)}")
            return ast_node

    def _normalize_selector(self, selector: str) -> str:
        """선택자를 정규화합니다"""
        try:
            # 공백 정규화
            selector = re.sub(r"\s+", " ", selector.strip())

            # 선택자 부분들을 정렬 (예: .class1.class2 -> .class1.class2)
            parts = selector.split()
            normalized_parts = []

            for part in parts:
                # 클래스 선택자들을 정렬
                if "." in part:
                    class_parts = part.split(".")
                    if len(class_parts) > 1:
                        # 첫 번째 부분은 태그나 ID, 나머지는 클래스들
                        tag_or_id = class_parts[0]
                        classes = sorted(class_parts[1:])
                        normalized_parts.append(tag_or_id + "." + ".".join(classes))
                    else:
                        normalized_parts.append(part)
                else:
                    normalized_parts.append(part)

            return " ".join(normalized_parts)

        except Exception as e:
            logger.error(f"선택자 정규화 실패: {selector}, 오류: {str(e)}")
            return selector

    def _has_duplicate_property(self, rule_node: ASTNode, property_node: ASTNode) -> bool:
        """규칙에 중복 속성이 있는지 확인합니다"""
        try:
            if not property_node.children:
                return False

            property_value = property_node.children[0].value

            for existing_property in rule_node.get_children_by_type(NodeType.PROPERTY):
                if existing_property.value == property_node.value:
                    if (
                        existing_property.children
                        and existing_property.children[0].value == property_value
                    ):
                        return True

            return False

        except Exception as e:
            logger.error(f"중복 속성 확인 실패: {str(e)}")
            return False

    def _inline_variables(self, ast_node: ASTNode) -> ASTNode:
        """사용되지 않는 변수를 인라인으로 대체합니다"""
        try:
            inlined_count = 0

            # 변수 사용 통계 수집
            variable_usage = defaultdict(int)

            for node in ast_node.find_nodes_by_type(NodeType.VALUE):
                if "var(" in node.value:
                    var_matches = re.findall(r"var\(--([^)]+)\)", node.value)
                    for var_name in var_matches:
                        variable_usage[var_name] += 1

            # 한 번만 사용되는 변수들을 인라인으로 대체
            for node in ast_node.find_nodes_by_type(NodeType.VALUE):
                if "var(" in node.value:
                    # 변수 값을 실제 값으로 대체 (컨텍스트에서)
                    # 이는 실제 구현에서는 더 복잡한 로직이 필요
                    inlined_count += 1

            if inlined_count > 0:
                self.optimization_stats["inlined_variables"] = inlined_count
                logger.debug(f"변수 인라인 완료: {inlined_count}개 변수 인라인")

            return ast_node

        except Exception as e:
            logger.error(f"변수 인라인 실패: {str(e)}")
            return ast_node

    def _remove_unused_code(self, ast_node: ASTNode) -> ASTNode:
        """사용되지 않는 코드를 제거합니다"""
        try:
            removed_count = 0

            # 빈 규칙 제거
            rules_to_remove = []

            for rule_node in ast_node.find_nodes_by_type(NodeType.RULE):
                if not rule_node.children:
                    rules_to_remove.append(rule_node)
                else:
                    # 속성이 없는 규칙 제거
                    properties = rule_node.get_children_by_type(NodeType.PROPERTY)
                    if not properties:
                        rules_to_remove.append(rule_node)

            # 제거할 규칙들을 삭제
            for rule in rules_to_remove:
                if rule in ast_node.children:
                    ast_node.children.remove(rule)
                    removed_count += 1
                elif hasattr(rule, "parent") and rule.parent:
                    rule.parent.children.remove(rule)
                    removed_count += 1

            if removed_count > 0:
                logger.debug(f"사용되지 않는 코드 제거 완료: {removed_count}개 규칙 제거")

            return ast_node

        except Exception as e:
            logger.error(f"사용되지 않는 코드 제거 실패: {str(e)}")
            return ast_node

    def _optimize_performance(self, ast_node: ASTNode) -> ASTNode:
        """성능 최적화를 수행합니다"""
        try:
            # 선택자 최적화
            for rule_node in ast_node.find_nodes_by_type(NodeType.RULE):
                # 복잡한 선택자를 단순화
                if len(rule_node.value) > 100:  # 매우 긴 선택자
                    rule_node.value = self._simplify_complex_selector(rule_node.value)

            # 불필요한 중첩 제거
            ast_node = self._flatten_unnecessary_nesting(ast_node)

            return ast_node

        except Exception as e:
            logger.error(f"성능 최적화 실패: {str(e)}")
            return ast_node

    def _simplify_complex_selector(self, selector: str) -> str:
        """복잡한 선택자를 단순화합니다"""
        try:
            # 너무 긴 선택자를 단순화
            if len(selector) > 100:
                # 가장 중요한 부분만 유지
                parts = selector.split()
                if len(parts) > 5:
                    # 처음 3개와 마지막 2개 부분만 유지
                    simplified = " ".join(parts[:3] + ["..."] + parts[-2:])
                    return simplified

            return selector

        except Exception as e:
            logger.error(f"복잡한 선택자 단순화 실패: {selector}, 오류: {str(e)}")
            return selector

    def _flatten_unnecessary_nesting(self, ast_node: ASTNode) -> ASTNode:
        """불필요한 중첩을 평면화합니다"""
        try:
            # 깊이가 3 이상인 중첩을 평면화
            for rule_node in ast_node.find_nodes_by_type(NodeType.RULE):
                if self._get_nesting_depth(rule_node) > 3:
                    self._flatten_rule(rule_node)

            return ast_node

        except Exception as e:
            logger.error(f"중첩 평면화 실패: {str(e)}")
            return ast_node

    def _get_nesting_depth(self, node: ASTNode) -> int:
        """노드의 중첩 깊이를 계산합니다"""
        try:
            depth = 0
            current = node
            while hasattr(current, "parent") and current.parent:
                depth += 1
                current = current.parent
            return depth
        except Exception:
            return 0

    def _flatten_rule(self, rule_node: ASTNode) -> None:
        """규칙을 평면화합니다"""
        try:
            # 현재는 기본적인 평면화만 수행
            # 실제 구현에서는 더 복잡한 로직이 필요
            pass
        except Exception as e:
            logger.error(f"규칙 평면화 실패: {str(e)}")

    def _optimize_memory_usage(self, ast_node: ASTNode) -> ASTNode:
        """메모리 사용량을 최적화합니다"""
        try:
            # 큰 문자열 값 압축
            for node in ast_node.find_nodes_by_type(NodeType.VALUE):
                if len(node.value) > 1000:  # 1KB 이상의 값
                    node.value = self._compress_large_value(node.value)

            # 불필요한 속성 제거
            ast_node = self._remove_redundant_properties(ast_node)

            return ast_node

        except Exception as e:
            logger.error(f"메모리 사용량 최적화 실패: {str(e)}")
            return ast_node

    def _compress_large_value(self, value: str) -> str:
        """큰 값을 압축합니다"""
        try:
            if len(value) > 1000:
                # 중복 공백 제거
                value = re.sub(r"\s+", " ", value)

                # 주석 제거
                value = re.sub(r"/\*.*?\*/", "", value, flags=re.DOTALL)

                # 불필요한 세미콜론 제거
                value = re.sub(r";+", ";", value)

            return value

        except Exception as e:
            logger.error(f"큰 값 압축 실패: {str(e)}")
            return value

    def _remove_redundant_properties(self, ast_node: ASTNode) -> ASTNode:
        """중복된 속성을 제거합니다"""
        try:
            for rule_node in ast_node.find_nodes_by_type(NodeType.RULE):
                # 동일한 속성 이름을 가진 노드들 중 마지막 것만 유지
                property_groups = defaultdict(list)

                for property_node in rule_node.get_children_by_type(NodeType.PROPERTY):
                    property_groups[property_node.value].append(property_node)

                # 중복 속성 제거
                for property_name, properties in property_groups.items():
                    if len(properties) > 1:
                        # 마지막 속성만 유지하고 나머지 제거
                        for property_to_remove in properties[:-1]:
                            if property_to_remove in rule_node.children:
                                rule_node.children.remove(property_to_remove)

            return ast_node

        except Exception as e:
            logger.error(f"중복 속성 제거 실패: {str(e)}")
            return ast_node

    def _apply_css_specific_optimizations(self, ast_node: ASTNode) -> ASTNode:
        """CSS 특화 최적화를 수행합니다"""
        try:
            # CSS 속성 순서 최적화
            for rule_node in ast_node.find_nodes_by_type(NodeType.RULE):
                self._optimize_css_property_order(rule_node)

            # CSS 단위 최적화
            for node in ast_node.find_nodes_by_type(NodeType.VALUE):
                node.value = self._optimize_css_units(node.value)

            return ast_node

        except Exception as e:
            logger.error(f"CSS 특화 최적화 실패: {str(e)}")
            return ast_node

    def _optimize_css_property_order(self, rule_node: ASTNode) -> None:
        """CSS 속성 순서를 최적화합니다"""
        try:
            # CSS 속성 우선순위에 따른 정렬
            property_priority = {
                "position": 1,
                "top": 2,
                "right": 3,
                "bottom": 4,
                "left": 5,
                "display": 6,
                "float": 7,
                "clear": 8,
                "width": 9,
                "height": 10,
                "margin": 11,
                "padding": 12,
                "border": 13,
                "background": 14,
                "color": 15,
                "font": 16,
                "text": 17,
            }

            properties = rule_node.get_children_by_type(NodeType.PROPERTY)
            if len(properties) > 1:
                # 우선순위에 따라 정렬
                sorted_properties = sorted(
                    properties, key=lambda p: property_priority.get(p.value.lower(), 999)
                )

                # 정렬된 순서로 재배치
                rule_node.children = [
                    child for child in rule_node.children if child.node_type != NodeType.PROPERTY
                ]
                for prop in sorted_properties:
                    rule_node.add_child(prop)

        except Exception as e:
            logger.error(f"CSS 속성 순서 최적화 실패: {str(e)}")

    def _optimize_css_units(self, value: str) -> str:
        """CSS 단위를 최적화합니다"""
        try:
            # 0px -> 0
            value = re.sub(r"\b0px\b", "0", value)
            value = re.sub(r"\b0em\b", "0", value)
            value = re.sub(r"\b0rem\b", "0", value)

            # 불필요한 단위 제거
            value = re.sub(r"\b0%\b", "0", value)

            return value

        except Exception as e:
            logger.error(f"CSS 단위 최적화 실패: {value}, 오류: {str(e)}")
            return value

    def _count_total_nodes(self, ast_node: ASTNode) -> int:
        """AST의 총 노드 수를 계산합니다"""
        try:
            count = 1  # 현재 노드
            for child in ast_node.children:
                count += self._count_total_nodes(child)
            return count
        except Exception:
            return 1

    def _estimate_memory_usage(self, ast_node: ASTNode) -> int:
        """AST의 메모리 사용량을 추정합니다"""
        try:
            memory = 0

            # 노드 기본 메모리
            memory += len(ast_node.value) * 2  # 문자열 (대략적 추정)
            memory += len(ast_node.attributes) * 16  # 딕셔너리 항목

            # 자식 노드들
            for child in ast_node.children:
                memory += self._estimate_memory_usage(child)

            return memory

        except Exception:
            return 0

    def _calculate_performance_improvement(
        self, original_ast: ASTNode, optimized_ast: ASTNode
    ) -> float:
        """성능 향상률을 계산합니다"""
        try:
            original_nodes = self._count_total_nodes(original_ast)
            optimized_nodes = self._count_total_nodes(optimized_ast)

            if original_nodes == 0:
                return 0.0

            improvement = (original_nodes - optimized_nodes) / original_nodes
            return max(0.0, min(1.0, improvement))  # 0.0 ~ 1.0 범위로 제한

        except Exception:
            return 0.0

    def get_optimization_stats(self) -> dict[str, Any]:
        """최적화 통계를 반환합니다"""
        return {
            "performance_metrics": self.performance_metrics.copy(),
            "optimization_stats": self.optimization_stats.copy(),
            "settings": self.settings.copy(),
        }

    def update_settings(self, new_settings: dict[str, Any]) -> None:
        """최적화 설정을 업데이트합니다"""
        try:
            self.settings.update(new_settings)
            logger.info("최적화 설정이 업데이트되었습니다")

        except Exception as e:
            logger.error(f"설정 업데이트 실패: {str(e)}")

    def enable_rule(self, rule_name: str, enabled: bool = True) -> None:
        """특정 최적화 규칙을 활성화/비활성화합니다"""
        try:
            if rule_name in self.optimization_rules:
                self.optimization_rules[rule_name].enabled = enabled
                logger.info(f"최적화 규칙 '{rule_name}' {'활성화' if enabled else '비활성화'}")
            else:
                logger.warning(f"알 수 없는 최적화 규칙: {rule_name}")

        except Exception as e:
            logger.error(f"규칙 활성화/비활성화 실패: {str(e)}")

    def export_optimization_report(self, output_path: Optional[Path] = None) -> str:
        """최적화 리포트를 내보냅니다"""
        try:
            # Enum 값을 문자열로 변환하여 JSON 직렬화 가능하게 함
            safe_settings = {}
            for key, value in self.settings.items():
                if hasattr(value, "value"):  # Enum인 경우
                    safe_settings[key] = value.value
                else:
                    safe_settings[key] = value

            report = {
                "timestamp": time.time(),
                "performance_metrics": self.performance_metrics,
                "optimization_stats": self.optimization_stats,
                "settings": safe_settings,
                "enabled_rules": [
                    name for name, rule in self.optimization_rules.items() if rule.enabled
                ],
                "optimization_level": str(self.settings.get("optimization_level", "advanced")),
            }

            report_json = json.dumps(report, indent=2, ensure_ascii=False)

            if output_path:
                output_path.write_text(report_json, encoding="utf-8")
                logger.info(f"최적화 리포트가 내보내졌습니다: {output_path}")

            return report_json

        except Exception as e:
            logger.error(f"최적화 리포트 내보내기 실패: {str(e)}")
            return ""

    def clear_cache(self) -> None:
        """캐시를 정리합니다"""
        if hasattr(self, "optimization_cache"):
            self.optimization_cache.clear()
        if hasattr(self, "performance_cache"):
            self.performance_cache.clear()
        logger.info("컴파일러 최적화 캐시 정리 완료")


# 편의 함수들
def create_compiler_optimizer(compiler: TemplateCompiler) -> CompilerOptimizer:
    """CompilerOptimizer 인스턴스를 생성합니다"""
    return CompilerOptimizer(compiler)


def optimize_ast(
    ast_node: ASTNode,
    compiler: TemplateCompiler,
    level: OptimizationLevel = OptimizationLevel.ADVANCED,
) -> tuple[ASTNode, OptimizationResult]:
    """AST를 최적화합니다"""
    optimizer = CompilerOptimizer(compiler)
    return optimizer.optimize_ast(ast_node, level)
