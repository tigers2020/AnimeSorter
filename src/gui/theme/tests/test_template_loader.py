"""
TemplateLoader 테스트 모듈

이 모듈은 TemplateLoader 클래스의 기능을 테스트합니다.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from src.gui.theme.engine.template_loader import TemplateLoader
from src.gui.theme.engine.types import (BorderSystem, BorderToken,
                                        ColorPalette, ColorToken, FontSystem,
                                        FontToken, SpacingSystem, SpacingToken,
                                        ThemeTokens)


class TestTemplateLoader(unittest.TestCase):
    """TemplateLoader 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir) / "templates"
        self.templates_dir.mkdir(parents=True)

        # 하위 디렉토리들 생성
        (self.templates_dir / "components").mkdir()
        (self.templates_dir / "layouts").mkdir()
        (self.templates_dir / "utilities").mkdir()

        # 테스트 템플릿 파일들 생성
        self._create_test_templates()

        # TemplateLoader 인스턴스 생성
        self.template_loader = TemplateLoader(self.templates_dir)

        # 테스트 토큰 데이터
        self.test_tokens = ThemeTokens(
            name="Test Theme",
            version="1.0.0",
            colors=ColorPalette(
                primary=ColorToken(value="#007acc", description="Primary color"),
                secondary=ColorToken(value="#6c757d", description="Secondary color"),
                background=ColorToken(value="#ffffff", description="Background color"),
                text=ColorToken(value="#212529", description="Text color"),
                surface=ColorToken(value="#f8f9fa", description="Surface color"),
                border=ColorToken(value="#dee2e6", description="Border color"),
            ),
            fonts=FontSystem(
                primary=FontToken(
                    family="Segoe UI, sans-serif", size=14, description="Primary font"
                ),
                sizes={"xs": 12, "sm": 14, "md": 16, "lg": 18, "xl": 20},
            ),
            spacing=SpacingSystem(
                xs=SpacingToken(value=4, description="Extra small spacing"),
                sm=SpacingToken(value=8, description="Small spacing"),
                md=SpacingToken(value=16, description="Medium spacing"),
                lg=SpacingToken(value=24, description="Large spacing"),
                xl=SpacingToken(value=32, description="Extra large spacing"),
            ),
            borders=BorderSystem(
                widths={
                    "thin": BorderToken(width=1, description="Thin border width"),
                    "normal": BorderToken(width=2, description="Normal border width"),
                    "thick": BorderToken(width=3, description="Thick border width"),
                },
                radiuses={
                    "small": BorderToken(radius=4, description="Small border radius"),
                    "default": BorderToken(radius=6, description="Default border radius"),
                    "large": BorderToken(radius=8, description="Large border radius"),
                },
            ),
        )

    def tearDown(self):
        """테스트 정리"""
        # 임시 디렉토리 제거
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_templates(self):
        """테스트용 템플릿 파일들을 생성합니다"""
        # button.qss
        button_content = """
        QPushButton {
            background-color: var(--primary-color);
            color: var(--text-color);
            border-radius: var(--border-radius);
            padding: var(--spacing-md);
        }
        """
        (self.templates_dir / "components" / "button.qss").write_text(
            button_content, encoding="utf-8"
        )

        # main_window.qss
        main_window_content = """
        QMainWindow {
            background-color: var(--background-color);
        }
        """
        (self.templates_dir / "layouts" / "main_window.qss").write_text(
            main_window_content, encoding="utf-8"
        )

        # utilities.qss
        utilities_content = """
        .utility-class {
            margin: var(--spacing-sm);
        }
        """
        (self.templates_dir / "utilities" / "utilities.qss").write_text(
            utilities_content, encoding="utf-8"
        )

    def test_init(self):
        """초기화 테스트"""
        self.assertEqual(self.template_loader.templates_dir, self.templates_dir)
        self.assertIsInstance(self.template_loader.template_cache, dict)
        self.assertIsInstance(self.template_loader.templates, dict)
        self.assertIsInstance(self.template_loader.variables, dict)
        self.assertIsInstance(self.template_loader.functions, dict)
        self.assertIsInstance(self.template_loader.imports, dict)

    def test_load_template_basic(self):
        """기본 템플릿 로딩 테스트"""
        template = self.template_loader.load_template("button")
        self.assertIsInstance(template, str)
        self.assertIn("QPushButton", template)
        self.assertIn("background-color", template)

    def test_load_template_not_found(self):
        """템플릿을 찾을 수 없는 경우 테스트"""
        template = self.template_loader.load_template("nonexistent")
        self.assertEqual(template, "")  # 빈 문자열 반환

    def test_load_all_templates(self):
        """모든 템플릿 로딩 테스트"""
        all_templates = self.template_loader.load_all_templates()
        self.assertIsInstance(all_templates, dict)
        self.assertIn("button", all_templates)
        self.assertIn("main_window", all_templates)
        self.assertIn("utilities", all_templates)

    def test_get_template(self):
        """템플릿 가져오기 테스트"""
        template = self.template_loader.get_template("button")
        self.assertIsInstance(template, str)
        self.assertIn("QPushButton", template)

    def test_set_template(self):
        """템플릿 설정 테스트"""
        test_content = "QTestWidget { color: red; }"
        self.template_loader.set_template("test", test_content)

        # 설정된 템플릿 확인
        self.assertIn("test", self.template_loader.templates)
        self.assertEqual(self.template_loader.templates["test"], test_content)

    def test_save_template(self):
        """템플릿 저장 테스트"""
        test_content = "QTestWidget { background: blue; }"
        result = self.template_loader.save_template("test_save", test_content, "components")

        self.assertTrue(result)

        # 파일이 실제로 생성되었는지 확인
        saved_file = self.templates_dir / "components" / "test_save.qss"
        self.assertTrue(saved_file.exists())
        self.assertEqual(saved_file.read_text(encoding="utf-8"), test_content)

    def test_delete_template(self):
        """템플릿 삭제 테스트"""
        # 먼저 템플릿 생성
        test_content = "QTestWidget { border: 1px solid black; }"
        self.template_loader.save_template("test_delete", test_content, "components")

        # 삭제 실행
        result = self.template_loader.delete_template("test_delete")
        self.assertTrue(result)

        # 템플릿이 실제로 삭제되었는지 확인
        self.assertNotIn("test_delete", self.template_loader.templates)
        saved_file = self.templates_dir / "components" / "test_delete.qss"
        self.assertFalse(saved_file.exists())

    def test_clear_templates(self):
        """모든 템플릿 제거 테스트"""
        # 템플릿들 생성
        self.template_loader.set_template("test1", "content1")
        self.template_loader.set_template("test2", "content2")

        # 제거 실행
        self.template_loader.clear_templates()

        # 모든 템플릿이 제거되었는지 확인
        self.assertEqual(len(self.template_loader.templates), 0)
        self.assertEqual(len(self.template_loader.template_cache), 0)

    def test_get_template_names(self):
        """템플릿 이름 목록 테스트"""
        # 템플릿들 생성
        self.template_loader.set_template("test1", "content1")
        self.template_loader.set_template("test2", "content2")

        names = self.template_loader.get_template_names()
        self.assertIn("test1", names)
        self.assertIn("test2", names)

    def test_get_template_paths(self):
        """템플릿 경로 매핑 테스트"""
        paths = self.template_loader.get_template_paths()
        self.assertIsInstance(paths, dict)

    def test_search_templates(self):
        """템플릿 검색 테스트"""
        # 검색 가능한 템플릿 생성
        self.template_loader.set_template("search_test", "QWidget { color: red; }")

        results = self.template_loader.search_templates("search")
        self.assertIn("search_test", results)

    def test_validate_template(self):
        """템플릿 유효성 검사 테스트"""
        # 유효한 템플릿
        valid_content = "QWidget { color: red; }"
        self.template_loader.set_template("valid", valid_content)

        is_valid, errors = self.template_loader.validate_template("valid")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_variable_management(self):
        """변수 관리 테스트"""
        # 변수 설정
        self.template_loader.set_variable("test_var", "test_value")
        self.assertEqual(self.template_loader.get_variable("test_var"), "test_value")

        # 여러 변수 설정
        variables = {"var1": "value1", "var2": "value2"}
        self.template_loader.set_variables(variables)
        self.assertEqual(self.template_loader.get_variable("var1"), "value1")
        self.assertEqual(self.template_loader.get_variable("var2"), "value2")

        # 모든 변수 가져오기
        all_vars = self.template_loader.get_variables()
        self.assertIn("test_var", all_vars)
        self.assertIn("var1", all_vars)
        self.assertIn("var2", all_vars)

        # 변수 제거
        self.template_loader.clear_variables()
        self.assertEqual(len(self.template_loader.get_variables()), 0)

    def test_function_management(self):
        """함수 관리 테스트"""

        # 사용자 정의 함수 등록
        def test_func():
            return "test_result"

        self.template_loader.register_function("test_func", test_func)

        # 등록된 함수 확인
        functions = self.template_loader.get_functions()
        self.assertIn("test_func", functions)

        # 함수 제거
        self.template_loader.unregister_function("test_func")
        functions_after = self.template_loader.get_functions()
        self.assertNotIn("test_func", functions_after)

    def test_reload_templates(self):
        """템플릿 재로딩 테스트"""
        # 템플릿 설정
        self.template_loader.set_template("reload_test", "QWidget { color: red; }")

        # 재로딩 실행
        self.template_loader.reload_templates()

        # 템플릿이 여전히 존재하는지 확인
        self.assertIn("reload_test", self.template_loader.templates)

    def test_get_template_info(self):
        """템플릿 정보 가져오기 테스트"""
        # 템플릿 설정
        test_content = "QWidget { color: red; }"
        self.template_loader.set_template("info_test", test_content)

        # 정보 가져오기
        info = self.template_loader.get_template_info("info_test")

        self.assertEqual(info["name"], "info_test")
        self.assertEqual(info["content"], test_content)
        self.assertEqual(info["content_length"], len(test_content))
        self.assertIsInstance(info["lines"], int)

    def test_export_import_template(self):
        """템플릿 내보내기/가져오기 테스트"""
        # 내보낼 템플릿 설정
        export_content = "QExportWidget { background: green; }"
        self.template_loader.set_template("export_test", export_content)

        # 내보내기
        export_path = Path(self.temp_dir) / "exported.qss"
        export_result = self.template_loader.export_template("export_test", export_path)
        self.assertTrue(export_result)
        self.assertTrue(export_path.exists())

        # 가져오기
        import_result = self.template_loader.import_template(export_path, "import_test")
        self.assertTrue(import_result)
        self.assertIn("import_test", self.template_loader.templates)
        self.assertEqual(self.template_loader.templates["import_test"], export_content)

    def test_cache_functionality(self):
        """캐시 기능 테스트"""
        # 첫 번째 로딩
        template1 = self.template_loader.load_template("button")

        # 두 번째 로딩 (캐시에서 가져와야 함)
        template2 = self.template_loader.load_template("button")

        # 동일한 내용인지 확인
        self.assertEqual(template1, template2)

        # 캐시에 저장되었는지 확인
        cache_key = "button_True"
        self.assertIn(cache_key, self.template_loader.template_cache)

    def test_template_with_variables(self):
        """변수가 포함된 템플릿 테스트"""
        # 변수 설정
        self.template_loader.set_variable("primary-color", "#007acc")
        self.template_loader.set_variable("text-color", "#ffffff")
        self.template_loader.set_variable("border-radius", "6px")
        self.template_loader.set_variable("spacing-md", "16px")

        # 변수가 포함된 템플릿 생성
        template_with_vars = """
        QPushButton {
            background-color: var(--primary-color);
            color: var(--text-color);
            border-radius: var(--border-radius);
            padding: var(--spacing-md);
        }
        """

        # 템플릿을 파일로 저장
        self.template_loader.save_template("var_test", template_with_vars, "components")

        # 변수 해석된 템플릿 로딩 (파일에서 로딩하여 변수 치환 수행)
        resolved_template = self.template_loader.load_template("var_test", resolve_variables=True)

        # 변수가 실제 값으로 치환되었는지 확인
        self.assertIn("#007acc", resolved_template)
        self.assertIn("#ffffff", resolved_template)
        self.assertIn("6px", resolved_template)
        self.assertIn("16px", resolved_template)

    def test_template_with_functions(self):
        """함수가 포함된 템플릿 테스트"""
        # 함수가 포함된 템플릿 생성
        template_with_funcs = """
        QWidget {
            background-color: theme(primary);
            margin: spacing(md);
        }
        """

        # 템플릿 설정
        self.template_loader.set_template("func_test", template_with_funcs)

        # 함수가 포함된 템플릿 가져오기 (set_template으로 설정했으므로 get_template 사용)
        template = self.template_loader.get_template("func_test")

        # 템플릿이 로딩되었는지 확인
        self.assertIsInstance(template, str)
        self.assertIn("QWidget", template)

    def test_error_handling(self):
        """오류 처리 테스트"""
        # 존재하지 않는 템플릿 로딩 시도
        template = self.template_loader.load_template("nonexistent")
        self.assertEqual(template, "")

        # 잘못된 경로로 TemplateLoader 생성
        invalid_loader = TemplateLoader("/invalid/path")
        self.assertIsInstance(invalid_loader.templates_dir, Path)

    def test_performance_metrics(self):
        """성능 메트릭 테스트"""
        # 여러 템플릿 로딩하여 성능 테스트
        import time

        start_time = time.time()
        for i in range(10):
            self.template_loader.load_template("button")
        end_time = time.time()

        # 로딩 시간이 합리적인 범위 내에 있는지 확인
        load_time = end_time - start_time
        self.assertLess(load_time, 1.0)  # 1초 이내

    def test_template_categories(self):
        """템플릿 카테고리 테스트"""
        # 각 카테고리에 템플릿 생성
        self.template_loader.save_template("cat_test", "QWidget { }", "components")
        self.template_loader.save_template("cat_test", "QWidget { }", "layouts")
        self.template_loader.save_template("cat_test", "QWidget { }", "utilities")

        # 모든 카테고리에서 템플릿 로딩
        all_templates = self.template_loader.load_all_templates()

        # 각 카테고리의 템플릿이 로딩되었는지 확인
        self.assertIn("cat_test", all_templates)

    def test_template_validation_edge_cases(self):
        """템플릿 검증 엣지 케이스 테스트"""
        # 빈 템플릿
        self.template_loader.set_template("empty", "")
        is_valid, errors = self.template_loader.validate_template("empty")
        self.assertTrue(is_valid)  # 빈 템플릿은 유효함

        # 특수 문자가 포함된 템플릿
        special_content = "QWidget { content: 'test\\'quote'; }"
        self.template_loader.set_template("special", special_content)
        is_valid, errors = self.template_loader.validate_template("special")
        self.assertTrue(is_valid)

    def test_variable_resolution_edge_cases(self):
        """변수 해석 엣지 케이스 테스트"""
        # 중첩된 변수 참조
        self.template_loader.set_variable("nested", "var(--inner)")
        self.template_loader.set_variable("inner", "actual_value")

        template_content = "QWidget { color: var(--nested); }"
        self.template_loader.set_template("nested_test", template_content)

        resolved = self.template_loader.load_template("nested_test", resolve_variables=True)
        # 변수 해석이 제한적으로 작동하는지 확인
        self.assertIsInstance(resolved, str)

    def test_function_execution_edge_cases(self):
        """함수 실행 엣지 케이스 테스트"""
        # 잘못된 함수 호출이 포함된 템플릿
        invalid_func_template = """
        QWidget {
            background: invalid_function(arg1, arg2);
        }
        """

        self.template_loader.set_template("invalid_func", invalid_func_template)

        # 함수 실행 오류가 있어도 템플릿이 로딩되는지 확인
        template = self.template_loader.load_template("invalid_func", resolve_variables=True)
        self.assertIsInstance(template, str)

    def test_template_imports(self):
        """템플릿 import 테스트"""
        # import할 템플릿 생성
        import_content = "QImportedWidget { color: blue; }"
        self.template_loader.save_template("imported", import_content, "components")

        # import 문이 포함된 템플릿 생성
        import_template = """
        @import './imported.qss';
        QMainWidget { background: white; }
        """

        self.template_loader.set_template("import_test", import_template)

        # import가 처리되는지 확인
        template = self.template_loader.load_template("import_test", resolve_variables=True)
        self.assertIsInstance(template, str)

    def test_template_compilation_patterns(self):
        """템플릿 컴파일 패턴 테스트"""
        # 정규식 패턴들이 컴파일되었는지 확인
        self.assertIsNotNone(self.template_loader.var_pattern)
        self.assertIsNotNone(self.template_loader.simple_var_pattern)
        self.assertIsNotNone(self.template_loader.function_pattern)
        self.assertIsNotNone(self.template_loader.import_pattern)
        self.assertIsNotNone(self.template_loader.comment_pattern)
        self.assertIsNotNone(self.template_loader.whitespace_pattern)

    def test_default_functions_registration(self):
        """기본 함수 등록 테스트"""
        # 기본 함수들이 등록되었는지 확인
        expected_functions = [
            "theme",
            "color",
            "spacing",
            "font",
            "border",
            "shadow",
            "transition",
            "z_index",
            "breakpoint",
            "math",
            "scale",
            "mix",
            "lighten",
            "darken",
            "alpha",
            "contrast",
        ]

        for func_name in expected_functions:
            self.assertIn(func_name, self.template_loader.functions)

    def test_template_file_finding(self):
        """템플릿 파일 찾기 테스트"""
        # 다양한 확장자로 템플릿 생성
        self.template_loader.save_template("ext_test", "QWidget { }", "components")

        # .qss 확장자로 찾기
        template = self.template_loader.load_template("ext_test")
        self.assertIsInstance(template, str)

        # 확장자 없이 찾기
        template_no_ext = self.template_loader.load_template("ext_test")
        self.assertIsInstance(template_no_ext, str)

    def test_template_cache_invalidation(self):
        """템플릿 캐시 무효화 테스트"""
        # 템플릿 로딩
        self.template_loader.load_template("button")

        # 캐시에 저장되었는지 확인
        cache_key = "button_True"
        self.assertIn(cache_key, self.template_loader.template_cache)

        # 템플릿 수정
        self.template_loader.set_template("button", "QPushButton { color: red; }")

        # 캐시가 무효화되었는지 확인
        self.assertNotIn(cache_key, self.template_loader.template_cache)

    def test_template_directory_validation(self):
        """템플릿 디렉토리 검증 테스트"""
        # 유효한 디렉토리
        valid_loader = TemplateLoader(self.templates_dir)
        self.assertEqual(valid_loader.templates_dir, self.templates_dir)

        # 존재하지 않는 디렉토리
        invalid_loader = TemplateLoader("/nonexistent/path")
        self.assertIsInstance(invalid_loader.templates_dir, Path)

    def test_template_content_processing(self):
        """템플릿 내용 처리 테스트"""
        # 주석과 공백이 포함된 템플릿
        template_with_comments = """
        /* 주석 */
        QWidget {
            color: red; /* 인라인 주석 */
        }
        """

        self.template_loader.set_template("comment_test", template_with_comments)

        # 템플릿 로딩
        template = self.template_loader.load_template("comment_test", resolve_variables=True)

        # 주석이 제거되었는지 확인
        self.assertNotIn("/*", template)
        self.assertNotIn("*/", template)

    def test_template_error_recovery(self):
        """템플릿 오류 복구 테스트"""
        # 오류가 발생할 수 있는 템플릿
        error_template = """
        QWidget {
            background: invalid_function();
            color: var(--undefined-var);
        }
        """

        self.template_loader.set_template("error_test", error_template)

        # 오류가 있어도 템플릿이 로딩되는지 확인
        template = self.template_loader.load_template("error_test", resolve_variables=True)
        self.assertIsInstance(template, str)


if __name__ == "__main__":
    unittest.main()
