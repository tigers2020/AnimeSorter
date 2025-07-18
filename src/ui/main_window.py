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
        # --- 병렬 TMDB 검색 ---
        async def fetch_all():
            tasks = [self.tmdb_provider.search(title, year) for (title, year, season) in self.group_keys]
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

class FileScanWorker(QRunnable):
    def __init__(self, file_paths, file_cleaner, config=None):
        super().__init__()
        self.signals = FileScanWorkerSignals()
        self.file_paths = file_paths
        self.file_cleaner = file_cleaner
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
        import threading
        from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
        
        MAX_WORKERS = min(8, os.cpu_count() or 4)
        start_time = time.time()
        
        total = len(self.file_paths)
        
        # 적응형 병렬 처리 전략: 파일 수에 따라 최적 방법 선택
        use_process_pool = total > 500  # 500개 이상일 때만 ProcessPoolExecutor 사용
        pool_type = "프로세스 풀" if use_process_pool else "스레드 풀"
        
        self.signals.log.emit(f"[벤치마크] 파일명 정제 및 그룹핑 시작: {total}개 파일 ({pool_type}: {MAX_WORKERS}개)")
        
        grouped_files = {}
        video_exts, subtitle_exts = self._get_ext_lists()
        clean_cache = {}
        file_name_list = []
        ext_type_list = []
        
        # 1단계: 파일 목록 준비 (즉시 진행률 표시)
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
        
        results = [None] * len(file_name_list)
        
        # 2단계: 적응형 병렬 파일명 정제
        media_files_count = sum(ext_type_list)
        completed_count = 0
        progress_lock = threading.Lock()
        
        def update_progress():
            """진행 상황 업데이트 (스레드 안전)"""
            nonlocal completed_count
            with progress_lock:
                completed_count += 1
                progress = 10 + int((completed_count / media_files_count) * 70)  # 10-80% 범위
                self.signals.progress.emit(progress, f"파일명 정제 중... ({completed_count}/{media_files_count}) [{pool_type}]")
        
        self.signals.progress.emit(10, f"파일명 정제 시작... (0/{media_files_count}) [{pool_type}]")
        
        try:
            if use_process_pool:
                # 대용량 파일: ProcessPoolExecutor 사용 (GIL 우회)
                with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    future_to_idx = {}
                    media_files = []
                    media_indices = []
                    
                    # 미디어 파일만 추출하여 배치 처리
                    for i in range(len(file_name_list)):
                        if ext_type_list[i]:
                            media_files.append(file_name_list[i])
                            media_indices.append(i)
                    
                    # 청크 단위로 제출하여 프로세스 간 통신 오버헤드 최소화
                    chunk_size = max(16, len(media_files) // (MAX_WORKERS * 2))  # 더 큰 청크 사용
                    self.signals.log.emit(f"[최적화] 청크 크기: {chunk_size}, 총 {len(media_files)}개 파일을 {MAX_WORKERS}개 프로세스로 처리")
                    
                    # 배치 작업 제출
                    for i in range(0, len(media_files), chunk_size):
                        if self._abort:
                            break
                        chunk_files = media_files[i:i+chunk_size]
                        chunk_indices = media_indices[i:i+chunk_size]
                        
                        for j, (file_path, original_idx) in enumerate(zip(chunk_files, chunk_indices)):
                            future = executor.submit(FileCleaner.clean_filename_static, file_path)
                            future_to_idx[future] = original_idx
                    
                    # 완료된 작업 처리
                    for future in as_completed(future_to_idx):
                        if self._abort:
                            self.signals.log.emit("[중단] 파일 정제 프로세스 풀 작업이 취소되었습니다.")
                            self.signals.finished.emit()
                            return
                            
                        idx = future_to_idx[future]
                        try:
                            clean = future.result()
                            results[idx] = clean
                            clean_cache[file_name_list[idx]] = clean
                            update_progress()
                        except Exception as e:
                            self.signals.log.emit(f"[프로세스 풀] {file_name_list[idx]}: 병렬 정제 오류: {e}")
                            update_progress()
            else:
                # 소용량 파일: ThreadPoolExecutor 사용 (오버헤드 최소)
                with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="cleaner") as executor:
                    future_to_idx = {}
                    
                    # 미디어 파일만 병렬 처리 제출
                    for i in range(len(file_name_list)):
                        if ext_type_list[i]:
                            future = executor.submit(FileCleaner.clean_filename_static, file_name_list[i])
                            future_to_idx[future] = i
                    
                    # 완료된 작업 처리 (실시간 진행률 업데이트)
                    for future in as_completed(future_to_idx):
                        if self._abort:
                            self.signals.log.emit("[중단] 파일 정제 스레드 풀 작업이 취소되었습니다.")
                            self.signals.finished.emit()
                            return
                            
                        idx = future_to_idx[future]
                        try:
                            clean = future.result()
                            results[idx] = clean
                            clean_cache[file_name_list[idx]] = clean
                            update_progress()  # 실시간 진행률 업데이트
                        except Exception as e:
                            self.signals.log.emit(f"[스레드 풀] {file_name_list[idx]}: 병렬 정제 오류: {e}")
                            update_progress()  # 오류가 있어도 진행률 업데이트
                        
        except Exception as e:
            self.signals.log.emit(f"{pool_type} 오류: {e}, 단일 프로세스 fallback")
            self.signals.progress.emit(15, "단일 프로세스로 파일명 정제 중...")
            
            # 단일 프로세스 fallback (진행률 표시)
            for i, file_name in enumerate(file_name_list):
                if self._abort:
                    self.signals.log.emit("[중단] 파일 정제 단일 작업이 취소되었습니다.")
                    self.signals.finished.emit()
                    return
                    
                if ext_type_list[i]:
                    try:
                        clean = FileCleaner.clean_filename_static(file_name)
                        results[i] = clean
                        clean_cache[file_name] = clean
                    except Exception as e:
                        self.signals.log.emit(f"{file_name}: 단일 정제 오류: {e}")
                    
                    # 단일 프로세스에서도 진행률 업데이트
                    completed_count += 1
                    progress = 15 + int((completed_count / media_files_count) * 65)  # 15-80% 범위
                    self.signals.progress.emit(progress, f"파일명 정제 중... ({completed_count}/{media_files_count})")
        
        # 3단계: 비미디어 파일 처리 (빠른 진행률 표시)
        self.signals.progress.emit(80, "비미디어 파일 처리 중...")
        from src.utils.file_cleaner import CleanResult
        
        for i, (file_name, is_media) in enumerate(zip(file_name_list, ext_type_list)):
            if self._abort:
                self.signals.log.emit("[중단] 그룹핑 작업이 취소되었습니다.")
                self.signals.finished.emit()
                return
                
            if not is_media:
                clean = CleanResult(
                    title="other",
                    original_filename=file_name,
                    season=1,
                    episode=None,
                    year=None,
                    is_movie=False,
                    extra_info={}
                )
                results[i] = clean
                clean_cache[file_name] = clean
        
        # 4단계: 그룹핑 (실시간 진행률 표시)
        self.signals.progress.emit(85, "파일 그룹핑 시작...")
        
        for idx, clean in enumerate(results):
            if self._abort:
                self.signals.log.emit("[중단] 그룹핑 결과 처리 작업이 취소되었습니다.")
                self.signals.finished.emit()
                return
                
            if clean is None:
                continue
                
            # dict/객체 모두 지원
            if isinstance(clean, dict):
                clean_title = clean.get("clean_title", clean.get("title", ""))
                year = clean.get("year", None)
                season = clean.get("season", 1)
            else:
                clean_title = getattr(clean, "title", "")
                year = getattr(clean, "year", None)
                season = getattr(clean, "season", 1)
                
            key = (clean_title.strip().lower(), year, season)
            grouped_files.setdefault(key, []).append(clean)
            
            # 그룹핑 진행률 업데이트 (85-100% 범위)
            progress = 85 + int((idx + 1) / total * 15)
            self.signals.progress.emit(progress, f"그룹핑 중... ({idx+1}/{total})")
            
            # 로그는 덜 자주 출력 (성능 최적화)
            if idx % max(1, total // 20) == 0 or idx == total - 1:
                self.signals.log.emit(f"[진행] {idx+1}/{total} 파일 그룹핑 중...")
        
        # 완료
        elapsed = time.time() - start_time
        speed = total / elapsed if elapsed > 0 else 0
        self.signals.log.emit(f"[벤치마크] 그룹핑 완료: {total}개 파일, {elapsed:.2f}초, 평균 {speed:.2f}개/초 [{pool_type} 최적화]")
        self.signals.progress.emit(100, f"완료! {total}개 파일 처리됨 ({speed:.1f}개/초)")
        
        self.signals.result.emit(grouped_files)
        self.signals.finished.emit()

class MainWindow(QMainWindow):
    """메인 애플리케이션 창"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnimeSorter")
        self.setMinimumSize(800, 600)
        
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
        self.threadpool = QThreadPool.globalInstance()
        
        # 스레드 추적 (QThread 정리용)
        self.active_threads = []
        
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
        self.control_panel.scan_button.clicked.connect(self._scan_files)
        self.control_panel.sync_button.clicked.connect(self._sync_metadata)
        self.control_panel.move_button.clicked.connect(self._move_files)
        
        # 디렉토리 선택기 연결
        self.source_selector.path_edit.textChanged.connect(self._on_source_dir_changed)
        self.target_selector.path_edit.textChanged.connect(self._on_target_dir_changed)
        
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
        """소스 디렉토리 변경 처리"""
        self.config.set("directories.source", path)
        
    def _on_target_dir_changed(self, path: str):
        """대상 디렉토리 변경 처리"""
        self.config.set("directories.target", path)
        
    def _scan_files(self):
        """
        소스 폴더의 파일들을 스캔하고 자동으로 정제
        같은 제목/연도는 하나의 row로 그룹핑 (백그라운드)
        zip 파일(.zip)은 별도 분리
        """
        source_dir = self.source_selector.get_path()
        if not source_dir:
            QMessageBox.warning(self, "경고", "소스 폴더를 선택해주세요.")
            return
        if not os.path.exists(source_dir):
            QMessageBox.warning(self, "경고", "소스 폴더가 존재하지 않습니다.")
            return
            
        # 스캔 시작 시간 기록
        self.scan_start_time = time.time()
            
        # 진행 상황 시각화 초기화
        self.status_panel.set_step_active("파일 스캔", True)
        self.status_panel.set_step_progress("파일 스캔", 0)
        self.status_panel.set_progress(0, "파일 스캔 중...")
            
        # os.scandir()를 사용한 최적화된 파일 탐색 (5배 빠름)
        file_paths = []
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
            
        worker = FileScanWorker(file_paths, self.file_cleaner, self.config)
        worker.signals.progress.connect(self._on_scan_progress)
        worker.signals.log.connect(self.status_panel.log_message)
        
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
            
    def _on_scan_finished(self):
        """스캔 완료 처리"""
        self.status_panel.set_progress(100, "스캔 완료")
        self.status_panel.set_step_completed("파일명 정제", True)
        self.status_panel.set_step_active("파일 스캔", False)

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
        self.control_panel.sync_button.setEnabled(has_files)
        
        # JSON 내보내기 메뉴 활성화
        if hasattr(self, 'export_current_action'):
            self.export_current_action.setEnabled(has_files)
        if hasattr(self, 'export_compressed_action'):
            self.export_compressed_action.setEnabled(has_files)
        
        self.status_panel.log_message(f"총 {self.file_list.rowCount()}개의 그룹(제목) 파일을 찾았습니다. (자동 정제 및 그룹핑 완료)")
        
        # --- 스캔 결과 JSON 저장 (개선된 버전) ---
        self._save_scan_results_to_json()
    
    def _save_scan_results_to_json(self):
        """스캔 결과를 JSON으로 저장"""
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
            
            # 스캔 소요 시간 계산
            scan_duration = time.time() - getattr(self, 'scan_start_time', time.time())
            
            # JSON 내보내기 실행
            saved_path = exporter.export_scan_results(
                grouped_files=self.grouped_files,
                source_directory=self.source_selector.get_path(),
                scan_duration=scan_duration,
                output_path=output_path,
                format=ExportFormat.JSON,
                include_metadata=True,
                compress=False
            )
            
            # 요약 정보 생성 및 로그 출력
            scan_data = exporter.load_scan_results(saved_path)
            summary = exporter.get_export_summary(scan_data)
            
            self.status_panel.log_message(f"✅ 스캔 결과 저장 완료: {saved_path}")
            self.status_panel.log_message(summary)
            
            # 압축 버전도 생성 (선택사항)
            compressed_path = exporter.export_scan_results(
                grouped_files=self.grouped_files,
                source_directory=self.source_selector.get_path(),
                scan_duration=scan_duration,
                output_path=output_path,
                format=ExportFormat.GZIPPED_JSON,
                include_metadata=True,
                compress=True
            )
            
            self.status_panel.log_message(f"📦 압축 버전 저장: {compressed_path}")
            
        except ImportError as e:
            self.status_panel.log_message(f"⚠️ JSON 내보내기 모듈을 찾을 수 없습니다: {e}")
            # 기존 방식으로 폴백
            self._save_scan_results_fallback()
        except Exception as e:
            self.status_panel.log_message(f"❌ 스캔 결과 저장 오류: {e}")
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
        """TMDB API를 통해 메타데이터 동기화 (백그라운드, 그룹별)"""
        # 메타데이터 검색 단계 활성화
        self.status_panel.set_step_active("메타데이터 검색", True)
        self.status_panel.set_step_progress("메타데이터 검색", 0)
        self.status_panel.set_status("TMDB 메타데이터 동기화 중...")
        self.status_panel.set_progress(0)
        self.status_panel.log_message("동기화 시작")
        
        group_keys = list(self.grouped_files.keys())
        
        # ETA 추적 시작
        self.status_panel.start_tracking(len(group_keys))
        
        worker = GroupSyncWorker(group_keys, self.tmdb_provider)
        worker.signals.progress.connect(self._on_sync_progress)
        worker.signals.log.connect(self.status_panel.log_message)
        worker.signals.error.connect(self.status_panel.log_message)
        worker.signals.result.connect(self._on_group_sync_result)
        worker.signals.finished.connect(self._on_sync_finished)
        self.threadpool.start(worker)
        
    def _on_sync_progress(self, percent: int, message: str):
        """메타데이터 동기화 진행률 업데이트"""
        self.status_panel.set_progress(percent, message)
        self.status_panel.set_step_progress("메타데이터 검색", percent)
        self.status_panel.update_progress(int(percent * len(self.grouped_files) / 100) if hasattr(self, 'grouped_files') else 0)

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
        self.status_panel.set_status("TMDB 동기화 완료")
        self.status_panel.log_message("동기화 종료")
        self.status_panel.set_step_completed("메타데이터 검색", True)
        self.status_panel.set_step_active("메타데이터 검색", False)
        self.control_panel.move_button.setEnabled(True)
        
    def _move_files(self):
        """파일 이동 처리"""
        if not self.grouped_files:
            QMessageBox.warning(self, "경고", "이동할 파일이 없습니다.")
            return
            
        target_root = self.target_selector.get_path()
        if not target_root:
            QMessageBox.warning(self, "경고", "대상 폴더를 선택해주세요.")
            return
            
        # 파일 이동 단계 활성화
        self.status_panel.set_step_active("파일 이동", True)
        self.status_panel.set_step_progress("파일 이동", 0)
        self.status_panel.set_status("파일 이동 중...")
        self.status_panel.set_progress(0)
        
        # 총 파일 수 계산
        total_files = sum(len(group) for group in self.grouped_files.values())
        self.status_panel.start_tracking(total_files)
            
        # 덮어쓰기 확인
        overwrite_existing = QMessageBox.question(
            self, "확인", "기존 파일이 있을 경우 덮어쓰시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes
            
        def get_unique_filename(target_path):
            """중복 파일명 처리"""
            if not target_path.exists():
                return target_path
            counter = 1
            while True:
                stem = target_path.stem
                suffix = target_path.suffix
                new_name = f"{stem}_{counter}{suffix}"
                new_path = target_path.parent / new_name
                if not new_path.exists():
                    return new_path
                counter += 1
                
        for (title, year), group in self.grouped_files.items():
            meta = self.file_metadata.get((title, year))
            if meta:
                korean_title = meta.get('name') or meta.get('title') or title
                # 미디어 타입 확인 (tv: 애니메이션, movie: 영화)
                media_type = meta.get('media_type', 'tv')  # 기본값은 tv (애니메이션)
            else:
                korean_title = title
                media_type = 'tv'  # 메타데이터가 없으면 기본적으로 애니메이션으로 분류
                
            korean_title = sanitize_folder_name(korean_title)
            
            def get_resolution(file):
                m = re.search(r'(\d{3,4})p', str(file.original_filename))
                return int(m.group(1)) if m else 0
            resolutions = [get_resolution(f) for f in group]
            max_res = max(resolutions) if resolutions else 0
            for file in group:
                res = get_resolution(file)
                src = Path(file.original_filename)
                season = getattr(file, "season", 1)
                # 시즌이 리스트면 첫 번째 값만 사용, int가 아니면 1로 fallback
                if isinstance(season, list):
                    season = season[0] if season else 1
                try:
                    season = int(season)
                except Exception:
                    season = 1
                ext = src.suffix.lower()
                # 압축 파일 확장자 목록
                archive_exts = ['.zip', '.rar', '.7z']
                if ext in archive_exts:
                    # 자막 폴더로 이동
                    dst = Path(target_root) / "자막" / src.name
                    try:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 중복 파일 처리
                        if dst.exists() and not overwrite_existing:
                            dst = get_unique_filename(dst)
                            self.status_panel.log_message(f"[자막 이동] 중복 파일명 변경: {src.name} → {dst.name}")
                        
                        shutil.move(str(src), str(dst))
                        self.status_panel.log_message(f"[자막 이동] {src} → {dst}")
                    except Exception as e:
                        self.status_panel.log_message(f"[자막 이동 실패] {src}: {e}")
                elif res == max_res:
                    # 미디어 타입에 따라 폴더 분리
                    if media_type == "movie":
                        # 영화: 영화 폴더에 저장
                        dst = Path(target_root) / "영화" / korean_title / src.name
                    else:
                        # 애니메이션 (tv): 애니메이션 폴더에 시즌별로 저장
                        dst = Path(target_root) / "애니메이션" / korean_title / f"Season {season}" / src.name
                        
                    try:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 중복 파일 처리
                        if dst.exists() and not overwrite_existing:
                            dst = get_unique_filename(dst)
                            self.status_panel.log_message(f"[이동] 중복 파일명 변경: {src.name} → {dst.name}")
                        
                        shutil.move(str(src), str(dst))
                        self.status_panel.log_message(f"[이동 완료] {src} → {dst}")
                        # --- 포스터 및 설명 저장 ---
                        if meta:
                            # 1. 포스터 저장
                            poster_path_val = meta.get("poster_path")
                            if poster_path_val:
                                poster_url = f"https://image.tmdb.org/t/p/w342{poster_path_val}"
                                poster_file = dst.parent / "poster.jpg"
                                if not poster_file.exists():
                                    try:
                                        resp = requests.get(poster_url, timeout=10)
                                        if resp.status_code == 200:
                                            with open(poster_file, "wb") as f:
                                                f.write(resp.content)
                                            self.status_panel.log_message(f"[포스터 저장] {poster_file}")
                                        else:
                                            self.status_panel.log_message(f"[포스터 다운로드 실패] {poster_url} ({resp.status_code})")
                                    except Exception as e:
                                        self.status_panel.log_message(f"[포스터 저장 오류] {poster_url}: {e}")
                            # 2. 설명 저장
                            overview = meta.get("overview")
                            if overview:
                                desc_file = dst.parent / "description.txt"
                                if not desc_file.exists():
                                    try:
                                        with open(desc_file, "w", encoding="utf-8") as f:
                                            f.write(overview)
                                        self.status_panel.log_message(f"[설명 저장] {desc_file}")
                                    except Exception as e:
                                        self.status_panel.log_message(f"[설명 저장 오류] {desc_file}: {e}")
                        # --- 끝 ---
                    except Exception as e:
                        self.status_panel.log_message(f"[이동 실패] {src}: {e}")
                else:
                    # 저해상도 파일도 미디어 타입에 따라 분리
                    if media_type == "movie":
                        dst = Path(target_root) / "영화" / "저해상도" / src.name
                    else:
                        dst = Path(target_root) / "애니메이션" / "저해상도" / src.name
                        
                    try:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 중복 파일 처리
                        if dst.exists() and not overwrite_existing:
                            dst = get_unique_filename(dst)
                            self.status_panel.log_message(f"[저해상도 이동] 중복 파일명 변경: {src.name} → {dst.name}")
                        
                        shutil.move(str(src), str(dst))
                        self.status_panel.log_message(f"[저해상도 이동] {src} → {dst}")
                    except Exception as e:
                        self.status_panel.log_message(f"[저해상도 이동 실패] {src}: {e}")
        self.status_panel.log_message("모든 파일 이동 완료.")
        
        # 파일 이동 완료 - 진행률 업데이트
        self.status_panel.set_progress(100, "파일 이동 완료")
        self.status_panel.set_step_completed("파일 이동", True)
        self.status_panel.set_step_active("파일 이동", False)
        
        # 이동 후 빈 폴더 삭제
        # 소스 디렉토리 경로 추출 (예: self.source_selector.get_path())
        source_root = self.source_selector.get_path() if hasattr(self, 'source_selector') else None
        if source_root:
            import os
            from pathlib import Path
            # 하위 폴더부터 재귀적으로 탐색하여 빈 폴더 삭제
            for dirpath, dirnames, filenames in os.walk(source_root, topdown=False):
                p = Path(dirpath)
                # 파일과 하위 폴더가 모두 없으면 삭제
                if not list(p.iterdir()):
                    try:
                        p.rmdir()
                        self.status_panel.log_message(f"[빈 폴더 삭제] {p}")
                    except Exception as e:
                        self.status_panel.log_message(f"[빈 폴더 삭제 실패] {p}: {e}")
                        
    async def _move_files_async(self, group_metadata, target_root, overwrite_existing):
        """비동기 파일 이동 처리"""
        try:
            # 파일 작업 목록 생성
            operations = []
            
            for (title, year, season), group in self.grouped_files.items():
                meta = group_metadata.get((title, year, season))
                if meta:
                    korean_title = meta.get('name') or meta.get('title') or title
                    # 미디어 타입 확인 (tv: 애니메이션, movie: 영화)
                    media_type = meta.get('media_type', 'tv')  # 기본값은 tv (애니메이션)
                else:
                    korean_title = title
                    media_type = 'tv'  # 메타데이터가 없으면 기본적으로 애니메이션으로 분류
                    
                korean_title = sanitize_folder_name(korean_title)
                
                def get_resolution(file):
                    m = re.search(r'(\d{3,4})p', str(file.original_filename))
                    return int(m.group(1)) if m else 0
                    
                resolutions = [get_resolution(f) for f in group]
                max_res = max(resolutions) if resolutions else 0
                
                for file in group:
                    res = get_resolution(file)
                    src = Path(file.original_filename)
                    season = getattr(file, "season", 1)
                    
                    # 시즌이 리스트면 첫 번째 값만 사용, int가 아니면 1로 fallback
                    if isinstance(season, list):
                        season = season[0] if season else 1
                    try:
                        season = int(season)
                    except Exception:
                        season = 1
                        
                    ext = src.suffix.lower()
                    # 압축 파일 확장자 목록
                    archive_exts = ['.zip', '.rar', '.7z']
                    
                    if ext in archive_exts:
                        # 자막 폴더로 이동
                        dst = Path(target_root) / "자막" / src.name
                        operation = FileOperation(
                            source=src,
                            target=dst,
                            operation_type="move",
                            metadata={"type": "subtitle", "original_name": src.name}
                        )
                        operations.append(operation)
                        
                    elif res == max_res:
                        # 미디어 타입에 따라 폴더 분리
                        if media_type == "movie":
                            # 영화: 영화 폴더에 저장
                            dst = Path(target_root) / "영화" / korean_title / src.name
                        else:
                            # 애니메이션 (tv): 애니메이션 폴더에 시즌별로 저장
                            dst = Path(target_root) / "애니메이션" / korean_title / f"Season {season}" / src.name
                            
                        operation = FileOperation(
                            source=src,
                            target=dst,
                            operation_type="move",
                            metadata={
                                "type": "main_content",
                                "media_type": media_type,
                                "title": korean_title,
                                "season": season,
                                "resolution": res,
                                "meta": meta
                            }
                        )
                        operations.append(operation)
                        
                    else:
                        # 저해상도 파일도 미디어 타입에 따라 분리
                        if media_type == "movie":
                            dst = Path(target_root) / "영화" / "저해상도" / src.name
                        else:
                            dst = Path(target_root) / "애니메이션" / "저해상도" / src.name
                            
                        operation = FileOperation(
                            source=src,
                            target=dst,
                            operation_type="move",
                            metadata={"type": "low_resolution", "media_type": media_type, "original_name": src.name}
                        )
                        operations.append(operation)
                        
            # 비동기 파일 관리자로 처리
            async with AsyncFileManager(max_workers=4) as file_manager:
                def progress_callback(current, total, message):
                    percent = int((current / total) * 100) if total > 0 else 0
                    self.status_panel.set_progress(percent, message)
                    
                results = await file_manager.process_files_batch(operations, progress_callback)
                
            # 결과 로깅
            self.status_panel.log_message(f"파일 이동 완료: {results['completed']}/{results['total']} 성공")
            
            # 포스터 및 설명 저장 (비동기)
            await self._save_metadata_async(group_metadata, target_root)
            
            # 빈 폴더 정리
            source_root = self.source_selector.get_path() if hasattr(self, 'source_selector') else None
            if source_root:
                async with AsyncFileManager() as file_manager:
                    cleaned_count = await file_manager.cleanup_empty_directories(Path(source_root))
                    if cleaned_count > 0:
                        self.status_panel.log_message(f"빈 폴더 {cleaned_count}개 정리 완료")
                        
        except Exception as e:
            self.status_panel.log_message(f"파일 이동 중 오류 발생: {e}")
            raise
            
    async def _save_metadata_async(self, group_metadata, target_root):
        """메타데이터를 비동기로 저장"""
        import aiofiles
        import requests
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            for (title, year, season), meta in group_metadata.items():
                if not meta:
                    continue
                    
                korean_title = meta.get('name') or meta.get('title') or title
                korean_title = sanitize_folder_name(korean_title)
                
                # 포스터 저장
                poster_path_val = meta.get("poster_path")
                if poster_path_val:
                    poster_url = f"https://image.tmdb.org/t/p/w342{poster_path_val}"
                    poster_file = Path(target_root) / korean_title / "poster.jpg"
                    
                    if not poster_file.exists():
                        try:
                            async with session.get(poster_url) as resp:
                                if resp.status == 200:
                                    poster_file.parent.mkdir(parents=True, exist_ok=True)
                                    async with aiofiles.open(poster_file, 'wb') as f:
                                        await f.write(await resp.read())
                                    self.status_panel.log_message(f"[포스터 저장] {poster_file}")
                        except Exception as e:
                            self.status_panel.log_message(f"[포스터 저장 오류] {poster_url}: {e}")
                            
                # 설명 저장
                overview = meta.get("overview")
                if overview:
                    desc_file = Path(target_root) / korean_title / "description.txt"
                    if not desc_file.exists():
                        try:
                            desc_file.parent.mkdir(parents=True, exist_ok=True)
                            async with aiofiles.open(desc_file, 'w', encoding='utf-8') as f:
                                await f.write(overview)
                            self.status_panel.log_message(f"[설명 저장] {desc_file}")
                        except Exception as e:
                            self.status_panel.log_message(f"[설명 저장 오류] {desc_file}: {e}")
        
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
        """작업 취소 (Esc)"""
        # 현재 진행 중인 작업이 있는지 확인
        if hasattr(self, 'active_threads') and self.active_threads:
            reply = QMessageBox.question(
                self, "작업 취소", 
                "진행 중인 작업을 취소하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # 모든 활성 스레드 중지
                for thread in self.active_threads[:]:
                    if hasattr(thread, 'stop'):
                        thread.stop()
                    thread.quit()
                    thread.wait(1000)  # 1초 대기
                    if thread.isRunning():
                        thread.terminate()
                self.active_threads.clear()
                self.status_panel.set_status("작업이 취소되었습니다.")
                self.status_panel.set_progress(0, "취소됨")
        else:
            self.status_panel.set_status("취소할 작업이 없습니다.")
    
    def dragEnterEvent(self, event):
        """드래그 진입 이벤트"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.logger.debug("드래그 진입: 파일/폴더 감지됨")
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """드래그 이동 이벤트"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """드롭 이벤트"""
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
            # 폴더인 경우 소스 디렉토리로 설정
            self.source_selector.set_path(str(path))
            self.logger.info(f"드롭된 폴더를 소스 디렉토리로 설정: {path}")
            self.status_panel.set_status(f"소스 폴더 설정됨: {path.name}")
        elif path.is_file():
            # 파일인 경우 부모 폴더를 소스 디렉토리로 설정
            parent_dir = path.parent
            self.source_selector.set_path(str(parent_dir))
            self.logger.info(f"드롭된 파일의 부모 폴더를 소스 디렉토리로 설정: {parent_dir}")
            self.status_panel.set_status(f"소스 폴더 설정됨: {parent_dir.name}")
        else:
            self.logger.warning(f"드롭된 경로가 유효하지 않음: {path}")
            self.status_panel.set_status("유효하지 않은 경로입니다")
        
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