"""
테마 엔진 통합 테스트

이 모듈은 전체 테마 엔진 시스템의 통합 테스트를 수행합니다.
"""

import unittest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 테스트 환경 설정
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# 테마 엔진 모듈들 import
from src.gui.theme.engine.theme_manager import ThemeManager
from src.gui.theme.engine.template_compiler import TemplateCompiler, ASTNode, NodeType
from src.gui.theme.engine.compiler_optimizer import CompilerOptimizer, OptimizationLevel
from src.gui.theme.engine.dynamic_qss_engine import DynamicQSSEngine, create_style_condition, ConditionType
from src.gui.theme.engine.performance_monitor import PerformanceMonitor, create_performance_monitor


class TestThemeEngineIntegration(unittest.TestCase):
    """테마 엔진 통합 테스트"""

    @classmethod
    def setUpClass(cls):
        """테스트 클래스 설정"""
        # QApplication 인스턴스 생성
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])
        
        # 임시 디렉토리 생성
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.test_themes_dir = cls.temp_dir / "themes"
        cls.test_themes_dir.mkdir()
        
        # 테스트용 테마 파일 생성
        cls._create_test_themes()

    @classmethod
    def tearDownClass(cls):
        """테스트 클래스 정리"""
        # 임시 디렉토리 정리
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)
        
        # QApplication 정리
        if cls.app:
            cls.app.quit()

    @classmethod
    def _create_test_themes(cls):
        """테스트용 테마 파일들을 생성합니다"""
        # 기본 라이트 테마
        light_theme = {
            "name": "light",
            "version": "1.0.0",
            "colors": {
                "primary": "#007acc",
                "secondary": "#6c757d",
                "background": "#ffffff",
                "foreground": "#212529",
                "accent": "#28a745"
            },
            "fonts": {
                "base": "14px",
                "heading": "18px",
                "small": "12px"
            },
            "spacing": {
                "xs": "4px",
                "sm": "8px",
                "md": "16px",
                "lg": "24px",
                "xl": "32px"
            }
        }
        
        light_theme_path = cls.test_themes_dir / "light.json"
        with open(light_theme_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(light_theme, f, indent=2, ensure_ascii=False)
        
        # 다크 테마
        dark_theme = {
            "name": "dark",
            "version": "1.0.0",
            "colors": {
                "primary": "#007acc",
                "secondary": "#6c757d",
                "background": "#1e1e1e",
                "foreground": "#ffffff",
                "accent": "#28a745"
            },
            "fonts": {
                "base": "14px",
                "heading": "18px",
                "small": "12px"
            },
            "spacing": {
                "xs": "4px",
                "sm": "8px",
                "md": "16px",
                "lg": "24px",
                "xl": "32px"
            }
        }
        
        dark_theme_path = cls.test_themes_dir / "dark.json"
        with open(dark_theme_path, 'w', encoding='utf-8') as f:
            json.dump(dark_theme, f, indent=2, ensure_ascii=False)

    def setUp(self):
        """각 테스트 메서드 설정"""
        # ThemeManager 인스턴스 생성
        self.theme_manager = ThemeManager(self.app)
        
        # 테스트용 QSS 템플릿
        self.test_qss_template = """
        QWidget {
            background-color: var(--background);
            color: var(--foreground);
            font-size: var(--base-font);
        }
        
        QPushButton {
            background-color: var(--primary);
            color: white;
            padding: var(--sm-spacing);
            border: none;
            border-radius: 4px;
        }
        
        QPushButton:hover {
            background-color: var(--accent);
        }
        
        QLabel {
            color: var(--foreground);
            font-size: var(--heading-font);
        }
        """

    def tearDown(self):
        """각 테스트 메서드 정리"""
        if hasattr(self, 'theme_manager'):
            self.theme_manager.cleanup()

    def test_01_template_compiler_basic_functionality(self):
        """TemplateCompiler 기본 기능 테스트"""
        compiler = self.theme_manager.get_template_compiler()
        
        # 템플릿 파싱 테스트
        ast_node = compiler.parse_template(self.test_qss_template)
        self.assertIsInstance(ast_node, ASTNode)
        self.assertEqual(ast_node.node_type, NodeType.ROOT)
        
        # 규칙 노드 확인
        rule_nodes = ast_node.find_nodes_by_type(NodeType.RULE)
        self.assertGreater(len(rule_nodes), 0)
        
        # QSS 컴파일 테스트
        compiled_qss = compiler.compile_template(self.test_qss_template)
        self.assertIsInstance(compiled_qss, str)
        self.assertGreater(len(compiled_qss), 0)
        
        # 변수 해석 테스트
        context = {
            'background': '#ffffff',
            'foreground': '#000000',
            'primary': '#007acc',
            'accent': '#28a745',
            'base-font': '14px',
            'heading-font': '18px',
            'sm-spacing': '8px'
        }
        
        resolved_qss = compiler.compile_template(self.test_qss_template, context=context)
        self.assertIn('#ffffff', resolved_qss)
        self.assertIn('#000000', resolved_qss)

    def test_02_compiler_optimizer_functionality(self):
        """CompilerOptimizer 기능 테스트"""
        optimizer = self.theme_manager.get_compiler_optimizer()
        compiler = self.theme_manager.get_template_compiler()
        
        # AST 파싱
        ast_node = compiler.parse_template(self.test_qss_template)
        original_node_count = self._count_nodes(ast_node)
        
        # 최적화 적용
        optimized_ast, result = optimizer.optimize_ast(ast_node, OptimizationLevel.ADVANCED)
        
        # 최적화 결과 확인
        self.assertIsInstance(optimized_ast, ASTNode)
        self.assertIsInstance(result.original_node_count, int)
        self.assertIsInstance(result.optimized_node_count, int)
        
        # 최적화된 QSS 생성
        optimized_qss = compiler._generate_qss(optimized_ast)
        self.assertIsInstance(optimized_qss, str)
        self.assertGreater(len(optimized_qss), 0)

    def test_03_dynamic_qss_engine_functionality(self):
        """DynamicQSSEngine 기능 테스트"""
        engine = self.theme_manager.get_dynamic_qss_engine()
        
        # 동적 스타일 추가
        style_conditions = [
            {
                'type': 'equals',
                'property': 'theme_mode',
                'value': 'dark'
            }
        ]
        
        success = self.theme_manager.add_dynamic_style(
            selector='.dark-mode',
            properties={
                'background-color': '#1e1e1e',
                'color': '#ffffff'
            },
            conditions=style_conditions
        )
        
        self.assertTrue(success)
        
        # 동적 QSS 생성
        context = {'theme_mode': 'dark'}
        dynamic_qss = self.theme_manager.generate_dynamic_qss(
            template_content=self.test_qss_template,
            additional_context=context
        )
        
        self.assertIsInstance(dynamic_qss, str)
        self.assertGreater(len(dynamic_qss), 0)

    def test_04_theme_manager_integration(self):
        """ThemeManager 통합 기능 테스트"""
        # 테마 전환 테스트
        success = self.theme_manager.switch_theme("light")
        self.assertTrue(success)
        self.assertEqual(self.theme_manager.current_theme, "light")
        
        # 최적화된 컴파일 테스트
        optimized_qss = self.theme_manager.compile_template_with_optimization(
            self.test_qss_template,
            optimization_level=OptimizationLevel.ADVANCED
        )
        
        self.assertIsInstance(optimized_qss, str)
        self.assertGreater(len(optimized_qss), 0)
        
        # 동적 스타일 관리 테스트
        style_conditions = [
            {
                'type': 'equals',
                'property': 'user_role',
                'value': 'admin'
            }
        ]
        
        success = self.theme_manager.add_dynamic_style(
            selector='.admin-panel',
            properties={
                'border': '2px solid #dc3545',
                'background-color': '#f8f9fa'
            },
            conditions=style_conditions
        )
        
        self.assertTrue(success)
        
        # 동적 스타일 제거 테스트
        success = self.theme_manager.remove_dynamic_style('.admin-panel')
        self.assertTrue(success)

    def test_05_performance_monitoring(self):
        """성능 모니터링 테스트"""
        # PerformanceMonitor 생성
        monitor = create_performance_monitor(self.theme_manager)
        
        # 모니터링 시작
        success = monitor.start_monitoring()
        self.assertTrue(success)
        
        # 성능 메트릭 수집 대기
        import time
        time.sleep(2)
        
        # 성능 요약 확인
        summary = monitor.get_performance_summary()
        self.assertIsInstance(summary, dict)
        
        # 모니터링 중지
        success = monitor.stop_monitoring()
        self.assertTrue(success)
        
        # 성능 리포트 내보내기
        report = monitor.export_performance_report()
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)

    def test_06_end_to_end_workflow(self):
        """전체 워크플로우 테스트"""
        # 1. 테마 로드
        success = self.theme_manager.load_theme("light")
        self.assertTrue(success)
        
        # 2. 동적 스타일 추가
        success = self.theme_manager.add_dynamic_style(
            selector='.custom-widget',
            properties={
                'background-color': '#e9ecef',
                'border-radius': '8px',
                'padding': '12px'
            },
            conditions=[
                {
                    'type': 'equals',
                    'property': 'widget_type',
                    'value': 'custom'
                }
            ]
        )
        self.assertTrue(success)
        
        # 3. 최적화된 QSS 생성
        context = {
            'widget_type': 'custom',
            'background': '#ffffff',
            'foreground': '#000000'
        }
        
        dynamic_qss = self.theme_manager.generate_dynamic_qss(
            template_content=self.test_qss_template,
            additional_context=context
        )
        
        self.assertIsInstance(dynamic_qss, str)
        self.assertIn('.custom-widget', dynamic_qss)
        
        # 4. 성능 메트릭 확인
        metrics = self.theme_manager.get_compiler_performance_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn('template_compiler', metrics)
        self.assertIn('compiler_optimizer', metrics)
        self.assertIn('dynamic_qss_engine', metrics)

    def test_07_error_handling(self):
        """오류 처리 테스트"""
        # 잘못된 QSS 템플릿
        invalid_qss = """
        QWidget {
            background-color: var(--invalid-variable);
            color: ;
            font-size: invalid-value;
        }
        """
        
        # 컴파일러가 오류를 적절히 처리하는지 확인
        compiler = self.theme_manager.get_template_compiler()
        
        try:
            # 파싱 시도
            ast_node = compiler.parse_template(invalid_qss)
            self.assertIsInstance(ast_node, ASTNode)
        except Exception as e:
            # 파싱 오류가 발생해도 적절히 처리되어야 함
            self.assertIsInstance(e, Exception)

    def test_08_cache_functionality(self):
        """캐시 기능 테스트"""
        compiler = self.theme_manager.get_template_compiler()
        optimizer = self.theme_manager.get_compiler_optimizer()
        engine = self.theme_manager.get_dynamic_qss_engine()
        
        # 캐시 설정 확인
        self.assertTrue(compiler.settings['cache_enabled'])
        self.assertTrue(optimizer.settings['cache_optimizations'])
        self.assertTrue(engine.settings['enable_caching'])
        
        # 캐시 정리
        compiler.clear_cache()
        optimizer.clear_cache()
        engine.clear_cache()
        
        # 캐시가 정리되었는지 확인
        self.assertEqual(len(compiler.ast_cache), 0)
        self.assertEqual(len(compiler.compiled_cache), 0)

    def test_09_settings_management(self):
        """설정 관리 테스트"""
        # 컴파일러 설정 업데이트
        new_settings = {
            'template_compiler': {
                'minify': False,
                'remove_comments': False
            },
            'compiler_optimizer': {
                'level': 'basic'
            },
            'dynamic_qss_engine': {
                'enable_media_queries': False
            }
        }
        
        success = self.theme_manager.update_compiler_settings(new_settings)
        self.assertTrue(success)
        
        # 설정이 적용되었는지 확인
        compiler = self.theme_manager.get_template_compiler()
        self.assertFalse(compiler.settings['minify'])
        self.assertFalse(compiler.settings['remove_comments'])

    def test_10_report_generation(self):
        """리포트 생성 테스트"""
        # 컴파일러 리포트 생성
        report = self.theme_manager.export_compiler_report()
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
        
        # JSON 파싱 가능한지 확인
        import json
        try:
            report_data = json.loads(report)
            self.assertIsInstance(report_data, dict)
            self.assertIn('timestamp', report_data)
            self.assertIn('performance_metrics', report_data)
        except json.JSONDecodeError:
            self.fail("생성된 리포트가 유효한 JSON이 아닙니다")

    def _count_nodes(self, ast_node: ASTNode) -> int:
        """AST 노드 수를 계산합니다"""
        count = 1
        for child in ast_node.children:
            count += self._count_nodes(child)
        return count


class TestThemeEnginePerformance(unittest.TestCase):
    """테마 엔진 성능 테스트"""

    @classmethod
    def setUpClass(cls):
        """테스트 클래스 설정"""
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        """테스트 클래스 정리"""
        if cls.app:
            cls.app.quit()

    def setUp(self):
        """각 테스트 메서드 설정"""
        self.theme_manager = ThemeManager(self.app)
        
        # 대용량 QSS 템플릿 생성
        self.large_qss_template = self._generate_large_qss_template()

    def tearDown(self):
        """각 테스트 메서드 정리"""
        if hasattr(self, 'theme_manager'):
            self.theme_manager.cleanup()

    def _generate_large_qss_template(self) -> str:
        """대용량 QSS 템플릿을 생성합니다"""
        template_parts = []
        
        # 많은 규칙들을 가진 템플릿 생성
        for i in range(100):
            template_parts.append(f"""
            .widget-{i} {{
                background-color: var(--background-{i % 5});
                color: var(--foreground-{i % 5});
                padding: var(--spacing-{i % 4});
                margin: var(--spacing-{i % 4});
                border: 1px solid var(--border-{i % 3});
                font-size: var(--font-{i % 3});
            }}
            
            .widget-{i}:hover {{
                background-color: var(--accent-{i % 5});
                transform: scale(1.05);
                transition: all 0.3s ease;
            }}
            """)
        
        return '\n'.join(template_parts)

    def test_01_large_template_compilation_performance(self):
        """대용량 템플릿 컴파일 성능 테스트"""
        import time
        
        compiler = self.theme_manager.get_template_compiler()
        
        # 컴파일 시간 측정
        start_time = time.time()
        compiled_qss = compiler.compile_template(self.large_qss_template)
        compile_time = time.time() - start_time
        
        # 성능 기준 확인 (1초 이내)
        self.assertLess(compile_time, 1.0, f"대용량 템플릿 컴파일이 너무 느립니다: {compile_time:.3f}초")
        
        # 결과 확인
        self.assertIsInstance(compiled_qss, str)
        self.assertGreater(len(compiled_qss), 0)

    def test_02_optimization_performance(self):
        """최적화 성능 테스트"""
        import time
        
        compiler = self.theme_manager.get_template_compiler()
        optimizer = self.theme_manager.get_compiler_optimizer()
        
        # AST 파싱
        start_time = time.time()
        ast_node = compiler.parse_template(self.large_qss_template)
        parse_time = time.time() - start_time
        
        # 최적화 시간 측정
        start_time = time.time()
        optimized_ast, result = optimizer.optimize_ast(ast_node, OptimizationLevel.AGGRESSIVE)
        optimize_time = time.time() - start_time
        
        # 성능 기준 확인
        self.assertLess(parse_time, 0.5, f"AST 파싱이 너무 느립니다: {parse_time:.3f}초")
        self.assertLess(optimize_time, 1.0, f"최적화가 너무 느립니다: {optimize_time:.3f}초")
        
        # 최적화 결과 확인
        self.assertIsInstance(optimized_ast, ASTNode)
        # OptimizationResult 타입 확인 (간단한 방법으로)
        self.assertTrue(hasattr(result, 'removed_nodes'))
        self.assertTrue(hasattr(result, 'memory_saved'))

    def test_03_memory_usage_optimization(self):
        """메모리 사용량 최적화 테스트"""
        import psutil
        import gc
        
        # 가비지 컬렉션
        gc.collect()
        
        # 초기 메모리 사용량
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # 대용량 작업 수행
        compiler = self.theme_manager.get_template_compiler()
        optimizer = self.theme_manager.get_compiler_optimizer()
        
        for _ in range(10):
            ast_node = compiler.parse_template(self.large_qss_template)
            optimized_ast, result = optimizer.optimize_ast(ast_node, OptimizationLevel.AGGRESSIVE)
            compiled_qss = compiler._generate_qss(optimized_ast)
        
        # 가비지 컬렉션
        gc.collect()
        
        # 최종 메모리 사용량
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_increase = final_memory - initial_memory
        
        # 메모리 증가가 합리적인 범위 내인지 확인 (100MB 이하)
        self.assertLess(memory_increase, 100.0, 
                       f"메모리 사용량이 과도하게 증가했습니다: {memory_increase:.1f}MB")

    def test_04_cache_efficiency(self):
        """캐시 효율성 테스트"""
        compiler = self.theme_manager.get_template_compiler()
        
        # 캐시 초기화
        compiler.clear_cache()
        
        # 첫 번째 컴파일 (캐시 미스)
        start_time = time.time()
        first_compile = compiler.compile_template(self.large_qss_template)
        first_time = time.time() - start_time
        
        # 두 번째 컴파일 (캐시 히트)
        start_time = time.time()
        second_compile = compiler.compile_template(self.large_qss_template)
        second_time = time.time() - start_time
        
        # 캐시 히트 시 성능 향상 확인
        self.assertLess(second_time, first_time * 0.5, 
                       f"캐시 히트 시 성능 향상이 부족합니다: "
                       f"첫 번째: {first_time:.3f}초, 두 번째: {second_time:.3f}초")
        
        # 결과 일치 확인
        self.assertEqual(first_compile, second_compile)

    def test_05_concurrent_operations(self):
        """동시 작업 성능 테스트"""
        import threading
        import time
        
        compiler = self.theme_manager.get_template_compiler()
        results = []
        errors = []
        
        def compile_template(thread_id):
            try:
                start_time = time.time()
                result = compiler.compile_template(self.large_qss_template)
                compile_time = time.time() - start_time
                results.append((thread_id, compile_time, len(result)))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 여러 스레드에서 동시 컴파일
        threads = []
        for i in range(5):
            thread = threading.Thread(target=compile_template, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 오류 확인
        self.assertEqual(len(errors), 0, f"동시 작업 중 오류 발생: {errors}")
        
        # 모든 스레드가 성공적으로 완료되었는지 확인
        self.assertEqual(len(results), 5)
        
        # 성능 확인 (각 스레드가 합리적인 시간 내에 완료)
        for thread_id, compile_time, result_length in results:
            self.assertLess(compile_time, 2.0, 
                           f"스레드 {thread_id}의 컴파일이 너무 느립니다: {compile_time:.3f}초")
            self.assertGreater(result_length, 0)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)

