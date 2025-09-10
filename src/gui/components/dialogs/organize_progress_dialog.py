"""
파일 정리 진행률 다이얼로그
파일 이동 작업의 진행률을 표시합니다.
"""

import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QProgressBar,
                             QPushButton, QTextEdit, QVBoxLayout)


@dataclass
class OrganizeResult:
    """파일 정리 결과"""

    success_count: int = 0
    error_count: int = 0
    skip_count: int = 0
    subtitle_count: int = 0
    cleaned_directories: int = 0
    errors: list[str] = None
    skipped_files: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.skipped_files is None:
            self.skipped_files = []


class OrganizeProgressDialog(QDialog):
    """파일 정리 진행률 다이얼로그"""

    def __init__(self, grouped_items: dict[str, list], destination_directory: str, parent=None):
        super().__init__(parent)
        self.grouped_items = grouped_items
        self.destination_directory = destination_directory
        self.worker = None
        self.result = None
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("📁 파일 정리 진행 중")
        self.setModal(True)
        self.setFixedSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        title_label = QLabel("파일 정리 중...")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("진행률: %p%")
        layout.addWidget(self.progress_bar)
        self.current_file_label = QLabel("대기 중...")
        self.current_file_label.setWordWrap(True)
        self.current_file_label.setStyleSheet(
            """
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
            }
        """
        )
        layout.addWidget(self.current_file_label)
        log_label = QLabel("처리 로그:")
        layout.addWidget(log_label)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        palette = self.palette()
        bg_color = palette.color(palette.Base).name()
        border_color = palette.color(palette.Mid).name()
        text_color = palette.color(palette.Text).name()
        self.log_text.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9px;
                color: {text_color};
            }}
        """
        )
        layout.addWidget(self.log_text)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_button = QPushButton("❌ 취소")
        self.cancel_button.setStyleSheet(
            """
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """
        )
        self.cancel_button.clicked.connect(self.cancel_operation)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def start_organization(self):
        """파일 정리 시작"""
        self.log_text.append("❌ 파일 정리 기능이 아직 구현되지 않았습니다.")
        self.cancel_button.setText("닫기")

    def update_progress(self, progress: int, current_file: str):
        """진행률 업데이트"""
        self.progress_bar.setValue(progress)
        self.current_file_label.setText(f"처리 중: {current_file}")

    def add_log(self, message: str):
        """로그 메시지 추가"""
        self.log_text.append(message)

    def cancel_operation(self):
        """작업 취소"""
        self.reject()

    def set_simulation_mode(self, enabled: bool):
        """시뮬레이션 모드 설정"""
        if enabled:
            self.setWindowTitle("📁 파일 정리 시뮬레이션")
            self.log_text.append("🔍 시뮬레이션 모드로 실행됩니다.")

    def get_result(self) -> OrganizeResult | None:
        """결과 반환"""
        return self.result
