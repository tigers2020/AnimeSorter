"""
테마 토큰 로더 모듈

이 모듈은 테마 정의에서 토큰을 로딩하고 파싱하여
테마 시스템에서 사용할 수 있는 형태로 변환합니다.
"""

import logging
import re
from functools import lru_cache
from typing import Any, Union

try:
    from .models import (BorderToken, ColorToken, FontToken, ShadowToken,
                         SpacingToken, TransitionToken)

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    ColorToken = FontToken = SpacingToken = BorderToken = ShadowToken = TransitionToken = None

logger = logging.getLogger(__name__)


class TokenLoader:
    """테마 토큰을 로딩하고 파싱하는 클래스"""

    def __init__(self, enable_validation: bool = True):
        """
        TokenLoader 초기화

        Args:
            enable_validation: Pydantic 모델 검증 활성화 여부
        """
        self.tokens: dict[str, Any] = {}
        self.token_cache: dict[str, Any] = {}
        self.variables: dict[str, str] = {}
        self.functions: dict[str, callable] = {}
        self.enable_validation = enable_validation and PYDANTIC_AVAILABLE

        # 기본 함수들 등록
        self._register_default_functions()

        # 성능 최적화를 위한 정규식 패턴 컴파일
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """정규식 패턴들을 컴파일합니다"""
        self.var_pattern = re.compile(r"\$\{([^}]+)\}")
        self.simple_var_pattern = re.compile(r"\$([a-zA-Z_][a-zA-Z0-9_]*)")
        self.function_pattern = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)")

    def _register_default_functions(self) -> None:
        """기본 토큰 함수들을 등록합니다"""
        self.functions.update(
            {
                "lighten": self._lighten_color,
                "darken": self._darken_color,
                "alpha": self._add_alpha,
                "mix": self._mix_colors,
                "contrast": self._get_contrast_color,
                "scale": self._scale_value,
                "math": self._math_operation,
                "rgb": self._rgb_color,
                "hsl": self._hsl_color,
                "hsla": self._hsla_color,
                "rgba": self._rgba_color,
                "invert": self._invert_color,
                "saturate": self._saturate_color,
                "desaturate": self._desaturate_color,
            }
        )

    def load_tokens(self, theme_data: dict[str, Any]) -> None:
        """
        테마 데이터에서 토큰을 로드합니다

        Args:
            theme_data: 테마 데이터 딕셔너리
        """
        try:
            # 기존 토큰 초기화
            self.tokens.clear()
            self.token_cache.clear()
            self.variables.clear()

            # 토큰 데이터 추출
            self._extract_tokens(theme_data)

            # 변수 해석
            self._resolve_variables()

            # 함수 실행
            self._execute_functions()

            # 모델 검증 (활성화된 경우)
            if self.enable_validation:
                self._validate_tokens()

            logger.info(f"토큰 로드 완료: {len(self.tokens)}개")

        except Exception as e:
            logger.error(f"토큰 로드 중 오류 발생: {e}")
            raise

    def _extract_tokens(self, data: Any, prefix: str = "") -> None:
        """
        데이터에서 토큰을 재귀적으로 추출합니다

        Args:
            data: 추출할 데이터
            prefix: 현재 경로 접두사
        """
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{prefix}.{key}" if prefix else key
                self._extract_tokens(value, current_path)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                current_path = f"{prefix}[{i}]"
                self._extract_tokens(value, current_path)
        else:
            # 리터럴 값인 경우 토큰으로 저장
            if prefix:
                self.tokens[prefix] = data

    def _resolve_variables(self) -> None:
        """토큰에서 변수를 해석합니다"""
        try:
            # 변수 정의 추출
            self._extract_variables()

            # 변수 치환 (최대 10회 반복으로 무한 루프 방지)
            max_iterations = 10
            for iteration in range(max_iterations):
                changed = False
                for token_name, token_value in self.tokens.items():
                    if isinstance(token_value, str):
                        resolved_value = self._resolve_string_variables(token_value)
                        if resolved_value != token_value:
                            self.tokens[token_name] = resolved_value
                            changed = True

                if not changed:
                    break

                if iteration == max_iterations - 1:
                    logger.warning("변수 해석 최대 반복 횟수 도달")

        except Exception as e:
            logger.error(f"변수 해석 중 오류 발생: {e}")

    def _extract_variables(self) -> None:
        """토큰에서 변수 정의를 추출합니다"""
        try:
            # 평면화된 변수 섹션 추출 (variables.variable_name 형태)
            variables_to_remove = []
            for token_name, token_value in self.tokens.items():
                if token_name.startswith("variables."):
                    var_name = token_name.replace("variables.", "")
                    self.variables[var_name] = token_value
                    variables_to_remove.append(token_name)

            # 추출된 변수 토큰들 제거
            for token_name in variables_to_remove:
                del self.tokens[token_name]

            # 중첩된 변수 구조 처리 (variables: {base: 16} 형태)
            if "variables" in self.tokens and isinstance(self.tokens["variables"], dict):
                for var_name, var_value in self.tokens["variables"].items():
                    self.variables[var_name] = var_value
                del self.tokens["variables"]

            # 개별 변수들도 추출 ($ 시작하는 토큰)
            for token_name, token_value in list(self.tokens.items()):
                if token_name.startswith("$"):
                    var_name = token_name[1:]  # $ 제거
                    self.variables[var_name] = token_value
                    del self.tokens[token_name]

            # 토큰 값들을 변수로도 등록 (예: fonts.size.base -> base)
            for token_name, token_value in self.tokens.items():
                if "." in token_name:
                    # 마지막 부분을 변수명으로 사용 (예: fonts.size.base -> base)
                    var_name = token_name.split(".")[-1]
                    if var_name not in self.variables:  # 기존 변수와 충돌하지 않도록
                        self.variables[var_name] = token_value

            logger.debug(f"추출된 변수: {self.variables}")

        except Exception as e:
            logger.error(f"변수 추출 중 오류 발생: {e}")

    def _resolve_string_variables(self, text: str) -> str:
        """
        문자열에서 변수 참조를 해석합니다

        Args:
            text: 해석할 문자열

        Returns:
            변수가 해석된 문자열
        """
        try:
            # ${variable} 형태의 변수 참조 처리
            def replace_var(match):
                var_name = match.group(1)
                return str(self.variables.get(var_name, match.group(0)))

            resolved_text = self.var_pattern.sub(replace_var, text)

            # $variable 형태의 변수 참조 처리
            def replace_simple_var(match):
                var_name = match.group(1)
                var_value = self.variables.get(var_name, match.group(0))
                # 원본 타입 유지 (숫자인 경우)
                if isinstance(var_value, (int, float)):
                    return str(var_value)  # 문자열로 변환하여 반환
                return str(var_value)

            resolved_text = self.simple_var_pattern.sub(replace_simple_var, resolved_text)

            return resolved_text

        except Exception as e:
            logger.error(f"문자열 변수 해석 중 오류 발생: {e}")
            return text

    def _execute_functions(self) -> None:
        """토큰에서 함수 호출을 실행합니다"""
        try:
            # 최대 10회 반복으로 무한 루프 방지 (중첩된 함수 호출을 위해 증가)
            max_iterations = 10
            for iteration in range(max_iterations):
                changed = False
                for token_name, token_value in self.tokens.items():
                    if isinstance(token_value, str):
                        resolved_value = self._resolve_function_calls(token_value)
                        if resolved_value != token_value:
                            self.tokens[token_name] = resolved_value
                            changed = True

                if not changed:
                    break

                if iteration == max_iterations - 1:
                    logger.warning("함수 실행 최대 반복 횟수 도달")

        except Exception as e:
            logger.error(f"함수 실행 중 오류 발생: {e}")

    def _resolve_function_calls(self, text: str) -> str:
        """
        문자열에서 함수 호출을 해석합니다

        Args:
            text: 해석할 문자열

        Returns:
            함수가 실행된 문자열
        """
        try:
            # 중첩된 함수 호출을 처리하기 위해 재귀적으로 해석
            def replace_function(match):
                func_name = match.group(1)
                args_str = match.group(2)

                if func_name in self.functions:
                    try:
                        # 인수 파싱 (재귀적으로 함수 호출 해석)
                        args = self._parse_function_args(args_str)

                        # 함수 실행
                        result = self.functions[func_name](*args)
                        return str(result)
                    except Exception as e:
                        logger.error(f"함수 {func_name} 실행 중 오류: {e}")
                        return match.group(0)
                else:
                    return match.group(0)

            # 중첩된 함수 호출을 처리하기 위해 여러 번 반복
            max_iterations = 5
            for iteration in range(max_iterations):
                old_text = text
                text = self.function_pattern.sub(replace_function, text)
                logger.debug(f"함수 해석 반복 {iteration + 1}: {old_text} -> {text}")
                if text == old_text:
                    break

            return text

        except Exception as e:
            logger.error(f"함수 호출 해석 중 오류 발생: {e}")
            return text

    def _parse_function_args(self, args_str: str) -> list[Any]:
        """
        함수 인수 문자열을 파싱합니다

        Args:
            args_str: 인수 문자열

        Returns:
            파싱된 인수 리스트
        """
        try:
            if not args_str.strip():
                return []

            args = []
            current_arg = ""
            in_quotes = False
            paren_count = 0

            for char in args_str:
                if char == '"' and (not current_arg or current_arg[-1] != "\\"):
                    in_quotes = not in_quotes
                    current_arg += char
                elif char == "(" and not in_quotes:
                    paren_count += 1
                    current_arg += char
                elif char == ")" and not in_quotes:
                    paren_count -= 1
                    current_arg += char
                elif char == "," and not in_quotes and paren_count == 0:
                    # 현재 인수를 파싱하기 전에 함수 호출이 있다면 먼저 해석
                    parsed_arg = self._parse_arg_value(current_arg.strip())
                    if isinstance(parsed_arg, str) and "(" in parsed_arg:
                        # 함수 호출이 포함된 인수는 재귀적으로 해석
                        parsed_arg = self._resolve_function_calls(parsed_arg)
                    args.append(parsed_arg)
                    current_arg = ""
                else:
                    current_arg += char

            if current_arg.strip():
                # 마지막 인수도 동일하게 처리
                parsed_arg = self._parse_arg_value(current_arg.strip())
                if isinstance(parsed_arg, str) and "(" in parsed_arg:
                    parsed_arg = self._resolve_function_calls(parsed_arg)
                args.append(parsed_arg)

            # 디버깅: 파싱된 인수 확인
            logger.debug(f"함수 인수 파싱 결과: '{args_str}' -> {args}")
            print(f"DEBUG: 함수 인수 파싱 결과: '{args_str}' -> {args}")  # 임시 디버깅

            # 괄호가 제대로 닫혔는지 확인
            if paren_count != 0:
                print(f"WARNING: 괄호가 제대로 닫히지 않음. paren_count: {paren_count}")
                print(f"WARNING: args_str: '{args_str}'")
                print(f"WARNING: current_arg: '{current_arg}'")

                # 괄호가 닫히지 않은 경우, 누락된 괄호를 추가
                if paren_count > 0:
                    current_arg += ")" * paren_count
                    print(f"WARNING: 누락된 괄호 추가: '{current_arg}'")

                    # 마지막 인수를 다시 파싱
                    if current_arg.strip():
                        parsed_arg = self._parse_arg_value(current_arg.strip())
                        if isinstance(parsed_arg, str) and "(" in parsed_arg:
                            parsed_arg = self._resolve_function_calls(parsed_arg)
                        args.append(parsed_arg)

                        # 디버깅: 수정된 인수 확인
                        print(f"DEBUG: 수정된 인수 추가: '{current_arg.strip()}' -> {parsed_arg}")
                        print(f"DEBUG: 최종 인수 리스트: {args}")

            return args

        except Exception as e:
            logger.error(f"함수 인수 파싱 중 오류 발생: {e}")
            return []

    def _parse_arg_value(self, arg_str: str) -> Any:
        """
        개별 인수 값을 파싱합니다

        Args:
            arg_str: 인수 문자열

        Returns:
            파싱된 값
        """
        try:
            arg_str = arg_str.strip()

            # 문자열 (따옴표로 둘러싸인 경우)
            if (arg_str.startswith('"') and arg_str.endswith('"')) or (
                arg_str.startswith("'") and arg_str.endswith("'")
            ):
                return arg_str[1:-1]

            # 숫자
            if arg_str.replace(".", "").replace("-", "").isdigit():
                if "." in arg_str:
                    return float(arg_str)
                else:
                    return int(arg_str)

            # 불린
            if arg_str.lower() == "true":
                return True
            elif arg_str.lower() == "false":
                return False

            # 변수 참조
            if arg_str.startswith("$"):
                var_name = arg_str[1:]
                return self.variables.get(var_name, arg_str)

            # 토큰 참조
            if arg_str in self.tokens:
                return self.tokens[arg_str]

            # 기본값은 문자열
            return arg_str

        except Exception as e:
            logger.error(f"인수 값 파싱 중 오류 발생: {e}")
            return arg_str

    def _validate_tokens(self) -> None:
        """토큰을 Pydantic 모델로 검증합니다"""
        if not self.enable_validation:
            return

        try:
            validation_errors = []

            for token_name, token_value in self.tokens.items():
                try:
                    # 토큰 타입에 따른 검증
                    if token_name.startswith("colors."):
                        self._validate_color_token(token_name, token_value)
                    elif token_name.startswith("fonts."):
                        self._validate_font_token(token_name, token_value)
                    elif token_name.startswith("spacing."):
                        self._validate_spacing_token(token_name, token_value)
                    elif token_name.startswith("borders."):
                        self._validate_border_token(token_name, token_value)
                    elif token_name.startswith("shadows."):
                        self._validate_shadow_token(token_name, token_value)
                    elif token_name.startswith("transitions."):
                        self._validate_transition_token(token_name, token_value)

                except Exception as e:
                    validation_errors.append(f"{token_name}: {e}")

            if validation_errors:
                logger.warning(f"토큰 검증 경고: {len(validation_errors)}개")
                for error in validation_errors[:5]:  # 처음 5개만 로그
                    logger.warning(f"  - {error}")

        except Exception as e:
            logger.error(f"토큰 검증 중 오류 발생: {e}")

    def _validate_color_token(self, token_name: str, token_value: Any) -> None:
        """색상 토큰을 검증합니다"""
        if isinstance(token_value, dict) and "value" in token_value:
            ColorToken(**token_value)

    def _validate_font_token(self, token_name: str, token_value: Any) -> None:
        """폰트 토큰을 검증합니다"""
        if isinstance(token_value, dict) and "value" in token_value:
            FontToken(**token_value)

    def _validate_spacing_token(self, token_name: str, token_value: Any) -> None:
        """간격 토큰을 검증합니다"""
        if isinstance(token_value, dict) and "value" in token_value:
            SpacingToken(**token_value)

    def _validate_border_token(self, token_name: str, token_value: Any) -> None:
        """테두리 토큰을 검증합니다"""
        if isinstance(token_value, dict) and "value" in token_value:
            BorderToken(**token_value)

    def _validate_shadow_token(self, token_name: str, token_value: Any) -> None:
        """그림자 토큰을 검증합니다"""
        if isinstance(token_value, dict) and "value" in token_value:
            ShadowToken(**token_value)

    def _validate_transition_token(self, token_name: str, token_value: Any) -> None:
        """전환 토큰을 검증합니다"""
        if isinstance(token_value, dict) and "value" in token_value:
            TransitionToken(**token_value)

    @lru_cache(maxsize=128)
    def get_token(self, token_name: str, default: Any = None) -> Any:
        """
        토큰 값을 가져옵니다 (캐시 적용)

        Args:
            token_name: 토큰 이름
            default: 기본값

        Returns:
            토큰 값 또는 기본값
        """
        try:
            # 직접 토큰 접근
            if token_name in self.tokens:
                value = self.tokens[token_name]
                # 숫자 문자열을 숫자로 변환 시도
                if isinstance(value, str) and value.replace(".", "").replace("-", "").isdigit():
                    if "." in value:
                        return float(value)
                    else:
                        return int(value)
                return value

            # 평면화된 토큰에서 중첩 구조 재구성
            if "." in token_name:
                # 해당 토큰으로 시작하는 모든 키 찾기
                matching_tokens = {}
                prefix = token_name + "."

                for key, value in self.tokens.items():
                    if key.startswith(prefix):
                        sub_key = key[len(prefix) :]
                        matching_tokens[sub_key] = value

                # 매칭되는 토큰이 있으면 딕셔너리로 반환
                if matching_tokens:
                    return matching_tokens

                # 기존 중첩 구조 접근 로직
                keys = token_name.split(".")
                current_value = self.tokens

                for key in keys:
                    if isinstance(current_value, dict) and key in current_value:
                        current_value = current_value[key]
                    else:
                        # 토큰이 평면화되어 있을 수도 있으므로 확인
                        flattened_key = ".".join(keys[: keys.index(key) + 1])
                        if flattened_key in self.tokens:
                            current_value = self.tokens[flattened_key]
                            # 남은 키들을 계속 탐색
                            remaining_keys = keys[keys.index(key) + 1 :]
                            for remaining_key in remaining_keys:
                                if (
                                    isinstance(current_value, dict)
                                    and remaining_key in current_value
                                ):
                                    current_value = current_value[remaining_key]
                                else:
                                    return default
                            return current_value
                        else:
                            return default

                return current_value

            return default

        except Exception as e:
            logger.error(f"토큰 가져오기 실패: {token_name}, 오류: {e}")
            return default

    def set_token(self, token_name: str, value: Any) -> None:
        """
        토큰 값을 설정합니다

        Args:
            token_name: 토큰 이름
            value: 설정할 값
        """
        try:
            self.tokens[token_name] = value
            # 캐시 무효화
            self.get_token.cache_clear()
            logger.debug(f"토큰 설정: {token_name} = {value}")
        except Exception as e:
            logger.error(f"토큰 설정 실패: {token_name}, 오류: {e}")

    def has_token(self, token_name: str) -> bool:
        """
        토큰이 존재하는지 확인합니다

        Args:
            token_name: 확인할 토큰 이름

        Returns:
            토큰 존재 여부
        """
        try:
            if token_name in self.tokens:
                return True

            # 점 표기법으로 중첩된 토큰 확인
            if "." in token_name:
                keys = token_name.split(".")
                value = self.tokens

                for key in keys:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return False

                return True

            return False

        except Exception as e:
            logger.error(f"토큰 존재 확인 실패: {token_name}, 오류: {e}")
            return False

    def get_all_tokens(self) -> dict[str, Any]:
        """모든 토큰을 반환합니다"""
        return self.tokens.copy()

    def clear_tokens(self) -> None:
        """모든 토큰을 초기화합니다"""
        self.tokens.clear()
        self.token_cache.clear()
        self.variables.clear()
        self.get_token.cache_clear()

    def get_token_paths(self) -> list[str]:
        """모든 토큰 경로를 반환합니다"""
        return list(self.tokens.keys())

    def search_tokens(self, query: str) -> dict[str, Any]:
        """
        쿼리와 일치하는 토큰들을 검색합니다

        Args:
            query: 검색 쿼리

        Returns:
            일치하는 토큰들
        """
        try:
            results = {}
            query_lower = query.lower()

            for token_name, token_value in self.tokens.items():
                if query_lower in token_name.lower():
                    results[token_name] = token_value
                elif isinstance(token_value, dict) and "description" in token_value:
                    if query_lower in token_value["description"].lower():
                        results[token_name] = token_value

            return results

        except Exception as e:
            logger.error(f"토큰 검색 중 오류 발생: {e}")
            return {}

    # 기본 함수들 구현
    def _lighten_color(self, color: str, amount: float) -> str:
        """색상을 밝게 만듭니다"""
        try:
            # 간단한 색상 밝기 조정 (실제로는 더 정교한 구현 필요)
            if color.startswith("#"):
                # HEX 색상 처리
                return self._lighten_hex_color(color, amount)
            return color
        except Exception as e:
            logger.error(f"색상 밝기 조정 실패: {e}")
            return color

    def _darken_color(self, color: str, amount: float) -> str:
        """색상을 어둡게 만듭니다"""
        try:
            # 간단한 색상 어둡기 조정
            if color.startswith("#"):
                # HEX 색상 처리
                return self._darken_hex_color(color, amount)
            return color
        except Exception as e:
            logger.error(f"색상 어둡기 조정 실패: {e}")
            return color

    def _add_alpha(self, color: str, alpha: float) -> str:
        """색상에 알파 채널을 추가합니다"""
        try:
            if color.startswith("#"):
                # HEX를 RGBA로 변환
                return self._hex_to_rgba(color, alpha)
            return color
        except Exception as e:
            logger.error(f"알파 채널 추가 실패: {e}")
            return color

    def _mix_colors(self, color1: str, color2: str, ratio: float) -> str:
        """두 색상을 혼합합니다"""
        try:
            if color1.startswith("#") and color2.startswith("#"):
                return self._mix_hex_colors(color1, color2, ratio)
            return color1
        except Exception as e:
            logger.error(f"색상 혼합 실패: {e}")
            return color1

    def _get_contrast_color(self, color: str) -> str:
        """대비되는 색상을 반환합니다"""
        try:
            if color.startswith("#"):
                # 밝기 계산 후 대비 색상 반환
                brightness = self._calculate_brightness(color)
                return "#000000" if brightness > 0.5 else "#FFFFFF"
            return color
        except Exception as e:
            logger.error(f"대비 색상 계산 실패: {e}")
            return color

    def _scale_value(self, value: Union[int, float], factor: float) -> Union[int, float]:
        """값을 스케일링합니다"""
        try:
            result = value * factor
            return int(result) if isinstance(value, int) else result
        except Exception as e:
            logger.error(f"값 스케일링 실패: {e}")
            return value

    def _math_operation(self, operation: str, *args) -> Union[int, float]:
        """수학 연산을 수행합니다"""
        try:
            # 디버깅: 인수 타입과 값 확인
            logger.debug(
                f"수학 연산 {operation} 호출: args={args}, types={[type(arg) for arg in args]}"
            )

            # 모든 인수를 숫자로 변환
            numeric_args = []
            for arg in args:
                if isinstance(arg, (int, float)):
                    numeric_args.append(arg)
                elif isinstance(arg, str):
                    # 문자열을 숫자로 변환 시도
                    if arg.replace(".", "").replace("-", "").isdigit():
                        if "." in arg:
                            numeric_args.append(float(arg))
                        else:
                            numeric_args.append(int(arg))
                    else:
                        logger.error(f"숫자로 변환할 수 없는 인수: {arg}")
                        return 0
                else:
                    logger.error(f"지원하지 않는 인수 타입: {type(arg)} = {arg}")
                    return 0

            if operation == "add":
                return sum(numeric_args)
            elif operation == "subtract":
                return numeric_args[0] - sum(numeric_args[1:])
            elif operation == "multiply":
                result = 1
                for arg in numeric_args:
                    result *= arg
                return result
            elif operation == "divide":
                if len(numeric_args) < 2:
                    return numeric_args[0]
                result = numeric_args[0]
                for arg in numeric_args[1:]:
                    if arg != 0:
                        result /= arg
                return result
            else:
                logger.warning(f"알 수 없는 수학 연산: {operation}")
                return numeric_args[0] if numeric_args else 0
        except Exception as e:
            logger.error(f"수학 연산 실패: {e}")
            return 0

    # 추가 색상 함수들
    def _rgb_color(self, r: int, g: int, b: int) -> str:
        """RGB 색상을 생성합니다"""
        try:
            r = max(0, min(255, int(r)))
            g = max(0, min(255, int(g)))
            b = max(0, min(255, int(b)))
            return f"rgb({r}, {g}, {b})"
        except Exception as e:
            logger.error(f"RGB 색상 생성 실패: {e}")
            return "#000000"

    def _rgba_color(self, r: int, g: int, b: int, a: float) -> str:
        """RGBA 색상을 생성합니다"""
        try:
            r = max(0, min(255, int(r)))
            g = max(0, min(255, int(g)))
            b = max(0, min(255, int(b)))
            a = max(0.0, min(1.0, float(a)))
            return f"rgba({r}, {g}, {b}, {a})"
        except Exception as e:
            logger.error(f"RGBA 색상 생성 실패: {e}")
            return "#000000"

    def _hsl_color(self, h: float, s: float, l: float) -> str:
        """HSL 색상을 생성합니다"""
        try:
            h = max(0, min(360, float(h)))
            s = max(0, min(100, float(s)))
            l = max(0, min(100, float(l)))
            # 정수 포맷팅으로 .0% 방지
            h_str = f"{int(h)}" if h == int(h) else f"{h}"
            s_str = f"{int(s)}" if s == int(s) else f"{s}"
            l_str = f"{int(l)}" if l == int(l) else f"{l}"
            return f"hsl({h_str}, {s_str}%, {l_str}%)"
        except Exception as e:
            logger.error(f"HSL 색상 생성 실패: {e}")
            return "#000000"

    def _hsla_color(self, h: float, s: float, l: float, a: float) -> str:
        """HSLA 색상을 생성합니다"""
        try:
            h = max(0, min(360, float(h)))
            s = max(0, min(100, float(s)))
            l = max(0, min(100, float(l)))
            a = max(0.0, min(1.0, float(a)))

            # 정수인 경우에만 정수로 포맷팅
            h_str = f"{int(h)}" if h == int(h) else f"{h}"
            s_str = f"{int(s)}" if s == int(s) else f"{s}"
            l_str = f"{int(l)}" if l == int(l) else f"{l}"

            return f"hsla({h_str}, {s_str}%, {l_str}%, {a})"
        except Exception as e:
            logger.error(f"HSLA 색상 생성 실패: {e}")
            return "#000000"

    def _invert_color(self, color: str) -> str:
        """색상을 반전시킵니다"""
        try:
            if color.startswith("#"):
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                return f"#{255-r:02x}{255-g:02x}{255-b:02x}"
            return color
        except Exception as e:
            logger.error(f"색상 반전 실패: {e}")
            return color

    def _saturate_color(self, color: str, amount: float) -> str:
        """색상의 채도를 높입니다"""
        try:
            # 간단한 구현 (실제로는 HSL 변환 필요)
            if color.startswith("#"):
                return self._adjust_color_saturation(color, amount)
            return color
        except Exception as e:
            logger.error(f"색상 채도 조정 실패: {e}")
            return color

    def _desaturate_color(self, color: str, amount: float) -> str:
        """색상의 채도를 낮춥니다"""
        try:
            return self._saturate_color(color, -amount)
        except Exception as e:
            logger.error(f"색상 채도 감소 실패: {e}")
            return color

    # 헬퍼 메서드들
    def _lighten_hex_color(self, color: str, amount: float) -> str:
        """HEX 색상을 밝게 만듭니다"""
        try:
            # 간단한 구현 (실제로는 더 정교한 색상 공간 변환 필요)
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            r = min(255, int(r + (255 - r) * amount))
            g = min(255, int(g + (255 - g) * amount))
            b = min(255, int(b + (255 - b) * amount))

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return color

    def _darken_hex_color(self, color: str, amount: float) -> str:
        """HEX 색상을 어둡게 만듭니다"""
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            r = max(0, int(r * (1 - amount)))
            g = max(0, int(g * (1 - amount)))
            b = max(0, int(b * (1 - amount)))

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return color

    def _hex_to_rgba(self, color: str, alpha: float) -> str:
        """HEX 색상을 RGBA로 변환합니다"""
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            a = int(alpha * 255)

            return f"rgba({r}, {g}, {b}, {alpha})"
        except Exception:
            return color

    def _mix_hex_colors(self, color1: str, color2: str, ratio: float) -> str:
        """두 HEX 색상을 혼합합니다"""
        try:
            r1 = int(color1[1:3], 16)
            g1 = int(color1[3:5], 16)
            b1 = int(color1[5:7], 16)

            r2 = int(color2[1:3], 16)
            g2 = int(color2[3:5], 16)
            b2 = int(color2[5:7], 16)

            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return color1

    def _calculate_brightness(self, color: str) -> float:
        """HEX 색상의 밝기를 계산합니다"""
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            # 표준 밝기 공식
            return (0.299 * r + 0.587 * g + 0.114 * b) / 255
        except Exception:
            return 0.5

    def _adjust_color_saturation(self, color: str, amount: float) -> str:
        """색상의 채도를 조정합니다"""
        try:
            # 간단한 구현 (실제로는 HSL 변환 필요)
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            # 채도 조정 (간단한 방법)
            factor = 1 + amount
            r = max(0, min(255, int(r * factor)))
            g = max(0, min(255, int(g * factor)))
            b = max(0, min(255, int(b * factor)))

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return color
