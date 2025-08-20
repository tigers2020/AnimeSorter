"""
리팩토링된 메인 윈도우 - AnimeSorter의 주요 GUI 인터페이스
컴포넌트 기반 아키텍처로 재구성되어 가독성과 유지보수성이 향상되었습니다.
"""

import os
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHeaderView,  # Added for QHeaderView
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

# New Architecture Components
from app import (
    ErrorMessageEvent,
    FileCountUpdateEvent,
    FilesScannedEvent,
    IFileScanService,
    IUIUpdateService,
    MemoryUsageUpdateEvent,
    ProgressUpdateEvent,
    ScanStatus,
    # UI 이벤트들
    StatusBarUpdateEvent,
    SuccessMessageEvent,
    TaskCancelledEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskProgressEvent,
    TaskStartedEvent,
    get_event_bus,
    get_service,
)
from core.file_manager import FileManager

# Local imports
from core.file_parser import FileParser
from core.settings_manager import SettingsManager
from core.tmdb_client import TMDBClient

# UI Components
from .components import LeftPanel, MainToolbar, ResultsView, RightPanel, SettingsDialog
from .components.organize_preflight_dialog import OrganizePreflightDialog
from .components.organize_progress_dialog import OrganizeProgressDialog
from .components.tmdb_search_dialog import TMDBSearchDialog

# Data Models
from .managers.anime_data_manager import AnimeDataManager, ParsedItem
from .managers.file_processing_manager import FileProcessingManager
from .managers.tmdb_manager import TMDBManager

# Table Models
from .table_models import DetailFileModel, GroupedListModel


class MainWindow(QMainWindow):
    """AnimeSorter 메인 윈도우 (리팩토링된 버전)"""

    def __init__(self):
        super().__init__()

        # 더미 스캔 방지를 위한 플래그 초기화
        self.tmdb_search_completed = False

        # 새로운 아키텍처 관련 초기화
        self.event_bus = None
        self.file_scan_service = None
        self.ui_update_service = None
        self.current_scan_id = None

        # 핵심 컴포넌트 초기화
        self.init_core_components()

        # 데이터 관리자 초기화
        self.init_data_managers()

        # TMDB 검색 다이얼로그 초기화
        self.tmdb_search_dialogs = {}  # 그룹별 검색 다이얼로그 저장

        # 초기 데이터 설정
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
            api_key = self.settings_manager.get_setting("tmdb_api_key") or os.getenv("TMDB_API_KEY")
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
            dest_root = self.settings_manager.get_setting("destination_root", "")
            safe_mode = self.settings_manager.get_setting("safe_mode", True)
            self.file_manager = FileManager(destination_root=dest_root, safe_mode=safe_mode)

            # FileManager 설정 적용
            naming_scheme = self.settings_manager.get_setting("naming_scheme", "standard")
            self.file_manager.set_naming_scheme(naming_scheme)

            # 새로운 아키텍처 컴포넌트 초기화
            self.init_new_architecture()

            # 설정을 UI 컴포넌트에 적용
            self.apply_settings_to_ui()

            print("✅ 핵심 컴포넌트 초기화 완료")

        except Exception as e:
            print(f"❌ 핵심 컴포넌트 초기화 실패: {e}")
            self.file_parser = None
            self.tmdb_client = None
            self.file_manager = None

    def init_new_architecture(self):
        """새로운 아키텍처 컴포넌트 초기화"""
        try:
            # EventBus 가져오기 (전역 인스턴스)
            self.event_bus = get_event_bus()
            print(f"✅ EventBus 연결됨: {id(self.event_bus)}")

            # FileScanService 가져오기 (DI Container에서)
            self.file_scan_service = get_service(IFileScanService)
            print(f"✅ FileScanService 연결됨: {id(self.file_scan_service)}")

            # UIUpdateService 가져오기 (DI Container에서)
            self.ui_update_service = get_service(IUIUpdateService)
            print(f"✅ UIUpdateService 연결됨: {id(self.ui_update_service)}")

            # UIUpdateService 초기화 (MainWindow 전달)
            self.ui_update_service.initialize(self)
            print("✅ UIUpdateService 초기화 완료")

            # 이벤트 구독 설정
            self.setup_event_subscriptions()

            print("✅ 새로운 아키텍처 컴포넌트 초기화 완료")

        except Exception as e:
            print(f"❌ 새로운 아키텍처 초기화 실패: {e}")
            # 기본값으로 설정 (기존 동작 유지)
            self.event_bus = None
            self.file_scan_service = None
            self.ui_update_service = None

    def setup_event_subscriptions(self):
        """이벤트 구독 설정"""
        if not self.event_bus:
            return

        try:
            # FilesScannedEvent 구독
            self.event_bus.subscribe(
                FilesScannedEvent,
                self.on_files_scanned,
                weak_ref=False,  # MainWindow가 존재하는 동안 구독 유지
            )
            print("✅ 파일 스캔 이벤트 구독 설정")

            # 백그라운드 작업 이벤트 구독
            self.event_bus.subscribe(TaskStartedEvent, self.on_task_started, weak_ref=False)
            self.event_bus.subscribe(TaskProgressEvent, self.on_task_progress, weak_ref=False)
            self.event_bus.subscribe(TaskCompletedEvent, self.on_task_completed, weak_ref=False)
            self.event_bus.subscribe(TaskFailedEvent, self.on_task_failed, weak_ref=False)
            self.event_bus.subscribe(TaskCancelledEvent, self.on_task_cancelled, weak_ref=False)
            print("✅ 백그라운드 작업 이벤트 구독 설정")

        except Exception as e:
            print(f"❌ 이벤트 구독 설정 실패: {e}")

    def on_files_scanned(self, event: FilesScannedEvent):
        """파일 스캔 완료 이벤트 핸들러"""
        print(
            f"📨 [MainWindow] 파일 스캔 이벤트 수신: {event.status.value} - {len(event.found_files)}개 파일"
        )
        print(f"🔍 [DEBUG] 스캔 ID: {event.scan_id}")
        print(f"🔍 [DEBUG] 디렉토리: {event.directory_path}")

        try:
            if event.status == ScanStatus.STARTED:
                self.update_status_bar("파일 스캔 시작됨")
                self.left_panel.update_progress(0)

            elif event.status == ScanStatus.IN_PROGRESS:
                progress = 0
                if event.scanned_files_count > 0:
                    # 대략적인 진행률 계산
                    progress = min(50, (event.scanned_files_count // 10) * 5)  # 최대 50%까지
                self.left_panel.update_progress(progress)
                self.update_status_bar(f"파일 스캔 중... ({event.total_files_found}개 발견)")

            elif event.status == ScanStatus.COMPLETED:
                self.left_panel.update_progress(100)
                self.update_status_bar(f"스캔 완료: {event.total_files_found}개 파일 발견")

                # 스캔 완료 후 파일 처리
                if event.found_files:
                    self.on_scan_completed(event.found_files)
                else:
                    self.update_status_bar("비디오 파일을 찾을 수 없습니다")

            elif event.status == ScanStatus.FAILED:
                self.update_status_bar(f"스캔 실패: {event.error_message}")
                self.left_panel.update_progress(0)

            elif event.status == ScanStatus.CANCELLED:
                self.update_status_bar("스캔이 취소되었습니다")
                self.left_panel.update_progress(0)

        except Exception as e:
            print(f"❌ 파일 스캔 이벤트 처리 실패: {e}")

    def on_task_started(self, event: TaskStartedEvent):
        """백그라운드 작업 시작 이벤트 핸들러"""
        print(f"🚀 [MainWindow] 작업 시작: {event.task_name} (ID: {event.task_id})")
        self.update_status_bar(f"작업 시작: {event.task_name}", 0)

    def on_task_progress(self, event: TaskProgressEvent):
        """백그라운드 작업 진행률 이벤트 핸들러"""
        print(f"📊 [MainWindow] 작업 진행률: {event.progress_percent}% - {event.current_step}")
        self.update_status_bar(
            f"{event.current_step} ({event.items_processed}개 처리됨)", event.progress_percent
        )
        if hasattr(self, "left_panel"):
            self.left_panel.update_progress(event.progress_percent)

    def on_task_completed(self, event: TaskCompletedEvent):
        """백그라운드 작업 완료 이벤트 핸들러"""
        print(f"✅ [MainWindow] 작업 완료: {event.task_name} (소요시간: {event.duration:.2f}초)")
        self.update_status_bar(
            f"작업 완료: {event.task_name} ({event.items_processed}개 처리됨)", 100
        )
        if hasattr(self, "left_panel"):
            self.left_panel.update_progress(100)

    def on_task_failed(self, event: TaskFailedEvent):
        """백그라운드 작업 실패 이벤트 핸들러"""
        print(f"❌ [MainWindow] 작업 실패: {event.task_name} - {event.error_message}")
        self.show_error_message(f"작업 실패: {event.task_name}", event.error_message, "task_failed")

    def on_task_cancelled(self, event: TaskCancelledEvent):
        """백그라운드 작업 취소 이벤트 핸들러"""
        print(f"🚫 [MainWindow] 작업 취소: {event.task_name} - {event.reason}")
        self.update_status_bar(f"작업 취소됨: {event.task_name}")

    def on_scan_completed(self, found_files: list):
        """스캔 완료 후 파일 처리"""
        try:
            # Path 객체를 문자열로 변환
            file_paths = [str(file_path) for file_path in found_files]

            # 기존 process_selected_files 메서드 호출
            self.process_selected_files(file_paths)

        except Exception as e:
            print(f"❌ 스캔 완료 후 처리 실패: {e}")

    def init_data_managers(self):
        """데이터 관리자 초기화"""
        self.anime_data_manager = AnimeDataManager(tmdb_client=self.tmdb_client)
        self.file_processing_manager = FileProcessingManager()

        # TMDBManager 초기화 시 API 키 전달
        api_key = self.settings_manager.get_setting("tmdb_api_key") or os.getenv("TMDB_API_KEY")
        self.tmdb_manager = TMDBManager(api_key=api_key)

    def apply_settings_to_ui(self):
        """설정을 UI 컴포넌트에 적용"""
        try:
            if not self.settings_manager:
                return

            settings = self.settings_manager.settings

            # 기본 설정 적용
            self.organize_mode = getattr(settings, "organize_mode", "이동")
            self.naming_scheme = getattr(settings, "naming_scheme", "standard")
            self.safe_mode = getattr(settings, "safe_mode", True)
            self.backup_before_organize = getattr(settings, "backup_before_organize", False)
            self.prefer_anitopy = getattr(settings, "prefer_anitopy", True)
            self.fallback_parser = getattr(settings, "fallback_parser", "GuessIt")
            self.realtime_monitoring = getattr(settings, "realtime_monitoring", False)
            self.auto_refresh_interval = getattr(settings, "auto_refresh_interval", 30)
            self.tmdb_language = getattr(settings, "tmdb_language", "ko-KR")
            self.show_advanced_options = getattr(settings, "show_advanced_options", False)
            self.log_level = getattr(settings, "log_level", "INFO")
            self.log_to_file = getattr(settings, "log_to_file", False)
            self.backup_location = getattr(settings, "backup_location", "")
            self.max_backup_count = getattr(settings, "max_backup_count", 10)

            print("✅ UI 설정 적용 완료")

        except Exception as e:
            print(f"⚠️ UI 설정 적용 실패: {e}")

    def initialize_data(self):
        """초기 데이터 설정"""
        # 빈 리스트로 초기화 (실제 파일 스캔 결과로 대체)
        self.scanning = False
        self.progress = 0

        # 파일 시스템 관련 변수 초기화
        self.source_directory = None
        self.source_files = []
        self.destination_directory = None

    def init_ui(self):
        """UI 초기화"""
        # 윈도우 기본 설정
        self.setWindowTitle("AnimeSorter v2.0.0 - 애니메이션 파일 정리 도구")
        self.setMinimumSize(1200, 800)  # 최소 크기 설정
        self.resize(1600, 1000)  # 기본 크기 설정

        # 중앙 위젯 생성
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 메인 레이아웃
        parent_layout = QVBoxLayout(central_widget)
        parent_layout.setSpacing(10)
        parent_layout.setContentsMargins(10, 10, 10, 10)

        # 메뉴바 생성
        self.create_menu_bar()

        # 메인 툴바 생성
        self.main_toolbar = MainToolbar()
        parent_layout.addWidget(self.main_toolbar)

        # 메인 스플리터 생성 (좌우 분할)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)  # 패널이 완전히 접히지 않도록
        splitter.setHandleWidth(8)  # 핸들 너비 증가

        # 왼쪽 패널: 빠른 작업, 통계, 필터
        self.left_panel = LeftPanel()
        self.left_panel.setMinimumWidth(350)  # 최소 너비 설정
        self.left_panel.setMaximumWidth(500)  # 최대 너비 제한
        splitter.addWidget(self.left_panel)

        # 오른쪽 패널: 결과 및 로그
        self.right_panel = RightPanel()
        splitter.addWidget(self.right_panel)

        # 결과 뷰 생성 (그룹 리스트 중심)
        self.results_view = ResultsView()
        self.right_panel.layout().addWidget(self.results_view)

        # 모델들 초기화
        # 대상 폴더 정보 가져오기
        self.destination_directory = self.settings_manager.get_setting(
            "destination_root", "대상 폴더"
        )

        self.grouped_model = GroupedListModel(
            {}, self.tmdb_client, self.destination_directory
        )  # 그룹 리스트용
        self.detail_model = DetailFileModel([], self.tmdb_client)  # 상세 파일 목록용

        # 결과 뷰에 모델 설정
        self.results_view.set_group_model(self.grouped_model)
        self.results_view.set_detail_model(self.detail_model)

        # 그룹 선택 시 상세 파일 목록 업데이트
        self.results_view.group_selected.connect(self.on_group_selected)

        # 스플리터 비율 설정 (반응형)
        splitter.setSizes([400, 1200])  # 초기 비율
        splitter.setStretchFactor(0, 0)  # 왼쪽 패널은 고정 크기
        splitter.setStretchFactor(1, 1)  # 오른쪽 패널은 확장 가능

        parent_layout.addWidget(splitter)

        # 상태바 생성
        self.create_status_bar()

        # 윈도우 크기 변경 이벤트 처리
        self.resizeEvent = self.on_resize_event

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

    def setup_connections(self):
        """시그널/슬롯 연결 설정"""
        # 툴바 연결
        self.main_toolbar.btnSettings.clicked.connect(self.open_settings)
        self.main_toolbar.organize_requested.connect(self.start_file_organization)

        # 왼쪽 패널 연결
        self.left_panel.source_folder_selected.connect(self.on_source_folder_selected)
        self.left_panel.source_files_selected.connect(self.on_source_files_selected)
        self.left_panel.destination_folder_selected.connect(self.on_destination_folder_selected)
        self.left_panel.scan_started.connect(self.start_scan)
        self.left_panel.scan_paused.connect(self.stop_scan)
        self.left_panel.completed_cleared.connect(self.clear_completed)

        # 오른쪽 패널 연결
        self.right_panel.commit_requested.connect(self.commit_organization)
        self.right_panel.simulate_requested.connect(self.simulate_organization)

        # TMDB 검색 시그널 연결
        self.anime_data_manager.tmdb_search_requested.connect(self.on_tmdb_search_requested)
        self.anime_data_manager.tmdb_anime_selected.connect(self.on_tmdb_anime_selected)

        # 타이머 설정 제거 - 불필요한 반복 호출 방지
        # self.timer = QTimer(self)
        # self.timer.setInterval(700)
        # self.timer.timeout.connect(self.on_scan_tick)

    def on_source_folder_selected(self, folder_path: str):
        """소스 폴더 선택 처리"""
        self.source_directory = folder_path
        self.update_scan_button_state()
        self.update_status_bar(f"소스 폴더가 선택되었습니다: {folder_path}")

    def on_source_files_selected(self, file_paths: list[str]):
        """소스 파일 선택 처리"""
        self.source_files = file_paths
        self.update_scan_button_state()
        self.update_status_bar(f"{len(file_paths)}개 파일이 선택되었습니다")

        # 선택된 파일들을 처리
        self.process_selected_files(file_paths)

    def on_destination_folder_selected(self, folder_path: str):
        """대상 폴더 선택 처리"""
        self.destination_directory = folder_path
        self.update_status_bar(f"대상 폴더가 선택되었습니다: {folder_path}")

        # GroupedListModel의 대상 폴더 정보 업데이트
        if hasattr(self, "grouped_model"):
            self.grouped_model.destination_directory = folder_path
            # 모델 새로고침 (기존 데이터로 다시 설정)
            if hasattr(self, "anime_data_manager"):
                grouped_items = self.anime_data_manager.get_grouped_items()
                self.grouped_model.set_grouped_items(grouped_items)

    def update_scan_button_state(self):
        """스캔 시작 버튼 활성화 상태 업데이트"""
        # 소스 디렉토리나 파일이 선택되어 있으면 버튼 활성화
        has_source = (self.source_directory and os.path.exists(self.source_directory)) or (
            self.source_directory and len(self.source_files) > 0
        )

        self.left_panel.update_scan_button_state(has_source)

        # 정리 실행 버튼 상태 업데이트
        has_groups = False
        if hasattr(self, "anime_data_manager"):
            grouped_items = self.anime_data_manager.get_grouped_items()
            has_groups = len(grouped_items) > 0 and any(
                group_id != "ungrouped" for group_id in grouped_items.keys()
            )

        has_destination = self.destination_directory and os.path.exists(self.destination_directory)
        self.main_toolbar.set_organize_enabled(has_groups and has_destination)

        if has_source:
            if self.source_directory:
                self.update_status_bar(f"스캔 준비 완료: {self.source_directory}")
            elif self.source_files:
                self.update_status_bar(f"스캔 준비 완료: {len(self.source_files)}개 파일")
        else:
            self.update_status_bar("소스 디렉토리나 파일을 선택해주세요")

    def on_tmdb_search_requested(self, group_id: str):
        """TMDB 검색 요청 처리"""
        try:
            # 그룹 정보 가져오기
            grouped_items = self.anime_data_manager.get_grouped_items()
            if group_id not in grouped_items:
                print(f"❌ 그룹 {group_id}를 찾을 수 없습니다")
                return

            group_items = grouped_items[group_id]
            if not group_items:
                print(f"❌ 그룹 {group_id}에 아이템이 없습니다")
                return

            # 그룹 제목 가져오기
            group_title = group_items[0].title or group_items[0].detectedTitle or "Unknown"

            print(f"🔍 TMDB 검색 시작: {group_title} (그룹 {group_id})")

            # 먼저 TMDB 검색을 실행하여 결과 개수 확인
            try:
                search_results = self.tmdb_client.search_anime(group_title)

                if len(search_results) == 1:
                    # 결과가 1개면 자동 선택하고 다이얼로그를 띄우지 않음
                    selected_anime = search_results[0]
                    print(f"✅ 검색 결과 1개 - 자동 선택: {selected_anime.name}")
                    self.on_tmdb_anime_selected(group_id, selected_anime)
                    return

                if len(search_results) == 0:
                    # 결과가 없으면 다이얼로그를 띄워서 수동 검색 가능하게 함
                    print("⚠️ 검색 결과 없음 - 다이얼로그 표시")
                else:
                    # 결과가 2개 이상이면 다이얼로그를 띄워서 선택하게 함
                    print(f"📋 검색 결과 {len(search_results)}개 - 다이얼로그 표시")

            except Exception as e:
                print(f"❌ TMDB 검색 실패: {e}")
                # 검색 실패 시에도 다이얼로그를 띄워서 수동 검색 가능하게 함

            # 다이얼로그가 필요한 경우에만 생성
            print(f"🔍 TMDB 검색 다이얼로그 생성: {group_title} (그룹 {group_id})")

            # 이미 열린 다이얼로그가 있으면 포커스
            if group_id in self.tmdb_search_dialogs:
                dialog = self.tmdb_search_dialogs[group_id]
                if dialog.isVisible():
                    dialog.raise_()
                    dialog.activateWindow()
                    return

            # 새 다이얼로그 생성
            dialog = TMDBSearchDialog(group_title, self.tmdb_client, self)
            dialog.anime_selected.connect(
                lambda anime: self.on_tmdb_anime_selected(group_id, anime)
            )

            # 다이얼로그 저장
            self.tmdb_search_dialogs[group_id] = dialog

            # 다이얼로그 표시
            dialog.show()

            print(f"✅ TMDB 검색 다이얼로그 표시됨: {group_title}")

        except Exception as e:
            print(f"❌ TMDB 검색 다이얼로그 생성 실패: {e}")
            self.update_status_bar(f"TMDB 검색 다이얼로그 생성 실패: {str(e)}")

    def on_tmdb_anime_selected(self, group_id: str, tmdb_anime):
        """TMDB 애니메이션 선택 처리"""
        try:
            # 데이터 관리자에 TMDB 매치 결과 설정
            self.anime_data_manager.set_tmdb_match_for_group(group_id, tmdb_anime)

            # 그룹 모델 업데이트
            self.update_group_model()

            # 상태바 업데이트 (name 속성 사용)
            self.update_status_bar(f"✅ {tmdb_anime.name} 매치 완료")

            # 다이얼로그 닫기
            if group_id in self.tmdb_search_dialogs:
                dialog = self.tmdb_search_dialogs[group_id]
                dialog.close()
                del self.tmdb_search_dialogs[group_id]

            # 순차적 처리를 위해 다음 그룹 처리 (잠시 대기 후)
            QTimer.singleShot(500, self.process_next_tmdb_group)

        except Exception as e:
            print(f"❌ TMDB 애니메이션 선택 처리 실패: {e}")
            # 에러가 발생해도 다음 그룹 처리
            QTimer.singleShot(500, self.process_next_tmdb_group)

    def update_group_model(self):
        """그룹 모델 업데이트"""
        try:
            if hasattr(self, "grouped_model"):
                grouped_items = self.anime_data_manager.get_grouped_items()
                self.grouped_model.set_grouped_items(grouped_items)
        except Exception as e:
            print(f"❌ 그룹 모델 업데이트 실패: {e}")

    def restore_table_column_widths(self):
        """테이블 컬럼 너비 복원"""
        try:
            if not self.settings_manager:
                return

            settings = self.settings_manager.settings
            column_widths = getattr(settings, "table_column_widths", {})

            if (
                column_widths
                and hasattr(self, "right_panel")
                and hasattr(self.right_panel, "results_view")
            ):
                results_view = self.right_panel.results_view

                # 그룹 테이블 컬럼 너비 복원
                if hasattr(results_view, "group_table") and results_view.group_table:
                    table = results_view.group_table
                    for col_str, width in column_widths.items():
                        try:
                            col = int(col_str)  # 문자열을 정수로 변환
                            if col < table.model().columnCount():
                                table.setColumnWidth(col, width)
                        except (ValueError, TypeError) as e:
                            print(f"⚠️ 컬럼 인덱스 변환 실패: {col_str} -> {e}")
                            continue

                # 상세 테이블 컬럼 너비 복원
                if hasattr(results_view, "detail_table") and results_view.detail_table:
                    table = results_view.detail_table
                    for col_str, width in column_widths.items():
                        try:
                            col = int(col_str)  # 문자열을 정수로 변환
                            if col < table.model().columnCount():
                                table.setColumnWidth(col, width)
                        except (ValueError, TypeError) as e:
                            print(f"⚠️ 컬럼 인덱스 변환 실패: {col_str} -> {e}")
                            continue

                print("✅ 테이블 컬럼 너비 복원 완료")

        except Exception as e:
            print(f"⚠️ 테이블 컬럼 너비 복원 실패: {e}")

    def get_table_column_widths(self):
        """테이블 컬럼 너비 가져오기"""
        try:
            column_widths = {}

            if hasattr(self, "right_panel") and hasattr(self.right_panel, "results_view"):
                results_view = self.right_panel.results_view

                # 그룹 테이블에서 컬럼 너비 가져오기
                if hasattr(results_view, "group_table") and results_view.group_table:
                    table = results_view.group_table
                    for i in range(table.model().columnCount()):
                        column_widths[str(i)] = table.columnWidth(i)

                # 상세 테이블에서 컬럼 너비 가져오기 (그룹 테이블과 동일한 구조라면 덮어씀)
                if hasattr(results_view, "detail_table") and results_view.detail_table:
                    table = results_view.detail_table
                    for i in range(table.model().columnCount()):
                        column_widths[str(i)] = table.columnWidth(i)

            return column_widths

        except Exception as e:
            print(f"⚠️ 테이블 컬럼 너비 가져오기 실패: {e}")
            return {}

    def process_selected_files(self, file_paths: list[str]):
        """선택된 파일들을 처리하고 메타데이터 검색"""
        if not self.file_parser:
            QMessageBox.warning(self, "경고", "FileParser가 초기화되지 않았습니다.")
            return

        if not self.tmdb_client:
            QMessageBox.warning(
                self,
                "경고",
                "TMDBClient가 초기화되지 않았습니다.\nTMDB_API_KEY 환경 변수를 설정해주세요.",
            )
            return

        self.update_status_bar("파일 파싱 및 메타데이터 검색 중...")

        # 파싱된 파일들을 저장할 리스트
        parsed_items = []

        # 각 파일을 처리
        for i, file_path in enumerate(file_paths):
            try:
                # 진행률 업데이트
                progress = int((i / len(file_paths)) * 100)
                self.update_status_bar(
                    f"파일 파싱 중... {i+1}/{len(file_paths)} ({progress}%)", progress
                )

                # 비디오 파일 크기 확인 (1MB 미만 제외 - 더미 파일 방지)
                # 참고: 자막 파일은 별도로 연관 검색하므로 여기서 제외하지 않음
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size < 1024 * 1024:  # 1MB 미만
                        print(
                            f"⚠️ 비디오 파일 크기가 너무 작음 (제외): {os.path.basename(file_path)} ({file_size} bytes)"
                        )
                        self.right_panel.add_activity_log(
                            f"⚠️ 제외됨: {os.path.basename(file_path)} (크기: {file_size} bytes)"
                        )
                        continue
                except OSError:
                    print(f"⚠️ 파일 크기 확인 실패 (제외): {os.path.basename(file_path)}")
                    self.right_panel.add_activity_log(
                        f"⚠️ 제외됨: {os.path.basename(file_path)} (파일 접근 불가)"
                    )
                    continue

                # 파일 파싱
                print(f"🔍 파싱 시작: {os.path.basename(file_path)}")
                parsed_metadata = self.file_parser.parse_filename(file_path)

                if parsed_metadata and parsed_metadata.title:
                    # 파싱된 항목 생성
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
                        parsingConfidence=parsed_metadata.confidence or 0.0,
                    )
                    parsed_items.append(parsed_item)

                    # 활동 로그 업데이트
                    log_message = f"✅ {os.path.basename(file_path)} - {parsed_metadata.title} S{parsed_item.season:02d}E{parsed_item.episode:02d}"
                    self.right_panel.add_activity_log(log_message)

                else:
                    # 파싱 실패
                    parsed_item = ParsedItem(
                        sourcePath=file_path,
                        detectedTitle="Unknown",
                        title="Unknown",
                        status="error",
                        parsingConfidence=0.0,
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
                    status="error",
                    parsingConfidence=0.0,
                )
                parsed_items.append(parsed_item)
                self.update_status_bar(f"파일 처리 오류: {os.path.basename(file_path)} - {str(e)}")

        # 파싱된 항목들을 데이터 관리자에 추가
        if parsed_items:
            self.anime_data_manager.add_items(parsed_items)

            # 그룹화 수행
            grouped_items = self.anime_data_manager.group_similar_titles()
            self.anime_data_manager.display_grouped_results()

            # 통계 업데이트
            stats = self.anime_data_manager.get_stats()
            self.left_panel.update_stats(
                stats["total"], stats["parsed"], stats["pending"], stats["groups"]
            )

            # 테이블에 결과 표시
            self.update_results_display()

            # 상태바 업데이트
            self.update_status_bar(f"파일 처리 완료: {len(parsed_items)}개 파일 파싱됨")
        else:
            self.update_status_bar("파일 처리 완료: 파싱된 파일 없음")

    def start_scan(self):
        """스캔 시작"""
        if not self.source_files and not self.source_directory:
            QMessageBox.warning(self, "경고", "먼저 소스 파일이나 폴더를 선택해주세요.")
            return

        self.scanning = True
        self.progress = 0
        self.left_panel.update_progress(0)
        self.status_progress.setValue(0)
        self.left_panel.btnStart.setEnabled(False)
        self.left_panel.btnPause.setEnabled(True)
        self.update_status_bar("파일 스캔 중...", 0)

        # TMDB 검색 플래그 초기화
        self._tmdb_search_started = False

        # 실제 스캔 로직 구현
        if self.source_files:
            self.process_selected_files(self.source_files)
        elif self.source_directory:
            # 폴더 내 파일들을 찾아서 처리
            self.scan_directory(self.source_directory)

        # self.timer.start() # 타이머 설정 제거

    def scan_directory(self, directory_path: str):
        """디렉토리 스캔 (백그라운드 FileScanService 사용)"""
        try:
            if self.file_scan_service:
                # 백그라운드 파일 스캔 서비스 사용
                print(f"🚀 백그라운드 서비스로 디렉토리 스캔: {directory_path}")
                self.current_scan_id = self.file_scan_service.scan_directory(
                    directory_path=directory_path,
                    recursive=True,
                    extensions={".mkv", ".mp4", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"},
                    min_size_mb=1.0,
                    max_size_gb=50.0,
                )
                print(f"🆔 백그라운드 작업 ID: {self.current_scan_id}")

                # UI 상태 업데이트
                self.update_status_bar("백그라운드에서 파일 스캔 중...", 0)
            else:
                # 폴백: 기존 방식 사용
                print("⚠️ FileScanService를 사용할 수 없음, 기존 방식으로 스캔")
                self._scan_directory_legacy(directory_path)

        except Exception as e:
            self.update_status_bar(f"디렉토리 스캔 오류: {str(e)}")
            print(f"디렉토리 스캔 오류: {e}")
            # 폴백: 기존 방식으로 재시도
            self._scan_directory_legacy(directory_path)

    def _scan_directory_legacy(self, directory_path: str):
        """기존 방식 디렉토리 스캔 (폴백용)"""
        try:
            video_extensions = (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm")
            video_files = []

            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    if file.lower().endswith(video_extensions):
                        full_path = os.path.join(root, file)

                        # 비디오 파일 크기 확인 (1MB 미만 제외 - 더미 파일 방지)
                        try:
                            file_size = os.path.getsize(full_path)
                            if file_size < 1024 * 1024:  # 1MB 미만
                                print(
                                    f"⚠️ 비디오 파일 크기가 너무 작음 (제외): {file} ({file_size} bytes)"
                                )
                                self.right_panel.add_activity_log(
                                    f"⚠️ 제외됨: {file} (크기: {file_size} bytes)"
                                )
                                continue
                        except OSError:
                            print(f"⚠️ 파일 크기 확인 실패 (제외): {file}")
                            self.right_panel.add_activity_log(f"⚠️ 제외됨: {file} (파일 접근 불가)")
                            continue

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
        # self.timer.stop() # 타이머 설정 제거

        # 새로운 FileScanService의 스캔 취소 시도
        if self.file_scan_service and hasattr(self, "current_scan_id") and self.current_scan_id:
            try:
                success = self.file_scan_service.cancel_scan(self.current_scan_id)
                if success:
                    print(f"✅ 스캔 취소 요청 성공: {self.current_scan_id}")
                else:
                    print(f"⚠️ 스캔 취소 실패: {self.current_scan_id}")
            except Exception as e:
                print(f"❌ 스캔 취소 중 오류: {e}")

        self.left_panel.btnStart.setEnabled(True)
        self.left_panel.btnPause.setEnabled(False)
        self.update_status_bar("스캔이 중지되었습니다")

    # def on_scan_tick(self):
    #     """스캔 진행률 업데이트 - 타이머 제거로 인해 주석 처리"""
    #     self.progress = min(100, self.progress + 7)
    #     self.left_panel.update_progress(self.progress)
    #     self.status_progress.setValue(self.progress)
    #     self.update_status_bar(f"스캔 진행 중... {self.progress}%", self.progress)
    #
    #     if self.progress >= 100:
    #         self.stop_scan()
    #         self.update_status_bar("스캔 완료")

    def clear_completed(self):
        """완료된 항목 정리"""
        self.anime_data_manager.clear_completed_items()

        # 통계 업데이트
        stats = self.anime_data_manager.get_stats()
        self.left_panel.update_stats(stats["total"], stats["parsed"], stats["pending"])

        self.update_status_bar("완료된 항목이 정리되었습니다")

    def reset_filters(self):
        """필터 초기화"""
        self.main_toolbar.reset_filters()
        self.update_status_bar("필터가 초기화되었습니다")

    def commit_organization(self):
        """정리 실행"""
        QMessageBox.information(self, "정리 실행", "파일 정리 계획을 실행합니다. (구현 예정)")

    def simulate_organization(self):
        """정리 시뮬레이션"""
        QMessageBox.information(self, "시뮬레이션", "파일 이동을 시뮬레이션합니다. (구현 예정)")

    def open_settings(self):
        """설정 다이얼로그 열기"""
        # 기존 SettingsDialog 사용 (별도 파일로 분리 필요)
        QMessageBox.information(self, "설정", "설정 다이얼로그 구현 필요")

    def choose_files(self):
        """파일 선택 (메뉴바용)"""
        from PyQt5.QtWidgets import QFileDialog

        files, _ = QFileDialog.getOpenFileNames(
            self, "파일 선택", "", "Video Files (*.mkv *.mp4 *.avi *.mov);;All Files (*)"
        )
        if files:
            self.on_source_files_selected(files)

    def choose_folder(self):
        """폴더 선택 (메뉴바용)"""
        from PyQt5.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder:
            self.on_source_folder_selected(folder)

    def export_results(self):
        """결과 내보내기"""
        from PyQt5.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self, "결과 내보내기", "animesorter_results.csv", "CSV Files (*.csv);;All Files (*)"
        )
        if filename:
            try:
                import csv

                items = self.anime_data_manager.get_items()

                with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                    fieldnames = [
                        "상태",
                        "제목",
                        "시즌",
                        "에피소드",
                        "년도",
                        "해상도",
                        "크기",
                        "TMDB ID",
                        "경로",
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for item in items:
                        writer.writerow(
                            {
                                "상태": item.status,
                                "제목": item.detectedTitle,
                                "시즌": item.season or "",
                                "에피소드": item.episode or "",
                                "년도": item.year or "",
                                "해상도": item.resolution or "",
                                "크기": f"{item.sizeMB}MB" if item.sizeMB else "",
                                "TMDB ID": item.tmdbId or "",
                                "경로": item.sourcePath,
                            }
                        )

                self.update_status_bar(f"결과가 {filename}에 저장되었습니다")
                QMessageBox.information(
                    self, "내보내기 완료", f"결과가 성공적으로 저장되었습니다:\n{filename}"
                )

            except Exception as e:
                QMessageBox.critical(
                    self, "내보내기 오류", f"파일 저장 중 오류가 발생했습니다:\n{str(e)}"
                )

    def show_about(self):
        """정보 다이얼로그 표시"""
        QMessageBox.about(
            self,
            "AnimeSorter 정보",
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
            <p><b>라이선스:</b> MIT License</p>""",
        )

    def open_settings(self):
        """설정 다이얼로그 열기"""
        try:
            if not self.settings_manager:
                QMessageBox.warning(self, "경고", "설정 관리자가 초기화되지 않았습니다.")
                return

            # 설정 다이얼로그 생성 및 표시
            settings_dialog = SettingsDialog(self.settings_manager, self)
            settings_dialog.settingsChanged.connect(self.on_settings_changed)

            if settings_dialog.exec_() == QDialog.Accepted:
                # 설정이 변경되었을 때 UI에 적용
                self.apply_settings_to_ui()
                print("✅ 설정이 업데이트되었습니다")

        except Exception as e:
            print(f"❌ 설정 다이얼로그 열기 실패: {e}")
            QMessageBox.critical(self, "오류", f"설정 다이얼로그를 열 수 없습니다:\n{e}")

    def on_settings_changed(self):
        """설정 변경 시 호출되는 메서드"""
        try:
            # 설정 변경 시 필요한 컴포넌트 업데이트
            self.apply_settings_to_ui()

            # TMDB 클라이언트 재초기화 (API 키가 변경된 경우)
            if self.settings_manager:
                api_key = self.settings_manager.settings.tmdb_api_key
                if api_key and (not self.tmdb_client or self.tmdb_client.api_key != api_key):
                    self.tmdb_client = TMDBClient(api_key=api_key)
                    print("✅ TMDBClient 재초기화 완료")

            # FileManager 설정 업데이트
            if self.settings_manager and self.file_manager:
                dest_root = self.settings_manager.settings.destination_root
                safe_mode = self.settings_manager.settings.safe_mode
                naming_scheme = self.settings_manager.settings.naming_scheme

                if dest_root:
                    self.file_manager.destination_root = dest_root
                self.file_manager.safe_mode = safe_mode
                self.file_manager.set_naming_scheme(naming_scheme)

                print("✅ FileManager 설정 업데이트 완료")

        except Exception as e:
            print(f"⚠️ 설정 변경 처리 실패: {e}")

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

    def restore_session_state(self):
        """이전 세션 상태 복원"""
        try:
            if not self.settings_manager:
                return

            settings = self.settings_manager.settings

            # 마지막으로 선택한 디렉토리들 복원
            if settings.remember_last_session:
                if settings.last_source_directory and os.path.exists(
                    settings.last_source_directory
                ):
                    self.source_directory = settings.last_source_directory
                    # UI 업데이트
                    self.left_panel.update_source_directory_display(self.source_directory)

                if settings.last_destination_directory and os.path.exists(
                    settings.last_destination_directory
                ):
                    self.destination_directory = settings.last_destination_directory
                    # UI 업데이트
                    self.left_panel.update_destination_directory_display(self.destination_directory)

                # 마지막으로 선택한 파일들 복원
                if settings.last_source_files:
                    self.source_files = [f for f in settings.last_source_files if os.path.exists(f)]
                    if self.source_files:
                        # UI 업데이트
                        self.left_panel.update_source_files_display(len(self.source_files))

            # 윈도우 기하학 복원
            if settings.window_geometry:
                try:
                    geometry_parts = settings.window_geometry.split(",")
                    if len(geometry_parts) == 4:
                        x, y, width, height = map(int, geometry_parts)
                        self.setGeometry(x, y, width, height)
                except:
                    pass  # 기하학 복원 실패 시 기본값 사용

            # 테이블 컬럼 너비 복원
            if hasattr(self, "results_view") and hasattr(self.results_view, "table"):
                self.restore_table_column_widths()

            # 스캔 시작 버튼 활성화 상태 업데이트
            self.update_scan_button_state()

            # 저장된 데이터가 있으면 테이블에 표시
            if hasattr(self, "anime_data_manager") and self.anime_data_manager.items:
                self.update_results_display()

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
            settings.window_geometry = (
                f"{geometry.x()},{geometry.y()},{geometry.width()},{geometry.height()}"
            )

            # 그룹 테이블 컬럼 너비 저장
            if hasattr(self, "results_view") and hasattr(self.results_view, "group_table"):
                table = self.results_view.group_table
                if table and table.model():
                    column_widths = {}
                    for i in range(table.model().columnCount()):
                        width = table.columnWidth(i)
                        column_widths[i] = width
                    settings.group_table_column_widths = column_widths

            # 설정 파일에 저장
            self.settings_manager.save_settings()
            print("✅ 세션 상태 저장 완료")

        except Exception as e:
            print(f"⚠️ 세션 상태 저장 실패: {e}")

    def update_results_display(self):
        """결과 표시 업데이트"""
        try:
            if hasattr(self, "anime_data_manager"):
                # 그룹화된 데이터로 그룹 모델 업데이트
                grouped_items = self.anime_data_manager.get_grouped_items()
                self.grouped_model.set_grouped_items(grouped_items)

                # 상태바 업데이트
                stats = self.anime_data_manager.get_stats()
                group_count = len(grouped_items)
                self.update_status_bar(
                    f"총 {stats['total']}개 파일이 {group_count}개 그룹으로 분류되었습니다"
                )

                # 정리 실행 버튼 상태 업데이트
                has_groups = len(grouped_items) > 0 and any(
                    group_id != "ungrouped" for group_id in grouped_items.keys()
                )
                has_destination = self.destination_directory and os.path.exists(
                    self.destination_directory
                )
                self.main_toolbar.set_organize_enabled(has_groups and has_destination)

                # 로그는 한 번만 출력
                print(f"✅ {group_count}개 그룹 표시 완료")

                # TMDB 검색 시작 (한 번만 실행되도록 플래그 확인)
                if not getattr(self, "_tmdb_search_started", False):
                    self._tmdb_search_started = True
                    self.start_tmdb_search_for_groups()
        except Exception as e:
            print(f"⚠️ 결과 표시 업데이트 실패: {e}")

    def start_tmdb_search_for_groups(self):
        """그룹화 후 TMDB 검색 시작 (순차적 처리)"""
        try:
            if not self.tmdb_client:
                print("⚠️ TMDB 클라이언트가 초기화되지 않아 검색을 건너뜁니다")
                self.update_status_bar("TMDB API 키가 설정되지 않아 검색을 건너뜁니다")
                return

            grouped_items = self.anime_data_manager.get_grouped_items()
            self.pending_tmdb_groups = []

            # 검색할 그룹들을 수집
            for group_id, group_items in grouped_items.items():
                if group_id == "ungrouped":
                    continue

                # 이미 TMDB 매치가 있는 그룹은 건너뛰기
                if self.anime_data_manager.get_tmdb_match_for_group(group_id):
                    continue

                # 그룹 제목으로 TMDB 검색 대기열에 추가
                group_title = group_items[0].title or group_items[0].detectedTitle or "Unknown"
                self.pending_tmdb_groups.append((group_id, group_title))

            if self.pending_tmdb_groups:
                print(
                    f"🔍 {len(self.pending_tmdb_groups)}개 그룹에 대해 순차적 TMDB 검색을 시작합니다"
                )
                self.update_status_bar(
                    f"TMDB 검색 시작: {len(self.pending_tmdb_groups)}개 그룹 (순차적 처리)"
                )
                # 첫 번째 그룹부터 시작
                self.process_next_tmdb_group()
            else:
                print("✅ 모든 그룹이 이미 TMDB 매치가 완료되었습니다")
                self.update_status_bar("모든 그룹의 TMDB 매치가 완료되었습니다")

        except Exception as e:
            print(f"❌ TMDB 검색 시작 실패: {e}")
            self.update_status_bar(f"TMDB 검색 시작 실패: {str(e)}")

    def process_next_tmdb_group(self):
        """다음 TMDB 그룹 처리"""
        if not hasattr(self, "pending_tmdb_groups") or not self.pending_tmdb_groups:
            print("✅ 모든 TMDB 검색이 완료되었습니다")
            self.update_status_bar("모든 TMDB 검색이 완료되었습니다")
            return

        group_id, group_title = self.pending_tmdb_groups.pop(0)
        print(
            f"🔍 TMDB 검색 시작: '{group_title}' (그룹 {group_id}) - {len(self.pending_tmdb_groups)}개 남음"
        )
        self.update_status_bar(
            f"TMDB 검색 중: {group_title} ({len(self.pending_tmdb_groups)}개 남음)"
        )

        # 현재 그룹에 대해 TMDB 검색 시작
        self.anime_data_manager.search_tmdb_for_group(group_id, group_title)

    def start_file_organization(self):
        """파일 정리 실행 시작"""
        try:
            # 기본 검증
            if not hasattr(self, "anime_data_manager"):
                QMessageBox.warning(
                    self, "경고", "스캔된 데이터가 없습니다. 먼저 파일을 스캔해주세요."
                )
                return

            grouped_items = self.anime_data_manager.get_grouped_items()
            if not grouped_items:
                QMessageBox.warning(
                    self, "경고", "정리할 그룹이 없습니다. 먼저 파일을 스캔해주세요."
                )
                return

            # 대상 폴더 확인
            if not self.destination_directory or not os.path.exists(self.destination_directory):
                QMessageBox.warning(
                    self, "경고", "대상 폴더가 설정되지 않았거나 존재하지 않습니다."
                )
                return

            # 프리플라이트 다이얼로그 표시
            dialog = OrganizePreflightDialog(grouped_items, self.destination_directory, self)
            dialog.proceed_requested.connect(self.on_organize_proceed)

            result = dialog.exec_()

            if result == QDialog.Accepted:
                print("✅ 프리플라이트 확인 완료 - 파일 정리 실행 준비")
            else:
                print("❌ 파일 정리 실행이 취소되었습니다")
                self.update_status_bar("파일 정리 실행이 취소되었습니다")

        except Exception as e:
            print(f"❌ 파일 정리 실행 시작 실패: {e}")
            QMessageBox.critical(self, "오류", f"파일 정리 실행 중 오류가 발생했습니다:\n{str(e)}")
            self.update_status_bar(f"파일 정리 실행 실패: {str(e)}")

    def on_organize_proceed(self):
        """프리플라이트 확인 후 실제 정리 실행"""
        try:
            print("🚀 파일 정리 실행 시작")
            self.update_status_bar("파일 정리 실행 중...")

            # 그룹화된 아이템 가져오기
            grouped_items = self.anime_data_manager.get_grouped_items()

            # 진행률 다이얼로그 생성 및 실행
            progress_dialog = OrganizeProgressDialog(
                grouped_items, self.destination_directory, self
            )
            progress_dialog.start_organization()

            result = progress_dialog.exec_()

            if result == QDialog.Accepted:
                # 결과 가져오기
                organize_result = progress_dialog.get_result()
                if organize_result:
                    self.on_organization_completed(organize_result)
                else:
                    print("⚠️ 파일 정리 결과를 가져올 수 없습니다")
                    self.update_status_bar("파일 정리 완료 (결과 확인 불가)")
            else:
                print("❌ 파일 정리가 취소되었습니다")
                self.update_status_bar("파일 정리가 취소되었습니다")

        except Exception as e:
            print(f"❌ 파일 정리 실행 실패: {e}")
            QMessageBox.critical(self, "오류", f"파일 정리 실행 중 오류가 발생했습니다:\n{str(e)}")
            self.update_status_bar(f"파일 정리 실행 실패: {str(e)}")

    def on_organization_completed(self, result):
        """파일 정리 완료 처리"""
        try:
            # 결과 요약 메시지 생성
            message = "파일 정리가 완료되었습니다.\n\n"
            message += "📊 결과 요약:\n"
            message += f"• 성공: {result.success_count}개 파일\n"
            message += f"• 실패: {result.error_count}개 파일\n"
            message += f"• 건너뜀: {result.skip_count}개 파일\n\n"

            if result.errors:
                message += "❌ 오류 목록:\n"
                for i, error in enumerate(result.errors[:5], 1):  # 처음 5개만 표시
                    message += f"{i}. {error}\n"
                if len(result.errors) > 5:
                    message += f"... 및 {len(result.errors) - 5}개 더\n"
                message += "\n"

            if result.skipped_files:
                message += "⏭️ 건너뛴 파일:\n"
                for i, skipped in enumerate(result.skipped_files[:3], 1):  # 처음 3개만 표시
                    message += f"{i}. {skipped}\n"
                if len(result.skipped_files) > 3:
                    message += f"... 및 {len(result.skipped_files) - 3}개 더\n"
                message += "\n"

            # 결과 다이얼로그 표시
            QMessageBox.information(self, "파일 정리 완료", message)

            # 상태바 업데이트
            if result.success_count > 0:
                self.update_status_bar(f"파일 정리 완료: {result.success_count}개 파일 이동 성공")
            else:
                self.update_status_bar("파일 정리 완료 (성공한 파일 없음)")

            # 모델 리프레시 (필요한 경우)
            # TODO: 파일 이동 후 모델 업데이트 로직 구현

            print(
                f"✅ 파일 정리 완료: 성공 {result.success_count}, 실패 {result.error_count}, 건너뜀 {result.skip_count}"
            )

        except Exception as e:
            print(f"❌ 파일 정리 완료 처리 실패: {e}")
            self.update_status_bar(f"파일 정리 완료 처리 실패: {str(e)}")

    def on_group_selected(self, group_info: dict):
        """그룹 선택 시 상세 파일 목록 업데이트"""
        try:
            if group_info and "items" in group_info:
                # 선택된 그룹의 파일들을 상세 모델에 설정
                self.detail_model.set_items(group_info["items"])

                # 상태바에 그룹 정보 표시
                title = group_info.get("title", "Unknown")
                file_count = group_info.get("file_count", 0)
                self.update_status_bar(f"선택된 그룹: {title} ({file_count}개 파일)")

                print(f"✅ 그룹 '{title}'의 {file_count}개 파일을 상세 목록에 표시")
        except Exception as e:
            print(f"⚠️ 그룹 선택 처리 실패: {e}")

    def update_status_bar(self, message, progress=None):
        """상태바 업데이트 - EventBus 기반으로 전환됨"""
        if not self.event_bus:
            # EventBus가 없으면 기존 방식으로 fallback
            self._update_status_bar_direct(message, progress)
            return

        try:
            # StatusBarUpdateEvent 발행
            self.event_bus.publish(StatusBarUpdateEvent(message=message, progress=progress))

            # 파일 수 업데이트 (한 번만 호출)
            if hasattr(self, "anime_data_manager") and not hasattr(self, "_last_stats_update"):
                stats = self.anime_data_manager.get_stats()
                self.event_bus.publish(FileCountUpdateEvent(count=stats["total"]))
                self._last_stats_update = True

            # 메모리 사용량 계산 (간단한 추정) - 주기적으로만 업데이트
            if not hasattr(self, "_last_memory_update") or not self._last_memory_update:
                import psutil

                try:
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    cpu_percent = process.cpu_percent()

                    self.event_bus.publish(
                        MemoryUsageUpdateEvent(memory_mb=memory_mb, cpu_percent=cpu_percent)
                    )
                    self._last_memory_update = True
                except Exception as e:
                    print(f"메모리 사용량 계산 실패: {e}")
                    self.event_bus.publish(MemoryUsageUpdateEvent(memory_mb=0.0))
                    self._last_memory_update = True

        except Exception as e:
            print(f"EventBus를 통한 상태바 업데이트 실패: {e}")
            # Fallback to direct update
            self._update_status_bar_direct(message, progress)

    def _update_status_bar_direct(self, message, progress=None):
        """직접 상태바 업데이트 (Fallback 용도)"""
        self.status_label.setText(message)
        if progress is not None:
            self.status_progress.setValue(progress)

        # 파일 수 업데이트 (한 번만 호출)
        if hasattr(self, "anime_data_manager") and not hasattr(self, "_last_stats_update"):
            stats = self.anime_data_manager.get_stats()
            self.status_file_count.setText(f"파일: {stats['total']}")
            self._last_stats_update = True

        # 메모리 사용량 계산 (간단한 추정) - 주기적으로만 업데이트
        if not hasattr(self, "_last_memory_update") or not self._last_memory_update:
            import psutil

            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.status_memory.setText(f"메모리: {memory_mb:.1f}MB")
                self._last_memory_update = True
            except:
                self.status_memory.setText("메모리: N/A")
                self._last_memory_update = True

    def show_error_message(self, message: str, details: str = "", error_type: str = "error"):
        """오류 메시지 표시 - EventBus 기반"""
        if self.event_bus:
            try:
                self.event_bus.publish(
                    ErrorMessageEvent(message=message, details=details, error_type=error_type)
                )
            except Exception as e:
                print(f"EventBus를 통한 오류 메시지 발행 실패: {e}")
                # Fallback
                self.update_status_bar(f"❌ {message}")
        else:
            # Fallback
            self.update_status_bar(f"❌ {message}")

    def show_success_message(self, message: str, details: str = "", auto_clear: bool = True):
        """성공 메시지 표시 - EventBus 기반"""
        if self.event_bus:
            try:
                self.event_bus.publish(
                    SuccessMessageEvent(message=message, details=details, auto_clear=auto_clear)
                )
            except Exception as e:
                print(f"EventBus를 통한 성공 메시지 발행 실패: {e}")
                # Fallback
                self.update_status_bar(f"✅ {message}")
        else:
            # Fallback
            self.update_status_bar(f"✅ {message}")

    def update_progress(self, current: int, total: int, message: str = ""):
        """진행률 업데이트 - EventBus 기반"""
        if self.event_bus:
            try:
                self.event_bus.publish(
                    ProgressUpdateEvent(current=current, total=total, message=message)
                )
            except Exception as e:
                print(f"EventBus를 통한 진행률 업데이트 실패: {e}")
                # Fallback
                if total > 0:
                    progress = int((current / total) * 100)
                    self.update_status_bar(f"{message} ({current}/{total})", progress)
                else:
                    self.update_status_bar(message)
        else:
            # Fallback
            if total > 0:
                progress = int((current / total) * 100)
                self.update_status_bar(f"{message} ({current}/{total})", progress)
            else:
                self.update_status_bar(message)

    def on_resize_event(self, event):
        """윈도우 크기 변경 이벤트 처리"""
        # 기본 리사이즈 이벤트 처리
        super().resizeEvent(event)

        # 레이아웃 업데이트
        self.update_layout_on_resize()

    def update_layout_on_resize(self):
        """크기 변경 시 레이아웃 업데이트"""
        # 현재 윈도우 크기
        window_width = self.width()
        window_height = self.height()

        # 왼쪽 패널 크기 조정
        if hasattr(self, "left_panel"):
            # 윈도우가 작을 때는 왼쪽 패널을 더 작게
            if window_width < 1400:
                self.left_panel.setMaximumWidth(350)
            else:
                self.left_panel.setMaximumWidth(450)

        # 결과 뷰의 테이블 컬럼 크기 조정
        if hasattr(self, "results_view") and hasattr(self.results_view, "group_table"):
            self.adjust_table_columns()

    def adjust_table_columns(self):
        """테이블 컬럼 크기를 윈도우 크기에 맞게 조정"""
        if not hasattr(self, "results_view"):
            return

        # 그룹 테이블 컬럼 조정
        if hasattr(self.results_view, "group_table"):
            group_table = self.results_view.group_table
            if group_table.model():
                header = group_table.horizontalHeader()
                model = group_table.model()

                # 모델에서 컬럼 정보 가져오기
                if hasattr(model, "get_column_widths"):
                    column_widths = model.get_column_widths()
                    stretch_columns = model.get_stretch_columns()

                    # 각 컬럼 설정
                    for col in range(header.count()):
                        if col in stretch_columns:
                            header.setSectionResizeMode(col, QHeaderView.Stretch)
                        else:
                            header.setSectionResizeMode(col, QHeaderView.Fixed)
                            if col in column_widths:
                                header.resizeSection(col, column_widths[col])

        # 상세 테이블 컬럼 조정
        if hasattr(self.results_view, "detail_table"):
            detail_table = self.results_view.detail_table
            if detail_table.model():
                header = detail_table.horizontalHeader()
                model = detail_table.model()

                # 모델에서 컬럼 정보 가져오기
                if hasattr(model, "get_column_widths"):
                    column_widths = model.get_column_widths()
                    stretch_columns = model.get_stretch_columns()

                    # 각 컬럼 설정
                    for col in range(header.count()):
                        if col in stretch_columns:
                            header.setSectionResizeMode(col, QHeaderView.Stretch)
                        else:
                            header.setSectionResizeMode(col, QHeaderView.Fixed)
                            if col in column_widths:
                                header.resizeSection(col, column_widths[col])

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
