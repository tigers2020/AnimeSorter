from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, 
    QLabel, QCheckBox, QGroupBox, QHBoxLayout, QPushButton, QTextEdit, 
    QTabWidget, QSpinBox, QFileDialog, QMessageBox, QProgressBar, QWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor
import json
import os
from pathlib import Path
from datetime import datetime
from src.config.config_manager import ConfigManager

class ConfigValidator:
    """설정 검증 클래스"""
    
    @staticmethod
    def validate_api_key(api_key: str) -> tuple[bool, str]:
        """TMDB API 키 검증"""
        if not api_key:
            return False, "API 키가 비어있습니다."
        if len(api_key) < 20:
            return False, "API 키가 너무 짧습니다."
        if not api_key.startswith(('eyJ', 'v3')):
            return False, "올바른 TMDB API 키 형식이 아닙니다."
        return True, "유효한 API 키입니다."
    
    @staticmethod
    def validate_language(language: str) -> tuple[bool, str]:
        """언어 설정 검증"""
        valid_languages = ["ko-KR", "en-US", "ja-JP", "zh-CN"]
        if language not in valid_languages:
            return False, f"지원하지 않는 언어입니다: {language}"
        return True, "유효한 언어 설정입니다."
    
    @staticmethod
    def validate_file_extensions(extensions: str) -> tuple[bool, str]:
        """파일 확장자 검증"""
        if not extensions:
            return False, "파일 확장자가 비어있습니다."
        ext_list = [ext.strip() for ext in extensions.split(',')]
        for ext in ext_list:
            if not ext.startswith('.'):
                return False, f"확장자는 '.'으로 시작해야 합니다: {ext}"
        return True, "유효한 파일 확장자입니다."

class SettingsPreview(QTextEdit):
    """설정 미리보기 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumHeight(150)
        self.setFont(QFont("Consolas", 9))
        
    def update_preview(self, config_data: dict):
        """미리보기 업데이트"""
        preview_text = "설정 미리보기:\n"
        preview_text += "=" * 30 + "\n"
        
        for key, value in config_data.items():
            if key == "tmdb.api_key" and value:
                # API 키는 일부만 표시
                masked_key = value[:8] + "*" * (len(value) - 12) + value[-4:]
                preview_text += f"{key}: {masked_key}\n"
            else:
                preview_text += f"{key}: {value}\n"
                
        self.setPlainText(preview_text)

class SettingsDialog(QDialog):
    """
    TMDB API 키 및 언어 설정 대화상자
    """
    
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.original_config = self._get_current_config()
        self.setWindowTitle("설정")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        self._setup_ui()
        self._load_config()
        self._setup_validation()
        
    def _get_current_config(self) -> dict:
        """현재 설정을 딕셔너리로 반환"""
        return {
            "tmdb.api_key": self.config.get("tmdb.api_key", ""),
            "tmdb.language": self.config.get("tmdb.language", "ko-KR"),
            "file_processing.overwrite_existing": self.config.get("file_processing.overwrite_existing", False),
            "file_processing.max_workers": self.config.get("file_processing.max_workers", 4),
            "file_processing.supported_extensions": self.config.get("file_processing.supported_extensions", ".mp4,.mkv,.avi,.mov"),
            "ui.theme": self.config.get("ui.theme", "system"),
            "ui.auto_save_interval": self.config.get("ui.auto_save_interval", 30)
        }

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 탭 위젯 생성
        tab_widget = QTabWidget()
        
        # TMDB 설정 탭
        tmdb_tab = self._create_tmdb_tab()
        tab_widget.addTab(tmdb_tab, "TMDB API")
        
        # 파일 처리 설정 탭
        file_tab = self._create_file_tab()
        tab_widget.addTab(file_tab, "파일 처리")
        
        # UI 설정 탭
        ui_tab = self._create_ui_tab()
        tab_widget.addTab(ui_tab, "UI 설정")
        
        # 백업/복원 탭
        backup_tab = self._create_backup_tab()
        tab_widget.addTab(backup_tab, "백업/복원")
        
        layout.addWidget(tab_widget)
        
        # 미리보기 영역
        preview_group = QGroupBox("설정 미리보기")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_widget = SettingsPreview()
        preview_layout.addWidget(self.preview_widget)
        layout.addWidget(preview_group)
        
        # 검증 결과 표시
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.validation_label)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        # 백업/복원 버튼
        backup_button = QPushButton("설정 백업")
        backup_button.clicked.connect(self._backup_settings)
        button_layout.addWidget(backup_button)
        
        restore_button = QPushButton("설정 복원")
        restore_button.clicked.connect(self._restore_settings)
        button_layout.addWidget(restore_button)
        
        button_layout.addStretch()
        
        # 표준 버튼
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.Reset
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self._reset_settings)
        button_layout.addWidget(self.button_box)
        
        layout.addLayout(button_layout)
        
    def _create_tmdb_tab(self):
        """TMDB 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # TMDB 설정 그룹
        tmdb_group = QGroupBox("TMDB API 설정")
        tmdb_layout = QFormLayout(tmdb_group)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("TMDB API 키를 입력하세요")
        tmdb_layout.addRow(QLabel("TMDB API 키:"), self.api_key_edit)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["ko-KR", "en-US", "ja-JP", "zh-CN"])
        tmdb_layout.addRow(QLabel("TMDB 언어:"), self.language_combo)
        
        # API 키 테스트 버튼
        test_button = QPushButton("API 키 테스트")
        test_button.clicked.connect(self._test_api_key)
        tmdb_layout.addRow("", test_button)
        
        layout.addWidget(tmdb_group)
        layout.addStretch()
        return widget
        
    def _create_file_tab(self):
        """파일 처리 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 파일 처리 설정 그룹
        file_group = QGroupBox("파일 처리 설정")
        file_layout = QFormLayout(file_group)
        
        self.overwrite_checkbox = QCheckBox("기존 파일 덮어쓰기")
        self.overwrite_checkbox.setToolTip("대상 폴더에 같은 이름의 파일이 있을 때 덮어쓰기 여부")
        file_layout.addRow(self.overwrite_checkbox)
        
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 16)
        self.max_workers_spin.setToolTip("동시에 처리할 파일 수")
        file_layout.addRow(QLabel("최대 동시 처리:"), self.max_workers_spin)
        
        self.extensions_edit = QLineEdit()
        self.extensions_edit.setPlaceholderText(".mp4,.mkv,.avi,.mov")
        self.extensions_edit.setToolTip("지원할 파일 확장자 (쉼표로 구분)")
        file_layout.addRow(QLabel("지원 확장자:"), self.extensions_edit)
        
        layout.addWidget(file_group)
        layout.addStretch()
        return widget
        
    def _create_ui_tab(self):
        """UI 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # UI 설정 그룹
        ui_group = QGroupBox("UI 설정")
        ui_layout = QFormLayout(ui_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        ui_layout.addRow(QLabel("테마:"), self.theme_combo)
        
        self.auto_save_spin = QSpinBox()
        self.auto_save_spin.setRange(10, 300)
        self.auto_save_spin.setSuffix(" 초")
        self.auto_save_spin.setToolTip("자동 저장 간격")
        ui_layout.addRow(QLabel("자동 저장 간격:"), self.auto_save_spin)
        
        layout.addWidget(ui_group)
        
        # 자동화 설정 그룹
        auto_group = QGroupBox("자동화 설정")
        auto_layout = QFormLayout(auto_group)
        
        self.auto_scan_checkbox = QCheckBox("소스 폴더 선택 시 자동 스캔")
        self.auto_scan_checkbox.setToolTip("소스 폴더를 선택하거나 변경할 때 자동으로 파일 스캔을 실행합니다")
        auto_layout.addRow(self.auto_scan_checkbox)
        
        self.auto_sync_checkbox = QCheckBox("스캔 완료 후 자동 메타데이터 동기화")
        self.auto_sync_checkbox.setToolTip("파일 스캔이 완료되면 자동으로 메타데이터 동기화를 실행합니다")
        auto_layout.addRow(self.auto_sync_checkbox)
        
        self.auto_start_checkbox = QCheckBox("프로그램 시작 시 자동 스캔")
        self.auto_start_checkbox.setToolTip("프로그램 시작 시 저장된 소스 폴더가 있으면 자동으로 스캔을 실행합니다")
        auto_layout.addRow(self.auto_start_checkbox)
        
        layout.addWidget(auto_group)
        layout.addStretch()
        return widget
        
    def _create_backup_tab(self):
        """백업/복원 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 백업 정보
        info_group = QGroupBox("백업 정보")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(100)
        info_text.setPlainText(
            "설정 백업/복원 기능:\n"
            "• 설정을 JSON 파일로 내보내기/가져오기\n"
            "• 설정 변경 전 자동 백업\n"
            "• 설정 복원 시 이전 상태로 되돌리기"
        )
        info_layout.addWidget(info_text)
        layout.addWidget(info_group)
        
        # 백업 목록
        backup_group = QGroupBox("백업 목록")
        backup_layout = QVBoxLayout(backup_group)
        
        self.backup_list = QTextEdit()
        self.backup_list.setReadOnly(True)
        self.backup_list.setMaximumHeight(150)
        backup_layout.addWidget(self.backup_list)
        
        # 백업 새로고침 버튼
        refresh_button = QPushButton("백업 목록 새로고침")
        refresh_button.clicked.connect(self._refresh_backup_list)
        backup_layout.addWidget(refresh_button)
        
        layout.addWidget(backup_group)
        layout.addStretch()
        return widget

    def _load_config(self):
        """설정 로드"""
        self.api_key_edit.setText(self.config.get("tmdb.api_key", ""))
        
        lang = self.config.get("tmdb.language", "ko-KR")
        idx = self.language_combo.findText(lang)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        
        self.overwrite_checkbox.setChecked(self.config.get("file_processing.overwrite_existing", False))
        self.max_workers_spin.setValue(self.config.get("file_processing.max_workers", 4))
        self.extensions_edit.setText(self.config.get("file_processing.supported_extensions", ".mp4,.mkv,.avi,.mov"))
        
        theme = self.config.get("ui.theme", "system")
        idx = self.theme_combo.findText(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
            
        self.auto_save_spin.setValue(self.config.get("ui.auto_save_interval", 30))
        
        # 자동화 설정 로드
        self.auto_scan_checkbox.setChecked(self.config.get("automation.auto_scan_on_folder_change", True))
        self.auto_sync_checkbox.setChecked(self.config.get("automation.auto_sync_after_scan", True))
        self.auto_start_checkbox.setChecked(self.config.get("automation.auto_scan_on_startup", True))
        
        # 미리보기 업데이트
        self._update_preview()
        self._refresh_backup_list()
        
    def _setup_validation(self):
        """설정 검증 설정"""
        # 실시간 검증을 위한 타이머
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self._validate_settings)
        
        # 입력 변경 시 검증 트리거
        self.api_key_edit.textChanged.connect(self._trigger_validation)
        self.language_combo.currentTextChanged.connect(self._trigger_validation)
        self.extensions_edit.textChanged.connect(self._trigger_validation)
        
        # 입력 변경 시 미리보기 업데이트
        self.api_key_edit.textChanged.connect(self._update_preview)
        self.language_combo.currentTextChanged.connect(self._update_preview)
        self.overwrite_checkbox.toggled.connect(self._update_preview)
        self.max_workers_spin.valueChanged.connect(self._update_preview)
        self.extensions_edit.textChanged.connect(self._update_preview)
        self.theme_combo.currentTextChanged.connect(self._update_preview)
        self.auto_save_spin.valueChanged.connect(self._update_preview)
        
        # 자동화 설정 변경 시 미리보기 업데이트
        self.auto_scan_checkbox.toggled.connect(self._update_preview)
        self.auto_sync_checkbox.toggled.connect(self._update_preview)
        self.auto_start_checkbox.toggled.connect(self._update_preview)
        
    def _trigger_validation(self):
        """검증 트리거"""
        self.validation_timer.start(500)  # 0.5초 후 검증
        
    def _validate_settings(self):
        """설정 검증"""
        errors = []
        warnings = []
        
        # API 키 검증
        api_key = self.api_key_edit.text().strip()
        is_valid, message = ConfigValidator.validate_api_key(api_key)
        if not is_valid:
            errors.append(f"API 키: {message}")
        elif api_key:
            warnings.append(f"API 키: {message}")
            
        # 언어 검증
        language = self.language_combo.currentText()
        is_valid, message = ConfigValidator.validate_language(language)
        if not is_valid:
            errors.append(f"언어: {message}")
            
        # 확장자 검증
        extensions = self.extensions_edit.text().strip()
        is_valid, message = ConfigValidator.validate_file_extensions(extensions)
        if not is_valid:
            errors.append(f"확장자: {message}")
            
        # 결과 표시
        if errors:
            self.validation_label.setText("❌ " + "; ".join(errors))
            self.validation_label.setStyleSheet("color: red; font-weight: bold;")
        elif warnings:
            self.validation_label.setText("⚠️ " + "; ".join(warnings))
            self.validation_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.validation_label.setText("✅ 모든 설정이 유효합니다")
            self.validation_label.setStyleSheet("color: green; font-weight: bold;")
            
    def _update_preview(self):
        """미리보기 업데이트"""
        config_data = {
            "tmdb.api_key": self.api_key_edit.text().strip(),
            "tmdb.language": self.language_combo.currentText(),
            "file_processing.overwrite_existing": self.overwrite_checkbox.isChecked(),
            "file_processing.max_workers": self.max_workers_spin.value(),
            "file_processing.supported_extensions": self.extensions_edit.text().strip(),
            "ui.theme": self.theme_combo.currentText(),
            "ui.auto_save_interval": self.auto_save_spin.value(),
            "automation.auto_scan_on_folder_change": self.auto_scan_checkbox.isChecked(),
            "automation.auto_sync_after_scan": self.auto_sync_checkbox.isChecked(),
            "automation.auto_scan_on_startup": self.auto_start_checkbox.isChecked()
        }
        self.preview_widget.update_preview(config_data)
        
    def _test_api_key(self):
        """API 키 테스트"""
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "경고", "API 키를 입력해주세요.")
            return
            
        # 간단한 API 테스트 (실제로는 TMDB API 호출)
        QMessageBox.information(self, "테스트", "API 키 테스트 기능은 향후 구현 예정입니다.")
        
    def _backup_settings(self):
        """설정 백업"""
        try:
            backup_dir = Path("./backups")
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"settings_backup_{timestamp}.json"
            
            config_data = self._get_current_config()
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
                
            QMessageBox.information(self, "백업 완료", f"설정이 백업되었습니다:\n{backup_file}")
            self._refresh_backup_list()
            
        except Exception as e:
            QMessageBox.critical(self, "백업 실패", f"설정 백업 중 오류가 발생했습니다:\n{e}")
            
    def _restore_settings(self):
        """설정 복원"""
        try:
            backup_file, _ = QFileDialog.getOpenFileName(
                self, "백업 파일 선택", "./backups", "JSON Files (*.json)"
            )
            
            if not backup_file:
                return
                
            with open(backup_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            # 설정 복원
            for key, value in config_data.items():
                self.config.set(key, value)
                
            # UI 업데이트
            self._load_config()
            
            QMessageBox.information(self, "복원 완료", "설정이 복원되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "복원 실패", f"설정 복원 중 오류가 발생했습니다:\n{e}")
            
    def _reset_settings(self):
        """설정 초기화"""
        reply = QMessageBox.question(
            self, "설정 초기화", 
            "모든 설정을 기본값으로 초기화하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 기본값으로 설정
            self.api_key_edit.clear()
            self.language_combo.setCurrentText("ko-KR")
            self.overwrite_checkbox.setChecked(False)
            self.max_workers_spin.setValue(4)
            self.extensions_edit.setText(".mp4,.mkv,.avi,.mov")
            self.theme_combo.setCurrentText("system")
            self.auto_save_spin.setValue(30)
            
            self._update_preview()
            self._validate_settings()
            
    def _refresh_backup_list(self):
        """백업 목록 새로고침"""
        try:
            backup_dir = Path("./backups")
            if not backup_dir.exists():
                self.backup_list.setPlainText("백업 폴더가 없습니다.")
                return
                
            backup_files = list(backup_dir.glob("settings_backup_*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            if not backup_files:
                self.backup_list.setPlainText("백업 파일이 없습니다.")
                return
                
            backup_text = "최근 백업 파일:\n"
            backup_text += "=" * 30 + "\n"
            
            for i, backup_file in enumerate(backup_files[:5]):  # 최근 5개만 표시
                mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                backup_text += f"{i+1}. {backup_file.name}\n"
                backup_text += f"   생성: {mtime.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                
            self.backup_list.setPlainText(backup_text)
            
        except Exception as e:
            self.backup_list.setPlainText(f"백업 목록 로드 실패: {e}")

    def accept(self):
        """확인 버튼 클릭 시 처리"""
        # 설정 검증
        self._validate_settings()
        
        # 오류가 있으면 저장하지 않음
        if "❌" in self.validation_label.text():
            QMessageBox.warning(self, "설정 오류", "설정에 오류가 있습니다. 수정 후 다시 시도해주세요.")
            return
            
        # 설정 저장
        self.config.set("tmdb.api_key", self.api_key_edit.text().strip())
        self.config.set("tmdb.language", self.language_combo.currentText())
        self.config.set("file_processing.overwrite_existing", self.overwrite_checkbox.isChecked())
        self.config.set("file_processing.max_workers", self.max_workers_spin.value())
        self.config.set("file_processing.supported_extensions", self.extensions_edit.text().strip())
        self.config.set("ui.theme", self.theme_combo.currentText())
        self.config.set("ui.auto_save_interval", self.auto_save_spin.value())
        
        # 자동화 설정
        self.config.set("automation.auto_scan_on_folder_change", self.auto_scan_checkbox.isChecked())
        self.config.set("automation.auto_sync_after_scan", self.auto_sync_checkbox.isChecked())
        self.config.set("automation.auto_scan_on_startup", self.auto_start_checkbox.isChecked())
        
        # 설정 파일에 저장
        self.config.save_config()
        
        super().accept() 