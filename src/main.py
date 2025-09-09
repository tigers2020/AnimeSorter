#!/usr/bin/env python3
"""
AnimeSorter 메인 실행 파일

이 파일은 AnimeSorter 애플리케이션의 진입점입니다.
PyQt5 기반 GUI 애플리케이션을 초기화하고 실행합니다.
"""

import sys
from pathlib import Path

# 절대 import로 변경 (런타임에서 상대 import 문제 해결)
from PyQt5.QtWidgets import QApplication

import src.app.setup as setup_module
import src.gui.main_window as main_window_module

# src 디렉토리를 Python 경로에 추가
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

cleanup_application = setup_module.cleanup_application
initialize_application = setup_module.initialize_application
MainWindow = main_window_module.MainWindow


def main():
    """메인 애플리케이션 실행 함수"""
    # PyQt5 애플리케이션 초기화
    app = QApplication(sys.argv)
    app.setApplicationName("AnimeSorter")
    app.setApplicationVersion("2.0.0")

    # 애플리케이션 설정 초기화
    initialize_application()

    try:
        # 메인 윈도우 생성 및 표시
        main_window = MainWindow()
        main_window.show()

        # 애플리케이션 실행
        sys.exit(app.exec_())

    finally:
        # 애플리케이션 정리
        cleanup_application()


if __name__ == "__main__":
    main()
