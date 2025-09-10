"""
왼쪽 패널 컴포넌트
빠른 작업, 통계, 필터 그룹을 포함하는 왼쪽 패널을 관리합니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QFormLayout, QFrame, QGroupBox, QHBoxLayout,
                             QLabel, QPushButton, QSizePolicy, QVBoxLayout,
                             QWidget)


class LeftPanel(QWidget):
    """메인 윈도우 왼쪽 패널"""

    source_folder_selected = pyqtSignal(str)
    source_files_selected = pyqtSignal(list)
    destination_folder_selected = pyqtSignal(str)
    scan_started = pyqtSignal()
    scan_paused = pyqtSignal()
    settings_opened = pyqtSignal()
    completed_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        quick_actions = self.create_quick_actions_group()
        layout.addWidget(quick_actions)
        stats_group = self.create_stats_group()
        layout.addWidget(stats_group)
        layout.addStretch(1)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    def create_quick_actions_group(self):
        """빠른 작업 그룹 생성"""
        group = QGroupBox("🚀 빠른 작업")
        group.setStyleSheet(
            """
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
        """
        )
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        source_group = QWidget()
        source_layout = QVBoxLayout(source_group)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_label = QLabel("📁 소스 디렉토리")
        source_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        source_layout.addWidget(source_label)
        self.source_dir_label = QLabel("선택되지 않음")
        self.source_dir_label.setStyleSheet(
            """
            QLabel {
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px;
                color: #7f8c8d;
                font-style: italic;
            }
        """
        )
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
        dest_group = QWidget()
        dest_layout = QVBoxLayout(dest_group)
        dest_layout.setContentsMargins(0, 0, 0, 0)
        dest_label = QLabel("🎯 대상 디렉토리")
        dest_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        dest_layout.addWidget(dest_label)
        self.dest_dir_label = QLabel("선택되지 않음")
        self.dest_dir_label.setStyleSheet(
            """
            QLabel {
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px;
                color: #7f8c8d;
                font-style: italic;
            }
        """
        )
        self.dest_dir_label.setWordWrap(True)
        dest_layout.addWidget(self.dest_dir_label)
        self.btnChooseDestFolder = QPushButton("📂 폴더 선택")
        self.btnChooseDestFolder.setStyleSheet(self.get_button_style("#27ae60"))
        self.btnChooseDestFolder.setToolTip("정리된 파일을 저장할 대상 폴더를 선택합니다")
        dest_layout.addWidget(self.btnChooseDestFolder)
        layout.addWidget(dest_group)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)
        scan_layout = QHBoxLayout()
        self.btnStart = QPushButton("▶️ 스캔 시작")
        self.btnStart.setStyleSheet(self.get_button_style("#e74c3c"))
        self.btnStart.setEnabled(False)
        self.btnPause = QPushButton("⏸️ 일시정지")
        self.btnPause.setStyleSheet(self.get_button_style("#f39c12"))
        self.btnPause.setEnabled(False)
        scan_layout.addWidget(self.btnStart)
        scan_layout.addWidget(self.btnPause)
        layout.addLayout(scan_layout)
        return group

    def create_stats_group(self):
        """통계 그룹 생성"""
        group = QGroupBox("📊 통계")
        group.setStyleSheet(
            """
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
        """
        )
        layout = QFormLayout(group)
        layout.setSpacing(8)
        self.lblTotal = QLabel("0")
        self.lblTotal.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 14px;")
        self.lblParsed = QLabel("0")
        self.lblParsed.setStyleSheet("font-weight: bold; color: #27ae60; font-size: 14px;")
        self.lblPending = QLabel("0")
        self.lblPending.setStyleSheet("font-weight: bold; color: #f39c12; font-size: 14px;")
        self.lblGroups = QLabel("0")
        self.lblGroups.setStyleSheet("font-weight: bold; color: #9b59b6; font-size: 14px;")
        self.btnClearCompleted = QPushButton("✅ 완료된 항목 정리")
        self.btnClearCompleted.setStyleSheet(self.get_button_style("#95a5a6"))
        layout.addRow("전체:", self.lblTotal)
        layout.addRow("완료:", self.lblParsed)
        layout.addRow("대기:", self.lblPending)
        layout.addRow("그룹:", self.lblGroups)
        layout.addRow("", self.btnClearCompleted)
        return group

    def update_scan_button_state(self, has_source: bool):
        """스캔 시작 버튼 활성화 상태 업데이트"""
        self.btnStart.setEnabled(has_source)

    def update_stats(self, total: int, parsed: int, pending: int, groups: int = 0):
        """통계 업데이트"""
        self.lblTotal.setText(str(total))
        self.lblParsed.setText(str(parsed))
        self.lblPending.setText(str(pending))
        if hasattr(self, "lblGroups"):
            self.lblGroups.setText(str(groups))

    def update_source_files_display(self, file_count: int):
        """소스 파일 수 표시 업데이트"""
        if file_count > 0:
            self.source_dir_label.setText(f"선택된 파일: {file_count}개")
            self.source_dir_label.setStyleSheet(
                """
                QLabel {
                    background-color: #d5f4e6;
                    border: 1px solid #27ae60;
                    border-radius: 4px;
                    padding: 8px;
                    color: #27ae60;
                    font-weight: bold;
                }
            """
            )
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

    def setup_connections(self):
        """시그널/슬롯 연결 설정"""
        self.btnChooseSourceFolder.clicked.connect(self.choose_source_folder)
        self.btnChooseSourceFiles.clicked.connect(self.choose_source_files)
        self.btnChooseDestFolder.clicked.connect(self.choose_dest_folder)
        self.btnStart.clicked.connect(self.start_scan)
        self.btnPause.clicked.connect(self.pause_scan)
        self.btnClearCompleted.clicked.connect(self.completed_cleared.emit)

    def set_main_window(self, main_window):
        """MainWindow 참조 설정"""
        self.main_window = main_window

    def choose_source_folder(self):
        """소스 폴더 선택"""
        from PyQt5.QtWidgets import QFileDialog

        start_dir = ""
        if self.main_window and hasattr(self.main_window, "settings_manager"):
            start_dir = getattr(
                self.main_window.settings_manager.config.user_preferences.gui_state,
                "last_source_directory",
                "",
            )
        folder = QFileDialog.getExistingDirectory(
            self, "애니메이션 파일이 있는 소스 폴더 선택", start_dir
        )
        if folder:
            self.update_source_directory_display(folder)
            self.source_folder_selected.emit(folder)
            if self.main_window:
                self.main_window.source_directory = folder
                logger.info("🔧 MainWindow.source_directory 업데이트: %s", folder)
            if self.main_window and hasattr(self.main_window, "settings_manager"):
                self.main_window.settings_manager.set_setting("last_source_directory", folder)
                if hasattr(self.main_window.settings_manager, "config"):
                    self.main_window.settings_manager.save_config()
                else:
                    self.main_window.settings_manager.save_settings()
                logger.info("💾 소스 디렉토리 저장됨: %s", folder)

    def choose_source_files(self):
        """소스 파일들 선택"""
        from PyQt5.QtWidgets import QFileDialog

        start_dir = ""
        if self.main_window and hasattr(self.main_window, "settings_manager"):
            start_dir = getattr(
                self.main_window.settings_manager.config.user_preferences.gui_state,
                "last_source_directory",
                "",
            )
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "애니메이션 파일들 선택",
            start_dir,
            "비디오 파일 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm);;모든 파일 (*)",
        )
        if files:
            self.update_source_files_display(len(files))
            self.source_files_selected.emit(files)
            if self.main_window:
                self.main_window.source_files = files
                logger.info("🔧 MainWindow.source_files 업데이트: %s개 파일", len(files))
            if self.main_window and hasattr(self.main_window, "settings_manager"):
                from pathlib import Path

                first_file_dir = str(Path(files[0]).parent)
                self.main_window.settings_manager.set_setting(
                    "last_source_directory", first_file_dir
                )
                if hasattr(self.main_window.settings_manager, "config"):
                    self.main_window.settings_manager.save_config()
                else:
                    self.main_window.settings_manager.save_settings()

    def choose_dest_folder(self):
        """대상 폴더 선택"""
        from PyQt5.QtWidgets import QFileDialog

        start_dir = ""
        if (
            self.main_window
            and hasattr(self.main_window, "settings_manager")
            and hasattr(self.main_window.settings_manager, "config")
        ):
            start_dir = getattr(
                self.main_window.settings_manager.config.user_preferences,
                "last_destination_directory",
                "",
            )
        folder = QFileDialog.getExistingDirectory(
            self, "정리된 파일을 저장할 대상 폴더 선택", start_dir
        )
        if folder:
            self.update_dest_directory_display(folder)
            self.destination_folder_selected.emit(folder)
            if self.main_window:
                self.main_window.destination_directory = folder
                logger.info("🔧 MainWindow.destination_directory 업데이트: %s", folder)
            if self.main_window and hasattr(self.main_window, "settings_manager"):
                if hasattr(self.main_window.settings_manager, "config"):
                    (
                        self.main_window.settings_manager.config.user_preferences.last_destination_directory
                    ) = folder
                    (self.main_window.settings_manager.config.application.destination_root) = folder
                    self.main_window.settings_manager.save_config()
                    self.main_window.settings_manager.set_setting("destination_root", folder)
                    if hasattr(self.main_window.settings_manager, "config"):
                        self.main_window.settings_manager.save_config()
                    else:
                        self.main_window.settings_manager.save_settings()
                logger.info("💾 대상 디렉토리 저장됨: %s", folder)

    def start_scan(self):
        """스캔 시작"""
        logger.info("🔴 LeftPanel.start_scan() 호출됨")
        self.scan_started.emit()
        logger.info("🔴 scan_started 시그널 발생됨")

    def pause_scan(self):
        """스캔 일시정지"""
        logger.info("🟡 LeftPanel.pause_scan() 호출됨")
        self.scan_paused.emit()
        logger.info("🟡 scan_paused 시그널 발생됨")

    def restore_directory_settings(self):
        """설정에서 디렉토리 정보 복원"""
        logger.info("🔧 [LeftPanel] 디렉토리 설정 복원 시작")
        if not self.main_window:
            logger.info("⚠️ [LeftPanel] main_window가 없습니다")
            return
        if not hasattr(self.main_window, "settings_manager"):
            logger.info("⚠️ [LeftPanel] settings_manager가 없습니다")
            return
        try:
            gui_state = self.main_window.settings_manager.config.user_preferences.gui_state
            logger.info("🔧 [LeftPanel] gui_state: %s", gui_state)
            source_dir = gui_state.get("last_source_directory", "")
            logger.info("🔧 [LeftPanel] source_dir: '%s'", source_dir)
            if source_dir:
                self.update_source_directory_display(source_dir)
                self.main_window.source_directory = source_dir
                logger.info("✅ [LeftPanel] MainWindow.source_directory 복원됨: %s", source_dir)
            else:
                logger.info("⚠️ [LeftPanel] source_dir이 비어있습니다")
            dest_dir = gui_state.get("last_destination_directory", "")
            logger.info("🔧 [LeftPanel] dest_dir: '%s'", dest_dir)
            if dest_dir:
                self.update_dest_directory_display(dest_dir)
                self.main_window.destination_directory = dest_dir
                logger.info("✅ [LeftPanel] MainWindow.destination_directory 복원됨: %s", dest_dir)
            else:
                logger.info("⚠️ [LeftPanel] dest_dir이 비어있습니다")
        except Exception as e:
            logger.info("❌ [LeftPanel] 디렉토리 설정 복원 실패: %s", e)
            import traceback

            traceback.print_exc()

    def update_source_directory_display(self, folder_path: str):
        """소스 디렉토리 표시 업데이트"""
        if folder_path:
            from pathlib import Path

            path = Path(folder_path)
            display_path = str(path)
            if len(display_path) > 40:
                display_path = f"...{display_path[-37:]}"
            self.source_dir_label.setText(f"소스 폴더: {display_path}")
            self.source_dir_label.setStyleSheet(
                """
                QLabel {
                    background-color: #d5f4e6;
                    border: 1px solid #27ae60;
                    border-radius: 4px;
                    padding: 8px;
                    color: #27ae60;
                    font-weight: bold;
                }
            """
            )
            self.btnStart.setEnabled(True)
        else:
            self.source_dir_label.setText("소스 폴더: 선택되지 않음")
            self.source_dir_label.setStyleSheet("")
            self.btnStart.setEnabled(False)

    def update_dest_directory_display(self, folder_path: str):
        """대상 디렉토리 표시 업데이트"""
        if folder_path:
            from pathlib import Path

            path = Path(folder_path)
            display_path = str(path)
            if len(display_path) > 40:
                display_path = f"...{display_path[-37:]}"
            self.dest_dir_label.setText(f"대상 폴더: {display_path}")
            self.dest_dir_label.setStyleSheet(
                """
                QLabel {
                    background-color: #ffeaa7;
                    border: 1px solid #fdcb6e;
                    border-radius: 4px;
                    padding: 8px;
                    color: #e17055;
                    font-weight: bold;
                }
            """
            )
        else:
            self.dest_dir_label.setText("대상 폴더: 선택되지 않음")
            self.dest_dir_label.setStyleSheet("")

    def update_progress(self, progress_percent: int):
        """진행률 업데이트 (0-100)"""

    def open_settings(self):
        """설정 창 열기"""
        self.settings_opened.emit()

    def stop_scan(self):
        """스캔 중지"""
        self.scan_paused.emit()

    def clear_completed(self):
        """완료된 항목 정리"""
        self.completed_cleared.emit()

    def update_destination_directory_display(self, folder_path: str):
        """대상 디렉토리 표시 업데이트 (alias for update_dest_directory_display)"""
        self.update_dest_directory_display(folder_path)
