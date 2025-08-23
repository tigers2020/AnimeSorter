"""
메인 툴바 컴포넌트 - Phase 1 UI/UX 리팩토링
상단의 스캔/미리보기/정리 실행 버튼, 검색, 진행률, 상태 요약을 포함하는 툴바를 관리합니다.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence, QPalette
from PyQt5.QtWidgets import (QAction, QApplication, QFrame, QHBoxLayout,
                             QLabel, QLineEdit, QProgressBar, QPushButton,
                             QSizePolicy, QWidget)


class StatusBadge(QFrame):
    """상태 요약 배지 위젯"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # 기본 상태 표시
        self.total_label = QLabel("총 0")
        self.unmatched_label = QLabel("미매칭 0")
        self.conflict_label = QLabel("충돌 0")
        self.duplicate_label = QLabel("중복 0")

        # 구분자 추가
        separator1 = QLabel("|")
        separator2 = QLabel("|")
        separator3 = QLabel("|")

        # 레이아웃에 추가
        layout.addWidget(self.total_label)
        layout.addWidget(separator1)
        layout.addWidget(self.unmatched_label)
        layout.addWidget(separator2)
        layout.addWidget(self.conflict_label)
        layout.addWidget(separator3)
        layout.addWidget(self.duplicate_label)

        # 스타일 설정
        self.setStyleSheet(
            """
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QLabel {
                color: #495057;
                font-size: 11px;
                font-weight: 500;
            }
        """
        )

        # 크기 정책 설정
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def update_status(self, total=0, unmatched=0, conflict=0, duplicate=0):
        """상태 업데이트"""
        self.total_label.setText(f"총 {total}")
        self.unmatched_label.setText(f"미매칭 {unmatched}")
        self.conflict_label.setText(f"충돌 {conflict}")
        self.duplicate_label.setText(f"중복 {duplicate}")

        # 색상 업데이트 (테마에 따라)
        self.update_theme_colors()

    def update_theme_colors(self):
        """테마에 따른 색상 업데이트"""
        palette = QApplication.palette()
        is_dark = palette.color(QPalette.Window).lightness() < 128

        if is_dark:
            # 다크 테마
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #343a40;
                    border: 1px solid #495057;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QLabel {
                    color: #e9ecef;
                    font-size: 11px;
                    font-weight: 500;
                }
            """
            )
        else:
            # 라이트 테마
            self.setStyleSheet(
                """
                QFrame {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QLabel {
                    color: #495057;
                    font-size: 11px;
                    font-weight: 500;
                }
            """
            )


class MainToolbar(QWidget):
    """메인 윈도우 상단 툴바 - Phase 1 리팩토링"""

    # 시그널 정의
    scan_requested = pyqtSignal()  # 스캔 요청
    preview_requested = pyqtSignal()  # 미리보기 요청
    organize_requested = pyqtSignal()  # 정리 실행 요청
    search_text_changed = pyqtSignal(str)  # 검색 텍스트 변경
    settings_requested = pyqtSignal()  # 설정 요청
    detail_panel_toggled = pyqtSignal(bool)  # 상세 패널 토글
    file_panel_toggled = pyqtSignal(bool)  # 파일 패널 토글

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_shortcuts()

    def init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 1. 좌측: 스캔/미리보기/정리 실행 버튼 그룹
        self.create_action_buttons(layout)

        # 구분자
        layout.addWidget(self.create_separator())

        # 2. 중앙: 검색 입력
        self.create_search_section(layout)

        # 구분자
        layout.addWidget(self.create_separator())

        # 3. 우측: 진행률 바, 상태 요약 배지, 패널 토글, 설정
        self.create_right_section(layout)

        # 툴바의 크기 정책 설정
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # 테마 변경 감지
        QApplication.instance().paletteChanged.connect(self.on_palette_changed)

    def create_action_buttons(self, layout):
        """액션 버튼 그룹 생성"""
        # 스캔 버튼 (중립색)
        self.btn_scan = QPushButton("🔍 스캔")
        self.btn_scan.setToolTip("소스 디렉토리 스캔 (F5)")
        self.btn_scan.setStyleSheet(self.get_button_style("#6c757d"))  # 중립색
        self.btn_scan.clicked.connect(self.scan_requested.emit)
        self.btn_scan.setMinimumHeight(32)
        self.btn_scan.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 미리보기 버튼 (중립색)
        self.btn_preview = QPushButton("👁️ 미리보기")
        self.btn_preview.setToolTip("변경 사항 미리보기 (Space)")
        self.btn_preview.setStyleSheet(self.get_button_style("#6c757d"))  # 중립색
        self.btn_preview.clicked.connect(self.preview_requested.emit)
        self.btn_preview.setMinimumHeight(32)
        self.btn_preview.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 정리 실행 버튼 (프라이머리 색상)
        self.btn_organize = QPushButton("🚀 정리 실행")
        self.btn_organize.setToolTip("파일 정리 실행 (Ctrl+Enter)")
        self.btn_organize.setStyleSheet(self.get_button_style("#27ae60", is_primary=True))
        self.btn_organize.clicked.connect(self.organize_requested.emit)
        self.btn_organize.setMinimumHeight(32)
        self.btn_organize.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 버튼들을 레이아웃에 추가
        layout.addWidget(self.btn_scan)
        layout.addWidget(self.btn_preview)
        layout.addWidget(self.btn_organize)

    def create_search_section(self, layout):
        """검색 섹션 생성"""
        # 검색 라벨
        search_label = QLabel("🔍")
        search_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 검색 입력 필드
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("제목, 경로로 검색... (Ctrl+F)")
        self.search_input.setMinimumWidth(200)
        self.search_input.setMaximumWidth(400)
        self.search_input.setMinimumHeight(28)
        self.search_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.search_input.textChanged.connect(self.search_text_changed.emit)

        # 검색 라벨과 입력 필드를 레이아웃에 추가
        layout.addWidget(search_label)
        layout.addWidget(self.search_input)

    def create_right_section(self, layout):
        """우측 섹션 생성"""
        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMinimumHeight(24)
        self.progress_bar.setMaximumHeight(24)
        self.progress_bar.setVisible(False)  # 기본적으로 숨김
        self.progress_bar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 상태 요약 배지
        self.status_badge = StatusBadge()

        # 패널 토글 버튼들
        self.create_panel_toggle_buttons(layout)

        # 설정 버튼
        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setToolTip("설정")
        self.btn_settings.setStyleSheet(self.get_button_style("#6c757d"))  # 중립색
        self.btn_settings.clicked.connect(self.settings_requested.emit)
        self.btn_settings.setMinimumHeight(28)
        self.btn_settings.setMaximumWidth(40)
        self.btn_settings.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 우측 섹션을 레이아웃에 추가
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_badge)
        layout.addWidget(self.btn_settings)

    def create_panel_toggle_buttons(self, layout):
        """패널 토글 버튼들 생성"""
        # 상세 패널 토글 버튼
        self.btn_detail_toggle = QPushButton("📋 상세")
        self.btn_detail_toggle.setToolTip("상세 패널 토글 (Alt+I)")
        self.btn_detail_toggle.setCheckable(True)
        self.btn_detail_toggle.setChecked(True)  # 기본적으로 표시
        self.btn_detail_toggle.setStyleSheet(self.get_toggle_button_style())
        self.btn_detail_toggle.clicked.connect(self.on_detail_toggle_clicked)
        self.btn_detail_toggle.setMinimumHeight(28)
        self.btn_detail_toggle.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 파일 패널 토글 버튼
        self.btn_file_toggle = QPushButton("📁 파일")
        self.btn_file_toggle.setToolTip("파일 패널 토글 (Alt+F)")
        self.btn_file_toggle.setCheckable(True)
        self.btn_file_toggle.setChecked(True)  # 기본적으로 표시
        self.btn_file_toggle.setStyleSheet(self.get_toggle_button_style())
        self.btn_file_toggle.clicked.connect(self.on_file_toggle_clicked)
        self.btn_file_toggle.setMinimumHeight(28)
        self.btn_file_toggle.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 토글 버튼들을 레이아웃에 추가
        layout.addWidget(self.btn_detail_toggle)
        layout.addWidget(self.btn_file_toggle)

    def on_detail_toggle_clicked(self):
        """상세 패널 토글 클릭"""
        is_checked = self.btn_detail_toggle.isChecked()
        self.detail_panel_toggled.emit(is_checked)

    def on_file_toggle_clicked(self):
        """파일 패널 토글 클릭"""
        is_checked = self.btn_file_toggle.isChecked()
        self.file_panel_toggled.emit(is_checked)

    def create_separator(self):
        """구분자 위젯 생성"""
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("QFrame { background-color: #dee2e6; }")
        separator.setMaximumWidth(1)
        separator.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        return separator

    def get_button_style(self, color, is_primary=False):
        """버튼 스타일 생성"""
        if is_primary:
            return f"""
                QPushButton {{
                    background-color: {color};
                color: white;
                border: none;
                padding: 8px 16px;
                    border-radius: 6px;
                font-weight: bold;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {self.darken_color(color)};
                }}
                QPushButton:pressed {{
                    background-color: {self.darken_color(color, 0.2)};
                }}
                QPushButton:disabled {{
                background-color: #95a5a6;
                color: #ecf0f1;
                }}
            """
        return f"""
                QPushButton {{
                    background-color: {color};
                color: white;
                border: none;
                    padding: 6px 12px;
                border-radius: 4px;
                    font-weight: 500;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {self.darken_color(color)};
                }}
                QPushButton:pressed {{
                    background-color: {self.darken_color(color, 0.2)};
                }}
                QPushButton:disabled {{
                    background-color: #95a5a6;
                    color: #ecf0f1;
                }}
            """

    def get_toggle_button_style(self):
        """토글 버튼 스타일 생성"""
        return """
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
            QPushButton:checked {
                background-color: #495057;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #ecf0f1;
            }
        """

    def darken_color(self, color, _factor=0.1):
        """색상을 어둡게 만드는 헬퍼 함수"""
        # 간단한 색상 어둡게 만들기 (실제로는 더 정교한 로직 필요)
        return color

    def setup_shortcuts(self):
        """단축키 설정"""
        # 기존 단축키들
        # F5: 스캔
        self.btn_scan.setShortcut(QKeySequence("F5"))

        # Space: 미리보기
        self.btn_preview.setShortcut(QKeySequence("Space"))

        # Ctrl+Enter: 정리 실행
        self.btn_organize.setShortcut(QKeySequence("Ctrl+Return"))

        # 상세 패널 토글 (Alt+I)
        self.detail_toggle_action = QAction("상세 패널 토글", self)
        self.detail_toggle_action.setShortcut(QKeySequence("Alt+I"))
        self.detail_toggle_action.triggered.connect(self.toggle_detail_panel)
        self.addAction(self.detail_toggle_action)

        # 파일 패널 토글 (Alt+F)
        self.file_toggle_action = QAction("파일 패널 토글", self)
        self.file_toggle_action.setShortcut(QKeySequence("Alt+F"))
        self.file_toggle_action.triggered.connect(self.toggle_file_panel)
        self.addAction(self.file_toggle_action)

    def on_palette_changed(self):
        """테마 변경 감지"""
        self.status_badge.update_theme_colors()

    def toggle_detail_panel(self):
        """상세 패널 토글 (단축키)"""
        current_state = self.btn_detail_toggle.isChecked()
        self.btn_detail_toggle.setChecked(not current_state)
        self.on_detail_toggle_clicked()

    def toggle_file_panel(self):
        """파일 패널 토글 (단축키)"""
        current_state = self.btn_file_toggle.isChecked()
        self.btn_file_toggle.setChecked(not current_state)
        self.on_file_toggle_clicked()

    def set_detail_panel_visible(self, visible: bool):
        """상세 패널 표시 상태 설정"""
        self.btn_detail_toggle.setChecked(visible)

    def set_file_panel_visible(self, visible: bool):
        """파일 패널 표시 상태 설정"""
        self.btn_file_toggle.setChecked(visible)

    # Public methods for external control
    def set_scan_enabled(self, enabled: bool):
        """스캔 버튼 활성화/비활성화"""
        self.btn_scan.setEnabled(enabled)

    def set_preview_enabled(self, enabled: bool):
        """미리보기 버튼 활성화/비활성화"""
        self.btn_preview.setEnabled(enabled)

    def set_organize_enabled(self, enabled: bool):
        """정리 실행 버튼 활성화/비활성화"""
        self.btn_organize.setEnabled(enabled)

    def set_progress_visible(self, visible: bool):
        """진행률 바 표시/숨김"""
        self.progress_bar.setVisible(visible)

    def set_progress_value(self, value: int):
        """진행률 값 설정 (0-100)"""
        self.progress_bar.setValue(value)

    def set_progress_range(self, minimum: int, maximum: int):
        """진행률 범위 설정"""
        self.progress_bar.setRange(minimum, maximum)

    def update_status_summary(self, total=0, unmatched=0, conflict=0, duplicate=0):
        """상태 요약 업데이트"""
        self.status_badge.update_status(total, unmatched, conflict, duplicate)

    def get_search_text(self) -> str:
        """검색 텍스트 반환"""
        return self.search_input.text()

    def clear_search(self):
        """검색 텍스트 초기화"""
        self.search_input.clear()

    def focus_search(self):
        """검색 입력에 포커스"""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def keyPressEvent(self, event):
        """키보드 이벤트 처리"""
        # Ctrl+F: 검색 입력에 포커스
        if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            self.focus_search()
            event.accept()
            return

        # 다른 키 이벤트는 기본 처리
        super().keyPressEvent(event)
