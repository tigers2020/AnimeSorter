"""
새로운 결과 뷰 컴포넌트 - Phase 2.4 결과 뷰 컴포넌트 분할
탭별 독립 클래스들을 사용하여 간소화된 메인 결과 뷰입니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QSizePolicy, QTabWidget

from src.gui.components.delegates import StatusDelegate, TextPreviewDelegate
from src.gui.components.models import BaseDetailModel, BaseGroupModel
from src.gui.components.views import (AllTabView, CompletedTabView,
                                      ConflictTabView, DuplicateTabView,
                                      UnmatchedTabView)


class ResultsViewNew(QTabWidget):
    """새로운 결과 표시 뷰 (5개 탭 구조)"""

    group_selected = pyqtSignal(dict)
    group_double_clicked = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_models()
        self.setup_delegates()
        self.setup_connections()

    def init_ui(self):
        """UI 초기화"""
        self.create_tabs()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCurrentIndex(1)
        self.currentChanged.connect(self.on_tab_changed)

    def create_tabs(self):
        """5개 탭 생성"""
        self.all_tab_view = AllTabView()
        self.addTab(self.all_tab_view, "📋 전체")
        self.unmatched_tab_view = UnmatchedTabView()
        self.addTab(self.unmatched_tab_view, "⚠️ 미매칭")
        self.conflict_tab_view = ConflictTabView()
        self.addTab(self.conflict_tab_view, "💥 충돌")
        self.duplicate_tab_view = DuplicateTabView()
        self.addTab(self.duplicate_tab_view, "🔄 중복")
        self.completed_tab_view = CompletedTabView()
        self.addTab(self.completed_tab_view, "✅ 완료")

    def setup_models(self):
        """모델 설정"""
        self.all_group_model = BaseGroupModel()
        self.unmatched_group_model = BaseGroupModel()
        self.conflict_group_model = BaseGroupModel()
        self.duplicate_group_model = BaseGroupModel()
        self.completed_group_model = BaseGroupModel()
        self.all_detail_model = BaseDetailModel()
        self.unmatched_detail_model = BaseDetailModel()
        self.duplicate_detail_model = BaseDetailModel()
        self.conflict_detail_model = BaseDetailModel()
        self.completed_detail_model = BaseDetailModel()
        self._connect_models_to_tables()

    def _connect_models_to_tables(self):
        """모델을 테이블에 연결"""
        self.all_tab_view.get_group_table().setModel(self.all_group_model)
        self.all_tab_view.get_detail_table().setModel(self.all_detail_model)
        self.unmatched_tab_view.get_group_table().setModel(self.unmatched_group_model)
        self.unmatched_tab_view.get_detail_table().setModel(self.unmatched_detail_model)
        self.conflict_tab_view.get_group_table().setModel(self.conflict_group_model)
        self.conflict_tab_view.get_detail_table().setModel(self.conflict_detail_model)
        self.duplicate_tab_view.get_group_table().setModel(self.duplicate_group_model)
        self.duplicate_tab_view.get_detail_table().setModel(self.duplicate_detail_model)
        self.completed_tab_view.get_group_table().setModel(self.completed_group_model)
        self.completed_tab_view.get_detail_table().setModel(self.completed_detail_model)

    def setup_delegates(self):
        """델리게이트 설정"""
        self._apply_delegates_to_tab(self.all_tab_view, "all")
        self._apply_delegates_to_tab(self.unmatched_tab_view, "unmatched")
        self._apply_delegates_to_tab(self.conflict_tab_view, "conflict")
        self._apply_delegates_to_tab(self.duplicate_tab_view, "duplicate")
        self._apply_delegates_to_tab(self.completed_tab_view, "completed")

    def _apply_delegates_to_tab(self, tab_view, tab_name):
        """탭에 델리게이트 적용"""
        try:
            group_table = tab_view.get_group_table()
            detail_table = tab_view.get_detail_table()
            group_table.setItemDelegateForColumn(0, TextPreviewDelegate(group_table))
            group_table.setItemDelegateForColumn(5, StatusDelegate(group_table))
            detail_table.setItemDelegateForColumn(0, TextPreviewDelegate(detail_table))
            logger.info("✅ %s 탭 델리게이트 설정 완료", tab_name)
        except Exception as e:
            logger.info("❌ %s 탭 델리게이트 설정 실패: %s", tab_name, e)

    def setup_connections(self):
        """시그널 연결 설정"""
        self._connect_group_table_signals(self.all_tab_view, "all")
        self._connect_group_table_signals(self.unmatched_tab_view, "unmatched")
        self._connect_group_table_signals(self.conflict_tab_view, "conflict")
        self._connect_group_table_signals(self.duplicate_tab_view, "duplicate")
        self._connect_group_table_signals(self.completed_tab_view, "completed")

    def _connect_group_table_signals(self, tab_view, tab_name):
        """그룹 테이블 시그널 연결"""
        try:
            group_table = tab_view.get_group_table()
            group_table.selectionModel().selectionChanged.connect(
                lambda selected, deselected, tab=tab_name: self._on_group_selection_changed(
                    selected, deselected, tab
                )
            )
            group_table.doubleClicked.connect(
                lambda index, tab=tab_name: self._on_group_double_clicked(index, tab)
            )
            logger.info("✅ %s 탭 시그널 연결 완료", tab_name)
        except Exception as e:
            logger.info("❌ %s 탭 시그널 연결 실패: %s", tab_name, e)

    def _on_group_selection_changed(self, selected, deselected, tab_name):
        """그룹 선택 변경 처리"""
        if selected.indexes():
            index = selected.indexes()[0]
            group_data = self._get_group_data_from_tab(tab_name, index)
            if group_data:
                self.group_selected.emit(group_data)

    def _on_group_double_clicked(self, index, tab_name):
        """그룹 더블클릭 처리"""
        group_data = self._get_group_data_from_tab(tab_name, index)
        if group_data:
            self.group_double_clicked.emit(group_data)

    def _get_group_data_from_tab(self, tab_name, index):
        """탭에서 그룹 데이터 가져오기"""
        try:
            if tab_name == "all":
                return self.all_group_model.get_row_data(index.row())
            if tab_name == "unmatched":
                return self.unmatched_group_model.get_row_data(index.row())
            if tab_name == "conflict":
                return self.conflict_group_model.get_row_data(index.row())
            if tab_name == "duplicate":
                return self.duplicate_group_model.get_row_data(index.row())
            if tab_name == "completed":
                return self.completed_group_model.get_row_data(index.row())
        except Exception as e:
            logger.info("❌ %s 탭에서 그룹 데이터 가져오기 실패: %s", tab_name, e)
        return None

    def on_tab_changed(self, index):
        """탭 변경 처리"""
        tab_names = ["all", "unmatched", "conflict", "duplicate", "completed"]
        if 0 <= index < len(tab_names):
            logger.info("🔄 탭 변경: %s", tab_names[index])

    def get_all_group_table(self):
        """전체 탭 그룹 테이블 반환"""
        return self.all_tab_view.get_group_table()

    def get_all_detail_table(self):
        """전체 탭 상세 테이블 반환"""
        return self.all_tab_view.get_detail_table()

    def get_unmatched_group_table(self):
        """미매칭 탭 그룹 테이블 반환"""
        return self.unmatched_tab_view.get_group_table()

    def get_unmatched_detail_table(self):
        """미매칭 탭 상세 테이블 반환"""
        return self.unmatched_tab_view.get_detail_table()

    def get_conflict_group_table(self):
        """충돌 탭 그룹 테이블 반환"""
        return self.conflict_tab_view.get_group_table()

    def get_conflict_detail_table(self):
        """충돌 탭 상세 테이블 반환"""
        return self.conflict_tab_view.get_detail_table()

    def get_duplicate_group_table(self):
        """중복 탭 그룹 테이블 반환"""
        return self.duplicate_tab_view.get_group_table()

    def get_duplicate_detail_table(self):
        """중복 탭 상세 테이블 반환"""
        return self.duplicate_tab_view.get_detail_table()

    def get_completed_group_table(self):
        """완료 탭 그룹 테이블 반환"""
        return self.completed_tab_view.get_group_table()

    def get_completed_detail_table(self):
        """완료 탭 상세 테이블 반환"""
        return self.completed_tab_view.get_detail_table()

    def get_all_splitter(self):
        """전체 탭 스플리터 반환"""
        return self.all_tab_view.get_splitter()

    def get_unmatched_splitter(self):
        """미매칭 탭 스플리터 반환"""
        return self.unmatched_tab_view.get_splitter()

    def get_conflict_splitter(self):
        """충돌 탭 스플리터 반환"""
        return self.conflict_tab_view.get_splitter()

    def get_duplicate_splitter(self):
        """중복 탭 스플리터 반환"""
        return self.duplicate_tab_view.get_splitter()

    def get_completed_splitter(self):
        """완료 탭 스플리터 반환"""
        return self.completed_tab_view.get_splitter()
