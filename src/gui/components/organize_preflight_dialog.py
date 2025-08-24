"""
정리 실행 프리플라이트 다이얼로그
파일 정리 실행 전 요약 정보를 표시하고 사용자 확인을 받습니다.
"""

import re
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class OrganizePreflightDialog(QDialog):
    """정리 실행 프리플라이트 확인 다이얼로그"""

    # 시그널 정의
    proceed_requested = pyqtSignal()  # 진행 요청

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

        # 스타일은 테마 시스템에서 관리

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 제목
        title_label = QLabel("파일 정리 실행을 시작합니다")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 요약 정보
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(300)
        # 스타일은 테마 시스템에서 관리
        layout.addWidget(self.summary_text)

        # 경고 메시지
        warning_label = QLabel(
            "⚠️ 주의사항: 이 작업은 파일을 실제로 이동시킵니다. 원본 파일은 삭제됩니다."
        )
        # 스타일은 테마 시스템에서 관리
        layout.addWidget(warning_label)

        # 버튼 영역
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 취소 버튼
        self.cancel_button = QPushButton("❌ 취소")
        # 스타일은 테마 시스템에서 관리
        self.cancel_button.clicked.connect(self.reject)

        # 진행 버튼
        self.proceed_button = QPushButton("✅ 진행")
        # 스타일은 테마 시스템에서 관리
        self.proceed_button.clicked.connect(self.on_proceed_clicked)

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.proceed_button)
        layout.addLayout(button_layout)

        # 자막 파일 처리 섹션
        subtitle_section = QLabel("📝 자막 파일 처리")
        # 스타일은 테마 시스템에서 관리
        layout.addWidget(subtitle_section)

        subtitle_info = QLabel(
            "• 비디오 파일과 연관된 자막 파일(.srt, .ass, .ssa, .sub, .vtt, .idx, .smi, .sami, .txt)이 자동으로 함께 이동됩니다\n"
            "• 파일명이 일치하는 자막 파일이 자동으로 감지되어 같은 폴더에 배치됩니다\n"
            "• 언어 코드가 포함된 자막 파일(예: .ko.srt, .en.ass)도 지원됩니다"
        )
        subtitle_info.setWordWrap(True)
        layout.addWidget(subtitle_info)

        # 빈 디렉토리 정리 섹션
        cleanup_section = QLabel("🗑️ 빈 디렉토리 정리")
        # 스타일은 테마 시스템에서 관리
        layout.addWidget(cleanup_section)

        cleanup_info = QLabel(
            "• 파일 이동 완료 후 소스 폴더의 빈 디렉토리들이 자동으로 삭제됩니다\n"
            "• 하위 디렉토리부터 상위 디렉토리 순으로 재귀적으로 정리됩니다\n"
            "• 소스 폴더가 깔끔하게 정리되어 불필요한 폴더 구조가 제거됩니다"
        )
        cleanup_info.setWordWrap(True)
        layout.addWidget(cleanup_info)

        # 기본 포커스 설정
        self.proceed_button.setFocus()

    def generate_summary(self):
        """요약 정보 생성"""
        try:
            summary_lines = []

            # 기본 통계
            total_groups = 0
            total_files = 0
            total_size_mb = 0
            sample_paths = []

            for group_id, group_items in self.grouped_items.items():
                if group_id == "ungrouped":
                    continue

                total_groups += 1
                total_files += len(group_items)

                # 파일 크기 계산
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

                # 샘플 경로 생성 (처음 5개 그룹만)
                if len(sample_paths) < 5 and group_items:
                    representative = group_items[0]
                    sample_path = self._generate_sample_path(representative)
                    if sample_path:
                        sample_paths.append(sample_path)

            # 요약 정보 추가
            summary_lines.append("📊 정리 실행 요약")
            summary_lines.append("=" * 50)
            summary_lines.append(f"• 총 그룹: {total_groups}개")
            summary_lines.append(f"• 총 파일: {total_files}개 (비디오 파일)")
            summary_lines.append(f"• 예상 크기: {total_size_mb:.1f} MB")
            summary_lines.append(f"• 대상 폴더: {self.destination_directory}")
            summary_lines.append("")

            # 샘플 경로 추가
            if sample_paths:
                summary_lines.append("📁 샘플 대상 경로:")
                summary_lines.append("-" * 30)
                for i, path in enumerate(sample_paths, 1):
                    summary_lines.append(f"{i}. {path}")
                summary_lines.append("")

                if len(sample_paths) < total_groups:
                    summary_lines.append(f"... 및 {total_groups - len(sample_paths)}개 그룹 더")
                    summary_lines.append("")

            # 예상 생성 디렉토리 수
            summary_lines.append("📂 예상 생성 디렉토리:")
            summary_lines.append("-" * 30)
            summary_lines.append(f"• 애니메이션 폴더: {total_groups}개")
            summary_lines.append(f"• 시즌 폴더: {total_groups}개 (기본값)")
            summary_lines.append("")

            # 자막 파일 정보 추가
            summary_lines.append("📝 자막 파일 처리:")
            summary_lines.append("-" * 30)
            summary_lines.append(
                "• 연관된 자막 파일(.srt, .ass, .ssa 등)이 자동으로 함께 이동됩니다"
            )
            summary_lines.append("• 자막 파일은 비디오 파일과 같은 폴더에 배치됩니다")
            summary_lines.append("")

            # 경고 사항
            summary_lines.append("⚠️ 주의사항:")
            summary_lines.append("-" * 30)
            summary_lines.append("• 원본 파일이 이동되어 삭제됩니다")
            summary_lines.append("• 동일한 파일명이 있으면 자동으로 번호가 추가됩니다")
            summary_lines.append("• 특수문자는 파일명에서 제거됩니다")
            summary_lines.append("• 작업 중 취소할 수 있습니다")

            # 요약 텍스트 설정
            self.summary_text.setPlainText("\n".join(summary_lines))

        except Exception as e:
            error_text = f"요약 생성 중 오류가 발생했습니다:\n{str(e)}"
            self.summary_text.setPlainText(error_text)

    def _generate_sample_path(self, representative):
        """샘플 경로 생성"""
        try:
            # 제목 정제 (특수문자 제거)
            if (
                hasattr(representative, "tmdbMatch")
                and representative.tmdbMatch
                and representative.tmdbMatch.name
            ):
                raw_title = representative.tmdbMatch.name
            else:
                raw_title = representative.title or representative.detectedTitle or "Unknown"

            # 특수문자 제거 및 정제 (알파벳, 숫자, 한글, 공백만 허용)
            safe_title = re.sub(r"[^a-zA-Z0-9가-힣\s]", "", raw_title)
            # 연속된 공백을 하나로 치환
            safe_title = re.sub(r"\s+", " ", safe_title)
            # 앞뒤 공백 제거
            safe_title = safe_title.strip()

            if not safe_title:
                safe_title = "Unknown"

            season = representative.season or 1
            season_folder = f"Season{season:02d}"

            # 파일명 (첫 번째 파일 기준)
            if hasattr(representative, "filename") and representative.filename:
                filename = representative.filename
            elif hasattr(representative, "sourcePath") and representative.sourcePath:
                filename = Path(representative.sourcePath).name
            else:
                filename = "example.mkv"

            return f"{self.destination_directory}/{safe_title}/{season_folder}/{filename}"

        except Exception as e:
            print(f"⚠️ 샘플 경로 생성 실패: {e}")
            return None

    def on_proceed_clicked(self):
        """진행 버튼 클릭 처리"""
        self.proceed_requested.emit()
        self.accept()

    def set_preview_mode(self, is_preview: bool):
        """미리보기 모드 설정"""
        self.is_preview_mode = is_preview

        if is_preview:
            # 미리보기 모드일 때 UI 변경
            self.setWindowTitle("👁️ 정리 미리보기")

            # 제목 변경
            title_label = self.findChild(QLabel, "")
            if title_label and title_label.text() == "파일 정리 실행을 시작합니다":
                title_label.setText("파일 정리 미리보기")

            # 진행 버튼 텍스트 변경
            if hasattr(self, "proceed_button"):
                self.proceed_button.setText("✅ 확인")
                self.proceed_button.setToolTip("미리보기 확인")

            # 경고 메시지 변경
            warning_label = self.findChild(QLabel, "")
            if (
                warning_label
                and "⚠️ 주의사항: 이 작업은 파일을 실제로 이동시킵니다" in warning_label.text()
            ):
                warning_label.setText("👁️ 미리보기 모드: 실제 파일 이동은 실행되지 않습니다.")
                # 스타일은 테마 시스템에서 관리
        else:
            # 일반 모드로 복원
            self.setWindowTitle("📁 정리 실행 확인")

            # 제목 복원
            title_label = self.findChild(QLabel, "")
            if title_label and title_label.text() == "파일 정리 미리보기":
                title_label.setText("파일 정리 실행을 시작합니다")

            # 진행 버튼 텍스트 복원
            if hasattr(self, "proceed_button"):
                self.proceed_button.setText("✅ 진행")
                self.proceed_button.setToolTip("파일 정리 실행")

            # 경고 메시지 복원
            warning_label = self.findChild(QLabel, "")
            if (
                warning_label
                and "👁️ 미리보기 모드: 실제 파일 이동은 실행되지 않습니다" in warning_label.text()
            ):
                warning_label.setText(
                    "⚠️ 주의사항: 이 작업은 파일을 실제로 이동시킵니다. 원본 파일은 삭제됩니다."
                )
                # 스타일은 테마 시스템에서 관리
