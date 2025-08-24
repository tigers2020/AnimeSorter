"""
테마 템플릿 로더

이 모듈은 QSS(Qt Style Sheets) 템플릿을 로딩하고 관리하는
TemplateLoader 클래스를 제공합니다.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
from collections import defaultdict
from functools import lru_cache

logger = logging.getLogger(__name__)


class TemplateLoader:
    """QSS 템플릿을 로딩하고 관리하는 클래스"""

    def __init__(self, templates_dir: Optional[Union[Path, str]] = None):
        """
        TemplateLoader 초기화

        Args:
            templates_dir: 템플릿 디렉토리 경로 (Path 또는 str, None인 경우 기본 경로 사용)
        """
        if templates_dir is None:
            self.templates_dir = Path(__file__).parent.parent / "templates"
        elif isinstance(templates_dir, str):
            self.templates_dir = Path(templates_dir)
        else:
            self.templates_dir = templates_dir
        self.templates: Dict[str, str] = {}
        self.template_cache: Dict[str, str] = {}
        self.variables: Dict[str, str] = {}
        self.functions: Dict[str, callable] = {}
        self.imports: Dict[str, List[str]] = defaultdict(list)
        
        # 기본 함수들 등록
        self._register_default_functions()
        
        # 성능 최적화를 위한 정규식 패턴 컴파일
        self._compile_patterns()
        
        # 템플릿 디렉토리 검증
        self._validate_templates_directory()

    def _validate_templates_directory(self) -> None:
        """템플릿 디렉토리 유효성 검사"""
        if not self.templates_dir.exists():
            logger.warning(f"템플릿 디렉토리가 존재하지 않습니다: {self.templates_dir}")
            return
        
        if not self.templates_dir.is_dir():
            logger.error(f"템플릿 경로가 디렉토리가 아닙니다: {self.templates_dir}")
            return
        
        logger.info(f"템플릿 디렉토리 로드됨: {self.templates_dir}")

    def _compile_patterns(self) -> None:
        """정규식 패턴들을 컴파일합니다"""
        self.var_pattern = re.compile(r'var\(--([^)]+)\)')
        self.simple_var_pattern = re.compile(r'--([a-zA-Z_][a-zA-Z0-9_-]*)')
        self.function_pattern = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)')
        self.import_pattern = re.compile(r'@import\s+["\']([^"\']+)["\']')
        self.comment_pattern = re.compile(r'/\*.*?\*/', re.DOTALL)
        self.whitespace_pattern = re.compile(r'\s+')

    def _register_default_functions(self) -> None:
        """기본 템플릿 함수들을 등록합니다"""
        self.functions.update({
            'theme': self._get_theme_value,
            'color': self._get_color_value,
            'spacing': self._get_spacing_value,
            'font': self._get_font_value,
            'border': self._get_border_value,
            'shadow': self._get_shadow_value,
            'transition': self._get_transition_value,
            'z_index': self._get_z_index_value,
            'breakpoint': self._get_breakpoint_value,
            'math': self._math_operation,
            'scale': self._scale_value,
            'mix': self._mix_colors,
            'lighten': self._lighten_color,
            'darken': self._darken_color,
            'alpha': self._add_alpha,
            'contrast': self._get_contrast_color,
        })

    def load_template(self, template_name: str, resolve_variables: bool = True) -> str:
        """
        템플릿을 로딩합니다

        Args:
            template_name: 템플릿 이름 (예: 'button', 'main_window')
            resolve_variables: 변수 해석 여부

        Returns:
            로딩된 템플릿 문자열
        """
        try:
            # 캐시 확인
            cache_key = f"{template_name}_{resolve_variables}"
            if cache_key in self.template_cache:
                return self.template_cache[cache_key]

            # 템플릿 파일 경로 찾기
            template_path = self._find_template_file(template_name)
            if not template_path:
                logger.error(f"템플릿을 찾을 수 없습니다: {template_name}")
                return ""

            # 템플릿 파일 읽기
            template_content = template_path.read_text(encoding='utf-8')
            
            # 변수 해석
            if resolve_variables:
                template_content = self._resolve_template_variables(template_content)
            
            # 캐시에 저장
            self.template_cache[cache_key] = template_content
            self.templates[template_name] = template_content
            
            logger.debug(f"템플릿 로드됨: {template_name}")
            return template_content

        except Exception as e:
            logger.error(f"템플릿 로드 실패: {template_name}, 오류: {e}")
            return ""

    def _find_template_file(self, template_name: str) -> Optional[Path]:
        """템플릿 파일 경로를 찾습니다"""
        # 가능한 확장자들
        extensions = ['.qss', '.css']
        
        # 템플릿 이름에서 확장자 제거
        base_name = template_name.replace('.qss', '').replace('.css', '')
        
        # 다양한 경로에서 템플릿 찾기
        search_paths = [
            self.templates_dir / f"{base_name}.qss",
            self.templates_dir / f"{base_name}.css",
            self.templates_dir / "components" / f"{base_name}.qss",
            self.templates_dir / "layouts" / f"{base_name}.qss",
            self.templates_dir / "utilities" / f"{base_name}.qss",
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        
        return None

    def _resolve_template_variables(self, template_content: str) -> str:
        """템플릿 내의 변수들을 해석합니다"""
        try:
            # 주석 제거
            template_content = self.comment_pattern.sub('', template_content)
            
            # @import 문 처리
            template_content = self._process_imports(template_content)
            
            # 변수 해석 (최대 10회 반복으로 무한 루프 방지)
            for _ in range(10):
                new_content = self._resolve_variables(template_content)
                if new_content == template_content:
                    break
                template_content = new_content
            
            # 함수 실행
            template_content = self._execute_functions(template_content)
            
            # 공백 정리
            template_content = self.whitespace_pattern.sub(' ', template_content).strip()
            
            return template_content

        except Exception as e:
            logger.error(f"템플릿 변수 해석 실패: {e}")
            return template_content

    def _process_imports(self, template_content: str) -> str:
        """@import 문을 처리합니다"""
        def replace_import(match):
            import_path = match.group(1)
            try:
                # 상대 경로를 절대 경로로 변환
                if import_path.startswith('./'):
                    import_path = import_path[2:]
                elif import_path.startswith('../'):
                    import_path = import_path[3:]
                
                import_file = self.templates_dir / import_path
                if import_file.exists():
                    imported_content = import_file.read_text(encoding='utf-8')
                    # 재귀적으로 import 처리
                    return self._process_imports(imported_content)
                else:
                    logger.warning(f"Import 파일을 찾을 수 없습니다: {import_path}")
                    return ""
            except Exception as e:
                logger.error(f"Import 처리 실패: {import_path}, 오류: {e}")
                return ""
        
        return self.import_pattern.sub(replace_import, template_content)

    def _resolve_variables(self, content: str) -> str:
        """변수들을 해석합니다"""
        def replace_var(match):
            var_name = match.group(1)
            return self.variables.get(var_name, f"var(--{var_name})")
        
        def replace_simple_var(match):
            var_name = match.group(1)
            return self.variables.get(var_name, f"--{var_name}")
        
        content = self.var_pattern.sub(replace_var, content)
        content = self.simple_var_pattern.sub(replace_simple_var, content)
        return content

    def _execute_functions(self, content: str) -> str:
        """함수 호출을 실행합니다 (최대 5회 반복으로 무한 루프 방지)"""
        for _ in range(5):
            new_content = self.function_pattern.sub(self._execute_function_call, content)
            if new_content == content:
                break
            content = new_content
        return content

    def _execute_function_call(self, match) -> str:
        """함수 호출을 실행합니다"""
        func_name = match.group(1)
        args_str = match.group(2)
        
        if func_name not in self.functions:
            logger.warning(f"알 수 없는 함수: {func_name}")
            return match.group(0)
        
        try:
            # 인수 파싱
            args = self._parse_function_args(args_str)
            
            # 함수 실행
            result = self.functions[func_name](*args)
            return str(result)
        
        except Exception as e:
            logger.error(f"함수 실행 실패: {func_name}({args_str}), 오류: {e}")
            return match.group(0)

    def _parse_function_args(self, args_str: str) -> List[str]:
        """함수 인수를 파싱합니다"""
        if not args_str.strip():
            return []
        
        args = []
        current_arg = ""
        paren_depth = 0
        quote_char = None
        
        for char in args_str:
            if quote_char is None and char in '"\'':
                quote_char = char
            elif quote_char == char:
                quote_char = None
            elif quote_char is not None:
                current_arg += char
            elif char == '(':
                paren_depth += 1
                current_arg += char
            elif char == ')':
                paren_depth -= 1
                current_arg += char
            elif char == ',' and paren_depth == 0:
                args.append(current_arg.strip())
                current_arg = ""
            else:
                current_arg += char
        
        if current_arg.strip():
            args.append(current_arg.strip())
        
        return args

    def load_all_templates(self, resolve_variables: bool = True) -> Dict[str, str]:
        """모든 템플릿을 로딩합니다"""
        try:
            all_templates = {}
            
            # components 디렉토리
            components_dir = self.templates_dir / "components"
            if components_dir.exists():
                for qss_file in components_dir.glob("*.qss"):
                    template_name = qss_file.stem
                    all_templates[template_name] = self.load_template(template_name, resolve_variables)
            
            # layouts 디렉토리
            layouts_dir = self.templates_dir / "layouts"
            if layouts_dir.exists():
                for qss_file in layouts_dir.glob("*.qss"):
                    template_name = qss_file.stem
                    all_templates[template_name] = self.load_template(template_name, resolve_variables)
            
            # utilities 디렉토리
            utilities_dir = self.templates_dir / "utilities"
            if utilities_dir.exists():
                for qss_file in utilities_dir.glob("*.qss"):
                    template_name = qss_file.stem
                    all_templates[template_name] = self.load_template(template_name, resolve_variables)
            
            logger.info(f"총 {len(all_templates)}개의 템플릿 로드됨")
            return all_templates

        except Exception as e:
            logger.error(f"모든 템플릿 로드 실패: {e}")
            return {}

    def get_template(self, template_name: str, default: str = "") -> str:
        """
        템플릿을 가져옵니다 (캐시 적용)

        Args:
            template_name: 템플릿 이름
            default: 기본값

        Returns:
            템플릿 문자열
        """
        if template_name in self.templates:
            return self.templates[template_name]
        
        # 로딩 시도
        loaded_template = self.load_template(template_name)
        if loaded_template:
            return loaded_template
        
        return default

    def set_template(self, template_name: str, content: str) -> None:
        """
        템플릿을 설정합니다

        Args:
            template_name: 템플릿 이름
            content: 템플릿 내용
        """
        try:
            self.templates[template_name] = content
            # 캐시 무효화
            self._clear_template_cache(template_name)
            logger.debug(f"템플릿 설정: {template_name}")
        except Exception as e:
            logger.error(f"템플릿 설정 실패: {template_name}, 오류: {e}")

    def save_template(self, template_name: str, content: str, category: str = "components") -> bool:
        """
        템플릿을 파일로 저장합니다

        Args:
            template_name: 템플릿 이름
            content: 템플릿 내용
            category: 템플릿 카테고리 (components, layouts, utilities)

        Returns:
            저장 성공 여부
        """
        try:
            category_dir = self.templates_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            template_file = category_dir / f"{template_name}.qss"
            template_file.write_text(content, encoding='utf-8')
            
            # 메모리에도 저장
            self.set_template(template_name, content)
            
            logger.info(f"템플릿 저장됨: {category}/{template_name}.qss")
            return True

        except Exception as e:
            logger.error(f"템플릿 저장 실패: {template_name}, 오류: {e}")
            return False

    def delete_template(self, template_name: str) -> bool:
        """
        템플릿을 삭제합니다

        Args:
            template_name: 템플릿 이름

        Returns:
            삭제 성공 여부
        """
        try:
            # 메모리에서 제거
            if template_name in self.templates:
                del self.templates[template_name]
            
            # 캐시에서 제거
            self._clear_template_cache(template_name)
            
            # 파일에서 제거
            template_path = self._find_template_file(template_name)
            if template_path and template_path.exists():
                template_path.unlink()
                logger.info(f"템플릿 파일 삭제됨: {template_path}")
            
            logger.info(f"템플릿 삭제됨: {template_name}")
            return True

        except Exception as e:
            logger.error(f"템플릿 삭제 실패: {template_name}, 오류: {e}")
            return False

    def _clear_template_cache(self, template_name: str = None) -> None:
        """템플릿 캐시를 무효화합니다"""
        if template_name:
            # 특정 템플릿의 캐시만 무효화
            keys_to_remove = [k for k in self.template_cache.keys() if k.startswith(f"{template_name}_")]
            for key in keys_to_remove:
                del self.template_cache[key]
        else:
            # 전체 캐시 무효화
            self.template_cache.clear()

    def clear_templates(self) -> None:
        """모든 템플릿을 제거합니다"""
        self.templates.clear()
        self.template_cache.clear()
        logger.info("모든 템플릿 제거됨")

    def get_template_names(self) -> List[str]:
        """사용 가능한 템플릿 이름 목록을 반환합니다"""
        return list(self.templates.keys())

    def get_template_paths(self) -> Dict[str, Path]:
        """템플릿 이름과 파일 경로의 매핑을 반환합니다"""
        paths = {}
        for template_name in self.templates.keys():
            template_path = self._find_template_file(template_name)
            if template_path:
                paths[template_name] = template_path
        return paths

    def search_templates(self, query: str) -> List[str]:
        """
        템플릿을 검색합니다

        Args:
            query: 검색 쿼리

        Returns:
            검색 결과 템플릿 이름 목록
        """
        results = []
        query_lower = query.lower()
        
        for template_name, content in self.templates.items():
            if (query_lower in template_name.lower() or 
                query_lower in content.lower()):
                results.append(template_name)
        
        return results

    def validate_template(self, template_name: str) -> Tuple[bool, List[str]]:
        """
        템플릿 유효성을 검사합니다

        Args:
            template_name: 템플릿 이름

        Returns:
            (유효성 여부, 오류 메시지 목록)
        """
        errors = []
        
        if template_name not in self.templates:
            errors.append(f"템플릿이 존재하지 않습니다: {template_name}")
            return False, errors
        
        content = self.templates[template_name]
        
        # 기본 QSS 문법 검사
        if not self._validate_qss_syntax(content):
            errors.append("QSS 문법 오류가 있습니다")
        
        # 변수 참조 검사
        undefined_vars = self._find_undefined_variables(content)
        if undefined_vars:
            errors.append(f"정의되지 않은 변수: {', '.join(undefined_vars)}")
        
        # 함수 호출 검사
        undefined_funcs = self._find_undefined_functions(content)
        if undefined_funcs:
            errors.append(f"정의되지 않은 함수: {', '.join(undefined_funcs)}")
        
        return len(errors) == 0, errors

    def _validate_qss_syntax(self, content: str) -> bool:
        """QSS 문법 유효성을 검사합니다"""
        try:
            # 기본적인 QSS 구조 검사
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('/*') and not line.startswith('@'):
                    # 선택자나 속성 라인 검사
                    if ':' in line and not line.startswith(':'):
                        # 속성:값 형식 검사
                        if line.count(':') == 1:
                            parts = line.split(':')
                            if len(parts) != 2:
                                return False
            return True
        except Exception:
            return False

    def _find_undefined_variables(self, content: str) -> List[str]:
        """정의되지 않은 변수들을 찾습니다"""
        undefined_vars = []
        
        # var(--variable) 형식 검사
        var_matches = self.var_pattern.findall(content)
        for var_name in var_matches:
            if var_name not in self.variables:
                undefined_vars.append(var_name)
        
        # --variable 형식 검사
        simple_var_matches = self.simple_var_pattern.findall(content)
        for var_name in simple_var_matches:
            if var_name not in self.variables:
                undefined_vars.append(var_name)
        
        return list(set(undefined_vars))

    def _find_undefined_functions(self, content: str) -> List[str]:
        """정의되지 않은 함수들을 찾습니다"""
        undefined_funcs = []
        
        func_matches = self.function_pattern.findall(content)
        for func_name, _ in func_matches:
            if func_name not in self.functions:
                undefined_funcs.append(func_name)
        
        return list(set(undefined_funcs))

    # 기본 함수들 구현
    def _get_theme_value(self, *args) -> str:
        """테마 값 가져오기"""
        if not args:
            return ""
        return self.variables.get(args[0], "")

    def _get_color_value(self, *args) -> str:
        """색상 값 가져오기"""
        if not args:
            return ""
        return self.variables.get(f"color-{args[0]}", "")

    def _get_spacing_value(self, *args) -> str:
        """간격 값 가져오기"""
        if not args:
            return ""
        return self.variables.get(f"spacing-{args[0]}", "")

    def _get_font_value(self, *args) -> str:
        """폰트 값 가져오기"""
        if not args:
            return ""
        return self.variables.get(f"font-{args[0]}", "")

    def _get_border_value(self, *args) -> str:
        """테두리 값 가져오기"""
        if not args:
            return ""
        return self.variables.get(f"border-{args[0]}", "")

    def _get_shadow_value(self, *args) -> str:
        """그림자 값 가져오기"""
        if not args:
            return ""
        return self.variables.get(f"shadow-{args[0]}", "")

    def _get_transition_value(self, *args) -> str:
        """전환 값 가져오기"""
        if not args:
            return ""
        return self.variables.get(f"transition-{args[0]}", "")

    def _get_z_index_value(self, *args) -> str:
        """Z-Index 값 가져오기"""
        if not args:
            return ""
        return self.variables.get(f"z-index-{args[0]}", "")

    def _get_breakpoint_value(self, *args) -> str:
        """브레이크포인트 값 가져오기"""
        if not args:
            return ""
        return self.variables.get(f"breakpoint-{args[0]}", "")

    def _math_operation(self, *args) -> str:
        """수학 연산 수행"""
        if len(args) < 3:
            return ""
        
        try:
            left = float(args[0])
            operator = args[1]
            right = float(args[2])
            
            if operator == '+':
                result = left + right
            elif operator == '-':
                result = left - right
            elif operator == '*':
                result = left * right
            elif operator == '/':
                result = left / right if right != 0 else 0
            else:
                return ""
            
            return str(result)
        except (ValueError, ZeroDivisionError):
            return ""

    def _scale_value(self, *args) -> str:
        """값을 스케일링합니다"""
        if len(args) < 2:
            return ""
        
        try:
            value = float(args[0])
            scale = float(args[1])
            return str(value * scale)
        except ValueError:
            return ""

    def _mix_colors(self, *args) -> str:
        """색상을 혼합합니다"""
        if len(args) < 3:
            return ""
        
        try:
            color1 = args[0]
            color2 = args[1]
            weight = float(args[2])
            
            # 간단한 색상 혼합 (실제로는 더 복잡한 로직 필요)
            return color1 if weight > 0.5 else color2
        except ValueError:
            return ""

    def _lighten_color(self, *args) -> str:
        """색상을 밝게 만듭니다"""
        if len(args) < 2:
            return ""
        
        try:
            color = args[0]
            amount = float(args[1])
            # 실제 구현에서는 색상 변환 로직 필요
            return color
        except ValueError:
            return ""

    def _darken_color(self, *args) -> str:
        """색상을 어둡게 만듭니다"""
        if len(args) < 2:
            return ""
        
        try:
            color = args[0]
            amount = float(args[1])
            # 실제 구현에서는 색상 변환 로직 필요
            return color
        except ValueError:
            return ""

    def _add_alpha(self, *args) -> str:
        """색상에 알파값을 추가합니다"""
        if len(args) < 2:
            return ""
        
        try:
            color = args[0]
            alpha = float(args[1])
            # 실제 구현에서는 색상 변환 로직 필요
            return color
        except ValueError:
            return ""

    def _get_contrast_color(self, *args) -> str:
        """대비 색상을 가져옵니다"""
        if not args:
            return ""
        
        color = args[0]
        # 실제 구현에서는 대비 계산 로직 필요
        return color

    def set_variable(self, name: str, value: str) -> None:
        """변수를 설정합니다"""
        self.variables[name] = value
        logger.debug(f"변수 설정: {name} = {value}")

    def set_variables(self, variables: Dict[str, str]) -> None:
        """여러 변수를 한번에 설정합니다"""
        self.variables.update(variables)
        logger.debug(f"{len(variables)}개의 변수 설정됨")

    def get_variable(self, name: str, default: str = "") -> str:
        """변수 값을 가져옵니다"""
        return self.variables.get(name, default)

    def get_variables(self) -> Dict[str, str]:
        """모든 변수를 가져옵니다"""
        return self.variables.copy()

    def clear_variables(self) -> None:
        """모든 변수를 제거합니다"""
        self.variables.clear()
        logger.info("모든 변수 제거됨")

    def register_function(self, name: str, func: callable) -> None:
        """사용자 정의 함수를 등록합니다"""
        self.functions[name] = func
        logger.debug(f"함수 등록: {name}")

    def unregister_function(self, name: str) -> None:
        """등록된 함수를 제거합니다"""
        if name in self.functions:
            del self.functions[name]
            logger.debug(f"함수 제거: {name}")

    def get_functions(self) -> Dict[str, callable]:
        """등록된 모든 함수를 가져옵니다"""
        return self.functions.copy()

    def reload_templates(self) -> None:
        """모든 템플릿을 다시 로딩합니다"""
        logger.info("템플릿 재로딩 시작")
        
        # 캐시 무효화
        self.template_cache.clear()
        
        # 기존 템플릿들 다시 로딩
        template_names = list(self.templates.keys())
        for template_name in template_names:
            self.load_template(template_name)
        
        logger.info("템플릿 재로딩 완료")

    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        템플릿 정보를 가져옵니다

        Args:
            template_name: 템플릿 이름

        Returns:
            템플릿 정보 딕셔너리
        """
        if template_name not in self.templates:
            return {}
        
        content = self.templates[template_name]
        template_path = self._find_template_file(template_name)
        
        info = {
            'name': template_name,
            'content': content,
            'content_length': len(content),
            'lines': len(content.split('\n')),
            'path': str(template_path) if template_path else None,
            'variables_used': self._find_undefined_variables(content),
            'functions_used': self._find_undefined_functions(content),
            'imports': self.imports.get(template_name, []),
        }
        
        return info

    def export_template(self, template_name: str, export_path: Path) -> bool:
        """
        템플릿을 외부 파일로 내보냅니다

        Args:
            template_name: 템플릿 이름
            export_path: 내보낼 파일 경로

        Returns:
            내보내기 성공 여부
        """
        try:
            if template_name not in self.templates:
                logger.error(f"템플릿이 존재하지 않습니다: {template_name}")
                return False
            
            content = self.templates[template_name]
            export_path.write_text(content, encoding='utf-8')
            
            logger.info(f"템플릿 내보내기 완료: {export_path}")
            return True

        except Exception as e:
            logger.error(f"템플릿 내보내기 실패: {template_name}, 오류: {e}")
            return False

    def import_template(self, import_path: Path, template_name: str = None) -> bool:
        """
        외부 파일에서 템플릿을 가져옵니다

        Args:
            import_path: 가져올 파일 경로
            template_name: 템플릿 이름 (None인 경우 파일명 사용)

        Returns:
            가져오기 성공 여부
        """
        try:
            if not import_path.exists():
                logger.error(f"가져올 파일이 존재하지 않습니다: {import_path}")
                return False
            
            content = import_path.read_text(encoding='utf-8')
            name = template_name or import_path.stem
            
            self.set_template(name, content)
            
            logger.info(f"템플릿 가져오기 완료: {name}")
            return True

        except Exception as e:
            logger.error(f"템플릿 가져오기 실패: {import_path}, 오류: {e}")
            return False
