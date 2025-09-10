"""
ThemeManager 통합 테스트

이 모듈은 ThemeManager 클래스의 통합 테스트를 제공합니다.
"""

import logging

logger = logging.getLogger(__name__)
import json
import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from src.engine.template_loader import TemplateLoader
from src.engine.theme_manager import ThemeManager, ThemeType
from src.engine.token_loader import TokenLoader


class TestThemeManager(unittest.TestCase):
    """ThemeManager 통합 테스트 클래스"""

    @classmethod
    def setUpClass(cls):
        """테스트 클래스 설정"""
        cls.app = QApplication([])
        cls.temp_dir = tempfile.mkdtemp()
        cls.temp_path = Path(cls.temp_dir)

    @classmethod
    def tearDownClass(cls):
        """테스트 클래스 정리"""
        cls.app.quit()
        import shutil

        shutil.rmtree(cls.temp_dir)

    def setUp(self):
        """각 테스트 메서드 실행 전 설정"""
        self.theme_dir = self.temp_path / "themes"
        self.theme_dir.mkdir(exist_ok=True)
        self.tokens_dir = self.temp_path / "tokens"
        self.tokens_dir.mkdir(exist_ok=True)
        self.templates_dir = self.temp_path / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        (self.templates_dir / "components").mkdir(exist_ok=True)
        (self.templates_dir / "layouts").mkdir(exist_ok=True)
        (self.templates_dir / "utilities").mkdir(exist_ok=True)

    def tearDown(self):
        """각 테스트 메서드 실행 후 정리"""
        if hasattr(self, "theme_manager"):
            self.theme_manager.cleanup()

    def test_theme_manager_initialization(self):
        """테마 매니저 초기화 테스트"""
        self.theme_manager = ThemeManager(self.app)
        self.assertIsNotNone(self.theme_manager)
        self.assertEqual(self.theme_manager.current_theme, "light")
        self.assertEqual(self.theme_manager.current_theme_type, ThemeType.LIGHT)
        self.assertIsInstance(self.theme_manager.token_loader, TokenLoader)
        self.assertIsInstance(self.theme_manager.template_loader, TemplateLoader)

    def test_builtin_themes_loading(self):
        """내장 테마 로딩 테스트"""
        self.theme_manager = ThemeManager(self.app)
        available_themes = self.theme_manager.get_available_themes()
        theme_names = [theme.name for theme in available_themes]
        self.assertIn("light", theme_names)
        self.assertIn("dark", theme_names)
        self.assertIn("high_contrast", theme_names)
        light_theme = self.theme_manager.get_theme_info("light")
        self.assertIsNotNone(light_theme)
        self.assertEqual(light_theme.type, ThemeType.LIGHT)
        self.assertTrue(light_theme.is_builtin)

    def test_theme_switching(self):
        """테마 전환 테스트"""
        self.theme_manager = ThemeManager(self.app)
        callback_called = False
        callback_theme = None

        def theme_change_callback(event):
            nonlocal callback_called, callback_theme
            callback_called = True
            callback_theme = event.new_theme

        self.theme_manager.add_theme_change_callback(theme_change_callback)
        result = self.theme_manager.switch_theme("dark", transition=False)
        self.assertTrue(result)
        self.assertTrue(callback_called)
        self.assertEqual(callback_theme, "dark")
        self.assertEqual(self.theme_manager.get_current_theme(), "dark")
        self.assertEqual(self.theme_manager.get_current_theme_type(), ThemeType.DARK)

    def test_custom_theme_creation(self):
        """사용자 정의 테마 생성 테스트"""
        self.theme_manager = ThemeManager(self.app)
        custom_theme_data = {
            "name": "custom_theme",
            "version": "1.0.0",
            "description": "사용자 정의 테마",
            "author": "Test User",
            "created_date": "2024-01-01",
            "modified_date": "2024-01-01",
            "tags": ["custom", "test"],
            "colors": {
                "primary": {"value": "#ff0000", "description": "빨간색"},
                "background": {"value": "#ffffff", "description": "흰색"},
            },
        }
        result = self.theme_manager.create_custom_theme("custom_theme", custom_theme_data)
        self.assertTrue(result)
        custom_theme_info = self.theme_manager.get_theme_info("custom_theme")
        self.assertIsNotNone(custom_theme_info)
        self.assertEqual(custom_theme_info.type, ThemeType.CUSTOM)
        self.assertFalse(custom_theme_info.is_builtin)

    def test_theme_export_import(self):
        """테마 내보내기/가져오기 테스트"""
        self.theme_manager = ThemeManager(self.app)
        export_path = self.temp_path / "exported_theme.json"
        result = self.theme_manager.export_theme("light", export_path)
        self.assertTrue(result)
        self.assertTrue(export_path.exists())
        result = self.theme_manager.import_theme(export_path, "light_imported")
        self.assertTrue(result)
        imported_themes = [
            theme.name
            for theme in self.theme_manager.get_available_themes()
            if theme.name.startswith("light_")
        ]
        self.assertTrue(len(imported_themes) > 0)

    def test_theme_preview(self):
        """테마 미리보기 테스트"""
        self.theme_manager = ThemeManager(self.app)
        preview = self.theme_manager.get_theme_preview("light")
        self.assertIsInstance(preview, dict)
        self.assertIn("name", preview)
        self.assertIn("type", preview)
        self.assertIn("description", preview)
        self.assertIn("color_samples", preview)
        self.assertIn("font_samples", preview)
        self.assertIn("spacing_samples", preview)

    def test_theme_variables_setting(self):
        """테마 변수 설정 테스트"""
        self.theme_manager = ThemeManager(self.app)
        variables = {
            "primary_color": "#ff0000",
            "background_color": "#ffffff",
            "text_color": "#000000",
        }
        self.theme_manager.template_loader.set_variables(variables)
        for var_name, var_value in variables.items():
            loaded_value = self.theme_manager.template_loader.get_variable(var_name)
            self.assertEqual(loaded_value, var_value)

    def test_theme_transition_support(self):
        """테마 전환 지원 테스트"""
        self.theme_manager = ThemeManager(self.app)
        transition_supported = self.theme_manager._is_transition_supported()
        self.assertTrue(transition_supported)
        duration = self.theme_manager._get_transition_duration()
        self.assertIsInstance(duration, int)
        self.assertGreater(duration, 0)

    def test_theme_config_saving(self):
        """테마 설정 저장 테스트"""
        self.theme_manager = ThemeManager(self.app)
        self.theme_manager._save_theme_config()
        config_file = Path(self.theme_manager.theme_config_file)
        self.assertTrue(config_file.exists())
        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)
        self.assertIn("current_theme", config)
        self.assertEqual(config["current_theme"], "light")

    def test_theme_validation(self):
        """테마 유효성 검사 테스트"""
        self.theme_manager = ThemeManager(self.app)
        is_valid, errors = self.theme_manager.template_loader.validate_template("variables")
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(errors, list)

    def test_theme_reloading(self):
        """테마 재로딩 테스트"""
        self.theme_manager = ThemeManager(self.app)
        initial_theme_count = len(self.theme_manager.get_available_themes())
        self.theme_manager.reload_themes()
        reloaded_theme_count = len(self.theme_manager.get_available_themes())
        self.assertEqual(reloaded_theme_count, initial_theme_count)

    def test_theme_cleanup(self):
        """테마 매니저 정리 테스트"""
        self.theme_manager = ThemeManager(self.app)
        self.assertIsNotNone(self.theme_manager.token_loader)
        self.assertIsNotNone(self.theme_manager.template_loader)
        self.theme_manager.cleanup()
        self.assertIsNotNone(self.theme_manager.token_loader)
        self.assertIsNotNone(self.theme_manager.template_loader)

    def test_theme_change_callbacks(self):
        """테마 변경 콜백 테스트"""
        self.theme_manager = ThemeManager(self.app)
        callback_called = False

        def test_callback(event):
            nonlocal callback_called
            callback_called = True

        self.theme_manager.add_theme_change_callback(test_callback)
        callbacks = self.theme_manager.get_functions()
        self.assertIsInstance(callbacks, dict)
        self.theme_manager.remove_theme_change_callback(test_callback)
        remaining_callbacks = self.theme_manager.theme_change_callbacks
        self.assertNotIn(test_callback, remaining_callbacks)

    def test_color_parsing(self):
        """색상 파싱 테스트"""
        self.theme_manager = ThemeManager(self.app)
        test_colors = [
            ("#ff0000", True),
            ("rgb(255, 0, 0)", True),
            ("rgba(255, 0, 0, 0.5)", True),
            ("invalid_color", False),
        ]
        for color_value, should_succeed in test_colors:
            parsed_color = self.theme_manager._parse_color_value(color_value)
            if should_succeed:
                self.assertIsNotNone(parsed_color)
            else:
                self.assertIsNone(parsed_color)

    def test_template_loading_integration(self):
        """템플릿 로딩 통합 테스트"""
        self.theme_manager = ThemeManager(self.app)
        template_names = self.theme_manager.template_loader.get_template_names()
        self.assertIsInstance(template_names, list)
        search_results = self.theme_manager.template_loader.search_templates("button")
        self.assertIsInstance(search_results, list)

    def test_token_loading_integration(self):
        """토큰 로딩 통합 테스트"""
        self.theme_manager = ThemeManager(self.app)
        token_names = list(self.theme_manager.token_loader.tokens.keys())
        self.assertIsInstance(token_names, list)
        test_variable = "test_var"
        test_value = "test_value"
        self.theme_manager.token_loader.set_token(test_variable, test_value)
        retrieved_value = self.theme_manager.token_loader.get_token(test_variable)
        self.assertEqual(retrieved_value, test_value)


class TestThemeManagerEdgeCases(unittest.TestCase):
    """ThemeManager 엣지 케이스 테스트"""

    @classmethod
    def setUpClass(cls):
        """테스트 클래스 설정"""
        cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        """테스트 클래스 정리"""
        cls.app.quit()

    def test_invalid_theme_switching(self):
        """잘못된 테마 전환 테스트"""
        theme_manager = ThemeManager(self.app)
        result = theme_manager.switch_theme("nonexistent_theme")
        self.assertFalse(result)
        self.assertEqual(theme_manager.get_current_theme(), "light")
        theme_manager.cleanup()

    def test_theme_manager_without_app(self):
        """QApplication 없이 ThemeManager 생성 테스트"""
        from unittest.mock import patch

        with patch("PyQt5.QtWidgets.QApplication.instance", return_value=None):
            with self.assertRaises(RuntimeError):
                ThemeManager(None)

    def test_theme_data_loading_failure(self):
        """테마 데이터 로딩 실패 테스트"""
        theme_manager = ThemeManager(self.app)
        result = theme_manager._load_theme_data("nonexistent_theme")
        self.assertFalse(result)
        theme_manager.cleanup()


if __name__ == "__main__":
    unittest.main()
