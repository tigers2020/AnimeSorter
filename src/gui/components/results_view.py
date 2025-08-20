"""
결과 뷰 컴포넌트
테이블 뷰와 트리 뷰를 포함하는 결과 표시 영역을 관리합니다.
"""

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


class ResultsView(QTabWidget):
    """결과 표시 뷰 (그룹 리스트 중심)"""

    # 시그널 정의
    group_selected = pyqtSignal(dict)  # 그룹 정보
    group_double_clicked = pyqtSignal(dict)  # 그룹 더블클릭

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        # 결과 헤더
        self.create_results_header()

        # 그룹 리스트 뷰 (메인)
        self.group_table = QTableView()
        self.group_table.verticalHeader().setVisible(False)
        self.group_table.setSelectionBehavior(QTableView.SelectRows)
        self.group_table.setAlternatingRowColors(True)
        self.group_table.setWordWrap(True)
        self.group_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 상세 파일 목록 (그룹 선택 시 표시)
        self.detail_table = QTableView()
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setSelectionBehavior(QTableView.SelectRows)
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setWordWrap(True)
        self.detail_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 스플리터로 분할
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)  # 패널이 완전히 접히지 않도록
        self.splitter.setHandleWidth(6)  # 핸들 너비 설정

        # 상단: 그룹 리스트
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(5)

        group_label = QLabel("📋 애니메이션 그룹")
        group_font = QFont()
        group_font.setPointSize(12)
        group_font.setBold(True)
        group_label.setFont(group_font)
        group_layout.addWidget(group_label)
        group_layout.addWidget(self.group_table)

        # 하단: 상세 파일 목록
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(5)

        detail_label = QLabel("📁 선택된 그룹의 파일들")
        detail_font = QFont()
        detail_font.setPointSize(12)
        detail_font.setBold(True)
        detail_label.setFont(detail_font)
        detail_layout.addWidget(detail_label)
        detail_layout.addWidget(self.detail_table)

        # 스플리터에 추가
        self.splitter.addWidget(group_widget)
        self.splitter.addWidget(detail_widget)

        # 스플리터 비율 설정 (반응형)
        self.splitter.setSizes([400, 300])  # 초기 비율
        self.splitter.setStretchFactor(0, 2)  # 그룹 리스트가 더 큰 비율
        self.splitter.setStretchFactor(1, 1)  # 상세 목록은 작은 비율

        # 탭 추가 (그룹 리스트만 사용)
        self.addTab(self.splitter, "📋 그룹별 보기")

        # 크기 정책 설정
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setup_connections(self):
        """시그널 연결 설정"""
        # 그룹 테이블 연결
        if self.group_table.selectionModel():
            self.group_table.selectionModel().selectionChanged.connect(
                self.on_group_selection_changed
            )
            self.group_table.doubleClicked.connect(self.on_group_double_clicked)

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

        # 헤더를 탭 위젯 위에 추가
        self.setCornerWidget(header_widget, Qt.TopLeftCorner)

    def set_group_model(self, model):
        """그룹 리스트 모델 설정"""
        self.group_table.setModel(model)

        # 모델에서 컬럼 정보를 가져와서 설정
        if hasattr(model, "get_column_widths"):
            self.adjust_group_table_columns(model)
        else:
            # 기본 설정 (기존 코드)
            self.group_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            self.group_table.setColumnWidth(0, 120)

            for i in range(1, model.columnCount()):
                self.group_table.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeToContents
                )

            self.group_table.horizontalHeader().setStretchLastSection(True)

        # 모델 설정 후 시그널 연결
        self.setup_connections()

    def set_detail_model(self, model):
        """상세 파일 목록 모델 설정"""
        self.detail_table.setModel(model)

        # 모델에서 컬럼 정보를 가져와서 설정
        if hasattr(model, "get_column_widths"):
            self.adjust_detail_table_columns(model)
        else:
            # 기본 설정 (기존 코드)
            self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
            self.detail_table.setColumnWidth(0, 120)

            for i in range(1, model.columnCount()):
                self.detail_table.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeToContents
                )

            self.detail_table.horizontalHeader().setStretchLastSection(True)

    def adjust_group_table_columns(self, model):
        """그룹 테이블 컬럼 크기 조정"""
        header = self.group_table.horizontalHeader()
        column_widths = model.get_column_widths()
        stretch_columns = model.get_stretch_columns()

        for col in range(header.count()):
            if col in stretch_columns:
                header.setSectionResizeMode(col, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(col, QHeaderView.Fixed)
                if col in column_widths:
                    header.resizeSection(col, column_widths[col])

    def adjust_detail_table_columns(self, model):
        """상세 테이블 컬럼 크기 조정"""
        header = self.detail_table.horizontalHeader()
        column_widths = model.get_column_widths()
        stretch_columns = model.get_stretch_columns()

        for col in range(header.count()):
            if col in stretch_columns:
                header.setSectionResizeMode(col, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(col, QHeaderView.Fixed)
                if col in column_widths:
                    header.resizeSection(col, column_widths[col])

    def on_group_selection_changed(self, selected, deselected):
        """그룹 선택 변경 시 호출"""
        indexes = selected.indexes()
        if indexes:
            row = indexes[0].row()
            model = self.group_table.model()
            if model:
                group = model.get_group_at_row(row)
                if group:
                    self.group_selected.emit(group)

    def on_group_double_clicked(self, index):
        """그룹 더블클릭 시 호출"""
        model = self.group_table.model()
        if model:
            group = model.get_group_at_row(index.row())
            if group:
                self.group_double_clicked.emit(group)

    def get_selected_group_row(self):
        """그룹 테이블에서 선택된 행 반환"""
        selection = self.group_table.selectionModel()
        if not selection.hasSelection():
            return -1

        indexes = selection.selectedRows()
        if indexes:
            return indexes[0].row()
        return -1
