"""
메인 윈도우 - AnimeSorter의 주요 GUI 인터페이스
사용자 친화적인 레이아웃과 직관적인 컨트롤을 제공합니다.
"""

import sys
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLineEdit, QLabel, QPushButton, QComboBox, QProgressBar, QTableView, QHeaderView,
    QGroupBox, QFormLayout, QFileDialog, QDialog, QDialogButtonBox, QCheckBox,
    QTabWidget, QTextEdit, QFrame, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QApplication, QListWidget, QListWidgetItem, QScrollArea, QGridLayout, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QAbstractTableModel, QModelIndex, QVariant, QSortFilterProxyModel, QThread, QDateTime
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QPixmap

# Local imports
from core.file_parser import FileParser, ParsedMetadata
from core.tmdb_client import TMDBClient, TMDBAnimeInfo
from core.settings_manager import SettingsManager
from core.file_manager import FileManager


# ----------------- Data Models -----------------
@dataclass
class ParsedItem:
    """파싱된 애니메이션 파일 정보"""
    id: str = None
    status: str = "pending"  # 'parsed' | 'needs_review' | 'error' | 'skipped'
    sourcePath: str = ""
    detectedTitle: str = ""
    filename: str = ""  # 파일명만
    path: str = ""      # 전체 경로
    title: str = ""     # 파싱된 제목
    season: Optional[int] = None
    episode: Optional[int] = None
    year: Optional[int] = None
    tmdbId: Optional[int] = None
    resolution: Optional[str] = None
    group: Optional[str] = None
    codec: Optional[str] = None
    container: Optional[str] = None
    sizeMB: Optional[int] = None
    message: Optional[str] = None
    tmdbMatch: Optional[TMDBAnimeInfo] = None  # TMDB 매치 결과
    parsingConfidence: Optional[float] = None   # 파싱 신뢰도
    groupId: Optional[str] = None  # 그룹 ID (동일 제목 파일들을 묶음)
    normalizedTitle: Optional[str] = None  # 정규화된 제목 (그룹화용)
    
    def __post_init__(self):
        """초기화 후 처리"""
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())[:8]
        if not self.filename and self.sourcePath:
            import os
            self.filename = os.path.basename(self.sourcePath)
        if not self.path and self.sourcePath:
            self.path = self.sourcePath
        if not self.title and self.detectedTitle:
            self.title = self.detectedTitle





# ----------------- Table Model -----------------
class ItemsTableModel(QAbstractTableModel):
    """파싱된 아이템을 테이블에 표시하는 모델"""
    headers = [
        "포스터", "제목(TMDB)", "대상 경로", "시즌", "에피소드", "년도", "해상도", "TMDB ID", "작업", "상태"
    ]

    def __init__(self, items: List[ParsedItem], tmdb_client=None):
        super().__init__()
        self.items = items
        self.tmdb_client = tmdb_client  # TMDB 클라이언트 직접 주입

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.items)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        item = self.items[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:  # 포스터
                if item.tmdbMatch and item.tmdbMatch.poster_path:
                    # 포스터 이미지 경로 반환 (이미지 표시용)
                    return item.tmdbMatch.poster_path
                elif item.status == "parsed":
                    return "✅"  # 파싱 완료
                elif item.status == "pending":
                    return "⏳"  # 대기중
                elif item.status == "error":
                    return "❌"  # 오류
                else:
                    return "❓"  # 알 수 없음
            elif col == 1:  # 제목(TMDB)
                if item.tmdbMatch:
                    return item.tmdbMatch.name
                return item.detectedTitle or "—"
            elif col == 2:  # 대상 경로
                return item.sourcePath or "—"
            elif col == 3:  # 시즌
                return item.season if item.season is not None else "-"
            elif col == 4:  # 에피소드
                return item.episode if item.episode is not None else "-"
            elif col == 5:  # 년도
                if item.tmdbMatch and item.tmdbMatch.first_air_date:
                    return item.tmdbMatch.first_air_date[:4]
                return item.year if item.year is not None else "-"
            elif col == 6:  # 해상도
                return item.resolution or "-"
            elif col == 7:  # TMDB ID
                return str(item.tmdbId) if item.tmdbId else "—"
            elif col == 8:  # 작업
                return "수정 / 삭제 / 상세보기"
            elif col == 9:  # 상태 (맨 뒤)
                status_map = {
                    'parsed': '✅ 완료',
                    'needs_review': '⚠️ 검토필요',
                    'error': '❌ 오류',
                    'skipped': '⏭️ 건너뛰기',
                    'pending': '⏳ 대기중'
                }
                return status_map.get(item.status, item.status)
        
        elif role == Qt.DecorationRole:
            if col == 0:  # 포스터 컬럼에 이미지 표시
                if item.tmdbMatch and item.tmdbMatch.poster_path and self.tmdb_client:
                    try:
                        poster_path = self.tmdb_client.get_poster_path(item.tmdbMatch.poster_path, 'w92')
                        
                        if poster_path and os.path.exists(poster_path):
                            pixmap = QPixmap(poster_path)
                            if not pixmap.isNull():
                                # 60x90 크기로 스케일링 (포스터 비율 유지)
                                scaled_pixmap = pixmap.scaled(60, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                return scaled_pixmap
                    except Exception as e:
                        print(f"포스터 로딩 오류: {e}")
                
                # 포스터가 없거나 로딩 실패 시 기본 아이콘
                if item.status == "parsed":
                    return QIcon("🎬")  # 기본 아이콘
                elif item.status == "pending":
                    return QIcon("⏳")
                elif item.status == "error":
                    return QIcon("❌")
                else:
                    return QIcon("❓")

        if role == Qt.TextAlignmentRole:
            if col in (0, 3, 4, 5, 6, 7, 9):  # 포스터, 시즌, 에피소드, 년도, 해상도, TMDB ID, 상태는 중앙 정렬
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter  # 제목, 경로, 작업은 왼쪽 정렬

        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return self.headers[section]
        return section + 1

    def setStatus(self, row: int, status: str):
        """아이템 상태 변경"""
        if 0 <= row < len(self.items):
            self.items[row].status = status
            # 상태 컬럼은 이제 9번째 (인덱스 9)
            self.dataChanged.emit(self.index(row, 9), self.index(row, 9), [Qt.DisplayRole])


# ----------------- Filter Proxy -----------------
class ItemsFilterProxy(QSortFilterProxyModel):
    """테이블 필터링 및 정렬을 위한 프록시 모델"""
    def __init__(self):
        super().__init__()
        self.query = ""
        self.status = "all"

    def setQuery(self, text: str):
        self.query = text.lower()
        self.invalidateFilter()

    def setStatus(self, status: str):
        self.status = status
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        model: ItemsTableModel = self.sourceModel()
        item = model.items[source_row]
        if self.status != "all" and item.status != self.status:
            return False
        if not self.query:
            return True
        hay = f"{item.sourcePath} {item.detectedTitle}".lower()
        return self.query in hay


# ----------------- Settings Dialog -----------------
class SettingsDialog(QDialog):
    """설정 다이얼로그"""
    settingsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.settings_manager = None
        
        # 부모 윈도우에서 설정 관리자 가져오기
        if hasattr(parent, 'settings_manager'):
            self.settings_manager = parent.settings_manager
        
        self.setWindowTitle("AnimeSorter 설정")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.init_ui()
        self.load_current_settings()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 탭 위젯 생성
        tab_widget = QTabWidget()
        
        # 파일 정리 탭
        file_org_tab = self.create_file_organization_tab()
        tab_widget.addTab(file_org_tab, "📁 파일 정리")
        
        # 파서 설정 탭
        parser_tab = self.create_parser_tab()
        tab_widget.addTab(parser_tab, "🔍 파서 설정")
        
        # TMDB 설정 탭
        tmdb_tab = self.create_tmdb_tab()
        tab_widget.addTab(tmdb_tab, "🎬 TMDB 설정")
        
        # UI 설정 탭
        ui_tab = self.create_ui_tab()
        tab_widget.addTab(ui_tab, "🎨 UI 설정")
        
        # 고급 설정 탭
        advanced_tab = self.create_advanced_tab()
        tab_widget.addTab(advanced_tab, "⚙️ 고급 설정")
        
        layout.addWidget(tab_widget)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        
        # 설정 내보내기/가져오기 버튼
        self.btnExport = QPushButton("📤 내보내기")
        self.btnExport.clicked.connect(self.export_settings)
        self.btnImport = QPushButton("📥 가져오기")
        self.btnImport.clicked.connect(self.import_settings)
        
        # 기본값 복원 버튼
        self.btnReset = QPushButton("🔄 기본값")
        self.btnReset.clicked.connect(self.reset_to_defaults)
        
        button_layout.addWidget(self.btnExport)
        button_layout.addWidget(self.btnImport)
        button_layout.addWidget(self.btnReset)
        button_layout.addStretch(1)
        
        # 저장/취소 버튼
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_apply_settings)
        buttons.rejected.connect(self.reject)
        
        button_layout.addWidget(buttons)
        layout.addLayout(button_layout)
        
    def create_file_organization_tab(self):
        """파일 정리 설정 탭"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        
        # 대상 디렉토리
        self.destination = QLineEdit()
        self.destination.setPlaceholderText("애니메이션 파일을 저장할 기본 디렉토리")
        self.btnBrowseDest = QPushButton("📂 찾아보기")
        self.btnBrowseDest.clicked.connect(self.browse_destination)
        
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(self.destination)
        dest_layout.addWidget(self.btnBrowseDest)
        layout.addRow("대상 디렉토리:", dest_layout)
        
        # 정리 모드
        self.organizeMode = QComboBox()
        self.organizeMode.addItems(["복사", "이동", "하드링크"])
        self.organizeMode.setToolTip("파일을 어떻게 처리할지 선택하세요")
        layout.addRow("정리 모드:", self.organizeMode)
        
        # 파일명 지정 방식
        self.namingScheme = QComboBox()
        self.namingScheme.addItems(["표준", "간소", "상세"])
        self.namingScheme.setToolTip("새 파일명을 어떻게 구성할지 선택하세요")
        layout.addRow("파일명 방식:", self.namingScheme)
        
        # 안전 모드
        self.safeMode = QCheckBox("안전 모드 (복사 후 원본 유지)")
        self.safeMode.setToolTip("체크하면 원본 파일을 보존합니다")
        layout.addRow("", self.safeMode)
        
        # 백업 설정
        self.backupBeforeOrganize = QCheckBox("정리 전 백업 생성")
        self.backupBeforeOrganize.setToolTip("파일 정리 전에 백업을 생성합니다")
        layout.addRow("", self.backupBeforeOrganize)
        
        return widget
        
    def create_parser_tab(self):
        """파서 설정 탭"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        
        # 파서 우선순위
        self.preferAnitopy = QCheckBox("Anitopy를 우선 사용")
        self.preferAnitopy.setToolTip("Anitopy 파서를 먼저 시도합니다")
        layout.addRow("", self.preferAnitopy)
        
        # 대안 파서
        self.fallback = QComboBox()
        self.fallback.addItems(["GuessIt", "Custom", "FileParser"])
        self.fallback.setToolTip("Anitopy 실패 시 사용할 대안 파서")
        layout.addRow("대안 파서:", self.fallback)
        
        # 실시간 감시
        self.realtime = QCheckBox("실시간 파일 감시")
        self.realtime.setToolTip("폴더 변경사항을 자동으로 감지합니다")
        layout.addRow("", self.realtime)
        
        # 자동 새로고침 간격
        self.autoRefreshInterval = QSpinBox()
        self.autoRefreshInterval.setRange(5, 300)
        self.autoRefreshInterval.setSuffix(" 초")
        self.autoRefreshInterval.setToolTip("UI 자동 새로고침 간격")
        layout.addRow("새로고침 간격:", self.autoRefreshInterval)
        
        return widget
        
    def create_tmdb_tab(self):
        """TMDB 설정 탭"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        
        # TMDB API 키
        self.tmdbKey = QLineEdit()
        self.tmdbKey.setPlaceholderText("TMDB API 키를 입력하세요")
        self.tmdbKey.setEchoMode(QLineEdit.Password)
        self.tmdbKey.setToolTip("TMDB에서 발급받은 API 키")
        layout.addRow("TMDB API 키:", self.tmdbKey)
        
        # 언어 설정
        self.tmdbLanguage = QComboBox()
        self.tmdbLanguage.addItems(["ko-KR", "en-US", "ja-JP"])
        self.tmdbLanguage.setToolTip("TMDB에서 가져올 메타데이터의 언어")
        layout.addRow("언어:", self.tmdbLanguage)
        
        # API 키 테스트 버튼
        self.btnTestTMDB = QPushButton("🔍 API 키 테스트")
        self.btnTestTMDB.clicked.connect(self.test_tmdb_api)
        layout.addRow("", self.btnTestTMDB)
        
        return widget
        
    def create_ui_tab(self):
        """UI 설정 탭"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        
        # 고급 옵션 표시
        self.showAdvancedOptions = QCheckBox("고급 옵션 표시")
        self.showAdvancedOptions.setToolTip("일반 사용자에게는 숨겨진 고급 설정을 표시합니다")
        layout.addRow("", self.showAdvancedOptions)
        
        # 테마 설정
        self.theme = QComboBox()
        self.theme.addItems(["시스템 기본", "밝은 테마", "어두운 테마"])
        self.theme.setToolTip("애플리케이션의 시각적 테마")
        layout.addRow("테마:", self.theme)
        
        # 로그 레벨
        self.logLevel = QComboBox()
        self.logLevel.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.logLevel.setToolTip("로그에 기록할 최소 레벨")
        layout.addRow("로그 레벨:", self.logLevel)
        
        # 파일 로깅
        self.logToFile = QCheckBox("로그를 파일에 저장")
        self.logToFile.setToolTip("로그를 파일에 저장합니다")
        layout.addRow("", self.logToFile)
        
        return widget
        
    def create_advanced_tab(self):
        """고급 설정 탭"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        
        # 백업 위치
        self.backupLocation = QLineEdit()
        self.backupLocation.setPlaceholderText("백업 파일을 저장할 위치")
        self.btnBrowseBackup = QPushButton("📂 찾아보기")
        self.btnBrowseBackup.clicked.connect(self.browse_backup_location)
        
        backup_layout = QHBoxLayout()
        backup_layout.addWidget(self.backupLocation)
        backup_layout.addWidget(self.btnBrowseBackup)
        layout.addRow("백업 위치:", backup_layout)
        
        # 최대 백업 수
        self.maxBackupCount = QSpinBox()
        self.maxBackupCount.setRange(1, 100)
        self.maxBackupCount.setToolTip("유지할 최대 백업 파일 수")
        layout.addRow("최대 백업 수:", self.maxBackupCount)
        
        # 설정 파일 경로 표시
        if self.settings_manager:
            config_path = self.settings_manager.settings_file
            config_label = QLabel(str(config_path))
            config_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
            layout.addRow("설정 파일:", config_label)
        
        return widget
        
    def load_current_settings(self):
        """현재 설정을 UI에 로드"""
        if not self.settings_manager:
            return
            
        settings = self.settings_manager.settings
        
        # 파일 정리 설정
        self.destination.setText(settings.destination_root)
        mode_map = {"복사": 0, "이동": 1, "하드링크": 2}
        self.organizeMode.setCurrentIndex(mode_map.get(settings.organize_mode, 0))
        
        scheme_map = {"standard": 0, "minimal": 1, "detailed": 2}
        self.namingScheme.setCurrentIndex(scheme_map.get(settings.naming_scheme, 0))
        
        self.safeMode.setChecked(settings.safe_mode)
        self.backupBeforeOrganize.setChecked(settings.backup_before_organize)
        
        # 파서 설정
        self.preferAnitopy.setChecked(settings.prefer_anitopy)
        fallback_map = {"GuessIt": 0, "Custom": 1, "FileParser": 2}
        self.fallback.setCurrentIndex(fallback_map.get(settings.fallback_parser, 0))
        
        self.realtime.setChecked(settings.realtime_monitoring)
        self.autoRefreshInterval.setValue(settings.auto_refresh_interval)
        
        # TMDB 설정
        self.tmdbKey.setText(settings.tmdb_api_key)
        language_map = {"ko-KR": 0, "en-US": 1, "ja-JP": 2}
        self.tmdbLanguage.setCurrentIndex(language_map.get(settings.tmdb_language, 0))
        
        # UI 설정
        self.showAdvancedOptions.setChecked(settings.show_advanced_options)
        self.theme.setCurrentIndex(0)  # 기본값
        log_level_map = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        self.logLevel.setCurrentIndex(log_level_map.get(settings.log_level, 1))
        self.logToFile.setChecked(settings.log_to_file)
        
        # 고급 설정
        self.backupLocation.setText(settings.backup_location)
        self.maxBackupCount.setValue(settings.max_backup_count)
        
    def save_and_apply_settings(self):
        """설정을 저장하고 적용"""
        if not self.settings_manager:
            QMessageBox.warning(self, "오류", "설정 관리자를 찾을 수 없습니다.")
            return
            
        try:
            # UI에서 설정 값 수집
            new_settings = {
                'destination_root': self.destination.text().strip(),
                'organize_mode': ["복사", "이동", "하드링크"][self.organizeMode.currentIndex()],
                'naming_scheme': ["standard", "minimal", "detailed"][self.namingScheme.currentIndex()],
                'safe_mode': self.safeMode.isChecked(),
                'backup_before_organize': self.backupBeforeOrganize.isChecked(),
                
                'prefer_anitopy': self.preferAnitopy.isChecked(),
                'fallback_parser': ["GuessIt", "Custom", "FileParser"][self.fallback.currentIndex()],
                'realtime_monitoring': self.realtime.isChecked(),
                'auto_refresh_interval': self.autoRefreshInterval.value(),
                
                'tmdb_api_key': self.tmdbKey.text().strip(),
                'tmdb_language': ["ko-KR", "en-US", "ja-JP"][self.tmdbLanguage.currentIndex()],
                
                'show_advanced_options': self.showAdvancedOptions.isChecked(),
                'log_level': ["DEBUG", "INFO", "WARNING", "ERROR"][self.logLevel.currentIndex()],
                'log_to_file': self.logToFile.isChecked(),
                
                'backup_location': self.backupLocation.text().strip(),
                'max_backup_count': self.maxBackupCount.value()
            }
            
            # 설정 유효성 검사
            errors = self.settings_manager.validate_settings()
            if errors:
                error_msg = "설정 오류가 발견되었습니다:\n\n"
                for field, error in errors.items():
                    error_msg += f"• {field}: {error}\n"
                QMessageBox.warning(self, "설정 오류", error_msg)
                return
            
            # 설정 업데이트
            if self.settings_manager.update_settings(new_settings):
                # 설정 파일에 저장
                if self.settings_manager.save_settings():
                    # 부모 윈도우에 설정 변경 알림
                    self.settingsChanged.emit()
                    
                    # 성공 메시지
                    QMessageBox.information(self, "설정 저장", "설정이 성공적으로 저장되었습니다.")
                    
                    # 부모 윈도우의 설정 적용
                    self.apply_settings_to_parent()
                    
                    self.accept()
                else:
                    QMessageBox.critical(self, "오류", "설정 저장에 실패했습니다.")
            else:
                QMessageBox.critical(self, "오류", "설정 업데이트에 실패했습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}")
    
    def apply_settings_to_parent(self):
        """부모 윈도우에 설정 적용"""
        if not self.parent_window:
            return
            
        try:
            # 대상 디렉토리 설정
            dest_root = self.destination.text().strip()
            if dest_root and hasattr(self.parent_window, 'file_manager'):
                self.parent_window.file_manager.set_destination_root(dest_root)
            
            # TMDB API 키 설정
            tmdb_key = self.tmdbKey.text().strip()
            if tmdb_key and hasattr(self.parent_window, 'tmdb_client'):
                # TMDB 클라이언트 재초기화
                self.parent_window.init_core_components()
            
            # 파일 관리자 설정
            if hasattr(self.parent_window, 'file_manager'):
                file_manager = self.parent_window.file_manager
                
                # 안전 모드 설정
                safe_mode = self.safeMode.isChecked()
                file_manager.set_safe_mode(safe_mode)
                
                # 이름 지정 방식 설정
                scheme_map = {0: "standard", 1: "minimal", 2: "detailed"}
                naming_scheme = scheme_map[self.namingScheme.currentIndex()]
                file_manager.set_naming_scheme(naming_scheme)
            
            # 상태바 업데이트
            if hasattr(self.parent_window, 'update_status_bar'):
                self.parent_window.update_status_bar("설정이 적용되었습니다")
                
        except Exception as e:
            print(f"설정 적용 중 오류: {e}")
    
    def browse_destination(self):
        """대상 디렉토리 찾아보기"""
        folder = QFileDialog.getExistingDirectory(
            self, "대상 디렉토리 선택", 
            self.destination.text()
        )
        if folder:
            self.destination.setText(folder)
    
    def browse_backup_location(self):
        """백업 위치 찾아보기"""
        folder = QFileDialog.getExistingDirectory(
            self, "백업 위치 선택", 
            self.backupLocation.text()
        )
        if folder:
            self.backupLocation.setText(folder)
    
    def test_tmdb_api(self):
        """TMDB API 키 테스트"""
        api_key = self.tmdbKey.text().strip()
        if not api_key:
            QMessageBox.warning(self, "경고", "먼저 TMDB API 키를 입력하세요.")
            return
            
        try:
            # 간단한 API 테스트
            import requests
            test_url = f"https://api.themoviedb.org/3/configuration?api_key={api_key}"
            response = requests.get(test_url, timeout=10)
            
            if response.status_code == 200:
                QMessageBox.information(self, "API 테스트 성공", "TMDB API 키가 유효합니다!")
            else:
                QMessageBox.warning(self, "API 테스트 실패", f"API 응답 오류: {response.status_code}")
                
        except Exception as e:
            QMessageBox.critical(self, "API 테스트 오류", f"API 테스트 중 오류가 발생했습니다:\n{str(e)}")
    
    def export_settings(self):
        """설정 내보내기"""
        if not self.settings_manager:
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "설정 내보내기", "animesorter_settings.json", 
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            if self.settings_manager.export_settings(filename):
                QMessageBox.information(self, "내보내기 완료", f"설정이 {filename}에 저장되었습니다.")
            else:
                QMessageBox.critical(self, "내보내기 실패", "설정 내보내기에 실패했습니다.")
    
    def import_settings(self):
        """설정 가져오기"""
        if not self.settings_manager:
            return
            
        filename, _ = QFileDialog.getOpenFileName(
            self, "설정 가져오기", "", 
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            if self.settings_manager.import_settings(filename):
                # UI에 가져온 설정 로드
                self.load_current_settings()
                QMessageBox.information(self, "가져오기 완료", f"{filename}에서 설정을 가져왔습니다.")
            else:
                QMessageBox.critical(self, "가져오기 실패", "설정 가져오기에 실패했습니다.")
    
    def reset_to_defaults(self):
        """설정을 기본값으로 초기화"""
        if not self.settings_manager:
            return
            
        reply = QMessageBox.question(
            self, "기본값 복원", 
            "모든 설정을 기본값으로 초기화하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.settings_manager.reset_to_defaults():
                # UI에 기본 설정 로드
                self.load_current_settings()
                QMessageBox.information(self, "초기화 완료", "설정이 기본값으로 초기화되었습니다.")
            else:
                QMessageBox.critical(self, "초기화 실패", "설정 초기화에 실패했습니다.")


# ----------------- Metadata Search Dialog -----------------
class MetadataSearchDialog(QDialog):
    """메타데이터 검색 결과 다이얼로그"""
    
    def __init__(self, parent=None, file_path="", parsed_metadata=None):
        super().__init__(parent)
        self.file_path = file_path
        self.parsed_metadata = parsed_metadata
        self.selected_result = None
        self.search_results = []  # 검색 결과 저장
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("메타데이터 검색 결과")
        self.setGeometry(400, 300, 800, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 파일 정보 표시
        file_info = QGroupBox("📁 파일 정보")
        file_layout = QFormLayout(file_info)
        
        self.lblFileName = QLabel(os.path.basename(self.file_path))
        self.lblFileName.setStyleSheet("font-weight: bold; color: #2c3e50;")
        file_layout.addRow("파일명:", self.lblFileName)
        
        if self.parsed_metadata:
            # title 속성 확인 (ParsedItem 또는 ParsedMetadata 모두 지원)
            title = getattr(self.parsed_metadata, 'title', None) or getattr(self.parsed_metadata, 'detectedTitle', '')
            self.lblParsedTitle = QLabel(title)
            self.lblParsedTitle.setStyleSheet("color: #27ae60;")
            file_layout.addRow("파싱된 제목:", self.lblParsedTitle)
            
            # season 속성 확인
            season = getattr(self.parsed_metadata, 'season', None)
            if season:
                self.lblSeason = QLabel(str(season))
                file_layout.addRow("시즌:", self.lblSeason)
                
            # episode 속성 확인
            episode = getattr(self.parsed_metadata, 'episode', None)
            if episode:
                self.lblEpisode = QLabel(str(episode))
                file_layout.addRow("에피소드:", self.lblEpisode)
                
            # resolution 속성 확인
            resolution = getattr(self.parsed_metadata, 'resolution', None)
            if resolution:
                self.lblResolution = QLabel(str(resolution))
                file_layout.addRow("해상도:", self.lblResolution)
                
            # confidence 또는 parsingConfidence 속성 확인
            confidence = getattr(self.parsed_metadata, 'confidence', None) or getattr(self.parsed_metadata, 'parsingConfidence', None)
            if confidence is not None:
                confidence_text = f"{confidence:.1%}"
                self.lblConfidence = QLabel(confidence_text)
                color = "#27ae60" if confidence >= 0.8 else "#f39c12" if confidence >= 0.5 else "#e74c3c"
                self.lblConfidence.setStyleSheet(f"color: {color}; font-weight: bold;")
                file_layout.addRow("파싱 신뢰도:", self.lblConfidence)
        
        layout.addWidget(file_info)
        
        # 검색 결과 표시
        results_group = QGroupBox("🔍 TMDB 검색 결과")
        results_layout = QVBoxLayout(results_group)
        
        # 검색 상태
        self.lblSearchStatus = QLabel("검색 중...")
        self.lblSearchStatus.setStyleSheet("color: #3498db; font-style: italic;")
        results_layout.addWidget(self.lblSearchStatus)
        
        # 검색 결과 리스트
        self.resultsList = QListWidget()
        self.resultsList.setAlternatingRowColors(True)
        self.resultsList.itemDoubleClicked.connect(self.on_result_selected)
        results_layout.addWidget(self.resultsList)
        
        # 수동 검색
        manual_search_layout = QHBoxLayout()
        self.txtManualSearch = QLineEdit()
        self.txtManualSearch.setPlaceholderText("수동으로 제목 입력...")
        self.txtManualSearch.returnPressed.connect(self.manual_search)
        
        # 파싱된 제목을 수동 검색 란에 미리 입력
        if self.parsed_metadata:
            title = getattr(self.parsed_metadata, 'title', None) or getattr(self.parsed_metadata, 'detectedTitle', '')
            if title:
                self.txtManualSearch.setText(title)
        
        self.btnManualSearch = QPushButton("🔍 검색")
        self.btnManualSearch.clicked.connect(self.manual_search)
        
        manual_search_layout.addWidget(self.txtManualSearch)
        manual_search_layout.addWidget(self.btnManualSearch)
        results_layout.addLayout(manual_search_layout)
        
        layout.addWidget(results_group)
        
        # 버튼
        button_layout = QHBoxLayout()
        self.btnSelect = QPushButton("✅ 선택")
        self.btnSelect.setEnabled(False)
        self.btnSelect.clicked.connect(self.accept)
        
        self.btnSkip = QPushButton("⏭️ 건너뛰기")
        self.btnSkip.clicked.connect(self.reject)
        
        self.btnRefresh = QPushButton("🔄 새로고침")
        self.btnRefresh.clicked.connect(self.refresh_search)
        
        button_layout.addWidget(self.btnSelect)
        button_layout.addWidget(self.btnSkip)
        button_layout.addWidget(self.btnRefresh)
        button_layout.addStretch(1)
        
        layout.addLayout(button_layout)
    
    def auto_select_single_result(self):
        """검색 결과가 1개일 때 자동 선택"""
        if len(self.search_results) == 1:
            # 자동으로 선택된 결과로 다이얼로그 종료
            self.selected_result = self.search_results[0]
            self.accept()
    
    def set_search_results(self, results: List[TMDBAnimeInfo]):
        """검색 결과 설정"""
        self.search_results = results  # 결과 저장
        self.resultsList.clear()
        
        if not results:
            self.lblSearchStatus.setText("검색 결과가 없습니다.")
            self.lblSearchStatus.setStyleSheet("color: #e74c3c; font-style: italic;")
            return
        
        # 검색 결과가 1개일 때 자동 선택
        if len(results) == 1:
            self.lblSearchStatus.setText("1개 결과를 찾았습니다. 자동으로 선택되었습니다.")
            self.lblSearchStatus.setStyleSheet("color: #27ae60; font-weight: bold;")
            
            # 첫 번째 결과를 자동 선택
            self.resultsList.addItem("자동 선택됨")
            self.resultsList.setCurrentRow(0)
            self.btnSelect.setEnabled(True)
            
            # 2초 후 자동으로 선택 (사용자가 취소할 수 있도록)
            QTimer.singleShot(2000, self.auto_select_single_result)
            return
        
        self.lblSearchStatus.setText(f"{len(results)}개 결과를 찾았습니다.")
        self.lblSearchStatus.setStyleSheet("color: #27ae60; font-weight: bold;")
        
        for i, anime in enumerate(results):
            item = QListWidgetItem()
            
            # 아이템 위젯 생성
            widget = self.create_result_widget(anime)
            item.setSizeHint(widget.sizeHint())
            
            self.resultsList.addItem(item)
            self.resultsList.setItemWidget(item, widget)
        
    def create_result_widget(self, anime: TMDBAnimeInfo) -> QWidget:
        """검색 결과 위젯 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 포스터 이미지 (나중에 구현)
        poster_label = QLabel("🎬")
        poster_label.setStyleSheet("font-size: 48px; color: #bdc3c7;")
        poster_label.setFixedSize(60, 90)
        layout.addWidget(poster_label)
        
        # 정보 레이아웃
        info_layout = QVBoxLayout()
        
        # 제목
        title_label = QLabel(anime.name)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        info_layout.addWidget(title_label)
        
        # 원제
        if anime.original_name and anime.original_name != anime.name:
            original_label = QLabel(f"원제: {anime.original_name}")
            original_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
            info_layout.addWidget(original_label)
        
        # 기본 정보
        basic_info = []
        if anime.first_air_date:
            basic_info.append(f"개봉: {anime.first_air_date}")
        if anime.number_of_seasons:
            basic_info.append(f"시즌: {anime.number_of_seasons}")
        if anime.number_of_episodes:
            basic_info.append(f"에피소드: {anime.number_of_episodes}")
        if anime.vote_average:
            basic_info.append(f"평점: {anime.vote_average}/10")
        
        if basic_info:
            info_text = " • ".join(basic_info)
            info_label = QLabel(info_text)
            info_label.setStyleSheet("font-size: 12px; color: #34495e;")
            info_layout.addWidget(info_label)
        
        # 개요
        if anime.overview:
            overview = anime.overview[:150] + "..." if len(anime.overview) > 150 else anime.overview
            overview_label = QLabel(overview)
            overview_label.setStyleSheet("font-size: 11px; color: #7f8c8d;")
            overview_label.setWordWrap(True)
            info_layout.addWidget(overview_label)
        
        layout.addLayout(info_layout)
        layout.addStretch(1)
        
        # 선택 표시
        select_label = QLabel("클릭하여 선택")
        select_label.setStyleSheet("font-size: 11px; color: #3498db; font-style: italic;")
        layout.addWidget(select_label)
        
        return widget
        
    def on_result_selected(self, item: QListWidgetItem):
        """검색 결과 선택"""
        row = self.resultsList.row(item)
        self.resultsList.setCurrentRow(row)
        self.btnSelect.setEnabled(True)
        
    def manual_search(self):
        """수동 검색"""
        query = self.txtManualSearch.text().strip()
        if not query:
            return
            
        # 부모 윈도우의 TMDB 클라이언트를 사용하여 검색
        if hasattr(self.parent(), 'tmdb_client'):
            results = self.parent().tmdb_client.search_anime(query)
            self.set_search_results(results)
        
    def refresh_search(self):
        """검색 새로고침"""
        if self.parsed_metadata and hasattr(self.parent(), 'tmdb_client'):
            title = getattr(self.parsed_metadata, 'title', None) or getattr(self.parsed_metadata, 'detectedTitle', '')
            if title:
                results = self.parent().tmdb_client.search_anime(title)
                self.set_search_results(results)
    
    def get_selected_result(self) -> Optional[TMDBAnimeInfo]:
        """선택된 결과 반환"""
        current_row = self.resultsList.currentRow()
        if current_row >= 0 and current_row < len(self.search_results):
            return self.search_results[current_row]
        return None


# ----------------- Main Window -----------------
class MainWindow(QMainWindow):
    """AnimeSorter 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        # 핵심 컴포넌트 초기화
        self.init_core_components()
        
        # 초기 데이터 설정 (UI 초기화 전에 필요)
        self.initialize_data()
        
        # UI 초기화
        self.init_ui()
        self.setup_connections()
        
        # 이전 세션 상태 복원
        self.restore_session_state()
        
    def init_core_components(self):
        """핵심 컴포넌트 초기화"""
        try:
            # 설정 관리자 초기화
            self.settings_manager = SettingsManager()
            
            # FileParser 초기화
            self.file_parser = FileParser()
            
            # TMDBClient 초기화 (설정에서 API 키 가져오기)
            api_key = self.settings_manager.get_setting('tmdb_api_key') or os.getenv('TMDB_API_KEY')
            if api_key:
                self.tmdb_client = TMDBClient(api_key=api_key)
                print("✅ TMDBClient 초기화 성공")
                
                # 포스터 캐시 초기화
                self.poster_cache = {}  # 포스터 이미지 캐시
            else:
                print("⚠️ TMDB_API_KEY가 설정되지 않았습니다.")
                print("   설정에서 TMDB API 키를 입력하거나 환경 변수를 설정하세요.")
                self.tmdb_client = None
            
            # FileManager 초기화
            dest_root = self.settings_manager.get_setting('destination_root', '')
            safe_mode = self.settings_manager.get_setting('safe_mode', True)
            self.file_manager = FileManager(destination_root=dest_root, safe_mode=safe_mode)
            
            # FileManager 설정 적용
            naming_scheme = self.settings_manager.get_setting('naming_scheme', 'standard')
            self.file_manager.set_naming_scheme(naming_scheme)
            
            print("✅ 핵심 컴포넌트 초기화 완료")
                
        except Exception as e:
            print(f"❌ 핵심 컴포넌트 초기화 실패: {e}")
            self.file_parser = None
            self.tmdb_client = None
            self.file_manager = None
    
    def restore_session_state(self):
        """이전 세션 상태 복원"""
        try:
            if not self.settings_manager:
                return
                
            settings = self.settings_manager.settings
            
            # 마지막으로 선택한 디렉토리들 복원
            if settings.remember_last_session:
                if settings.last_source_directory and os.path.exists(settings.last_source_directory):
                    self.source_directory = settings.last_source_directory
                    self.update_source_directory_display()
                
                if settings.last_destination_directory and os.path.exists(settings.last_destination_directory):
                    self.destination_directory = settings.last_destination_directory
                    self.update_destination_directory_display()
                
                # 마지막으로 선택한 파일들 복원
                if settings.last_source_files:
                    self.source_files = [f for f in settings.last_source_files if os.path.exists(f)]
                    if self.source_files:
                        self.update_source_files_display()
            
            # 스캔 시작 버튼 활성화 상태 업데이트
            self.update_scan_button_state()
            
            # 윈도우 상태 복원
            if settings.window_geometry:
                try:
                    geometry = [int(x) for x in settings.window_geometry.split(',')]
                    if len(geometry) == 4:
                        self.setGeometry(*geometry)
                except:
                    pass
            
            # 테이블 컬럼 너비 복원
            if settings.table_column_widths:
                self.restore_table_column_widths(settings.table_column_widths)
            
            print("✅ 세션 상태 복원 완료")
                
        except Exception as e:
            print(f"⚠️ 세션 상태 복원 실패: {e}")
    
    def save_session_state(self):
        """현재 세션 상태 저장"""
        try:
            if not self.settings_manager:
                return
                
            settings = self.settings_manager.settings
            
            # 현재 디렉토리들 저장
            if self.source_directory:
                settings.last_source_directory = self.source_directory
            
            if self.destination_directory:
                settings.last_destination_directory = self.destination_directory
            
            # 현재 선택된 파일들 저장
            if self.source_files:
                settings.last_source_files = self.source_files[:]  # 복사본 저장
            
            # 윈도우 상태 저장
            geometry = self.geometry()
            settings.window_geometry = f"{geometry.x()},{geometry.y()},{geometry.width()},{geometry.height()}"
            
            # 테이블 컬럼 너비 저장
            settings.table_column_widths = self.get_table_column_widths()
            
            # 설정 파일에 저장
            self.settings_manager.save_settings()
            print("✅ 세션 상태 저장 완료")
                
        except Exception as e:
            print(f"⚠️ 세션 상태 저장 실패: {e}")
    
    def get_table_column_widths(self) -> Dict[str, int]:
        """테이블 컬럼 너비 가져오기"""
        widths = {}
        try:
            if hasattr(self, 'itemsTable') and self.itemsTable:
                header = self.itemsTable.horizontalHeader()
                for i in range(header.count()):
                    column_name = self.itemsTable.model().headerData(i, Qt.Horizontal)
                    if column_name:
                        widths[str(column_name)] = header.sectionSize(i)
        except Exception as e:
            print(f"⚠️ 컬럼 너비 가져오기 실패: {e}")
        return widths
    
    def restore_table_column_widths(self, widths: Dict[str, int]):
        """테이블 컬럼 너비 복원"""
        try:
            if hasattr(self, 'itemsTable') and self.itemsTable and widths:
                header = self.itemsTable.horizontalHeader()
                for i in range(header.count()):
                    column_name = self.itemsTable.model().headerData(i, Qt.Horizontal)
                    if column_name and str(column_name) in widths:
                        header.resizeSection(i, widths[str(column_name)])
        except Exception as e:
            print(f"⚠️ 컬럼 너비 복원 실패: {e}")
    
    def update_source_directory_display(self):
        """소스 디렉토리 표시 업데이트"""
        if hasattr(self, 'source_dir_label') and self.source_directory:
            self.source_dir_label.setText(f"소스 폴더: {self.source_directory}")
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
    
    def update_destination_directory_display(self):
        """대상 디렉토리 표시 업데이트"""
        if hasattr(self, 'dest_dir_label') and self.destination_directory:
            self.dest_dir_label.setText(f"대상 폴더: {self.destination_directory}")
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
    
    def update_source_files_display(self):
        """소스 파일들 표시 업데이트"""
        if hasattr(self, 'source_dir_label') and self.source_files:
            self.source_dir_label.setText(f"선택된 파일: {len(self.source_files)}개")
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
    
    def update_scan_button_state(self):
        """스캔 시작 버튼 활성화 상태 업데이트"""
        if hasattr(self, 'btnStart'):
            # 소스 디렉토리나 파일이 선택되어 있으면 버튼 활성화
            has_source = (self.source_directory and os.path.exists(self.source_directory)) or \
                        (self.source_files and len(self.source_files) > 0)
            
            self.btnStart.setEnabled(has_source)
            
            if has_source:
                if self.source_directory:
                    self.update_status_bar(f"스캔 준비 완료: {self.source_directory}")
                elif self.source_files:
                    self.update_status_bar(f"스캔 준비 완료: {len(self.source_files)}개 파일")
            else:
                self.update_status_bar("소스 디렉토리나 파일을 선택해주세요")
    
    def normalize_title_for_grouping(self, title: str) -> str:
        """제목을 그룹화용으로 정규화"""
        if not title:
            return ""
        
        # 소문자로 변환
        normalized = title.lower()
        
        # 특수문자 및 공백 제거
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # 일반적인 애니메이션 제목 패턴 정리
        patterns_to_remove = [
            r'\bthe\b', r'\banimation\b', r'\banime\b', r'\btv\b', r'\bseries\b',
            r'\bseason\b', r'\bepisode\b', r'\bep\b', r'\bova\b', r'\bmovie\b'
        ]
        
        for pattern in patterns_to_remove:
            normalized = re.sub(pattern, '', normalized)
        
        # 앞뒤 공백 제거
        normalized = normalized.strip()
        
        return normalized
    
    def group_similar_titles(self, parsed_items: List[ParsedItem]) -> List[ParsedItem]:
        """유사한 제목을 가진 파일들을 그룹화"""
        if not parsed_items:
            return parsed_items
        
        # 제목 정규화 및 그룹 ID 할당
        title_groups = {}  # 정규화된 제목 -> 그룹 ID 매핑
        group_counter = 1
        
        for item in parsed_items:
            if not item.title:
                continue
            
            # 제목 정규화
            normalized_title = self.normalize_title_for_grouping(item.title)
            item.normalizedTitle = normalized_title
            
            # 유사한 제목이 있는지 확인 (Levenshtein 거리 기반)
            best_match = None
            best_similarity = 0.8  # 최소 유사도 임계값
            
            for existing_title, group_id in title_groups.items():
                similarity = self.calculate_title_similarity(normalized_title, existing_title)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = existing_title
            
            if best_match:
                # 기존 그룹에 추가
                item.groupId = title_groups[best_match]
                print(f"🔗 그룹화: '{item.title}' → 그룹 {item.groupId} (유사도: {best_similarity:.2f})")
            else:
                # 새 그룹 생성
                new_group_id = f"group_{group_counter:03d}"
                item.groupId = new_group_id
                title_groups[normalized_title] = new_group_id
                group_counter += 1
                print(f"🆕 새 그룹 생성: '{item.title}' → 그룹 {new_group_id}")
        
        return parsed_items
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """두 제목 간의 유사도 계산 (0.0 ~ 1.0)"""
        if not title1 or not title2:
            return 0.0
        
        # 간단한 유사도 계산 (공통 단어 기반)
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard 유사도
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
        
        jaccard_similarity = intersection / union
        
        # 추가 가중치: 제목 길이 유사성
        length_diff = abs(len(title1) - len(title2))
        max_length = max(len(title1), len(title2))
        length_similarity = 1.0 - (length_diff / max_length) if max_length > 0 else 0.0
        
        # 최종 유사도 (Jaccard 70%, 길이 30%)
        final_similarity = (jaccard_similarity * 0.7) + (length_similarity * 0.3)
        
        return final_similarity
    
    def display_grouped_results(self, parsed_items: List[ParsedItem]):
        """그룹화된 결과를 GUI에 표시"""
        if not parsed_items:
            return
        
        # 그룹별로 정리
        groups = {}
        for item in parsed_items:
            group_id = item.groupId or "ungrouped"
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(item)
        
        # 그룹 정보 출력
        print(f"\n📊 그룹화 결과:")
        print(f"총 {len(parsed_items)}개 파일이 {len(groups)}개 그룹으로 분류되었습니다.")
        
        for group_id, items in groups.items():
            if group_id == "ungrouped":
                print(f"\n❓ 미분류 그룹:")
            else:
                print(f"\n🔗 그룹 {group_id}:")
            
            for item in items:
                episode_info = f"E{item.episode:02d}" if item.episode else "Unknown"
                status_icon = "✅" if item.status == "parsed" else "⚠️" if item.status == "needs_review" else "❌"
                print(f"  {status_icon} {item.title} {episode_info} ({item.status})")
        
        # 상태바 업데이트
        total_groups = len([g for g in groups.keys() if g != "ungrouped"])
        self.update_status_bar(f"그룹화 완료: {len(parsed_items)}개 파일 → {total_groups}개 그룹")
    
    def process_tmdb_search_by_groups(self, parsed_items: List[ParsedItem]):
        """그룹별로 TMDB 검색 수행 (중복 제거)"""
        if not parsed_items:
            return
        
        # 그룹별로 정리
        groups = {}
        for item in parsed_items:
            group_id = item.groupId or "ungrouped"
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(item)
        
        # 각 그룹별로 한 번만 TMDB 검색
        for group_id, items in groups.items():
            if group_id == "ungrouped":
                continue
            
            # 그룹의 대표 제목 선택 (첫 번째 항목 사용)
            representative_item = items[0]
            representative_title = representative_item.title
            
            print(f"\n🔍 그룹 {group_id} TMDB 검색: '{representative_title}'")
            
            # TMDB 검색 수행
            search_results = self.tmdb_client.search_anime(representative_title)
            print(f"📊 검색 결과: {len(search_results)}개")
            
            if search_results:
                # 검색 결과가 1개일 때는 자동 선택
                if len(search_results) == 1:
                    selected_result = search_results[0]
                    print(f"✅ 자동 선택: {selected_result.name}")
                    
                    # 그룹의 모든 항목에 동일한 TMDB 결과 적용
                    for item in items:
                        item.tmdbMatch = selected_result
                        item.tmdbId = selected_result.id  # TMDB ID 설정
                        item.status = "parsed"
                        print(f"  🔗 {item.title} E{item.episode:02d} → {selected_result.name}")
                        
                        # 활동 로그 업데이트
                        log_message = f"🔗 {os.path.basename(item.sourcePath)} → {selected_result.name} (자동 선택)"
                        self.add_activity_log(log_message)
                    
                else:
                    # 검색 결과가 여러 개일 때는 사용자 선택
                    print(f"⚠️ 여러 결과 발견, 사용자 선택 필요")
                    dialog = MetadataSearchDialog(self, representative_item.sourcePath, representative_item)
                    dialog.set_search_results(search_results)
                    
                    if dialog.exec_() == QDialog.Accepted:
                        selected_result = dialog.get_selected_result()
                        if selected_result:
                            print(f"✅ 사용자 선택: {selected_result.name}")
                            
                            # 그룹의 모든 항목에 동일한 TMDB 결과 적용
                            for item in items:
                                item.tmdbMatch = selected_result
                                item.tmdbId = selected_result.id  # TMDB ID 설정
                                item.status = "parsed"
                                print(f"  🔗 {item.title} E{item.episode:02d} → {selected_result.name}")
                                
                                # 활동 로그 업데이트
                                log_message = f"🔗 {os.path.basename(item.sourcePath)} → {selected_result.name} (사용자 선택)"
                                self.add_activity_log(log_message)
                        else:
                            print(f"❌ 사용자가 선택하지 않음")
                            for item in items:
                                item.status = "needs_review"
                    else:
                        print(f"⏭️ 사용자가 건너뛰기")
                        for item in items:
                            item.status = "skipped"
            else:
                # 검색 결과가 없을 때도 수동 검색 시도
                print(f"❌ 검색 결과 없음, 수동 검색 시도")
                dialog = MetadataSearchDialog(self, representative_item.sourcePath, representative_item)
                dialog.set_search_results([])  # 빈 결과로 다이얼로그 표시
                
                if dialog.exec_() == QDialog.Accepted:
                    selected_result = dialog.get_selected_result()
                    if selected_result:
                        print(f"✅ 수동 검색으로 선택: {selected_result.name}")
                        
                        # 그룹의 모든 항목에 동일한 TMDB 결과 적용
                        for item in items:
                            item.tmdbMatch = selected_result
                            item.tmdbId = selected_result.id  # TMDB ID 설정
                            item.status = "parsed"
                            print(f"  🔗 {item.title} E{item.episode:02d} → {selected_result.name}")
                            
                            # 활동 로그 업데이트
                            log_message = f"🔗 {os.path.basename(item.sourcePath)} → {selected_result.name} (수동 검색)"
                            self.add_activity_log(log_message)
                    else:
                        print(f"❌ 수동 검색에서도 선택하지 않음")
                        for item in items:
                            item.status = "needs_review"
                            
                            # 활동 로그 업데이트
                            log_message = f"❌ {os.path.basename(item.sourcePath)} - 수동 검색에서 선택하지 않음"
                            self.add_activity_log(log_message)
                else:
                    print(f"⏭️ 수동 검색 다이얼로그 취소")
                    for item in items:
                        item.status = "skipped"
                        
                        # 활동 로그 업데이트
                        log_message = f"⏭️ {os.path.basename(item.sourcePath)} - 수동 검색 건너뛰기"
                        self.add_activity_log(log_message)
        
        print(f"\n✅ 그룹별 TMDB 검색 완료")
        
        # 테이블 모델 업데이트 강제
        if hasattr(self, 'model') and self.model:
            self.model.dataChanged.emit(
                self.model.index(0, 0), 
                self.model.index(self.model.rowCount()-1, self.model.columnCount()-1)
            )
        
    def init_ui(self):
        """사용자 인터페이스 초기화"""
        # 윈도우 기본 설정
        self.setWindowTitle("AnimeSorter v2.0.0 - 애니메이션 파일 정리 도구")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1000, 700)
        
        # 애플리케이션 아이콘 설정
        self.setWindowIcon(QIcon("🎬"))
        
        # 메뉴바 생성
        self.create_menu_bar()
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        
        # 상단 툴바 영역
        self.create_toolbar(main_layout)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        main_layout.addWidget(line)
        
        # 메인 콘텐츠 영역 (스플리터)
        self.create_main_content(main_layout)
        
        # 상태바 생성
        self.create_status_bar()
    
    def closeEvent(self, event):
        """프로그램 종료 시 이벤트 처리"""
        try:
            # 현재 세션 상태 저장
            self.save_session_state()
            print("✅ 프로그램 종료 시 설정 저장 완료")
        except Exception as e:
            print(f"⚠️ 프로그램 종료 시 설정 저장 실패: {e}")
        
        # 기본 종료 처리
        super().closeEvent(event)
        
    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일(&F)")
        
        # 파일 선택 액션
        open_files_action = file_menu.addAction("파일 선택(&O)")
        open_files_action.setShortcut("Ctrl+O")
        open_files_action.setStatusTip("애니메이션 파일을 선택합니다")
        open_files_action.triggered.connect(self.choose_files)
        
        open_folder_action = file_menu.addAction("폴더 선택(&F)")
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.setStatusTip("애니메이션 파일이 있는 폴더를 선택합니다")
        open_folder_action.triggered.connect(self.choose_folder)
        
        file_menu.addSeparator()
        
        # 내보내기 액션
        export_action = file_menu.addAction("결과 내보내기(&E)")
        export_action.setShortcut("Ctrl+E")
        export_action.setStatusTip("스캔 결과를 CSV 파일로 내보냅니다")
        export_action.triggered.connect(self.export_results)
        
        file_menu.addSeparator()
        
        # 종료 액션
        exit_action = file_menu.addAction("종료(&X)")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("애플리케이션을 종료합니다")
        exit_action.triggered.connect(self.close)
        
        # 편집 메뉴
        edit_menu = menubar.addMenu("편집(&E)")
        
        # 설정 액션
        settings_action = edit_menu.addAction("설정(&S)")
        settings_action.setShortcut("Ctrl+,")
        settings_action.setStatusTip("애플리케이션 설정을 변경합니다")
        settings_action.triggered.connect(self.open_settings)
        
        edit_menu.addSeparator()
        
        # 필터 초기화 액션
        reset_filters_action = edit_menu.addAction("필터 초기화(&R)")
        reset_filters_action.setShortcut("Ctrl+R")
        reset_filters_action.setStatusTip("모든 필터를 초기화합니다")
        reset_filters_action.triggered.connect(self.reset_filters)
        
        # 도구 메뉴
        tools_menu = menubar.addMenu("도구(&T)")
        
        # 스캔 시작/중지 액션
        start_scan_action = tools_menu.addAction("스캔 시작(&S)")
        start_scan_action.setShortcut("F5")
        start_scan_action.setStatusTip("파일 스캔을 시작합니다")
        start_scan_action.triggered.connect(self.start_scan)
        
        stop_scan_action = tools_menu.addAction("스캔 중지(&P)")
        stop_scan_action.setShortcut("F6")
        stop_scan_action.setStatusTip("파일 스캔을 중지합니다")
        stop_scan_action.triggered.connect(self.stop_scan)
        
        tools_menu.addSeparator()
        
        # 정리 실행 액션
        commit_action = tools_menu.addAction("정리 실행(&C)")
        commit_action.setShortcut("F7")
        commit_action.setStatusTip("파일 정리를 실행합니다")
        commit_action.triggered.connect(self.commit_organization)
        
        # 시뮬레이션 액션
        simulate_action = tools_menu.addAction("시뮬레이션(&M)")
        simulate_action.setShortcut("F8")
        simulate_action.setStatusTip("파일 정리를 시뮬레이션합니다")
        simulate_action.triggered.connect(self.simulate_organization)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말(&H)")
        
        # 정보 액션
        about_action = help_menu.addAction("정보(&A)")
        about_action.setStatusTip("AnimeSorter에 대한 정보를 표시합니다")
        about_action.triggered.connect(self.show_about)
        
        # 사용법 액션
        help_action = help_menu.addAction("사용법(&H)")
        help_action.setShortcut("F1")
        help_action.setStatusTip("사용법을 표시합니다")
        help_action.triggered.connect(self.show_help)
        
    def create_toolbar(self, parent_layout):
        """상단 툴바 생성"""
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        
        # 앱 제목
        title_label = QLabel("🎬 AnimeSorter")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50;")
        toolbar_layout.addWidget(title_label)
        
        toolbar_layout.addStretch(1)
        
        # 검색 및 필터
        search_label = QLabel("🔍 검색:")
        self.search = QLineEdit()
        self.search.setPlaceholderText("제목, 경로로 검색...")
        self.search.setMinimumWidth(250)
        
        status_label = QLabel("상태:")
        self.statusFilter = QComboBox()
        self.statusFilter.addItems(["전체", "parsed", "needs_review", "error"])
        
        # 설정 버튼
        self.btnSettings = QPushButton("⚙️ 설정")
        self.btnSettings.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        toolbar_layout.addWidget(search_label)
        toolbar_layout.addWidget(self.search)
        toolbar_layout.addWidget(status_label)
        toolbar_layout.addWidget(self.statusFilter)
        toolbar_layout.addWidget(self.btnSettings)
        
        parent_layout.addWidget(toolbar)
        
    def create_main_content(self, parent_layout):
        """메인 콘텐츠 영역 생성"""
        # 스플리터를 사용하여 좌우 분할
        splitter = QSplitter(Qt.Horizontal)
        
        # 왼쪽 패널: 컨트롤 및 통계
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 오른쪽 패널: 결과 및 로그
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # 스플리터 비율 설정
        splitter.setSizes([400, 1000])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        parent_layout.addWidget(splitter)
        
    def create_left_panel(self):
        """왼쪽 패널 생성"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)
        
        # 빠른 작업 그룹
        quick_actions = self.create_quick_actions_group()
        left_layout.addWidget(quick_actions)
        
        # 통계 그룹
        stats_group = self.create_stats_group()
        left_layout.addWidget(stats_group)
        
        # 필터 그룹
        filter_group = self.create_filter_group()
        left_layout.addWidget(filter_group)
        
        left_layout.addStretch(1)
        return left_widget
        
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
        
        # 완료된 항목 정리 버튼
        self.btnClearCompleted = QPushButton("✅ 완료된 항목 정리")
        self.btnClearCompleted.setStyleSheet(self.get_button_style("#95a5a6"))
        
        layout.addRow("전체:", self.lblTotal)
        layout.addRow("완료:", self.lblParsed)
        layout.addRow("대기:", self.lblPending)
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
        
    def create_right_panel(self):
        """오른쪽 패널 생성"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)
        
        # 결과 헤더
        results_header = self.create_results_header()
        right_layout.addWidget(results_header)
        
        # 뷰 탭 (테이블/트리)
        self.viewTabs = self.create_view_tabs()
        right_layout.addWidget(self.viewTabs, 1)
        
        # 하단 액션
        bottom_actions = self.create_bottom_actions()
        right_layout.addWidget(bottom_actions)
        
        # 로그 탭
        log_tabs = self.create_log_tabs()
        right_layout.addWidget(log_tabs)
        
        # 수동 매칭
        manual_match = self.create_manual_match_group()
        right_layout.addWidget(manual_match)
        
        return right_widget
        
    def create_results_header(self):
        """결과 헤더 생성"""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("📋 스캔 결과")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        layout.addWidget(title_label)
        layout.addStretch(1)
        
        # 스마트 필터 및 벌크 액션 버튼
        self.btnSmartFilter = QPushButton("🧠 스마트 필터")
        self.btnSmartFilter.setStyleSheet(self.get_button_style("#9b59b6"))
        
        self.btnBulk = QPushButton("📦 일괄 작업...")
        self.btnBulk.setStyleSheet(self.get_button_style("#e67e22"))
        
        layout.addWidget(self.btnSmartFilter)
        layout.addWidget(self.btnBulk)
        
        return header
        
    def create_view_tabs(self):
        """뷰 탭 생성"""
        tab_widget = QTabWidget()
        
        # 테이블 뷰
        self.model = ItemsTableModel([], self.tmdb_client)  # TMDB 클라이언트 전달
        self.proxy = ItemsFilterProxy()
        self.proxy.setSourceModel(self.model)
        
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        # 포스터 컬럼 너비 고정 (이미지 표시용)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 100)  # 포스터 컬럼 너비 (이미지 + 여백)
        
        # 나머지 컬럼은 자동 크기 조정
        for i in range(1, self.model.columnCount()):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # 트리 뷰 (시즌/에피소드 그룹화)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["제목 / 시즌 / 에피소드", "파일 수", "최고 해상도"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 320)
        
        tab_widget.addTab(self.table, "📊 테이블 보기")
        tab_widget.addTab(self.tree, "🌳 시즌별 보기")
        
        return tab_widget
        
    def create_bottom_actions(self):
        """하단 액션 생성"""
        bottom = QWidget()
        layout = QHBoxLayout(bottom)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 표시 정보
        self.lblShowing = QLabel("")
        layout.addWidget(self.lblShowing)
        layout.addStretch(1)
        
        # 커밋 및 시뮬레이션 버튼
        self.btnCommit = QPushButton("💾 정리 실행")
        self.btnCommit.setStyleSheet(self.get_button_style("#e74c3c"))
        
        self.btnSimulate = QPushButton("🎭 시뮬레이션")
        self.btnSimulate.setStyleSheet(self.get_button_style("#3498db"))
        
        layout.addWidget(self.btnCommit)
        layout.addWidget(self.btnSimulate)
        
        return bottom
        
    def create_log_tabs(self):
        """로그 탭 생성"""
        tab_widget = QTabWidget()
        
        # 활동 로그
        self.txtLog = QTextEdit()
        self.txtLog.setReadOnly(True)
        self.txtLog.setMaximumHeight(120)
        self.txtLog.setText("""[12:00:01] /downloads 폴더 감시 중...
[12:00:04] Frieren S01E01 파싱 완료 (점수=0.92, tmdb=209867)
[12:00:08] 스페셜 에피소드 발견; 검토 대기 중
[12:00:17] 1개 항목 정리 준비 완료 (복사 모드)""")
        
        # 오류 로그
        self.txtErr = QTextEdit()
        self.txtErr.setReadOnly(True)
        self.txtErr.setMaximumHeight(120)
        self.txtErr.setText("""[12:01:12] Unknown.Show.12v2.mp4 TMDB 매칭 실패 — 별칭으로 수동 검색을 시도해주세요.""")
        
        tab_widget.addTab(self.txtLog, "📝 활동 로그")
        tab_widget.addTab(self.txtErr, "⚠️ 오류 로그")
        
        return tab_widget
        
    def export_results(self):
        """결과 내보내기"""
        from PyQt5.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self, "결과 내보내기", "animesorter_results.csv", 
            "CSV Files (*.csv);;All Files (*)"
        )
        if filename:
            try:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['상태', '제목', '시즌', '에피소드', '년도', '해상도', '크기', 'TMDB ID', '경로']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for item in self.items:
                        writer.writerow({
                            '상태': item.status,
                            '제목': item.detectedTitle,
                            '시즌': item.season or '',
                            '에피소드': item.episode or '',
                            '년도': item.year or '',
                            '해상도': item.resolution or '',
                            '크기': f"{item.sizeMB}MB" if item.sizeMB else '',
                            'TMDB ID': item.tmdbId or '',
                            '경로': item.sourcePath
                        })
                
                self.update_status_bar(f"결과가 {filename}에 저장되었습니다")
                QMessageBox.information(self, "내보내기 완료", f"결과가 성공적으로 저장되었습니다:\n{filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "내보내기 오류", f"파일 저장 중 오류가 발생했습니다:\n{str(e)}")
                
    def show_about(self):
        """정보 다이얼로그 표시"""
        QMessageBox.about(self, "AnimeSorter 정보", 
            """<h2>AnimeSorter v2.0.0</h2>
            <p><b>애니메이션 파일 정리 도구</b></p>
            <p>PyQt5 기반의 사용자 친화적인 GUI로 애니메이션 파일을 자동으로 정리하고 
            TMDB API를 통해 메타데이터를 가져와 체계적으로 관리합니다.</p>
            <p><b>주요 기능:</b></p>
            <ul>
                <li>파일명 자동 파싱</li>
                <li>TMDB 메타데이터 검색</li>
                <li>자동 파일 정리</li>
                <li>배치 처리</li>
                <li>안전 모드 및 백업</li>
            </ul>
            <p><b>개발:</b> AnimeSorter 개발팀</p>
            <p><b>라이선스:</b> MIT License</p>""")
            
    def show_help(self):
        """사용법 다이얼로그 표시"""
        help_text = """
        <h2>AnimeSorter 사용법</h2>
        
        <h3>1. 파일 선택</h3>
        <p>• <b>파일 선택</b>: 개별 애니메이션 파일들을 선택합니다 (Ctrl+O)</p>
        <p>• <b>폴더 선택</b>: 애니메이션 파일이 있는 폴더를 선택합니다 (Ctrl+Shift+O)</p>
        
        <h3>2. 스캔 및 파싱</h3>
        <p>• <b>스캔 시작</b>: 선택된 파일들을 분석하고 파싱합니다 (F5)</p>
        <p>• <b>스캔 중지</b>: 진행 중인 스캔을 중지합니다 (F6)</p>
        
        <h3>3. 메타데이터 매칭</h3>
        <p>• 자동으로 TMDB에서 애니메이션 정보를 검색합니다</p>
        <p>• 매칭되지 않은 항목은 수동으로 검색할 수 있습니다</p>
        
        <h3>4. 파일 정리</h3>
        <p>• <b>시뮬레이션</b>: 파일 이동을 미리 확인합니다 (F8)</p>
        <p>• <b>정리 실행</b>: 실제로 파일을 정리합니다 (F7)</p>
        
        <h3>5. 필터링 및 검색</h3>
        <p>• 상태, 해상도, 코덱 등으로 결과를 필터링할 수 있습니다</p>
        <p>• 제목이나 경로로 검색할 수 있습니다</p>
        
        <h3>단축키</h3>
        <p>• Ctrl+O: 파일 선택</p>
        <p>• Ctrl+Shift+O: 폴더 선택</p>
        <p>• F5: 스캔 시작</p>
        <p>• F6: 스캔 중지</p>
        <p>• F7: 정리 실행</p>
        <p>• F8: 시뮬레이션</p>
        <p>• Ctrl+R: 필터 초기화</p>
        <p>• Ctrl+E: 결과 내보내기</p>
        <p>• Ctrl+,: 설정</p>
        <p>• F1: 도움말</p>
        """
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("사용법")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(help_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
    def create_manual_match_group(self):
        """수동 매칭 그룹 생성"""
        group = QGroupBox("🔗 수동 매칭")
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
        
        layout = QHBoxLayout(group)
        
        self.leManual = QLineEdit()
        self.leManual.setPlaceholderText("TMDB에서 제목 검색 (ja/en/ko)")
        self.leManual.setMinimumWidth(300)
        
        btnMMSearch = QPushButton("🔍 검색")
        btnMMSearch.setStyleSheet(self.get_button_style("#3498db"))
        
        btnMMAttach = QPushButton("📎 연결")
        btnMMAttach.setStyleSheet(self.get_button_style("#27ae60"))
        
        layout.addWidget(self.leManual)
        layout.addWidget(btnMMSearch)
        layout.addWidget(btnMMAttach)
        
        return group
        
    def get_button_style(self, color):
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
        # 버튼 클릭 이벤트
        self.btnChooseSourceFolder.clicked.connect(self.choose_source_folder)
        self.btnChooseSourceFiles.clicked.connect(self.choose_source_files)
        self.btnChooseDestFolder.clicked.connect(self.choose_destination_folder)
        self.btnStart.clicked.connect(self.start_scan)
        self.btnPause.clicked.connect(self.stop_scan)
        self.btnSettings.clicked.connect(self.open_settings)
        self.btnClearCompleted.clicked.connect(self.clear_completed)
        self.btnResetFilters.clicked.connect(self.reset_filters)
        self.btnBulk.clicked.connect(self.bulk_actions)
        self.btnCommit.clicked.connect(self.commit_organization)
        self.btnSimulate.clicked.connect(self.simulate_organization)
        
        # 검색 및 필터
        self.search.textChanged.connect(self.proxy.setQuery)
        self.statusFilter.currentTextChanged.connect(self.on_status_filter_changed)
        
        # 더블클릭 이벤트
        self.table.doubleClicked.connect(self.on_table_double_clicked)
        
        # 타이머 설정
        self.timer = QTimer(self)
        self.timer.setInterval(700)
        self.timer.timeout.connect(self.on_scan_tick)
        
    def initialize_data(self):
        """초기 데이터 설정"""
        # 빈 리스트로 초기화 (실제 파일 스캔 결과로 대체)
        self.items = []
        self.scanning = False
        self.progress = 0
        
        # 파일 시스템 관련 변수 초기화
        self.source_directory = None
        self.source_files = []
        self.destination_directory = None
        
        # UI 초기화 후에 호출할 메서드들은 주석 처리
        # self.refresh_stats()
        # self.refresh_showing()
        # self.rebuild_grouped_view()
        
    # ------- UI 액션 메서드들 -------
    def choose_files(self):
        """파일 선택 (기존 메서드 - 메뉴바용)"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "파일 선택", "", 
            "Video Files (*.mkv *.mp4 *.avi *.mov);;All Files (*)"
        )
        if files:
            self.source_files = files
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
            self.update_status_bar(f"{len(files)}개 파일이 선택되었습니다")
            self.update_scan_button_state()
            QMessageBox.information(self, "파일 선택", f"{len(files)}개 파일이 선택되었습니다.")
            
    def choose_folder(self):
        """폴더 선택 (기존 메서드 - 메뉴바용)"""
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder:
            self.source_directory = folder
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
            self.update_status_bar(f"선택된 폴더: {folder}")
            self.update_scan_button_state()
            QMessageBox.information(self, "폴더 선택", f"선택된 폴더: {folder}")
            
    def choose_source_folder(self):
        """소스 폴더 선택 (새로운 메서드)"""
        folder = QFileDialog.getExistingDirectory(
            self, "소스 폴더 선택", 
            self.source_directory if hasattr(self, 'source_directory') else ""
        )
        if folder:
            self.source_directory = folder
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
            self.update_status_bar(f"소스 폴더가 선택되었습니다: {folder}")
            self.update_scan_button_state()
            
            # 소스 폴더 내 파일 수 확인
            try:
                import os
                video_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv')
                file_count = sum(1 for f in os.listdir(folder) 
                               if f.lower().endswith(video_extensions))
                self.update_status_bar(f"소스 폴더: {folder} ({file_count}개 비디오 파일 발견)")
            except Exception as e:
                self.update_status_bar(f"소스 폴더: {folder} (파일 수 확인 실패)")
            
            # 설정에 소스 폴더 저장
            self.save_session_state()
                
    def choose_source_files(self):
        """소스 파일 선택 (새로운 메서드)"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "애니메이션 파일 선택", 
            self.source_directory if hasattr(self, 'source_directory') else "", 
            "Video Files (*.mkv *.mp4 *.avi *.mov *.wmv *.flv);;All Files (*)"
        )
        if files:
            self.source_files = files
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
            self.update_status_bar(f"{len(files)}개 파일이 선택되었습니다")
            self.update_scan_button_state()
            
            # 선택된 파일들을 파싱하고 메타데이터 검색
            self.process_selected_files(files)
            
            # 설정에 선택된 파일들 저장
            self.save_session_state()
            
    def process_selected_files(self, file_paths: List[str]):
        """선택된 파일들을 처리하고 메타데이터 검색"""
        if not self.file_parser:
            QMessageBox.warning(self, "경고", "FileParser가 초기화되지 않았습니다.")
            return
            
        if not self.tmdb_client:
            QMessageBox.warning(self, "경고", "TMDBClient가 초기화되지 않았습니다.\nTMDB_API_KEY 환경 변수를 설정해주세요.")
            return
            
        self.update_status_bar("파일 파싱 및 메타데이터 검색 중...")
        
        # 파싱된 파일들을 저장할 리스트
        parsed_items = []
        
        # 각 파일을 처리 (파싱만 수행, TMDB 검색은 나중에)
        for i, file_path in enumerate(file_paths):
            try:
                # 진행률 업데이트
                progress = int((i / len(file_paths)) * 100)
                self.update_status_bar(f"파일 파싱 중... {i+1}/{len(file_paths)} ({progress}%)", progress)
                
                # 파일 파싱
                print(f"🔍 파싱 시작: {os.path.basename(file_path)}")
                parsed_metadata = self.file_parser.parse_filename(file_path)
                
                # 파싱 결과 디버깅
                if parsed_metadata:
                    print(f"✅ 파싱 성공:")
                    print(f"   제목: {parsed_metadata.title}")
                    print(f"   시즌: {parsed_metadata.season}")
                    print(f"   에피소드: {parsed_metadata.episode}")
                    print(f"   해상도: {parsed_metadata.resolution}")
                    print(f"   그룹: {parsed_metadata.group}")
                    print(f"   코덱: {parsed_metadata.codec}")
                    print(f"   컨테이너: {parsed_metadata.container}")
                    print(f"   신뢰도: {parsed_metadata.confidence or 'N/A'}")
                else:
                    print(f"❌ 파싱 실패: {os.path.basename(file_path)}")
                
                if parsed_metadata and parsed_metadata.title:
                    # 파싱된 항목 생성 (TMDB 검색은 나중에)
                    parsed_item = ParsedItem(
                        sourcePath=file_path,
                        detectedTitle=parsed_metadata.title,
                        title=parsed_metadata.title,
                        season=parsed_metadata.season or 1,
                        episode=parsed_metadata.episode or 1,
                        resolution=parsed_metadata.resolution or "Unknown",
                        container=parsed_metadata.container or "Unknown",
                        codec=parsed_metadata.codec or "Unknown",
                        year=parsed_metadata.year,
                        group=parsed_metadata.group or "Unknown",
                        status="pending",
                        tmdbMatch=None,
                        parsingConfidence=parsed_metadata.confidence or 0.0,
                        normalizedTitle=self.normalize_title_for_grouping(parsed_metadata.title)
                    )
                    parsed_items.append(parsed_item)
                    
                    # 활동 로그 업데이트
                    log_message = f"✅ {os.path.basename(file_path)} - {parsed_metadata.title} S{parsed_item.season:02d}E{parsed_item.episode:02d}\n    └─ 파싱 신뢰도: {parsed_metadata.confidence*100:.1f}%"
                    self.add_activity_log(log_message)
                    
                    self.update_status_bar(f"'{parsed_metadata.title}' 파싱 완료")
                        
                else:
                    print(f"❌ 파싱 실패 또는 제목 없음: {os.path.basename(file_path)}")
                    # 파싱 실패
                    parsed_item = ParsedItem(
                        sourcePath=file_path,
                        detectedTitle="Unknown",
                        title="Unknown",
                        season=1,
                        episode=1,
                        resolution="Unknown",
                        container="Unknown",
                        codec="Unknown",
                        year=None,
                        group="Unknown",
                        status="error",
                        tmdbMatch=None,
                        parsingConfidence=0.0
                    )
                    parsed_items.append(parsed_item)
                    self.update_status_bar(f"파일명 파싱 실패: {os.path.basename(file_path)}")
                    
            except Exception as e:
                print(f"❌ 파일 처리 오류: {file_path} - {e}")
                # 에러 발생 시
                parsed_item = ParsedItem(
                    sourcePath=file_path,
                    detectedTitle="Error",
                    title="Error",
                    season=1,
                    episode=1,
                    resolution="Unknown",
                    container="Unknown",
                    codec="Unknown",
                    year=None,
                    group="Unknown",
                    status="error",
                    tmdbMatch=None,
                    parsingConfidence=0.0
                )
                parsed_items.append(parsed_item)
                self.update_status_bar(f"파일 처리 오류: {os.path.basename(file_path)} - {str(e)}")
                print(f"파일 처리 오류: {file_path} - {e}")
        
        print(f"📊 최종 파싱 결과: {len(parsed_items)}개 항목")
        
        # 유사한 제목을 가진 파일들을 그룹화
        if parsed_items:
            print("\n🔗 파일 그룹화 시작...")
            grouped_items = self.group_similar_titles(parsed_items)
            self.display_grouped_results(grouped_items)
            
            # 그룹별로 TMDB 검색 수행 (중복 제거)
            print("\n🔍 그룹별 TMDB 검색 시작...")
            self.process_tmdb_search_by_groups(grouped_items)
            
            # 그룹화된 항목들을 GUI에 추가
            self.add_parsed_items_to_gui(grouped_items)
            self.update_status_bar(f"파일 처리 완료: {len(parsed_items)}개 파일 파싱됨 (그룹화 및 TMDB 검색 완료)")
        else:
            self.update_status_bar("파일 처리 완료: 파싱된 파일 없음")
    
    def add_parsed_items_to_gui(self, parsed_items: List[ParsedItem]):
        """파싱된 항목들을 GUI에 추가"""
        # 기존 항목에 새로 파싱된 항목들 추가
        self.items.extend(parsed_items)
        
        # 모델 업데이트
        self.model.beginResetModel()
        self.model.items = self.items
        self.model.endResetModel()
        
        # 통계 및 뷰 새로고침
        self.refresh_stats()
        self.refresh_showing()
        self.rebuild_grouped_view()
        
        # 로그에 추가
        for item in parsed_items:
            status_emoji = {
                "parsed": "✅",
                "needs_review": "⚠️", 
                "skipped": "⏭️",
                "error": "❌"
            }.get(item.status, "❓")
            
            # 올바른 필드 참조
            filename = item.filename or os.path.basename(item.sourcePath)
            title = item.title or item.detectedTitle or "Unknown"
            season = item.season or 1
            episode = item.episode or 1
            
            self.txtLog.append(f"[{self.get_current_time()}] {status_emoji} {filename} - {title} S{season:02d}E{episode:02d}")
            
            # 파싱 신뢰도가 있다면 로그에 추가
            if item.parsingConfidence is not None:
                confidence_text = f" (신뢰도: {item.parsingConfidence:.1%})"
                self.txtLog.append(f"    └─ 파싱 신뢰도: {item.parsingConfidence:.1%}")
    
    def get_current_time(self):
        """현재 시간을 HH:MM:SS 형식으로 반환"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    def choose_destination_folder(self):
        """대상 폴더 선택 (새로운 메서드)"""
        folder = QFileDialog.getExistingDirectory(
            self, "대상 폴더 선택", 
            self.destination_directory if hasattr(self, 'destination_directory') else ""
        )
        if folder:
            self.destination_directory = folder
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
            self.update_status_bar(f"대상 폴더가 선택되었습니다: {folder}")
            
            # 대상 폴더 쓰기 권한 확인
            try:
                import os
                test_file = os.path.join(folder, ".animesorter_test")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                self.update_status_bar(f"대상 폴더: {folder} (쓰기 권한 확인됨)")
            except Exception as e:
                self.update_status_bar(f"대상 폴더: {folder} (쓰기 권한 없음 - 경고)")
                QMessageBox.warning(self, "권한 경고", 
                    f"대상 폴더에 쓰기 권한이 없습니다:\n{folder}\n\n다른 폴더를 선택하거나 권한을 확인해주세요.")
            
            # 설정에 대상 폴더 저장
            self.save_session_state()
            
    def start_scan(self):
        """스캔 시작"""
        if not self.source_files and not self.source_directory:
            QMessageBox.warning(self, "경고", "먼저 소스 파일이나 폴더를 선택해주세요.")
            return
            
        self.scanning = True
        self.progress = 0
        self.progressBar.setValue(0)
        self.status_progress.setValue(0)
        self.btnStart.setEnabled(False)
        self.btnPause.setEnabled(True)
        self.update_status_bar("파일 스캔 중...", 0)
        
        # 실제 스캔 로직 구현
        if self.source_files:
            self.process_selected_files(self.source_files)
        elif self.source_directory:
            # 폴더 내 파일들을 찾아서 처리
            self.scan_directory(self.source_directory)
            
        self.timer.start()
        
    def scan_directory(self, directory_path: str):
        """디렉토리 스캔"""
        try:
            video_extensions = ('.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm')
            video_files = []
            
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    if file.lower().endswith(video_extensions):
                        full_path = os.path.join(root, file)
                        video_files.append(full_path)
            
            if video_files:
                self.update_status_bar(f"디렉토리에서 {len(video_files)}개 비디오 파일 발견")
                self.process_selected_files(video_files)
            else:
                self.update_status_bar("디렉토리에서 비디오 파일을 찾을 수 없습니다")
                
        except Exception as e:
            self.update_status_bar(f"디렉토리 스캔 오류: {str(e)}")
            print(f"디렉토리 스캔 오류: {e}")
        
    def stop_scan(self):
        """스캔 중지"""
        self.scanning = False
        self.timer.stop()
        self.btnStart.setEnabled(True)
        self.btnPause.setEnabled(False)
        self.update_status_bar("스캔이 중지되었습니다")
        
    def on_scan_tick(self):
        """스캔 진행률 업데이트"""
        self.progress = min(100, self.progress + 7)
        self.progressBar.setValue(self.progress)
        self.status_progress.setValue(self.progress)
        self.update_status_bar(f"스캔 진행 중... {self.progress}%", self.progress)
        
        if self.progress >= 100:
            self.stop_scan()
            self.update_status_bar("스캔 완료. 2개 항목 파싱 완료; 1개 대기 중.")
            self.txtLog.append("[12:02:23] 스캔 완료. 2개 항목 파싱 완료; 1개 대기 중.")
            
    def clear_completed(self):
        """완료된 항목 정리"""
        self.model.beginResetModel()
        self.items = [it for it in self.items if it.status != 'parsed']
        self.model.items = self.items
        self.model.endResetModel()
        self.refresh_stats()
        self.refresh_showing()
        self.rebuild_grouped_view()
        
    def reset_filters(self):
        """필터 초기화"""
        self.cmbResolution.setCurrentIndex(0)
        self.cmbContainer.setCurrentIndex(0)
        self.cmbCodec.setCurrentIndex(0)
        self.cmbYear.setCurrentIndex(0)
        self.search.clear()
        self.statusFilter.setCurrentText("전체")
        
    def bulk_actions(self):
        """일괄 작업"""
        QMessageBox.information(self, "일괄 작업", 
            "• TMDB 자동 매칭\n• 선택된 항목 정리\n• CSV 내보내기\n(구현 예정)")
            
    def commit_organization(self):
        """정리 실행"""
        QMessageBox.information(self, "정리 실행", "파일 정리 계획을 실행합니다. (구현 예정)")
        
    def simulate_organization(self):
        """정리 시뮬레이션"""
        QMessageBox.information(self, "시뮬레이션", "파일 이동을 시뮬레이션합니다. (구현 예정)")
        
    def open_settings(self):
        """설정 다이얼로그 열기"""
        dlg = SettingsDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "설정", "설정이 저장되었습니다.")
            
    def on_status_filter_changed(self, text):
        """상태 필터 변경"""
        status_map = {"전체": "all", "parsed": "parsed", "needs_review": "needs_review", "error": "error"}
        self.proxy.setStatus(status_map.get(text, "all"))
        self.refresh_showing()
        self.rebuild_grouped_view()
        
    def on_table_double_clicked(self, index):
        """테이블 더블클릭 이벤트"""
        src = self.proxy.mapToSource(index)
        row = src.row()
        if row < 0:
            return
            
        current = self.model.items[row].status
        next_status = {"parsed": "needs_review", "needs_review": "error", "error": "parsed"}[current]
        self.model.setStatus(row, next_status)
        self.refresh_stats()
        self.refresh_showing()
        self.rebuild_grouped_view()
        
    def refresh_stats(self):
        """통계 새로고침"""
        total = len(self.items)
        parsed = len([i for i in self.items if i.status == 'parsed'])
        pending = total - parsed
        
        self.lblTotal.setText(str(total))
        self.lblParsed.setText(str(parsed))
        self.lblPending.setText(str(pending))
        
    def refresh_showing(self):
        """표시 정보 새로고침"""
        self.lblShowing.setText(f"표시 중: {self.proxy.rowCount()} / {self.model.rowCount()} 항목")
        
    def rebuild_grouped_view(self):
        """그룹화된 뷰 재구성"""
        self.tree.clear()
        season_nodes = {}
        
        def best_res(res_list):
            order = {"4320p": 5, "2160p": 4, "1440p": 3, "1080p": 2, "720p": 1}
            sel = None
            score = -1
            for r in res_list:
                sc = order.get(r or "", 0)
                if sc > score:
                    sel, score = r, sc
            return sel or "-"
            
        # (제목, 시즌, 에피소드)로 그룹화
        groups = {}
        for r in range(self.proxy.rowCount()):
            src = self.proxy.mapToSource(self.proxy.index(r, 0))
            it = self.model.items[src.row()]
            key = (it.detectedTitle, it.season or 0, it.episode or 0)
            groups.setdefault(key, []).append(it)
            
        # 트리 구성
        for (title, season, episode), files in sorted(groups.items(), key=lambda k: (k[0][0].lower(), k[0][1], k[0][2])):
            s_key = (title, season)
            if s_key not in season_nodes:
                season_item = QTreeWidgetItem([f"{title} – 시즌 {season}", "", ""])
                self.tree.addTopLevelItem(season_item)
                season_nodes[s_key] = season_item
            else:
                season_item = season_nodes[s_key]
                
            # 에피소드 노드
            res_list = [f.resolution for f in files if f.resolution]
            ep_best = best_res(res_list)
            ep_item = QTreeWidgetItem([f"E{episode:02d}", str(len(files)), ep_best])
            season_item.addChild(ep_item)
            
            # 각 파일의 리프 노드
            for f in files:
                leaf = QTreeWidgetItem([f.sourcePath, "1", f.resolution or "-"])
                ep_item.addChild(leaf)
                
        self.tree.expandToDepth(1)

    def create_status_bar(self):
        """상태바 생성"""
        status_bar = self.statusBar()
        
        # 기본 상태 메시지
        self.status_label = QLabel("준비됨")
        status_bar.addWidget(self.status_label)
        
        # 진행률 표시
        status_bar.addPermanentWidget(QLabel("진행률:"))
        self.status_progress = QProgressBar()
        self.status_progress.setMaximumWidth(200)
        self.status_progress.setMaximumHeight(20)
        status_bar.addPermanentWidget(self.status_progress)
        
        # 파일 수 표시
        self.status_file_count = QLabel("파일: 0")
        status_bar.addPermanentWidget(self.status_file_count)
        
        # 메모리 사용량 표시
        self.status_memory = QLabel("메모리: 0MB")
        status_bar.addPermanentWidget(self.status_memory)
        
        # 초기 상태 설정
        self.update_status_bar("애플리케이션이 준비되었습니다")
        
    def update_status_bar(self, message, progress=None):
        """상태바 업데이트"""
        self.status_label.setText(message)
        if progress is not None:
            self.status_progress.setValue(progress)
        self.status_file_count.setText(f"파일: {len(self.items)}")
        
        # 메모리 사용량 계산 (간단한 추정)
        import psutil
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.status_memory.setText(f"메모리: {memory_mb:.1f}MB")
        except:
            self.status_memory.setText("메모리: N/A")
    
    def add_activity_log(self, message: str):
        """활동 로그에 메시지 추가"""
        if hasattr(self, 'txtLog'):
            timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
            log_entry = f"[{timestamp}] {message}"
            self.txtLog.append(log_entry)
            
            # 스크롤을 맨 아래로
            scrollbar = self.txtLog.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
