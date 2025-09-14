"""
단순 2-pane 중앙 레이아웃 - Fluent UI 리팩토링
좌측: 그룹 테이블 | 우측: 파일 목록
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)


class CentralSimpleLayout(QWidget):
    """
    단순 2-pane 중앙 레이아웃 컴포넌트

    레이아웃: 그룹 테이블 | 파일 목록
    비율: 그룹 1fr | 파일 1fr (사용자가 조절 가능)
    """

    group_selection_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # 메인 스플리터 생성
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(8)

        # 패널들 생성
        self.create_group_panel()
        self.create_file_panel()

        # 스플리터에 패널 추가
        self.main_splitter.addWidget(self.group_panel)
        self.main_splitter.addWidget(self.file_panel)

        # 스플리터 비율 설정 (1:1)
        self.setup_splitter_ratios()

        main_layout.addWidget(self.main_splitter)

    def create_group_panel(self):
        """그룹 패널 생성"""
        self.group_panel = QFrame()
        self.group_panel.setFrameStyle(QFrame.StyledPanel)
        self.group_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(self.group_panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 그룹 테이블 제목
        title_label = QLabel("📁 애니메이션 그룹")
        title_label.setProperty("class", "title-label")
        layout.addWidget(title_label)

        # 그룹 테이블
        self.group_table = QTableView()
        self.group_table.setObjectName("groupTable")
        self.group_table.setAlternatingRowColors(True)
        self.group_table.setSelectionBehavior(QTableView.SelectRows)
        self.group_table.setSelectionMode(QTableView.SingleSelection)
        self.group_table.setSortingEnabled(True)
        self.group_table.horizontalHeader().setStretchLastSection(True)
        self.group_table.verticalHeader().setVisible(False)

        layout.addWidget(self.group_table)

    def create_file_panel(self):
        """파일 패널 생성"""
        self.file_panel = QFrame()
        self.file_panel.setFrameStyle(QFrame.StyledPanel)
        self.file_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(self.file_panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 파일 테이블 제목
        title_label = QLabel("🎬 파일 목록")
        title_label.setProperty("class", "title-label")
        layout.addWidget(title_label)

        # 파일 테이블
        self.file_table = QTableView()
        self.file_table.setObjectName("fileTable")
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSelectionBehavior(QTableView.SelectRows)
        self.file_table.setSelectionMode(QTableView.ExtendedSelection)
        self.file_table.setSortingEnabled(True)
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.verticalHeader().setVisible(False)

        layout.addWidget(self.file_table)

    def setup_splitter_ratios(self):
        """스플리터 비율 설정 (1:1)"""
        # 기본 크기 설정 (각각 50%)
        self.main_splitter.setSizes([400, 400])
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)

    def get_splitter_sizes(self):
        """스플리터 크기 반환"""
        return self.main_splitter.sizes()

    def set_splitter_sizes(self, sizes):
        """스플리터 크기 설정"""
        self.main_splitter.setSizes(sizes)

    def set_group_table_model(self, model):
        """그룹 테이블 모델 설정"""
        self.group_table.setModel(model)

    def set_file_table_model(self, model):
        """파일 테이블 모델 설정"""
        self.file_table.setModel(model)

    def connect_group_selection(self, slot):
        """그룹 선택 시그널 연결"""
        self.group_table.selectionModel().currentRowChanged.connect(slot)

    def get_selected_group_index(self):
        """선택된 그룹 인덱스 반환"""
        selection = self.group_table.selectionModel()
        if selection.hasSelection():
            return selection.currentIndex().row()
        return -1

    def get_selected_file_indices(self):
        """선택된 파일 인덱스들 반환"""
        selection = self.file_table.selectionModel()
        if selection.hasSelection():
            return [index.row() for index in selection.selectedRows()]
        return []

    def clear_group_selection(self):
        """그룹 선택 해제"""
        self.group_table.clearSelection()

    def clear_file_selection(self):
        """파일 선택 해제"""
        self.file_table.clearSelection()

    def refresh_tables(self):
        """테이블 새로고침"""
        if self.group_table.model():
            self.group_table.model().layoutChanged.emit()
        if self.file_table.model():
            self.file_table.model().layoutChanged.emit()
