"""
테마 템플릿 컴파일러

이 모듈은 QSS(Qt Style Sheets) 템플릿을 AST로 파싱하고
최적화된 컴파일을 수행하는 TemplateCompiler 클래스를 제공합니다.
"""

import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """AST 노드 타입"""

    ROOT = "root"
    RULE = "rule"
    SELECTOR = "selector"
    PROPERTY = "property"
    VALUE = "value"
    VARIABLE = "variable"
    FUNCTION = "function"
    IMPORT = "import"
    MEDIA = "media"
    KEYFRAME = "keyframe"
    COMMENT = "comment"


@dataclass
class ASTNode:
    """AST 노드 기본 클래스"""

    node_type: NodeType
    value: str = ""
    children: list["ASTNode"] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    line_number: int = 0
    column: int = 0

    def add_child(self, child: "ASTNode") -> None:
        """자식 노드 추가"""
        self.children.append(child)

    def get_children_by_type(self, node_type: NodeType) -> list["ASTNode"]:
        """특정 타입의 자식 노드들을 반환"""
        return [child for child in self.children if child.node_type == node_type]

    def find_nodes_by_type(self, node_type: NodeType) -> list["ASTNode"]:
        """재귀적으로 특정 타입의 노드들을 찾습니다"""
        result = []
        if self.node_type == node_type:
            result.append(self)
        for child in self.children:
            result.extend(child.find_nodes_by_type(node_type))
        return result

    def to_dict(self) -> dict[str, Any]:
        """노드를 딕셔너리로 변환"""
        return {
            "type": self.node_type.value,
            "value": self.value,
            "attributes": self.attributes,
            "line": self.line_number,
            "column": self.column,
            "children": [child.to_dict() for child in self.children],
        }


class TemplateCompiler:
    """QSS 템플릿을 AST로 파싱하고 최적화된 컴파일을 수행하는 클래스"""

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        TemplateCompiler 초기화

        Args:
            templates_dir: 템플릿 디렉토리 경로
        """
        self.templates_dir = templates_dir or Path(__file__).parent.parent / "templates"
        self.ast_cache: dict[str, ASTNode] = {}
        self.compiled_cache: dict[str, str] = {}
        self.optimization_stats: dict[str, dict[str, Any]] = {}

        # 정규식 패턴들 컴파일
        self._compile_patterns()

        # 컴파일러 설정
        self.settings = {
            "minify": True,
            "remove_comments": True,
            "optimize_selectors": True,
            "merge_duplicates": True,
            "cache_enabled": True,
            "max_cache_size": 1000,
        }

        # 성능 측정
        self.performance_metrics = {
            "parse_time": 0.0,
            "compile_time": 0.0,
            "optimize_time": 0.0,
            "total_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def _compile_patterns(self) -> None:
        """정규식 패턴들을 컴파일합니다"""
        # CSS 선택자 패턴
        self.selector_pattern = re.compile(r"([^{]+)\s*\{")

        # CSS 속성-값 패턴
        self.property_pattern = re.compile(r"([^:]+):\s*([^;]+);?")

        # 변수 패턴
        self.var_pattern = re.compile(r"var\(--([^)]+)\)")
        self.simple_var_pattern = re.compile(r"--([a-zA-Z_][a-zA-Z0-9_-]*)")

        # 함수 패턴
        self.function_pattern = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)")

        # 주석 패턴
        self.comment_pattern = re.compile(r"/\*.*?\*/", re.DOTALL)

        # 공백 패턴
        self.whitespace_pattern = re.compile(r"\s+")

        # 미디어 쿼리 패턴
        self.media_pattern = re.compile(r"@media\s+([^{]+)\s*\{")

        # 키프레임 패턴
        self.keyframe_pattern = re.compile(r"@keyframes\s+([^{]+)\s*\{")

        # import 패턴
        self.import_pattern = re.compile(r'@import\s+["\']([^"\']+)["\']')

    def parse_template(self, template_content: str, template_name: str = "") -> ASTNode:
        """
        템플릿 내용을 파싱하여 AST를 생성합니다

        Args:
            template_content: 파싱할 템플릿 내용
            template_name: 템플릿 이름 (캐싱용)

        Returns:
            파싱된 AST 노드
        """
        start_time = time.time()

        try:
            # 캐시 확인
            if self.settings["cache_enabled"] and template_name in self.ast_cache:
                self.performance_metrics["cache_hits"] += 1
                logger.debug(f"AST 캐시 히트: {template_name}")
                return self.ast_cache[template_name]

            self.performance_metrics["cache_misses"] += 1

            # 주석 제거
            if self.settings["remove_comments"]:
                template_content = self.comment_pattern.sub("", template_content)

            # 루트 노드 생성
            root_node = ASTNode(NodeType.ROOT, value="root")

            # 템플릿을 라인별로 분리
            lines = template_content.split("\n")
            current_line = 0

            # 파싱 상태 관리
            in_rule_block = False
            current_rule = None
            brace_count = 0

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                # 미디어 쿼리 처리
                media_match = self.media_pattern.match(line)
                if media_match:
                    media_node = ASTNode(
                        NodeType.MEDIA,
                        value=media_match.group(1).strip(),
                        line_number=line_num,
                        column=0,
                    )
                    root_node.add_child(media_node)
                    current_rule = media_node
                    in_rule_block = True
                    brace_count = 1
                    continue

                # 키프레임 처리
                keyframe_match = self.keyframe_pattern.match(line)
                if keyframe_match:
                    keyframe_node = ASTNode(
                        NodeType.KEYFRAME,
                        value=keyframe_match.group(1).strip(),
                        line_number=line_num,
                        column=0,
                    )
                    root_node.add_child(keyframe_node)
                    current_rule = keyframe_node
                    in_rule_block = True
                    brace_count = 1
                    continue

                # import 처리
                import_match = self.import_pattern.match(line)
                if import_match:
                    import_node = ASTNode(
                        NodeType.IMPORT,
                        value=import_match.group(1).strip(),
                        line_number=line_num,
                        column=0,
                    )
                    root_node.add_child(import_node)
                    continue

                # CSS 규칙 블록 시작
                if "{" in line and not in_rule_block:
                    selector_match = self.selector_pattern.match(line)
                    if selector_match:
                        selector_text = selector_match.group(1).strip()
                        rule_node = ASTNode(
                            NodeType.RULE, value=selector_text, line_number=line_num, column=0
                        )
                        root_node.add_child(rule_node)
                        current_rule = rule_node
                        in_rule_block = True
                        brace_count = line.count("{") - line.count("}")

                # CSS 속성-값 쌍 처리
                elif in_rule_block and current_rule:
                    # 중괄호 개수 추적
                    brace_count += line.count("{") - line.count("}")

                    # 속성-값 파싱
                    property_match = self.property_pattern.search(line)
                    if property_match:
                        property_name = property_match.group(1).strip()
                        property_value = property_match.group(2).strip()

                        # 속성 노드 생성
                        property_node = ASTNode(
                            NodeType.PROPERTY,
                            value=property_name,
                            line_number=line_num,
                            column=line.find(":"),
                        )

                        # 값 노드 생성
                        value_node = ASTNode(
                            NodeType.VALUE,
                            value=property_value,
                            line_number=line_num,
                            column=line.find(":") + 1,
                        )

                        property_node.add_child(value_node)
                        current_rule.add_child(property_node)

                    # 규칙 블록 종료 확인
                    if brace_count <= 0:
                        in_rule_block = False
                        current_rule = None

            # 캐시에 저장
            if self.settings["cache_enabled"] and template_name:
                self._add_to_cache(template_name, root_node, "ast")

            parse_time = time.time() - start_time
            self.performance_metrics["parse_time"] += parse_time

            logger.info(f"템플릿 파싱 완료: {template_name} (소요시간: {parse_time:.4f}초)")
            return root_node

        except Exception as e:
            logger.error(f"템플릿 파싱 실패: {template_name}, 오류: {str(e)}")
            raise

    def compile_template(
        self,
        template_content: str,
        template_name: str = "",
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        템플릿을 컴파일하여 최적화된 QSS를 생성합니다

        Args:
            template_content: 컴파일할 템플릿 내용
            template_name: 템플릿 이름
            context: 컴파일 컨텍스트 (변수, 함수 등)

        Returns:
            컴파일된 QSS 문자열
        """
        start_time = time.time()

        try:
            # 캐시 확인
            cache_key = f"{template_name}_{hash(str(context) if context else '')}"
            if self.settings["cache_enabled"] and cache_key in self.compiled_cache:
                self.performance_metrics["cache_hits"] += 1
                logger.debug(f"컴파일 캐시 히트: {template_name}")
                return self.compiled_cache[cache_key]

            self.performance_metrics["cache_misses"] += 1

            # 1단계: AST 파싱
            ast_node = self.parse_template(template_content, template_name)

            # 2단계: AST 최적화
            optimized_ast = self._optimize_ast(ast_node, context)

            # 3단계: QSS 생성
            compiled_qss = self._generate_qss(optimized_ast, context)

            # 4단계: 최종 최적화
            if self.settings["minify"]:
                compiled_qss = self._minify_qss(compiled_qss)

            # 캐시에 저장
            if self.settings["cache_enabled"]:
                self._add_to_cache(cache_key, compiled_qss, "compiled")

            compile_time = time.time() - start_time
            self.performance_metrics["compile_time"] += compile_time

            logger.info(f"템플릿 컴파일 완료: {template_name} (소요시간: {compile_time:.4f}초)")
            return compiled_qss

        except Exception as e:
            logger.error(f"템플릿 컴파일 실패: {template_name}, 오류: {str(e)}")
            raise

    def _optimize_ast(self, ast_node: ASTNode, context: Optional[dict[str, Any]] = None) -> ASTNode:
        """
        AST를 최적화합니다

        Args:
            ast_node: 최적화할 AST 노드
            context: 최적화 컨텍스트

        Returns:
            최적화된 AST 노드
        """
        start_time = time.time()

        try:
            # AST 복사본 생성
            optimized_ast = self._deep_copy_ast(ast_node)

            # 1. 중복 선택자 병합
            if self.settings["merge_duplicates"]:
                optimized_ast = self._merge_duplicate_selectors(optimized_ast)

            # 2. 선택자 최적화
            if self.settings["optimize_selectors"]:
                optimized_ast = self._optimize_selectors(optimized_ast)

            # 3. 불필요한 규칙 제거
            optimized_ast = self._remove_unnecessary_rules(optimized_ast)

            # 4. 변수 해석
            if context:
                optimized_ast = self._resolve_variables(optimized_ast, context)

            optimize_time = time.time() - start_time
            self.performance_metrics["optimize_time"] += optimize_time

            return optimized_ast

        except Exception as e:
            logger.error(f"AST 최적화 실패: {str(e)}")
            return ast_node

    def _merge_duplicate_selectors(self, ast_node: ASTNode) -> ASTNode:
        """중복 선택자를 병합합니다"""
        try:
            # 규칙 노드들을 선택자별로 그룹화
            selector_groups = defaultdict(list)

            for rule_node in ast_node.find_nodes_by_type(NodeType.RULE):
                selector_groups[rule_node.value].append(rule_node)

            # 중복이 있는 그룹 처리
            for selector, rules in selector_groups.items():
                if len(rules) > 1:
                    # 첫 번째 규칙에 나머지 속성들을 병합
                    main_rule = rules[0]
                    for other_rule in rules[1:]:
                        for property_node in other_rule.children:
                            # 중복 속성 확인
                            existing_property = main_rule.get_children_by_type(NodeType.PROPERTY)
                            if not any(p.value == property_node.value for p in existing_property):
                                main_rule.add_child(property_node)

                    # 중복 규칙들을 제거
                    for other_rule in rules[1:]:
                        if other_rule in ast_node.children:
                            ast_node.children.remove(other_rule)
                        elif other_rule.parent:
                            other_rule.parent.children.remove(other_rule)

            return ast_node

        except Exception as e:
            logger.error(f"중복 선택자 병합 실패: {str(e)}")
            return ast_node

    def _optimize_selectors(self, ast_node: ASTNode) -> ASTNode:
        """CSS 선택자를 최적화합니다"""
        try:
            for rule_node in ast_node.find_nodes_by_type(NodeType.RULE):
                # 선택자 단순화
                optimized_selector = self._simplify_selector(rule_node.value)
                rule_node.value = optimized_selector

            return ast_node

        except Exception as e:
            logger.error(f"선택자 최적화 실패: {str(e)}")
            return ast_node

    def _simplify_selector(self, selector: str) -> str:
        """CSS 선택자를 단순화합니다"""
        try:
            # 불필요한 공백 제거
            selector = self.whitespace_pattern.sub(" ", selector.strip())

            # 중복 공백 제거
            selector = " ".join(selector.split())

            # 선택자 단순화 규칙들
            # 예: div div div -> div div div (유지, CSS 특성상)
            # 예: .class1.class2 -> .class1.class2 (유지)

            return selector

        except Exception as e:
            logger.error(f"선택자 단순화 실패: {selector}, 오류: {str(e)}")
            return selector

    def _remove_unnecessary_rules(self, ast_node: ASTNode) -> ASTNode:
        """불필요한 규칙들을 제거합니다"""
        try:
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
                elif hasattr(rule, "parent") and rule.parent:
                    rule.parent.children.remove(rule)

            return ast_node

        except Exception as e:
            logger.error(f"불필요한 규칙 제거 실패: {str(e)}")
            return ast_node

    def _resolve_variables(self, ast_node: ASTNode, context: dict[str, Any]) -> ASTNode:
        """변수를 해석합니다"""
        try:
            for node in ast_node.find_nodes_by_type(NodeType.VALUE):
                if "var(" in node.value:
                    node.value = self._resolve_css_variable(node.value, context)
                elif "--" in node.value:
                    node.value = self._resolve_simple_variable(node.value, context)

            return ast_node

        except Exception as e:
            logger.error(f"변수 해석 실패: {str(e)}")
            return ast_node

    def _resolve_css_variable(self, value: str, context: dict[str, Any]) -> str:
        """CSS 변수를 해석합니다"""
        try:

            def replace_var(match):
                var_name = match.group(1)
                return context.get(var_name, f"var(--{var_name})")

            return self.var_pattern.sub(replace_var, value)

        except Exception as e:
            logger.error(f"CSS 변수 해석 실패: {value}, 오류: {str(e)}")
            return value

    def _resolve_simple_variable(self, value: str, context: dict[str, Any]) -> str:
        """간단한 변수를 해석합니다"""
        try:

            def replace_simple_var(match):
                var_name = match.group(1)
                return context.get(var_name, f"--{var_name}")

            return self.simple_var_pattern.sub(replace_simple_var, value)

        except Exception as e:
            logger.error(f"간단한 변수 해석 실패: {value}, 오류: {str(e)}")
            return value

    def _generate_qss(self, ast_node: ASTNode, context: Optional[dict[str, Any]] = None) -> str:
        """AST에서 QSS를 생성합니다"""
        try:
            qss_parts = []

            for child in ast_node.children:
                if child.node_type == NodeType.RULE:
                    qss_parts.append(self._generate_rule_qss(child))
                elif child.node_type == NodeType.MEDIA:
                    qss_parts.append(self._generate_media_qss(child))
                elif child.node_type == NodeType.KEYFRAME:
                    qss_parts.append(self._generate_keyframe_qss(child))
                elif child.node_type == NodeType.IMPORT:
                    qss_parts.append(self._generate_import_qss(child))

            return "\n\n".join(qss_parts)

        except Exception as e:
            logger.error(f"QSS 생성 실패: {str(e)}")
            return ""

    def _generate_rule_qss(self, rule_node: ASTNode) -> str:
        """규칙 노드에서 QSS를 생성합니다"""
        try:
            qss_parts = [f"{rule_node.value} {{"]

            for property_node in rule_node.get_children_by_type(NodeType.PROPERTY):
                if property_node.children:
                    value = property_node.children[0].value
                    qss_parts.append(f"    {property_node.value}: {value};")

            qss_parts.append("}")
            return "\n".join(qss_parts)

        except Exception as e:
            logger.error(f"규칙 QSS 생성 실패: {str(e)}")
            return ""

    def _generate_media_qss(self, media_node: ASTNode) -> str:
        """미디어 노드에서 QSS를 생성합니다"""
        try:
            qss_parts = [f"@media {media_node.value} {{"]

            for child in media_node.children:
                if child.node_type == NodeType.RULE:
                    qss_parts.append(self._generate_rule_qss(child))

            qss_parts.append("}")
            return "\n".join(qss_parts)

        except Exception as e:
            logger.error(f"미디어 QSS 생성 실패: {str(e)}")
            return ""

    def _generate_keyframe_qss(self, keyframe_node: ASTNode) -> str:
        """키프레임 노드에서 QSS를 생성합니다"""
        try:
            qss_parts = [f"@keyframes {keyframe_node.value} {{"]

            for child in keyframe_node.children:
                if child.node_type == NodeType.RULE:
                    qss_parts.append(self._generate_rule_qss(child))

            qss_parts.append("}")
            return "\n".join(qss_parts)

        except Exception as e:
            logger.error(f"키프레임 QSS 생성 실패: {str(e)}")
            return ""

    def _generate_import_qss(self, import_node: ASTNode) -> str:
        """import 노드에서 QSS를 생성합니다"""
        try:
            return f'@import "{import_node.value}";'
        except Exception as e:
            logger.error(f"import QSS 생성 실패: {str(e)}")
            return ""

    def _minify_qss(self, qss: str) -> str:
        """QSS를 최소화합니다"""
        try:
            # 주석 제거
            qss = self.comment_pattern.sub("", qss)

            # 불필요한 공백 제거
            qss = self.whitespace_pattern.sub(" ", qss)

            # 선택자와 중괄호 사이 공백 제거
            qss = re.sub(r"\s*\{\s*", "{", qss)
            qss = re.sub(r"\s*\}\s*", "}", qss)

            # 속성-값 사이 공백 제거
            qss = re.sub(r"\s*:\s*", ":", qss)
            qss = re.sub(r"\s*;\s*", ";", qss)

            # 줄바꿈 제거
            qss = qss.replace("\n", "")

            return qss

        except Exception as e:
            logger.error(f"QSS 최소화 실패: {str(e)}")
            return qss

    def _deep_copy_ast(self, ast_node: ASTNode) -> ASTNode:
        """AST를 깊은 복사합니다"""
        try:
            new_node = ASTNode(
                node_type=ast_node.node_type,
                value=ast_node.value,
                attributes=ast_node.attributes.copy(),
                line_number=ast_node.line_number,
                column=ast_node.column,
            )

            for child in ast_node.children:
                new_child = self._deep_copy_ast(child)
                new_node.add_child(new_child)

            return new_node

        except Exception as e:
            logger.error(f"AST 깊은 복사 실패: {str(e)}")
            return ast_node

    def _add_to_cache(self, key: str, value: Any, cache_type: str) -> None:
        """캐시에 항목을 추가합니다"""
        try:
            if cache_type == "ast":
                if len(self.ast_cache) >= self.settings["max_cache_size"]:
                    # LRU 방식으로 오래된 항목 제거
                    oldest_key = next(iter(self.ast_cache))
                    del self.ast_cache[oldest_key]
                self.ast_cache[key] = value
            elif cache_type == "compiled":
                if len(self.compiled_cache) >= self.settings["max_cache_size"]:
                    oldest_key = next(iter(self.compiled_cache))
                    del self.compiled_cache[oldest_key]
                self.compiled_cache[key] = value

        except Exception as e:
            logger.error(f"캐시 추가 실패: {str(e)}")

    def get_performance_metrics(self) -> dict[str, Any]:
        """성능 메트릭을 반환합니다"""
        return self.performance_metrics.copy()

    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """캐시를 정리합니다"""
        try:
            if cache_type is None or cache_type == "ast":
                self.ast_cache.clear()
            if cache_type is None or cache_type == "compiled":
                self.compiled_cache.clear()

            logger.info("캐시가 정리되었습니다")

        except Exception as e:
            logger.error(f"캐시 정리 실패: {str(e)}")

    def update_settings(self, new_settings: dict[str, Any]) -> None:
        """컴파일러 설정을 업데이트합니다"""
        try:
            self.settings.update(new_settings)
            logger.info("컴파일러 설정이 업데이트되었습니다")

        except Exception as e:
            logger.error(f"설정 업데이트 실패: {str(e)}")

    def export_ast(self, ast_node: ASTNode, output_path: Optional[Path] = None) -> str:
        """AST를 JSON 형태로 내보냅니다"""
        try:
            ast_dict = ast_node.to_dict()
            ast_json = json.dumps(ast_dict, indent=2, ensure_ascii=False)

            if output_path:
                output_path.write_text(ast_json, encoding="utf-8")
                logger.info(f"AST가 내보내졌습니다: {output_path}")

            return ast_json

        except Exception as e:
            logger.error(f"AST 내보내기 실패: {str(e)}")
            return ""

    def validate_template(self, template_content: str) -> dict[str, Any]:
        """템플릿 유효성을 검사합니다"""
        try:
            validation_result = {"is_valid": True, "errors": [], "warnings": [], "stats": {}}

            # AST 파싱 시도
            try:
                ast_node = self.parse_template(template_content)
                validation_result["stats"]["total_rules"] = len(
                    ast_node.find_nodes_by_type(NodeType.RULE)
                )
                validation_result["stats"]["total_properties"] = len(
                    ast_node.find_nodes_by_type(NodeType.PROPERTY)
                )
                validation_result["stats"]["total_variables"] = len(
                    ast_node.find_nodes_by_type(NodeType.VARIABLE)
                )
            except Exception as e:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"파싱 오류: {str(e)}")

            # 기본 검증
            if not template_content.strip():
                validation_result["warnings"].append("템플릿이 비어있습니다")

            if "var(" in template_content and "--" not in template_content:
                validation_result["warnings"].append("CSS 변수 정의가 없습니다")

            return validation_result

        except Exception as e:
            logger.error(f"템플릿 검증 실패: {str(e)}")
            return {"is_valid": False, "errors": [str(e)], "warnings": [], "stats": {}}


# 편의 함수들
def create_template_compiler(templates_dir: Optional[Path] = None) -> TemplateCompiler:
    """TemplateCompiler 인스턴스를 생성합니다"""
    return TemplateCompiler(templates_dir)


def compile_template(
    template_content: str,
    templates_dir: Optional[Path] = None,
    context: Optional[dict[str, Any]] = None,
) -> str:
    """템플릿을 컴파일합니다"""
    compiler = TemplateCompiler(templates_dir)
    return compiler.compile_template(template_content, context=context)


def parse_template(template_content: str, templates_dir: Optional[Path] = None) -> ASTNode:
    """템플릿을 파싱하여 AST를 생성합니다"""
    compiler = TemplateCompiler(templates_dir)
    return compiler.parse_template(template_content)
