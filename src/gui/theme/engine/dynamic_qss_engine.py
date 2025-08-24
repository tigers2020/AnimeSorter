"""
동적 QSS 생성 엔진

이 모듈은 조건부 스타일 적용과 동적 테마 생성을 담당하는
DynamicQSSEngine 클래스를 제공합니다.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time
import json

from .template_compiler import ASTNode, NodeType, TemplateCompiler
from .compiler_optimizer import CompilerOptimizer, OptimizationLevel

logger = logging.getLogger(__name__)


class ConditionType(Enum):
    """조건 타입"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX_MATCH = "regex_match"
    CUSTOM = "custom"


class MediaQueryType(Enum):
    """미디어 쿼리 타입"""
    SCREEN_SIZE = "screen_size"
    DARK_MODE = "dark_mode"
    HIGH_CONTRAST = "high_contrast"
    REDUCED_MOTION = "reduced_motion"
    PRINT = "print"
    CUSTOM = "custom"


@dataclass
class StyleCondition:
    """스타일 조건"""
    condition_type: ConditionType
    property_name: str
    value: Any
    operator: str = "=="
    custom_function: Optional[str] = None
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """조건을 평가합니다"""
        try:
            if self.condition_type == ConditionType.CUSTOM and self.custom_function:
                return self._evaluate_custom_function(context)
            
            context_value = context.get(self.property_name)
            
            if self.condition_type == ConditionType.EQUALS:
                return context_value == self.value
            elif self.condition_type == ConditionType.NOT_EQUALS:
                return context_value != self.value
            elif self.condition_type == ConditionType.GREATER_THAN:
                return context_value > self.value
            elif self.condition_type == ConditionType.LESS_THAN:
                return context_value < self.value
            elif self.condition_type == ConditionType.CONTAINS:
                return self.value in context_value if context_value else False
            elif self.condition_type == ConditionType.NOT_CONTAINS:
                return self.value not in context_value if context_value else True
            elif self.condition_type == ConditionType.REGEX_MATCH:
                if isinstance(context_value, str) and isinstance(self.value, str):
                    return bool(re.match(self.value, context_value))
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"조건 평가 실패: {str(e)}")
            return False
    
    def _evaluate_custom_function(self, context: Dict[str, Any]) -> bool:
        """커스텀 함수를 평가합니다"""
        try:
            # 간단한 표현식 평가 (보안상 제한적)
            if self.custom_function:
                # 안전한 수학 표현식만 허용
                safe_expr = re.sub(r'[^a-zA-Z0-9_+\-*/()<>=!&\|]', '', self.custom_function)
                # 컨텍스트 변수들을 안전하게 대체
                for key, value in context.items():
                    if isinstance(value, (int, float)):
                        safe_expr = safe_expr.replace(key, str(value))
                
                # eval 대신 안전한 방법 사용 (실제 구현에서는 더 안전한 방법 필요)
                return eval(safe_expr) if safe_expr else False
            
            return False
            
        except Exception as e:
            logger.error(f"커스텀 함수 평가 실패: {str(e)}")
            return False


@dataclass
class MediaQuery:
    """미디어 쿼리"""
    query_type: MediaQueryType
    conditions: List[StyleCondition]
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    orientation: Optional[str] = None
    custom_query: Optional[str] = None
    
    def generate_css(self) -> str:
        """CSS 미디어 쿼리를 생성합니다"""
        try:
            parts = []
            
            if self.query_type == MediaQueryType.SCREEN_SIZE:
                if self.min_width:
                    parts.append(f"(min-width: {self.min_width}px)")
                if self.max_width:
                    parts.append(f"(max-width: {self.max_width}px)")
                if self.min_height:
                    parts.append(f"(min-height: {self.min_height}px)")
                if self.max_height:
                    parts.append(f"(max-height: {self.max_height}px)")
            
            elif self.query_type == MediaQueryType.DARK_MODE:
                parts.append("(prefers-color-scheme: dark)")
            
            elif self.query_type == MediaQueryType.HIGH_CONTRAST:
                parts.append("(prefers-contrast: high)")
            
            elif self.query_type == MediaQueryType.REDUCED_MOTION:
                parts.append("(prefers-reduced-motion: reduce)")
            
            elif self.query_type == MediaQueryType.PRINT:
                parts.append("print")
            
            elif self.query_type == MediaQueryType.CUSTOM and self.custom_query:
                parts.append(self.custom_query)
            
            # 방향성 추가
            if self.orientation:
                parts.append(f"(orientation: {self.orientation})")
            
            return " and ".join(parts) if parts else ""
            
        except Exception as e:
            logger.error(f"CSS 미디어 쿼리 생성 실패: {str(e)}")
            return ""


@dataclass
class DynamicStyle:
    """동적 스타일"""
    selector: str
    properties: Dict[str, str]
    conditions: List[StyleCondition]
    media_queries: List[MediaQuery]
    priority: int = 0
    enabled: bool = True
    
    def should_apply(self, context: Dict[str, Any]) -> bool:
        """스타일을 적용해야 하는지 확인합니다"""
        try:
            if not self.enabled:
                return False
            
            # 모든 조건이 참이어야 함
            for condition in self.conditions:
                if not condition.evaluate(context):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"동적 스타일 적용 조건 확인 실패: {str(e)}")
            return False
    
    def generate_qss(self, context: Dict[str, Any]) -> str:
        """QSS를 생성합니다"""
        try:
            if not self.should_apply(context):
                return ""
            
            qss_parts = []
            
            # 미디어 쿼리가 있는 경우
            if self.media_queries:
                for media_query in self.media_queries:
                    media_css = media_query.generate_css()
                    if media_css:
                        qss_parts.append(f"@media {media_css} {{")
                        qss_parts.append(self._generate_rule_qss())
                        qss_parts.append("}")
                    else:
                        qss_parts.append(self._generate_rule_qss())
            else:
                qss_parts.append(self._generate_rule_qss())
            
            return '\n'.join(qss_parts)
            
        except Exception as e:
            logger.error(f"QSS 생성 실패: {str(e)}")
            return ""
    
    def _generate_rule_qss(self) -> str:
        """규칙 QSS를 생성합니다"""
        try:
            qss_parts = [f"{self.selector} {{"]
            
            for property_name, property_value in self.properties.items():
                qss_parts.append(f"    {property_name}: {property_value};")
            
            qss_parts.append("}")
            return '\n'.join(qss_parts)
            
        except Exception as e:
            logger.error(f"규칙 QSS 생성 실패: {str(e)}")
            return ""


class DynamicQSSEngine:
    """동적 QSS 생성 엔진"""

    def __init__(self, compiler: TemplateCompiler, optimizer: Optional[CompilerOptimizer] = None):
        """
        DynamicQSSEngine 초기화

        Args:
            compiler: TemplateCompiler 인스턴스
            optimizer: CompilerOptimizer 인스턴스 (선택사항)
        """
        self.compiler = compiler
        self.optimizer = optimizer or CompilerOptimizer(compiler)
        
        # 동적 스타일 저장소
        self.dynamic_styles: List[DynamicStyle] = []
        self.style_cache: Dict[str, str] = {}
        
        # 컨텍스트 관리
        self.global_context: Dict[str, Any] = {}
        self.context_history: List[Dict[str, Any]] = []
        
        # 성능 측정
        self.performance_metrics = {
            'generation_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'styles_generated': 0,
            'conditions_evaluated': 0
        }
        
        # 엔진 설정
        self.settings = {
            'enable_caching': True,
            'max_cache_size': 1000,
            'enable_optimization': True,
            'optimization_level': OptimizationLevel.ADVANCED,
            'enable_media_queries': True,
            'enable_conditional_styles': True,
            'auto_cleanup_cache': True,
            'cache_ttl': 300  # 5분
        }

    def add_dynamic_style(self, style: DynamicStyle) -> None:
        """동적 스타일을 추가합니다"""
        try:
            self.dynamic_styles.append(style)
            # 우선순위에 따라 정렬
            self.dynamic_styles.sort(key=lambda s: s.priority, reverse=True)
            logger.info(f"동적 스타일 추가됨: {style.selector}")
            
        except Exception as e:
            logger.error(f"동적 스타일 추가 실패: {str(e)}")

    def remove_dynamic_style(self, selector: str) -> bool:
        """동적 스타일을 제거합니다"""
        try:
            initial_count = len(self.dynamic_styles)
            self.dynamic_styles = [s for s in self.dynamic_styles if s.selector != selector]
            removed_count = initial_count - len(self.dynamic_styles)
            
            if removed_count > 0:
                logger.info(f"동적 스타일 제거됨: {selector} ({removed_count}개)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"동적 스타일 제거 실패: {str(e)}")
            return False

    def update_global_context(self, context: Dict[str, Any]) -> None:
        """전역 컨텍스트를 업데이트합니다"""
        try:
            # 컨텍스트 히스토리에 추가
            self.context_history.append(self.global_context.copy())
            
            # 최대 히스토리 크기 제한
            if len(self.context_history) > 100:
                self.context_history.pop(0)
            
            # 전역 컨텍스트 업데이트
            self.global_context.update(context)
            
            # 캐시 무효화
            if self.settings['enable_caching']:
                self._invalidate_cache()
            
            logger.debug(f"전역 컨텍스트 업데이트됨: {len(context)}개 항목")
            
        except Exception as e:
            logger.error(f"전역 컨텍스트 업데이트 실패: {str(e)}")

    def generate_dynamic_qss(self, template_content: str = "", 
                            additional_context: Optional[Dict[str, Any]] = None) -> str:
        """
        동적 QSS를 생성합니다

        Args:
            template_content: 기본 템플릿 내용
            additional_context: 추가 컨텍스트

        Returns:
            생성된 동적 QSS
        """
        start_time = time.time()
        
        try:
            # 컨텍스트 병합
            context = {**self.global_context}
            if additional_context:
                context.update(additional_context)
            
            # 캐시 확인
            cache_key = self._generate_cache_key(context)
            if self.settings['enable_caching'] and cache_key in self.style_cache:
                self.performance_metrics['cache_hits'] += 1
                logger.debug("동적 QSS 캐시 히트")
                return self.style_cache[cache_key]
            
            self.performance_metrics['cache_misses'] += 1
            
            # 기본 QSS 생성
            base_qss = ""
            if template_content:
                base_qss = self.compiler.compile_template(template_content, context=context)
            
            # 동적 스타일 적용
            dynamic_qss = self._apply_dynamic_styles(context)
            
            # 미디어 쿼리 처리
            media_qss = self._generate_media_queries(context)
            
            # 전체 QSS 조합
            final_qss = self._combine_qss_parts(base_qss, dynamic_qss, media_qss)
            
            # 최적화 적용
            if self.settings['enable_optimization']:
                final_qss = self._optimize_qss(final_qss, context)
            
            # 캐시에 저장
            if self.settings['enable_caching']:
                self._add_to_cache(cache_key, final_qss)
            
            generation_time = time.time() - start_time
            self.performance_metrics['generation_time'] += generation_time
            self.performance_metrics['styles_generated'] += 1
            
            logger.info(f"동적 QSS 생성 완료: {len(final_qss)}자, "
                       f"소요시간: {generation_time:.4f}초")
            
            return final_qss
            
        except Exception as e:
            logger.error(f"동적 QSS 생성 실패: {str(e)}")
            return ""

    def _apply_dynamic_styles(self, context: Dict[str, Any]) -> str:
        """동적 스타일을 적용합니다"""
        try:
            qss_parts = []
            
            # 디버깅: 컨텍스트와 동적 스타일 상태 확인
            logger.debug(f"동적 스타일 적용 시작: {len(self.dynamic_styles)}개 스타일, 컨텍스트: {context}")
            
            for style in self.dynamic_styles:
                logger.debug(f"스타일 '{style.selector}' 조건 평가 중...")
                should_apply = style.should_apply(context)
                logger.debug(f"  - 적용 여부: {should_apply}")
                
                if should_apply:
                    qss = style.generate_qss(context)
                    if qss:
                        qss_parts.append(qss)
                        self.performance_metrics['conditions_evaluated'] += len(style.conditions)
                        logger.debug(f"  - QSS 생성됨: {qss[:100]}...")
                    else:
                        logger.debug(f"  - QSS 생성 실패")
                else:
                    logger.debug(f"  - 조건 불만족으로 스킵")
            
            result = '\n\n'.join(qss_parts)
            logger.debug(f"동적 스타일 적용 완료: {len(qss_parts)}개 스타일 적용됨")
            return result
            
        except Exception as e:
            logger.error(f"동적 스타일 적용 실패: {str(e)}")
            return ""

    def _generate_media_queries(self, context: Dict[str, Any]) -> str:
        """미디어 쿼리를 생성합니다"""
        try:
            if not self.settings['enable_media_queries']:
                return ""
            
            qss_parts = []
            
            # 화면 크기 기반 미디어 쿼리
            screen_width = context.get('screen_width', 1920)
            screen_height = context.get('screen_height', 1080)
            
            # 반응형 브레이크포인트
            breakpoints = [
                (480, 'mobile'),
                (768, 'tablet'),
                (1024, 'desktop'),
                (1440, 'large_desktop')
            ]
            
            for breakpoint, device_type in breakpoints:
                if screen_width <= breakpoint:
                    qss_parts.append(f"/* {device_type} styles */")
                    qss_parts.append(self._generate_device_specific_styles(device_type, context))
                    break
            
            # 다크 모드 지원
            if context.get('dark_mode', False):
                qss_parts.append("/* Dark mode styles */")
                qss_parts.append(self._generate_dark_mode_styles(context))
            
            # 고대비 모드 지원
            if context.get('high_contrast', False):
                qss_parts.append("/* High contrast styles */")
                qss_parts.append(self._generate_high_contrast_styles(context))
            
            return '\n\n'.join(qss_parts)
            
        except Exception as e:
            logger.error(f"미디어 쿼리 생성 실패: {str(e)}")
            return ""

    def _generate_device_specific_styles(self, device_type: str, context: Dict[str, Any]) -> str:
        """디바이스별 스타일을 생성합니다"""
        try:
            device_styles = {
                'mobile': {
                    'font-size': '14px',
                    'padding': '8px',
                    'margin': '4px'
                },
                'tablet': {
                    'font-size': '16px',
                    'padding': '12px',
                    'margin': '8px'
                },
                'desktop': {
                    'font-size': '18px',
                    'padding': '16px',
                    'margin': '12px'
                },
                'large_desktop': {
                    'font-size': '20px',
                    'padding': '20px',
                    'margin': '16px'
                }
            }
            
            styles = device_styles.get(device_type, {})
            qss_parts = []
            
            for property_name, property_value in styles.items():
                qss_parts.append(f"    {property_name}: {property_value};")
            
            return '\n'.join(qss_parts) if qss_parts else ""
            
        except Exception as e:
            logger.error(f"디바이스별 스타일 생성 실패: {str(e)}")
            return ""

    def _generate_dark_mode_styles(self, context: Dict[str, Any]) -> str:
        """다크 모드 스타일을 생성합니다"""
        try:
            dark_styles = {
                'background-color': '#1a1a1a',
                'color': '#ffffff',
                'border-color': '#333333'
            }
            
            qss_parts = []
            for property_name, property_value in dark_styles.items():
                qss_parts.append(f"    {property_name}: {property_value};")
            
            return '\n'.join(qss_parts) if qss_parts else ""
            
        except Exception as e:
            logger.error(f"다크 모드 스타일 생성 실패: {str(e)}")
            return ""

    def _generate_high_contrast_styles(self, context: Dict[str, Any]) -> str:
        """고대비 모드 스타일을 생성합니다"""
        try:
            high_contrast_styles = {
                'background-color': '#000000',
                'color': '#ffffff',
                'border-color': '#ffffff',
                'border-width': '2px'
            }
            
            qss_parts = []
            for property_name, property_value in high_contrast_styles.items():
                qss_parts.append(f"    {property_name}: {property_value};")
            
            return '\n'.join(qss_parts) if qss_parts else ""
            
        except Exception as e:
            logger.error(f"고대비 모드 스타일 생성 실패: {str(e)}")
            return ""

    def _combine_qss_parts(self, base_qss: str, dynamic_qss: str, media_qss: str) -> str:
        """QSS 부분들을 조합합니다"""
        try:
            parts = []
            
            # 디버깅: 각 QSS 부분의 내용 확인
            logger.debug(f"QSS 조합 시작:")
            logger.debug(f"  - base_qss: {repr(base_qss[:100])}...")
            logger.debug(f"  - dynamic_qss: {repr(dynamic_qss[:100])}...")
            logger.debug(f"  - media_qss: {repr(media_qss[:100])}...")
            
            if base_qss:
                parts.append("/* Base styles */")
                parts.append(base_qss)
            
            if dynamic_qss:
                parts.append("/* Dynamic styles */")
                parts.append(dynamic_qss)
            
            if media_qss:
                parts.append("/* Media queries */")
                parts.append(media_qss)
            
            result = '\n\n'.join(parts)
            logger.debug(f"QSS 조합 완료: {len(parts)}개 부분, 총 {len(result)}자")
            logger.debug(f"  - 최종 결과: {repr(result[:200])}...")
            
            return result
            
        except Exception as e:
            logger.error(f"QSS 조합 실패: {str(e)}")
            return base_qss

    def _optimize_qss(self, qss: str, context: Dict[str, Any]) -> str:
        """QSS를 최적화합니다"""
        try:
            if not self.settings['enable_optimization']:
                return qss
            
            # 동적 스타일 부분을 분리하여 보존
            dynamic_parts = []
            base_parts = []
            
            lines = qss.split('\n')
            in_dynamic_section = False
            
            for line in lines:
                if '/* Dynamic styles */' in line:
                    in_dynamic_section = True
                    dynamic_parts.append(line)
                elif '/* ' in line and ' */' in line and 'Dynamic styles' not in line:
                    in_dynamic_section = False
                    base_parts.append(line)
                elif in_dynamic_section:
                    dynamic_parts.append(line)
                else:
                    base_parts.append(line)
            
            # 기본 QSS만 최적화
            base_qss = '\n'.join(base_parts)
            if base_qss.strip():
                # AST로 파싱
                ast_node = self.compiler.parse_template(base_qss)
                
                # 최적화 적용
                optimization_level = self.settings['optimization_level']
                optimized_ast, result = self.optimizer.optimize_ast(ast_node, optimization_level)
                
                # 최적화된 QSS 생성
                optimized_base_qss = self.compiler._generate_qss(optimized_ast, context)
                
                logger.debug(f"QSS 최적화 완료: {result.removed_nodes}개 노드 제거, "
                            f"메모리 {result.memory_saved}바이트 절약")
                
                # 동적 스타일과 최적화된 기본 QSS 조합
                final_parts = []
                if optimized_base_qss.strip():
                    final_parts.append("/* Base styles */")
                    final_parts.append(optimized_base_qss)
                
                if dynamic_parts:
                    final_parts.extend(dynamic_parts)
                
                return '\n\n'.join(final_parts)
            else:
                # 기본 QSS가 없으면 동적 스타일만 반환
                return '\n'.join(dynamic_parts)
            
        except Exception as e:
            logger.error(f"QSS 최적화 실패: {str(e)}")
            return qss

    def _generate_cache_key(self, context: Dict[str, Any]) -> str:
        """캐시 키를 생성합니다"""
        try:
            # 컨텍스트를 정렬된 문자열로 변환
            sorted_items = sorted(context.items())
            context_str = json.dumps(sorted_items, sort_keys=True)
            
            # 동적 스타일 상태를 포함
            style_states = []
            for style in self.dynamic_styles:
                style_states.append(f"{style.selector}:{style.enabled}")
            
            style_str = '|'.join(style_states)
            
            return f"{hash(context_str)}_{hash(style_str)}"
            
        except Exception as e:
            logger.error(f"캐시 키 생성 실패: {str(e)}")
            return str(time.time())

    def _add_to_cache(self, key: str, value: str) -> None:
        """캐시에 항목을 추가합니다"""
        try:
            if len(self.style_cache) >= self.settings['max_cache_size']:
                # LRU 방식으로 오래된 항목 제거
                oldest_key = next(iter(self.style_cache))
                del self.style_cache[oldest_key]
            
            self.style_cache[key] = value
            
        except Exception as e:
            logger.error(f"캐시 추가 실패: {str(e)}")

    def _invalidate_cache(self) -> None:
        """캐시를 무효화합니다"""
        try:
            self.style_cache.clear()
            logger.debug("캐시가 무효화되었습니다")
            
        except Exception as e:
            logger.error(f"캐시 무효화 실패: {str(e)}")

    def create_conditional_style(self, selector: str, properties: Dict[str, str],
                                conditions: List[StyleCondition], priority: int = 0) -> DynamicStyle:
        """조건부 스타일을 생성합니다"""
        try:
            style = DynamicStyle(
                selector=selector,
                properties=properties,
                conditions=conditions,
                media_queries=[],
                priority=priority,
                enabled=True
            )
            
            return style
            
        except Exception as e:
            logger.error(f"조건부 스타일 생성 실패: {str(e)}")
            return None

    def create_media_query_style(self, selector: str, properties: Dict[str, str],
                                media_query: MediaQuery, priority: int = 0) -> DynamicStyle:
        """미디어 쿼리 스타일을 생성합니다"""
        try:
            style = DynamicStyle(
                selector=selector,
                properties=properties,
                conditions=[],
                media_queries=[media_query],
                priority=priority,
                enabled=True
            )
            
            return style
            
        except Exception as e:
            logger.error(f"미디어 쿼리 스타일 생성 실패: {str(e)}")
            return None

    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭을 반환합니다"""
        return self.performance_metrics.copy()

    def clear_cache(self) -> None:
        """캐시를 정리합니다"""
        try:
            self.style_cache.clear()
            logger.info("캐시가 정리되었습니다")
            
        except Exception as e:
            logger.error(f"캐시 정리 실패: {str(e)}")

    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """엔진 설정을 업데이트합니다"""
        try:
            self.settings.update(new_settings)
            logger.info("엔진 설정이 업데이트되었습니다")
            
        except Exception as e:
            logger.error(f"설정 업데이트 실패: {str(e)}")

    def export_dynamic_styles(self, output_path: Optional[Path] = None) -> str:
        """동적 스타일을 내보냅니다"""
        try:
            # Enum 값을 문자열로 변환하여 JSON 직렬화 가능하게 함
            safe_settings = {}
            for key, value in self.settings.items():
                if hasattr(value, 'value'):  # Enum인 경우
                    safe_settings[key] = value.value
                else:
                    safe_settings[key] = value
            
            export_data = {
                'timestamp': time.time(),
                'dynamic_styles': [],
                'global_context': self.global_context,
                'settings': safe_settings
            }
            
            for style in self.dynamic_styles:
                style_data = {
                    'selector': style.selector,
                    'properties': style.properties,
                    'conditions': [
                        {
                            'type': condition.condition_type.value,
                            'property': condition.property_name,
                            'value': condition.value,
                            'operator': condition.operator
                        }
                        for condition in style.conditions
                    ],
                    'media_queries': [
                        {
                            'type': query.query_type.value,
                            'custom_query': query.custom_query
                        }
                        for query in style.media_queries
                    ],
                    'priority': style.priority,
                    'enabled': style.enabled
                }
                export_data['dynamic_styles'].append(style_data)
            
            export_json = json.dumps(export_data, indent=2, ensure_ascii=False)
            
            if output_path:
                output_path.write_text(export_json, encoding='utf-8')
                logger.info(f"동적 스타일이 내보내졌습니다: {output_path}")
            
            return export_json
            
        except Exception as e:
            logger.error(f"동적 스타일 내보내기 실패: {str(e)}")
            return ""


# 편의 함수들
def create_dynamic_qss_engine(compiler: TemplateCompiler, 
                             optimizer: Optional[CompilerOptimizer] = None) -> DynamicQSSEngine:
    """DynamicQSSEngine 인스턴스를 생성합니다"""
    return DynamicQSSEngine(compiler, optimizer)


def create_style_condition(condition_type: ConditionType, property_name: str, 
                          value: Any, operator: str = "==") -> StyleCondition:
    """StyleCondition 인스턴스를 생성합니다"""
    return StyleCondition(condition_type, property_name, value, operator)


def create_media_query(query_type: MediaQueryType, custom_query: Optional[str] = None) -> MediaQuery:
    """MediaQuery 인스턴스를 생성합니다"""
    return MediaQuery(query_type, [], custom_query=custom_query)
