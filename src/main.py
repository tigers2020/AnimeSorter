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

from PyQt5.QtWidgets import QApplication

import src.app.setup as setup_module
import src.gui.main_window as main_window_module

src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))
cleanup_application = setup_module.cleanup_application
initialize_application = setup_module.initialize_application
MainWindow = main_window_module.MainWindow


def main():
    """메인 애플리케이션 실행 함수"""
    app = QApplication(sys.argv)
    app.setApplicationName("AnimeSorter")
    app.setApplicationVersion("2.0.0")
    initialize_application()
    try:
        main_window = MainWindow()
        main_window.show()
        sys.exit(app.exec_())
    finally:
        cleanup_application()


if __name__ == "__main__":
    main()
