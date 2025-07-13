#!/usr/bin/env python3
"""
AnimeSorter - 애니메이션 파일 정리 도구
"""

from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import sys
import os
import datetime
import requests
from pathlib import Path
from src.ui.main_window import MainWindow

# --- src 경로를 sys.path에 추가 (import 오류 방지) ---
sys.path.insert(0, str(Path(__file__).parent / "src"))

EXPORT_DIR = "./tmdb_exports"
TMDB_EXPORT_BASE = "http://files.tmdb.org/p/exports"
DATE_FMT = "%m_%d_%Y"

EXPORT_TYPES = [
    ("Movies", "movie_ids_{date}.json.gz"),
    ("TV Series", "tv_series_ids_{date}.json.gz"),
    ("People", "person_ids_{date}.json.gz"),
    ("Collections", "collection_ids_{date}.json.gz"),
    ("TV Networks", "tv_network_ids_{date}.json.gz"),
    ("Keywords", "keyword_ids_{date}.json.gz"),
    ("Production Companies", "production_company_ids_{date}.json.gz"),
]

class TMDBDownloadWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def run(self):
        try:
            os.makedirs(EXPORT_DIR, exist_ok=True)
            today = datetime.datetime.utcnow().strftime(DATE_FMT)
            for label, pattern in EXPORT_TYPES:
                filename = pattern.format(date=today)
                url = f"{TMDB_EXPORT_BASE}/{filename}"
                local_path = os.path.join(EXPORT_DIR, filename)
                if os.path.exists(local_path):
                    self.progress.emit(f"[{label}] {filename} 이미 존재, 건너뜀")
                    continue
                self.progress.emit(f"[{label}] {filename} 다운로드 중...")
                resp = requests.get(url, stream=True, timeout=30)
                if resp.status_code == 200:
                    with open(local_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    self.progress.emit(f"[{label}] {filename} 다운로드 완료")
                else:
                    self.error.emit(f"[{label}] {filename} 다운로드 실패 (status {resp.status_code})")
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()

class TMDBDownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TMDB 데이터 다운로드")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)
        layout = QVBoxLayout(self)
        self.label = QLabel("TMDB 데이터 다운로드 중...", self)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        self.worker = TMDBDownloadWorker()
        self.worker.progress.connect(self.label.setText)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.accept)
        self.worker.start()

    def on_error(self, msg):
        self.label.setText(f"오류: {msg}")


def main():
    app = QApplication(sys.argv)
    # TMDB export 다운로드 다이얼로그 최우선 실행
    dialog = TMDBDownloadDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        from src.ui.main_window import MainWindow
        window = MainWindow()
        window.show()
        sys.exit(app.exec())

if __name__ == "__main__":
    main() 