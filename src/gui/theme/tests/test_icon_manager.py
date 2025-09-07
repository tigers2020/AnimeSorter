"""
IconManager 단위 테스트

이 모듈은 IconManager 클래스의 모든 기능을 테스트합니다.
"""

import unittest
import tempfile
import json
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon

# 테스트할 모듈
from src.engine.icon_manager import IconManager


class TestIconManager(unittest.TestCase):
    """IconManager 단위 테스트 클래스"""
    
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
        # 테스트용 아이콘 디렉토리 구조 생성
        self._create_test_icon_structure()
        
        # IconManager 인스턴스 생성
        self.icon_manager = IconManager(self.app, self.temp_path)
    
    def tearDown(self):
        """각 테스트 메서드 실행 후 정리"""
        if hasattr(self, 'icon_manager'):
            self.icon_manager.cleanup()
    
    def _create_test_icon_structure(self):
        """테스트용 아이콘 디렉토리 구조 생성"""
        # 테마별 디렉토리 생성
        light_dir = self.temp_path / "light"
        dark_dir = self.temp_path / "dark"
        
        light_dir.mkdir(exist_ok=True)
        dark_dir.mkdir(exist_ok=True)
        
        # 라이트 테마 아이콘 생성
        light_home_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke="#333333" stroke-width="2"/>
</svg>"""
        
        light_settings_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="3" stroke="#333333" stroke-width="2"/>
</svg>"""
        
        # 다크 테마 아이콘 생성
        dark_home_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke="#ffffff" stroke-width="2"/>
</svg>"""
        
        dark_settings_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="3" stroke="#ffffff" stroke-width="2"/>
</svg>"""
        
        # 고해상도 아이콘 생성
        light_home_2x_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M6 18l18-14 18 14v22a4 4 0 0 1-4 4H10a4 4 0 0 1-4-4z" stroke="#333333" stroke-width="3"/>
</svg>"""
        
        # 파일 생성
        with open(light_dir / "home.svg", 'w', encoding='utf-8') as f:
            f.write(light_home_svg)
        
        with open(light_dir / "settings.svg", 'w', encoding='utf-8') as f:
            f.write(light_settings_svg)
        
        with open(dark_dir / "home.svg", 'w', encoding='utf-8') as f:
            f.write(dark_home_svg)
        
        with open(dark_dir / "settings.svg", 'w', encoding='utf-8') as f:
            f.write(dark_settings_svg)
        
        with open(light_dir / "home@2x.svg", 'w', encoding='utf-8') as f:
            f.write(light_home_2x_svg)
    
    def test_initialization(self):
        """IconManager 초기화 테스트"""
        self.assertIsNotNone(self.icon_manager)
        self.assertEqual(self.icon_manager.get_theme(), "light")
        self.assertEqual(self.icon_manager.get_icon_theme(), "light")
        self.assertIsInstance(self.icon_manager.theme_paths, dict)
        self.assertIn("light", self.icon_manager.theme_paths)
        self.assertIn("dark", self.icon_manager.theme_paths)
    
    def test_theme_switching(self):
        """테마 전환 테스트"""
        # 라이트에서 다크로 전환
        success = self.icon_manager.set_theme("dark")
        self.assertTrue(success)
        self.assertEqual(self.icon_manager.get_theme(), "dark")
        self.assertEqual(self.icon_manager.get_icon_theme(), "dark")
        
        # 다크에서 라이트로 전환
        success = self.icon_manager.set_theme("light")
        self.assertTrue(success)
        self.assertEqual(self.icon_manager.get_theme(), "light")
        self.assertEqual(self.icon_manager.get_icon_theme(), "light")
        
        # 고대비 테마 전환
        success = self.icon_manager.set_theme("high-contrast")
        self.assertTrue(success)
        self.assertEqual(self.icon_manager.get_theme(), "high-contrast")
        self.assertEqual(self.icon_manager.get_icon_theme(), "dark")  # 고대비는 다크 아이콘 사용
    
    def test_invalid_theme(self):
        """잘못된 테마 설정 테스트"""
        success = self.icon_manager.set_theme("invalid_theme")
        self.assertFalse(success)
        self.assertEqual(self.icon_manager.get_theme(), "light")  # 원래 테마 유지
    
    def test_icon_loading_from_theme_path(self):
        """테마별 아이콘 경로에서 아이콘 로딩 테스트"""
        # 라이트 테마에서 홈 아이콘 로딩
        icon = self.icon_manager.get_icon("home")
        self.assertIsNotNone(icon)
        self.assertIsInstance(icon, QIcon)
        self.assertFalse(icon.isNull())
        
        # 다크 테마로 전환 후 홈 아이콘 로딩
        self.icon_manager.set_theme("dark")
        icon = self.icon_manager.get_icon("home")
        self.assertIsNotNone(icon)
        self.assertIsInstance(icon, QIcon)
        self.assertFalse(icon.isNull())
    
    def test_icon_loading_with_size(self):
        """크기 지정 아이콘 로딩 테스트"""
        size = QSize(32, 32)
        icon = self.icon_manager.get_icon("home", size)
        self.assertIsNotNone(icon)
        self.assertIsInstance(icon, QIcon)
        self.assertFalse(icon.isNull())
    
    def test_high_dpi_icon_loading(self):
        """고해상도 아이콘 로딩 테스트"""
        # 고해상도 아이콘 파일 존재 확인
        high_dpi_icons = self.icon_manager.get_high_dpi_icons("home")
        self.assertIn("1x", high_dpi_icons)
        self.assertIn("2x", high_dpi_icons)
        
        # 고해상도 아이콘 로딩
        icon = self.icon_manager.get_icon("home", QSize(48, 48))
        self.assertIsNotNone(icon)
        self.assertFalse(icon.isNull())
    
    def test_icon_path_retrieval(self):
        """아이콘 파일 경로 반환 테스트"""
        # 라이트 테마에서 홈 아이콘 경로
        icon_path = self.icon_manager.get_icon_path("home")
        self.assertIsNotNone(icon_path)
        self.assertTrue(icon_path.exists())
        self.assertEqual(icon_path.suffix, ".svg")
        
        # 다크 테마로 전환 후 홈 아이콘 경로
        self.icon_manager.set_theme("dark")
        icon_path = self.icon_manager.get_icon_path("home")
        self.assertIsNotNone(icon_path)
        self.assertTrue(icon_path.exists())
        self.assertEqual(icon_path.suffix, ".svg")
    
    def test_available_icons_listing(self):
        """사용 가능한 아이콘 목록 반환 테스트"""
        # 라이트 테마에서 사용 가능한 아이콘
        icons = self.icon_manager.list_available_icons()
        self.assertIsInstance(icons, list)
        self.assertIn("home", icons)
        self.assertIn("settings", icons)
        self.assertEqual(len(icons), 2)
        
        # 다크 테마로 전환 후 사용 가능한 아이콘
        self.icon_manager.set_theme("dark")
        icons = self.icon_manager.list_available_icons()
        self.assertIsInstance(icons, list)
        self.assertIn("home", icons)
        self.assertIn("settings", icons)
        self.assertEqual(len(icons), 2)
    
    def test_icon_quality_info(self):
        """아이콘 품질 정보 반환 테스트"""
        info = self.icon_manager.get_icon_quality_info("home")
        self.assertIsInstance(info, dict)
        self.assertEqual(info["name"], "home")
        self.assertEqual(info["format"], ".svg")
        self.assertEqual(info["type"], "vector")
        self.assertTrue(info["scalable"])
        self.assertTrue(info["optimized"])
    
    def test_svg_optimization_check(self):
        """SVG 최적화 상태 확인 테스트"""
        # 홈 아이콘 최적화 상태 확인
        home_icon_path = self.icon_manager.get_icon_path("home")
        is_optimized = self.icon_manager._is_svg_optimized(home_icon_path)
        self.assertTrue(is_optimized)
    
    def test_dpi_awareness_check(self):
        """고해상도 디스플레이 인식 확인 테스트"""
        # 홈 아이콘 DPI 인식 확인
        home_icon_path = self.icon_manager.get_icon_path("home")
        is_dpi_aware = self.icon_manager._is_dpi_aware(home_icon_path)
        self.assertTrue(is_dpi_aware)  # @2x 파일이 존재하므로 True
    
    def test_icon_set_creation(self):
        """여러 크기의 아이콘 세트 생성 테스트"""        
        sizes = [QSize(16, 16), QSize(24, 24), QSize(32, 32)]

        icon_set = self.icon_manager.create_icon_set("home", sizes)

        self.assertIsInstance(icon_set, dict)
        self.assertEqual(len(icon_set), 3)

        # 문자열 키를 사용하여 검증
        for size in sizes:
            size_key = f"{size.width()}x{size.height()}"
            self.assertIn(size_key, icon_set)
            self.assertIsInstance(icon_set[size_key], QIcon)
            self.assertFalse(icon_set[size_key].isNull())
    
    def test_svg_optimization_analysis(self):
        """SVG 아이콘 최적화 분석 테스트"""
        optimization_results = self.icon_manager.optimize_svg_icons()
        self.assertIsInstance(optimization_results, dict)
        self.assertIn("home", optimization_results)
        self.assertIn("settings", optimization_results)
        self.assertTrue(optimization_results["home"])
        self.assertTrue(optimization_results["settings"])
    
    def test_icon_integrity_validation(self):
        """아이콘 무결성 검증 테스트"""
        # 홈 아이콘 무결성 검증
        integrity = self.icon_manager.validate_icon_integrity("home")
        self.assertIsInstance(integrity, dict)
        self.assertTrue(integrity["valid"])
        self.assertEqual(integrity["format"], ".svg")
        self.assertTrue(integrity["high_dpi_support"])
        self.assertIn("1x", integrity["high_dpi_versions"])
        self.assertIn("2x", integrity["high_dpi_versions"])
    
    def test_icon_statistics(self):
        """아이콘 통계 정보 반환 테스트"""
        stats = self.icon_manager.get_icon_statistics()
        self.assertIsInstance(stats, dict)
        self.assertEqual(stats["total_themes"], 3)
        self.assertIn("light", stats["theme_stats"])
        self.assertIn("dark", stats["theme_stats"])
        
        # 라이트 테마 통계
        light_stats = stats["theme_stats"]["light"]
        self.assertEqual(light_stats["total_icons"], 3)  # home, settings, home@2x
        self.assertEqual(light_stats["svg_icons"], 3)
        self.assertEqual(light_stats["high_dpi_icons"], 1)
    
    def test_cache_functionality(self):
        """캐시 기능 테스트"""
        # 초기 캐시 정보
        initial_cache_info = self.icon_manager.get_cache_info()
        
        # 아이콘 로딩 (캐시에 저장됨)
        icon1 = self.icon_manager.get_icon("home")
        icon2 = self.icon_manager.get_icon("home")  # 캐시에서 로드
        
        # 캐시 크기 증가 확인
        cache_info = self.icon_manager.get_cache_info()
        self.assertGreater(cache_info["icon_cache_size"], initial_cache_info["icon_cache_size"])
        
        # 캐시 클리어
        self.icon_manager.clear_cache()
        cleared_cache_info = self.icon_manager.get_cache_info()
        self.assertEqual(cleared_cache_info["icon_cache_size"], 0)
    
    def test_icon_addition_and_removal(self):
        """아이콘 추가 및 제거 테스트"""
        # 새 아이콘 추가
        test_icon_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="3" y="3" width="18" height="18" stroke="#333333" stroke-width="2"/>
</svg>"""
        
        test_icon_path = self.temp_path / "test_icon.svg"
        with open(test_icon_path, 'w', encoding='utf-8') as f:
            f.write(test_icon_content)
        
        # 아이콘 추가
        success = self.icon_manager.add_icon("test", test_icon_path, "light")
        self.assertTrue(success)
        
        # 추가된 아이콘 확인
        icon = self.icon_manager.get_icon("test")
        self.assertIsNotNone(icon)
        self.assertFalse(icon.isNull())
        
        # 아이콘 제거
        success = self.icon_manager.remove_icon("test", "light")
        self.assertTrue(success)
        
        # 제거된 아이콘 확인 (fallback 비활성화)
        icon = self.icon_manager.get_icon("test", enable_fallback=False)
        self.assertIsNone(icon)
    
    def test_fallback_icon_creation(self):
        """기본 아이콘 생성 테스트"""
        # 존재하지 않는 아이콘에 대한 기본 아이콘 생성
        icon = self.icon_manager.get_icon("nonexistent_icon")
        self.assertIsNotNone(icon)
        self.assertIsInstance(icon, QIcon)
    
    def test_color_extraction_from_name(self):
        """아이콘 이름에서 색상 추출 테스트"""
        # 색상 키워드가 포함된 이름에서 색상 추출
        red_color = self.icon_manager._extract_color_from_name("red_button")
        self.assertEqual(red_color, "#ff0000")
        
        blue_color = self.icon_manager._extract_color_from_name("blue_icon")
        self.assertEqual(blue_color, "#0000ff")
        
        # 색상 키워드가 없는 이름
        no_color = self.icon_manager._extract_color_from_name("home")
        self.assertIsNone(no_color)
    
    def test_signal_emission(self):
        """시그널 발생 테스트"""
        # 테마 변경 시그널 확인
        signal_received = False
        signal_theme = None
        
        def on_icon_theme_changed(theme):
            nonlocal signal_received, signal_theme
            signal_received = True
            signal_theme = theme
        
        self.icon_manager.icon_theme_changed.connect(on_icon_theme_changed)
        
        # 테마 변경
        self.icon_manager.set_theme("dark")
        
        # 시그널 발생 확인
        self.assertTrue(signal_received)
        self.assertEqual(signal_theme, "dark")
    
    def test_error_handling(self):
        """오류 처리 테스트"""
        # 존재하지 않는 테마로 전환 시도
        success = self.icon_manager.set_theme("invalid_theme")
        self.assertFalse(success)
        
        # 존재하지 않는 아이콘 로딩 (fallback 비활성화)
        icon = self.icon_manager.get_icon("nonexistent", enable_fallback=False)
        self.assertIsNone(icon)
        
        # 잘못된 경로로 아이콘 추가 시도
        success = self.icon_manager.add_icon("test", "nonexistent_path.svg", "light")
        self.assertFalse(success)
    
    def test_cleanup(self):
        """리소스 정리 테스트"""
        # 아이콘 로딩으로 캐시 채우기
        self.icon_manager.get_icon("home")
        self.icon_manager.get_icon("settings")
        
        # 캐시에 아이콘이 있는지 확인
        cache_info = self.icon_manager.get_cache_info()
        self.assertGreater(cache_info["icon_cache_size"], 0)
        
        # 정리
        self.icon_manager.cleanup()
        
        # 캐시가 비워졌는지 확인
        cache_info = self.icon_manager.get_cache_info()
        self.assertEqual(cache_info["icon_cache_size"], 0)


if __name__ == '__main__':
    unittest.main()
