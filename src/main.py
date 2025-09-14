"""
AnimeSorter 메인 실행 파일

이 파일은 AnimeSorter 애플리케이션의 진입점입니다.
PyQt5 기반 GUI 애플리케이션을 초기화하고 실행합니다.
"""

import logging
import sys

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)
from pathlib import Path

from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication

import src.app.setup as setup_module
import src.gui.main_window as main_window_module

src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))
cleanup_application = setup_module.cleanup_application
initialize_application = setup_module.initialize_application
MainWindow = main_window_module.MainWindow


def load_common_stylesheet(app: QApplication) -> None:
    """
    공통 스타일시트를 로드하고 적용합니다.

    Args:
        app: QApplication 인스턴스
    """
    try:
        # 공통 스타일시트 파일 경로
        stylesheet_path = src_path / "gui" / "styles" / "common_styles.qss"

        if not stylesheet_path.exists():
            logger.warning(f"공통 스타일시트 파일을 찾을 수 없습니다: {stylesheet_path}")
            return

        # QFile을 사용하여 스타일시트 파일 읽기
        file = QFile(str(stylesheet_path))
        if file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(file)
            stylesheet_content = stream.readAll()
            file.close()

            # 현재 스타일시트에 공통 스타일시트 추가
            current_style = app.styleSheet()
            if current_style:
                combined_style = current_style + "\n" + stylesheet_content
            else:
                combined_style = stylesheet_content

            app.setStyleSheet(combined_style)
            logger.info("공통 스타일시트가 성공적으로 로드되었습니다")
        else:
            logger.error(f"스타일시트 파일을 열 수 없습니다: {stylesheet_path}")

    except Exception as e:
        logger.error(f"공통 스타일시트 로드 실패: {e}")


def main():
    """메인 애플리케이션 실행 함수"""
    app = QApplication(sys.argv)
    app.setApplicationName("AnimeSorter")
    app.setApplicationVersion("2.0.0")
    initialize_application()

    # 공통 스타일시트 로드
    load_common_stylesheet(app)

    try:
        main_window = MainWindow()
        main_window.show()
        sys.exit(app.exec_())
    finally:
        cleanup_application()


if __name__ == "__main__":
    main()
