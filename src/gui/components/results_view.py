"""
결과 뷰 컴포넌트 - Phase 3 UI/UX 리팩토링
5개 탭(전체, 미매칭, 충돌, 중복, 완료)을 가진 QTabWidget 기반의 결과 표시 영역을 관리합니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QSplitter,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.gui.components.cell_delegates import (
    ProgressCellDelegate,
    StatusCellDelegate,
    TextPreviewCellDelegate,
)


class ResultsView(QTabWidget):
    """결과 표시 뷰 (5개 탭 구조)"""

    group_selected = pyqtSignal(dict)
    group_double_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.filter_manager = None
        self._current_group_selection = None
        self._cross_tab_sync_enabled = True
        self._detail_model = None

    def init_ui(self):
        """UI 초기화"""
        self.create_results_header()
        self.create_tabs()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCurrentIndex(1)
        self.currentChanged.connect(self.on_tab_changed)
        self.setup_delegates()

    def setup_delegates(self):
        """Phase 6: 각 테이블에 적절한 Delegate 설정"""
        try:
            self._apply_delegates_to_table(self.all_group_table, "group")
            self._apply_delegates_to_table(self.all_detail_table, "detail")
            self._apply_delegates_to_table(self.unmatched_group_table, "group")
            self._apply_delegates_to_table(self.unmatched_detail_table, "detail")
            self._apply_delegates_to_table(self.conflict_group_table, "group")
            self._apply_delegates_to_table(self.conflict_detail_table, "detail")
            self._apply_delegates_to_table(self.duplicate_group_table, "group")
            self._apply_delegates_to_table(self.duplicate_detail_table, "detail")
            self._apply_delegates_to_table(self.completed_group_table, "group")
            self._apply_delegates_to_table(self.completed_detail_table, "detail")
            logger.info("✅ 셀 표현 Delegate 설정 완료")
        except Exception as e:
            logger.info("❌ Delegate 설정 실패: %s", e)

    def _apply_delegates_to_table(self, table: QTableView, table_type: str):
        """테이블에 Delegate 적용"""
        if not table:
            return
        if table_type == "group":
            table.setItemDelegateForColumn(0, TextPreviewCellDelegate(table))
            table.setItemDelegateForColumn(1, TextPreviewCellDelegate(table))
            table.setItemDelegateForColumn(2, TextPreviewCellDelegate(table))
            table.setItemDelegateForColumn(3, ProgressCellDelegate(table))
            table.setItemDelegateForColumn(4, TextPreviewCellDelegate(table))
            table.setItemDelegateForColumn(5, StatusCellDelegate(table))
        elif table_type == "detail":
            table.setItemDelegateForColumn(0, TextPreviewCellDelegate(table))
            table.setItemDelegateForColumn(1, TextPreviewCellDelegate(table))
            table.setItemDelegateForColumn(2, ProgressCellDelegate(table))
            table.setItemDelegateForColumn(3, TextPreviewCellDelegate(table))
            table.setItemDelegateForColumn(4, TextPreviewCellDelegate(table))
            table.setItemDelegateForColumn(5, StatusCellDelegate(table))

    def on_tab_changed(self, index):
        """탭 변경 시 호출"""
        if self.filter_manager:
            stats = self.filter_manager.get_filter_stats()
            tab_name = self.tabText(index)
            logger.info("📊 %s 탭으로 변경됨 - 필터 통계: %s", tab_name, stats)

    def setup_filter_manager(self):
        """필터 관리자 설정"""
        from src.gui.components.status_filter_proxy import TabFilterManager

        self.filter_manager = TabFilterManager(self)

    def create_tabs(self):
        """5개 탭 생성"""
        self.all_tab = self.create_tab_content("📋 전체")
        self.addTab(self.all_tab, "📋 전체")
        self.unmatched_tab = self.create_tab_content("⚠️ 미매칭")
        self.addTab(self.unmatched_tab, "⚠️ 미매칭")
        self.conflict_tab = self.create_tab_content("💥 충돌")
        self.addTab(self.conflict_tab, "💥 충돌")
        self.duplicate_tab = self.create_tab_content("🔄 중복")
        self.addTab(self.duplicate_tab, "🔄 중복")
        self.completed_tab = self.create_tab_content("✅ 완료")
        self.addTab(self.completed_tab, "✅ 완료")

    def create_tab_content(self, title):
        """탭 내용 생성 (마스터-디테일 스플리터 구조)"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(5)
        group_label = QLabel("📋 애니메이션 그룹")
        group_font = QFont()
        group_font.setPointSize(11)
        group_font.setBold(True)
        group_label.setFont(group_font)
        group_layout.addWidget(group_label)
        group_table = QTableView()
        group_table.verticalHeader().setVisible(False)
        group_table.setSelectionBehavior(QTableView.SelectRows)
        group_table.setAlternatingRowColors(True)
        group_table.setWordWrap(True)
        group_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        group_table.setMouseTracking(True)
        group_table.setToolTip(
            "애니메이션 그룹 목록 - 제목에 마우스를 올리면 포스터를 볼 수 있습니다"
        )
        if hasattr(group_table, "setUniformRowHeights"):
            group_table.setUniformRowHeights(True)
        group_table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        group_table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        group_table.setShowGrid(False)
        group_layout.addWidget(group_table)
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(5)
        detail_label = QLabel("📁 선택된 그룹의 파일들")
        detail_font = QFont()
        detail_font.setPointSize(11)
        detail_font.setBold(True)
        detail_label.setFont(detail_font)
        detail_layout.addWidget(detail_label)
        detail_table = QTableView()
        detail_table.verticalHeader().setVisible(False)
        detail_table.setSelectionBehavior(QTableView.SelectRows)
        detail_table.setAlternatingRowColors(True)
        detail_table.setWordWrap(True)
        detail_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        detail_table.setMouseTracking(True)
        detail_table.setToolTip("파일 상세 목록 - 파일명에 마우스를 올리면 포스터를 볼 수 있습니다")
        if hasattr(detail_table, "setUniformRowHeights"):
            detail_table.setUniformRowHeights(True)
        detail_table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        detail_table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        detail_table.setShowGrid(False)
        detail_layout.addWidget(detail_table)
        splitter.addWidget(group_widget)
        splitter.addWidget(detail_widget)
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)
        if title == "📋 전체":
            self.all_group_table = group_table
            self.all_detail_table = detail_table
            self.all_splitter = splitter
        elif title == "⚠️ 미매칭":
            self.unmatched_group_table = group_table
            self.unmatched_detail_table = detail_table
            self.unmatched_splitter = splitter
        elif title == "💥 충돌":
            self.conflict_group_table = group_table
            self.conflict_detail_table = detail_table
            self.conflict_splitter = splitter
        elif title == "🔄 중복":
            self.duplicate_group_table = group_table
            self.duplicate_detail_table = detail_table
            self.duplicate_splitter = splitter
        elif title == "✅ 완료":
            self.completed_group_table = group_table
            self.completed_detail_table = detail_table
            self.completed_splitter = splitter
        return tab_widget

    def setup_connections(self):
        """시그널 연결 설정"""
        logger.info("🔧 setup_connections 호출됨")
        tables = [
            self.all_group_table,
            self.unmatched_group_table,
            self.conflict_group_table,
            self.duplicate_group_table,
            self.completed_group_table,
        ]
        for i, table in enumerate(tables):
            if table:
                logger.info("🔧 테이블 %s 연결 중: %s", i, type(table).__name__)
                if table.selectionModel():
                    table.selectionModel().selectionChanged.connect(self.on_group_selection_changed)
                    table.doubleClicked.connect(self.on_group_double_clicked)
                    logger.info("✅ 테이블 %s 시그널 연결 완료", i)
                else:
                    logger.info("⚠️ 테이블 %s의 selectionModel이 None", i)
            else:
                logger.info("⚠️ 테이블 %s가 None", i)
        logger.info("🔧 setup_connections 완료")

    def create_results_header(self):
        """결과 헤더 생성"""
        header_widget = QWidget()
        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel("📋 스캔 결과")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        layout.addStretch(1)
        self.setCornerWidget(header_widget, Qt.TopLeftCorner)

    def set_group_model(self, model):
        """그룹 리스트 모델 설정 (모든 탭에 동일한 모델 적용)"""
        tables = [
            self.all_group_table,
            self.unmatched_group_table,
            self.conflict_group_table,
            self.duplicate_group_table,
            self.completed_group_table,
        ]
        for table in tables:
            table.setModel(model)
            self.adjust_group_table_columns(table, model)
        if not self.filter_manager:
            self.setup_filter_manager()
        if self.filter_manager:
            self.filter_manager.update_source_model(model)
        self.setup_connections()

    def set_detail_model(self, model):
        """상세 파일 목록 모델 설정 (모든 탭에 동일한 모델 적용)"""
        self._detail_model = model
        tables = [
            self.all_detail_table,
            self.unmatched_detail_table,
            self.conflict_detail_table,
            self.duplicate_detail_table,
            self.completed_detail_table,
        ]
        for table in tables:
            table.setModel(model)
            self.adjust_detail_table_columns(table, model)

    def adjust_group_table_columns(self, table, model):
        """그룹 테이블 컬럼 크기 조정"""
        header = table.horizontalHeader()
        if hasattr(model, "get_column_widths"):
            column_widths = model.get_column_widths()
            stretch_columns = model.get_stretch_columns()
            for col in range(header.count()):
                if col in stretch_columns:
                    header.setSectionResizeMode(col, QHeaderView.Stretch)
                else:
                    header.setSectionResizeMode(col, QHeaderView.Fixed)
                    if col in column_widths:
                        header.resizeSection(col, column_widths[col])
        else:
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            table.setColumnWidth(0, 120)
            for i in range(1, model.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            header.setStretchLastSection(True)
        table.verticalHeader().setDefaultSectionSize(25)

    def adjust_detail_table_columns(self, table, model):
        """상세 테이블 컬럼 크기 조정"""
        header = table.horizontalHeader()
        if hasattr(model, "get_column_widths"):
            column_widths = model.get_column_widths()
            stretch_columns = model.get_stretch_columns()
            for col in range(header.count()):
                if col in stretch_columns:
                    header.setSectionResizeMode(col, QHeaderView.Stretch)
                else:
                    header.setSectionResizeMode(col, QHeaderView.Fixed)
                    if col in column_widths:
                        header.resizeSection(col, column_widths[col])
        else:
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            table.setColumnWidth(0, 120)
            for i in range(1, model.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            header.setStretchLastSection(True)
        table.verticalHeader().setDefaultSectionSize(25)

    def sync_selection_across_tabs(self, group_id):
        """모든 탭에서 동일한 그룹 선택 동기화 (상세 뷰 업데이트 없이)"""
        if not self._cross_tab_sync_enabled:
            return
        self._current_group_selection = group_id
        all_tables = [
            self.all_group_table,
            self.unmatched_group_table,
            self.conflict_group_table,
            self.duplicate_group_table,
            self.completed_group_table,
        ]
        for table in all_tables:
            if table and table.model():
                table.clearSelection()
                self._select_group_in_table(table, group_id)

    def _select_group_in_table(self, table, group_id):
        """테이블에서 특정 그룹 ID를 가진 행 선택"""
        model = table.model()
        if not model:
            return
        source_model = model.sourceModel() if hasattr(model, "sourceModel") else model
        if hasattr(source_model, "find_group_by_id"):
            row_index = source_model.find_group_by_id(group_id)
            if row_index >= 0:
                if hasattr(model, "mapFromSource"):
                    proxy_index = model.mapFromSource(source_model.index(row_index, 0))
                    if proxy_index.isValid():
                        table.selectRow(proxy_index.row())
                else:
                    table.selectRow(row_index)

    def enable_cross_tab_sync(self, enabled=True):
        """탭 간 동기화 활성화/비활성화"""
        self._cross_tab_sync_enabled = enabled

    def get_current_selection(self):
        """현재 선택된 그룹 정보 반환"""
        return self._current_group_selection

    def refresh_all_tabs(self):
        """모든 탭 새로고침"""
        if self.filter_manager:
            self.filter_manager.refresh_filters()
        all_tables = [
            self.all_group_table,
            self.unmatched_group_table,
            self.conflict_group_table,
            self.duplicate_group_table,
            self.completed_group_table,
        ]
        for table in all_tables:
            if table and table.model():
                table.viewport().update()

    def get_tab_statistics(self):
        """각 탭별 통계 정보 반환"""
        stats = {}
        if self.filter_manager:
            filter_stats = self.filter_manager.get_filter_stats()
            for tab_name, data in filter_stats.items():
                stats[tab_name] = {
                    "filtered_count": data["filtered_count"],
                    "source_count": data["source_count"],
                    "percentage": (
                        data["filtered_count"] / data["source_count"] * 100
                        if data["source_count"] > 0
                        else 0
                    ),
                }
        return stats

    def set_tab_visibility(self, tab_name, visible):
        """특정 탭의 가시성 설정"""
        tab_index = -1
        if tab_name == "all":
            tab_index = 0
        elif tab_name == "unmatched":
            tab_index = 1
        elif tab_name == "conflict":
            tab_index = 2
        elif tab_name == "duplicate":
            tab_index = 3
        elif tab_name == "completed":
            tab_index = 4
        if tab_index >= 0:
            self.setTabVisible(tab_index, visible)

    def get_visible_tabs(self):
        """현재 보이는 탭 목록 반환"""
        visible_tabs = []
        for i in range(self.count()):
            if self.isTabVisible(i):
                visible_tabs.append(
                    {
                        "index": i,
                        "name": self.tabText(i),
                        "tooltip": self.tabToolTip(i) if self.tabToolTip(i) else "",
                    }
                )
        return visible_tabs

    def on_group_selection_changed(self, selected, deselected):
        """그룹 선택 변경 시 호출"""
        logger.info(
            "🔍 그룹 선택 변경 감지: selected=%s, deselected=%s",
            len(selected.indexes()),
            len(deselected.indexes()),
        )
        indexes = selected.indexes()
        if indexes:
            row = indexes[0].row()
            logger.info("🔍 선택된 행: %s", row)
            current_widget = self.currentWidget()
            if current_widget:
                tables = current_widget.findChildren(QTableView)
                logger.info(
                    "🔍 찾은 테이블들: %s",
                    [(type(t.model()).__name__ if t.model() else "None") for t in tables],
                )
                if tables and len(tables) > 0:
                    group_table = None
                    for table in tables:
                        model = table.model()
                        if model:
                            if hasattr(model, "sourceModel") and model.sourceModel():
                                source_model = model.sourceModel()
                                if hasattr(source_model, "get_group_at_row"):
                                    group_table = table
                                    break
                            elif hasattr(model, "get_group_at_row"):
                                group_table = table
                                break
                    if group_table:
                        model = group_table.model()
                        logger.info("🔍 그룹 테이블 모델: %s", type(model).__name__)
                        if model:
                            if hasattr(model, "sourceModel") and model.sourceModel():
                                source_model = model.sourceModel()
                                logger.info("🔍 소스 모델: %s", type(source_model).__name__)
                                if hasattr(source_model, "get_group_at_row"):
                                    group = source_model.get_group_at_row(row)
                                    if group:
                                        logger.info(
                                            "✅ 그룹 정보 가져옴: %s", group.get("title", "Unknown")
                                        )
                                        self.update_detail_view(group)
                                        self.sync_selection_across_tabs(group.get("key", ""))
                                    else:
                                        logger.info("⚠️ 그룹 정보가 None")
                                else:
                                    logger.info("⚠️ 소스 모델에 get_group_at_row 메서드 없음")
                            elif hasattr(model, "get_group_at_row"):
                                group = model.get_group_at_row(row)
                                if group:
                                    logger.info(
                                        "✅ 그룹 정보 가져옴: %s", group.get("title", "Unknown")
                                    )
                                    self.update_detail_view(group)
                                    self.sync_selection_across_tabs(group.get("key", ""))
                                else:
                                    logger.info("⚠️ 그룹 정보가 None")
                            else:
                                logger.info("⚠️ 모델에 get_group_at_row 메서드 없음")
                        else:
                            logger.info("⚠️ 그룹 테이블 모델이 None")
                    else:
                        logger.info(
                            "⚠️ 그룹 테이블을 찾을 수 없음 (get_group_at_row 메서드가 있는 모델이 없음)"
                        )
                else:
                    logger.info("⚠️ 테이블을 찾을 수 없음")
            else:
                logger.info("⚠️ 현재 위젯이 None")
        else:
            logger.info("⚠️ 선택된 인덱스가 없음")

    def on_group_double_clicked(self, index):
        """그룹 더블클릭 시 호출"""
        current_widget = self.currentWidget()
        if current_widget:
            tables = current_widget.findChildren(QTableView)
            if tables and len(tables) > 0:
                group_table = tables[0]
                model = group_table.model()
                if model and hasattr(model, "get_group_at_row"):
                    group = model.get_group_at_row(index.row())
                    if group:
                        self.group_double_clicked.emit(group)

    def get_selected_group_row(self):
        """현재 활성 탭의 그룹 테이블에서 선택된 행 반환"""
        current_widget = self.currentWidget()
        if current_widget:
            group_table = current_widget.findChild(QTableView)
            if group_table:
                selection = group_table.selectionModel()
                if not selection.hasSelection():
                    return -1
                indexes = selection.selectedRows()
                if indexes:
                    return indexes[0].row()
        return -1

    def get_current_tab_name(self):
        """현재 활성 탭 이름 반환"""
        return self.tabText(self.currentIndex())

    def set_current_tab_by_status(self, status):
        """상태에 따라 해당하는 탭으로 이동"""
        status_to_tab = {
            "tmdb_matched": 4,
            "complete": 4,
            "error": 2,
            "needs_review": 1,
            "pending": 1,
        }
        tab_index = status_to_tab.get(status, 0)
        self.setCurrentIndex(tab_index)

    def update_detail_view(self, group):
        """상세 뷰 업데이트"""
        logger.info(
            "🔍 update_detail_view 호출됨: group=%s",
            group.get("title", "Unknown") if group else "None",
        )
        if not group:
            logger.info("⚠️ 그룹이 None이므로 업데이트 중단")
            return
        current_widget = self.currentWidget()
        if current_widget:
            detail_table = self._find_detail_table(current_widget)
            if detail_table:
                logger.info("🔍 상세 테이블 찾음: %s", type(detail_table).__name__)
                if self._detail_model:
                    logger.info("🔍 상세 모델 설정: %s", type(self._detail_model).__name__)
                    detail_table.setModel(self._detail_model)
                    if "items" in group:
                        items = group["items"]
                        logger.info("🔍 그룹의 파일 수: %s", len(items))
                        self._detail_model.set_items(items)
                        logger.info("✅ 상세 뷰 업데이트 완료: %s개 파일", len(items))
                    else:
                        logger.info("⚠️ 그룹에 'items' 키가 없음: %s", list(group.keys()))
                    self.adjust_detail_table_columns(detail_table, self._detail_model)
                else:
                    logger.info("⚠️ 상세 모델이 None")
            else:
                logger.info("⚠️ 상세 테이블을 찾을 수 없음")
        else:
            logger.info("⚠️ 현재 위젯이 None")

    def _find_detail_table(self, widget):
        """위젯에서 상세 테이블을 찾는 헬퍼 메서드"""
        tables = widget.findChildren(QTableView)
        logger.info("🔍 찾은 테이블 수: %s", len(tables))
        if len(tables) < 2:
            return None
        for table in tables:
            parent = table.parent()
            if parent:
                for child in parent.children():
                    if isinstance(child, QLabel):
                        label_text = child.text()
                        if "선택된 그룹의 파일들" in label_text:
                            logger.info("🔍 상세 테이블 발견: 라벨='%s'", label_text)
                            return table
        logger.info("🔍 라벨로 상세 테이블을 찾지 못함, 두 번째 테이블 사용")
        return tables[1] if len(tables) > 1 else None

    def get_current_splitter(self):
        """현재 활성 탭의 스플리터 반환"""
        current_index = self.currentIndex()
        if current_index == 0:
            return getattr(self, "all_splitter", None)
        if current_index == 1:
            return getattr(self, "unmatched_splitter", None)
        if current_index == 2:
            return getattr(self, "conflict_splitter", None)
        if current_index == 3:
            return getattr(self, "duplicate_splitter", None)
        if current_index == 4:
            return getattr(self, "completed_splitter", None)
        return None

    def set_splitter_ratio(self, ratio):
        """현재 활성 탭의 스플리터 비율 설정"""
        splitter = self.get_current_splitter()
        if splitter:
            total_height = splitter.height()
            group_height = int(total_height * ratio)
            detail_height = total_height - group_height
            splitter.setSizes([group_height, detail_height])

    def get_splitter_ratio(self):
        """현재 활성 탭의 스플리터 비율 반환"""
        splitter = self.get_current_splitter()
        if splitter:
            sizes = splitter.sizes()
            if sizes[1] > 0:
                return sizes[0] / (sizes[0] + sizes[1])
        return 0.6

    def get_file_model_for_group(self, group_index):
        """선택된 그룹의 파일 모델을 반환"""
        try:
            if not group_index.isValid():
                logger.info("❌ 유효하지 않은 그룹 인덱스")
                return None
            group_model = group_index.model()
            if not group_model:
                logger.info("❌ 그룹 모델이 None")
                return None
            logger.info("🔍 그룹 모델 타입: %s", type(group_model).__name__)
            if hasattr(group_model, "get_group_at_row"):
                logger.info("✅ GroupedListModel 감지됨")
                group_info = group_model.get_group_at_row(group_index.row())
                if not group_info:
                    logger.info("❌ 그룹 정보를 찾을 수 없음: row=%s", group_index.row())
                    return None
                logger.info("✅ 그룹 정보 찾음: %s", group_info.get("title", "Unknown"))
                group_items = group_info.get("items", [])
                if not group_items:
                    logger.info("❌ 그룹에 파일이 없음")
                    return None
                logger.info("✅ 그룹 내 파일 수: %s", len(group_items))
                from src.gui.table_models import DetailFileModel

                file_model = DetailFileModel()
                file_model.set_items(group_items)
                logger.info("✅ 파일 모델 생성 완료: %s개 파일", len(group_items))
                return file_model
            logger.info("❌ get_group_at_row 메서드가 없는 모델: %s", type(group_model).__name__)
            logger.info("🔍 MainWindow의 grouped_model 사용 시도")
            from PyQt5.QtWidgets import QApplication

            app = QApplication.instance()
            if app:
                main_windows = [
                    widget for widget in app.topLevelWidgets() if hasattr(widget, "grouped_model")
                ]
                if main_windows:
                    main_window = main_windows[0]
                    if hasattr(main_window, "grouped_model") and main_window.grouped_model:
                        grouped_model = main_window.grouped_model
                        logger.info(
                            "✅ MainWindow의 grouped_model 찾음: %s", type(grouped_model).__name__
                        )
                        if hasattr(grouped_model, "get_group_at_row"):
                            group_info = grouped_model.get_group_at_row(group_index.row())
                            if group_info:
                                group_items = group_info.get("items", [])
                                if group_items:
                                    from src.gui.table_models import DetailFileModel

                                    file_model = DetailFileModel()
                                    file_model.set_items(group_items)
                                    logger.info(
                                        "✅ MainWindow grouped_model로 파일 모델 생성: %s개 파일",
                                        len(group_items),
                                    )
                                    return file_model
            logger.info("❌ MainWindow의 grouped_model에서도 그룹 정보를 찾을 수 없음")
            return None
        except Exception as e:
            logger.info("❌ get_file_model_for_group 실패: %s", e)
            import traceback

            traceback.print_exc()
            return None
