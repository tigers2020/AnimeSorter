"""
중복 탭 뷰 클래스 - Phase 2.1 결과 뷰 컴포넌트 분할
중복 탭의 UI와 로직을 담당하는 독립적인 클래스입니다.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QLabel,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..advanced_splitter import AdvancedSplitter, SplitterControlPanel


class DuplicateTabView(QWidget):
    """중복 탭 뷰 클래스"""

    # 시그널 정의
    group_selected = pyqtSignal(dict)  # 그룹 정보
    group_double_clicked = pyqtSignal(dict)  # 그룹 더블클릭

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 탭 제목 라벨
        title_label = QLabel("🔄 중복")
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

        # 고급 스플리터 설정
        self.splitter.set_minimum_sizes([200, 150])  # 최소 크기 보장
        self.splitter.set_preferred_ratios([0.6, 0.4])  # 선호 비율 설정

        # 스플리터 상태 로드
        self.splitter.load_splitter_state()

        layout.addWidget(self.splitter)

    def _create_group_section(self):
        """그룹 섹션 생성"""
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
            "중복 애니메이션 그룹 목록 - 제목에 마우스를 올리면 포스터를 볼 수 있습니다"
        )

        # 성능 최적화 설정
        if hasattr(self.group_table, "setUniformRowHeights"):
            self.group_table.setUniformRowHeights(True)
        self.group_table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.group_table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.group_table.setShowGrid(False)

        group_layout.addWidget(self.group_table)
        return group_widget

    def _create_detail_section(self):
        """상세 섹션 생성"""
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

        # 상세 테이블 생성
        self.detail_table = QTableView()
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setSelectionBehavior(QTableView.SelectRows)
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setWordWrap(True)
        self.detail_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 툴팁 활성화
        self.detail_table.setMouseTracking(True)
        self.detail_table.setToolTip(
            "파일 상세 목록 - 파일명에 마우스를 올리면 포스터를 볼 수 있습니다"
        )

        # 성능 최적화 설정
        if hasattr(self.detail_table, "setUniformRowHeights"):
            self.detail_table.setUniformRowHeights(True)
        self.detail_table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.detail_table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.detail_table.setShowGrid(False)

        detail_layout.addWidget(self.detail_table)
        return detail_widget

    def setup_connections(self):
        """시그널 연결 설정"""
        # 그룹 테이블 시그널 연결
        self.group_table.selectionModel().selectionChanged.connect(self._on_group_selection_changed)
        self.group_table.doubleClicked.connect(self._on_group_double_clicked)

    def _on_group_selection_changed(self, selected, deselected):
        """그룹 선택 변경 처리"""
        if selected.indexes():
            # 그룹 선택 시그널 발생
            # 실제 구현은 모델에서 데이터를 가져와서 처리
            pass

    def _on_group_double_clicked(self, index):
        """그룹 더블클릭 처리"""
        # 그룹 더블클릭 시그널 발생
        # 실제 구현은 모델에서 데이터를 가져와서 처리

    def get_group_table(self):
        """그룹 테이블 반환"""
        return self.group_table

    def get_detail_table(self):
        """상세 테이블 반환"""
        return self.detail_table

    def get_splitter(self):
        """스플리터 반환"""
        return self.splitter

    def get_control_panel(self):
        """제어 패널 반환"""
        return self.control_panel
