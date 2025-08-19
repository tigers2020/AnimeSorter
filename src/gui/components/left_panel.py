"""
왼쪽 패널 컴포넌트
빠른 작업, 통계, 필터 그룹을 포함하는 왼쪽 패널을 관리합니다.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLabel, 
    QPushButton, QLineEdit, QComboBox, QCheckBox, QProgressBar, QFrame,
    QSpinBox
)
from PyQt5.QtCore import pyqtSignal


class LeftPanel(QWidget):
    """메인 윈도우 왼쪽 패널"""
    
    # 시그널 정의
    source_folder_selected = pyqtSignal(str)
    source_files_selected = pyqtSignal(list)
    destination_folder_selected = pyqtSignal(str)
    scan_started = pyqtSignal()
    scan_paused = pyqtSignal()
    settings_opened = pyqtSignal()
    completed_cleared = pyqtSignal()
    filters_reset = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 빠른 작업 그룹
        quick_actions = self.create_quick_actions_group()
        layout.addWidget(quick_actions)
        
        # 통계 그룹
        stats_group = self.create_stats_group()
        layout.addWidget(stats_group)
        
        # 필터 그룹
        filter_group = self.create_filter_group()
        layout.addWidget(filter_group)
        
        layout.addStretch(1)
        
    def create_quick_actions_group(self):
        """빠른 작업 그룹 생성"""
        group = QGroupBox("🚀 빠른 작업")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # 소스 디렉토리 선택
        source_group = QWidget()
        source_layout = QVBoxLayout(source_group)
        source_layout.setContentsMargins(0, 0, 0, 0)
        
        source_label = QLabel("📁 소스 디렉토리")
        source_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        source_layout.addWidget(source_label)
        
        self.source_dir_label = QLabel("선택되지 않음")
        self.source_dir_label.setStyleSheet("""
            QLabel {
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px;
                color: #7f8c8d;
                font-style: italic;
            }
        """)
        self.source_dir_label.setWordWrap(True)
        source_layout.addWidget(self.source_dir_label)
        
        source_buttons = QHBoxLayout()
        self.btnChooseSourceFolder = QPushButton("📂 폴더 선택")
        self.btnChooseSourceFolder.setStyleSheet(self.get_button_style("#3498db"))
        self.btnChooseSourceFolder.setToolTip("애니메이션 파일이 있는 소스 폴더를 선택합니다")
        
        self.btnChooseSourceFiles = QPushButton("📄 파일 선택")
        self.btnChooseSourceFiles.setStyleSheet(self.get_button_style("#3498db"))
        self.btnChooseSourceFiles.setToolTip("개별 애니메이션 파일들을 선택합니다")
        
        source_buttons.addWidget(self.btnChooseSourceFolder)
        source_buttons.addWidget(self.btnChooseSourceFiles)
        source_layout.addLayout(source_buttons)
        
        layout.addWidget(source_group)
        
        # 대상 디렉토리 선택
        dest_group = QWidget()
        dest_layout = QVBoxLayout(dest_group)
        dest_layout.setContentsMargins(0, 0, 0, 0)
        
        dest_label = QLabel("🎯 대상 디렉토리")
        dest_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        dest_layout.addWidget(dest_label)
        
        self.dest_dir_label = QLabel("선택되지 않음")
        self.dest_dir_label.setStyleSheet("""
            QLabel {
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px;
                color: #7f8c8d;
                font-style: italic;
            }
        """)
        self.dest_dir_label.setWordWrap(True)
        dest_layout.addWidget(self.dest_dir_label)
        
        self.btnChooseDestFolder = QPushButton("📂 폴더 선택")
        self.btnChooseDestFolder.setStyleSheet(self.get_button_style("#27ae60"))
        self.btnChooseDestFolder.setToolTip("정리된 파일을 저장할 대상 폴더를 선택합니다")
        
        dest_layout.addWidget(self.btnChooseDestFolder)
        layout.addWidget(dest_group)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)
        
        # 스캔 제어 버튼들
        scan_layout = QHBoxLayout()
        self.btnStart = QPushButton("▶️ 스캔 시작")
        self.btnStart.setStyleSheet(self.get_button_style("#e74c3c"))
        self.btnStart.setEnabled(False)  # 소스가 선택되지 않으면 비활성화
        
        self.btnPause = QPushButton("⏸️ 일시정지")
        self.btnPause.setStyleSheet(self.get_button_style("#f39c12"))
        self.btnPause.setEnabled(False)
        
        scan_layout.addWidget(self.btnStart)
        scan_layout.addWidget(self.btnPause)
        
        # 진행률 표시
        progress_label = QLabel("진행률:")
        self.progressBar = QProgressBar()
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        
        layout.addLayout(scan_layout)
        layout.addWidget(progress_label)
        layout.addWidget(self.progressBar)
        
        return group
        
    def create_stats_group(self):
        """통계 그룹 생성"""
        group = QGroupBox("📊 통계")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QFormLayout(group)
        layout.setSpacing(8)
        
        # 통계 라벨들
        self.lblTotal = QLabel("0")
        self.lblTotal.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 14px;")
        
        self.lblParsed = QLabel("0")
        self.lblParsed.setStyleSheet("font-weight: bold; color: #27ae60; font-size: 14px;")
        
        self.lblPending = QLabel("0")
        self.lblPending.setStyleSheet("font-weight: bold; color: #f39c12; font-size: 14px;")
        
        self.lblGroups = QLabel("0")
        self.lblGroups.setStyleSheet("font-weight: bold; color: #9b59b6; font-size: 14px;")
        
        # 완료된 항목 정리 버튼
        self.btnClearCompleted = QPushButton("✅ 완료된 항목 정리")
        self.btnClearCompleted.setStyleSheet(self.get_button_style("#95a5a6"))
        
        layout.addRow("전체:", self.lblTotal)
        layout.addRow("완료:", self.lblParsed)
        layout.addRow("대기:", self.lblPending)
        layout.addRow("그룹:", self.lblGroups)
        layout.addRow("", self.btnClearCompleted)
        
        return group
        
    def create_filter_group(self):
        """필터 그룹 생성"""
        group = QGroupBox("🔍 필터")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QFormLayout(group)
        layout.setSpacing(8)
        
        # 필터 콤보박스들
        self.cmbResolution = QComboBox()
        self.cmbResolution.addItems(["전체", "2160p", "1080p", "720p"])
        
        self.cmbContainer = QComboBox()
        self.cmbContainer.addItems(["전체", "MKV", "MP4"])
        
        self.cmbCodec = QComboBox()
        self.cmbCodec.addItems(["전체", "HEVC", "H.264"])
        
        self.cmbYear = QComboBox()
        self.cmbYear.addItems(["전체", "2025", "2024", "2023"])
        
        # 필터 초기화 버튼
        self.btnResetFilters = QPushButton("🔄 필터 초기화")
        self.btnResetFilters.setStyleSheet(self.get_button_style("#e67e22"))
        
        layout.addRow("해상도:", self.cmbResolution)
        layout.addRow("컨테이너:", self.cmbContainer)
        layout.addRow("코덱:", self.cmbCodec)
        layout.addRow("년도:", self.cmbYear)
        layout.addRow("", self.btnResetFilters)
        
        return group
        
    def setup_connections(self):
        """시그널/슬롯 연결 설정"""
        self.btnChooseSourceFolder.clicked.connect(self.on_source_folder_clicked)
        self.btnChooseSourceFiles.clicked.connect(self.on_source_files_clicked)
        self.btnChooseDestFolder.clicked.connect(self.on_destination_folder_clicked)
        self.btnStart.clicked.connect(self.scan_started.emit)
        self.btnPause.clicked.connect(self.scan_paused.emit)
        self.btnClearCompleted.clicked.connect(self.completed_cleared.emit)
        self.btnResetFilters.clicked.connect(self.filters_reset.emit)
        
    def on_source_folder_clicked(self):
        """소스 폴더 선택 버튼 클릭"""
        from PyQt5.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "소스 폴더 선택")
        if folder:
            self.source_dir_label.setText(f"소스 폴더: {folder}")
            self.source_dir_label.setStyleSheet("""
                QLabel {
                    background-color: #d5f4e6;
                    border: 1px solid #27ae60;
                    border-radius: 4px;
                    padding: 8px;
                    color: #27ae60;
                    font-weight: bold;
                }
            """)
            self.source_folder_selected.emit(folder)
            
    def on_source_files_clicked(self):
        """소스 파일 선택 버튼 클릭"""
        from PyQt5.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(
            self, "애니메이션 파일 선택", "",
            "Video Files (*.mkv *.mp4 *.avi *.mov *.wmv *.flv);;All Files (*)"
        )
        if files:
            self.source_dir_label.setText(f"선택된 파일: {len(files)}개")
            self.source_dir_label.setStyleSheet("""
                QLabel {
                    background-color: #d5f4e6;
                    border: 1px solid #27ae60;
                    border-radius: 4px;
                    padding: 8px;
                    color: #27ae60;
                    font-weight: bold;
                }
            """)
            self.source_files_selected.emit(files)
            
    def on_destination_folder_clicked(self):
        """대상 폴더 선택 버튼 클릭"""
        from PyQt5.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "대상 폴더 선택")
        if folder:
            self.dest_dir_label.setText(f"대상 폴더: {folder}")
            self.dest_dir_label.setStyleSheet("""
                QLabel {
                    background-color: #d5f4e6;
                    border: 1px solid #27ae60;
                    border-radius: 4px;
                    padding: 8px;
                    color: #27ae60;
                    font-weight: bold;
                }
            """)
            self.destination_folder_selected.emit(folder)
    
    def update_scan_button_state(self, has_source: bool):
        """스캔 시작 버튼 활성화 상태 업데이트"""
        self.btnStart.setEnabled(has_source)
        
    def update_progress(self, value: int):
        """진행률 업데이트"""
        self.progressBar.setValue(value)
        
    def update_stats(self, total: int, parsed: int, pending: int, groups: int = 0):
        """통계 업데이트"""
        self.lblTotal.setText(str(total))
        self.lblParsed.setText(str(parsed))
        self.lblPending.setText(str(pending))
        
        # 그룹 수 표시 (기존 통계 라벨이 있다면 업데이트)
        if hasattr(self, 'lblGroups'):
            self.lblGroups.setText(str(groups))
        
    def reset_filters(self):
        """필터 초기화"""
        self.cmbResolution.setCurrentIndex(0)
        self.cmbContainer.setCurrentIndex(0)
        self.cmbCodec.setCurrentIndex(0)
        self.cmbYear.setCurrentIndex(0)
        
    def update_source_directory_display(self, directory: str):
        """소스 디렉토리 표시 업데이트"""
        if directory and os.path.exists(directory):
            self.source_dir_label.setText(f"소스 폴더: {directory}")
            self.source_dir_label.setStyleSheet("""
                QLabel {
                    background-color: #d5f4e6;
                    border: 1px solid #27ae60;
                    border-radius: 4px;
                    padding: 8px;
                    color: #27ae60;
                    font-weight: bold;
                }
            """)
        else:
            self.source_dir_label.setText("소스 폴더: 선택되지 않음")
            self.source_dir_label.setStyleSheet("")
    
    def update_destination_directory_display(self, directory: str):
        """대상 디렉토리 표시 업데이트"""
        if directory and os.path.exists(directory):
            self.dest_dir_label.setText(f"대상 폴더: {directory}")
            self.dest_dir_label.setStyleSheet("""
                QLabel {
                    background-color: #d5f4e6;
                    border: 1px solid #27ae60;
                    border-radius: 4px;
                    padding: 8px;
                    color: #27ae60;
                    font-weight: bold;
                }
            """)
        else:
            self.dest_dir_label.setText("대상 폴더: 선택되지 않음")
            self.dest_dir_label.setStyleSheet("")
    
    def update_source_files_display(self, file_count: int):
        """소스 파일 수 표시 업데이트"""
        if file_count > 0:
            self.source_dir_label.setText(f"선택된 파일: {file_count}개")
            self.source_dir_label.setStyleSheet("""
                QLabel {
                    background-color: #d5f4e6;
                    border: 1px solid #27ae60;
                    border-radius: 4px;
                    padding: 8px;
                    color: #27ae60;
                    font-weight: bold;
                }
            """)
        else:
            self.source_dir_label.setText("소스 폴더: 선택되지 않음")
            self.source_dir_label.setStyleSheet("")
    
    def get_button_style(self, color: str) -> str:
        """버튼 스타일 생성"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
                color: #7f8c8d;
            }}
        """
