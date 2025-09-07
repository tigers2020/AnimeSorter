#!/usr/bin/env python3
"""
기본 테마 시스템 테스트
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

from src.gui.theme import ThemeManager, ThemeMode, A11yOptions


def test_theme_system():
    """테마 시스템을 테스트합니다."""
    app = QApplication(sys.argv)
    
    # 메인 윈도우 생성
    window = QMainWindow()
    window.setWindowTitle("테마 시스템 테스트")
    window.setGeometry(100, 100, 400, 300)
    
    # 중앙 위젯
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    # 레이아웃
    layout = QVBoxLayout(central_widget)
    
    # 테마 변경 버튼들
    light_btn = QPushButton("라이트 테마")
    dark_btn = QPushButton("다크 테마")
    high_contrast_btn = QPushButton("고대비 테마")
    
    # 접근성 옵션 버튼들
    font_scale_btn = QPushButton("폰트 크기 증가")
    contrast_boost_btn = QPushButton("대비 향상")
    
    # 버튼들을 레이아웃에 추가
    layout.addWidget(light_btn)
    layout.addWidget(dark_btn)
    layout.addWidget(high_contrast_btn)
    layout.addWidget(font_scale_btn)
    layout.addWidget(contrast_boost_btn)
    
    # 테마 매니저 생성
    theme_manager = ThemeManager()
    
    # 시그널 연결
    def apply_light_theme():
        theme_manager.apply(ThemeMode.LIGHT, A11yOptions())
        print("라이트 테마 적용됨")
    
    def apply_dark_theme():
        theme_manager.apply(ThemeMode.DARK, A11yOptions())
        print("다크 테마 적용됨")
    
    def apply_high_contrast_theme():
        theme_manager.apply(ThemeMode.HIGH_CONTRAST, A11yOptions())
        print("고대비 테마 적용됨")
    
    def increase_font_scale():
        current_a11y = theme_manager.current_a11y
        new_a11y = A11yOptions(
            font_scale=current_a11y.font_scale + 0.1,
            contrast_boost=current_a11y.contrast_boost,
            reduce_motion=current_a11y.reduce_motion,
            high_contrast=current_a11y.high_contrast
        )
        theme_manager.apply(theme_manager.current_mode, new_a11y)
        print(f"폰트 크기 증가: {new_a11y.font_scale}")
    
    def toggle_contrast_boost():
        current_a11y = theme_manager.current_a11y
        new_a11y = A11yOptions(
            font_scale=current_a11y.font_scale,
            contrast_boost=not current_a11y.contrast_boost,
            reduce_motion=current_a11y.reduce_motion,
            high_contrast=current_a11y.high_contrast
        )
        theme_manager.apply(theme_manager.current_mode, new_a11y)
        print(f"대비 향상: {new_a11y.contrast_boost}")
    
    # 버튼 클릭 이벤트 연결
    light_btn.clicked.connect(apply_light_theme)
    dark_btn.clicked.connect(apply_dark_theme)
    high_contrast_btn.clicked.connect(apply_high_contrast_theme)
    font_scale_btn.clicked.connect(increase_font_scale)
    contrast_boost_btn.clicked.connect(toggle_contrast_boost)
    
    # 윈도우 표시
    window.show()
    
    # 기본 테마 적용
    theme_manager.apply(ThemeMode.LIGHT, A11yOptions())
    
    # 이벤트 루프 실행
    sys.exit(app.exec_())


if __name__ == "__main__":
    test_theme_system()
