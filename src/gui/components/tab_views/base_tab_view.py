"""
Tab View 베이스 클래스 - 중복 코드 제거를 위한 공통 기능 제공
"""

from PyQt5.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QLabel, QSizePolicy, QTableView, QVBoxLayout,
                             QWidget)

from src.advanced_splitter import AdvancedSplitter, SplitterControlPanel


class BaseTabView(QWidget):
    """Tab View 베이스 클래스 - 공통 기능 제공"""

    # 시그널 정의
    group_selected = pyqtSignal(dict)  # 그룹 정보
    group_double_clicked = pyqtSignal(dict)  # 그룹 더블클릭

    def __init__(self, title: str, group_label: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.group_label = group_label
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 탭 제목 라벨
        title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # 고급 스플리터로 분할
        self.splitter = AdvancedSplitter(Qt.Vertical)

        # 스플리터 제어 패널 추가
        self.control_panel = SplitterControlPanel(self.splitter)
        layout.addWidget(self.control_panel)

        # 상단: 그룹 리스트
        self.group_widget = self._create_group_section()
        self.splitter.addWidget(self.group_widget)

        # 하단: 상세 파일 목록
        self.detail_widget = self._create_detail_section()
        self.splitter.addWidget(self.detail_widget)

        # 스플리터 크기 설정
        self.splitter.setSizes([400, 300])

        layout.addWidget(self.splitter)

    def _create_group_section(self):
        """그룹 섹션 생성"""
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(5)

        group_label = QLabel(self.group_label)
        group_font = QFont()
        group_font.setPointSize(11)
        group_font.setBold(True)
        group_label.setFont(group_font)
        group_layout.addWidget(group_label)

        # 그룹 테이블 생성
        self.group_table = QTableView()
        self.group_table.verticalHeader().setVisible(False)
        self.group_table.setSelectionBehavior(QTableView.SelectRows)
        self.group_table.setAlternatingRowColors(True)
        self.group_table.setWordWrap(True)
        self.group_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 툴팁 활성화
        self.group_table.setMouseTracking(True)
        self.group_table.setToolTip(
            "애니메이션 그룹 목록 - 제목에 마우스를 올리면 포스터를 볼 수 있습니다"
        )

        # 성능 최적화 설정
        if hasattr(self.group_table, "setUniformRowHeights"):
            self.group_table.setUniformRowHeights(True)
        self.group_table.setHorizontalScrollMode(QTableView.ScrollPerPixel)

        group_layout.addWidget(self.group_table)
        return group_widget

    def _create_detail_section(self):
        """상세 섹션 생성"""
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(5)

        detail_label = QLabel("📄 파일 상세")
        detail_font = QFont()
        detail_font.setPointSize(11)
        detail_font.setBold(True)
        detail_label.setFont(detail_font)
        detail_layout.addWidget(detail_label)

        # 상세 테이블 생성
        self.detail_table = QTableView()
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setSelectionBehavior(QTableView.SelectRows)
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setWordWrap(True)
        self.detail_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 툴팁 활성화
        self.detail_table.setMouseTracking(True)
        self.detail_table.setToolTip("선택된 그룹의 파일 상세 정보")

        # 성능 최적화 설정
        if hasattr(self.detail_table, "setUniformRowHeights"):
            self.detail_table.setUniformRowHeights(True)
        self.detail_table.setHorizontalScrollMode(QTableView.ScrollPerPixel)

        detail_layout.addWidget(self.detail_table)
        return detail_widget

    def setup_connections(self):
        """시그널 연결 설정"""
        # 그룹 테이블 선택 변경
        self.group_table.selectionModel().selectionChanged.connect(self._on_group_selection_changed)

        # 그룹 테이블 더블클릭
        self.group_table.doubleClicked.connect(self._on_group_double_clicked)

    def _on_group_selection_changed(self, selected, deselected):
        """그룹 선택 변경 처리"""
        if selected.indexes():
            index = selected.indexes()[0]
            group_data = self._get_group_data_from_index(index)
            if group_data:
                self.group_selected.emit(group_data)

    def _on_group_double_clicked(self, index):
        """그룹 더블클릭 처리"""
        group_data = self._get_group_data_from_index(index)
        if group_data:
            self.group_double_clicked.emit(group_data)

    def _get_group_data_from_index(self, index: QModelIndex):
        """인덱스에서 그룹 데이터 추출"""
        if not index.isValid():
            return None

        # 모델에서 그룹 데이터 가져오기
        model = self.group_table.model()
        if model:
            return model.data(index, role=Qt.UserRole)
        return None

    def set_group_model(self, model):
        """그룹 모델 설정"""
        self.group_table.setModel(model)

    def set_detail_model(self, model):
        """상세 모델 설정"""
        self.detail_table.setModel(model)

    def refresh_views(self):
        """뷰 새로고침"""
        if hasattr(self.group_table, "viewport"):
            self.group_table.viewport().update()
        if hasattr(self.detail_table, "viewport"):
            self.detail_table.viewport().update()

    def get_selected_group_index(self):
        """선택된 그룹 인덱스 반환"""
        selection = self.group_table.selectionModel().selection()
        if selection.indexes():
            return selection.indexes()[0]
        return None

    def get_selected_detail_index(self):
        """선택된 상세 인덱스 반환"""
        selection = self.detail_table.selectionModel().selection()
        if selection.indexes():
            return selection.indexes()[0]
        return None
