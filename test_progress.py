#!/usr/bin/env python3
"""
실시간 진행 상태 테스트 스크립트
FileScanWorker의 진행 상태 업데이트가 제대로 작동하는지 확인
"""

import sys
import os
import tempfile
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QProgressBar, QTextEdit, QLabel
from PyQt5.QtCore import QThreadPool

# src 디렉토리를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ui.main_window import FileScanWorker
from utils.file_cleaner import FileCleaner

class ProgressTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileScanWorker 진행 상태 테스트")
        self.setGeometry(100, 100, 600, 400)
        
        # UI 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.status_label = QLabel("테스트 준비됨")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.log_text = QTextEdit()
        layout.addWidget(self.log_text)
        
        self.test_button = QPushButton("진행 상태 테스트 시작 (100개 파일)")
        self.test_button.clicked.connect(self.start_test)
        layout.addWidget(self.test_button)
        
        # 테스트 파일 생성
        self.temp_dir = tempfile.mkdtemp()
        self.create_test_files()
        
    def create_test_files(self):
        """테스트용 가짜 파일 목록 생성"""
        self.test_files = []
        
        # 다양한 애니메이션 파일명 패턴 생성
        anime_names = [
            "Attack on Titan", "Demon Slayer", "My Hero Academia", "One Piece", 
            "Naruto", "Dragon Ball", "Death Note", "Fullmetal Alchemist",
            "Tokyo Ghoul", "Hunter x Hunter", "Bleach", "Fairy Tail"
        ]
        
        for i in range(100):
            anime = anime_names[i % len(anime_names)]
            episode = i % 24 + 1
            season = i // 24 + 1
            
            # 다양한 파일명 패턴
            patterns = [
                f"[SubsPlease] {anime} - S{season:02d}E{episode:02d} [1080p].mkv",
                f"{anime} Season {season} Episode {episode} [720p].mp4",
                f"[Erai-raws] {anime} - {episode:02d} [1080p][Multiple Subtitle].mkv",
                f"{anime}.S{season:02d}E{episode:02d}.1080p.WEB-DL.x264.mkv"
            ]
            
            filename = patterns[i % len(patterns)]
            file_path = Path(self.temp_dir) / filename
            self.test_files.append(file_path)
        
        self.log_text.append(f"테스트 파일 {len(self.test_files)}개 생성됨")
        self.log_text.append(f"임시 디렉토리: {self.temp_dir}")
        
    def start_test(self):
        """FileScanWorker 테스트 시작"""
        self.test_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("테스트 시작...")
        self.log_text.append("\n=== FileScanWorker 진행 상태 테스트 시작 ===")
        
        # FileScanWorker 생성 및 시그널 연결
        self.worker = FileScanWorker(
            file_paths=self.test_files,
            export_dir=self.temp_dir,
            file_cleaner=FileCleaner(),
            config=None
        )
        
        # 시그널 연결
        self.worker.signals.progress.connect(self.on_progress)
        self.worker.signals.log.connect(self.on_log)
        self.worker.signals.result.connect(self.on_result)
        self.worker.signals.finished.connect(self.on_finished)
        
        # 백그라운드에서 실행
        QThreadPool.globalInstance().start(self.worker)
        
    def on_progress(self, percent, message):
        """진행 상태 업데이트"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"{percent}% - {message}")
        
    def on_log(self, message):
        """로그 메시지 표시"""
        self.log_text.append(message)
        
    def on_result(self, grouped_files):
        """결과 처리"""
        self.log_text.append(f"\n=== 결과 ===")
        self.log_text.append(f"그룹 수: {len(grouped_files)}")
        
        # 상위 5개 그룹 표시
        for i, (key, files) in enumerate(list(grouped_files.items())[:5]):
            title, year = key
            self.log_text.append(f"그룹 {i+1}: '{title}' ({year}) - {len(files)}개 파일")
            
    def on_finished(self):
        """작업 완료"""
        self.test_button.setEnabled(True)
        self.status_label.setText("테스트 완료!")
        self.log_text.append("=== 테스트 완료 ===")

def main():
    app = QApplication(sys.argv)
    window = ProgressTestWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 