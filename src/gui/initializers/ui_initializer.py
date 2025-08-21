#!/usr/bin/env python3
"""
UI Initializer for MainWindow

MainWindow의 UI 초기화 로직을 관리하는 클래스입니다.
UI 컴포넌트 생성, 레이아웃 설정, 메뉴/툴바 생성을 담당합니다.
"""

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel,
    QMainWindow,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..builders.menu_builder import MenuBuilder
from ..builders.toolbar_builder import ToolbarBuilder


class UIInitializer:
    """MainWindow의 UI 초기화를 담당하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        """UIInitializer 초기화"""
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # 빌더들 초기화
        self.menu_builder = MenuBuilder(main_window)
        self.toolbar_builder = ToolbarBuilder(main_window)

    def init_ui(self):
        """UI 초기화 메인 메서드"""
        try:
            self.logger.info("UI 초기화 시작")

            # 기본 윈도우 설정
            self.setup_basic_window()

            # 중앙 위젯 설정
            self.setup_central_widget()

            # 메뉴바 생성
            self.create_menu_bar()

            # 툴바 생성
            self.create_toolbar()

            # 상태바 설정
            self.create_status_bar()

            # 레이아웃 설정
            self.setup_layout()

            # 스플리터 설정
            self.setup_splitters()

            self.logger.info("UI 초기화 완료")

        except Exception as e:
            self.logger.error(f"UI 초기화 실패: {e}")
            raise

    def setup_basic_window(self):
        """기본 윈도우 설정"""
        try:
            # 윈도우 제목 및 크기 설정
            self.main_window.setWindowTitle("AnimeSorter v2.0.0 - 애니메이션 파일 정리 도구")
            self.main_window.setMinimumSize(1200, 800)
            self.main_window.resize(1600, 1000)

            self.logger.debug("기본 윈도우 설정 완료")

        except Exception as e:
            self.logger.error(f"기본 윈도우 설정 실패: {e}")
            raise

    def setup_central_widget(self):
        """중앙 위젯 설정"""
        try:
            # 중앙 위젯 생성
            central_widget = QWidget()
            self.main_window.setCentralWidget(central_widget)

            # 메인 레이아웃 설정
            parent_layout = QVBoxLayout(central_widget)
            parent_layout.setSpacing(10)
            parent_layout.setContentsMargins(10, 10, 10, 10)

            # 레이아웃을 main_window에 저장
            self.main_window.parent_layout = parent_layout
            self.main_window.central_widget = central_widget

            self.logger.debug("중앙 위젯 설정 완료")

        except Exception as e:
            self.logger.error(f"중앙 위젯 설정 실패: {e}")
            raise

    def create_menu_bar(self):
        """메뉴바 생성"""
        try:
            self.menu_builder.create_menu_bar()
            self.logger.debug("메뉴바 생성 완료")

        except Exception as e:
            self.logger.error(f"메뉴바 생성 실패: {e}")
            raise

    def create_toolbar(self):
        """툴바 생성"""
        try:
            # MainToolbar 생성
            from ..components import MainToolbar

            self.main_window.main_toolbar = MainToolbar()

            # 기본 툴바도 생성 (백업용)
            self.toolbar_builder.create_toolbar()

            self.logger.debug("툴바 생성 완료")

        except Exception as e:
            self.logger.error(f"툴바 생성 실패: {e}")
            raise

    def create_status_bar(self):
        """상태바 설정"""
        try:
            # 상태바 생성
            status_bar = self.main_window.statusBar()

            # 기본 상태 메시지
            self.main_window.status_label = QLabel("준비됨")
            status_bar.addWidget(self.main_window.status_label)

            # 진행률 표시
            status_bar.addPermanentWidget(QLabel("진행률:"))
            self.main_window.status_progress = QProgressBar()
            self.main_window.status_progress.setMaximumWidth(200)
            self.main_window.status_progress.setMaximumHeight(20)
            status_bar.addPermanentWidget(self.main_window.status_progress)

            # 파일 수 표시
            self.main_window.status_file_count = QLabel("파일: 0")
            status_bar.addPermanentWidget(self.main_window.status_file_count)

            # 메모리 사용량 표시
            self.main_window.status_memory = QLabel("메모리: 0MB")
            status_bar.addPermanentWidget(self.main_window.status_memory)

            # 초기 상태 설정
            self.main_window.update_status_bar("애플리케이션이 준비되었습니다")

            self.logger.debug("상태바 설정 완료")

        except Exception as e:
            self.logger.error(f"상태바 설정 실패: {e}")
            raise

    def setup_layout(self):
        """레이아웃 설정"""
        try:
            # 메인 레이아웃에 기본 컴포넌트들 추가
            parent_layout = self.main_window.parent_layout

            # 메인 툴바 추가
            if hasattr(self.main_window, "main_toolbar"):
                parent_layout.addWidget(self.main_window.main_toolbar)

            self.logger.debug("레이아웃 설정 완료")

        except Exception as e:
            self.logger.error(f"레이아웃 설정 실패: {e}")
            raise

    def setup_splitters(self):
        """스플리터 설정"""
        try:
            parent_layout = self.main_window.parent_layout

            # 메인 스플리터 생성 (좌우 분할)
            splitter = QSplitter(Qt.Horizontal)
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(8)

            # 패널들을 생성하고 추가
            self.create_panels(splitter)

            # 스플리터 비율 설정 (반응형)
            splitter.setSizes([400, 1200])
            splitter.setStretchFactor(0, 0)  # 왼쪽 패널은 고정 크기
            splitter.setStretchFactor(1, 1)  # 오른쪽 패널은 확장 가능

            # 레이아웃에 스플리터 추가
            parent_layout.addWidget(splitter)

            # 스플리터를 main_window에 저장
            self.main_window.main_splitter = splitter

            self.logger.debug("스플리터 설정 완료")

        except Exception as e:
            self.logger.error(f"스플리터 설정 실패: {e}")
            raise

    def create_panels(self, splitter):
        """패널들 생성"""
        try:
            # UI Components import 추가
            from ..components import LeftPanel, ResultsView, RightPanel

            # 왼쪽 패널: 빠른 작업, 통계, 필터
            self.main_window.left_panel = LeftPanel()
            self.main_window.left_panel.setMinimumWidth(350)
            self.main_window.left_panel.setMaximumWidth(500)
            splitter.addWidget(self.main_window.left_panel)

            # 오른쪽 패널: 결과 및 로그
            self.main_window.right_panel = RightPanel()
            splitter.addWidget(self.main_window.right_panel)

            # 결과 뷰 생성 (그룹 리스트 중심)
            self.main_window.results_view = ResultsView()
            self.main_window.right_panel.layout().addWidget(self.main_window.results_view)

            # 모델들 초기화
            self.setup_models()

            self.logger.debug("패널들 생성 완료")

        except Exception as e:
            self.logger.error(f"패널 생성 실패: {e}")
            raise

    def setup_models(self):
        """모델들 초기화"""
        try:
            # 모델 import
            from ..table_models import DetailFileModel, GroupedListModel

            # 대상 폴더 정보 가져오기
            destination_directory = ""
            if hasattr(self.main_window, "settings_manager"):
                destination_directory = self.main_window.settings_manager.get_setting(
                    "destination_root", "대상 폴더"
                )

            # 모델들 생성
            tmdb_client = getattr(self.main_window, "tmdb_client", None)

            self.main_window.grouped_model = GroupedListModel(
                {}, tmdb_client, destination_directory
            )  # 그룹 리스트용
            self.main_window.detail_model = DetailFileModel([], tmdb_client)  # 상세 파일 목록용

            # 결과 뷰에 모델 설정
            if hasattr(self.main_window, "results_view"):
                self.main_window.results_view.set_group_model(self.main_window.grouped_model)
                self.main_window.results_view.set_detail_model(self.main_window.detail_model)

                # 그룹 선택 시 상세 파일 목록 업데이트
                self.main_window.results_view.group_selected.connect(
                    self.main_window.on_group_selected
                )

            self.logger.debug("모델들 초기화 완료")

        except Exception as e:
            self.logger.error(f"모델 초기화 실패: {e}")
            raise

    def setup_connections(self):
        """UI 연결 설정"""
        try:
            # 기본 시그널/슬롯 연결
            # (필요한 경우 여기에 추가)

            self.logger.debug("UI 연결 설정 완료")

        except Exception as e:
            self.logger.error(f"UI 연결 설정 실패: {e}")
            raise
