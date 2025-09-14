"""
설정 다이얼로그 컴포넌트
AnimeSorter의 모든 설정을 편집할 수 있는 다이얼로그를 제공합니다.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)
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

from src.state.base_state import BaseState


class SettingsDialog(BaseState, QDialog):
    """설정 편집 다이얼로그"""

    settingsChanged = pyqtSignal()

    def __init__(self, settings_manager, parent=None):
        # Initialize QDialog first
        QDialog.__init__(self, parent)
        # Then initialize BaseState
        BaseState.__init__(self)
        self.settings_manager = settings_manager
        self.settings = settings_manager.config
        self.init_ui()
        self.load_current_settings()
        self.setup_connections()

    def _get_default_state_config(self) -> Dict[str, Any]:
        """
        Get the default state configuration for this dialog.

        Returns:
            Dictionary containing default state configuration.
        """
        return {
            "managers": {"settings_manager": None},
            "collections": {"settings": "dict"},
            "strings": {},
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
        self.settings_manager = getattr(self, "settings_manager", None)
        self.settings = getattr(self, "settings", {})

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("AnimeSorter 설정")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        self.create_general_tab()
        self.create_parsing_tab()
        self.create_tmdb_tab()
        self.create_appearance_tab()
        self.create_advanced_tab()
        self.create_backup_tab()
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
        session_group = QGroupBox("세션 관리")
        session_layout = QFormLayout(session_group)
        self.remember_session_check = QCheckBox("마지막 세션 기억")
        self.remember_session_check.setToolTip("프로그램 재시작 시 마지막으로 선택한 폴더와 파일을 복원합니다")
        session_layout.addRow("", self.remember_session_check)
        layout.addWidget(session_group)
        layout.addStretch(1)
        self.tab_widget.addTab(tab, "일반")

    def create_parsing_tab(self):
        """파싱 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
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

    def create_appearance_tab(self):
        """외관 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        theme_group = QGroupBox("테마 설정")
        theme_layout = QFormLayout(theme_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["자동", "라이트", "다크"])
        self.theme_combo.setToolTip("애플리케이션의 색상 테마를 선택합니다")
        theme_layout.addRow("테마:", self.theme_combo)
        layout.addWidget(theme_group)
        accessibility_group = QGroupBox("접근성 설정")
        accessibility_layout = QFormLayout(accessibility_group)
        self.high_contrast_check = QCheckBox("고대비 모드")
        self.high_contrast_check.setToolTip("고대비 모드를 활성화하여 텍스트 가독성을 향상시킵니다")
        self.keyboard_navigation_check = QCheckBox("키보드 네비게이션 강화")
        self.keyboard_navigation_check.setToolTip("키보드만으로 모든 기능을 사용할 수 있도록 합니다")
        self.screen_reader_check = QCheckBox("스크린 리더 지원")
        self.screen_reader_check.setToolTip("스크린 리더와의 호환성을 향상시킵니다")
        accessibility_layout.addRow("", self.high_contrast_check)
        accessibility_layout.addRow("", self.keyboard_navigation_check)
        accessibility_layout.addRow("", self.screen_reader_check)
        layout.addWidget(accessibility_group)
        language_group = QGroupBox("언어 설정")
        language_layout = QFormLayout(language_group)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["한국어", "English"])
        self.language_combo.setToolTip("애플리케이션의 언어를 선택합니다")
        language_layout.addRow("언어:", self.language_combo)
        layout.addWidget(language_group)
        layout.addStretch(1)
        self.tab_widget.addTab(tab, "외관")

    def create_advanced_tab(self):
        """고급 설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
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
        self.theme_combo.currentTextChanged.connect(self.on_setting_changed)
        self.high_contrast_check.toggled.connect(self.on_setting_changed)
        self.keyboard_navigation_check.toggled.connect(self.on_setting_changed)
        self.screen_reader_check.toggled.connect(self.on_setting_changed)
        self.language_combo.currentTextChanged.connect(self.on_setting_changed)

    def load_current_settings(self):
        """현재 설정을 UI에 로드"""
        logger.info("🔧 [SettingsDialog] 설정 로딩 시작")
        try:
            if hasattr(self.settings_manager, "config"):
                logger.info("🔧 [SettingsDialog] config: %s", self.settings_manager.config)
                logger.info("🔧 [SettingsDialog] application: %s", self.settings.application)
                logger.info("🔧 [SettingsDialog] services: %s", self.settings.services)
                logger.info(
                    "🔧 [SettingsDialog] user_preferences: %s", self.settings.user_preferences
                )
                destination_root = self.settings.application.file_organization.get(
                    "destination_root", ""
                )
                logger.info("🔧 [SettingsDialog] destination_root: '%s'", destination_root)
                self.destination_root_edit.setText(destination_root)
                organize_mode = self.settings.application.file_organization.get(
                    "organize_mode", "복사"
                )
                logger.info("🔧 [SettingsDialog] organize_mode: '%s'", organize_mode)
                self.organize_mode_combo.setCurrentText(organize_mode)
                naming_scheme = self.settings.application.file_organization.get(
                    "naming_scheme", "standard"
                )
                logger.info("🔧 [SettingsDialog] naming_scheme: '%s'", naming_scheme)
                self.naming_scheme_combo.setCurrentText(naming_scheme)
                remember_session = self.settings.user_preferences.remember_last_session
                logger.info("🔧 [SettingsDialog] remember_last_session: %s", remember_session)
                self.remember_session_check.setChecked(remember_session)
                prefer_anitopy = self.settings.application.file_organization.get(
                    "prefer_anitopy", False
                )
                logger.info("🔧 [SettingsDialog] prefer_anitopy: %s", prefer_anitopy)
                self.prefer_anitopy_check.setChecked(prefer_anitopy)
                fallback_parser = self.settings.application.file_organization.get(
                    "fallback_parser", "FileParser"
                )
                logger.info("🔧 [SettingsDialog] fallback_parser: '%s'", fallback_parser)
                self.fallback_parser_combo.setCurrentText(fallback_parser)
                realtime_monitoring = self.settings.application.file_organization.get(
                    "realtime_monitoring", False
                )
                logger.info("🔧 [SettingsDialog] realtime_monitoring: %s", realtime_monitoring)
                self.realtime_monitoring_check.setChecked(realtime_monitoring)
                auto_refresh_interval = self.settings.application.file_organization.get(
                    "auto_refresh_interval", 30
                )
                logger.info("🔧 [SettingsDialog] auto_refresh_interval: %s", auto_refresh_interval)
                self.auto_refresh_spin.setValue(auto_refresh_interval)
                tmdb_api_key = self.settings.services.tmdb_api.get("api_key", "")
                logger.info("🔧 [SettingsDialog] tmdb_api_key: '%s'", tmdb_api_key)
                self.tmdb_api_key_edit.setText(tmdb_api_key)
                tmdb_language = self.settings.services.tmdb_api.get("language", "ko-KR")
                logger.info("🔧 [SettingsDialog] tmdb_language: '%s'", tmdb_language)
                self.tmdb_language_combo.setCurrentText(tmdb_language)
                show_advanced = self.settings.application.file_organization.get(
                    "show_advanced_options", False
                )
                logger.info("🔧 [SettingsDialog] show_advanced: %s", show_advanced)
                self.show_advanced_check.setChecked(show_advanced)
                safe_mode = self.settings.application.file_organization.get("safe_mode", True)
                logger.info("🔧 [SettingsDialog] safe_mode: %s", safe_mode)
                self.safe_mode_check.setChecked(safe_mode)
                log_level = self.settings.application.logging_config.get("log_level", "INFO")
                logger.info("🔧 [SettingsDialog] log_level: '%s'", log_level)
                self.log_level_combo.setCurrentText(log_level)
                log_to_file = self.settings.application.logging_config.get("log_to_file", False)
                logger.info("🔧 [SettingsDialog] log_to_file: %s", log_to_file)
                self.log_to_file_check.setChecked(log_to_file)
                backup_before_organize = self.settings.application.file_organization.get(
                    "backup_before_organize", False
                )
                logger.info("🔧 [SettingsDialog] backup_before_organize: %s", backup_before_organize)
                self.backup_before_organize_check.setChecked(backup_before_organize)
                backup_location = self.settings.application.backup_settings.get(
                    "backup_location", ""
                )
                logger.info("🔧 [SettingsDialog] backup_location: '%s'", backup_location)
                self.backup_location_edit.setText(backup_location)
                max_backup_count = self.settings.application.backup_settings.get(
                    "max_backup_count", 10
                )
                logger.info("🔧 [SettingsDialog] max_backup_count: %s", max_backup_count)
                self.max_backup_count_spin.setValue(max_backup_count)
                theme_map = {"auto": "자동", "light": "라이트", "dark": "다크"}
                current_theme = self.settings.user_preferences.theme_preferences.get(
                    "theme", "auto"
                )
                logger.info("🔧 [SettingsDialog] current_theme: '%s'", current_theme)
                self.theme_combo.setCurrentText(theme_map.get(current_theme, "자동"))
                high_contrast_mode = self.settings.user_preferences.accessibility.get(
                    "high_contrast_mode", False
                )
                logger.info("🔧 [SettingsDialog] high_contrast_mode: %s", high_contrast_mode)
                self.high_contrast_check.setChecked(high_contrast_mode)
                keyboard_navigation = self.settings.user_preferences.accessibility.get(
                    "keyboard_navigation", True
                )
                logger.info("🔧 [SettingsDialog] keyboard_navigation: %s", keyboard_navigation)
                self.keyboard_navigation_check.setChecked(keyboard_navigation)
                screen_reader_support = self.settings.user_preferences.accessibility.get(
                    "screen_reader_support", True
                )
                logger.info("🔧 [SettingsDialog] screen_reader_support: %s", screen_reader_support)
                self.screen_reader_check.setChecked(screen_reader_support)
                language_map = {"ko": "한국어", "en": "English"}
                current_language = self.settings.user_preferences.theme_preferences.get(
                    "language", "ko"
                )
                logger.info("🔧 [SettingsDialog] current_language: '%s'", current_language)
                self.language_combo.setCurrentText(language_map.get(current_language, "한국어"))
        except Exception as e:
            logger.info("⚠️ 설정 로드 실패: %s", e)

    def save_settings(self):
        """UI 설정을 저장"""
        logger.info("🔧 [SettingsDialog] 설정 저장 시작")
        try:
            if hasattr(self.settings_manager, "config"):
                logger.info("🔧 [SettingsDialog] unified_config_manager 사용")
                self.settings.application.file_organization[
                    "destination_root"
                ] = self.destination_root_edit.text().strip()
                self.settings.application.file_organization[
                    "organize_mode"
                ] = self.organize_mode_combo.currentText()
                self.settings.application.file_organization[
                    "naming_scheme"
                ] = self.naming_scheme_combo.currentText()
                self.settings.user_preferences.gui_state[
                    "remember_last_session"
                ] = self.remember_session_check.isChecked()
                self.settings.application.file_organization[
                    "prefer_anitopy"
                ] = self.prefer_anitopy_check.isChecked()
                self.settings.application.file_organization[
                    "fallback_parser"
                ] = self.fallback_parser_combo.currentText()
                self.settings.application.file_organization[
                    "realtime_monitoring"
                ] = self.realtime_monitoring_check.isChecked()
                self.settings.application.file_organization[
                    "auto_refresh_interval"
                ] = self.auto_refresh_spin.value()
                self.settings.services.tmdb_api["api_key"] = self.tmdb_api_key_edit.text().strip()
                self.settings.services.tmdb_api["language"] = self.tmdb_language_combo.currentText()
                self.settings.application.file_organization[
                    "show_advanced_options"
                ] = self.show_advanced_check.isChecked()
                self.settings.application.file_organization[
                    "safe_mode"
                ] = self.safe_mode_check.isChecked()
                self.settings.application.logging_config[
                    "log_level"
                ] = self.log_level_combo.currentText()
                self.settings.application.logging_config[
                    "log_to_file"
                ] = self.log_to_file_check.isChecked()
                self.settings.application.file_organization[
                    "backup_before_organize"
                ] = self.backup_before_organize_check.isChecked()
                self.settings.application.backup_settings[
                    "backup_location"
                ] = self.backup_location_edit.text().strip()
                self.settings.application.backup_settings[
                    "max_backup_count"
                ] = self.max_backup_count_spin.value()
                theme_map = {"자동": "auto", "라이트": "light", "다크": "dark"}
                self.settings.user_preferences.theme_preferences["theme"] = theme_map.get(
                    self.theme_combo.currentText(), "auto"
                )
                self.settings.user_preferences.accessibility[
                    "high_contrast_mode"
                ] = self.high_contrast_check.isChecked()
                self.settings.user_preferences.accessibility[
                    "keyboard_navigation"
                ] = self.keyboard_navigation_check.isChecked()
                self.settings.user_preferences.accessibility[
                    "screen_reader_support"
                ] = self.screen_reader_check.isChecked()
                language_map = {"한국어": "ko", "English": "en"}
                self.settings.user_preferences.theme_preferences["language"] = language_map.get(
                    self.language_combo.currentText(), "ko"
                )
                logger.info("🔧 [SettingsDialog] 설정 저장 중...")
                self.settings_manager.save_config()
                logger.info("✅ [SettingsDialog] 설정 저장 완료")
            logger.info("✅ 설정 저장 완료")
        except Exception as e:
            logger.info("❌ 설정 저장 실패: %s", e)
            QMessageBox.critical(self, "오류", f"설정 저장에 실패했습니다:\n{e}")

    def reset_to_defaults(self):
        """기본값으로 초기화"""
        reply = QMessageBox.question(
            self,
            "기본값으로 초기화",
            """모든 설정을 기본값으로 초기화하시겠습니까?
이 작업은 되돌릴 수 없습니다.""",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if hasattr(self.settings_manager, "config"):
                from src.core.unified_config import UnifiedConfig

                self.settings = UnifiedConfig()
                self.settings_manager.config = self.settings
            self.load_current_settings()
            logger.info("✅ 설정을 기본값으로 초기화했습니다")

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
        self.settingsChanged.emit()

    def accept(self):
        """확인 버튼 클릭 시 설정 저장"""
        self.save_settings()
        super().accept()

    def reject(self):
        """취소 버튼 클릭 시 다이얼로그 닫기"""
        super().reject()
