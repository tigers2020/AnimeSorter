"""
설정 다이얼로그 컴포넌트
AnimeSorter의 모든 설정을 편집할 수 있는 다이얼로그를 제공합니다.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    """설정 편집 다이얼로그"""

    settingsChanged = pyqtSignal()  # 설정 변경 시그널

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.settings = settings_manager.settings

        self.init_ui()
        self.load_current_settings()
        self.setup_connections()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("AnimeSorter 설정")
        self.setModal(True)
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 탭들 생성
        self.create_general_tab()
        self.create_parsing_tab()
        self.create_tmdb_tab()
        self.create_advanced_tab()
        self.create_backup_tab()

        # 버튼 박스
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Reset
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(self.reset_to_defaults)
        layout.addWidget(button_box)

    def create_general_tab(self):
        """일반 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 파일 정리 설정 그룹
        organize_group = QGroupBox("파일 정리 설정")
        organize_layout = QFormLayout(organize_group)

        self.destination_root_edit = QLineEdit()
        self.destination_root_edit.setPlaceholderText("대상 폴더 경로를 입력하세요")
        browse_btn = QPushButton("찾아보기")
        browse_btn.clicked.connect(self.browse_destination_folder)

        dest_layout = QHBoxLayout()
        dest_layout.addWidget(self.destination_root_edit)
        dest_layout.addWidget(browse_btn)

        self.organize_mode_combo = QComboBox()
        self.organize_mode_combo.addItems(["이동", "복사", "하드링크"])

        self.naming_scheme_combo = QComboBox()
        self.naming_scheme_combo.addItems(["standard", "minimal", "detailed"])

        organize_layout.addRow("대상 폴더:", dest_layout)
        organize_layout.addRow("정리 모드:", self.organize_mode_combo)
        organize_layout.addRow("파일명 방식:", self.naming_scheme_combo)

        layout.addWidget(organize_group)

        # 세션 관리 그룹
        session_group = QGroupBox("세션 관리")
        session_layout = QFormLayout(session_group)

        self.remember_session_check = QCheckBox("마지막 세션 기억")
        self.remember_session_check.setToolTip(
            "프로그램 재시작 시 마지막으로 선택한 폴더와 파일을 복원합니다"
        )

        session_layout.addRow("", self.remember_session_check)

        layout.addWidget(session_group)
        layout.addStretch(1)

        self.tab_widget.addTab(tab, "일반")

    def create_parsing_tab(self):
        """파싱 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 파싱 설정 그룹
        parsing_group = QGroupBox("파싱 설정")
        parsing_layout = QFormLayout(parsing_group)

        self.prefer_anitopy_check = QCheckBox("Anitopy 우선 사용")
        self.prefer_anitopy_check.setToolTip("파일명 파싱 시 Anitopy를 우선적으로 사용합니다")

        self.fallback_parser_combo = QComboBox()
        self.fallback_parser_combo.addItems(["GuessIt", "FileParser", "Custom"])

        self.realtime_monitoring_check = QCheckBox("실시간 모니터링")
        self.realtime_monitoring_check.setToolTip("폴더 변경사항을 실시간으로 감지합니다")

        self.auto_refresh_spin = QSpinBox()
        self.auto_refresh_spin.setRange(10, 300)
        self.auto_refresh_spin.setSuffix(" 초")

        parsing_layout.addRow("", self.prefer_anitopy_check)
        parsing_layout.addRow("대체 파서:", self.fallback_parser_combo)
        parsing_layout.addRow("", self.realtime_monitoring_check)
        parsing_layout.addRow("자동 새로고침:", self.auto_refresh_spin)

        layout.addWidget(parsing_group)
        layout.addStretch(1)

        self.tab_widget.addTab(tab, "파싱")

    def create_tmdb_tab(self):
        """TMDB 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # TMDB 설정 그룹
        tmdb_group = QGroupBox("TMDB 설정")
        tmdb_layout = QFormLayout(tmdb_group)

        self.tmdb_api_key_edit = QLineEdit()
        self.tmdb_api_key_edit.setPlaceholderText("TMDB API 키를 입력하세요")
        self.tmdb_api_key_edit.setEchoMode(QLineEdit.Password)

        self.tmdb_language_combo = QComboBox()
        self.tmdb_language_combo.addItems(["ko-KR", "en-US", "ja-JP"])

        tmdb_layout.addRow("API 키:", self.tmdb_api_key_edit)
        tmdb_layout.addRow("언어:", self.tmdb_language_combo)

        layout.addWidget(tmdb_group)
        layout.addStretch(1)

        self.tab_widget.addTab(tab, "TMDB")

    def create_advanced_tab(self):
        """고급 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 고급 설정 그룹
        advanced_group = QGroupBox("고급 설정")
        advanced_layout = QFormLayout(advanced_group)

        self.show_advanced_check = QCheckBox("고급 옵션 표시")
        self.show_advanced_check.setToolTip("고급 설정 옵션들을 UI에 표시합니다")

        self.safe_mode_check = QCheckBox("안전 모드")
        self.safe_mode_check.setToolTip("파일 정리 시 안전 모드를 사용합니다")

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])

        self.log_to_file_check = QCheckBox("파일로 로그 저장")
        self.log_to_file_check.setToolTip("로그를 파일로 저장합니다")

        advanced_layout.addRow("", self.show_advanced_check)
        advanced_layout.addRow("", self.safe_mode_check)
        advanced_layout.addRow("로그 레벨:", self.log_level_combo)
        advanced_layout.addRow("", self.log_to_file_check)

        layout.addWidget(advanced_group)
        layout.addStretch(1)

        self.tab_widget.addTab(tab, "고급")

    def create_backup_tab(self):
        """백업 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 백업 설정 그룹
        backup_group = QGroupBox("백업 설정")
        backup_layout = QFormLayout(backup_group)

        self.backup_before_organize_check = QCheckBox("정리 전 백업")
        self.backup_before_organize_check.setToolTip("파일 정리 전에 백업을 생성합니다")

        self.backup_location_edit = QLineEdit()
        self.backup_location_edit.setPlaceholderText("백업 폴더 경로를 입력하세요")
        backup_browse_btn = QPushButton("찾아보기")
        backup_browse_btn.clicked.connect(self.browse_backup_folder)

        backup_loc_layout = QHBoxLayout()
        backup_loc_layout.addWidget(self.backup_location_edit)
        backup_loc_layout.addWidget(backup_browse_btn)

        self.max_backup_count_spin = QSpinBox()
        self.max_backup_count_spin.setRange(1, 100)
        self.max_backup_count_spin.setSuffix(" 개")

        backup_layout.addRow("", self.backup_before_organize_check)
        backup_layout.addRow("백업 위치:", backup_loc_layout)
        backup_layout.addRow("최대 백업 수:", self.max_backup_count_spin)

        layout.addWidget(backup_group)
        layout.addStretch(1)

        self.tab_widget.addTab(tab, "백업")

    def setup_connections(self):
        """시그널/슬롯 연결"""
        # 설정 변경 감지를 위한 연결
        self.destination_root_edit.textChanged.connect(self.on_setting_changed)
        self.organize_mode_combo.currentTextChanged.connect(self.on_setting_changed)
        self.naming_scheme_combo.currentTextChanged.connect(self.on_setting_changed)
        self.remember_session_check.toggled.connect(self.on_setting_changed)
        self.prefer_anitopy_check.toggled.connect(self.on_setting_changed)
        self.fallback_parser_combo.currentTextChanged.connect(self.on_setting_changed)
        self.realtime_monitoring_check.toggled.connect(self.on_setting_changed)
        self.auto_refresh_spin.valueChanged.connect(self.on_setting_changed)
        self.tmdb_api_key_edit.textChanged.connect(self.on_setting_changed)
        self.tmdb_language_combo.currentTextChanged.connect(self.on_setting_changed)
        self.show_advanced_check.toggled.connect(self.on_setting_changed)
        self.safe_mode_check.toggled.connect(self.on_setting_changed)
        self.log_level_combo.currentTextChanged.connect(self.on_setting_changed)
        self.log_to_file_check.toggled.connect(self.on_setting_changed)
        self.backup_before_organize_check.toggled.connect(self.on_setting_changed)
        self.backup_location_edit.textChanged.connect(self.on_setting_changed)
        self.max_backup_count_spin.valueChanged.connect(self.on_setting_changed)

    def load_current_settings(self):
        """현재 설정을 UI에 로드"""
        try:
            # 일반 설정
            self.destination_root_edit.setText(self.settings.destination_root or "")
            self.organize_mode_combo.setCurrentText(self.settings.organize_mode)
            self.naming_scheme_combo.setCurrentText(self.settings.naming_scheme)
            self.remember_session_check.setChecked(self.settings.remember_last_session)

            # 파싱 설정
            self.prefer_anitopy_check.setChecked(self.settings.prefer_anitopy)
            self.fallback_parser_combo.setCurrentText(self.settings.fallback_parser)
            self.realtime_monitoring_check.setChecked(self.settings.realtime_monitoring)
            self.auto_refresh_spin.setValue(self.settings.auto_refresh_interval)

            # TMDB 설정
            self.tmdb_api_key_edit.setText(self.settings.tmdb_api_key or "")
            self.tmdb_language_combo.setCurrentText(self.settings.tmdb_language)

            # 고급 설정
            self.show_advanced_check.setChecked(self.settings.show_advanced_options)
            self.safe_mode_check.setChecked(self.settings.safe_mode)
            self.log_level_combo.setCurrentText(self.settings.log_level)
            self.log_to_file_check.setChecked(self.settings.log_to_file)

            # 백업 설정
            self.backup_before_organize_check.setChecked(self.settings.backup_before_organize)
            self.backup_location_edit.setText(self.settings.backup_location or "")
            self.max_backup_count_spin.setValue(self.settings.max_backup_count)

        except Exception as e:
            print(f"⚠️ 설정 로드 실패: {e}")

    def save_settings(self):
        """UI 설정을 저장"""
        try:
            # 일반 설정
            self.settings.destination_root = self.destination_root_edit.text().strip()
            self.settings.organize_mode = self.organize_mode_combo.currentText()
            self.settings.naming_scheme = self.naming_scheme_combo.currentText()
            self.settings.remember_last_session = self.remember_session_check.isChecked()

            # 파싱 설정
            self.settings.prefer_anitopy = self.prefer_anitopy_check.isChecked()
            self.settings.fallback_parser = self.fallback_parser_combo.currentText()
            self.settings.realtime_monitoring = self.realtime_monitoring_check.isChecked()
            self.settings.auto_refresh_interval = self.auto_refresh_spin.value()

            # TMDB 설정
            self.settings.tmdb_api_key = self.tmdb_api_key_edit.text().strip()
            self.settings.tmdb_language = self.tmdb_language_combo.currentText()

            # 고급 설정
            self.settings.show_advanced_options = self.show_advanced_check.isChecked()
            self.settings.safe_mode = self.safe_mode_check.isChecked()
            self.settings.log_level = self.log_level_combo.currentText()
            self.settings.log_to_file = self.log_to_file_check.isChecked()

            # 백업 설정
            self.settings.backup_before_organize = self.backup_before_organize_check.isChecked()
            self.settings.backup_location = self.backup_location_edit.text().strip()
            self.settings.max_backup_count = self.max_backup_count_spin.value()

            # 설정 파일에 저장
            self.settings_manager.save_settings()

            print("✅ 설정 저장 완료")

        except Exception as e:
            print(f"❌ 설정 저장 실패: {e}")
            QMessageBox.critical(self, "오류", f"설정 저장에 실패했습니다:\n{e}")

    def reset_to_defaults(self):
        """기본값으로 초기화"""
        reply = QMessageBox.question(
            self,
            "기본값으로 초기화",
            "모든 설정을 기본값으로 초기화하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # 기본 설정으로 초기화
            self.settings = self.settings_manager.get_default_settings()
            self.load_current_settings()
            print("✅ 설정을 기본값으로 초기화했습니다")

    def browse_destination_folder(self):
        """대상 폴더 찾아보기"""
        folder = QFileDialog.getExistingDirectory(self, "대상 폴더 선택")
        if folder:
            self.destination_root_edit.setText(folder)

    def browse_backup_folder(self):
        """백업 폴더 찾아보기"""
        folder = QFileDialog.getExistingDirectory(self, "백업 폴더 선택")
        if folder:
            self.backup_location_edit.setText(folder)

    def on_setting_changed(self):
        """설정 변경 감지"""
        # 설정 변경 시그널 발생
        self.settingsChanged.emit()

    def accept(self):
        """확인 버튼 클릭 시 설정 저장"""
        self.save_settings()
        super().accept()

    def reject(self):
        """취소 버튼 클릭 시 다이얼로그 닫기"""
        super().reject()
