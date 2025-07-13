import os
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
from thefuzz import fuzz
from concurrent.futures import ThreadPoolExecutor, as_completed

from .widgets import DirectorySelector, StatusPanel, FileListTable, ControlPanel
from .widgets.settings_dialog import SettingsDialog
from ..config.config_manager import ConfigManager
from ..utils.file_cleaner import FileCleaner
from src.plugin.tmdb.provider import TMDBProvider

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
        import time
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
        import asyncio, time
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        total = len(self.group_keys)
        group_metadata = {}
        prev_title = None
        prev_meta = None
        # --- 병렬 TMDB 검색 ---
        async def fetch_all():
            tasks = [self.tmdb_provider.search(title, year) for (title, year) in self.group_keys]
            return await asyncio.gather(*tasks, return_exceptions=True)
        t0 = time.time()
        results = loop.run_until_complete(fetch_all())
        t1 = time.time()
        for idx, ((title, year), result) in enumerate(zip(self.group_keys, results)):
            if isinstance(result, Exception):
                self.signals.error.emit(f"'{title}' TMDB 오류: {result}")
                group_metadata[(title, year)] = None
                continue
            self.signals.log.emit(f"[{idx+1}/{total}] '{title}'({year if year else 'any'}) TMDB 검색 완료 (병렬, {t1-t0:.2f}s)")
            group_metadata[(title, year)] = result
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
        loop.run_until_complete(self.tmdb_provider.close())
        loop.close()

class FileScanWorkerSignals(QObject):
    progress = pyqtSignal(int, str)
    log = pyqtSignal(str)
    result = pyqtSignal(dict)
    finished = pyqtSignal()

class FileScanWorker(QRunnable):
    def __init__(self, file_paths, export_dir, file_cleaner, config=None):
        super().__init__()
        self.signals = FileScanWorkerSignals()
        self.file_paths = file_paths
        self.export_dir = export_dir
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
        import time
        MAX_WORKERS = min(8, os.cpu_count() or 4)
        start_time = time.time()
        self.signals.log.emit(f"[벤치마크] 파일명 정제 및 그룹핑 시작: {len(self.file_paths)}개 파일")
        grouped_files = {}
        total = len(self.file_paths)
        video_exts, subtitle_exts = self._get_ext_lists()
        clean_cache = {}
        file_name_list = []
        ext_type_list = []
        for file_path in self.file_paths:
            if self._abort:
                self.signals.log.emit("[중단] 파일 스캔이 취소되었습니다.")
                self.signals.finished.emit()
                return
            ext = Path(file_path).suffix.lower()
            file_name = str(file_path)
            is_media = ext in video_exts or ext in subtitle_exts
            file_name_list.append(file_name)
            ext_type_list.append(is_media)
        results = [None] * len(file_name_list)
        try:
            # QRunnable(이미 QThreadPool에서 실행) 내부에서 ThreadPoolExecutor를 사용할 때
            # 반드시 max_workers 제한 필요. 중첩 풀 구조는 피하고, 필요시 QThreadPool 재사용 권장.
            # (현재는 I/O-bound라 ThreadPoolExecutor로 충분, CPU-bound면 ProcessPoolExecutor 고려)
            with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="cleaner") as executor:
                future_to_idx = {executor.submit(FileCleaner.clean_filename_static, file_name_list[i]): i for i in range(len(file_name_list)) if ext_type_list[i]}
                for future in as_completed(future_to_idx):
                    if self._abort:
                        self.signals.log.emit("[중단] 파일 정제 병렬 작업이 취소되었습니다.")
                        self.signals.finished.emit()
                        return
                    idx = future_to_idx[future]
                    try:
                        clean = future.result()
                        results[idx] = clean
                        clean_cache[file_name_list[idx]] = clean
                    except Exception as e:
                        self.signals.log.emit(f"[cleaner-thread] {file_name_list[idx]}: 병렬 정제 오류: {e}")
        except Exception as e:
            self.signals.log.emit(f"멀티스레딩 오류: {e}, 단일 프로세스 fallback")
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
        for idx, clean in enumerate(results):
            if self._abort:
                self.signals.log.emit("[중단] 그룹핑 결과 처리 작업이 취소되었습니다.")
                self.signals.finished.emit()
                return
            if clean is None:
                continue
            # dict/객체 모두 지원
            if isinstance(clean, dict):
                clean_title = clean.get("title", "")
                year = clean.get("year", None)
            else:
                clean_title = getattr(clean, "title", "")
                year = getattr(clean, "year", None)
            key = (clean_title.strip().lower(), year)
            grouped_files.setdefault(key, []).append(clean)
            if idx % max(1, total // 10) == 0 or idx == total - 1:
                self.signals.log.emit(f"[진행] {idx+1}/{total} 파일 그룹핑 중...")
            self.signals.progress.emit(int((idx+1)/total*100), f"{idx+1}/{total} 파일 처리 중...")
        elapsed = time.time() - start_time
        speed = total / elapsed if elapsed > 0 else 0
        self.signals.log.emit(f"[벤치마크] 그룹핑 완료: {total}개 파일, {elapsed:.2f}초, 평균 {speed:.2f}개/초")
        self.signals.result.emit(grouped_files)
        self.signals.finished.emit()

class MainWindow(QMainWindow):
    """메인 애플리케이션 창"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnimeSorter")
        self.setMinimumSize(800, 600)
        
        # 설정 관리자 초기화
        self.config = ConfigManager()
        
        # 파일명 정제 유틸리티 초기화
        self.file_cleaner = FileCleaner(self.config)
        
        # TMDBProvider 초기화
        self.tmdb_provider = TMDBProvider(
            api_key=self.config.get("tmdb.api_key", ""),
            language=self.config.get("tmdb.language", "ko-KR")
        )
        
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
        
    def _setup_ui(self):
        """UI 요소 생성 및 배치"""
        # 메뉴바 추가
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("설정")
        settings_action = settings_menu.addAction("설정...")
        settings_action.triggered.connect(self._open_settings_dialog)
        
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
        file_paths = []
        self.zip_files = []
        for root, dirs, files in os.walk(source_dir):
            for fname in files:
                path = Path(root) / fname
                if path.suffix.lower() == ".zip":
                    self.zip_files.append(path)
                else:
                    file_paths.append(path)
        if not file_paths:
            QMessageBox.information(self, "안내", "파일이 없습니다.")
            return
        self.status_panel.log_message(f"[스캔] 총 {len(file_paths)}개 파일 스캔 시작... (zip 파일 {len(self.zip_files)}개 분리)")
        if self.zip_files:
            self.status_panel.log_message(f"[스캔] 분리된 zip 파일: {[str(z) for z in self.zip_files]}")
        export_dir = "./tmdb_exports"
        worker = FileScanWorker(file_paths, export_dir, self.file_cleaner, self.config)
        worker.signals.progress.connect(lambda p, m: self.status_panel.set_progress(p, m))
        worker.signals.log.connect(self.status_panel.log_message)
        def on_result(grouped_files):
            self.grouped_files = grouped_files
            self._update_table_from_grouped_files()
        worker.signals.result.connect(on_result)
        worker.signals.finished.connect(lambda: self.status_panel.set_progress(100, "스캔 완료"))
        self.threadpool.start(worker)

    def _update_table_from_grouped_files(self):
        """grouped_files 데이터를 테이블에 반영 및 json 저장"""
        self.file_list.setRowCount(0)
        for (title, year), results in self.grouped_files.items():
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
        self.status_panel.log_message(f"총 {self.file_list.rowCount()}개의 그룹(제목) 파일을 찾았습니다. (자동 정제 및 그룹핑 완료)")
        # --- 스캔 결과 json 저장 ---
        try:
            save_dir = Path("./scan_results")
            save_dir.mkdir(exist_ok=True)
            save_path = save_dir / f"scan_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            # json 직렬화: grouped_files를 dict로 변환
            serializable = {}
            for (title, year), results in self.grouped_files.items():
                serializable_key = f"{title}__{year if year else ''}"
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
            self.status_panel.log_message(f"스캔 결과 저장: {save_path}")
        except Exception as e:
            self.status_panel.log_message(f"스캔 결과 저장 오류: {e}")

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
        self.status_panel.set_status("TMDB 메타데이터 동기화 중...")
        self.status_panel.set_progress(0)
        self.status_panel.log_message("동기화 시작")
        group_keys = list(self.grouped_files.keys())
        worker = GroupSyncWorker(group_keys, self.tmdb_provider)
        worker.signals.progress.connect(self.status_panel.set_progress)
        worker.signals.log.connect(self.status_panel.log_message)
        worker.signals.error.connect(self.status_panel.log_message)
        worker.signals.result.connect(self._on_group_sync_result)
        worker.signals.finished.connect(self._on_sync_finished)
        self.threadpool.start(worker)

    def _on_group_sync_result(self, group_metadata):
        self.group_metadata = group_metadata
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
            # 포스터 이미지
            poster_url = None
            if result and result.get("poster_path"):
                poster_url = f"https://image.tmdb.org/t/p/w185{result['poster_path']}"
            if poster_url:
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
                            self.status_panel.log_message(f"이미지 로드 실패: {poster_url}")
                    else:
                        self.file_list.setItem(row, 6, QTableWidgetItem("이미지 오류(HTTP)"))
                        self.status_panel.log_message(f"이미지 HTTP 오류 {response.status_code}: {poster_url}")
                except Exception as e:
                    self.file_list.setItem(row, 6, QTableWidgetItem("이미지 오류(예외)"))
                    self.status_panel.log_message(f"이미지 예외: {poster_url} {e}")
            else:
                self.file_list.setItem(row, 6, QTableWidgetItem(""))
            # 줄거리(overview)
            overview = result.get("overview") if result else None
            self.file_list.setItem(row, 7, QTableWidgetItem(overview or ""))
            # 이동 위치 경로(메타 동기화 후)
            # title, season 정보로 이동 경로 계산
            title_for_path = new_title or key[0]
            season = key[1] or 1
            target_root = self.target_selector.get_path() if hasattr(self, 'target_selector') else self.target_dir
            if target_root:
                from pathlib import Path
                target_path = Path(target_root) / str(title_for_path) / f"Season {season}"
                self.file_list.setItem(row, 8, QTableWidgetItem(str(target_path)))

    def _on_sync_finished(self):
        self.status_panel.set_status("TMDB 동기화 완료")
        self.status_panel.log_message("동기화 종료")
        self.control_panel.move_button.setEnabled(True)
        
    def _move_files(self):
        """파일들을 대상 폴더로 이동 (메타데이터 한글 제목 기반, 해상도/시즌 분기 포함)"""
        import shutil
        from pathlib import Path
        group_metadata = getattr(self, 'group_metadata', None)
        if group_metadata is None:
            self.status_panel.log_message("TMDB 메타데이터가 없습니다. 먼저 동기화하세요.")
            return
        target_root = self.target_selector.get_path()
        for (title, year), group in self.grouped_files.items():
            meta = group_metadata.get((title, year))
            if meta:
                korean_title = meta.get('name') or meta.get('title') or title
            else:
                korean_title = title
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
                        shutil.move(str(src), str(dst))
                        self.status_panel.log_message(f"[자막 이동] {src} → {dst}")
                    except Exception as e:
                        self.status_panel.log_message(f"[자막 이동 실패] {src}: {e}")
                elif res == max_res:
                    dst = Path(target_root) / korean_title / f"Season {season}" / src.name
                    try:
                        dst.parent.mkdir(parents=True, exist_ok=True)
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
                    dst = Path(target_root) / "저해상도" / src.name
                    try:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(src), str(dst))
                        self.status_panel.log_message(f"[저해상도 이동] {src} → {dst}")
                    except Exception as e:
                        self.status_panel.log_message(f"[저해상도 이동 실패] {src}: {e}")
        self.status_panel.log_message("모든 파일 이동 완료.")
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
        
    def _open_settings_dialog(self):
        dlg = SettingsDialog(self.config, self)
        dlg.exec()
        
    def closeEvent(self, event):
        """창 닫기 이벤트 처리"""
        # 설정 저장
        self._save_settings()
        event.accept() 