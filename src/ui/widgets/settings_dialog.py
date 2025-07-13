from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel
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
        form = QFormLayout()
        self.api_key_edit = QLineEdit()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["ko-KR", "en-US", "ja-JP", "zh-CN"])
        form.addRow(QLabel("TMDB API 키:"), self.api_key_edit)
        form.addRow(QLabel("TMDB 언어:"), self.language_combo)
        layout.addLayout(form)
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

    def accept(self):
        self.config.set("tmdb.api_key", self.api_key_edit.text().strip())
        self.config.set("tmdb.language", self.language_combo.currentText())
        self.config.save_config()
        super().accept() 