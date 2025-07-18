from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel, QCheckBox, QGroupBox
from src.config.config_manager import ConfigManager

class SettingsDialog(QDialog):
    """
    TMDB API 키 및 언어 설정 대화상자
    """
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("설정")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # TMDB 설정 그룹
        tmdb_group = QGroupBox("TMDB API 설정")
        tmdb_layout = QFormLayout(tmdb_group)
        self.api_key_edit = QLineEdit()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["ko-KR", "en-US", "ja-JP", "zh-CN"])
        tmdb_layout.addRow(QLabel("TMDB API 키:"), self.api_key_edit)
        tmdb_layout.addRow(QLabel("TMDB 언어:"), self.language_combo)
        layout.addWidget(tmdb_group)
        
        # 파일 처리 설정 그룹
        file_group = QGroupBox("파일 처리 설정")
        file_layout = QFormLayout(file_group)
        self.overwrite_checkbox = QCheckBox("기존 파일 덮어쓰기")
        self.overwrite_checkbox.setToolTip("대상 폴더에 같은 이름의 파일이 있을 때 덮어쓰기 여부")
        file_layout.addRow(self.overwrite_checkbox)
        layout.addWidget(file_group)
        
        # 버튼
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _load_config(self):
        self.api_key_edit.setText(self.config.get("tmdb.api_key", ""))
        lang = self.config.get("tmdb.language", "ko-KR")
        idx = self.language_combo.findText(lang)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        
        # 파일 처리 설정 로드
        overwrite = self.config.get("file_processing.overwrite_existing", False)
        self.overwrite_checkbox.setChecked(overwrite)

    def accept(self):
        self.config.set("tmdb.api_key", self.api_key_edit.text().strip())
        self.config.set("tmdb.language", self.language_combo.currentText())
        self.config.set("file_processing.overwrite_existing", self.overwrite_checkbox.isChecked())
        self.config.save_config()
        super().accept() 