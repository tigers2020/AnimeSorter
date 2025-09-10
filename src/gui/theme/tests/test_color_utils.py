"""
ColorUtils 클래스 테스트

이 모듈은 ColorUtils 클래스의 모든 기능에 대한 단위 테스트를 포함합니다.
"""

import logging

logger = logging.getLogger(__name__)
import unittest

from src.gui.theme.engine.color_utils import Color, ColorUtils


class TestColorUtils(unittest.TestCase):
    """ColorUtils 클래스 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.color_utils = ColorUtils()

    def test_color_initialization(self):
        """Color 클래스 초기화 테스트"""
        color = Color(255, 0, 0)
        self.assertEqual(color.r, 255)
        self.assertEqual(color.g, 0)
        self.assertEqual(color.b, 0)
        self.assertEqual(color.a, 1.0)
        color_with_alpha = Color(0, 255, 0, 0.5)
        self.assertEqual(color_with_alpha.a, 0.5)
        color_limited = Color(300, -10, 100, 1.5)
        self.assertEqual(color_limited.r, 255)
        self.assertEqual(color_limited.g, 0)
        self.assertEqual(color_limited.a, 1.0)

    def test_color_format_conversion(self):
        """색상 형식 변환 테스트"""
        color = Color(255, 0, 0, 0.8)
        hex_str = color.to_hex()
        self.assertEqual(hex_str, "#ff0000")
        rgb_str = color.to_rgb()
        self.assertEqual(rgb_str, "rgb(255, 0, 0)")
        rgba_str = color.to_rgba()
        self.assertEqual(rgba_str, "rgba(255, 0, 0, 0.800)")
        hsl_str = color.to_hsl()
        self.assertEqual(hsl_str, "hsl(0, 100%, 50%)")
        hsla_str = color.to_hsla()
        self.assertEqual(hsla_str, "hsla(0, 100%, 50%, 0.800)")

    def test_color_parsing(self):
        """색상 파싱 테스트"""
        hex_color = self.color_utils.parse_color("#ff0000")
        self.assertIsNotNone(hex_color)
        self.assertEqual(hex_color.r, 255)
        self.assertEqual(hex_color.g, 0)
        self.assertEqual(hex_color.b, 0)
        short_hex = self.color_utils.parse_color("#f0a")
        self.assertIsNotNone(short_hex)
        self.assertEqual(short_hex.r, 255)
        self.assertEqual(short_hex.g, 0)
        self.assertEqual(short_hex.b, 170)
        rgb_color = self.color_utils.parse_color("rgb(0, 255, 0)")
        self.assertIsNotNone(rgb_color)
        self.assertEqual(rgb_color.r, 0)
        self.assertEqual(rgb_color.g, 255)
        self.assertEqual(rgb_color.b, 0)
        rgba_color = self.color_utils.parse_color("rgba(0, 0, 255, 0.5)")
        self.assertIsNotNone(rgba_color)
        self.assertEqual(rgba_color.r, 0)
        self.assertEqual(rgba_color.g, 0)
        self.assertEqual(rgba_color.b, 255)
        self.assertEqual(rgba_color.a, 0.5)
        hsl_color = self.color_utils.parse_color("hsl(120, 100%, 50%)")
        self.assertIsNotNone(hsl_color)
        hsla_color = self.color_utils.parse_color("hsla(240, 100%, 50%, 0.8)")
        self.assertIsNotNone(hsla_color)
        named_color = self.color_utils.parse_color("red")
        self.assertIsNotNone(named_color)
        self.assertEqual(named_color.to_hex(), "#ff0000")
        invalid_color = self.color_utils.parse_color("invalid")
        self.assertIsNone(invalid_color)

    def test_color_manipulation(self):
        """색상 조작 테스트"""
        base_color = Color(100, 150, 200)
        lighter = self.color_utils.lighten(base_color, 0.2)
        self.assertIsNotNone(lighter)
        self.assertGreater(lighter.r, base_color.r)
        self.assertGreater(lighter.g, base_color.g)
        self.assertGreater(lighter.b, base_color.b)
        darker = self.color_utils.darken(base_color, 0.2)
        self.assertIsNotNone(darker)
        self.assertLess(darker.r, base_color.r)
        self.assertLess(darker.g, base_color.g)
        self.assertLess(darker.b, base_color.b)
        saturated = self.color_utils.saturate(base_color, 0.3)
        self.assertIsNotNone(saturated)
        desaturated = self.color_utils.desaturate(base_color, 0.3)
        self.assertIsNotNone(desaturated)
        hue_adjusted = self.color_utils.adjust_hue(base_color, 90)
        self.assertIsNotNone(hue_adjusted)
        complement = self.color_utils.complement(base_color)
        self.assertIsNotNone(complement)

    def test_color_mixing(self):
        """색상 혼합 테스트"""
        color1 = Color(255, 0, 0)
        color2 = Color(0, 0, 255)
        mixed = self.color_utils.mix(color1, color2, 0.5)
        self.assertIsNotNone(mixed)
        self.assertEqual(mixed.r, 127)
        self.assertEqual(mixed.g, 0)
        self.assertEqual(mixed.b, 127)
        color1_only = self.color_utils.mix(color1, color2, 0.0)
        self.assertIsNotNone(color1_only)
        self.assertEqual(color1_only.r, color1.r)
        color2_only = self.color_utils.mix(color1, color2, 1.0)
        self.assertIsNotNone(color2_only)
        self.assertEqual(color2_only.r, color2.r)

    def test_color_harmony(self):
        """색상 조화 테스트"""
        base_color = Color(255, 0, 0)
        triad_colors = self.color_utils.triad(base_color)
        self.assertEqual(len(triad_colors), 3)
        analogous_colors = self.color_utils.analogous(base_color, 5)
        self.assertEqual(len(analogous_colors), 5)
        monochromatic_colors = self.color_utils.monochromatic(base_color, 7)
        self.assertEqual(len(monochromatic_colors), 7)
        split_complementary = self.color_utils.split_complementary(base_color)
        self.assertEqual(len(split_complementary), 3)
        tetradic_colors = self.color_utils.tetradic(base_color)
        self.assertEqual(len(tetradic_colors), 4)

    def test_color_blending(self):
        """색상 블렌딩 테스트"""
        base_color = Color(100, 100, 100)
        blend_color = Color(200, 200, 200)
        normal_blend = self.color_utils.blend_normal(base_color, blend_color, 0.5)
        self.assertIsNotNone(normal_blend)
        darken_blend = self.color_utils.blend_darken(base_color, blend_color)
        self.assertIsNotNone(darken_blend)
        self.assertEqual(darken_blend.r, min(base_color.r, blend_color.r))
        lighten_blend = self.color_utils.blend_lighten(base_color, blend_color)
        self.assertIsNotNone(lighten_blend)
        self.assertEqual(lighten_blend.r, max(base_color.r, blend_color.r))
        multiply_blend = self.color_utils.blend_multiply(base_color, blend_color)
        self.assertIsNotNone(multiply_blend)
        screen_blend = self.color_utils.blend_screen(base_color, blend_color)
        self.assertIsNotNone(screen_blend)

    def test_contrast_calculation(self):
        """대비 계산 테스트"""
        high_contrast = self.color_utils.contrast_ratio(Color(255, 255, 255), Color(0, 0, 0))
        self.assertGreater(high_contrast, 20.0)
        low_contrast = self.color_utils.contrast_ratio(Color(100, 100, 100), Color(110, 110, 110))
        self.assertLess(low_contrast, 2.0)
        medium_contrast = self.color_utils.contrast_ratio(Color(255, 0, 0), Color(255, 255, 255))
        self.assertGreater(medium_contrast, 3.0)

    def test_wcag_compliance(self):
        """WCAG 준수 테스트"""
        is_aa_compliant = self.color_utils.is_wcag_compliant(
            Color(255, 255, 255), Color(0, 0, 0), "AA"
        )
        self.assertTrue(is_aa_compliant)
        is_aaa_compliant = self.color_utils.is_wcag_compliant(
            Color(255, 255, 255), Color(0, 0, 0), "AAA"
        )
        self.assertTrue(is_aaa_compliant)
        level = self.color_utils.get_wcag_level(8.0)
        self.assertIn("AAA", level)
        requirements = self.color_utils.get_wcag_requirements("large", True)
        self.assertIn("AA", requirements)
        self.assertEqual(requirements["AA"], 3.0)

    def test_accessibility_color_generation(self):
        """접근성 색상 생성 테스트"""
        base_color = Color(100, 100, 100)
        background = Color(255, 255, 255)
        compliant_colors = self.color_utils.generate_wcag_compliant_colors(
            base_color, background, "AA"
        )
        self.assertIsInstance(compliant_colors, list)
        optimal_color = self.color_utils.find_optimal_wcag_color(base_color, background, "AA")
        if optimal_color:
            self.assertIsInstance(optimal_color, Color)
        accessible_palette = self.color_utils.generate_accessible_palette(
            base_color, background, "AA"
        )
        self.assertIsInstance(accessible_palette, dict)

    def test_color_validation(self):
        """색상 검증 테스트"""
        self.assertTrue(self.color_utils.validate_color("#ff0000"))
        self.assertTrue(self.color_utils.validate_color("rgb(255, 0, 0)"))
        self.assertTrue(self.color_utils.validate_color("red"))
        self.assertFalse(self.color_utils.validate_color("invalid"))
        self.assertFalse(self.color_utils.validate_color("rgb(300, 0, 0)"))
        self.assertFalse(self.color_utils.validate_color("#gg0000"))

    def test_color_info(self):
        """색상 정보 테스트"""
        color = Color(255, 0, 0)
        info = self.color_utils.get_color_info(color)
        self.assertIn("hex", info)
        self.assertIn("rgb", info)
        self.assertIn("rgba", info)
        self.assertIn("hsl", info)
        self.assertIn("hsla", info)
        self.assertIn("components", info)
        self.assertIn("hsl_components", info)
        self.assertIn("is_light", info)
        self.assertIn("is_dark", info)
        self.assertIn("is_saturated", info)

    def test_color_temperature(self):
        """색상 온도 테스트"""
        warm_color = Color(255, 0, 0)
        temperature = self.color_utils.get_color_temperature(warm_color)
        self.assertEqual(temperature, "warm")
        cool_color = Color(0, 0, 255)
        temperature = self.color_utils.get_color_temperature(cool_color)
        self.assertEqual(temperature, "cool")
        neutral_color = Color(128, 128, 128)
        temperature = self.color_utils.get_color_temperature(neutral_color)
        self.assertEqual(temperature, "neutral")

    def test_gradient_generation(self):
        """그라디언트 생성 테스트"""
        start_color = Color(255, 0, 0)
        end_color = Color(0, 0, 255)
        gradient = self.color_utils.create_gradient(start_color, end_color, 5)
        self.assertEqual(len(gradient), 5)
        radial_gradient = self.color_utils.create_radial_gradient(start_color, end_color, 7)
        self.assertEqual(len(radial_gradient), 7)

    def test_alpha_operations(self):
        """알파 채널 작업 테스트"""
        color = Color(255, 0, 0, 0.5)
        adjusted = self.color_utils.adjust_opacity(color, 0.8)
        self.assertEqual(adjusted.a, 0.8)
        transparent = self.color_utils.make_transparent(color, 0.3)
        self.assertEqual(transparent.a, 0.2)
        opaque = self.color_utils.make_opaque(color, 0.3)
        self.assertEqual(opaque.a, 0.8)

    def test_background_blending(self):
        """배경 블렌딩 테스트"""
        foreground = Color(255, 0, 0, 0.5)
        background = Color(255, 255, 255)
        blended = self.color_utils.blend_with_background(foreground, background)
        self.assertIsNotNone(blended)
        self.assertEqual(blended.a, 1.0)
        colors = [Color(255, 0, 0, 0.5), Color(0, 255, 0, 0.5)]
        blended_colors = self.color_utils.get_alpha_blended_colors(colors, background)
        self.assertEqual(len(blended_colors), 2)

    def test_alpha_mask(self):
        """알파 마스크 테스트"""
        base_color = Color(255, 0, 0)
        mask_color = Color(128, 128, 128)
        masked = self.color_utils.create_alpha_mask(base_color, mask_color)
        self.assertIsNotNone(masked)
        self.assertLess(masked.a, 1.0)
        applied = self.color_utils.apply_alpha_mask(base_color, mask_color)
        self.assertIsNotNone(applied)

    def test_accessibility_theme_validation(self):
        """접근성 테마 검증 테스트"""
        theme_colors = {
            "primary": Color(255, 0, 0),
            "secondary": Color(0, 255, 0),
            "text": Color(0, 0, 0),
        }
        background = Color(255, 255, 255)
        validation = self.color_utils.validate_accessibility_theme(theme_colors, background, "AA")
        self.assertIn("valid", validation)
        self.assertIn("overall_score", validation)
        self.assertIn("color_analysis", validation)
        self.assertIn("recommendations", validation)

    def test_accessibility_improvements(self):
        """접근성 개선 제안 테스트"""
        foreground = Color(100, 100, 100)
        background = Color(255, 255, 255)
        suggestions = self.color_utils.suggest_accessibility_improvements(
            foreground, background, "AA"
        )
        self.assertIn("current_contrast", suggestions)
        self.assertIn("required_contrast", suggestions)
        self.assertIn("wcag_level", suggestions)
        self.assertIn("improvements", suggestions)

    def test_high_contrast_theme_creation(self):
        """고대비 테마 생성 테스트"""
        base_colors = {"primary": Color(100, 100, 100), "secondary": Color(150, 150, 150)}
        background = Color(255, 255, 255)
        high_contrast_theme = self.color_utils.create_high_contrast_theme(
            base_colors, background, "AAA"
        )
        self.assertIsInstance(high_contrast_theme, dict)

    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        self.assertIsNone(self.color_utils.parse_color(None))
        self.assertIsNone(self.color_utils.parse_color(""))
        self.assertIsNone(self.color_utils.parse_color("rgb(300, 0, 0)"))
        self.assertIsNone(self.color_utils.parse_color("hsl(400, 100%, 50%)"))
        edge_color = Color(0, 0, 0, 0.0)
        self.assertEqual(edge_color.a, 0.0)
        edge_color2 = Color(255, 255, 255, 1.0)
        self.assertEqual(edge_color2.a, 1.0)

    def test_performance(self):
        """성능 테스트"""
        import time

        start_time = time.time()
        for i in range(1000):
            color = Color(i % 256, (i + 50) % 256, (i + 100) % 256)
            self.color_utils.get_color_info(color)
        end_time = time.time()
        self.assertLess(end_time - start_time, 1.0)


if __name__ == "__main__":
    unittest.main()
