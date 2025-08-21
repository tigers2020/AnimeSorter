#!/usr/bin/env python3
"""
AnimeSorter - PyQt5 기반 애니메이션 파일 정리 도구

메인 애플리케이션 진입점
사용자 친화적인 GUI와 직관적인 컨트롤을 제공합니다.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt

# PyQt5 imports
from PyQt5.QtWidgets import QApplication

from app import cleanup_application, initialize_application

# Local imports
from gui.main_window import MainWindow


def setup_logging():
    """로깅 시스템 설정"""
    try:
        # 기존 핸들러 제거 (테스트 환경에서 안정성을 위해)
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()  # 핸들러를 명시적으로 닫기
            root_logger.removeHandler(handler)

        # 로그 디렉토리 생성
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # 로그 파일명 (날짜별)
        log_filename = log_dir / f"animesorter_{datetime.now().strftime('%Y%m%d')}.log"

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_filename, encoding="utf-8", mode="a"),
                logging.StreamHandler(sys.stdout),
            ],
            force=True,  # 기존 설정을 강제로 덮어쓰기
        )

        # 특정 모듈의 로그 레벨 조정
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

        # 로그 메시지 기록 및 즉시 플러시
        logging.info("로깅 시스템 초기화 완료")
        logging.info(f"로그 파일: {log_filename}")

        # 핸들러에 즉시 플러시
        for handler in logging.getLogger().handlers:
            handler.flush()

        # 로깅 시스템이 제대로 작동하는지 확인
        test_logger = logging.getLogger("animesorter.test")
        test_logger.info("로깅 시스템 테스트 메시지")

        # 모든 핸들러에 즉시 플러시
        for handler in logging.getLogger().handlers:
            handler.flush()

        # 파일이 실제로 생성되었는지 확인
        if not log_filename.exists():
            # 파일이 생성되지 않았으면 다시 시도
            logging.info("로그 파일 재생성 시도")
            for handler in logging.getLogger().handlers:
                handler.flush()

    except Exception as e:
        print(f"로깅 설정 실패: {e}")
        # 기본 로깅 설정
        logging.basicConfig(level=logging.INFO, force=True)


def setup_application_style():
    """애플리케이션 전역 스타일 설정"""
    app = QApplication.instance()

    # 기본 폰트 설정
    default_font = QApplication.font()  # Windows 기본 폰트
    app.setFont(default_font)

    # 애플리케이션 스타일시트
    app.setStyleSheet(
        """
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
    """
    )


def main():
    """메인 애플리케이션 함수"""
    # 로깅 시스템 초기화
    setup_logging()

    # High DPI 설정 (QApplication 생성 이전에 설정해야 함)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # QApplication 인스턴스 생성
    app = QApplication(sys.argv)

    # 애플리케이션 정보 설정
    app.setApplicationName("AnimeSorter")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("AnimeSorter")
    app.setApplicationDisplayName("AnimeSorter - 애니메이션 파일 정리 도구")

    # 전역 스타일 설정
    setup_application_style()

    try:
        # 애플리케이션 초기화 (DI Container, EventBus 등)
        initialize_application()

        # 메인 윈도우 생성 및 표시
        main_window = MainWindow()
        main_window.show()

        # 이벤트 루프 시작
        exit_code = app.exec_()

    finally:
        # 애플리케이션 정리
        cleanup_application()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
