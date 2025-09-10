"""
Toolbar Builder for MainWindow

MainWindow의 툴바 생성을 담당하는 클래스입니다.
툴바 버튼들과 액션들을 체계적으로 관리합니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import QMainWindow


class ToolbarBuilder:
    """MainWindow의 툴바 생성을 담당하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        """ToolbarBuilder 초기화"""
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def create_toolbar(self):
        """툴바 생성"""
        try:
            if hasattr(self.main_window, "main_toolbar"):
                self.logger.debug("기존 툴바가 이미 존재합니다")
                return
            self.create_basic_toolbar()
            self.logger.debug("툴바 생성 완료")
        except Exception as e:
            self.logger.error(f"툴바 생성 실패: {e}")
            raise

    def create_basic_toolbar(self):
        """기본 툴바 생성 (MainToolbar가 없는 경우)"""
        try:
            toolbar = self.main_window.addToolBar("메인 툴바")
            toolbar.setMovable(False)
            open_files_action = toolbar.addAction("파일 선택")
            open_files_action.setStatusTip("애니메이션 파일을 선택합니다")
            open_files_action.triggered.connect(self.main_window.choose_files)
            open_folder_action = toolbar.addAction("폴더 선택")
            open_folder_action.setStatusTip("애니메이션 파일이 있는 폴더를 선택합니다")
            open_folder_action.triggered.connect(self.main_window.choose_folder)
            toolbar.addSeparator()
            start_scan_action = toolbar.addAction("스캔 시작")
            start_scan_action.setStatusTip("파일 스캔을 시작합니다")
            start_scan_action.triggered.connect(self.main_window.start_scan)
            stop_scan_action = toolbar.addAction("스캔 중지")
            stop_scan_action.setStatusTip("파일 스캔을 중지합니다")
            stop_scan_action.triggered.connect(self.main_window.stop_scan)
            toolbar.addSeparator()
            commit_action = toolbar.addAction("정리 실행")
            commit_action.setStatusTip("파일 정리를 실행합니다")
            commit_action.triggered.connect(self.main_window.commit_organization)
            toolbar.addSeparator()
            settings_action = toolbar.addAction("설정")
            settings_action.setStatusTip("애플리케이션 설정을 변경합니다")
            settings_action.triggered.connect(self.main_window.show_settings_dialog)
            self.main_window.main_toolbar = toolbar
        except Exception as e:
            self.logger.error(f"기본 툴바 생성 실패: {e}")
            raise
