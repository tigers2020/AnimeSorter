"""
결과 뷰 컴포넌트
테이블 뷰와 트리 뷰를 포함하는 결과 표시 영역을 관리합니다.
"""

from PyQt5.QtWidgets import (
    QTabWidget, QTableView, QTreeWidget, QHeaderView, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class ResultsView(QTabWidget):
    """결과 표시 뷰 (그룹 리스트 중심)"""
    
    # 시그널 정의
    group_selected = pyqtSignal(dict)  # 그룹 정보
    group_double_clicked = pyqtSignal(dict)  # 그룹 더블클릭
    bulk_action_requested = pyqtSignal()
    smart_filter_requested = pyqtSignal()
    
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
        
        # 상세 파일 목록 (그룹 선택 시 표시)
        self.detail_table = QTableView()
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setSelectionBehavior(QTableView.SelectRows)
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setWordWrap(True)
        
        # 스플리터로 분할
        self.splitter = QSplitter(Qt.Vertical)
        
        # 상단: 그룹 리스트
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        
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
        
        detail_label = QLabel("📁 선택된 그룹의 파일들")
        detail_font = QFont()
        detail_font.setPointSize(12)
        detail_font.setBold(True)
        detail_label.setFont(group_font)
        detail_layout.addWidget(detail_label)
        detail_layout.addWidget(self.detail_table)
        
        # 스플리터에 추가
        self.splitter.addWidget(group_widget)
        self.splitter.addWidget(detail_widget)
        self.splitter.setSizes([400, 300])
        
        # 탭 추가 (그룹 리스트만 사용)
        self.addTab(self.splitter, "📋 그룹별 보기")
        
    def setup_connections(self):
        """시그널 연결 설정"""
        # 그룹 테이블 연결
        if self.group_table.selectionModel():
            self.group_table.selectionModel().selectionChanged.connect(self.on_group_selection_changed)
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
        
        # 스마트 필터 및 벌크 액션 버튼
        self.btnSmartFilter = QPushButton("🧠 스마트 필터")
        self.btnSmartFilter.setStyleSheet(self.get_button_style("#9b59b6"))
        self.btnSmartFilter.clicked.connect(self.smart_filter_requested.emit)
        
        self.btnBulk = QPushButton("📦 일괄 작업...")
        self.btnBulk.setStyleSheet(self.get_button_style("#e67e22"))
        self.btnBulk.clicked.connect(self.bulk_action_requested.emit)
        
        layout.addWidget(self.btnSmartFilter)
        layout.addWidget(self.btnBulk)
        
        # 헤더를 탭 위젯 위에 추가
        self.setCornerWidget(header_widget, Qt.TopLeftCorner)
        
    def set_group_model(self, model):
        """그룹 리스트 모델 설정"""
        self.group_table.setModel(model)
        
        # 포스터 컬럼 너비 고정 (이미지 표시용)
        self.group_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.group_table.setColumnWidth(0, 120)  # 포스터 컬럼 너비 증가
        
        # 나머지 컬럼은 자동 크기 조정
        for i in range(1, model.columnCount()):
            self.group_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.group_table.horizontalHeader().setStretchLastSection(True)
        
        # 모델 설정 후 시그널 연결
        self.setup_connections()
        
    def set_detail_model(self, model):
        """상세 파일 목록 모델 설정"""
        self.detail_table.setModel(model)
        
        # 포스터 컬럼 너비 고정
        self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.detail_table.setColumnWidth(0, 120)  # 포스터 컬럼 너비 증가
        
        # 나머지 컬럼은 자동 크기 조정
        for i in range(1, model.columnCount()):
            self.detail_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.detail_table.horizontalHeader().setStretchLastSection(True)
        
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
    
    def get_button_style(self, color: str) -> str:
        """버튼 스타일 생성"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
        """
