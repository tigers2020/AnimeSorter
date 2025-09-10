"""
3열 트리플 패널 레이아웃 - PRD 기반 구현
상세 패널 | 그룹 테이블 | 파일 목록 3열 구조
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QSizePolicy,
                             QSplitter, QTableView, QVBoxLayout, QWidget)

# 상세 패널 컴포넌트 import
from src.gui.components.group_detail_panel import GroupDetailPanel


class CentralTripleLayout(QWidget):
    """
    3열 트리플 패널 레이아웃 컴포넌트

    레이아웃: 상세 패널 | 그룹 테이블 | 파일 목록
    열 비율: 상세 300px 고정(clamp 280-360px) | 그룹 1.5fr | 파일 1fr
    """

    # 시그널 정의
    group_selection_changed = pyqtSignal(object)  # 그룹 선택 변경 시
    detail_panel_toggled = pyqtSignal(bool)  # 상세 패널 토글 시
    file_panel_toggled = pyqtSignal(bool)  # 파일 패널 토글 시

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        # 메인 레이아웃
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)  # 그리드 간격 8px

        # 메인 스플리터 생성
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(1)  # 컬럼 간 시각 구분선

        # 3개 패널 생성
        self.create_detail_panel()
        self.create_group_panel()
        self.create_file_panel()

        # 스플리터에 패널 추가
        self.main_splitter.addWidget(self.detail_panel)
        self.main_splitter.addWidget(self.group_panel)
        self.main_splitter.addWidget(self.file_panel)

        # 스플리터 비율 설정
        self.setup_splitter_ratios()

        # 메인 레이아웃에 스플리터 추가
        main_layout.addWidget(self.main_splitter)

        # 초기 상태 설정
        self.detail_visible = True
        self.file_visible = True

        # 사용자 토글 상태 추적
        self._user_detail_toggle = False
        self._user_file_toggle = False

        # 반응형 상태 추적
        self._responsive_mode = False

    def create_detail_panel(self):
        """상세 패널 생성"""
        self.detail_panel = QFrame()
        self.detail_panel.setFrameStyle(QFrame.StyledPanel)
        self.detail_panel.setMinimumWidth(280)
        self.detail_panel.setMaximumWidth(360)
        self.detail_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # 상세 패널 레이아웃
        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setSpacing(8)

        # 헤더
        header_label = QLabel("그룹 상세")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        detail_layout.addWidget(header_label)

        # 실제 상세 패널 컴포넌트
        self.group_detail_panel = GroupDetailPanel()
        detail_layout.addWidget(self.group_detail_panel)

    def create_group_panel(self):
        """그룹 테이블 패널 생성"""
        self.group_panel = QFrame()
        self.group_panel.setFrameStyle(QFrame.StyledPanel)
        self.group_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 그룹 패널 레이아웃
        group_layout = QVBoxLayout(self.group_panel)
        group_layout.setContentsMargins(12, 12, 12, 12)
        group_layout.setSpacing(8)

        # 헤더
        header_label = QLabel("애니메이션 그룹")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        group_layout.addWidget(header_label)

        # 필터 칩들 (임시)
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(6)

        filter_chips = ["전체", "미매칭", "충돌", "중복", "완료"]
        for chip_text in filter_chips:
            chip = QLabel(chip_text)
            chip.setStyleSheet(
                """
                QLabel {
                    background: #343a44;
                    border-radius: 999px;
                    padding: 4px 10px;
                    font-size: 12px;
                    color: #c9cfda;
                }
            """
            )
            filter_layout.addWidget(chip)

        filter_layout.addStretch()
        group_layout.addLayout(filter_layout)

        # 그룹 테이블
        self.group_table = QTableView()
        self.group_table.setStyleSheet(
            """
            QTableView {
                background: #2a2f37;
                border: 1px solid #323844;
                border-radius: 8px;
            }
            QHeaderView::section {
                background: #20252c;
                padding: 9px 10px;
                border-bottom: 1px solid #323844;
                font-weight: 600;
            }
        """
        )
        group_layout.addWidget(self.group_table)

    def create_file_panel(self):
        """파일 목록 패널 생성"""
        self.file_panel = QFrame()
        self.file_panel.setFrameStyle(QFrame.StyledPanel)
        self.file_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 파일 패널 레이아웃
        file_layout = QVBoxLayout(self.file_panel)
        file_layout.setContentsMargins(12, 12, 12, 12)
        file_layout.setSpacing(8)

        # 헤더
        header_label = QLabel("선택된 그룹의 파일들")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        file_layout.addWidget(header_label)

        # 파일 테이블
        self.file_table = QTableView()
        self.file_table.setStyleSheet(
            """
            QTableView {
                background: #2a2f37;
                border: 1px solid #323844;
                border-radius: 8px;
            }
            QHeaderView::section {
                background: #20252c;
                padding: 9px 10px;
                border-bottom: 1px solid #323844;
                font-weight: 600;
            }
        """
        )
        file_layout.addWidget(self.file_table)

    def setup_splitter_ratios(self):
        """스플리터 비율 설정"""
        # 상세 패널: 고정 너비 (300px)
        self.main_splitter.setStretchFactor(0, 0)  # 상세는 고정

        # 그룹 테이블: 1.5fr
        self.main_splitter.setStretchFactor(1, 3)  # 1.5배 가중치

        # 파일 목록: 1fr
        self.main_splitter.setStretchFactor(2, 2)  # 1배 가중치

    def set_detail_visible(self, visible: bool, user_toggle: bool = False):
        """상세 패널 표시/숨김 설정"""
        self.detail_visible = visible
        self.detail_panel.setVisible(visible)

        # 사용자 토글 상태 추적
        if user_toggle:
            self._user_detail_toggle = True

        self.detail_panel_toggled.emit(visible)

    def set_file_visible(self, visible: bool, user_toggle: bool = False):
        """파일 패널 표시/숨김 설정"""
        self.file_visible = visible
        self.file_panel.setVisible(visible)

        # 사용자 토글 상태 추적
        if user_toggle:
            self._user_file_toggle = True

        self.file_panel_toggled.emit(visible)

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

    def update_detail_from_group(self, group_data: dict):
        """그룹 데이터로 상세 패널 업데이트"""
        self.group_detail_panel.update_from_group(group_data)

    def connect_group_selection(self, slot):
        """그룹 선택 시그널 연결"""
        self.group_table.selectionModel().currentRowChanged.connect(slot)

    def handle_responsive_layout(self, window_width: int):
        """반응형 레이아웃 처리 (MainWindow에서 호출)"""
        # 브레이크포인트별 레이아웃 조정
        if window_width >= 1600:
            # 3열 유지 (기본 상태)
            self._apply_three_column_layout()
        elif 1400 <= window_width < 1600:
            # 파일 패널 자동 접힘 (사용자 토글 우선)
            self._apply_two_column_layout_hide_file()
        elif 1280 <= window_width < 1400:
            # 상세 패널 자동 접힘 (사용자 토글 우선)
            self._apply_one_column_layout_hide_detail()
        else:
            # <1280px: 좌측 도크 접힘은 MainWindow에서 처리
            pass

    def _apply_three_column_layout(self):
        """3열 레이아웃 적용"""
        # 사용자 토글이 있으면 우선 적용
        if self._user_detail_toggle:
            self.set_detail_visible(True, False)
        if self._user_file_toggle:
            self.set_file_visible(True, False)
        else:
            # 기본 3열 상태로 복원
            self.set_detail_visible(True, False)
            self.set_file_visible(True, False)

    def _apply_two_column_layout_hide_file(self):
        """2열 레이아웃 적용 (파일 패널 숨김)"""
        # 사용자 토글이 있으면 우선 적용
        if self._user_detail_toggle:
            self.set_detail_visible(True, False)
        if self._user_file_toggle:
            self.set_file_visible(True, False)
        else:
            # 상세 + 그룹만 표시
            self.set_detail_visible(True, False)
            self.set_file_visible(False, False)

    def _apply_one_column_layout_hide_detail(self):
        """1열 레이아웃 적용 (상세 패널 숨김)"""
        # 사용자 토글이 있으면 우선 적용
        if self._user_detail_toggle:
            self.set_detail_visible(True, False)
        if self._user_file_toggle:
            self.set_file_visible(True, False)
        else:
            # 그룹만 표시
            self.set_detail_visible(False, False)
            self.set_file_visible(False, False)

    def reset_user_toggles(self):
        """사용자 토글 상태 초기화"""
        self._user_detail_toggle = False
        self._user_file_toggle = False

    def resizeEvent(self, event):
        """리사이즈 이벤트 처리"""
        super().resizeEvent(event)
        # 반응형 처리는 MainWindow에서 호출
