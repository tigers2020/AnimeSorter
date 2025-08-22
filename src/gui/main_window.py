"""
리팩토링된 메인 윈도우 - AnimeSorter의 주요 GUI 인터페이스
컴포넌트 기반 아키텍처로 재구성되어 가독성과 유지보수성이 향상되었습니다.
"""

import os
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHeaderView,  # Added for QHeaderView
    QMainWindow,
    QMessageBox,
)

# New Architecture Components
from app import (
    IFileOrganizationService,
    IFileScanService,
    IMediaDataService,
    ITMDBSearchService,
    IUIUpdateService,
    # Journal System Events
    get_event_bus,
    get_service,
)

# UI Command Bridge
from core.file_manager import FileManager

# Local imports
from core.file_parser import FileParser
from core.settings_manager import SettingsManager
from core.tmdb_client import TMDBClient

# Phase 10.1: 접근성 관리 시스템
from .components.accessibility_manager import AccessibilityManager

# Phase 10.2: 국제화 관리 시스템
from .components.i18n_manager import I18nManager

# UI Components
from .components.settings_dialog import SettingsDialog

# Phase 9.2: 테마 관리 시스템
from .components.theme_manager import ThemeManager
from .components.ui_migration_manager import UIMigrationManager

# Phase 8: UI 상태 관리 및 마이그레이션
from .components.ui_state_manager import UIStateManager

# UI Components
# Event Handler Manager
from .handlers.event_handler_manager import EventHandlerManager

# UI Initializer
from .initializers.ui_initializer import UIInitializer

# Data Models
from .managers.anime_data_manager import AnimeDataManager, ParsedItem
from .managers.file_processing_manager import FileProcessingManager
from .managers.status_bar_manager import StatusBarManager
from .managers.tmdb_manager import TMDBManager

# Table Models


class MainWindow(QMainWindow):
    """AnimeSorter 메인 윈도우 (리팩토링된 버전)"""

    def __init__(self):
        super().__init__()

        # 기본 설정
        self.setWindowTitle("AnimeSorter")
        self.setGeometry(100, 100, 1600, 900)

        # 로그 Dock 추가 (Phase 5)
        self.setup_log_dock()

        # UI 초기화는 UIInitializer에서 처리됩니다
        # self.init_ui()  # UIInitializer로 이동됨

        self.setup_connections()
        # 단축키 설정은 UIInitializer에서 처리됩니다
        # self.setup_shortcuts()  # UIInitializer로 이동됨

        # 상태 초기화
        self.scanning = False
        self.progress = 0
        self.source_files = []
        self.source_directory = ""

        # UI 컴포넌트 속성 초기화
        self.status_progress = None  # 상태바 진행률 표시기

        # 설정 관리자 초기화
        self.settings_manager = SettingsManager()

        # TMDB 클라이언트 초기화는 init_core_components에서 처리됩니다
        # self.setup_tmdb_client()  # init_core_components로 이동됨
        self.tmdb_client = None

        # 파일 파서 초기화
        self.file_parser = FileParser()

        # 애니메 데이터 관리자 초기화
        self.anime_data_manager = AnimeDataManager()

        # 이벤트 버스 초기화
        self.event_bus = get_event_bus()

        # 그룹별 TMDB 검색 다이얼로그 저장
        self.tmdb_search_dialogs = {}  # 그룹별 검색 다이얼로그 저장

        # 새로운 아키텍처 관련 초기화
        self.event_bus = None
        self.file_scan_service = None
        self.file_organization_service = None
        self.media_data_service = None
        self.tmdb_search_service = None
        self.ui_update_service = None
        self.current_scan_id = None
        self.current_organization_id = None
        self.current_tmdb_search_id = None

        # UI Command 시스템 관련 초기화
        self.undo_stack_bridge = None
        self.staging_manager = None
        self.journal_manager = None
        self.ui_command_bridge = None

        # Event Handler Manager 초기화
        self.event_handler_manager = None

        # Status Bar Manager 초기화
        self.status_bar_manager = None

        # 핵심 컴포넌트 초기화
        self.init_core_components()

        # 데이터 관리자 초기화
        self.init_data_managers()

        # TMDB 검색 다이얼로그 초기화
        self.tmdb_search_dialogs = {}  # 그룹별 검색 다이얼로그 저장

        # 초기 데이터 설정
        self.initialize_data()

        # 새로운 아키텍처 컴포넌트 초기화 (데이터 관리자 초기화 이후에 호출)
        self.init_new_architecture()

        # Phase 8: UI 상태 관리자 및 마이그레이션 관리자 초기화
        self.init_ui_state_management()

        # Phase 9.2: 테마 관리자 초기화
        self.theme_manager = ThemeManager(self)
        self.theme_manager.theme_changed.connect(self.on_theme_changed)

        # 설정에서 저장된 테마 적용
        saved_theme = self.settings_manager.get_setting("theme", "auto")
        self.theme_manager.apply_theme(saved_theme)
        print(f"✅ 테마 관리자 초기화 완료 (테마: {saved_theme})")

        # Phase 10.1: 접근성 관리자 초기화
        self.accessibility_manager = AccessibilityManager(self)
        self.accessibility_manager.initialize(self)
        print("✅ 접근성 관리자 초기화 완료")

        # Phase 10.2: 국제화 관리자 초기화
        self.i18n_manager = I18nManager(self)
        self.i18n_manager.initialize_with_system_language()
        self.i18n_manager.language_changed.connect(self.on_language_changed)
        print("✅ 국제화 관리자 초기화 완료")

        # 이전 세션 상태 복원 (Phase 8로 대체됨)
        # self.restore_session_state()

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
                print(f"✅ TMDBClient 초기화 성공 (API 키: {api_key[:8]}...)")

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

            # ViewModel 초기화
            self.init_view_model()

            # Event Handler Manager 초기화 (event_bus가 설정된 후에 초기화됨)
            # self.event_handler_manager = EventHandlerManager(self)
            # self.event_handler_manager.setup_event_subscriptions()

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

            # 모든 서비스들 가져오기 (DI Container에서)
            self.file_scan_service = get_service(IFileScanService)
            print(f"✅ FileScanService 연결됨: {id(self.file_scan_service)}")

            self.file_organization_service = get_service(IFileOrganizationService)
            print(f"✅ FileOrganizationService 연결됨: {id(self.file_organization_service)}")

            self.media_data_service = get_service(IMediaDataService)
            print(f"✅ MediaDataService 연결됨: {id(self.media_data_service)}")

            self.tmdb_search_service = get_service(ITMDBSearchService)
            print(f"✅ TMDBSearchService 연결됨: {id(self.tmdb_search_service)}")

            self.ui_update_service = get_service(IUIUpdateService)
            print(f"✅ UIUpdateService 연결됨: {id(self.ui_update_service)}")

            # Safety System 초기화
            self.init_safety_system()
            print("✅ Safety System 초기화 완료")

            # Command System 초기화
            self.init_command_system()
            print("✅ Command System 초기화 완료")

            # Preflight System 초기화는 FileOrganizationHandler에서 처리됩니다

            # Journal System 초기화
            self.init_journal_system()
            print("✅ Journal System 초기화 완료")

            # Undo/Redo System 초기화
            self.init_undo_redo_system()
            print("✅ Undo/Redo System 초기화 완료")

            # UIUpdateService 초기화 (MainWindow 전달)
            self.ui_update_service.initialize(self)
            print("✅ UIUpdateService 초기화 완료")

            # EventHandlerManager 초기화 및 이벤트 구독 설정
            self.event_handler_manager = EventHandlerManager(self, self.event_bus)
            self.event_handler_manager.setup_event_subscriptions()

            # UI 초기화
            self.ui_initializer = UIInitializer(self)
            self.ui_initializer.init_ui()

            # TMDBSearchHandler 초기화
            from .handlers.tmdb_search_handler import TMDBSearchHandler

            self.tmdb_search_handler = TMDBSearchHandler(self)

            # TMDB 검색 시그널-슬롯 연결
            if hasattr(self, "anime_data_manager"):
                self.anime_data_manager.tmdb_search_requested.connect(
                    self.tmdb_search_handler.on_tmdb_search_requested
                )
                print("✅ TMDB 검색 시그널-슬롯 연결 완료")

            print("✅ TMDB Search Handler 초기화 완료")

            # FileOrganizationHandler 초기화
            from .handlers.file_organization_handler import FileOrganizationHandler

            self.file_organization_handler = FileOrganizationHandler(self)
            self.file_organization_handler.init_preflight_system()
            print("✅ File Organization Handler 초기화 완료")

            # Status Bar Manager 초기화
            self.status_bar_manager = StatusBarManager(self)
            print("✅ Status Bar Manager 초기화 완료")

            # UI 초기화 완료 후 연결 설정
            self.setup_connections()

            print("✅ 새로운 아키텍처 컴포넌트 초기화 완료")

        except Exception as e:
            print(f"❌ 새로운 아키텍처 초기화 실패: {e}")
            # 기본값으로 설정 (기존 동작 유지)
            self.event_bus = None
            self.file_scan_service = None
            self.file_organization_service = None
            self.media_data_service = None
            self.tmdb_search_service = None
            self.ui_update_service = None

    def init_ui_state_management(self):
        """Phase 8: UI 상태 관리 및 마이그레이션 초기화"""
        try:
            # UI 상태 관리자 초기화
            self.ui_state_manager = UIStateManager(self)
            print("✅ UI State Manager 초기화 완료")

            # UI 마이그레이션 관리자 초기화
            self.ui_migration_manager = UIMigrationManager(self)
            print("✅ UI Migration Manager 초기화 완료")

            # UI 상태 복원
            self.ui_state_manager.restore_ui_state()
            print("✅ UI 상태 복원 완료")

            # 마이그레이션 상태 확인 및 처리
            self._handle_ui_migration()

        except Exception as e:
            print(f"❌ UI 상태 관리 초기화 실패: {e}")

    def _handle_ui_migration(self):
        """UI 마이그레이션 상태 확인 및 처리"""
        try:
            migration_info = self.ui_migration_manager.get_migration_info()
            current_version = migration_info["current_version"]

            print(f"📋 현재 UI 버전: {current_version}")

            if current_version == "1.0":
                # v1에서 v2로 마이그레이션 가능한지 확인
                if self.ui_migration_manager.is_migration_available():
                    print("🔄 UI v2 마이그레이션이 가능합니다.")
                    # 자동 마이그레이션은 사용자 확인 후 진행
                    # self.ui_migration_manager.start_migration_to_v2()
                else:
                    print("⚠️ UI v2 마이그레이션이 불가능합니다.")
            elif current_version == "2.0":
                print("✅ UI v2가 이미 활성화되어 있습니다.")

                # v2 레이아웃 유효성 검증
                is_valid, errors = self.ui_migration_manager.validate_v2_layout()
                if not is_valid:
                    print(f"⚠️ UI v2 레이아웃 검증 실패: {errors}")
                else:
                    print("✅ UI v2 레이아웃 검증 완료")

        except Exception as e:
            print(f"❌ UI 마이그레이션 처리 실패: {e}")

    def init_safety_system(self):
        """Safety System 초기화"""
        try:
            from .managers.safety_system_manager import SafetySystemManager

            # Safety System Manager 초기화
            self.safety_system_manager = SafetySystemManager(self)
            print("✅ Safety System Manager 초기화 완료")

        except Exception as e:
            print(f"⚠️ Safety System 초기화 실패: {e}")
            self.safety_system_manager = None

    def init_command_system(self):
        """Command System 초기화"""
        try:
            from .managers.command_system_manager import CommandSystemManager

            # Command System Manager 초기화
            self.command_system_manager = CommandSystemManager(self)
            print("✅ Command System Manager 초기화 완료")

        except Exception as e:
            print(f"⚠️ Command System 초기화 실패: {e}")
            self.command_system_manager = None

    # Preflight System 초기화는 FileOrganizationHandler에서 처리됩니다

    def init_journal_system(self):
        """Journal System 초기화"""
        try:
            from app import IJournalManager, IRollbackEngine

            # Journal Manager 가져오기
            self.journal_manager = get_service(IJournalManager)
            print(f"✅ JournalManager 연결됨: {id(self.journal_manager)}")

            # Rollback Engine 가져오기
            self.rollback_engine = get_service(IRollbackEngine)
            print(f"✅ RollbackEngine 연결됨: {id(self.rollback_engine)}")

        except Exception as e:
            print(f"⚠️ Journal System 초기화 실패: {e}")
            self.journal_manager = None
            self.rollback_engine = None

    def init_undo_redo_system(self):
        """Undo/Redo System 초기화"""
        try:
            # CommandSystemManager에서 이미 처리됨
            print("✅ Undo/Redo System 초기화 완료 (CommandSystemManager에서 처리)")

        except Exception as e:
            print(f"⚠️ Undo/Redo System 초기화 실패: {e}")

    # UI Command 시스템 초기화는 CommandSystemManager에서 처리됩니다

    def init_view_model(self):
        """ViewModel 초기화"""
        try:
            # Python path에 src 디렉토리 추가
            import sys
            from pathlib import Path

            src_dir = Path(__file__).parent.parent
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))

            from gui.view_models.main_window_view_model_new import MainWindowViewModelNew

            print("📋 [MainWindow] ViewModel 초기화 시작...")

            # ViewModel 인스턴스 생성
            self.view_model = MainWindowViewModelNew()
            print(f"✅ [MainWindow] ViewModel 생성됨: {id(self.view_model)}")

            # ViewModel과 MainWindow 바인딩 설정
            if self.event_bus:
                print("🔗 [MainWindow] ViewModel과 EventBus 연결 중...")
                # ViewModel의 이벤트 발행을 MainWindow에서 처리할 필요가 있다면 여기서 설정
                # 현재는 ViewModel이 독립적으로 EventBus를 통해 통신함

            print("✅ [MainWindow] ViewModel 초기화 완료")

        except Exception as e:
            print(f"❌ [MainWindow] ViewModel 초기화 실패: {e}")
            import traceback

            traceback.print_exc()
            # 폴백: ViewModel 없이 동작
            self.view_model = None

    # 이벤트 구독 설정은 EventHandlerManager에서 처리됩니다

    # 이벤트 핸들러들은 EventHandlerManager에서 처리됩니다

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

    # UI 초기화는 UIInitializer에서 처리됩니다
    # def init_ui(self):
    #     """UI 초기화"""
    #     # UIInitializer로 이동됨

    # 메뉴바 생성은 MenuBuilder에서 처리됩니다
    # def create_menu_bar(self):
    #     """메뉴바 생성"""
    #     # MenuBuilder로 이동됨

    # 상태바 생성은 UIInitializer에서 처리됩니다
    # def create_status_bar(self):
    #     """상태바 생성"""
    #     # UIInitializer로 이동됨

    def setup_connections(self):
        """시그널/슬롯 연결 설정"""
        try:
            # 툴바 연결 (안전하게 연결)
            if hasattr(self, "main_toolbar") and self.main_toolbar:
                # 기본 툴바의 경우 이미 액션들이 연결되어 있음
                pass

            # 패널 연결 (패널이 존재하는 경우에만)
            if hasattr(self, "left_panel") and self.left_panel:
                try:
                    self.left_panel.source_folder_selected.connect(self.on_source_folder_selected)
                    self.left_panel.source_files_selected.connect(self.on_source_files_selected)
                    self.left_panel.destination_folder_selected.connect(
                        self.on_destination_folder_selected
                    )
                    self.left_panel.scan_started.connect(self.on_scan_started)
                    self.left_panel.scan_paused.connect(self.on_scan_paused)
                    self.left_panel.settings_opened.connect(self.on_settings_opened)
                    self.left_panel.completed_cleared.connect(self.on_completed_cleared)
                except Exception as e:
                    print(f"⚠️ 패널 연결 실패: {e}")

            # 결과 뷰 연결
            if hasattr(self, "results_view") and self.results_view:
                try:
                    self.results_view.group_selected.connect(self.on_group_selected)
                except Exception as e:
                    print(f"⚠️ 결과 뷰 연결 실패: {e}")

            print("✅ 시그널/슬롯 연결 설정 완료")

        except Exception as e:
            print(f"❌ 시그널/슬롯 연결 설정 실패: {e}")

    # 툴바 시그널 핸들러 메서드들
    def on_scan_requested(self):
        """툴바에서 스캔 요청 처리"""
        try:
            print("🔍 툴바에서 스캔 요청됨")
            # 기존 스캔 로직 호출
            if hasattr(self, "left_panel") and self.left_panel:
                self.left_panel.start_scan()
            else:
                print("⚠️ left_panel이 초기화되지 않음")
        except Exception as e:
            print(f"❌ 스캔 요청 처리 실패: {e}")

    def on_preview_requested(self):
        """툴바에서 미리보기 요청 처리"""
        try:
            print("👁️ 툴바에서 미리보기 요청됨")
            # 기존 미리보기 로직 호출
            if hasattr(self, "file_organization_handler"):
                self.file_organization_handler.show_preview()
            else:
                print("⚠️ file_organization_handler가 초기화되지 않음")
        except Exception as e:
            print(f"❌ 미리보기 요청 처리 실패: {e}")

    def on_organize_requested(self):
        """툴바에서 정리 실행 요청 처리"""
        try:
            print("🚀 툴바에서 정리 실행 요청됨")
            # 기존 정리 실행 로직 호출
            if hasattr(self, "file_organization_handler"):
                self.file_organization_handler.start_file_organization()
            else:
                print("⚠️ file_organization_handler가 초기화되지 않음")
        except Exception as e:
            print(f"❌ 정리 실행 요청 처리 실패: {e}")

    def on_search_text_changed(self, text: str):
        """툴바에서 검색 텍스트 변경 처리"""
        try:
            print(f"🔍 검색 텍스트 변경: {text}")
            # 검색 로직 구현 (나중에 구현)
            # 현재는 로그만 출력
        except Exception as e:
            print(f"❌ 검색 텍스트 변경 처리 실패: {e}")

    def on_settings_requested(self):
        """툴바에서 설정 요청 처리"""
        try:
            print("⚙️ 툴바에서 설정 요청됨")
            # 설정 다이얼로그 직접 호출
            self.show_settings_dialog()
        except Exception as e:
            print(f"❌ 설정 요청 처리 실패: {e}")

    # 패널 시그널 핸들러 메서드들
    def on_scan_started(self):
        """스캔 시작 처리"""
        try:
            print("🔍 스캔 시작됨")
            self.start_scan()
        except Exception as e:
            print(f"❌ 스캔 시작 처리 실패: {e}")

    def on_scan_paused(self):
        """스캔 일시정지 처리"""
        try:
            print("⏸️ 스캔 일시정지됨")
            self.stop_scan()
        except Exception as e:
            print(f"❌ 스캔 일시정지 처리 실패: {e}")

    def on_settings_opened(self):
        """설정 열기 처리"""
        try:
            print("⚙️ 설정 열기 요청됨")
            self.show_settings_dialog()
        except Exception as e:
            print(f"❌ 설정 열기 처리 실패: {e}")

    def on_completed_cleared(self):
        """완료된 항목 정리 처리"""
        try:
            print("🧹 완료된 항목 정리 요청됨")
            self.clear_completed()
        except Exception as e:
            print(f"❌ 완료된 항목 정리 처리 실패: {e}")

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
        has_source = (self.source_directory and Path(self.source_directory).exists()) or (
            self.source_directory and len(self.source_files) > 0
        )

        self.left_panel.update_scan_button_state(has_source)

        # 정리 실행 버튼 상태 업데이트
        has_groups = False
        if hasattr(self, "anime_data_manager"):
            grouped_items = self.anime_data_manager.get_grouped_items()
            has_groups = len(grouped_items) > 0 and any(
                group_id != "ungrouped" for group_id in grouped_items
            )

        has_destination = self.destination_directory and Path(self.destination_directory).exists()
        self.main_toolbar.set_organize_enabled(has_groups and has_destination)

        if has_source:
            if self.source_directory:
                self.update_status_bar(f"스캔 준비 완료: {self.source_directory}")
            elif self.source_files:
                self.update_status_bar(f"스캔 준비 완료: {len(self.source_files)}개 파일")
        else:
            self.update_status_bar("소스 디렉토리나 파일을 선택해주세요")

    # TMDB 검색 관련 메서드들은 TMDBSearchHandler에서 처리됩니다

    def restore_table_column_widths(self):
        """테이블 컬럼 너비 복원"""
        try:
            if not self.settings_manager:
                return

            settings = self.settings_manager.settings
            column_widths = getattr(settings, "table_column_widths", {})

            if (
                column_widths
                and hasattr(self, "central_triple_layout")
                and hasattr(self.central_triple_layout, "results_view")
            ):
                results_view = self.central_triple_layout.results_view

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

            if hasattr(self, "central_triple_layout") and hasattr(
                self.central_triple_layout, "results_view"
            ):
                results_view = self.central_triple_layout.results_view

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
                    f"파일 파싱 중... {i + 1}/{len(file_paths)} ({progress}%)", progress
                )

                # 비디오 파일 크기 확인 (1MB 미만 제외 - 더미 파일 방지)
                # 참고: 자막 파일은 별도로 연관 검색하므로 여기서 제외하지 않음
                try:
                    file_size = Path(file_path).stat().st_size
                    if file_size < 1024 * 1024:  # 1MB 미만
                        print(
                            f"⚠️ 비디오 파일 크기가 너무 작음 (제외): {Path(file_path).name} ({file_size} bytes)"
                        )
                        # TODO: 활동 로그 기능을 새로운 레이아웃에 구현 필요
                        print(f"⚠️ 제외됨: {Path(file_path).name} (크기: {file_size} bytes)")
                        continue
                except OSError:
                    print(f"⚠️ 파일 크기 확인 실패 (제외): {Path(file_path).name}")
                    # TODO: 활동 로그 기능을 새로운 레이아웃에 구현 필요
                    print(f"⚠️ 제외됨: {Path(file_path).name} (파일 접근 불가)")
                    continue

                # 파일 파싱
                print(f"🔍 파싱 시작: {Path(file_path).name}")
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
                    log_message = f"✅ {Path(file_path).name} - {parsed_metadata.title} S{parsed_item.season:02d}E{parsed_item.episode:02d}"
                    # TODO: 활동 로그 기능을 새로운 레이아웃에 구현 필요
                    print(log_message)

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
                    self.update_status_bar(f"파일명 파싱 실패: {Path(file_path).name}")

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
                self.update_status_bar(f"파일 처리 오류: {Path(file_path).name} - {str(e)}")

        # 파싱된 항목들을 데이터 관리자에 추가
        if parsed_items:
            self.anime_data_manager.add_items(parsed_items)

            # 그룹화 수행
            self.anime_data_manager.group_similar_titles()
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

        # status_progress가 None이 아닐 때만 설정
        if hasattr(self, "status_progress") and self.status_progress:
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
        """디렉토리 스캔 - ViewModel로 위임"""
        try:
            # 비즈니스 로직은 ViewModel에서 처리
            if hasattr(self, "view_model") and self.view_model:
                print(f"📋 [MainWindow] ViewModel을 통한 디렉토리 스캔: {directory_path}")
                self.view_model.start_directory_scan(directory_path)
            elif self.file_scan_service:
                # 폴백: 직접 서비스 호출
                print(f"🚀 [MainWindow] 백그라운드 서비스로 디렉토리 스캔: {directory_path}")
                self.current_scan_id = self.file_scan_service.scan_directory(
                    directory_path=directory_path,
                    recursive=True,
                    extensions={".mkv", ".mp4", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"},
                    min_size_mb=1.0,
                    max_size_gb=50.0,
                )
                print(f"🆔 [MainWindow] 백그라운드 작업 ID: {self.current_scan_id}")

                # UI 상태 업데이트
                self.update_status_bar("백그라운드에서 파일 스캔 중...", 0)
            else:
                # 마지막 폴백: 기존 방식 사용
                print("⚠️ [MainWindow] FileScanService를 사용할 수 없음, 기존 방식으로 스캔")
                self._scan_directory_legacy(directory_path)

        except Exception as e:
            self.show_error_message(f"디렉토리 스캔 오류: {str(e)}")
            print(f"❌ [MainWindow] 디렉토리 스캔 오류: {e}")
            # 폴백: 기존 방식으로 재시도
            self._scan_directory_legacy(directory_path)

    def _scan_directory_legacy(self, directory_path: str):
        """기존 방식 디렉토리 스캔 (폴백용)"""
        try:
            video_extensions = (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm")
            video_files = []

            for file_path in Path(directory_path).rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                    # 비디오 파일 크기 확인 (1MB 미만 제외 - 더미 파일 방지)
                    try:
                        file_size = file_path.stat().st_size
                        if file_size < 1024 * 1024:  # 1MB 미만
                            print(
                                f"⚠️ 비디오 파일 크기가 너무 작음 (제외): {file_path.name} ({file_size} bytes)"
                            )
                            # TODO: 활동 로그 기능을 새로운 레이아웃에 구현 필요
                            print(f"⚠️ 제외됨: {file_path.name} (크기: {file_size} bytes)")
                            continue
                    except OSError:
                        print(f"⚠️ 파일 크기 확인 실패 (제외): {file_path.name}")
                        # TODO: 활동 로그 기능을 새로운 레이아웃에 구현 필요
                        print(f"⚠️ 제외됨: {file_path.name} (파일 접근 불가)")
                        continue

                    video_files.append(str(file_path))

            if video_files:
                self.update_status_bar(f"디렉토리에서 {len(video_files)}개 비디오 파일 발견")
                self.process_selected_files(video_files)
            else:
                self.update_status_bar("디렉토리에서 비디오 파일을 찾을 수 없습니다")

        except Exception as e:
            self.update_status_bar(f"디렉토리 스캔 오류: {str(e)}")
            print(f"디렉토리 스캔 오류: {e}")

    def stop_scan(self):
        """스캔 중지 - ViewModel로 위임"""
        try:
            # 비즈니스 로직은 ViewModel에서 처리
            if hasattr(self, "view_model") and self.view_model:
                print("📋 [MainWindow] ViewModel을 통한 스캔 중지")
                self.view_model.stop_current_scan()
            else:
                # 폴백: 직접 서비스 호출
                self.scanning = False

                # 새로운 FileScanService의 스캔 취소 시도
                if (
                    self.file_scan_service
                    and hasattr(self, "current_scan_id")
                    and self.current_scan_id
                ):
                    try:
                        success = self.file_scan_service.cancel_scan(self.current_scan_id)
                        if success:
                            print(f"✅ [MainWindow] 스캔 취소 요청 성공: {self.current_scan_id}")
                        else:
                            print(f"⚠️ [MainWindow] 스캔 취소 실패: {self.current_scan_id}")
                    except Exception as e:
                        print(f"❌ [MainWindow] 스캔 취소 중 오류: {e}")

                # UI 상태 업데이트
                self.left_panel.btnStart.setEnabled(True)
                self.left_panel.btnPause.setEnabled(False)
                self.update_status_bar("스캔이 중지되었습니다")

        except Exception as e:
            print(f"❌ [MainWindow] 스캔 중지 처리 실패: {e}")
            # 직접 UI 업데이트
            self.left_panel.btnStart.setEnabled(True)
            self.left_panel.btnPause.setEnabled(False)
            self.show_error_message("스캔 중지 중 오류가 발생했습니다")

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

    # 파일 정리 관련 메서드들은 FileOrganizationHandler에서 처리됩니다

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

                with Path(filename).open("w", newline="", encoding="utf-8") as csvfile:
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
                if settings.last_source_directory and Path(settings.last_source_directory).exists():
                    self.source_directory = settings.last_source_directory
                    # UI 업데이트
                    self.left_panel.update_source_directory_display(self.source_directory)

                if (
                    settings.last_destination_directory
                    and Path(settings.last_destination_directory).exists()
                ):
                    self.destination_directory = settings.last_destination_directory
                    # UI 업데이트
                    self.left_panel.update_destination_directory_display(self.destination_directory)

                # 마지막으로 선택한 파일들 복원
                if settings.last_source_files:
                    self.source_files = [f for f in settings.last_source_files if Path(f).exists()]
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
                except (ValueError, IndexError):
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
                    group_id != "ungrouped" for group_id in grouped_items
                )
                has_destination = (
                    self.destination_directory and Path(self.destination_directory).exists()
                )
                self.main_toolbar.set_organize_enabled(has_groups and has_destination)

                # 로그는 한 번만 출력
                print(f"✅ {group_count}개 그룹 표시 완료")

                # TMDB 검색 시작 (한 번만 실행되도록 플래그 확인)
                if not getattr(self, "_tmdb_search_started", False):
                    self._tmdb_search_started = True
                    if hasattr(self, "tmdb_search_handler"):
                        self.tmdb_search_handler.start_tmdb_search_for_groups()
                    else:
                        print("⚠️ TMDBSearchHandler가 초기화되지 않았습니다")
        except Exception as e:
            print(f"⚠️ 결과 표시 업데이트 실패: {e}")

    # TMDB 검색 관련 메서드들은 TMDBSearchHandler에서 처리됩니다

    # 파일 정리 관련 메서드들은 FileOrganizationHandler에서 처리됩니다

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
        """상태바 업데이트 - StatusBarManager로 위임"""
        if hasattr(self, "status_bar_manager") and self.status_bar_manager:
            self.status_bar_manager.update_status_bar(message, progress)
        else:
            # Fallback: 직접 업데이트
            if hasattr(self, "status_label"):
                self.status_label.setText(message)
            if progress is not None and hasattr(self, "status_progress"):
                self.status_progress.setValue(progress)

    def show_error_message(self, message: str, details: str = "", error_type: str = "error"):
        """오류 메시지 표시 - StatusBarManager로 위임"""
        if hasattr(self, "status_bar_manager") and self.status_bar_manager:
            self.status_bar_manager.show_error_message(message, details, error_type)
        else:
            # Fallback
            self.update_status_bar(f"❌ {message}")

    def show_success_message(self, message: str, details: str = "", auto_clear: bool = True):
        """성공 메시지 표시 - StatusBarManager로 위임"""
        if hasattr(self, "status_bar_manager") and self.status_bar_manager:
            self.status_bar_manager.show_success_message(message, details, auto_clear)
        else:
            # Fallback
            self.update_status_bar(f"✅ {message}")

    def update_progress(self, current: int, total: int, message: str = ""):
        """진행률 업데이트 - StatusBarManager로 위임"""
        if hasattr(self, "status_bar_manager") and self.status_bar_manager:
            self.status_bar_manager.update_progress(current, total, message)
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

        # 3열 레이아웃 반응형 처리
        if hasattr(self, "central_triple_layout"):
            self.central_triple_layout.handle_responsive_layout(window_width)

        # 좌측 도크 반응형 처리 (<1280px에서 자동 접힘)
        if window_width < 1280:
            if hasattr(self, "left_panel_dock") and self.left_panel_dock.isVisible():
                self.left_panel_dock.hide()
        else:
            if hasattr(self, "left_panel_dock") and not self.left_panel_dock.isVisible():
                # 사용자가 수동으로 숨기지 않았다면 다시 표시
                if not hasattr(self, "_user_dock_toggle") or not self._user_dock_toggle:
                    self.left_panel_dock.show()

        # 왼쪽 패널 크기 조정 (기존 로직)
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

    # FileOrganizationService, MediaDataService, TMDBSearchService 이벤트 핸들러들은 EventHandlerManager에서 처리됩니다

    def closeEvent(self, event):
        """프로그램 종료 시 이벤트 처리"""
        try:
            # Phase 8: UI 상태 저장
            if hasattr(self, "ui_state_manager"):
                self.ui_state_manager.save_ui_state()
                print("✅ 프로그램 종료 시 UI 상태 저장 완료")
            else:
                # 폴백: 기존 세션 상태 저장
                self.save_session_state()
                print("✅ 프로그램 종료 시 기존 세션 상태 저장 완료")
        except Exception as e:
            print(f"⚠️ 프로그램 종료 시 상태 저장 실패: {e}")

        # 기본 종료 처리
        super().closeEvent(event)

    # Safety System 이벤트 핸들러들은 EventHandlerManager에서 처리됩니다

    # Command System 이벤트 핸들러들은 EventHandlerManager에서 처리됩니다

    # Preflight System 이벤트 핸들러들은 EventHandlerManager에서 처리됩니다

    # Journal System 및 Undo/Redo System 이벤트 핸들러들은 EventHandlerManager에서 처리됩니다

    # Safety System 관련 메서드들은 SafetySystemManager에서 처리됩니다

    # Command System 관련 메서드들은 CommandSystemManager에서 처리됩니다

    def setup_log_dock(self):
        """로그 Dock 설정 (Phase 5)"""
        try:
            from .components import LogDock

            # LogDock 생성
            self.log_dock = LogDock(self)

            # 하단 영역에 추가
            self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)

            # 기본 상태: 숨김 (접힘)
            self.log_dock.setVisible(False)

            # Dock 상태 로드
            self.log_dock.load_dock_state()

            print("✅ 로그 Dock 설정 완료")

        except Exception as e:
            print(f"❌ 로그 Dock 설정 실패: {e}")
            self.log_dock = None

    def add_activity_log(self, message: str):
        """활동 로그 추가 (LogDock으로 리다이렉트)"""
        if hasattr(self, "log_dock") and self.log_dock:
            self.log_dock.add_activity_log(message)
        else:
            # 폴백: 콘솔에 출력
            print(f"[활동] {message}")

    def add_error_log(self, message: str):
        """오류 로그 추가 (LogDock으로 리다이렉트)"""
        if hasattr(self, "log_dock") and self.log_dock:
            self.log_dock.add_error_log(message)
        else:
            # 폴백: 콘솔에 출력
            print(f"[오류] {message}")

    def clear_logs(self):
        """로그 초기화 (LogDock으로 리다이렉트)"""
        if hasattr(self, "log_dock") and self.log_dock:
            self.log_dock.clear_logs()
        else:
            # 폴백: 콘솔에 출력
            print("[로그] 로그 클리어 요청됨")

    def toggle_log_dock(self):
        """로그 Dock 가시성 토글"""
        if hasattr(self, "log_dock") and self.log_dock:
            self.log_dock.toggle_visibility()

    def show_log_dock(self):
        """로그 Dock 표시"""
        if hasattr(self, "log_dock") and self.log_dock:
            self.log_dock.show_log_dock()

    def hide_log_dock(self):
        """로그 Dock 숨김"""
        if hasattr(self, "log_dock") and self.log_dock:
            self.log_dock.hide_log_dock()

    # Phase 9.2: 테마 관리 이벤트 핸들러
    def on_theme_changed(self, theme: str):
        """테마 변경 이벤트 처리"""
        print(f"🎨 테마가 {theme}로 변경되었습니다")

        # 테마 변경에 따른 추가 UI 조정
        if hasattr(self, "results_view") and self.results_view:
            # 결과 뷰의 테이블들에 테마 적용
            self._apply_theme_to_tables()

        # 상태바에 테마 정보 표시
        if hasattr(self, "status_bar_manager") and self.status_bar_manager:
            self.status_bar_manager.update_status_bar(f"테마가 {theme}로 변경되었습니다")

    def _apply_theme_to_tables(self):
        """테이블들에 현재 테마 적용"""
        try:
            # 모든 탭의 테이블에 테마 적용
            tables = [
                getattr(self.results_view, "all_group_table", None),
                getattr(self.results_view, "unmatched_group_table", None),
                getattr(self.results_view, "conflict_group_table", None),
                getattr(self.results_view, "duplicate_group_table", None),
                getattr(self.results_view, "completed_group_table", None),
            ]

            for table in tables:
                if table and hasattr(table, "viewport"):
                    # 테이블 뷰포트에 테마 적용
                    table.viewport().update()

        except Exception as e:
            print(f"⚠️ 테마 적용 중 오류 발생: {e}")

    def get_current_theme(self) -> str:
        """현재 테마 반환"""
        if hasattr(self, "theme_manager"):
            return self.theme_manager.get_current_theme()
        return "auto"

    def toggle_theme(self):
        """테마 토글 (라이트 ↔ 다크)"""
        if hasattr(self, "theme_manager"):
            self.theme_manager.toggle_theme()

    def reset_theme_to_auto(self):
        """자동 테마 모드로 복원"""
        if hasattr(self, "theme_manager"):
            self.theme_manager.reset_to_auto()

    # Phase 10.1: 접근성 관리 이벤트 핸들러
    def toggle_accessibility_mode(self):
        """접근성 모드 토글"""
        if hasattr(self, "accessibility_manager"):
            features = ["screen_reader_support", "keyboard_navigation", "focus_indicators"]
            current_info = self.accessibility_manager.get_accessibility_info()

            if current_info["screen_reader_support"]:
                self.accessibility_manager.disable_accessibility_features(features)
                print("🔧 접근성 모드 비활성화")
            else:
                self.accessibility_manager.enable_accessibility_features(features)
                print("🔧 접근성 모드 활성화")

    def toggle_high_contrast_mode(self):
        """고대비 모드 토글"""
        if hasattr(self, "accessibility_manager"):
            self.accessibility_manager.toggle_high_contrast_mode()

    def get_accessibility_info(self) -> dict:
        """접근성 정보 반환"""
        if hasattr(self, "accessibility_manager"):
            return self.accessibility_manager.get_accessibility_info()
        return {}

    # Phase 10.2: 국제화 관리 이벤트 핸들러
    def on_language_changed(self, language_code: str):
        """언어 변경 이벤트 처리"""
        print(f"🌍 언어가 {language_code}로 변경되었습니다")

        # UI 텍스트 업데이트
        self._update_ui_texts()

        # 상태바에 언어 변경 정보 표시
        if hasattr(self, "status_bar_manager") and self.status_bar_manager:
            language_name = self.i18n_manager.get_language_name(language_code)
            self.status_bar_manager.update_status_bar(f"언어가 {language_name}로 변경되었습니다")

    def _update_ui_texts(self):
        """UI 텍스트 업데이트 (번역 적용)"""
        try:
            if not hasattr(self, "i18n_manager"):
                return

            tr = self.i18n_manager.tr

            # 메인 윈도우 제목 업데이트
            self.setWindowTitle(tr("main_window_title", "AnimeSorter"))

            # 툴바 액션 텍스트 업데이트
            if hasattr(self, "main_toolbar"):
                toolbar = self.main_toolbar

                if hasattr(toolbar, "scan_action"):
                    toolbar.scan_action.setText(tr("scan_files", "파일 스캔"))
                    toolbar.scan_action.setToolTip(
                        tr("scan_files_desc", "선택된 폴더의 애니메이션 파일들을 스캔합니다")
                    )

                if hasattr(toolbar, "preview_action"):
                    toolbar.preview_action.setText(tr("preview_organization", "미리보기"))
                    toolbar.preview_action.setToolTip(
                        tr("preview_organization_desc", "정리 작업의 미리보기를 표시합니다")
                    )

                if hasattr(toolbar, "organize_action"):
                    toolbar.organize_action.setText(tr("organize_files", "파일 정리"))
                    toolbar.organize_action.setToolTip(
                        tr("organize_files_desc", "스캔된 파일들을 정리된 구조로 이동합니다")
                    )

                if hasattr(toolbar, "settings_action"):
                    toolbar.settings_action.setText(tr("settings", "설정"))
                    toolbar.settings_action.setToolTip(
                        tr("settings_desc", "애플리케이션 설정을 엽니다")
                    )

            # 결과 뷰 탭 텍스트 업데이트
            if hasattr(self, "results_view") and hasattr(self.results_view, "tab_widget"):
                tab_widget = self.results_view.tab_widget

                tab_texts = [
                    tr("tab_all", "전체"),
                    tr("tab_unmatched", "미매칭"),
                    tr("tab_conflict", "충돌"),
                    tr("tab_duplicate", "중복"),
                    tr("tab_completed", "완료"),
                ]

                for i, text in enumerate(tab_texts):
                    if i < tab_widget.count():
                        tab_widget.setTabText(i, text)

            print("✅ UI 텍스트 업데이트 완료")

        except Exception as e:
            print(f"⚠️ UI 텍스트 업데이트 실패: {e}")

    def change_language(self, language_code: str):
        """언어 변경"""
        if hasattr(self, "i18n_manager"):
            return self.i18n_manager.set_language(language_code)
        return False

    def get_current_language(self) -> str:
        """현재 언어 반환"""
        if hasattr(self, "i18n_manager"):
            return self.i18n_manager.get_current_language()
        return "ko"

    def get_supported_languages(self) -> dict:
        """지원 언어 목록 반환"""
        if hasattr(self, "i18n_manager"):
            return self.i18n_manager.get_supported_languages()
        return {"ko": "한국어", "en": "English"}

    def tr(self, key: str, fallback: str = None) -> str:
        """번역 함수"""
        if hasattr(self, "i18n_manager"):
            return self.i18n_manager.tr(key, fallback)
        return fallback if fallback else key

    def show_settings_dialog(self):
        """설정 다이얼로그 표시"""
        try:
            dialog = SettingsDialog(self.settings_manager, self)
            if dialog.exec_() == SettingsDialog.Accepted:
                # 설정이 변경되었을 때 처리
                self.settings_manager.save_settings()

                # 테마 설정 적용
                if hasattr(self, "theme_manager"):
                    new_theme = self.settings_manager.settings.get("theme", "auto")
                    self.theme_manager.apply_theme(new_theme)
                    print(f"✅ 테마가 '{new_theme}'로 변경되었습니다.")

                # 접근성 설정 적용
                if hasattr(self, "accessibility_manager"):
                    high_contrast = self.settings_manager.settings.get("high_contrast_mode", False)
                    if high_contrast != self.accessibility_manager.high_contrast_mode:
                        if high_contrast:
                            self.accessibility_manager.toggle_high_contrast_mode()
                        print(f"✅ 고대비 모드: {'활성화' if high_contrast else '비활성화'}")

                    keyboard_nav = self.settings_manager.settings.get("keyboard_navigation", True)
                    self.accessibility_manager.set_keyboard_navigation(keyboard_nav)

                    screen_reader = self.settings_manager.settings.get(
                        "screen_reader_support", True
                    )
                    self.accessibility_manager.set_screen_reader_support(screen_reader)

                # 언어 설정 적용
                if hasattr(self, "i18n_manager"):
                    new_language = self.settings_manager.settings.get("language", "ko")
                    if new_language != self.i18n_manager.get_current_language():
                        self.i18n_manager.set_language(new_language)
                        print(f"✅ 언어가 '{new_language}'로 변경되었습니다.")

                print("✅ 설정이 저장되고 적용되었습니다.")
        except Exception as e:
            print(f"❌ 설정 다이얼로그 표시 실패: {e}")
            QMessageBox.critical(self, "오류", f"설정 다이얼로그를 열 수 없습니다:\n{e}")
