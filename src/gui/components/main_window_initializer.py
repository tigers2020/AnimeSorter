"""
메인 윈도우 초기화 로직을 담당하는 클래스
MainWindow의 과도한 __init__ 메서드 로직을 분리하여 가독성과 유지보수성을 향상시킵니다.
"""

from typing import TYPE_CHECKING, Any

from PyQt5.QtWidgets import QMainWindow

# Legacy FileManager import removed - using FileProcessingManager's unified service instead
from src.core.file_parser import FileParser
from src.core.tmdb_client import TMDBClient
from src.core.unified_config import unified_config_manager
from src.gui.components.accessibility_manager import AccessibilityManager
from src.gui.components.i18n_manager import I18nManager
from src.gui.components.ui_migration_manager import UIMigrationManager
from src.gui.components.ui_state_manager import UIStateManager
from src.gui.handlers.event_handler_manager import EventHandlerManager
from src.gui.managers.anime_data_manager import AnimeDataManager
from src.gui.managers.file_processing_manager import FileProcessingManager
from src.gui.managers.status_bar_manager import StatusBarManager
from src.gui.managers.tmdb_manager import TMDBManager

if TYPE_CHECKING:
    from src.gui.initializers.ui_initializer import UIInitializer


class MainWindowInitializer:
    """메인 윈도우 초기화를 담당하는 클래스"""

    def __init__(self, main_window: QMainWindow) -> None:
        self.main_window = main_window
        self.settings_manager: Any | None = None
        self.file_parser: FileParser | None = None
        self.tmdb_client: TMDBClient | None = None
        # Legacy FileManager removed - using FileProcessingManager's unified service instead
        self.anime_data_manager: AnimeDataManager | None = None
        self.file_processing_manager: FileProcessingManager | None = None
        self.tmdb_manager: TMDBManager | None = None
        self.accessibility_manager: AccessibilityManager | None = None
        self.i18n_manager: I18nManager | None = None
        self.ui_state_manager: UIStateManager | None = None
        self.ui_migration_manager: UIMigrationManager | None = None
        self.event_handler_manager: EventHandlerManager | None = None
        self.status_bar_manager: StatusBarManager | None = None
        self.ui_initializer: UIInitializer | None = None

        # 새로운 아키텍처 관련 속성들
        self.event_bus: Any | None = None
        self.file_scan_service: Any | None = None
        self.file_organization_service: Any | None = None
        self.media_data_service: Any | None = None
        self.tmdb_search_service: Any | None = None
        self.ui_update_service: Any | None = None
        self.current_scan_id: str | None = None
        self.current_organization_id: str | None = None
        self.current_tmdb_search_id: str | None = None

        # UI Command 시스템 관련 속성들
        self.undo_stack_bridge: Any | None = None
        self.staging_manager: Any | None = None
        self.journal_manager: Any | None = None
        self.ui_command_bridge: Any | None = None

        # TMDB 검색 다이얼로그 저장
        self.tmdb_search_dialogs: dict[str, Any] = {}

        # 포스터 캐시
        self.poster_cache: dict[str, Any] = {}

        # TMDB 검색 플래그
        self._tmdb_search_started: bool = False

    def _init_core_components(self) -> None:
        """핵심 컴포넌트 초기화"""
        try:
            # 설정 관리자 초기화 (통합 설정 시스템 사용)
            self.settings_manager = unified_config_manager
            self.main_window.settings_manager = self.settings_manager

            # FileParser 초기화
            self.file_parser = FileParser()
            self.main_window.file_parser = self.file_parser

            # TMDBClient 초기화 (통합 설정에서 API 키 가져오기)
            services_section = unified_config_manager.get_section("services")
            api_key = ""
            if services_section:
                tmdb_config = getattr(services_section, "tmdb_api", {})
                # 딕셔너리에서 API 키 가져오기
                api_key = (
                    tmdb_config.get("api_key", "")
                    if isinstance(tmdb_config, dict)
                    else getattr(tmdb_config, "api_key", "")
                )

            print(f"🔍 TMDB API 키 확인: 통합 설정={api_key[:8] if api_key else '없음'}")
            if not api_key:
                print("⚠️ TMDB API 키가 통합 설정에 없습니다.")
                print("   통합 설정 파일에서 TMDB API 키를 설정하거나 환경 변수를 설정하세요.")
                self.tmdb_client = None
                self.main_window.tmdb_client = None
                return

            self.tmdb_client = TMDBClient(api_key=api_key)
            self.main_window.tmdb_client = self.tmdb_client
            print(f"✅ TMDBClient 초기화 성공 (API 키: {api_key[:8]}...)")

            # Legacy FileManager initialization removed - using FileProcessingManager's unified service instead
            # FileProcessingManager is initialized below and contains the unified file organization service

            print("✅ 핵심 컴포넌트 초기화 완료")

        except Exception as e:
            print(f"❌ 핵심 컴포넌트 초기화 실패: {e}")
            self.file_parser = None
            self.tmdb_client = None
            self.file_manager = None

    def _init_data_managers(self) -> None:
        """데이터 관리자 초기화"""
        try:
            # 애니메 데이터 관리자 초기화
            self.anime_data_manager = AnimeDataManager(tmdb_client=self.tmdb_client)
            self.main_window.anime_data_manager = self.anime_data_manager

            # 파일 처리 관리자 초기화
            self.file_processing_manager = FileProcessingManager()
            self.main_window.file_processing_manager = self.file_processing_manager

            # TMDBManager 초기화 시 API 키 전달
            api_key = unified_config_manager.get("services", "tmdb_api", {}).get("api_key", "")
            self.tmdb_manager = TMDBManager(api_key=api_key)
            self.main_window.tmdb_manager = self.tmdb_manager

            print("✅ 데이터 관리자 초기화 완료")

        except Exception as e:
            print(f"❌ 데이터 관리자 초기화 실패: {e}")

    def _init_new_architecture(self) -> None:
        """새로운 아키텍처 컴포넌트 초기화"""
        try:
            # 애플리케이션 서비스 설정
            from src.app.setup import setup_application_services

            setup_application_services()
            print("✅ 애플리케이션 서비스 설정 완료")

            # EventBus 가져오기 (전역 인스턴스)
            from src.app import (IFileScanService, IMediaDataService,
                                 ITMDBSearchService, IUIUpdateService,
                                 get_event_bus, get_service)

            self.event_bus = get_event_bus()
            self.main_window.event_bus = self.event_bus
            print(f"✅ EventBus 연결됨: {id(self.event_bus)}")

            # 모든 서비스들 가져오기 (DI Container에서)
            self.file_scan_service = get_service(IFileScanService)
            self.main_window.file_scan_service = self.file_scan_service
            print(f"✅ FileScanService 연결됨: {id(self.file_scan_service)}")

            # Legacy FileOrganizationService removed - using FileProcessingManager's unified service instead

            self.media_data_service = get_service(IMediaDataService)
            self.main_window.media_data_service = self.media_data_service
            print(f"✅ MediaDataService 연결됨: {id(self.media_data_service)}")

            self.tmdb_search_service = get_service(ITMDBSearchService)
            self.main_window.tmdb_search_service = self.tmdb_search_service
            print(f"✅ TMDBSearchService 연결됨: {id(self.tmdb_search_service)}")

            self.ui_update_service = get_service(IUIUpdateService)
            self.main_window.ui_update_service = self.ui_update_service
            print(f"✅ UIUpdateService 연결됨: {id(self.ui_update_service)}")

            # Safety System 초기화
            self._init_safety_system()
            print("✅ Safety System 초기화 완료")

            # Command System 초기화
            self._init_command_system()
            print("✅ Command System 초기화 완료")

            # Journal System 초기화
            self._init_journal_system()
            print("✅ Journal System 초기화 완료")

            # Undo/Redo System 초기화
            self._init_undo_redo_system()
            print("✅ Undo/Redo System 초기화 완료")

            # UIUpdateService 초기화 (MainWindow 전달)
            self.ui_update_service.initialize(self.main_window)
            print("✅ UIUpdateService 초기화 완료")

            # EventHandlerManager 초기화 및 이벤트 구독 설정
            self.event_handler_manager = EventHandlerManager(self.main_window, self.event_bus)
            self.main_window.event_handler_manager = self.event_handler_manager
            self.event_handler_manager.setup_event_subscriptions()

            # UI 초기화는 UIComponentManager에서 처리됨 (중복 제거)
            # self.ui_initializer = UIInitializer(self.main_window)
            # self.main_window.ui_initializer = self.ui_initializer
            # self.ui_initializer.init_ui()

            # TMDBSearchHandler 초기화
            from src.gui.handlers.tmdb_search_handler import TMDBSearchHandler

            self.main_window.tmdb_search_handler = TMDBSearchHandler(self.main_window)

            # TMDB 검색 시그널-슬롯 연결
            if not (
                hasattr(self.main_window, "anime_data_manager")
                and self.main_window.anime_data_manager
            ):
                print("❌ anime_data_manager가 없습니다")
                return

            print(f"🔍 anime_data_manager 존재: {self.main_window.anime_data_manager}")
            print(
                f"🔍 tmdb_search_handler 존재: {hasattr(self.main_window, 'tmdb_search_handler')}"
            )
            if not hasattr(self.main_window, "tmdb_search_handler"):
                print("❌ tmdb_search_handler가 없습니다")
                return

            self.main_window.anime_data_manager.tmdb_search_requested.connect(
                self.main_window.tmdb_search_handler.on_tmdb_search_requested
            )
            print("✅ TMDB 검색 시그널-슬롯 연결 완료")

            print("✅ TMDB Search Handler 초기화 완료")

            # FileOrganizationHandler 초기화
            try:
                print("🔧 FileOrganizationHandler 초기화 시작...")
                # FileOrganizationHandler import - 여러 방법 시도
                FileOrganizationHandler = None
                import_errors = []

                # 방법 1: 직접 import
                try:
                    from src.gui.handlers.file_organization_handler import \
                        FileOrganizationHandler

                    print("✅ 방법 1: 직접 import 성공")
                except ImportError as ie1:
                    import_errors.append(f"직접 import 실패: {ie1}")

                    # 방법 2: sys.path 추가 후 import
                    try:
                        import sys

                        if "src" not in sys.path:
                            sys.path.insert(0, "src")
                        from gui.handlers.file_organization_handler import \
                            FileOrganizationHandler

                        print("✅ 방법 2: sys.path 추가 후 import 성공")
                    except ImportError as ie2:
                        import_errors.append(f"sys.path 추가 후 import 실패: {ie2}")

                        # 방법 3: 절대 경로 import
                        try:
                            import importlib.util

                            spec = importlib.util.spec_from_file_location(
                                "file_organization_handler",
                                "src/gui/handlers/file_organization_handler.py",
                            )
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            FileOrganizationHandler = module.FileOrganizationHandler
                            print("✅ 방법 3: 절대 경로 import 성공")
                        except Exception as ie3:
                            import_errors.append(f"절대 경로 import 실패: {ie3}")

                if FileOrganizationHandler is None:
                    print("❌ 모든 import 방법 실패:")
                    for error in import_errors:
                        print(f"   {error}")
                    raise ImportError("FileOrganizationHandler를 import할 수 없습니다")

                self.main_window.file_organization_handler = FileOrganizationHandler(
                    self.main_window
                )
                print("✅ FileOrganizationHandler 인스턴스 생성 완료")

                # Preflight System 초기화 시도 (실패해도 기본 기능은 작동)
                try:
                    self.main_window.file_organization_handler.init_preflight_system()
                    print("✅ FileOrganizationHandler 초기화 및 Preflight System 완료")
                except Exception as e:
                    print(f"⚠️ Preflight System 초기화 실패 (기본 기능은 사용 가능): {e}")
                    print("✅ FileOrganizationHandler 기본 초기화 완료")

                # 초기화 상태 확인
                if not hasattr(self.main_window, "file_organization_handler"):
                    print("❌ file_organization_handler 속성 설정 실패")
                    return

                print(
                    f"✅ file_organization_handler 속성 설정됨: {type(self.main_window.file_organization_handler)}"
                )

            except Exception as e:
                print(f"❌ FileOrganizationHandler 초기화 실패: {e}")
                import traceback

                traceback.print_exc()
                self.main_window.file_organization_handler = None

            # Status Bar Manager 초기화
            self.status_bar_manager = StatusBarManager(self.main_window)
            self.main_window.status_bar_manager = self.status_bar_manager
            print("✅ Status Bar Manager 초기화 완료")

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

    def _init_safety_system(self) -> None:
        """Safety System 초기화"""
        try:
            from src.gui.managers.safety_system_manager import \
                SafetySystemManager

            self.main_window.safety_system_manager = SafetySystemManager(self.main_window)
            print("✅ Safety System Manager 초기화 완료")
        except Exception as e:
            print(f"⚠️ Safety System 초기화 실패: {e}")
            self.main_window.safety_system_manager = None

    def _init_command_system(self) -> None:
        """Command System 초기화"""
        try:
            from src.gui.managers.command_system_manager import \
                CommandSystemManager

            self.main_window.command_system_manager = CommandSystemManager(self.main_window)
            print("✅ Command System Manager 초기화 완료")
        except Exception as e:
            print(f"⚠️ Command System 초기화 실패: {e}")
            self.main_window.command_system_manager = None

    def _init_journal_system(self) -> None:
        """Journal System 초기화"""
        try:
            from app import IJournalManager, IRollbackEngine, get_service

            # Journal Manager 가져오기
            self.journal_manager = get_service(IJournalManager)
            self.main_window.journal_manager = self.journal_manager
            print(f"✅ JournalManager 연결됨: {id(self.journal_manager)}")

            # Rollback Engine 가져오기
            self.rollback_engine = get_service(IRollbackEngine)
            self.main_window.rollback_engine = self.rollback_engine
            print(f"✅ RollbackEngine 연결됨: {id(self.rollback_engine)}")

        except Exception as e:
            print(f"⚠️ Journal System 초기화 실패: {e}")
            self.main_window.journal_manager = None
            self.main_window.rollback_engine = None

    def _init_undo_redo_system(self) -> None:
        """Undo/Redo System 초기화"""
        try:
            # CommandSystemManager에서 이미 처리됨
            print("✅ Undo/Redo System 초기화 완료 (CommandSystemManager에서 처리)")
        except Exception as e:
            print(f"⚠️ Undo/Redo System 초기화 실패: {e}")

    def _init_ui_state_management(self) -> None:
        """UI 상태 관리 및 마이그레이션 초기화"""
        try:
            # UI 상태 관리자 초기화
            self.ui_state_manager = UIStateManager(self.main_window)
            self.main_window.ui_state_manager = self.ui_state_manager
            print("✅ UI State Manager 초기화 완료")

            # UI 마이그레이션 관리자 초기화
            self.ui_migration_manager = UIMigrationManager(self.main_window)
            self.main_window.ui_migration_manager = self.ui_migration_manager
            print("✅ UI Migration Manager 초기화 완료")

            # UI 상태 복원
            self.ui_state_manager.restore_ui_state()
            print("✅ UI 상태 복원 완료")

            # 마이그레이션 상태 확인 및 처리
            self._handle_ui_migration()

        except Exception as e:
            print(f"❌ UI 상태 관리 초기화 실패: {e}")

    def _handle_ui_migration(self) -> None:
        """UI 마이그레이션 상태 확인 및 처리"""
        try:
            migration_info = self.ui_migration_manager.get_migration_info()
            current_version = migration_info["current_version"]

            print(f"📋 현재 UI 버전: {current_version}")

            if current_version == "1.0":
                # v1에서 v2로 마이그레이션 가능한지 확인
                if not self.ui_migration_manager.is_migration_available():
                    print("⚠️ UI v2 마이그레이션이 불가능합니다.")
                    return

                print("🔄 UI v2 마이그레이션이 가능합니다.")
                # 자동 마이그레이션은 사용자 확인 후 진행
                # self.ui_migration_manager.start_migration_to_v2()
                return

            if current_version != "2.0":
                return

            print("✅ UI v2가 이미 활성화되어 있습니다.")

            # v2 레이아웃 유효성 검증
            is_valid, errors = self.ui_migration_manager.validate_v2_layout()
            if not is_valid:
                print(f"⚠️ UI v2 레이아웃 검증 실패: {errors}")
                return

            print("✅ UI v2 레이아웃 검증 완료")

        except Exception as e:
            print(f"❌ UI 마이그레이션 처리 실패: {e}")

    def _init_accessibility_and_i18n(self) -> None:
        """접근성 및 국제화 관리자 초기화"""
        try:
            # 접근성 관리자 초기화
            self.accessibility_manager = AccessibilityManager(self.main_window)
            self.main_window.accessibility_manager = self.accessibility_manager
            self.accessibility_manager.initialize(self.main_window)
            print("✅ 접근성 관리자 초기화 완료")

            # 국제화 관리자 초기화
            self.i18n_manager = I18nManager(self.main_window)
            self.main_window.i18n_manager = self.i18n_manager
            self.i18n_manager.initialize_with_system_language()
            self.i18n_manager.language_changed.connect(self.main_window.on_language_changed)
            print("✅ 국제화 관리자 초기화 완료")

        except Exception as e:
            print(f"❌ 접근성 및 국제화 관리자 초기화 실패: {e}")

    def apply_settings_to_ui(self) -> None:
        """설정을 UI 컴포넌트에 적용"""
        try:
            if not self.settings_manager:
                return

            # unified_config_manager의 경우 config 속성 사용
            if hasattr(self.settings_manager, "config"):
                config = self.settings_manager.config
                app_settings = config.application

                # 기본 설정 적용
                self.main_window.organize_mode = getattr(app_settings, "organize_mode", "이동")
                self.main_window.naming_scheme = getattr(app_settings, "naming_scheme", "standard")
                self.main_window.safe_mode = getattr(app_settings, "safe_mode", True)
                self.main_window.backup_before_organize = getattr(
                    app_settings, "backup_before_organize", False
                )
                self.main_window.prefer_anitopy = getattr(app_settings, "prefer_anitopy", True)
                self.main_window.fallback_parser = getattr(
                    app_settings, "fallback_parser", "GuessIt"
                )
                self.main_window.realtime_monitoring = getattr(
                    app_settings, "realtime_monitoring", False
                )
                self.main_window.auto_refresh_interval = getattr(
                    app_settings, "auto_refresh_interval", 30
                )
                self.main_window.tmdb_language = getattr(app_settings, "tmdb_language", "ko-KR")
                self.main_window.show_advanced_options = getattr(
                    app_settings, "show_advanced_options", False
                )
                self.main_window.log_level = getattr(app_settings, "log_level", "INFO")
                self.main_window.log_to_file = getattr(app_settings, "log_to_file", False)
                self.main_window.backup_location = getattr(app_settings, "backup_location", "")
                self.main_window.max_backup_count = getattr(app_settings, "max_backup_count", 10)
                # file_organization 설정
                file_org = app_settings.file_organization
                self.main_window.organize_mode = file_org.get("organize_mode", "이동")
                self.main_window.naming_scheme = file_org.get("naming_scheme", "standard")
                self.main_window.safe_mode = file_org.get("safe_mode", True)
                self.main_window.backup_before_organize = file_org.get(
                    "backup_before_organize", False
                )
                self.main_window.prefer_anitopy = file_org.get("prefer_anitopy", True)
                self.main_window.fallback_parser = file_org.get("fallback_parser", "GuessIt")
                self.main_window.realtime_monitoring = file_org.get("realtime_monitoring", False)
                self.main_window.auto_refresh_interval = file_org.get("auto_refresh_interval", 30)
                self.main_window.show_advanced_options = file_org.get(
                    "show_advanced_options", False
                )

                # TMDB 설정
                tmdb_config = self.settings_manager.config.services.tmdb_api
                self.main_window.tmdb_language = tmdb_config.get("language", "ko-KR")

            print("✅ UI 설정 적용 완료")

        except Exception as e:
            print(f"⚠️ UI 설정 적용 실패: {e}")
