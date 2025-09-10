"""
UI Initializer for MainWindow

MainWindow의 UI 초기화 로직을 관리하는 클래스입니다.
UI 컴포넌트 생성, 레이아웃 설정, 메뉴/툴바 생성을 담당합니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QLabel, QMainWindow, QSplitter, QVBoxLayout,
                             QWidget)

from src.gui.builders.menu_builder import MenuBuilder
from src.gui.builders.toolbar_builder import ToolbarBuilder


class UIInitializer:
    """MainWindow의 UI 초기화를 담당하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        """UIInitializer 초기화"""
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        self.menu_builder = MenuBuilder(main_window)
        self.toolbar_builder = ToolbarBuilder(main_window)

    def init_ui(self):
        """UI 초기화 메인 메서드"""
        try:
            self.logger.info("UI 초기화 시작")
            self.setup_basic_window()
            self.setup_central_widget()
            self.create_menu_bar()
            self.create_toolbar()
            self.create_status_bar()
            self.setup_layout()
            self.setup_models()  # 모델 초기화 추가
            self.logger.info("UI 초기화 완료")
        except Exception as e:
            self.logger.error(f"UI 초기화 실패: {e}")
            raise

    def setup_basic_window(self):
        """기본 윈도우 설정"""
        try:
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
            central_widget = QWidget()
            self.main_window.setCentralWidget(central_widget)
            parent_layout = QVBoxLayout(central_widget)
            parent_layout.setSpacing(10)
            parent_layout.setContentsMargins(10, 10, 10, 10)
            self.main_window.parent_layout = parent_layout
            self.main_window.central_widget = central_widget
            self.logger.debug("중앙 위젯 설정 완료")
        except Exception as e:
            self.logger.error(f"중앙 위젯 설정 실패: {e}")
            raise

    def create_menu_bar(self):
        """메뉴바 생성"""
        try:
            if (
                not hasattr(self.main_window, "safety_system_manager")
                or self.main_window.safety_system_manager is None
            ):
                self.logger.warning(
                    "safety_system_manager가 초기화되지 않았습니다. 메뉴바 생성을 건너뜁니다."
                )
                return
            self.menu_builder.create_menu_bar()
            self.logger.debug("메뉴바 생성 완료")
        except Exception as e:
            self.logger.error(f"메뉴바 생성 실패: {e}")
            raise

    def create_toolbar(self):
        """툴바 생성"""
        try:
            from src.gui.components.main_toolbar import MainToolbar

            self.main_window.main_toolbar = MainToolbar()
            self.toolbar_builder.create_toolbar()
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
                toolbar.scan_requested.connect(self.main_window.on_scan_requested)
                toolbar.preview_requested.connect(self.main_window.on_preview_requested)
                toolbar.organize_requested.connect(self.main_window.on_organize_requested)
                toolbar.search_text_changed.connect(self.main_window.on_search_text_changed)
                toolbar.settings_requested.connect(self.main_window.on_settings_requested)
                self.logger.debug("툴바 시그널 연결 완료")
        except Exception as e:
            self.logger.error(f"툴바 시그널 연결 실패: {e}")

    def create_status_bar(self):
        """상태바 설정"""
        try:
            status_bar = self.main_window.statusBar()
            self.main_window.status_label = QLabel("준비됨")
            status_bar.addWidget(self.main_window.status_label)
            from PyQt5.QtWidgets import QProgressBar

            status_bar.addPermanentWidget(QLabel("진행률:"))
            self.main_window.status_progress = QProgressBar()
            self.main_window.status_progress.setMaximumWidth(200)
            self.main_window.status_progress.setMaximumHeight(20)
            status_bar.addPermanentWidget(self.main_window.status_progress)
            self.main_window.status_file_count = QLabel("파일: 0")
            status_bar.addPermanentWidget(self.main_window.status_file_count)
            self.main_window.status_memory = QLabel("메모리: 0MB")
            status_bar.addPermanentWidget(self.main_window.status_memory)
            self.main_window.update_status_bar("애플리케이션이 준비되었습니다")
            self.logger.debug("상태바 설정 완료")
        except Exception as e:
            self.logger.error(f"상태바 설정 실패: {e}")
            raise

    def setup_layout(self):
        """레이아웃 설정"""
        try:
            parent_layout = self.main_window.parent_layout
            if hasattr(self.main_window, "main_toolbar"):
                parent_layout.addWidget(self.main_window.main_toolbar)
            self.setup_splitters()
            self.logger.debug("레이아웃 설정 완료")
        except Exception as e:
            self.logger.error(f"레이아웃 설정 실패: {e}")
            raise

    def setup_splitters(self):
        """스플리터 설정"""
        try:
            parent_layout = self.main_window.parent_layout
            splitter = QSplitter(Qt.Horizontal)
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(8)
            self.create_panels(splitter)
            splitter.setSizes([1200])
            splitter.setStretchFactor(0, 1)
            parent_layout.addWidget(splitter)
            self.main_window.main_splitter = splitter
            self.logger.debug("스플리터 설정 완료")
        except Exception as e:
            self.logger.error(f"스플리터 설정 실패: {e}")
            raise

    def create_panels(self, splitter):
        """패널들 생성"""
        try:
            from src.gui.components.central_triple_layout import \
                CentralTripleLayout
            from src.gui.components.panels.left_panel_dock import LeftPanelDock
            from src.gui.components.results_view import ResultsView

            self.main_window.left_panel_dock = LeftPanelDock()
            self.main_window.addDockWidget(Qt.LeftDockWidgetArea, self.main_window.left_panel_dock)
            self.main_window.left_panel = self.main_window.left_panel_dock.left_panel
            self.main_window.left_panel.set_main_window(self.main_window)
            self.main_window.left_panel.restore_directory_settings()
            self.main_window.results_view = ResultsView()
            self.main_window.central_triple_layout = CentralTripleLayout()
            from PyQt5.QtCore import QTimer

            QTimer.singleShot(0, self.setup_triple_layout_models)
            splitter.addWidget(self.main_window.central_triple_layout)
            self.setup_models()
            self.logger.debug("패널들 생성 완료")
        except Exception as e:
            self.logger.error(f"패널 생성 실패: {e}")
            raise

    def setup_triple_layout_models(self):
        """3열 레이아웃에 기존 모델들 연결"""
        try:
            results_view = self.main_window.results_view
            if hasattr(results_view, "all_group_table") and results_view.all_group_table.model():
                self.main_window.central_triple_layout.set_group_table_model(
                    results_view.all_group_table.model()
                )
                self.logger.debug("그룹 테이블 모델 연결 완료")
            else:
                self.logger.warning("그룹 테이블 모델을 찾을 수 없습니다")
            if hasattr(results_view, "all_detail_table") and results_view.all_detail_table.model():
                self.main_window.central_triple_layout.set_file_table_model(
                    results_view.all_detail_table.model()
                )
                self.logger.debug("파일 테이블 모델 연결 완료")
            else:
                self.logger.warning("파일 테이블 모델을 찾을 수 없습니다")
            if hasattr(results_view, "group_selected"):
                results_view.group_selected.connect(self.on_group_selected)
            self.main_window.central_triple_layout.connect_group_selection(
                self.on_group_selection_changed
            )
            self.main_window.central_triple_layout.group_selection_changed.connect(
                self.on_group_selected
            )
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
                group_data = self.extract_group_data_from_index(current_index)
                self.main_window.central_triple_layout.update_detail_from_group(group_data)
                self.update_file_table_for_group(current_index)
        except Exception as e:
            self.logger.error(f"그룹 선택 변경 처리 실패: {e}")

    def extract_group_data_from_index(self, index):
        """인덱스에서 그룹 데이터 추출"""
        try:
            if hasattr(self.main_window, "grouped_model") and self.main_window.grouped_model:
                grouped_model = self.main_window.grouped_model
                if hasattr(grouped_model, "get_group_at_row"):
                    group_info = grouped_model.get_group_at_row(index.row())
                    if group_info:
                        logger.info(
                            "✅ 그룹 데이터 추출 성공: %s", group_info.get("title", "Unknown")
                        )
                        return {
                            "title": group_info.get("title", "제목 없음"),
                            "original_title": group_info.get("original_title", "원제목 없음"),
                            "season": group_info.get("season", "시즌 정보 없음"),
                            "episode_count": group_info.get("episode_count", 0),
                            "status": group_info.get("status", "상태 정보 없음"),
                            "file_count": group_info.get("file_count", 0),
                            "total_size": group_info.get("total_size", "0 B"),
                            "tmdb_match": group_info.get("tmdb_match"),
                            "tags": group_info.get("tags", []),
                        }
            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view
                if hasattr(results_view, "extract_group_data_from_index"):
                    return results_view.extract_group_data_from_index(index)
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
                    "tmdb_match": None,
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
            results_view = self.main_window.results_view
            if hasattr(results_view, "get_file_model_for_group"):
                logger.info("🔍 그룹 %s의 파일 모델 요청", group_index.row())
                file_model = results_view.get_file_model_for_group(group_index)
                if file_model:
                    self.main_window.central_triple_layout.set_file_table_model(file_model)
                    self.logger.debug(f"그룹 {group_index.row()}의 파일 모델을 파일 테이블에 설정")
                    logger.info("✅ 그룹 %s의 파일 모델을 파일 테이블에 설정", group_index.row())
                else:
                    self.logger.warning(f"그룹 {group_index.row()}의 파일 모델을 찾을 수 없습니다")
                    logger.info("❌ 그룹 %s의 파일 모델을 찾을 수 없습니다", group_index.row())
            elif (
                hasattr(results_view, "all_detail_table") and results_view.all_detail_table.model()
            ):
                self.main_window.central_triple_layout.set_file_table_model(
                    results_view.all_detail_table.model()
                )
                self.logger.debug("기본 파일 모델을 파일 테이블에 설정")
                logger.info("✅ 기본 파일 모델을 파일 테이블에 설정")
        except Exception as e:
            self.logger.error(f"파일 테이블 업데이트 실패: {e}")
            logger.info("❌ 파일 테이블 업데이트 실패: %s", e)
            import traceback

            traceback.print_exc()

    def setup_models(self):
        """모델들 초기화"""
        try:
            from src.gui.table_models import DetailFileModel, GroupedListModel

            destination_directory = ""
            if hasattr(self.main_window, "settings_manager") and hasattr(
                self.main_window.settings_manager, "config"
            ):
                destination_directory = getattr(
                    self.main_window.settings_manager.config.application,
                    "destination_root",
                    "대상 폴더",
                )
            tmdb_client = getattr(self.main_window, "tmdb_client", None)
            self.main_window.grouped_model = GroupedListModel(
                {}, tmdb_client, destination_directory
            )
            self.main_window.detail_model = DetailFileModel([], tmdb_client)
            if hasattr(self.main_window, "results_view"):
                self.main_window.results_view.set_group_model(self.main_window.grouped_model)
                self.main_window.results_view.set_detail_model(self.main_window.detail_model)
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
            self.logger.debug("UI 연결 설정 완료")
        except Exception as e:
            self.logger.error(f"UI 연결 설정 실패: {e}")
            raise
