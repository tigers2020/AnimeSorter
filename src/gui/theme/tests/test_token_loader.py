"""
TokenLoader 클래스 테스트 모듈

이 모듈은 TokenLoader의 모든 기능에 대한 단위 테스트를 포함합니다.
"""

import logging

logger = logging.getLogger(__name__)
import re
import unittest
from unittest.mock import Mock, patch

from src.engine.token_loader import TokenLoader


class TestTokenLoader(unittest.TestCase):
    """TokenLoader 클래스 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.token_loader = TokenLoader(enable_validation=False)
        self.test_tokens = {
            "variables": {
                "primary_color": "#007bff",
                "base_spacing": 8,
                "font_family": "Arial, sans-serif",
            },
            "colors": {
                "primary": {
                    "value": "$primary_color",
                    "description": "주요 색상",
                    "category": "semantic",
                },
                "secondary": {
                    "value": "lighten($primary_color, 0.2)",
                    "description": "보조 색상",
                    "category": "semantic",
                },
            },
            "spacing": {
                "xs": {
                    "value": "$base_spacing * 0.5",
                    "description": "매우 작은 간격",
                    "category": "spacing",
                },
                "sm": {"value": "$base_spacing", "description": "작은 간격", "category": "spacing"},
            },
            "fonts": {
                "primary": {"value": "$font_family", "description": "주요 폰트", "category": "font"}
            },
        }

    def tearDown(self):
        """테스트 정리"""
        self.token_loader.clear_tokens()

    def test_initialization(self):
        """초기화 테스트"""
        self.assertIsInstance(self.token_loader.tokens, dict)
        self.assertIsInstance(self.token_loader.variables, dict)
        self.assertIsInstance(self.token_loader.functions, dict)
        self.assertFalse(self.token_loader.enable_validation)
        expected_functions = ["lighten", "darken", "mix", "contrast", "scale", "math"]
        for func_name in expected_functions:
            self.assertIn(func_name, self.token_loader.functions)

    def test_load_tokens(self):
        """토큰 로드 테스트"""
        self.token_loader.load_tokens(self.test_tokens)
        self.assertIn("primary_color", self.token_loader.variables)
        self.assertEqual(self.token_loader.variables["primary_color"], "#007bff")
        self.assertIn("colors.primary.value", self.token_loader.tokens)
        self.assertIn("spacing.xs.value", self.token_loader.tokens)

    def test_variable_resolution(self):
        """변수 해석 테스트"""
        self.token_loader.load_tokens(self.test_tokens)
        primary_color = self.token_loader.get_token("colors.primary.value")
        self.assertEqual(primary_color, "#007bff")
        spacing_xs = self.token_loader.get_token("spacing.xs.value")
        self.assertEqual(spacing_xs, "8 * 0.5")

    def test_function_execution(self):
        """함수 실행 테스트"""
        self.token_loader.load_tokens(self.test_tokens)
        secondary_color = self.token_loader.get_token("colors.secondary.value")
        self.assertNotEqual(secondary_color, "lighten($primary_color, 0.2)")

    def test_get_token(self):
        """토큰 가져오기 테스트"""
        self.token_loader.load_tokens(self.test_tokens)
        primary_color = self.token_loader.get_token("colors.primary")
        self.assertIsInstance(primary_color, dict)
        self.assertEqual(primary_color["value"], "#007bff")
        primary_value = self.token_loader.get_token("colors.primary.value")
        self.assertEqual(primary_value, "#007bff")
        non_existent = self.token_loader.get_token("non.existent", "default")
        self.assertEqual(non_existent, "default")

    def test_set_token(self):
        """토큰 설정 테스트"""
        self.token_loader.set_token("test.token", "test_value")
        self.assertTrue(self.token_loader.has_token("test.token"))
        self.assertEqual(self.token_loader.get_token("test.token"), "test_value")

    def test_has_token(self):
        """토큰 존재 확인 테스트"""
        self.token_loader.set_token("test.token", "test_value")
        self.assertTrue(self.token_loader.has_token("test.token"))
        self.assertFalse(self.token_loader.has_token("non.existent"))
        self.token_loader.set_token("nested", {"level1": {"level2": "value"}})
        self.assertTrue(self.token_loader.has_token("nested.level1.level2"))

    def test_clear_tokens(self):
        """토큰 초기화 테스트"""
        self.token_loader.load_tokens(self.test_tokens)
        self.assertGreater(len(self.token_loader.tokens), 0)
        self.token_loader.clear_tokens()
        self.assertEqual(len(self.token_loader.tokens), 0)
        self.assertEqual(len(self.token_loader.variables), 0)

    def test_get_all_tokens(self):
        """모든 토큰 가져오기 테스트"""
        self.token_loader.load_tokens(self.test_tokens)
        all_tokens = self.token_loader.get_all_tokens()
        self.assertIsNot(all_tokens, self.token_loader.tokens)
        self.assertEqual(all_tokens, self.token_loader.tokens)

    def test_get_token_paths(self):
        """토큰 경로 가져오기 테스트"""
        self.token_loader.load_tokens(self.test_tokens)
        paths = self.token_loader.get_token_paths()
        self.assertIn("colors.primary.value", paths)
        self.assertIn("spacing.xs.value", paths)
        self.assertIsInstance(paths, list)

    def test_search_tokens(self):
        """토큰 검색 테스트"""
        self.token_loader.load_tokens(self.test_tokens)
        color_results = self.token_loader.search_tokens("color")
        self.assertGreater(len(color_results), 0)
        spacing_results = self.token_loader.search_tokens("spacing")
        self.assertGreater(len(spacing_results), 0)
        empty_results = self.token_loader.search_tokens("nonexistent")
        self.assertEqual(len(empty_results), 0)

    def test_color_functions(self):
        """색상 함수 테스트"""
        lightened = self.token_loader._lighten_color("#000000", 0.5)
        self.assertNotEqual(lightened, "#000000")
        darkened = self.token_loader._darken_color("#ffffff", 0.5)
        self.assertNotEqual(darkened, "#ffffff")
        mixed = self.token_loader._mix_colors("#ff0000", "#0000ff", 0.5)
        self.assertNotEqual(mixed, "#ff0000")
        self.assertNotEqual(mixed, "#0000ff")
        contrast = self.token_loader._get_contrast_color("#000000")
        self.assertEqual(contrast, "#FFFFFF")
        contrast2 = self.token_loader._get_contrast_color("#ffffff")
        self.assertEqual(contrast2, "#000000")

    def test_math_functions(self):
        """수학 함수 테스트"""
        result = self.token_loader._math_operation("add", 1, 2, 3)
        self.assertEqual(result, 6)
        result = self.token_loader._math_operation("subtract", 10, 3, 2)
        self.assertEqual(result, 5)
        result = self.token_loader._math_operation("multiply", 2, 3, 4)
        self.assertEqual(result, 24)
        result = self.token_loader._math_operation("divide", 20, 4, 2)
        self.assertEqual(result, 2.5)

    def test_scale_function(self):
        """스케일 함수 테스트"""
        result = self.token_loader._scale_value(10, 2)
        self.assertEqual(result, 20)
        self.assertIsInstance(result, int)
        result = self.token_loader._scale_value(10.5, 2)
        self.assertEqual(result, 21.0)
        self.assertIsInstance(result, float)

    def test_additional_color_functions(self):
        """추가 색상 함수 테스트"""
        rgb = self.token_loader._rgb_color(255, 0, 0)
        self.assertEqual(rgb, "rgb(255, 0, 0)")
        rgba = self.token_loader._rgba_color(255, 0, 0, 0.5)
        self.assertEqual(rgba, "rgba(255, 0, 0, 0.5)")
        hsl = self.token_loader._hsl_color(0, 100, 50)
        self.assertEqual(hsl, "hsl(0, 100%, 50%)")
        hsla = self.token_loader._hsla_color(0, 100, 50, 0.5)
        self.assertEqual(hsla, "hsla(0, 100%, 50%, 0.5)")
        inverted = self.token_loader._invert_color("#ffffff")
        self.assertEqual(inverted, "#000000")

    def test_error_handling(self):
        """에러 처리 테스트"""
        result = self.token_loader._lighten_color("invalid_color", 0.5)
        self.assertEqual(result, "invalid_color")
        result = self.token_loader._math_operation("invalid_op", 1, 2)
        self.assertEqual(result, 1)
        result = self.token_loader._math_operation("divide", 10, 0)
        self.assertEqual(result, 10)

    def test_infinite_loop_prevention(self):
        """무한 루프 방지 테스트"""
        circular_tokens = {"variables": {"var1": "$var2", "var2": "$var1"}, "test": "$var1"}
        self.token_loader.load_tokens(circular_tokens)
        self.assertIsInstance(self.token_loader.tokens, dict)

    def test_complex_token_resolution(self):
        """복잡한 토큰 해석 테스트"""
        complex_tokens = {
            "variables": {"base": 16, "ratio": 1.5},
            "fonts": {
                "size": {
                    "base": "$base",
                    "large": "math(multiply, $base, $ratio)",
                    "xlarge": "math(multiply, $base, 2.25)",
                }
            },
        }
        self.token_loader.load_tokens(complex_tokens)
        base_size = self.token_loader.get_token("fonts.size.base")
        large_size = self.token_loader.get_token("fonts.size.large")
        xlarge_size = self.token_loader.get_token("fonts.size.xlarge")
        self.assertEqual(base_size, 16)
        self.assertEqual(large_size, 24.0)
        self.assertEqual(xlarge_size, 36.0)

    def test_token_validation_disabled(self):
        """토큰 검증 비활성화 테스트"""
        loader = TokenLoader(enable_validation=False)
        invalid_tokens = {
            "colors": {"invalid": {"value": "not_a_color", "description": "잘못된 색상"}}
        }
        loader.load_tokens(invalid_tokens)
        self.assertIn("colors.invalid.value", loader.tokens)

    @patch("src.gui.theme.engine.token_loader.ColorToken")
    def test_token_validation_enabled(self, mock_color_token):
        """토큰 검증 활성화 테스트"""
        mock_color_token.return_value = Mock()
        with patch("src.gui.theme.engine.token_loader.PYDANTIC_AVAILABLE", True):
            loader = TokenLoader(enable_validation=True)
            valid_tokens = {
                "colors": {
                    "primary": {
                        "value": "#007bff",
                        "description": "주요 색상",
                        "category": "semantic",
                    }
                }
            }
            loader.load_tokens(valid_tokens)
            self.assertIn("colors.primary.value", loader.tokens)

    def test_performance_optimizations(self):
        """성능 최적화 테스트"""
        self.assertIsInstance(self.token_loader.var_pattern, type(re.compile("")))
        self.assertIsInstance(self.token_loader.simple_var_pattern, type(re.compile("")))
        self.assertIsInstance(self.token_loader.function_pattern, type(re.compile("")))
        self.token_loader.set_token("test.cache", "cached_value")
        result1 = self.token_loader.get_token("test.cache")
        self.assertEqual(result1, "cached_value")
        result2 = self.token_loader.get_token("test.cache")
        self.assertEqual(result2, "cached_value")

    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        self.token_loader.load_tokens({})
        self.assertEqual(len(self.token_loader.tokens), 0)
        self.token_loader.set_token("null.token", None)
        self.assertIsNone(self.token_loader.get_token("null.token"))
        self.token_loader.set_token("empty.token", "")
        self.assertEqual(self.token_loader.get_token("empty.token"), "")
        self.token_loader.set_token("special-char.token", "value")
        self.assertEqual(self.token_loader.get_token("special-char.token"), "value")


if __name__ == "__main__":
    unittest.main()
