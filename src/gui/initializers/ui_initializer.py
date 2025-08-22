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

            # LeftPanel 초기화 (MainWindow 참조 설정 및 디렉토리 설정 복원)
            self.initialize_left_panel()

            self.logger.info("UI 초기화 완료")

        except Exception as e:
            self.logger.error(f"UI 초기화 실패: {e}")
            raise

    def initialize_left_panel(self):
        """LeftPanel 초기화 - MainWindow 참조 설정 및 디렉토리 설정 복원"""
        try:
            # LeftPanel에 MainWindow 참조 설정
            self.main_window.left_panel.set_main_window(self.main_window)

            # 저장된 디렉토리 설정 복원
            self.main_window.left_panel.restore_directory_settings()

            self.logger.debug("LeftPanel 초기화 완료")

        except Exception as e:
            self.logger.error(f"LeftPanel 초기화 실패: {e}")
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
            # MainToolbar 생성 (새로운 Phase 1 디자인)
            from ..components import MainToolbar

            self.main_window.main_toolbar = MainToolbar()

            # 기본 툴바도 생성 (백업용)
            self.toolbar_builder.create_toolbar()

            # 툴바 시그널 연결
            self.connect_toolbar_signals()

            self.logger.debug("툴바 생성 완료")

        except Exception as e:
            self.logger.error(f"툴바 생성 실패: {e}")
            raise

    def connect_toolbar_signals(self):
        """툴바 시그널 연결"""
        try:
            if hasattr(self.main_window, "main_toolbar") and self.main_window.main_toolbar:
                toolbar = self.main_window.main_toolbar

                # 스캔 요청 연결
                toolbar.scan_requested.connect(self.main_window.on_scan_requested)

                # 미리보기 요청 연결
                toolbar.preview_requested.connect(self.main_window.on_preview_requested)

                # 정리 실행 요청 연결
                toolbar.organize_requested.connect(self.main_window.on_organize_requested)

                # 검색 텍스트 변경 연결
                toolbar.search_text_changed.connect(self.main_window.on_search_text_changed)

                # 설정 요청 연결
                toolbar.settings_requested.connect(self.main_window.on_settings_requested)

                self.logger.debug("툴바 시그널 연결 완료")

        except Exception as e:
            self.logger.error(f"툴바 시그널 연결 실패: {e}")
            # 연결 실패 시에도 계속 진행

    def create_status_bar(self):
        """상태바 설정"""
        try:
            # 상태바 생성
            status_bar = self.main_window.statusBar()

            # 기본 상태 메시지
            self.main_window.status_label = QLabel("준비됨")
            status_bar.addWidget(self.main_window.status_label)

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

            # 메인 스플리터 생성 (오른쪽 패널만 포함, 왼쪽은 Dock으로 처리)
            splitter = QSplitter(Qt.Horizontal)
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(8)

            # 패널들을 생성하고 추가 (왼쪽 패널은 Dock으로 별도 처리)
            self.create_panels(splitter)

            # 스플리터 비율 설정 (오른쪽 패널만 포함)
            splitter.setSizes([1200])  # 오른쪽 패널만
            splitter.setStretchFactor(0, 1)  # 오른쪽 패널은 확장 가능

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
            from ..components import LeftPanelDock, ResultsView
            from ..components.central_triple_layout import CentralTripleLayout

            # 왼쪽 패널: 빠른 작업, 통계, 필터 (Dock으로 변경)
            self.main_window.left_panel_dock = LeftPanelDock()

            # Dock을 MainWindow에 추가 (QSplitter 대신)
            self.main_window.addDockWidget(Qt.LeftDockWidgetArea, self.main_window.left_panel_dock)

            # 기존 left_panel 참조도 유지 (호환성)
            self.main_window.left_panel = self.main_window.left_panel_dock.left_panel

            # LeftPanel에 MainWindow 참조 설정
            self.main_window.left_panel.set_main_window(self.main_window)

            # 저장된 디렉토리 설정 복원
            self.main_window.left_panel.restore_directory_settings()

            # 기존 ResultsView 생성 (모델 및 데이터 관리용)
            self.main_window.results_view = ResultsView()

            # 3열 레이아웃 생성 (기존 오른쪽 패널 대체)
            self.main_window.central_triple_layout = CentralTripleLayout()

            # ResultsView가 완전히 초기화된 후에 모델 연결을 시도
            # QTimer.singleShot을 사용하여 다음 이벤트 루프에서 실행
            from PyQt5.QtCore import QTimer

            QTimer.singleShot(0, self.setup_triple_layout_models)

            # 3열 레이아웃을 스플리터에 추가
            splitter.addWidget(self.main_window.central_triple_layout)

            # 로그 Dock은 MainWindow.__init__에서 이미 설정됨 (Phase 5)
            # 여기서는 참조만 확인
            if not hasattr(self.main_window, "log_dock"):
                print("⚠️ 로그 Dock이 설정되지 않았습니다. MainWindow.__init__을 확인하세요.")

            # 모델들 초기화
            self.setup_models()

            self.logger.debug("패널들 생성 완료")

        except Exception as e:
            self.logger.error(f"패널 생성 실패: {e}")
            raise

    def setup_triple_layout_models(self):
        """3열 레이아웃에 기존 모델들 연결"""
        try:
            # ResultsView에서 모델들을 가져와서 3열 레이아웃에 연결
            results_view = self.main_window.results_view

            # 그룹 테이블 모델 연결 (기본적으로 '전체' 탭의 그룹 테이블 사용)
            if hasattr(results_view, "all_group_table") and results_view.all_group_table.model():
                self.main_window.central_triple_layout.set_group_table_model(
                    results_view.all_group_table.model()
                )
                self.logger.debug("그룹 테이블 모델 연결 완료")
            else:
                self.logger.warning("그룹 테이블 모델을 찾을 수 없습니다")

            # 파일 테이블 모델 연결 (기본적으로 '전체' 탭의 상세 테이블 사용)
            if hasattr(results_view, "all_detail_table") and results_view.all_detail_table.model():
                self.main_window.central_triple_layout.set_file_table_model(
                    results_view.all_detail_table.model()
                )
                self.logger.debug("파일 테이블 모델 연결 완료")
            else:
                self.logger.warning("파일 테이블 모델을 찾을 수 없습니다")

            # 그룹 선택 시그널 연결
            if hasattr(results_view, "group_selected"):
                results_view.group_selected.connect(self.on_group_selected)

            # 3열 레이아웃의 그룹 테이블 선택 시그널 연결
            self.main_window.central_triple_layout.connect_group_selection(
                self.on_group_selection_changed
            )

            # 상세 패널 업데이트를 위한 시그널 연결
            self.main_window.central_triple_layout.group_selection_changed.connect(
                self.on_group_selected
            )

            # 툴바 토글 시그널 연결
            if hasattr(self.main_window, "main_toolbar"):
                toolbar = self.main_window.main_toolbar
                toolbar.detail_panel_toggled.connect(self.on_detail_panel_toggled)
                toolbar.file_panel_toggled.connect(self.on_file_panel_toggled)

            self.logger.debug("3열 레이아웃 모델 연결 완료")

        except Exception as e:
            self.logger.error(f"3열 레이아웃 모델 연결 실패: {e}")

    def on_detail_panel_toggled(self, visible: bool):
        """상세 패널 토글 처리"""
        try:
            if hasattr(self.main_window, "central_triple_layout"):
                self.main_window.central_triple_layout.set_detail_visible(visible, user_toggle=True)
        except Exception as e:
            self.logger.error(f"상세 패널 토글 처리 실패: {e}")

    def on_file_panel_toggled(self, visible: bool):
        """파일 패널 토글 처리"""
        try:
            if hasattr(self.main_window, "central_triple_layout"):
                self.main_window.central_triple_layout.set_file_visible(visible, user_toggle=True)
        except Exception as e:
            self.logger.error(f"파일 패널 토글 처리 실패: {e}")

    def on_group_selected(self, group_data):
        """그룹 선택 시 상세 패널 업데이트"""
        try:
            if hasattr(self.main_window, "central_triple_layout"):
                self.main_window.central_triple_layout.update_detail_from_group(group_data)
        except Exception as e:
            self.logger.error(f"그룹 선택 처리 실패: {e}")

    def on_group_selection_changed(self, current_index):
        """그룹 선택 변경 시 상세 패널 업데이트"""
        try:
            if hasattr(self.main_window, "central_triple_layout") and current_index.isValid():
                # 그룹 데이터 추출 (기존 로직 활용)
                group_data = self.extract_group_data_from_index(current_index)
                self.main_window.central_triple_layout.update_detail_from_group(group_data)

                # 선택된 그룹의 파일들을 파일 테이블에 표시
                self.update_file_table_for_group(current_index)
        except Exception as e:
            self.logger.error(f"그룹 선택 변경 처리 실패: {e}")

    def extract_group_data_from_index(self, index):
        """인덱스에서 그룹 데이터 추출"""
        try:
            # MainWindow의 grouped_model에서 직접 그룹 정보 가져오기
            if hasattr(self.main_window, "grouped_model") and self.main_window.grouped_model:
                grouped_model = self.main_window.grouped_model
                if hasattr(grouped_model, "get_group_at_row"):
                    group_info = grouped_model.get_group_at_row(index.row())
                    if group_info:
                        print(f"✅ 그룹 데이터 추출 성공: {group_info.get('title', 'Unknown')}")

                        # TMDB 매치 정보 포함하여 반환
                        group_data = {
                            "title": group_info.get("title", "제목 없음"),
                            "original_title": group_info.get("original_title", "원제 없음"),
                            "season": group_info.get("season", "시즌 정보 없음"),
                            "episode_count": group_info.get("episode_count", 0),
                            "status": group_info.get("status", "상태 정보 없음"),
                            "file_count": group_info.get("file_count", 0),
                            "total_size": group_info.get("total_size", "0 B"),
                            "tmdb_match": group_info.get("tmdb_match"),  # TMDB 매치 정보 포함
                            "tags": group_info.get("tags", []),
                        }

                        return group_data

            # 기존 ResultsView의 로직을 활용하여 그룹 데이터 추출 (fallback)
            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view
                if hasattr(results_view, "extract_group_data_from_index"):
                    return results_view.extract_group_data_from_index(index)

            # 최후의 수단: 모델에서 직접 데이터 추출
            model = index.model()
            if model:
                return {
                    "title": model.data(model.index(index.row(), 0), Qt.DisplayRole),
                    "original_title": model.data(model.index(index.row(), 1), Qt.DisplayRole),
                    "season": model.data(model.index(index.row(), 2), Qt.DisplayRole),
                    "episode_count": model.data(model.index(index.row(), 3), Qt.DisplayRole),
                    "status": model.data(model.index(index.row(), 4), Qt.DisplayRole),
                    "file_count": model.data(model.index(index.row(), 5), Qt.DisplayRole),
                    "total_size": model.data(model.index(index.row(), 6), Qt.DisplayRole),
                    "tmdb_match": None,  # TMDB 매치 정보 없음
                    "tags": [],
                }

            return {}

        except Exception as e:
            self.logger.error(f"그룹 데이터 추출 실패: {e}")
            return {}

    def update_file_table_for_group(self, group_index):
        """선택된 그룹의 파일들을 파일 테이블에 표시"""
        try:
            if not hasattr(self.main_window, "central_triple_layout"):
                return

            # ResultsView에서 해당 그룹의 파일 모델을 가져와서 파일 테이블에 설정
            results_view = self.main_window.results_view
            if hasattr(results_view, "get_file_model_for_group"):
                print(f"🔍 그룹 {group_index.row()}의 파일 모델 요청")
                file_model = results_view.get_file_model_for_group(group_index)
                if file_model:
                    self.main_window.central_triple_layout.set_file_table_model(file_model)
                    self.logger.debug(f"그룹 {group_index.row()}의 파일 모델을 파일 테이블에 설정")
                    print(f"✅ 그룹 {group_index.row()}의 파일 모델을 파일 테이블에 설정")
                else:
                    self.logger.warning(f"그룹 {group_index.row()}의 파일 모델을 찾을 수 없습니다")
                    print(f"❌ 그룹 {group_index.row()}의 파일 모델을 찾을 수 없습니다")
            else:
                # ResultsView에 해당 메서드가 없으면 기본 파일 모델 사용
                if (
                    hasattr(results_view, "all_detail_table")
                    and results_view.all_detail_table.model()
                ):
                    self.main_window.central_triple_layout.set_file_table_model(
                        results_view.all_detail_table.model()
                    )
                    self.logger.debug("기본 파일 모델을 파일 테이블에 설정")
                    print("✅ 기본 파일 모델을 파일 테이블에 설정")

        except Exception as e:
            self.logger.error(f"파일 테이블 업데이트 실패: {e}")
            print(f"❌ 파일 테이블 업데이트 실패: {e}")
            import traceback

            traceback.print_exc()

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
