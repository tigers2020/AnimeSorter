#!/usr/bin/env python3
"""
AnimeSorter - PyQt5 기반 애니메이션 파일 정리 도구

메인 애플리케이션 진입점
사용자 친화적인 GUI와 직관적인 컨트롤을 제공합니다.
"""

import sys
import os
from pathlib import Path

# PyQt5 imports
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Local imports
from gui.main_window import MainWindow


def setup_application_style():
    """애플리케이션 전역 스타일 설정"""
    app = QApplication.instance()
    
    # 기본 폰트 설정
    default_font = QFont("Segoe UI", 9)  # Windows 기본 폰트
    app.setFont(default_font)
    
    # 애플리케이션 스타일시트
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f8f9fa;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: white;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #495057;
        }
        
        QTableView {
            background-color: white;
            alternate-background-color: #f8f9fa;
            gridline-color: #dee2e6;
            selection-background-color: #007bff;
            selection-color: white;
        }
        
        QTreeWidget {
            background-color: white;
            alternate-background-color: #f8f9fa;
            border: 1px solid #dee2e6;
        }
        
        QTabWidget::pane {
            border: 1px solid #dee2e6;
            background-color: white;
        }
        
        QTabBar::tab {
            background-color: #e9ecef;
            border: 1px solid #dee2e6;
            padding: 8px 16px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            border-bottom-color: white;
        }
        
        QTextEdit {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }
        
        QLineEdit {
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 6px 8px;
            background-color: white;
        }
        
        QLineEdit:focus {
            border-color: #007bff;
            outline: none;
        }
        
        QComboBox {
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 6px 8px;
            background-color: white;
        }
        
        QComboBox:focus {
            border-color: #007bff;
        }
        
        QProgressBar {
            border: 1px solid #ced4da;
            border-radius: 4px;
            text-align: center;
            background-color: #e9ecef;
        }
        
        QProgressBar::chunk {
            background-color: #007bff;
            border-radius: 3px;
        }
    """)


def main():
    """메인 애플리케이션 함수"""
    # QApplication 인스턴스 생성
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("AnimeSorter")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("AnimeSorter")
    app.setApplicationDisplayName("AnimeSorter - 애니메이션 파일 정리 도구")
    
    # 전역 스타일 설정
    setup_application_style()
    
    # 메인 윈도우 생성 및 표시
    main_window = MainWindow()
    main_window.show()
    
    # 이벤트 루프 시작
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
