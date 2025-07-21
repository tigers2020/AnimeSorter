import os
import time
from pathlib import Path
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QGroupBox, QFileDialog
)
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QTableWidgetItem, QLabel
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize
import requests
from io import BytesIO
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
import gzip
try:
    from thefuzz import fuzz
except ImportError:
    # thefuzz가 없으면 간단한 유사도 함수 사용
    def fuzz_ratio(s1, s2):
        if not s1 or not s2:
            return 0
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        if s1_lower == s2_lower:
            return 100
        # 간단한 부분 문자열 매칭
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return 80
        return 0
    
    class fuzz:
        @staticmethod
        def ratio(s1, s2):
            return fuzz_ratio(s1, s2)

from concurrent.futures import ThreadPoolExecutor, as_completed

from .widgets import DirectorySelector, StatusPanel, FileListTable, ControlPanel
from .widgets.settings_dialog import SettingsDialog
from ..config.config_manager import ConfigManager
from ..utils.file_cleaner import FileCleaner
from src.plugin.tmdb.provider import TMDBProvider

# 새로운 모듈들 import
from ..utils.logger import get_logger
from ..exceptions import AnimeSorterError, ConfigError, FileManagerError, TMDBApiError
from ..utils.error_messages import translate_error
from ..cache.cache_db import CacheDB
from ..security.key_manager import KeyManager
from .theme_manager import ThemeManager, ThemeMode, create_theme_manager
from ..core.async_file_manager import AsyncFileManager, FileOperation

# Windows 폴더명에서 금지 문자 제거 함수
import re

def sanitize_folder_name(name: str) -> str:
    """Windows에서 사용할 수 없는 문자 제거"""
    return re.sub(r'[\\/:*?"<>|]', '', name)

class SyncWorkerSignals(QObject):
    progress = pyqtSignal(int, str)  # percent, message
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    result = pyqtSignal(dict)
    finished = pyqtSignal()

class SyncWorker(QRunnable):
    def __init__(self, file_list, file_cleaner, tmdb_provider):
        super().__init__()
        self.signals = SyncWorkerSignals()
        self.file_list = file_list
        self.file_cleaner = file_cleaner
        self.tmdb_provider = tmdb_provider

    def _strong_clean_title(self, filename):
        # 파일명에서 괄호, 대괄호, 숫자, 특수문자, 불필요한 단어 최대 제거
        import re
        name = filename
        name = re.sub(r'\[[^\]]*\]', '', name)  # [ ... ] 제거
        name = re.sub(r'\([^\)]*\)', '', name)  # ( ... ) 제거
        name = re.sub(r'\d{4}', '', name)         # 연도(4자리 숫자) 제거
        name = re.sub(r'\d+', '', name)           # 기타 숫자 제거
        name = re.sub(r'[_\-.]', ' ', name)       # 구분자 -> 공백
        name = re.sub(r'[^\w\s가-힣]', '', name) # 특수문자 제거
        name = re.sub(r'\b(ep|ova|movie|special|theatrical|bluray|web|tv|x264|x265|hevc|aac|flac|subs?)\b', '', name, flags=re.I)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def run(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        total = len(self.file_list)
        file_metadata = {}
        prev_title = None
        prev_meta = None
        for idx, file_path in enumerate(self.file_list):
            try:
                clean_result = FileCleaner.clean_filename_static(file_path)
                title = clean_result.title
                year = clean_result.year
                self.signals.log.emit(f"[{idx+1}/{total}] {file_path.name} → '{title}'({year if year else 'any'}) TMDB 검색 시도")
                if title == prev_title and prev_meta is not None:
                    result = prev_meta
                    self.signals.log.emit(f"  └─ 이전 결과 재사용")
                else:
                    t0 = time.time()
                    result = loop.run_until_complete(self.tmdb_provider.search(title, year))
                    t1 = time.time()
                    prev_title = title
                    prev_meta = result
                    self.signals.log.emit(f"  └─ TMDB 검색 완료 ({t1-t0:.2f}s)")
                # 검색 실패 시 강력 클린 후 재검색
                if not result:
                    strong_title = self._strong_clean_title(file_path.stem)
                    if strong_title and strong_title != title:
                        self.signals.log.emit(f"  └─ 1차 검색 실패, 강력 클린 '{strong_title}'로 재검색 시도")
                        t0 = time.time()
                        result2 = loop.run_until_complete(self.tmdb_provider.search(strong_title, None))
                        t1 = time.time()
                        if result2:
                            self.signals.log.emit(f"    └─ 강력 클린 재검색 성공 ({t1-t0:.2f}s)")
                            result = result2
                            prev_title = strong_title
                            prev_meta = result2
                        else:
                            self.signals.log.emit(f"    └─ 강력 클린 재검색도 실패 ({t1-t0:.2f}s)")
                file_metadata[file_path] = result
                if result:
                    genres = ", ".join([g["name"] for g in result.get("genres", [])])
                    msg = f"  └─ 장르: {genres} / 줄거리: {bool(result.get('overview'))} / 포스터: {bool(result.get('poster_path'))}"
                    self.signals.log.emit(msg)
                else:
                    self.signals.log.emit("  └─ TMDB 결과 없음")
                percent = int((idx+1)/total*100)
                self.signals.progress.emit(percent, f"{file_path.name} 동기화 완료")
            except Exception as e:
                self.signals.error.emit(f"{file_path.name} TMDB 오류: {e}")
        self.signals.result.emit(file_metadata)
        self.signals.finished.emit()
        loop.run_until_complete(self.tmdb_provider.close())
        loop.close()

class GroupSyncWorkerSignals(QObject):
    progress = pyqtSignal(int, str)
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    result = pyqtSignal(dict)
    finished = pyqtSignal()

class GroupSyncWorker(QRunnable):
    def __init__(self, group_keys, tmdb_provider):
        super().__init__()
        self.signals = GroupSyncWorkerSignals()
        self.group_keys = group_keys
        self.tmdb_provider = tmdb_provider

    def run(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        total = len(self.group_keys)
        group_metadata = {}
        prev_title = None
        prev_meta = None
        # --- 병렬 TMDB 검색 (시즌 정보 포함) ---
        async def fetch_all():
            tasks = [self.tmdb_provider.search(title, year, season) for (title, year, season) in self.group_keys]
            return await asyncio.gather(*tasks, return_exceptions=True)
        t0 = time.time()
        results = loop.run_until_complete(fetch_all())
        t1 = time.time()
        for idx, ((title, year, season), result) in enumerate(zip(self.group_keys, results)):
            if isinstance(result, Exception):
                self.signals.error.emit(f"'{title}' TMDB 오류: {result}")
                group_metadata[(title, year, season)] = None
                continue
            self.signals.log.emit(f"[{idx+1}/{total}] '{title}'({year if year else 'any'}, 시즌: {season}) TMDB 검색 완료 (병렬, {t1-t0:.2f}s)")
            group_metadata[(title, year, season)] = result
            if result:
                genres = ", ".join([g["name"] for g in result.get("genres", [])])
                msg = f"  └─ 장르: {genres} / 줄거리: {bool(result.get('overview'))} / 포스터: {bool(result.get('poster_path'))}"
                self.signals.log.emit(msg)
            else:
                self.signals.log.emit("  └─ TMDB 결과 없음")
            percent = int((idx+1)/total*100)
            self.signals.progress.emit(percent, f"'{title}' 동기화 완료")
        self.signals.result.emit(group_metadata)
        self.signals.finished.emit()
        
        # TMDBProvider close를 비동기로 처리 (딜레이 방지)
        try:
            loop.run_until_complete(asyncio.wait_for(self.tmdb_provider.close(), timeout=1.0))
        except asyncio.TimeoutError:
            # 1초 타임아웃 후 강제 종료
            pass
        except Exception as e:
            # close 실패해도 무시 (이미 작업 완료됨)
            pass
        
        loop.close()

class FileScanWorkerSignals(QObject):
    progress = pyqtSignal(int, str)
    log = pyqtSignal(str)
    result = pyqtSignal(dict)
    finished = pyqtSignal()
    metadata_ready = pyqtSignal(str, dict)  # file_path, metadata

class FileScanWorker(QRunnable):
    def __init__(self, file_paths, file_cleaner, tmdb_provider=None, config=None):
        super().__init__()
        self.signals = FileScanWorkerSignals()
        self.file_paths = file_paths
        self.file_cleaner = file_cleaner
        self.tmdb_provider = tmdb_provider
        self.config = config
        self._abort = False  # 취소 플래그

    def stop(self):
        """작업 중단 요청"""
        self._abort = True

    def _get_ext_lists(self):
        # config에서 확장자 목록을 가져오거나 기본값 사용
        video_exts = [
            ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v", ".flv"
        ]
        subtitle_exts = [
            ".srt", ".ass", ".ssa", ".sub", ".idx", ".smi", ".vtt"
        ]
        if self.config:
            video_exts = self.config.get("file_formats.video", video_exts)
            subtitle_exts = self.config.get("file_formats.subtitle", subtitle_exts)
        return set(e.lower() for e in video_exts), set(e.lower() for e in subtitle_exts)

    @staticmethod
    def _clean_filename_static(file_path_str):
        # 순수 static method 직접 호출
        return FileCleaner.clean_filename_static(file_path_str)

    def run(self):
        import os
        import asyncio
        import threading
        from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
        
        MAX_WORKERS = min(8, os.cpu_count() or 4)
        start_time = time.time()
        
        total = len(self.file_paths)
        
        self.signals.log.emit(f"[스트리밍] 파일 스캔 시작: {total}개 파일")
        
        grouped_files = {}
        video_exts, subtitle_exts = self._get_ext_lists()
        clean_cache = {}
        file_name_list = []
        ext_type_list = []
        
        # 1단계: 파일 목록 준비
        self.signals.progress.emit(5, "파일 목록 준비 중...")
        for file_path in self.file_paths:
            if self._abort:
                self.signals.log.emit("[중단] 파일 목록 준비가 취소되었습니다.")
                self.signals.finished.emit()
                return
                
            ext = Path(file_path).suffix.lower()
            file_name = str(file_path)
            is_media = ext in video_exts or ext in subtitle_exts
            file_name_list.append(file_name)
            ext_type_list.append(is_media)
        
        # 파일 크기 및 수정 시간 정보 수집
        self.signals.progress.emit(7, "파일 정보 수집 중...")
        file_info_cache = {}
        for file_path in self.file_paths:
            try:
                path_obj = Path(file_path)
                if path_obj.exists():
                    stat_info = path_obj.stat()
                    file_info_cache[str(file_path)] = {
                        'file_size': stat_info.st_size,
                        'last_modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                    }
                else:
                    file_info_cache[str(file_path)] = {
                        'file_size': 0,
                        'last_modified': datetime.now().isoformat()
                    }
            except (OSError, FileNotFoundError):
                file_info_cache[str(file_path)] = {
                    'file_size': 0,
                    'last_modified': datetime.now().isoformat()
                }
        
        # 2단계: 각 파일별 순차 처리 (정제 → 메타데이터 검색 → UI 업데이트)
        media_files_count = sum(ext_type_list)
        completed_count = 0
        
        self.signals.progress.emit(10, f"파일별 처리 시작... (0/{media_files_count})")
        
        # 미디어 파일만 처리
        for i, file_name in enumerate(file_name_list):
            if self._abort:
                self.signals.log.emit("[중단] 파일별 처리가 취소되었습니다.")
                self.signals.finished.emit()
                return
                
            if not ext_type_list[i]:
                continue
                
            try:
                # 파일명 정제
                self.signals.log.emit(f"[스트리밍] 파일 {i+1}/{media_files_count} 정제 중: {Path(file_name).name}")
                clean = FileCleaner.clean_filename_static(file_name)
                clean_cache[file_name] = clean
                
                # 메타데이터 검색 (TMDB 프로바이더가 있는 경우)
                if self.tmdb_provider and clean and clean.title:
                    self.signals.log.emit(f"[스트리밍] 메타데이터 검색 중: {clean.title}")
                    
                    # 비동기 메타데이터 검색을 위한 루프 생성
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        metadata = loop.run_until_complete(
                            self.tmdb_provider.search(clean.title, clean.year)
                        )
                        
                        if metadata:
                            self.signals.log.emit(f"[스트리밍] 메타데이터 발견: {metadata.get('title', metadata.get('name', 'Unknown'))}")
                            # 메타데이터 준비 시그널 발생
                            self.signals.metadata_ready.emit(file_name, metadata)
                        else:
                            self.signals.log.emit(f"[스트리밍] 메타데이터 없음: {clean.title}")
                    except Exception as e:
                        self.signals.log.emit(f"[스트리밍] 메타데이터 검색 오류: {e}")
                    finally:
                        loop.close()
                
                # 그룹핑 로직
                if clean and clean.title:
                    group_key = clean.title
                    if group_key not in grouped_files:
                        grouped_files[group_key] = {
                            'title': clean.title,
                            'year': clean.year,
                            'season': clean.season,
                            'episode': clean.episode,
                            'is_movie': clean.is_movie,
                            'files': [],
                            'metadata': None,
                            'file_info': {}
                        }
                    
                    grouped_files[group_key]['files'].append(file_name)
                    grouped_files[group_key]['file_info'][file_name] = file_info_cache.get(file_name, {})
                
                completed_count += 1
                progress = 10 + int((completed_count / media_files_count) * 80)  # 10-90% 범위
                self.signals.progress.emit(progress, f"파일별 처리 중... ({completed_count}/{media_files_count})")
                
            except Exception as e:
                self.signals.log.emit(f"[스트리밍] 파일 처리 오류 {file_name}: {e}")
                completed_count += 1
        
        # 3단계: 완료 처리
        elapsed = time.time() - start_time
        speed = total / elapsed if elapsed > 0 else 0
        self.signals.log.emit(f"[스트리밍] 스캔 완료: {total}개 파일, {elapsed:.2f}초, 평균 {speed:.2f}개/초")
        self.signals.progress.emit(100, f"완료! {total}개 파일 처리됨 ({speed:.1f}개/초)")
        
        self.signals.result.emit(grouped_files)
        self.signals.finished.emit()

class MainWindow(QMainWindow):
    """메인 애플리케이션 창"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnimeSorter")
        self.setMinimumSize(800, 600)
        
        # 스레드 풀을 먼저 초기화 (다른 초기화에서 사용될 수 있음)
        self.threadpool = QThreadPool.globalInstance()
        self.active_threads = []
        
        # 로거 초기화
        self.logger = get_logger("animesorter.ui.main_window")
        self.logger.info("AnimeSorter 메인 윈도우 초기화 시작")
        
        # 설정 관리자 초기화 (설정 파일 사용)
        try:
            config_file = Path("config/animesorter_config.yaml")
            self.config = ConfigManager(config_path=str(config_file))
            self.logger.info("설정 관리자 초기화 완료")
        except Exception as e:
            self.logger.error(f"설정 관리자 초기화 실패: {e}")
            QMessageBox.critical(self, "초기화 오류", f"설정 관리자 초기화 실패:\n{translate_error(e)}")
        
        # 파일명 정제 유틸리티 초기화
        try:
            self.file_cleaner = FileCleaner()
            self.logger.info("파일 정제기 초기화 완료")
        except Exception as e:
            self.logger.error(f"파일 정제기 초기화 실패: {e}")
            QMessageBox.critical(self, "초기화 오류", f"파일 정제기 초기화 실패:\n{translate_error(e)}")
        
        # 캐시 시스템 초기화
        try:
            self.cache_db = CacheDB("cache/animesorter_cache.db")
            # 비동기 초기화를 동기적으로 실행
            import asyncio
            asyncio.run(self.cache_db.initialize())
            self.logger.info("캐시 시스템 초기화 완료")
        except Exception as e:
            self.logger.error(f"캐시 시스템 초기화 실패: {e}")
            QMessageBox.critical(self, "초기화 오류", f"캐시 시스템 초기화 실패:\n{translate_error(e)}")
        
        # API 키 관리자 초기화
        try:
            self.key_manager = KeyManager("config")
            self.logger.info("API 키 관리자 초기화 완료")
        except Exception as e:
            self.logger.error(f"API 키 관리자 초기화 실패: {e}")
            QMessageBox.critical(self, "초기화 오류", f"API 키 관리자 초기화 실패:\n{translate_error(e)}")
            
        # 테마 관리자 초기화
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings("AnimeSorter", "AnimeSorter")
            self.theme_manager = create_theme_manager(settings)
            # 현재 테마 적용
            self.theme_manager.refresh_theme()
            self.logger.info("테마 관리자 초기화 완료")
        except Exception as e:
            self.logger.error(f"테마 관리자 초기화 실패: {e}")
            QMessageBox.critical(self, "초기화 오류", f"테마 관리자 초기화 실패:\n{translate_error(e)}")
        
        # TMDBProvider 초기화
        try:
            api_key = self.key_manager.get_api_key("TMDB_API_KEY") or self.config.get("tmdb.api_key", "")
            self.tmdb_provider = TMDBProvider(
                api_key=api_key,
                cache_db=self.cache_db,  # 캐시 시스템 전달
                language=self.config.get("tmdb.language", "ko-KR")
            )
            self.logger.info("TMDB 제공자 초기화 완료")
        except Exception as e:
            self.logger.error(f"TMDB 제공자 초기화 실패: {e}")
            QMessageBox.critical(self, "초기화 오류", f"TMDB 제공자 초기화 실패:\n{translate_error(e)}")
        
        # 중앙 위젯 설정
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 레이아웃 설정
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # UI 요소 초기화
        self._setup_ui()
        self._create_connections()
        
        # 자동 저장 타이머 설정
        self._setup_autosave()
        
        # 저장된 설정 로드
        self._load_saved_settings()
        
        self.grouped_files = {}  # (title, year) -> [CleanResult, ...]
        self.file_metadata = {}
        
        self.logger.info("AnimeSorter 메인 윈도우 초기화 완료")
        
    def _setup_ui(self):
        """UI 요소 생성 및 배치"""
        # 메뉴바 추가
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        # JSON 내보내기 메뉴
        export_menu = file_menu.addMenu("JSON 내보내기")
        
        # 현재 스캔 결과 내보내기
        export_current_action = export_menu.addAction("현재 스캔 결과 내보내기")
        export_current_action.setEnabled(False)  # 초기에는 비활성화
        export_current_action.triggered.connect(self._export_current_scan_results)
        self.export_current_action = export_current_action
        
        # 압축 JSON 내보내기
        export_compressed_action = export_menu.addAction("압축 JSON 내보내기")
        export_compressed_action.setEnabled(False)  # 초기에는 비활성화
        export_compressed_action.triggered.connect(self._export_compressed_scan_results)
        self.export_compressed_action = export_compressed_action
        
        # 저장된 JSON 로드
        load_json_action = export_menu.addAction("저장된 JSON 로드")
        load_json_action.triggered.connect(self._load_saved_scan_results)
        
        file_menu.addSeparator()
        
        # 설정 메뉴
        settings_menu = menubar.addMenu("설정")
        settings_action = settings_menu.addAction("설정...")
        settings_action.triggered.connect(self._open_settings_dialog)
        
        # 테마 메뉴
        theme_menu = menubar.addMenu("테마")
        
        # 라이트 모드 액션
        light_action = theme_menu.addAction("라이트 모드")
        light_action.setCheckable(True)
        light_action.triggered.connect(lambda: self._set_theme(ThemeMode.LIGHT))
        
        # 다크 모드 액션
        dark_action = theme_menu.addAction("다크 모드")
        dark_action.setCheckable(True)
        dark_action.triggered.connect(lambda: self._set_theme(ThemeMode.DARK))
        
        # 시스템 테마 액션
        system_action = theme_menu.addAction("시스템 테마")
        system_action.setCheckable(True)
        system_action.triggered.connect(lambda: self._set_theme(ThemeMode.SYSTEM))
        
        # 테마 토글 액션
        theme_menu.addSeparator()
        toggle_action = theme_menu.addAction("테마 토글 (Ctrl+T)")
        toggle_action.triggered.connect(self._toggle_theme)
        
        # 테마 액션들을 저장
        self.theme_actions = {
            ThemeMode.LIGHT: light_action,
            ThemeMode.DARK: dark_action,
            ThemeMode.SYSTEM: system_action
        }
        
        # 현재 테마에 따라 체크 상태 설정
        self._update_theme_menu_state()
        
        # 키보드 단축키 설정
        from PyQt6.QtGui import QKeySequence, QShortcut
        toggle_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        toggle_shortcut.activated.connect(self._toggle_theme)
        
        # 추가 단축키 설정
        open_folder_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        open_folder_shortcut.activated.connect(self._open_source_folder)
        
        save_settings_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_settings_shortcut.activated.connect(self._save_settings)
        
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._scan_files)
        
        cancel_shortcut = QShortcut(QKeySequence("Esc"), self)
        cancel_shortcut.activated.connect(self._cancel_operation)
        
        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)
        
        # 경로 선택 영역
        self.path_group = QGroupBox("디렉토리 설정")
        path_layout = QVBoxLayout(self.path_group)
        
        # 디렉토리 선택기
        self.source_selector = DirectorySelector("소스 폴더:", is_target=False)
        self.target_selector = DirectorySelector("대상 폴더:", is_target=True)
        
        path_layout.addWidget(self.source_selector)
        path_layout.addWidget(self.target_selector)
        
        # 컨트롤 패널
        self.control_panel = ControlPanel()
        path_layout.addWidget(self.control_panel)
        
        # 메인 레이아웃에 추가
        self.main_layout.addWidget(self.path_group)
        
        # 파일 목록 테이블
        self.file_list = FileListTable()
        self.main_layout.addWidget(self.file_list)
        
        # 상태 패널
        self.status_panel = StatusPanel()
        self.main_layout.addWidget(self.status_panel)
        
    def _create_connections(self):
        """시그널-슬롯 연결"""
        # 스캔과 동기화 버튼 연결 제거 (자동화됨)
        self.control_panel.move_button.clicked.connect(self._move_files)
        
        # 디렉토리 선택기 연결 - 자동 스캔 실행
        self.source_selector.path_edit.textChanged.connect(self._on_source_dir_changed)
        self.target_selector.path_edit.textChanged.connect(self._on_target_dir_changed)
        
        # 파일 목록 테이블 드래그 앤 드롭 연결
        self.file_list.files_dropped.connect(self._on_files_dropped)
        
    def _setup_autosave(self):
        """자동 저장 타이머 설정"""
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._save_settings)
        self.autosave_timer.start(30000)  # 30초마다 저장
        
    def _load_saved_settings(self):
        """저장된 설정 로드"""
        # 디렉토리 설정 로드
        source_dir = self.config.get("directories.source", "")
        target_dir = self.config.get("directories.target", "")
        
        if source_dir:
            self.source_selector.set_path(source_dir)
        if target_dir:
            self.target_selector.set_path(target_dir)
            
    def _save_settings(self):
        """현재 설정 저장"""
        # 디렉토리 설정 저장
        self.config.set("directories.source", self.source_selector.get_path())
        self.config.set("directories.target", self.target_selector.get_path())
        
        # 설정 파일에 저장
        self.config.save_config()
        
    def _on_source_dir_changed(self, path: str):
        """소스 디렉토리 변경 처리 - 자동 스캔 실행"""
        self.config.set("directories.source", path)
        
        # 경로가 유효하고 비어있지 않으면 자동 스캔 실행
        if path and os.path.exists(path):
            self.status_panel.log_message(f"[자동] 소스 폴더 변경 감지: {path}")
            self._scan_files()
        
    def _on_target_dir_changed(self, path: str):
        """대상 디렉토리 변경 처리"""
        self.config.set("directories.target", path)
        
    def _scan_files(self):
        """파일 스캔"""
        source_dir = self.config.get("directories.source")
        if not source_dir or not os.path.exists(source_dir):
            QMessageBox.warning(self, "경고", "유효한 소스 디렉토리를 선택해주세요.")
            return
            
        # 스캔 버튼 비활성화 제거 (자동화됨)
        
        # 파일 경로 수집
        file_paths = []
        try:
            for ext in self.config.get("file_extensions.video", [".mp4", ".mkv", ".avi"]):
                file_paths.extend(Path(source_dir).rglob(f"*{ext}"))
        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일 스캔 중 오류가 발생했습니다: {e}")
            return
            
        # 스캔 시작 시간 기록
        self.scan_start_time = time.time()
            
        # 진행 상황 시각화 초기화
        self.status_panel.set_step_active("파일 스캔", True)
        self.status_panel.set_step_progress("파일 스캔", 0)
        self.status_panel.set_progress(0, "파일 스캔 중...")
            
        # os.scandir()를 사용한 최적화된 파일 탐색 (5배 빠름)
        self.zip_files = []
        
        def scan_directory_optimized(root_path):
            """os.scandir()를 사용한 재귀적 파일 탐색"""
            stack = [Path(root_path)]
            
            while stack:
                current_path = stack.pop()
                try:
                    with os.scandir(current_path) as entries:
                        for entry in entries:
                            if entry.is_dir(follow_symlinks=False):
                                # 디렉토리면 스택에 추가하여 재귀 탐색
                                stack.append(Path(entry.path))
                            elif entry.is_file(follow_symlinks=False):
                                # 파일이면 확장자에 따라 분류
                                file_path = Path(entry.path)
                                if file_path.suffix.lower() == ".zip":
                                    self.zip_files.append(file_path)
                                else:
                                    file_paths.append(file_path)
                except (PermissionError, OSError) as e:
                    self.status_panel.log_message(f"[경고] 접근 불가: {current_path} - {e}")
                    continue
        
        # 최적화된 파일 탐색 실행
        scan_start = time.time()
        scan_directory_optimized(source_dir)
        scan_elapsed = time.time() - scan_start
        
        if not file_paths:
            QMessageBox.information(self, "안내", "파일이 없습니다.")
            self.status_panel.set_step_active("파일 스캔", False)
            return
            
        # 스캔 완료 - 진행률 업데이트
        self.status_panel.set_step_progress("파일 스캔", 100)
        self.status_panel.set_step_completed("파일 스캔", True)
        
        # 속도 계산 및 표시
        scan_speed = len(file_paths) / scan_elapsed if scan_elapsed > 0 else 0
        self.status_panel.update_speed(scan_speed)
        
        self.status_panel.log_message(f"[스캔] 파일 탐색 완료: {len(file_paths)}개 파일 ({scan_elapsed:.2f}초, {scan_speed:.1f}개/초)")
        self.status_panel.log_message(f"[스캔] 총 {len(file_paths)}개 파일 스캔 시작... (zip 파일 {len(self.zip_files)}개 분리)")
        
        if self.zip_files:
            self.status_panel.log_message(f"[스캔] 분리된 zip 파일: {[str(z) for z in self.zip_files]}")
            
        # ETA 추적 시작
        self.status_panel.start_tracking(len(file_paths))
            
        worker = FileScanWorker(file_paths, self.file_cleaner, self.tmdb_provider, self.config)
        worker.signals.progress.connect(self._on_scan_progress)
        worker.signals.log.connect(self.status_panel.log_message)
        worker.signals.metadata_ready.connect(self._on_metadata_ready)
        
        def on_result(grouped_files):
            self.grouped_files = grouped_files
            self._update_table_from_grouped_files()
            
        worker.signals.result.connect(on_result)
        worker.signals.finished.connect(self._on_scan_finished)
        self.threadpool.start(worker)
        
    def _on_scan_progress(self, percent: int, message: str):
        """스캔 진행률 업데이트"""
        self.status_panel.set_progress(percent, message)
        self.status_panel.update_progress(int(percent * len(self.grouped_files) / 100) if hasattr(self, 'grouped_files') else 0)
        
        # 파일명 정제 단계 진행률도 함께 업데이트
        if percent > 0:
            self.status_panel.set_step_progress("파일명 정제", percent)
            
    def _on_metadata_ready(self, file_path: str, metadata: dict):
        """메타데이터 준비 시그널 처리"""
        # UI 테이블에서 해당 파일의 행을 찾아 메타데이터 업데이트
        for row in range(self.file_list.rowCount()):
            file_item = self.file_list.item(row, 0)  # 파일명 컬럼
            if file_item and file_item.data(Qt.UserRole) == file_path:
                # 메타데이터 컬럼 업데이트
                title = metadata.get('title', metadata.get('name', 'Unknown'))
                year = metadata.get('release_date', metadata.get('first_air_date', ''))
                if year:
                    try:
                        year = year.split('-')[0]
                    except:
                        year = ''
                
                metadata_text = f"{title} ({year})" if year else title
                metadata_item = QTableWidgetItem(metadata_text)
                metadata_item.setData(Qt.UserRole, metadata)
                self.file_list.setItem(row, 2, metadata_item)  # 메타데이터 컬럼
                
                # 포스터가 있으면 다운로드
                poster_path = metadata.get('poster_path')
                if poster_path:
                    poster_url = f"https://image.tmdb.org/t/p/p92{poster_path}"
                    self._download_poster_async(row, poster_url)
                
                self.status_panel.log_message(f"✅ [스트리밍] UI 업데이트 완료: {Path(file_path).name}")
                break
    
    def _on_scan_finished(self):
        """스캔 완료 처리"""
        self.status_panel.set_progress(100, "스캔 완료")
        self.status_panel.set_step_completed("파일명 정제", True)
        self.status_panel.set_step_active("파일 스캔", False)
        
        # 스캔된 파일이 있으면 스트리밍 파이프라인 준비 메시지
        if hasattr(self, 'grouped_files') and self.grouped_files:
            self.status_panel.log_message("🎯 [스트리밍] 파일 스캔 완료! 이제 '파일 이동' 버튼을 클릭하여 스트리밍 처리를 시작하세요.")
            self.status_panel.log_message("💡 각 파일이 정제 → 메타데이터 검색 → UI 업데이트 순서로 실시간 처리됩니다.")
        else:
            self.status_panel.log_message("📁 스캔된 파일이 없습니다.")

    def _update_table_from_grouped_files(self):
        """grouped_files 데이터를 테이블에 반영 및 JSON 저장"""
        self.file_list.setRowCount(0)
        for (title, year, season), results in self.grouped_files.items():
            row = self.file_list.rowCount()
            self.file_list.insertRow(row)
            # 파일명들
            filenames = "\n".join([
                Path(r["original_filename"]).name if isinstance(r, dict) and "original_filename" in r
                else Path(getattr(r, "original_filename", "")).name
                for r in results
            ])
            self.file_list.setItem(row, 0, QTableWidgetItem(filenames))
            # 확장자들
            exts = ", ".join(sorted(set(
                Path(r["original_filename"]).suffix[1:] if isinstance(r, dict) and "original_filename" in r
                else Path(getattr(r, "original_filename", "")).suffix[1:]
                for r in results if Path(r["original_filename"] if isinstance(r, dict) and "original_filename" in r else getattr(r, "original_filename", "")).suffix
            )))
            self.file_list.setItem(row, 1, QTableWidgetItem(exts))
            self.file_list.setItem(row, 2, QTableWidgetItem(title))
            seasons = ", ".join(sorted({
                str(r["season"]) if isinstance(r, dict) and "season" in r else str(getattr(r, "season", 1))
                for r in results
            }))
            self.file_list.setItem(row, 3, QTableWidgetItem(seasons))
            episodes = ", ".join(sorted({
                str(r["episode"]) if isinstance(r, dict) and "episode" in r and r["episode"] is not None
                else str(getattr(r, "episode", None)) for r in results if (r["episode"] if isinstance(r, dict) and "episode" in r else getattr(r, "episode", None)) is not None
            }))
            self.file_list.setItem(row, 4, QTableWidgetItem(episodes))
            for i in range(5, len(self.file_list.COLUMNS)):
                self.file_list.setItem(row, i, QTableWidgetItem(""))
        has_files = self.file_list.rowCount() > 0
        # 동기화 버튼 활성화 제거 (자동화됨)
        
        # JSON 내보내기 메뉴 활성화
        if hasattr(self, 'export_current_action'):
            self.export_current_action.setEnabled(has_files)
        if hasattr(self, 'export_compressed_action'):
            self.export_compressed_action.setEnabled(has_files)
        
        self.status_panel.log_message(f"총 {self.file_list.rowCount()}개의 그룹(제목) 파일을 찾았습니다. (자동 정제 및 그룹핑 완료)")
        
        # --- 스캔 결과 JSON 저장 (개선된 버전) ---
        # 백그라운드에서 JSON 저장 실행
        self._save_scan_results_async()
    
    def _save_scan_results_async(self):
        """스캔 결과를 백그라운드에서 JSON으로 저장"""
        class JSONSaveWorker(QRunnable):
            def __init__(self, grouped_files, source_directory, scan_duration, status_panel):
                super().__init__()
                self.grouped_files = grouped_files
                self.source_directory = source_directory
                self.scan_duration = scan_duration
                self.status_panel = status_panel
                self.signals = JSONSaveSignals()
                
            def run(self):
                try:
                    from utils.json_exporter import JSONExporter, ExportFormat
                    
                    # JSON 내보내기 객체 생성
                    exporter = JSONExporter()
                    
                    # 저장 디렉토리 생성
                    save_dir = Path("./scan_results")
                    save_dir.mkdir(exist_ok=True)
                    
                    # 파일명 생성 (타임스탬프 포함)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_path = save_dir / f"scan_result_{timestamp}"
                    
                    # 스트리밍 JSON 내보내기 실행 (최적화된 버전)
                    saved_path = exporter._export_scan_results_streaming(
                        grouped_files=self.grouped_files,
                        source_directory=self.source_directory,
                        scan_duration=self.scan_duration,
                        output_path=output_path,
                        compress=False
                    )
                    
                    # 요약 정보 생성
                    scan_data = exporter.load_scan_results(saved_path)
                    summary = exporter.get_export_summary(scan_data)
                    
                    # 결과 시그널 전송
                    self.signals.success.emit(str(saved_path), summary)
                    
                    # 압축 버전도 생성 (선택사항)
                    compressed_path = exporter._export_scan_results_streaming(
                        grouped_files=self.grouped_files,
                        source_directory=self.source_directory,
                        scan_duration=self.scan_duration,
                        output_path=output_path,
                        compress=True
                    )
                    
                    self.signals.compressed.emit(str(compressed_path))
                    
                except ImportError as e:
                    self.signals.error.emit(f"JSON 내보내기 모듈을 찾을 수 없습니다: {e}")
                except Exception as e:
                    self.signals.error.emit(f"스캔 결과 저장 오류: {e}")
        
        class JSONSaveSignals(QObject):
            success = pyqtSignal(str, str)  # saved_path, summary
            compressed = pyqtSignal(str)    # compressed_path
            error = pyqtSignal(str)         # error_message
        
        # 워커 생성 및 실행
        worker = JSONSaveWorker(
            self.grouped_files,
            self.source_selector.get_path(),
            time.time() - getattr(self, 'scan_start_time', time.time()),
            self.status_panel
        )
        
        # 시그널 연결
        worker.signals.success.connect(
            lambda path, summary: self.status_panel.log_message(f"✅ 스캔 결과 저장 완료: {path}\n{summary}")
        )
        worker.signals.compressed.connect(
            lambda path: self.status_panel.log_message(f"📦 압축 버전 저장: {path}")
        )
        worker.signals.error.connect(
            lambda error: self._handle_json_save_error(error)
        )
        
        # 백그라운드에서 실행
        QThreadPool.globalInstance().start(worker)
    
    def _handle_json_save_error(self, error_message: str):
        """JSON 저장 오류 처리"""
        self.status_panel.log_message(f"❌ {error_message}")
        # 기존 방식으로 폴백
        self._save_scan_results_fallback()
    
    def _save_scan_results_fallback(self):
        """기존 방식으로 스캔 결과 저장 (폴백)"""
        try:
            save_dir = Path("./scan_results")
            save_dir.mkdir(exist_ok=True)
            save_path = save_dir / f"scan_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # json 직렬화: grouped_files를 dict로 변환
            serializable = {}
            for (title, year, season), results in self.grouped_files.items():
                serializable_key = f"{title}__{year if year else ''}__{season}"
                serializable[serializable_key] = [
                    {
                        "original_filename": str(r["original_filename"]) if isinstance(r, dict) and "original_filename" in r else str(getattr(r, "original_filename", "")),
                        "title": r["title"] if isinstance(r, dict) and "title" in r else getattr(r, "title", ""),
                        "season": r["season"] if isinstance(r, dict) and "season" in r else getattr(r, "season", 1),
                        "episode": r["episode"] if isinstance(r, dict) and "episode" in r else getattr(r, "episode", None),
                        "year": r["year"] if isinstance(r, dict) and "year" in r else getattr(r, "year", None),
                        "is_movie": r["is_movie"] if isinstance(r, dict) and "is_movie" in r else getattr(r, "is_movie", False),
                        "extra_info": r["extra_info"] if isinstance(r, dict) and "extra_info" in r else getattr(r, "extra_info", {})
                    }
                    for r in results
                ]
            
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)
            
            self.status_panel.log_message(f"📄 스캔 결과 저장 (기존 방식): {save_path}")
            
        except Exception as e:
            self.status_panel.log_message(f"❌ 스캔 결과 저장 실패: {e}")
    
    def _export_current_scan_results(self):
        """현재 스캔 결과를 JSON으로 내보내기"""
        if not hasattr(self, 'grouped_files') or not self.grouped_files:
            QMessageBox.warning(self, "경고", "내보낼 스캔 결과가 없습니다. 먼저 파일을 스캔해주세요.")
            return
        
        try:
            from PyQt6.QtWidgets import QFileDialog
            from utils.json_exporter import JSONExporter, ExportFormat
            
            # 파일 저장 대화상자
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "스캔 결과 JSON 저장",
                f"scan_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON 파일 (*.json)"
            )
            
            if not file_path:
                return
            
            # JSON 내보내기 실행
            exporter = JSONExporter()
            scan_duration = time.time() - getattr(self, 'scan_start_time', time.time())
            
            saved_path = exporter.export_scan_results(
                grouped_files=self.grouped_files,
                source_directory=self.source_selector.get_path(),
                scan_duration=scan_duration,
                output_path=file_path,
                format=ExportFormat.JSON,
                include_metadata=True,
                compress=False
            )
            
            # 요약 정보 표시
            scan_data = exporter.load_scan_results(saved_path)
            summary = exporter.get_export_summary(scan_data)
            
            QMessageBox.information(self, "내보내기 완료", 
                f"스캔 결과가 성공적으로 저장되었습니다.\n\n{summary}")
            
        except ImportError as e:
            QMessageBox.warning(self, "오류", f"JSON 내보내기 모듈을 찾을 수 없습니다: {e}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"JSON 내보내기 중 오류가 발생했습니다: {e}")
    
    def _export_compressed_scan_results(self):
        """현재 스캔 결과를 압축 JSON으로 내보내기"""
        if not hasattr(self, 'grouped_files') or not self.grouped_files:
            QMessageBox.warning(self, "경고", "내보낼 스캔 결과가 없습니다. 먼저 파일을 스캔해주세요.")
            return
        
        try:
            from PyQt6.QtWidgets import QFileDialog
            from utils.json_exporter import JSONExporter, ExportFormat
            
            # 파일 저장 대화상자
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "스캔 결과 압축 JSON 저장",
                f"scan_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.gz",
                "압축 JSON 파일 (*.json.gz)"
            )
            
            if not file_path:
                return
            
            # JSON 내보내기 실행
            exporter = JSONExporter()
            scan_duration = time.time() - getattr(self, 'scan_start_time', time.time())
            
            saved_path = exporter.export_scan_results(
                grouped_files=self.grouped_files,
                source_directory=self.source_selector.get_path(),
                scan_duration=scan_duration,
                output_path=file_path,
                format=ExportFormat.GZIPPED_JSON,
                include_metadata=True,
                compress=True
            )
            
            # 파일 크기 정보 표시
            file_size = saved_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            QMessageBox.information(self, "압축 내보내기 완료", 
                f"압축 JSON 파일이 성공적으로 저장되었습니다.\n\n"
                f"파일 크기: {size_mb:.2f} MB\n"
                f"저장 위치: {saved_path}")
            
        except ImportError as e:
            QMessageBox.warning(self, "오류", f"JSON 내보내기 모듈을 찾을 수 없습니다: {e}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"압축 JSON 내보내기 중 오류가 발생했습니다: {e}")
    
    def _load_saved_scan_results(self):
        """저장된 JSON 파일에서 스캔 결과 로드"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            from utils.json_exporter import JSONExporter
            
            # 파일 열기 대화상자
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "저장된 스캔 결과 JSON 로드",
                "",
                "JSON 파일 (*.json *.json.gz)"
            )
            
            if not file_path:
                return
            
            # JSON 로드
            exporter = JSONExporter()
            scan_data = exporter.load_scan_results(file_path)
            
            # 그룹화된 파일 데이터로 변환
            self.grouped_files = {}
            for group in scan_data.groups:
                key = (group.title, group.year)
                self.grouped_files[key] = []
                
                for file_info in group.files:
                    # CleanResult 객체 생성
                    from utils.file_cleaner import CleanResult
                    clean_result = CleanResult(
                        title=group.title,
                        original_filename=file_info.original_path,
                        season=group.season,
                        episode=group.episode,
                        year=group.year,
                        is_movie=False,
                        extra_info=file_info.metadata
                    )
                    self.grouped_files[key].append(clean_result)
            
            # 테이블 업데이트
            self._update_table_from_grouped_files()
            
            # 요약 정보 표시
            summary = exporter.get_export_summary(scan_data)
            QMessageBox.information(self, "로드 완료", 
                f"스캔 결과가 성공적으로 로드되었습니다.\n\n{summary}")
            
        except ImportError as e:
            QMessageBox.warning(self, "오류", f"JSON 내보내기 모듈을 찾을 수 없습니다: {e}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"JSON 로드 중 오류가 발생했습니다: {e}")

    def _clean_filenames(self):
        """파일명 정제 및 결과 저장"""
        try:
            # 정제 결과를 저장할 딕셔너리
            cleaning_results = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_directory": self.source_selector.get_path(),
                "files": []
            }

            for row in range(self.file_list.rowCount()):
                file_path = self.file_list.file_paths[row]
                clean_result = self.file_cleaner.clean_filename(file_path)
                self.file_list.update_clean_info(row, clean_result)

                # CleanResult의 필드명을 그대로 저장
                file_info = {
                    "original_path": str(file_path),
                    "title": getattr(clean_result, 'title', ''),
                    "original_filename": getattr(clean_result, 'original_filename', ''),
                    "season": getattr(clean_result, 'season', 1),
                    "episode": getattr(clean_result, 'episode', None),
                    "year": getattr(clean_result, 'year', None),
                    "is_movie": getattr(clean_result, 'is_movie', False),
                    "extra_info": getattr(clean_result, 'extra_info', {})
                }
                cleaning_results["files"].append(file_info)

            # 저장 경로를 프로젝트 루트로 지정
            save_dir = Path.cwd()
            save_path = save_dir / f"cleaning_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(cleaning_results, f, ensure_ascii=False, indent=2)

            self.status_panel.set_status(f"정제 결과 저장: {save_path}")
        except Exception as e:
            self.status_panel.set_status(f"정제 중 오류: {e}")
        
    def _sync_metadata(self):
        """메타데이터 동기화"""
        if not hasattr(self, 'grouped_files') or not self.grouped_files:
            QMessageBox.warning(self, "경고", "먼저 파일을 스캔해주세요.")
            return
            
        # 동기화 버튼 비활성화 제거 (자동화됨)
        
        # 그룹 키 추출
        group_keys = list(self.grouped_files.keys())
        
        # 동기화 워커 생성 및 실행
        self.sync_worker = GroupSyncWorker(group_keys, self.tmdb_provider)
        self.sync_worker.signals.progress.connect(self._on_sync_progress)
        self.sync_worker.signals.result.connect(self._on_group_sync_result)
        self.sync_worker.signals.finished.connect(self._on_sync_finished)
        
        # 스레드 풀에 추가
        QThreadPool.globalInstance().start(self.sync_worker)
        
        # 상태 업데이트
        self.status_panel.set_status("메타데이터 동기화 중...")
        self.status_panel.set_step_active("메타데이터 동기화", True)
        
    def _on_sync_progress(self, percent: int, message: str):
        """메타데이터 동기화 진행률 업데이트"""
        self.status_panel.set_progress(percent, message)
        self.status_panel.set_step_progress("메타데이터 검색", percent)
        self.status_panel.update_progress(int(percent * len(self.grouped_files) / 100) if hasattr(self, 'grouped_files') else 0)
        
        # 진행 상황을 더 자세히 표시
        if percent % 10 == 0:  # 10%마다 로그 출력
            self.status_panel.log_message(f"🔄 TMDB 검색 진행률: {percent}% - {message}")

    def _on_group_sync_result(self, group_metadata):
        self.group_metadata = group_metadata
        # file_metadata도 업데이트 (파일 이동 시 사용)
        self.file_metadata.update(group_metadata)
        
        # 디버깅: 메타데이터 로깅
        for (title, year, season), meta in group_metadata.items():
            if meta:
                media_type = meta.get('media_type', 'unknown')
                korean_title = meta.get('name') or meta.get('title') or title
                self.logger.info(f"[메타데이터] {title} ({year}, 시즌: {season}) -> {korean_title} (media_type: {media_type})")
            else:
                self.logger.warning(f"[메타데이터] {title} ({year}, 시즌: {season}) -> 메타데이터 없음")
        
        # 테이블에 결과 반영 (포스터, 장르, 줄거리 등)
        for row, key in enumerate(self.grouped_files.keys()):
            result = group_metadata.get(key)
            # 장르
            if result and "genres" in result:
                genres = ", ".join([g["name"] for g in result["genres"]])
                self.file_list.setItem(row, 5, QTableWidgetItem(genres))
            else:
                self.file_list.setItem(row, 5, QTableWidgetItem(""))
            # 한글 타이틀
            new_title = result.get("title") if result else None
            if not new_title and result:
                new_title = result.get("name")
            if new_title:
                self.file_list.setItem(row, 2, QTableWidgetItem(new_title))
            # 포스터 이미지 (비동기 처리로 변경)
            poster_url = None
            if result and result.get("poster_path"):
                poster_url = f"https://image.tmdb.org/t/p/w185{result['poster_path']}"
            if poster_url:
                # 포스터 다운로드를 별도 스레드에서 처리
                self._download_poster_async(row, poster_url)
            else:
                self.file_list.setItem(row, 6, QTableWidgetItem(""))
            # 줄거리(overview)
            overview = result.get("overview") if result else None
            self.file_list.setItem(row, 7, QTableWidgetItem(overview or ""))
            # 이동 위치 경로(메타 동기화 후)
            # title, season 정보로 이동 경로 계산
            title_for_path = new_title or key[0]
            season = key[2] if len(key) > 2 else 1
            target_root = self.target_selector.get_path() if hasattr(self, 'target_selector') else self.target_dir
            
            if target_root:
                from pathlib import Path
                # 미디어 타입 확인 (tv: 애니메이션, movie: 영화)
                media_type = result.get('media_type', 'tv') if result else 'tv'
                
                # 디버깅: 이동 경로 계산 로깅
                self.logger.info(f"[이동경로] {title_for_path} (media_type: {media_type}) -> 계산 중...")
                
                if media_type == "movie":
                    # 영화: 영화 폴더에 저장
                    target_path = Path(target_root) / "영화" / str(title_for_path)
                    self.logger.info(f"[이동경로] 영화로 분류: {target_path}")
                else:
                    # 애니메이션 (tv): 애니메이션 폴더에 시즌별로 저장
                    target_path = Path(target_root) / "애니메이션" / str(title_for_path) / f"Season {season}"
                    self.logger.info(f"[이동경로] 애니메이션으로 분류: {target_path}")
                    
                self.file_list.setItem(row, 8, QTableWidgetItem(str(target_path)))

    def _download_poster_async(self, row, poster_url):
        """포스터 이미지를 비동기로 다운로드"""
        from PyQt6.QtCore import QThread, pyqtSignal, QObject
        
        class PosterDownloader(QObject):
            finished = pyqtSignal(int, str)  # row, poster_url
            error = pyqtSignal(int, str)     # row, error_message
            
            def __init__(self, row, poster_url):
                super().__init__()
                self.row = row
                self.poster_url = poster_url
                
            def download(self):
                try:
                    import requests
                    response = requests.get(self.poster_url, timeout=5)
                    if response.status_code == 200:
                        self.finished.emit(self.row, self.poster_url)
                    else:
                        self.error.emit(self.row, f"HTTP {response.status_code}")
                except Exception as e:
                    self.error.emit(self.row, str(e))
        
        class PosterDownloadThread(QThread):
            def __init__(self, downloader):
                super().__init__()
                self.downloader = downloader
                self.downloader.moveToThread(self)
                
            def run(self):
                self.downloader.download()
                
            def cleanup(self):
                """스레드 정리"""
                if self.isRunning():
                    self.quit()
                    if not self.wait(2000):  # 2초 대기
                        self.terminate()  # 강제 종료
                        self.wait(1000)   # 추가 대기
                self.deleteLater()
                self.downloader.deleteLater()
        
        # 다운로더 생성 및 실행
        downloader = PosterDownloader(row, poster_url)
        thread = PosterDownloadThread(downloader)
        
        # 스레드 추적에 추가
        self.active_threads.append(thread)
        
        # 시그널 연결
        downloader.finished.connect(self._on_poster_downloaded)
        downloader.error.connect(self._on_poster_download_error)
        thread.finished.connect(thread.cleanup)
        thread.finished.connect(lambda: self.active_threads.remove(thread) if thread in self.active_threads else None)
        
        # 스레드 시작
        thread.start()

    def _on_poster_downloaded(self, row, poster_url):
        """포스터 다운로드 완료 처리"""
        try:
            import requests
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtWidgets import QLabel
            from PyQt6.QtCore import Qt
            
            response = requests.get(poster_url, timeout=5)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    label = QLabel()
                    label.setPixmap(pixmap.scaled(120, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.file_list.setCellWidget(row, 6, label)
                    self.file_list.setRowHeight(row, 200)
                    self.file_list.setColumnWidth(6, 150)
                else:
                    self.file_list.setItem(row, 6, QTableWidgetItem("이미지 오류(pixmap)"))
            else:
                self.file_list.setItem(row, 6, QTableWidgetItem("이미지 오류(HTTP)"))
        except Exception as e:
            self.file_list.setItem(row, 6, QTableWidgetItem("이미지 오류(예외)"))

    def _on_poster_download_error(self, row, error_message):
        """포스터 다운로드 오류 처리"""
        self.file_list.setItem(row, 6, QTableWidgetItem(f"이미지 오류: {error_message}"))

    def _on_sync_finished(self):
        """메타데이터 동기화 완료 처리"""
        self.status_panel.set_progress(100, "메타데이터 동기화 완료")
        self.status_panel.set_step_completed("메타데이터 동기화", True)
        self.status_panel.set_step_active("메타데이터 동기화", False)
        
        # 동기화 결과 요약
        if hasattr(self, 'group_metadata'):
            total_groups = len(self.group_metadata)
            successful = sum(1 for meta in self.group_metadata.values() if meta is not None)
            failed = total_groups - successful
            
            self.status_panel.log_message("✅ TMDB 메타데이터 검색 완료!")
            self.status_panel.log_message(f"📊 검색 결과: {successful}개 성공, {failed}개 실패 (총 {total_groups}개)")
            
            if successful > 0:
                self.status_panel.log_message("🎬 포스터, 장르, 줄거리 정보가 테이블에 업데이트되었습니다.")
            if failed > 0:
                self.status_panel.log_message("⚠️ 일부 파일의 메타데이터를 찾지 못했습니다. 수동으로 검색해보세요.")
        
        # 동기화 버튼 비활성화 제거 (자동화됨)
        
        # 이동 버튼 활성화
        if self.file_list.rowCount() > 0:
            self.control_panel.move_button.setEnabled(True)
        
    def _move_files(self):
        """파일 이동 처리 (스트리밍 파이프라인 사용)"""
        if not self.grouped_files:
            QMessageBox.warning(self, "경고", "먼저 파일을 스캔해주세요.")
            return
            
        # 이동 버튼 비활성화
        self.control_panel.move_button.setEnabled(False)
        
        # 대상 디렉토리 확인
        target_root = self.target_selector.get_path() if hasattr(self, 'target_selector') else self.target_dir
        if not target_root:
            QMessageBox.warning(self, "경고", "대상 디렉토리를 선택해주세요.")
            self.control_panel.move_button.setEnabled(True)
            return
            
        # 파일 경로 목록 생성
        file_paths = []
        for (title, year), group in self.grouped_files.items():
            for file_info in group:
                file_path = Path(file_info.original_filename)
                if file_path.exists():
                    file_paths.append(file_path)
                    
        if not file_paths:
            QMessageBox.warning(self, "경고", "처리할 파일이 없습니다.")
            self.control_panel.move_button.setEnabled(True)
            return
            
        # 상태 업데이트
        self.status_panel.set_status("스트리밍 파이프라인으로 파일 처리 중...")
        self.status_panel.set_progress(0)
        self.status_panel.start_tracking(len(file_paths))
        self.status_panel.set_step_active("파일 이동", True)
        
        # 에러 목록 초기화
        self.status_panel.clear_errors()
        
        # 스트리밍 워커 매니저 초기화
        from src.ui.workers.streaming_worker import StreamingWorkerManager
        if not hasattr(self, 'streaming_manager'):
            self.streaming_manager = StreamingWorkerManager()
            
        # 스트리밍 처리 시작 시간 설정
        self._streaming_start_time = time.time()
        
        # 스트리밍 처리 시작
        worker = self.streaming_manager.start_processing(
            file_paths=file_paths,
            tmdb_provider=self.tmdb_provider,
            target_directory=target_root,
            folder_template="{title} ({year})",
            progress_callback=self._on_streaming_progress,
            error_callback=self._on_streaming_error,
            finished_callback=self._on_streaming_finished,
            cancelled_callback=self._on_streaming_cancelled,
            log_callback=self._on_streaming_log,
            poster_callback=self._on_streaming_poster_ready
        )
        
        # 취소 버튼 활성화
        self.control_panel.cancel_button.setEnabled(True)
        
    def _on_streaming_progress(self, current: int, total: int, message: str):
        """스트리밍 진행 상황 업데이트"""
        # 진행률 계산
        progress = int((current / total) * 100) if total > 0 else 0
        
        # UI 업데이트
        self.status_panel.set_progress(progress, message)
        self.status_panel.set_step_progress("파일 이동", progress)
        self.status_panel.update_progress(current)
        
        # 처리 속도 계산
        if hasattr(self, '_streaming_start_time'):
            elapsed = time.time() - self._streaming_start_time
            if elapsed > 0:
                speed = current / elapsed
                self.status_panel.update_speed(speed)
                
    def _on_streaming_error(self, file_path: str, error_type: str, error_message: str):
        """스트리밍 에러 처리"""
        # 에러 로그 추가
        self.status_panel.log_error(file_path, error_type, error_message)
        
        # 에러 통계 업데이트
        if not hasattr(self, '_streaming_error_count'):
            self._streaming_error_count = 0
        self._streaming_error_count += 1
        
    def _on_streaming_finished(self, final_stats: dict):
        """스트리밍 처리 완료"""
        # 상태 업데이트
        self.status_panel.set_status("스트리밍 파이프라인 처리 완료")
        self.status_panel.set_progress(100)
        self.status_panel.set_step_completed("파일 이동", True)
        self.status_panel.set_step_active("파일 이동", False)
        
        # 버튼 상태 복원
        self.control_panel.move_button.setEnabled(True)
        self.control_panel.cancel_button.setEnabled(False)
        
        # 완료 메시지
        total_files = final_stats.get("total_files", 0)
        completion_message = f"스트리밍 파이프라인 처리 완료!\n\n총 {total_files}개 파일 처리 완료"
        
        QMessageBox.information(self, "처리 완료", completion_message)
        
        # 메타데이터 검사 실행
        self._run_metadata_inspection()
        
        # 스트리밍 매니저 정리
        self.streaming_manager.current_worker = None
        
    def _on_streaming_cancelled(self):
        """스트리밍 처리 취소"""
        self.status_panel.set_status("스트리밍 파이프라인 처리 취소됨")
        self.status_panel.set_step_active("파일 이동", False)
        
        # 버튼 상태 복원
        self.control_panel.move_button.setEnabled(True)
        self.control_panel.cancel_button.setEnabled(False)
        
        QMessageBox.information(self, "처리 취소", "파일 처리가 취소되었습니다.")
        
        # 스트리밍 매니저 정리
        self.streaming_manager.current_worker = None
        
    def _on_streaming_log(self, log_message: str):
        """스트리밍 로그 처리"""
        self.status_panel.log_message(log_message)
        
    def _on_streaming_poster_ready(self, file_path: str, poster_url: str):
        """스트리밍 포스터 준비 처리"""
        # 파일 리스트에서 해당 파일을 찾아 포스터 표시
        for row in range(self.file_list.rowCount()):
            if hasattr(self.file_list, 'file_paths') and row < len(self.file_list.file_paths):
                if str(self.file_list.file_paths[row]) == file_path:
                    # 포스터 다운로드 및 표시
                    self._download_poster_async(row, poster_url)
                    break
        
    def _cancel_operation(self):
        """작업 취소"""
        # 스트리밍 처리 취소
        if hasattr(self, 'streaming_manager') and self.streaming_manager.is_processing():
            self.streaming_manager.cancel_processing()
            self.status_panel.log_message("사용자가 작업을 취소했습니다.")
            return
            
        # 기존 워커들 취소
        if hasattr(self, 'scan_worker') and self.scan_worker:
            self.scan_worker.stop()
            self.status_panel.log_message("파일 스캔이 취소되었습니다.")
            
        if hasattr(self, 'sync_worker') and self.sync_worker:
            # GroupSyncWorker는 취소 기능이 없으므로 로그만 출력
            self.status_panel.log_message("메타데이터 동기화는 취소할 수 없습니다.")
            
        # 상태 초기화
        self.status_panel.set_status("작업 취소됨")
        self.status_panel.set_progress(0)
        
        # 버튼 상태 복원
        self.control_panel.scan_button.setEnabled(True)
        self.control_panel.move_button.setEnabled(True)
        self.control_panel.cancel_button.setEnabled(False)
                        
    def _run_metadata_inspection(self):
        """파일 이동 후 메타데이터 검사 실행"""
        # 설정 확인: 메타데이터 검사 활성화 여부
        metadata_check = self.config.get("post_process.metadata_check", True)
        
        if not metadata_check:
            self.status_panel.log_message("[설정] 메타데이터 검사가 비활성화되어 있습니다.")
            return
            
        try:
            self.status_panel.log_message("[검사] 메타데이터 무결성 검사 시작...")
            
            # 검사할 파일 목록 수집
            target_root = self.target_selector.get_path() if hasattr(self, 'target_selector') else self.target_dir
            if not target_root:
                self.status_panel.log_message("[검사] 대상 디렉토리를 찾을 수 없습니다.")
                return
                
            # 검사 결과 저장
            inspection_results = {
                'timestamp': datetime.now().isoformat(),
                'target_directory': str(target_root),
                'total_files': 0,
                'files_with_metadata': 0,
                'files_without_metadata': 0,
                'missing_posters': 0,
                'missing_descriptions': 0,
                'details': []
            }
            
            # 애니메이션 폴더 검사
            anime_dir = Path(target_root) / "애니메이션"
            if anime_dir.exists():
                for series_dir in anime_dir.iterdir():
                    if series_dir.is_dir():
                        for season_dir in series_dir.iterdir():
                            if season_dir.is_dir() and season_dir.name.startswith("Season"):
                                for file_path in season_dir.iterdir():
                                    if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.mkv', '.avi', '.mov']:
                                        inspection_results['total_files'] += 1
                                        
                                        # 메타데이터 파일 확인
                                        poster_file = season_dir / "poster.jpg"
                                        desc_file = season_dir / "description.txt"
                                        
                                        file_info = {
                                            'file_path': str(file_path),
                                            'series': series_dir.name,
                                            'season': season_dir.name,
                                            'has_poster': poster_file.exists(),
                                            'has_description': desc_file.exists()
                                        }
                                        
                                        if poster_file.exists() and desc_file.exists():
                                            inspection_results['files_with_metadata'] += 1
                                        else:
                                            inspection_results['files_without_metadata'] += 1
                                            if not poster_file.exists():
                                                inspection_results['missing_posters'] += 1
                                            if not desc_file.exists():
                                                inspection_results['missing_descriptions'] += 1
                                                
                                        inspection_results['details'].append(file_info)
            
            # 영화 폴더 검사
            movie_dir = Path(target_root) / "영화"
            if movie_dir.exists():
                for movie_folder in movie_dir.iterdir():
                    if movie_folder.is_dir():
                        for file_path in movie_folder.iterdir():
                            if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.mkv', '.avi', '.mov']:
                                inspection_results['total_files'] += 1
                                
                                # 메타데이터 파일 확인
                                poster_file = movie_folder / "poster.jpg"
                                desc_file = movie_folder / "description.txt"
                                
                                file_info = {
                                    'file_path': str(file_path),
                                    'movie': movie_folder.name,
                                    'has_poster': poster_file.exists(),
                                    'has_description': desc_file.exists()
                                }
                                
                                if poster_file.exists() and desc_file.exists():
                                    inspection_results['files_with_metadata'] += 1
                                else:
                                    inspection_results['files_without_metadata'] += 1
                                    if not poster_file.exists():
                                        inspection_results['missing_posters'] += 1
                                    if not desc_file.exists():
                                        inspection_results['missing_descriptions'] += 1
                                        
                                inspection_results['details'].append(file_info)
            
            # 검사 결과 저장
            inspection_dir = Path("./scan_results")
            inspection_dir.mkdir(exist_ok=True)
            inspection_file = inspection_dir / f"metadata_inspection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(inspection_file, "w", encoding="utf-8") as f:
                json.dump(inspection_results, f, ensure_ascii=False, indent=2)
            
            # 결과 요약 로그
            total = inspection_results['total_files']
            with_meta = inspection_results['files_with_metadata']
            without_meta = inspection_results['files_without_metadata']
            missing_posters = inspection_results['missing_posters']
            missing_descriptions = inspection_results['missing_descriptions']
            
            self.status_panel.log_message(f"[검사] 메타데이터 검사 완료:")
            self.status_panel.log_message(f"  └─ 총 파일: {total}개")
            self.status_panel.log_message(f"  └─ 메타데이터 완전: {with_meta}개 ({with_meta/total*100:.1f}%)")
            self.status_panel.log_message(f"  └─ 메타데이터 불완전: {without_meta}개 ({without_meta/total*100:.1f}%)")
            self.status_panel.log_message(f"  └─ 포스터 누락: {missing_posters}개")
            self.status_panel.log_message(f"  └─ 설명 누락: {missing_descriptions}개")
            self.status_panel.log_message(f"  └─ 검사 결과 저장: {inspection_file}")
            
        except Exception as e:
            self.status_panel.log_message(f"[검사] 메타데이터 검사 중 오류 발생: {e}")
            self.logger.error(f"메타데이터 검사 오류: {e}")

    def _open_settings_dialog(self):
        dlg = SettingsDialog(self.config, self)
        dlg.exec()
        
    def _set_theme(self, theme: ThemeMode) -> None:
        """테마 설정"""
        try:
            self.theme_manager.set_theme(theme)
            self._update_theme_menu_state()
            self.logger.info(f"테마가 {theme.value}로 변경되었습니다.")
        except Exception as e:
            self.logger.error(f"테마 변경 실패: {e}")
            QMessageBox.critical(self, "테마 오류", f"테마 변경 실패:\n{translate_error(e)}")
            
    def _toggle_theme(self) -> None:
        """테마 토글"""
        try:
            self.theme_manager.toggle_theme()
            self._update_theme_menu_state()
            self.logger.info("테마가 토글되었습니다.")
        except Exception as e:
            self.logger.error(f"테마 토글 실패: {e}")
            QMessageBox.critical(self, "테마 오류", f"테마 토글 실패:\n{translate_error(e)}")
            
    def _update_theme_menu_state(self) -> None:
        """테마 메뉴 상태 업데이트"""
        current_theme = self.theme_manager.get_current_theme()
        
        # 모든 액션 체크 해제
        for action in self.theme_actions.values():
            action.setChecked(False)
            
        # 현재 테마 액션 체크
        if current_theme in self.theme_actions:
            self.theme_actions[current_theme].setChecked(True)
            
    def _open_source_folder(self):
        """소스 폴더 열기 (Ctrl+O)"""
        folder = QFileDialog.getExistingDirectory(self, "소스 폴더 선택")
        if folder:
            self.source_selector.set_path(folder)
            
    def _cancel_operation(self):
        """작업 취소"""
        # 스트리밍 처리 취소
        if hasattr(self, 'streaming_manager') and self.streaming_manager.is_processing():
            self.streaming_manager.cancel_processing()
            self.status_panel.log_message("사용자가 작업을 취소했습니다.")
            return
            
        # 기존 워커들 취소
        if hasattr(self, 'scan_worker') and self.scan_worker:
            self.scan_worker.stop()
            self.status_panel.log_message("파일 스캔이 취소되었습니다.")
            
        if hasattr(self, 'sync_worker') and self.sync_worker:
            # GroupSyncWorker는 취소 기능이 없으므로 로그만 출력
            self.status_panel.log_message("메타데이터 동기화는 취소할 수 없습니다.")
            
        # 상태 초기화
        self.status_panel.set_status("작업 취소됨")
        self.status_panel.set_progress(0)
        
        # 버튼 상태 복원
        self.control_panel.scan_button.setEnabled(True)
        self.control_panel.move_button.setEnabled(True)
        self.control_panel.cancel_button.setEnabled(False)
            
    def _on_files_dropped(self, dropped_files: list):
        """파일 목록 테이블에 드롭된 파일들 처리"""
        if not dropped_files:
            return
            
        # 비디오 파일 확장자 필터링
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.flv'}
        video_files = [f for f in dropped_files if f.suffix.lower() in video_extensions]
        
        if not video_files:
            QMessageBox.information(self, "안내", "드롭된 파일 중 비디오 파일이 없습니다.")
            return
            
        # 기존 파일 목록에 추가
        current_files = getattr(self, 'file_paths', [])
        new_files = [f for f in video_files if f not in current_files]
        
        if not new_files:
            QMessageBox.information(self, "안내", "모든 파일이 이미 목록에 있습니다.")
            return
            
        # 파일 목록 업데이트
        if not hasattr(self, 'file_paths'):
            self.file_paths = []
        self.file_paths.extend(new_files)
        
        # 테이블에 새 파일들 추가
        for file_path in new_files:
            self.file_list.add_file(file_path)
            
        # 상태 업데이트
        self.status_panel.log_message(f"드롭된 파일 {len(new_files)}개가 목록에 추가되었습니다.")
        self.status_panel.set_status(f"{len(new_files)}개 파일 추가됨")
        
        # 동기화 버튼 활성화 제거 (자동화됨)
    
    def dragEnterEvent(self, event):
        """드래그 진입 이벤트"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.logger.debug("드래그 진입: 파일/폴더 감지됨")
            self._update_drag_visual_feedback(True)
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """드래그 이동 이벤트"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """드래그 떠남 이벤트"""
        self._update_drag_visual_feedback(False)
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        """드롭 이벤트"""
        self._update_drag_visual_feedback(False)
        
        urls = event.mimeData().urls()
        
        if not urls:
            return
        
        # 첫 번째 URL만 처리 (소스 디렉토리로 설정)
        url = urls[0]
        local_path = url.toLocalFile()
        
        if not local_path:
            return
        
        path = Path(local_path)
        
        if path.is_dir():
            # 폴더인 경우 소스 디렉토리로 설정하고 자동 스캔 실행
            self.source_selector.set_path(str(path))
            self.logger.info(f"드롭된 폴더를 소스 디렉토리로 설정: {path}")
            self.status_panel.set_status(f"소스 폴더 설정됨: {path.name}")
            # 자동 스캔 실행
            self.status_panel.log_message(f"[자동] 드롭된 폴더 스캔 시작: {path.name}")
            self._scan_files()
        elif path.is_file():
            # 파일인 경우 부모 폴더를 소스 디렉토리로 설정하고 자동 스캔 실행
            parent_dir = path.parent
            self.source_selector.set_path(str(parent_dir))
            self.logger.info(f"드롭된 파일의 부모 폴더를 소스 디렉토리로 설정: {parent_dir}")
            self.status_panel.set_status(f"소스 폴더 설정됨: {parent_dir.name}")
            # 자동 스캔 실행
            self.status_panel.log_message(f"[자동] 드롭된 파일의 폴더 스캔 시작: {parent_dir.name}")
            self._scan_files()
        else:
            self.logger.warning(f"드롭된 경로가 유효하지 않음: {path}")
            self.status_panel.set_status("유효하지 않은 경로입니다")
            
    def _update_drag_visual_feedback(self, is_dragging: bool):
        """드래그 시각적 피드백 업데이트"""
        if is_dragging:
            # 드래그 오버 시 창 제목 변경
            original_title = getattr(self, '_original_title', self.windowTitle())
            if not hasattr(self, '_original_title'):
                self._original_title = original_title
            self.setWindowTitle(f"{original_title} - 파일을 여기에 드롭하세요")
        else:
            # 원래 제목으로 복원
            if hasattr(self, '_original_title'):
                self.setWindowTitle(self._original_title)
        
    def closeEvent(self, event):
        """창 닫기 이벤트 처리"""
        try:
            self.logger.info("AnimeSorter 종료 시작")
            
            # 설정 저장
            self._save_settings()
            
            # QThreadPool 정리
            from PyQt6.QtCore import QThreadPool
            thread_pool = QThreadPool.globalInstance()
            if thread_pool.activeThreadCount() > 0:
                self.logger.info(f"활성 스레드 {thread_pool.activeThreadCount()}개 정리 중...")
                thread_pool.waitForDone(3000)  # 3초 대기
                if thread_pool.activeThreadCount() > 0:
                    self.logger.warning(f"일부 스레드가 정리되지 않음: {thread_pool.activeThreadCount()}개")
            
            # 개별 QThread 정리
            if hasattr(self, 'active_threads') and self.active_threads:
                self.logger.info(f"개별 스레드 {len(self.active_threads)}개 정리 중...")
                for thread in self.active_threads[:]:  # 복사본으로 반복
                    if thread.isRunning():
                        thread.quit()
                        if not thread.wait(2000):  # 2초 대기
                            thread.terminate()  # 강제 종료
                            thread.wait(1000)   # 추가 대기
                    thread.deleteLater()
                self.active_threads.clear()
            
            # 캐시 시스템 정리
            if hasattr(self, 'cache_db'):
                try:
                    import asyncio
                    asyncio.run(self.cache_db.close())
                    self.logger.info("캐시 시스템 정리 완료")
                except Exception as e:
                    self.logger.error(f"캐시 시스템 정리 실패: {e}")
            
            # TMDB 제공자 정리
            if hasattr(self, 'tmdb_provider'):
                try:
                    import asyncio
                    asyncio.run(self.tmdb_provider.close())
                    self.logger.info("TMDB 제공자 정리 완료")
                except Exception as e:
                    self.logger.error(f"TMDB 제공자 정리 실패: {e}")
            
            self.logger.info("AnimeSorter 종료 완료")
            
        except Exception as e:
            self.logger.error(f"종료 중 오류 발생: {e}")
        finally:
            event.accept() 