"""
메인 툴바 컴포넌트
상단의 검색, 필터, 설정 버튼 등을 포함하는 툴바를 관리합니다.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class MainToolbar(QWidget):
    """메인 윈도우 상단 툴바"""

    # 시그널 정의
    organize_requested = pyqtSignal()  # 정리 실행 요청

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        # 앱 제목
        title_label = QLabel("🎬 AnimeSorter")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50;")
        title_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(title_label)

        layout.addStretch(1)

        # 검색 및 필터
        search_label = QLabel("🔍 검색:")
        search_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.search = QLineEdit()
        self.search.setPlaceholderText("제목, 경로로 검색...")
        self.search.setMinimumWidth(200)
        self.search.setMaximumWidth(400)
        self.search.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        status_label = QLabel("상태:")
        status_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.statusFilter = QComboBox()
        self.statusFilter.addItems(["전체", "parsed", "needs_review", "error"])
        self.statusFilter.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 정리 실행 버튼
        self.btnOrganize = QPushButton("📁 정리 실행")
        self.btnOrganize.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #ecf0f1;
            }
        """
        )
        self.btnOrganize.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btnOrganize.clicked.connect(self.organize_requested.emit)

        # 설정 버튼
        self.btnSettings = QPushButton("⚙️ 설정")
        self.btnSettings.setStyleSheet(
            """
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """
        )
        self.btnSettings.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout.addWidget(search_label)
        layout.addWidget(self.search)
        layout.addWidget(status_label)
        layout.addWidget(self.statusFilter)
        layout.addWidget(self.btnOrganize)
        layout.addWidget(self.btnSettings)

        # 툴바의 크기 정책 설정
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def get_search_text(self) -> str:
        """검색 텍스트 반환"""
        return self.search.text()

    def get_status_filter(self) -> str:
        """상태 필터 값 반환"""
        return self.statusFilter.currentText()

    def clear_search(self):
        """검색 텍스트 초기화"""
        self.search.clear()

    def reset_filters(self):
        """필터 초기화"""
        self.statusFilter.setCurrentIndex(0)
        self.search.clear()

    def set_organize_enabled(self, enabled: bool):
        """정리 실행 버튼 활성화/비활성화"""
        self.btnOrganize.setEnabled(enabled)
