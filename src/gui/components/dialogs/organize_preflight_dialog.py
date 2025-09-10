"""
정리 실행 프리플라이트 다이얼로그
파일 정리 실행 전 요약 정보를 표시하고 사용자 확인을 받습니다.
"""

import logging

logger = logging.getLogger(__name__)
import re
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPushButton,
                             QTextEdit, QVBoxLayout)


class OrganizePreflightDialog(QDialog):
    """정리 실행 프리플라이트 확인 다이얼로그"""

    proceed_requested = pyqtSignal()

    def __init__(self, grouped_items: dict[str, list], destination_directory: str, parent=None):
        super().__init__(parent)
        self.grouped_items = grouped_items
        self.destination_directory = destination_directory
        self.is_preview_mode = False
        self.init_ui()
        self.generate_summary()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("📁 정리 실행 확인")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.setStyleSheet(
            """
            QDialog {
                background-color: palette(window);
                color: palette(window-text);
            }
            QLabel {
                color: palette(window-text);
            }
        """
        )
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        title_label = QLabel("파일 정리 실행을 시작합니다")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(300)
        self.summary_text.setStyleSheet(
            """
            QTextEdit {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """
        )
        layout.addWidget(self.summary_text)
        warning_label = QLabel(
            "⚠️ 주의사항: 이 작업은 파일을 실제로 이동시킵니다. 원본 파일은 삭제됩니다."
        )
        warning_label.setStyleSheet(
            """
            QLabel {
                color: palette(button-text);
                background-color: palette(light);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }
        """
        )
        layout.addWidget(warning_label)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_button = QPushButton("❌ 취소")
        self.cancel_button.setStyleSheet(
            """
            QPushButton {
                background-color: palette(button);
                color: palette(button-text);
                border: 1px solid palette(mid);
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: palette(light);
            }
        """
        )
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        self.proceed_button = QPushButton("✅ 진행")
        self.proceed_button.setStyleSheet(
            """
            QPushButton {
                background-color: palette(button);
                color: palette(button-text);
                border: 1px solid palette(mid);
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: palette(light);
            }
        """
        )
        self.proceed_button.clicked.connect(self.on_proceed_clicked)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.proceed_button)
        layout.addLayout(button_layout)
        subtitle_section = QLabel("📝 자막 파일 처리")
        subtitle_section.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(subtitle_section)
        subtitle_info = QLabel(
            """• 비디오 파일과 연관된 자막 파일(.srt, .ass, .ssa, .sub, .vtt, .idx, .smi, .sami, .txt)이 자동으로 함께 이동됩니다
• 파일명이 일치하는 자막 파일이 자동으로 감지되어 같은 폴더에 배치됩니다
• 언어 코드가 포함된 자막 파일(예: .ko.srt, .en.ass)도 지원됩니다"""
        )
        subtitle_info.setWordWrap(True)
        layout.addWidget(subtitle_info)
        cleanup_section = QLabel("🗑️ 빈 디렉토리 정리")
        cleanup_section.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(cleanup_section)
        cleanup_info = QLabel(
            """• 파일 이동 완료 후 소스 폴더의 빈 디렉토리들이 자동으로 삭제됩니다
• 하위 디렉토리부터 상위 디렉토리 순으로 재귀적으로 정리됩니다
• 소스 폴더가 깔끔하게 정리되어 불필요한 폴더 구조가 제거됩니다"""
        )
        cleanup_info.setWordWrap(True)
        layout.addWidget(cleanup_info)
        self.proceed_button.setFocus()

    def generate_summary(self):
        """요약 정보 생성"""
        try:
            summary_lines = []
            total_groups = 0
            total_files = 0
            total_size_mb = 0
            sample_paths = []
            for group_id, group_items in self.grouped_items.items():
                if group_id == "ungrouped":
                    continue
                total_groups += 1
                total_files += len(group_items)
                for item in group_items:
                    if (
                        hasattr(item, "sourcePath")
                        and item.sourcePath
                        and Path(item.sourcePath).exists()
                    ):
                        try:
                            file_size = Path(item.sourcePath).stat().st_size
                            total_size_mb += file_size / (1024 * 1024)
                        except OSError:
                            pass
                if len(sample_paths) < 5 and group_items:
                    representative = group_items[0]
                    sample_path = self._generate_sample_path(representative)
                    if sample_path:
                        sample_paths.append(sample_path)
            summary_lines.append("📊 정리 실행 요약")
            summary_lines.append("=" * 50)
            summary_lines.append(f"• 총 그룹: {total_groups}개")
            summary_lines.append(f"• 총 파일: {total_files}개 (비디오 파일)")
            summary_lines.append(f"• 예상 크기: {total_size_mb:.1f} MB")
            summary_lines.append(f"• 대상 폴더: {self.destination_directory}")
            summary_lines.append("")
            if sample_paths:
                summary_lines.append("📁 샘플 대상 경로:")
                summary_lines.append("-" * 30)
                for i, path in enumerate(sample_paths, 1):
                    summary_lines.append(f"{i}. {path}")
                summary_lines.append("")
                if len(sample_paths) < total_groups:
                    summary_lines.append(f"... 및 {total_groups - len(sample_paths)}개 그룹 더")
                    summary_lines.append("")
            summary_lines.append("📂 예상 생성 디렉토리:")
            summary_lines.append("-" * 30)
            summary_lines.append(f"• 애니메이션 폴더: {total_groups}개")
            summary_lines.append(f"• 시즌 폴더: {total_groups}개 (기본값)")
            summary_lines.append("")
            summary_lines.append("📝 자막 파일 처리:")
            summary_lines.append("-" * 30)
            summary_lines.append(
                "• 연관된 자막 파일(.srt, .ass, .ssa 등)이 자동으로 함께 이동됩니다"
            )
            summary_lines.append("• 자막 파일은 비디오 파일과 같은 폴더에 배치됩니다")
            summary_lines.append("")
            summary_lines.append("⚠️ 주의사항:")
            summary_lines.append("-" * 30)
            summary_lines.append("• 원본 파일이 이동되어 삭제됩니다")
            summary_lines.append("• 동일한 파일명이 있으면 자동으로 번호가 추가됩니다")
            summary_lines.append("• 특수문자는 파일명에서 제거됩니다")
            summary_lines.append("• 작업 중 취소할 수 있습니다")
            self.summary_text.setPlainText("\n".join(summary_lines))
        except Exception as e:
            error_text = f"요약 생성 중 오류가 발생했습니다:\n{str(e)}"
            self.summary_text.setPlainText(error_text)

    def _generate_sample_path(self, representative):
        """샘플 경로 생성"""
        try:
            if (
                hasattr(representative, "tmdbMatch")
                and representative.tmdbMatch
                and representative.tmdbMatch.name
            ):
                raw_title = representative.tmdbMatch.name
            else:
                raw_title = representative.title or representative.detectedTitle or "Unknown"
            safe_title = re.sub("[^a-zA-Z0-9가-힣\\s]", "", raw_title)
            safe_title = re.sub("\\s+", " ", safe_title)
            safe_title = safe_title.strip()
            if not safe_title:
                safe_title = "Unknown"
            season = representative.season or 1
            season_folder = f"Season{season:02d}"
            if hasattr(representative, "filename") and representative.filename:
                filename = representative.filename
            elif hasattr(representative, "sourcePath") and representative.sourcePath:
                filename = Path(representative.sourcePath).name
            else:
                filename = "example.mkv"
            return f"{self.destination_directory}/{safe_title}/{season_folder}/{filename}"
        except Exception as e:
            logger.info("⚠️ 샘플 경로 생성 실패: %s", e)
            return None

    def on_cancel_clicked(self):
        """취소 버튼 클릭 처리"""
        self.reject()

    def on_proceed_clicked(self):
        """진행 버튼 클릭 처리"""
        self.proceed_requested.emit()
        self.accept()

    def set_preview_mode(self, is_preview: bool):
        """미리보기 모드 설정"""
        self.is_preview_mode = is_preview
        if is_preview:
            self.setWindowTitle("👁️ 정리 미리보기")
            title_label = self.findChild(QLabel, "")
            if title_label and title_label.text() == "파일 정리 실행을 시작합니다":
                title_label.setText("파일 정리 미리보기")
            if hasattr(self, "proceed_button"):
                self.proceed_button.setText("✅ 확인")
                self.proceed_button.setToolTip("미리보기 확인")
            warning_label = self.findChild(QLabel, "")
            if (
                warning_label
                and "⚠️ 주의사항: 이 작업은 파일을 실제로 이동시킵니다" in warning_label.text()
            ):
                warning_label.setText("👁️ 미리보기 모드: 실제 파일 이동은 실행되지 않습니다.")
                warning_label.setStyleSheet(
                    """
                    QLabel {
                        color: palette(button-text);
                        background-color: palette(light);
                        border: 1px solid palette(mid);
                        border-radius: 4px;
                        padding: 10px;
                        font-weight: bold;
                    }
                """
                )
        else:
            self.setWindowTitle("📁 정리 실행 확인")
            title_label = self.findChild(QLabel, "")
            if title_label and title_label.text() == "파일 정리 미리보기":
                title_label.setText("파일 정리 실행을 시작합니다")
            if hasattr(self, "proceed_button"):
                self.proceed_button.setText("✅ 진행")
                self.proceed_button.setToolTip("파일 정리 실행")
            warning_label = self.findChild(QLabel, "")
            if (
                warning_label
                and "👁️ 미리보기 모드: 실제 파일 이동은 실행되지 않습니다" in warning_label.text()
            ):
                warning_label.setText(
                    "⚠️ 주의사항: 이 작업은 파일을 실제로 이동시킵니다. 원본 파일은 삭제됩니다."
                )
                warning_label.setStyleSheet(
                    """
                    QLabel {
                        color: palette(button-text);
                        background-color: palette(light);
                        border: 1px solid palette(mid);
                        border-radius: 4px;
                        padding: 10px;
                        font-weight: bold;
                    }
                """
                )
