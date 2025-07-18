"""
테마 관리 시스템

PyQt6 애플리케이션에서 다크 모드와 라이트 모드를 지원하는 테마 관리자입니다.
"""

import os
import sys
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QPalette, QColor


class ThemeMode(Enum):
    """테마 모드 열거형"""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"  # 시스템 설정 따라가기


class ThemeManager:
    """테마 관리자 클래스"""
    
    def __init__(self, settings: QSettings):
        """
        테마 관리자 초기화
        
        Args:
            settings: QSettings 인스턴스
        """
        self.settings = settings
        self.current_theme = ThemeMode.LIGHT
        self._load_theme_setting()
        
    def _load_theme_setting(self) -> None:
        """저장된 테마 설정 로드"""
        theme_name = self.settings.value("ui/theme", "light", str)
        try:
            self.current_theme = ThemeMode(theme_name)
        except ValueError:
            self.current_theme = ThemeMode.LIGHT
            
    def _save_theme_setting(self) -> None:
        """테마 설정 저장"""
        self.settings.setValue("ui/theme", self.current_theme.value)
        
    def get_current_theme(self) -> ThemeMode:
        """현재 테마 모드 반환"""
        return self.current_theme
        
    def set_theme(self, theme: ThemeMode) -> None:
        """
        테마 설정
        
        Args:
            theme: 설정할 테마 모드
        """
        self.current_theme = theme
        self._save_theme_setting()
        self._apply_theme(theme)
        
    def _apply_theme(self, theme: ThemeMode) -> None:
        """
        테마 적용
        
        Args:
            theme: 적용할 테마 모드
        """
        app = QApplication.instance()
        if app is None:
            return
            
        if theme == ThemeMode.SYSTEM:
            # 시스템 테마 감지
            theme = self._detect_system_theme()
            
        if theme == ThemeMode.DARK:
            self._apply_dark_theme(app)
        else:
            self._apply_light_theme(app)
            
    def _detect_system_theme(self) -> ThemeMode:
        """시스템 테마 감지"""
        if sys.platform == "win32":
            # Windows 시스템 테마 감지
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                   r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return ThemeMode.LIGHT if value == 1 else ThemeMode.DARK
            except:
                return ThemeMode.LIGHT
        else:
            # Linux/macOS는 기본적으로 라이트 모드
            return ThemeMode.LIGHT
            
    def _apply_dark_theme(self, app: QApplication) -> None:
        """다크 테마 적용"""
        # 팔레트 설정
        palette = QPalette()
        
        # 배경색
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        app.setPalette(palette)
        
        # 스타일시트 적용
        dark_stylesheet = """
        QMainWindow {
            background-color: #353535;
            color: #ffffff;
        }
        
        QWidget {
            background-color: #353535;
            color: #ffffff;
        }
        
        QGroupBox {
            background-color: #2a2a2a;
            border: 1px solid #555555;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        #progress-step {
            background-color: #232323;
            border: 1px solid #444444;
            border-radius: 4px;
        }
        #speed-meter, #eta-widget {
            background-color: #232323;
            border: 1px solid #444444;
            border-radius: 5px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #ffffff;
        }
        
        QPushButton {
            background-color: #2a2a2a;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 5px 15px;
            color: #ffffff;
        }
        
        QPushButton:hover {
            background-color: #3a3a3a;
            border: 1px solid #666666;
        }
        
        QPushButton:pressed {
            background-color: #1a1a1a;
        }
        
        QPushButton:disabled {
            background-color: #2a2a2a;
            color: #888888;
        }
        
        QLineEdit {
            background-color: #2a2a2a;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 5px;
            color: #ffffff;
        }
        
        QLineEdit:focus {
            border: 1px solid #42a2da;
        }
        
        QTableWidget {
            background-color: #2a2a2a;
            alternate-background-color: #3a3a3a;
            border: 1px solid #555555;
            gridline-color: #555555;
            color: #ffffff;
        }
        
        QTableWidget::item {
            padding: 5px;
        }
        
        QTableWidget::item:selected {
            background-color: #42a2da;
        }
        
        QHeaderView::section {
            background-color: #2a2a2a;
            border: 1px solid #555555;
            padding: 5px;
            color: #ffffff;
        }
        
        QProgressBar {
            border: 1px solid #555555;
            border-radius: 3px;
            text-align: center;
            background-color: #2a2a2a;
            color: #ffffff;
        }
        
        QProgressBar::chunk {
            background-color: #42a2da;
            border-radius: 2px;
        }
        
        QLabel {
            color: #ffffff;
        }
        
        QMenuBar {
            background-color: #2a2a2a;
            color: #ffffff;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 5px 10px;
        }
        
        QMenuBar::item:selected {
            background-color: #3a3a3a;
        }
        
        QMenu {
            background-color: #2a2a2a;
            border: 1px solid #555555;
            color: #ffffff;
        }
        
        QMenu::item {
            padding: 5px 20px;
        }
        
        QMenu::item:selected {
            background-color: #3a3a3a;
        }
        
        QDialog {
            background-color: #353535;
            color: #ffffff;
        }
        
        QMessageBox {
            background-color: #353535;
            color: #ffffff;
        }
        
        QScrollBar:vertical {
            background-color: #2a2a2a;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
        
        QScrollBar:horizontal {
            background-color: #2a2a2a;
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #555555;
            border-radius: 6px;
            min-width: 20px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #666666;
        }
        """
        
        app.setStyleSheet(dark_stylesheet)
        
    def _apply_light_theme(self, app: QApplication) -> None:
        """라이트 테마 적용"""
        # 팔레트 설정
        palette = QPalette()
        
        # 배경색
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        app.setPalette(palette)
        
        # 라이트 테마 스타일시트 적용
        light_stylesheet = """
        QMainWindow {
            background-color: #f0f0f0;
            color: #000000;
        }
        
        QWidget {
            background-color: #f0f0f0;
            color: #000000;
        }
        
        QGroupBox {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        #progress-step {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }
        #speed-meter, #eta-widget {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #000000;
        }
        
        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 5px 15px;
            color: #000000;
        }
        
        QPushButton:hover {
            background-color: #e0e0e0;
            border: 1px solid #bbbbbb;
        }
        
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
        
        QPushButton:disabled {
            background-color: #f0f0f0;
            color: #888888;
        }
        
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 5px;
            color: #000000;
        }
        
        QLineEdit:focus {
            border: 1px solid #42a2da;
        }
        
        QTableWidget {
            background-color: #ffffff;
            alternate-background-color: #f8f8f8;
            border: 1px solid #cccccc;
            gridline-color: #cccccc;
            color: #000000;
        }
        
        QTableWidget::item {
            padding: 5px;
        }
        
        QTableWidget::item:selected {
            background-color: #42a2da;
            color: #ffffff;
        }
        
        QHeaderView::section {
            background-color: #f0f0f0;
            border: 1px solid #cccccc;
            padding: 5px;
            color: #000000;
        }
        
        QProgressBar {
            border: 1px solid #cccccc;
            border-radius: 3px;
            text-align: center;
            background-color: #f0f0f0;
            color: #000000;
        }
        
        QProgressBar::chunk {
            background-color: #42a2da;
            border-radius: 2px;
        }
        
        QLabel {
            color: #000000;
        }
        
        QMenuBar {
            background-color: #f0f0f0;
            color: #000000;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 5px 10px;
        }
        
        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }
        
        QMenu {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            color: #000000;
        }
        
        QMenu::item {
            padding: 5px 20px;
        }
        
        QMenu::item:selected {
            background-color: #e0e0e0;
        }
        
        QMenu::separator {
            height: 1px;
            background-color: #cccccc;
            margin: 5px 0px;
        }
        
        QDialog {
            background-color: #f0f0f0;
            color: #000000;
        }
        
        QMessageBox {
            background-color: #f0f0f0;
            color: #000000;
        }
        
        QScrollBar:vertical {
            background-color: #f0f0f0;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #cccccc;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #bbbbbb;
        }
        
        QScrollBar:horizontal {
            background-color: #f0f0f0;
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #cccccc;
            border-radius: 6px;
            min-width: 20px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #bbbbbb;
        }
        
        QComboBox {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 5px;
            color: #000000;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #000000;
        }
        
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            color: #000000;
        }
        
        QComboBox QAbstractItemView::item:hover {
            background-color: #e0e0e0;
        }
        
        QComboBox QAbstractItemView::item:selected {
            background-color: #42a2da;
            color: #ffffff;
        }
        
        QCheckBox {
            color: #000000;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        
        QCheckBox::indicator:unchecked {
            border: 1px solid #cccccc;
            background-color: #ffffff;
        }
        
        QCheckBox::indicator:checked {
            border: 1px solid #42a2da;
            background-color: #42a2da;
        }
        
        QRadioButton {
            color: #000000;
        }
        
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
        }
        
        QRadioButton::indicator:unchecked {
            border: 1px solid #cccccc;
            background-color: #ffffff;
            border-radius: 8px;
        }
        
        QRadioButton::indicator:checked {
            border: 1px solid #42a2da;
            background-color: #42a2da;
            border-radius: 8px;
        }
        
        QTextEdit {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            color: #000000;
        }
        
        QPlainTextEdit {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            color: #000000;
        }
        
        QListWidget {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            color: #000000;
        }
        
        QListWidget::item {
            padding: 5px;
        }
        
        QListWidget::item:selected {
            background-color: #42a2da;
            color: #ffffff;
        }
        
        QTreeWidget {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            color: #000000;
        }
        
        QTreeWidget::item {
            padding: 5px;
        }
        
        QTreeWidget::item:selected {
            background-color: #42a2da;
            color: #ffffff;
        }
        """
        
        app.setStyleSheet(light_stylesheet)
            
    def toggle_theme(self) -> None:
        """테마 토글 (라이트 ↔ 다크)"""
        if self.current_theme == ThemeMode.LIGHT:
            self.set_theme(ThemeMode.DARK)
        elif self.current_theme == ThemeMode.DARK:
            self.set_theme(ThemeMode.LIGHT)
        else:
            # SYSTEM 모드인 경우 현재 시스템 테마의 반대
            system_theme = self._detect_system_theme()
            opposite_theme = ThemeMode.DARK if system_theme == ThemeMode.LIGHT else ThemeMode.LIGHT
            self.set_theme(opposite_theme)
            
    def refresh_theme(self) -> None:
        """테마 새로고침 (시스템 테마 변경 감지용)"""
        self._apply_theme(self.current_theme)


def create_theme_manager(settings: QSettings) -> ThemeManager:
    """
    테마 관리자 생성 (편의 함수)
    
    Args:
        settings: QSettings 인스턴스
        
    Returns:
        ThemeManager: 테마 관리자 인스턴스
    """
    return ThemeManager(settings) 