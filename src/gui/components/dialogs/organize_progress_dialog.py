"""
파일 정리 진행률 다이얼로그
파일 이동 작업의 진행률을 표시합니다.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)
from dataclasses import dataclass

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.state.base_state import BaseState


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


class OrganizeProgressDialog(BaseState, QDialog):
    """파일 정리 진행률 다이얼로그"""

    def __init__(self, grouped_items: dict[str, list], destination_directory: str, parent=None):
        # Initialize QDialog first
        QDialog.__init__(self, parent)
        # Then initialize BaseState
        BaseState.__init__(self)
        self.grouped_items = grouped_items
        self.destination_directory = destination_directory
        self.is_cancelled = False
        self.is_organizing = False
        self.init_ui()

    def _get_default_state_config(self) -> Dict[str, Any]:
        """
        Get the default state configuration for this dialog.

        Returns:
            Dictionary containing default state configuration.
        """
        return {
            "managers": {"worker": None},
            "collections": {"grouped_items": "dict", "result": None},
            "strings": {"destination_directory": ""},
            "flags": {},
            "config": {},
        }

    def _initialize_state(self) -> None:
        """
        Initialize the dialog state with class-specific values.

        This method is called by BaseState during initialization and
        handles the specific state setup for this dialog.
        """
        # Call the parent's initialization first
        super()._initialize_state()

        # Set class-specific state that was passed in constructor
        self.grouped_items = getattr(self, "grouped_items", {})
        self.destination_directory = getattr(self, "destination_directory", "")

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
        self.is_cancelled = False
        self.is_organizing = True
        self.cancel_button.setText("❌ 취소")
        self.cancel_button.setEnabled(True)

        self.log_text.append("🚀 파일 정리 작업을 시작합니다...")
        self.log_text.append(f"📁 대상 디렉토리: {self.destination_directory}")
        self.log_text.append(f"📊 총 {len(self.grouped_items)} 개의 그룹을 처리합니다.")

        # Initialize result
        self.result = OrganizeResult()

        # Simulate organization process
        total_groups = len(self.grouped_items)
        processed_groups = 0

        for group_name, files in self.grouped_items.items():
            # Check for cancellation
            if self.is_cancelled:
                self.add_log("⚠️ 작업이 사용자에 의해 취소되었습니다.")
                self.update_progress(0, "취소됨")
                self.cancel_button.setText("닫기")
                self.is_organizing = False
                return

            if processed_groups >= total_groups:
                break

            # Update progress
            progress = int((processed_groups / total_groups) * 100)
            self.update_progress(progress, f"그룹 처리 중: {group_name}")

            # Simulate processing each file in the group
            for file_path in files:
                # Check for cancellation during file processing
                if self.is_cancelled:
                    self.add_log("⚠️ 작업이 사용자에 의해 취소되었습니다.")
                    self.update_progress(0, "취소됨")
                    self.cancel_button.setText("닫기")
                    self.is_organizing = False
                    return

                self.add_log(f"📄 처리 중: {file_path}")
                self.result.success_count += 1

            processed_groups += 1

        # Complete the process
        self.update_progress(100, "완료")
        self.add_log("✅ 파일 정리 작업이 완료되었습니다.")
        self.add_log(f"📈 성공: {self.result.success_count}개 파일")
        self.cancel_button.setText("닫기")
        self.is_organizing = False

    def update_progress(self, progress: int, current_file: str):
        """진행률 업데이트"""
        self.progress_bar.setValue(progress)
        self.current_file_label.setText(f"처리 중: {current_file}")

    def add_log(self, message: str):
        """로그 메시지 추가"""
        self.log_text.append(message)

    def cancel_operation(self):
        """작업 취소"""
        if self.is_organizing:
            # If currently organizing, set cancellation flag
            self.is_cancelled = True
            self.add_log("🛑 취소 요청됨...")
        else:
            # If not organizing, just close the dialog
            self.reject()

    def set_simulation_mode(self, enabled: bool):
        """시뮬레이션 모드 설정"""
        if enabled:
            self.setWindowTitle("📁 파일 정리 시뮬레이션")
            self.log_text.append("🔍 시뮬레이션 모드로 실행됩니다.")

    def get_result(self) -> OrganizeResult | None:
        """결과 반환"""
        return self.result

    def reset_dialog_state(self):
        """Reset the dialog state to its initial values.

        This method resets all dialog state variables and UI elements
        to their initial state, clearing any accumulated data from
        previous operations.
        """
        try:
            logger.info("🔄 Resetting OrganizeProgressDialog state...")

            # Use BaseState's reset functionality
            self.reset_all_states()

            # Reset UI elements to initial state
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("진행률: %p%")
            self.current_file_label.setText("대기 중...")
            self.log_text.clear()

            # Reset button state
            self.cancel_button.setText("❌ 취소")
            self.cancel_button.setEnabled(True)

            # Reset organization state
            self.is_cancelled = False
            self.is_organizing = False

            # Reset window title
            self.setWindowTitle("📁 파일 정리 진행 중")

            logger.info("✅ OrganizeProgressDialog state reset completed")

        except Exception as e:
            logger.error(f"❌ Error resetting OrganizeProgressDialog state: {e}")
            import traceback

            traceback.print_exc()

    def reset_state(self):
        """Public method to reset dialog state.

        This is an alias for reset_dialog_state() to maintain
        consistency with other components' reset methods.
        """
        self.reset_dialog_state()
