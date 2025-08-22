#!/usr/bin/env python3
"""
Toolbar Builder for MainWindow

MainWindow의 툴바 생성을 담당하는 클래스입니다.
툴바 버튼들과 액션들을 체계적으로 관리합니다.
"""

import logging

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
            # MainToolbar 클래스가 이미 존재한다고 가정
            # 실제로는 MainToolbar 클래스를 import하거나 여기서 직접 생성해야 함
            if hasattr(self.main_window, "main_toolbar"):
                self.logger.debug("기존 툴바가 이미 존재합니다")
                return

            # MainToolbar가 없는 경우를 위한 기본 툴바 생성
            self.create_basic_toolbar()

            self.logger.debug("툴바 생성 완료")

        except Exception as e:
            self.logger.error(f"툴바 생성 실패: {e}")
            raise

    def create_basic_toolbar(self):
        """기본 툴바 생성 (MainToolbar가 없는 경우)"""
        try:
            # 기본 툴바 생성
            toolbar = self.main_window.addToolBar("메인 툴바")
            toolbar.setMovable(False)  # 툴바 이동 불가

            # 파일 선택 액션
            open_files_action = toolbar.addAction("파일 선택")
            open_files_action.setStatusTip("애니메이션 파일을 선택합니다")
            open_files_action.triggered.connect(self.main_window.choose_files)

            open_folder_action = toolbar.addAction("폴더 선택")
            open_folder_action.setStatusTip("애니메이션 파일이 있는 폴더를 선택합니다")
            open_folder_action.triggered.connect(self.main_window.choose_folder)

            toolbar.addSeparator()

            # 스캔 액션
            start_scan_action = toolbar.addAction("스캔 시작")
            start_scan_action.setStatusTip("파일 스캔을 시작합니다")
            start_scan_action.triggered.connect(self.main_window.start_scan)

            stop_scan_action = toolbar.addAction("스캔 중지")
            stop_scan_action.setStatusTip("파일 스캔을 중지합니다")
            stop_scan_action.triggered.connect(self.main_window.stop_scan)

            toolbar.addSeparator()

            # 정리 액션
            commit_action = toolbar.addAction("정리 실행")
            commit_action.setStatusTip("파일 정리를 실행합니다")
            commit_action.triggered.connect(self.main_window.commit_organization)

            toolbar.addSeparator()

            # 설정 액션
            settings_action = toolbar.addAction("설정")
            settings_action.setStatusTip("애플리케이션 설정을 변경합니다")
            settings_action.triggered.connect(self.main_window.show_settings_dialog)

            # 툴바를 main_window에 저장
            self.main_window.main_toolbar = toolbar

        except Exception as e:
            self.logger.error(f"기본 툴바 생성 실패: {e}")
            raise
