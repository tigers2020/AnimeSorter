"""
상태별 필터링 프록시 모델 - Phase 3 UI/UX 리팩토링
각 탭에서 상태별로 데이터를 필터링하는 QSortFilterProxyModel을 구현합니다.
Phase 7: 검색 및 필터 기능 구현 - 실시간 검색과 고급 필터링 추가
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import QSortFilterProxyModel, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


class StatusFilterProxyModel(QSortFilterProxyModel):
    """상태별 필터링 및 검색을 위한 프록시 모델"""

    def __init__(self, status_filter="", parent=None):
        super().__init__(parent)
        self.status_filter = status_filter
        self.search_text = ""
        self.setFilterRole(Qt.UserRole)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._apply_search_filter)

    def set_status_filter(self, status_filter):
        """상태 필터 설정"""
        self.status_filter = status_filter
        self.invalidateFilter()

    def set_search_text(self, search_text):
        """검색 텍스트 설정 (디바운스 적용)"""
        self.search_text = search_text
        self.search_timer.start(250)

    def _apply_search_filter(self):
        """검색 필터 적용 (디바운스 후 호출)"""
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """행 필터링 로직 (상태 필터 + 검색 필터)"""
        if not self._accepts_status_filter(source_row, source_parent):
            return False
        return self._accepts_search_filter(source_row, source_parent)

    def _accepts_status_filter(self, source_row, source_parent):
        """상태 필터 확인"""
        if not self.status_filter:
            return True
        source_model = self.sourceModel()
        if not source_model:
            return True
        if hasattr(source_model, "get_group_at_row"):
            group = source_model.get_group_at_row(source_row)
            if group and "status" in group:
                group_status = group["status"]
                return self._matches_status_filter(group_status)
        status_index = source_model.index(
            source_row, self._get_status_column_index(source_model), source_parent
        )
        if status_index.isValid():
            status_data = source_model.data(status_index, Qt.DisplayRole)
            if status_data:
                return self._matches_status_filter(status_data)
        return True

    def _accepts_search_filter(self, source_row, source_parent):
        """검색 필터 확인"""
        if not self.search_text:
            return True
        source_model = self.sourceModel()
        if not source_model:
            return True
        search_fields = self._get_searchable_fields(source_model, source_row, source_parent)
        for field_value in search_fields:
            if field_value and self.search_text.lower() in str(field_value).lower():
                return True
        return False

    def _get_searchable_fields(self, source_model, source_row, source_parent):
        """검색 가능한 필드들의 값들을 가져오기"""
        searchable_fields = []
        if hasattr(source_model, "headers"):
            headers = source_model.headers
            searchable_indices = [1, 2, 3, 4, 5]
            for col_index in searchable_indices:
                if col_index < len(headers):
                    index = source_model.index(source_row, col_index, source_parent)
                    if index.isValid():
                        field_value = source_model.data(index, Qt.DisplayRole)
                        searchable_fields.append(field_value)
        elif hasattr(source_model, "columnCount"):
            searchable_indices = [1, 2, 3, 4, 5]
            for col_index in searchable_indices:
                if col_index < source_model.columnCount():
                    index = source_model.index(source_row, col_index, source_parent)
                    if index.isValid():
                        field_value = source_model.data(index, Qt.DisplayRole)
                        searchable_fields.append(field_value)
        return searchable_fields

    def _matches_status_filter(self, status):
        """상태가 필터와 일치하는지 확인"""
        if not self.status_filter:
            return True
        status_mapping = {
            "all": ["tmdb_matched", "complete", "error", "needs_review", "pending"],
            "unmatched": ["needs_review", "pending"],
            "conflict": ["error"],
            "duplicate": ["needs_review"],
            "completed": ["tmdb_matched", "complete"],
        }
        allowed_statuses = status_mapping.get(self.status_filter, [])
        return status in allowed_statuses

    def _get_status_column_index(self, source_model):
        """상태 컬럼의 인덱스 찾기"""
        if hasattr(source_model, "headers") and "상태" in source_model.headers:
            return source_model.headers.index("상태")
        return source_model.columnCount() - 1

    def get_filtered_row_count(self):
        """필터링된 행 수 반환"""
        return self.rowCount()

    def get_source_row_count(self):
        """원본 모델의 행 수 반환"""
        source_model = self.sourceModel()
        return source_model.rowCount() if source_model else 0

    def get_search_text(self):
        """현재 검색 텍스트 반환"""
        return self.search_text

    def clear_search(self):
        """검색 텍스트 초기화"""
        self.search_text = ""
        self.invalidateFilter()


class SearchWidget(QWidget):
    """검색 위젯 - 검색 입력 필드와 라벨을 포함"""

    search_text_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._emit_search_text)
        self._last_search_text = ""

    def init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        search_label = QLabel("🔍 검색:")
        search_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("제목, 경로, 시즌, 에피소드, 해상도, 코덱으로 검색...")
        self.search_input.setMinimumWidth(300)
        self.search_input.setStyleSheet(
            """
            QLineEdit {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                font-size: 12px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3498db;
                background-color: #f8f9fa;
            }
        """
        )
        layout.addWidget(self.search_input)
        self.search_input.textChanged.connect(self._on_text_changed)
        clear_button = QLabel("❌")
        clear_button.setStyleSheet(
            """
            QLabel {
                color: #e74c3c;
                font-size: 16px;
                padding: 5px;
            }
            QLabel:hover {
                color: #c0392b;
            }
        """
        )
        clear_button.mousePressEvent = self._clear_search
        layout.addWidget(clear_button)
        layout.addStretch(1)

    def _on_text_changed(self, text):
        """검색 텍스트 변경 시 디바운스 적용"""
        if text != self._last_search_text:
            self._last_search_text = text
            self.search_timer.start(250)

    def _emit_search_text(self):
        """디바운스 후 검색 텍스트 시그널 발생"""
        search_text = self.search_input.text().strip()
        self.search_text_changed.emit(search_text)

    def _clear_search(self, event):
        """검색 초기화"""
        self.search_input.clear()
        self._last_search_text = ""
        self.search_text_changed.emit("")

    def set_search_text(self, text):
        """검색 텍스트 설정"""
        self.search_input.setText(text)
        self._last_search_text = text


class TabFilterManager:
    """탭별 필터 관리자 - Phase 7: 검색 기능 추가"""

    def __init__(self, results_view):
        self.results_view = results_view
        self.filter_proxies = {}
        self.search_widgets = {}
        self.setup_filters()

    def setup_filters(self):
        """탭별 필터 설정"""
        self.filter_proxies = {
            "all": StatusFilterProxyModel("all"),
            "unmatched": StatusFilterProxyModel("unmatched"),
            "conflict": StatusFilterProxyModel("conflict"),
            "duplicate": StatusFilterProxyModel("duplicate"),
            "completed": StatusFilterProxyModel("completed"),
        }
        self._add_search_widgets_to_tabs()
        self._apply_filters_to_tables()

    def _add_search_widgets_to_tabs(self):
        """각 탭에 검색 위젯 추가"""
        tab_configs = [
            ("all", self.results_view.all_tab, self.results_view.all_group_table),
            ("unmatched", self.results_view.unmatched_tab, self.results_view.unmatched_group_table),
            ("conflict", self.results_view.conflict_tab, self.results_view.conflict_group_table),
            ("duplicate", self.results_view.duplicate_tab, self.results_view.duplicate_group_table),
            ("completed", self.results_view.completed_tab, self.results_view.completed_group_table),
        ]
        for tab_name, tab_widget, group_table in tab_configs:
            if tab_widget and group_table:
                search_widget = SearchWidget()
                self.search_widgets[tab_name] = search_widget
                search_widget.search_text_changed.connect(
                    lambda text, name=tab_name: self._on_search_text_changed(name, text)
                )
                tab_layout = tab_widget.layout()
                if tab_layout:
                    group_label_index = self._find_group_label_index(tab_layout)
                    if group_label_index >= 0:
                        tab_layout.insertWidget(group_label_index + 1, search_widget)
                    else:
                        tab_layout.insertWidget(0, search_widget)

    def _find_group_label_index(self, layout):
        """레이아웃에서 그룹 라벨의 인덱스 찾기"""
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and isinstance(widget, QLabel) and "애니메이션 그룹" in widget.text():
                return i
        return -1

    def _on_search_text_changed(self, tab_name, search_text):
        """탭별 검색 텍스트 변경 처리"""
        if tab_name in self.filter_proxies:
            self.filter_proxies[tab_name].set_search_text(search_text)

    def _apply_filters_to_tables(self):
        """필터를 각 탭의 테이블에 적용"""
        if hasattr(self.results_view, "all_group_table"):
            self.filter_proxies["all"].setSourceModel(self.results_view.all_group_table.model())
            self.results_view.all_group_table.setModel(self.filter_proxies["all"])
        if hasattr(self.results_view, "unmatched_group_table"):
            self.filter_proxies["unmatched"].setSourceModel(
                self.results_view.unmatched_group_table.model()
            )
            self.results_view.unmatched_group_table.setModel(self.filter_proxies["unmatched"])
        if hasattr(self.results_view, "conflict_group_table"):
            self.filter_proxies["conflict"].setSourceModel(
                self.results_view.conflict_group_table.model()
            )
            self.results_view.conflict_group_table.setModel(self.filter_proxies["conflict"])
        if hasattr(self.results_view, "duplicate_group_table"):
            self.filter_proxies["duplicate"].setSourceModel(
                self.results_view.duplicate_group_table.model()
            )
            self.results_view.duplicate_group_table.setModel(self.filter_proxies["duplicate"])
        if hasattr(self.results_view, "completed_group_table"):
            self.filter_proxies["completed"].setSourceModel(
                self.results_view.completed_group_table.model()
            )
            self.results_view.completed_group_table.setModel(self.filter_proxies["completed"])

    def update_source_model(self, source_model):
        """소스 모델 업데이트 (모든 필터에 적용)"""
        for proxy in self.filter_proxies.values():
            proxy.setSourceModel(source_model)

    def refresh_filters(self):
        """모든 필터 새로고침"""
        for proxy in self.filter_proxies.values():
            proxy.invalidateFilter()

    def get_filter_stats(self):
        """각 탭별 필터링된 행 수 통계 반환"""
        stats = {}
        for tab_name, proxy in self.filter_proxies.items():
            stats[tab_name] = {
                "filtered_count": proxy.get_filtered_row_count(),
                "source_count": proxy.get_source_row_count(),
                "search_text": proxy.get_search_text(),
            }
        return stats

    def set_filter_status(self, tab_name, status_filter):
        """특정 탭의 필터 상태 설정"""
        if tab_name in self.filter_proxies:
            self.filter_proxies[tab_name].set_status_filter(status_filter)
            self.filter_proxies[tab_name].invalidateFilter()

    def clear_all_search(self):
        """모든 탭의 검색 초기화"""
        for search_widget in self.search_widgets.values():
            search_widget.clear_search()

    def get_search_widget(self, tab_name):
        """특정 탭의 검색 위젯 반환"""
        return self.search_widgets.get(tab_name)
