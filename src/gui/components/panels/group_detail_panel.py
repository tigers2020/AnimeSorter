"""
그룹 상세 패널 컴포넌트 - PRD 기반 구현
포스터 영역 200x300(비율 유지, 라운드 8-12px)
메타데이터 그리드(제목/원제/시즌/에피소드/상태/파일수/총용량)
태그 칩들, 그라데이션 배경 포스터 플레이스홀더
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QSizePolicy, QVBoxLayout, QWidget)


class GroupDetailPanel(QWidget):
    """
    그룹 상세 패널 컴포넌트

    포스터 영역: 200x300(비율 유지, 라운드 8-12px)
    메타데이터: 제목/원제/시즌/에피소드/상태/파일수/총용량
    태그 칩들: 1080p, TMDB, 자막 有 등
    """

    poster_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_accessibility()

    def init_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        self.create_poster_area()
        main_layout.addWidget(self.poster_frame)
        self.create_metadata_area()
        main_layout.addLayout(self.metadata_layout)
        self.create_tags_area()
        main_layout.addLayout(self.tags_layout)
        main_layout.addStretch()
        self.clear_content()

    def setup_accessibility(self):
        """접근성 설정"""
        self.setAccessibleName("그룹 상세 패널")
        self.setAccessibleDescription("선택된 애니메이션 그룹의 상세 정보를 표시합니다")
        self.setFocusPolicy(Qt.StrongFocus)

    def create_poster_area(self):
        """포스터 영역 생성"""
        self.poster_frame = QFrame()
        self.poster_frame.setFixedSize(200, 300)
        self.poster_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.poster_frame.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(x1:0, y:1, x2:1, y:0,
                    stop:0 #404853, stop:1 #2d323b);
                border-radius: 12px;
                border: 1px solid #323844;
            }
        """
        )
        self.poster_frame.setAccessibleName("포스터 영역")
        self.poster_frame.setAccessibleDescription("애니메이션 포스터 이미지를 표시합니다")
        self.poster_frame.setFocusPolicy(Qt.StrongFocus)
        poster_layout = QVBoxLayout(self.poster_frame)
        poster_layout.setContentsMargins(8, 8, 8, 8)
        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.poster_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border-radius: 8px;
                color: #c9cfda;
                font-weight: 600;
                font-size: 14px;
            }
        """
        )
        self.poster_label.setAccessibleName("포스터 이미지")
        self.poster_label.setAccessibleDescription("애니메이션 포스터 이미지")
        poster_layout.addWidget(self.poster_label)
        self.poster_frame.mousePressEvent = self.on_poster_clicked
        self.poster_frame.keyPressEvent = self.on_poster_key_pressed

    def create_metadata_area(self):
        """메타데이터 영역 생성"""
        self.metadata_layout = QGridLayout()
        self.metadata_layout.setSpacing(6)
        self.metadata_layout.setColumnStretch(1, 1)
        self.metadata_fields = {}
        fields = [
            ("title", "📺 제목", ""),
            ("original_title", "🎬 원제", ""),
            ("season", "📅 시즌", ""),
            ("episode", "🎭 에피소드", ""),
            ("status", "⚡ 상태", ""),
            ("file_count", "📁 파일 개수", ""),
            ("total_size", "💾 총 용량", ""),
        ]
        for i, (key, label_text, default_value) in enumerate(fields):
            label = QLabel(label_text)
            label.setStyleSheet(
                """
                QLabel {
                    color: #9aa3b2;
                    font-size: 12px;
                    font-weight: 500;
                }
            """
            )
            label.setAccessibleName(f"{label_text} 라벨")
            value_label = QLabel(default_value)
            value_label.setStyleSheet(
                """
                QLabel {
                    color: #e7eaf0;
                    font-size: 12px;
                    font-weight: 400;
                }
            """
            )
            value_label.setWordWrap(True)
            value_label.setAccessibleName(f"{label_text} 값")
            value_label.setAccessibleDescription(f"{label_text} 정보를 표시합니다")
            self.metadata_layout.addWidget(label, i, 0)
            self.metadata_layout.addWidget(value_label, i, 1)
            self.metadata_fields[key] = value_label

    def create_tags_area(self):
        """태그 칩들 영역 생성"""
        self.tags_layout = QHBoxLayout()
        self.tags_layout.setSpacing(6)
        self.tags_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.tag_chips = []

    def set_poster(self, poster_path: str = None, poster_url: str = None):
        """포스터 설정 (로컬 파일 또는 URL)"""
        logger.info("🖼️ 포스터 설정 요청: path=%s, url=%s", poster_path, poster_url)
        if poster_path and poster_path.strip():
            pixmap = QPixmap(poster_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(184, 276, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.poster_label.setPixmap(scaled_pixmap)
                self.poster_label.setText("")
                logger.info("✅ 로컬 포스터 로드 성공: %s", poster_path)
                self.poster_label.setAccessibleDescription(
                    f"애니메이션 포스터 이미지: {poster_path}"
                )
                return
            logger.info("❌ 로컬 포스터 로드 실패: %s", poster_path)
        if poster_url and poster_url.strip():
            try:
                import requests

                logger.info("🌐 URL에서 포스터 다운로드 시도: %s", poster_url)
                response = requests.get(poster_url, timeout=10)
                if response.status_code == 200:
                    pixmap = QPixmap()
                    if pixmap.loadFromData(response.content):
                        scaled_pixmap = pixmap.scaled(
                            184, 276, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                        self.poster_label.setPixmap(scaled_pixmap)
                        self.poster_label.setText("")
                        logger.info("✅ URL 포스터 로드 성공: %s", poster_url)
                        self.poster_label.setAccessibleDescription(
                            f"애니메이션 포스터 이미지: {poster_url}"
                        )
                        return
                    logger.info("❌ 포스터 데이터 파싱 실패")
                else:
                    logger.info("❌ HTTP 오류: %s", response.status_code)
            except Exception as e:
                logger.info("❌ URL 포스터 다운로드 실패: %s", e)
        self.set_poster_placeholder("200×300")

    def set_poster_placeholder(self, text: str):
        """포스터 플레이스홀더 설정"""
        self.poster_label.clear()
        self.poster_label.setText(text)
        self.poster_label.setAccessibleDescription(f"포스터 플레이스홀더: {text}")

    def set_metadata(self, metadata: dict):
        """메타데이터 설정"""
        default_metadata = {
            "title": "제목 없음",
            "original_title": "원제 없음",
            "season": "시즌 정보 없음",
            "episode": "에피소드 정보 없음",
            "status": "상태 정보 없음",
            "file_count": "0",
            "total_size": "0 B",
        }
        if metadata:
            default_metadata.update(metadata)
        for key, value in default_metadata.items():
            if key in self.metadata_fields:
                if key == "status":
                    self.set_status_chip(value)
                else:
                    self.metadata_fields[key].setText(str(value))
                    field_labels = {
                        "title": "제목",
                        "original_title": "원제",
                        "season": "시즌",
                        "episode": "에피소드",
                        "file_count": "파일 개수",
                        "total_size": "총 용량",
                    }
                    if key in field_labels:
                        self.metadata_fields[key].setAccessibleDescription(
                            f"{field_labels[key]}: {value}"
                        )

    def set_status_chip(self, status: str):
        """상태 칩 설정"""
        if "status" in self.metadata_fields:
            old_label = self.metadata_fields["status"]
            self.metadata_layout.removeWidget(old_label)
            old_label.deleteLater()
        status_chip = QLabel(status)
        status_chip.setStyleSheet(
            """
            QLabel {
                background: #343a44;
                color: #cfd6e3;
                font-size: 12px;
                padding: 2px 8px;
                border-radius: 999px;
                font-weight: 500;
            }
        """
        )
        status_chip.setAccessibleName("상태")
        status_chip.setAccessibleDescription(f"애니메이션 상태: {status}")
        self.metadata_layout.addWidget(status_chip, 4, 1)
        self.metadata_fields["status"] = status_chip

    def set_tags(self, tags: list):
        """태그 칩들 설정"""
        for chip in self.tag_chips:
            self.tags_layout.removeWidget(chip)
            chip.deleteLater()
        self.tag_chips.clear()
        for i, tag in enumerate(tags):
            chip = QLabel(tag)
            chip.setStyleSheet(
                """
                QLabel {
                    background: #343a44;
                    color: #c9cfda;
                    font-size: 12px;
                    padding: 4px 8px;
                    border-radius: 999px;
                    font-weight: 500;
                }
            """
            )
            chip.setAccessibleName(f"태그 {i + 1}")
            chip.setAccessibleDescription(f"애니메이션 태그: {tag}")
            self.tags_layout.addWidget(chip)
            self.tag_chips.append(chip)
        self.tags_layout.addStretch()

    def clear_content(self):
        """내용 초기화"""
        self.set_poster_placeholder("200×300")
        self.set_metadata({})
        self.set_tags([])

    def on_poster_clicked(self, event):
        """포스터 클릭 이벤트"""
        self.poster_clicked.emit()

    def on_poster_key_pressed(self, event):
        """포스터 키보드 이벤트"""
        if event.key() in [Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space]:
            self.poster_clicked.emit()
            event.accept()
        else:
            event.ignore()

    def update_from_group(self, group_data: dict):
        """그룹 데이터로부터 상세 정보 업데이트"""
        if not group_data:
            self.clear_content()
            return
        logger.info("🔄 그룹 상세 업데이트: %s", group_data.get("title", "Unknown"))
        metadata = {
            "title": group_data.get("title", "제목 없음"),
            "original_title": group_data.get("original_title", "원제 없음"),
            "season": group_data.get("season", "시즌 정보 없음"),
            "episode": group_data.get("episode_count", "0"),
            "status": group_data.get("status", "상태 정보 없음"),
            "file_count": str(group_data.get("file_count", 0)),
            "total_size": group_data.get("total_size", "0 B"),
        }
        poster_path = group_data.get("poster_path", "")
        poster_url = group_data.get("poster_url", "")
        tmdb_match = group_data.get("tmdb_match")
        if (
            tmdb_match
            and hasattr(tmdb_match, "poster_path")
            and tmdb_match.poster_path
            and not poster_url
        ):
            poster_url = f"https://image.tmdb.org/t/p/w500{tmdb_match.poster_path}"
            logger.info("🎯 TMDB 포스터 URL 생성: %s", poster_url)
        tags = group_data.get("tags", [])
        self.set_poster(poster_path, poster_url)
        self.set_metadata(metadata)
        self.set_tags(tags)
        title = metadata.get("title", "제목 없음")
        self.setAccessibleDescription(f"애니메이션 '{title}'의 상세 정보를 표시합니다")
