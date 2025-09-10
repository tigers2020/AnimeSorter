"""
메인 윈도우 초기화 로직을 담당하는 클래스
MainWindow의 과도한 __init__ 메서드 로직을 분리하여 가독성과 유지보수성을 향상시킵니다.
"""

import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import QMainWindow

from src.core.file_parser import FileParser
from src.core.tmdb_client import TMDBClient
from src.core.unified_config import unified_config_manager
from src.gui.components.managers.accessibility_manager import \
    AccessibilityManager
from src.gui.components.managers.i18n_manager import I18nManager
from src.gui.components.managers.ui_migration_manager import UIMigrationManager
from src.gui.components.managers.ui_state_manager import UIStateManager
from src.gui.handlers.event_handler_manager import EventHandlerManager
from src.gui.managers.anime_data_manager import AnimeDataManager
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
        self.anime_data_manager: AnimeDataManager | None = None
        self.tmdb_manager: TMDBManager | None = None
        self.accessibility_manager: AccessibilityManager | None = None
        self.i18n_manager: I18nManager | None = None
        self.ui_state_manager: UIStateManager | None = None
        self.ui_migration_manager: UIMigrationManager | None = None
        self.event_handler_manager: EventHandlerManager | None = None
        self.status_bar_manager: StatusBarManager | None = None
        self.ui_initializer: UIInitializer | None = None
        self.event_bus: Any | None = None
        self.file_scan_service: Any | None = None
        self.file_organization_service: Any | None = None
        self.media_data_service: Any | None = None
        self.tmdb_search_service: Any | None = None
        self.ui_update_service: Any | None = None
        self.current_scan_id: str | None = None
        self.current_organization_id: str | None = None
        self.current_tmdb_search_id: str | None = None
        self.undo_stack_bridge: Any | None = None
        self.staging_manager: Any | None = None
        # Journal 시스템 제거됨
        self.ui_command_bridge: Any | None = None
        self.tmdb_search_dialogs: dict[str, Any] = {}
        self.poster_cache: dict[str, Any] = {}
        self._tmdb_search_started: bool = False

    def _init_core_components(self) -> None:
        """핵심 컴포넌트 초기화"""
        try:
            self.settings_manager = unified_config_manager
            self.main_window.settings_manager = self.settings_manager
            self.file_parser = FileParser()
            self.main_window.file_parser = self.file_parser
            services_section = unified_config_manager.get_section("services")
            api_key = ""
            if services_section:
                tmdb_config = getattr(services_section, "tmdb_api", {})
                api_key = (
                    tmdb_config.get("api_key", "")
                    if isinstance(tmdb_config, dict)
                    else getattr(tmdb_config, "api_key", "")
                )
            logger.info("🔍 TMDB API 키 확인: 통합 설정=%s", api_key[:8] if api_key else "없음")
            if not api_key:
                logger.info("⚠️ TMDB API 키가 통합 설정에 없습니다.")
                logger.info(
                    "   통합 설정 파일에서 TMDB API 키를 설정하거나 환경 변수를 설정하세요."
                )
                self.tmdb_client = None
                self.main_window.tmdb_client = None
                return
            self.tmdb_client = TMDBClient(api_key=api_key)
            self.main_window.tmdb_client = self.tmdb_client
            logger.info("✅ TMDBClient 초기화 성공 (API 키: %s...)", api_key[:8])
            logger.info("✅ 핵심 컴포넌트 초기화 완료")
        except Exception as e:
            logger.info(f"❌ 핵심 컴포넌트 초기화 실패: {e}")
            self.file_parser = None
            self.tmdb_client = None
            self.file_manager = None

    def _init_data_managers(self) -> None:
        """데이터 관리자 초기화"""
        try:
            self.anime_data_manager = AnimeDataManager(tmdb_client=self.tmdb_client)
            self.main_window.anime_data_manager = self.anime_data_manager
            from src.core.services.unified_file_organization_service import (
                FileOrganizationConfig, UnifiedFileOrganizationService)

            config = FileOrganizationConfig(safe_mode=True, backup_before_operation=True)
            self.file_organization_service = UnifiedFileOrganizationService(config)
            self.main_window.file_organization_service = self.file_organization_service
            api_key = unified_config_manager.get("services", "tmdb_api", {}).get("api_key", "")
            self.tmdb_manager = TMDBManager(api_key=api_key)
            self.main_window.tmdb_manager = self.tmdb_manager
            logger.info("✅ 데이터 관리자 초기화 완료")
        except Exception as e:
            logger.info(f"❌ 데이터 관리자 초기화 실패: {e}")

    def _init_new_architecture(self) -> None:
        """새로운 아키텍처 컴포넌트 초기화"""
        try:
            from src.app.setup import setup_application_services

            setup_application_services()
            logger.info("✅ 애플리케이션 서비스 설정 완료")
            from src.app import (IFileScanService, IMediaDataService,
                                 ITMDBSearchService, IUIUpdateService,
                                 get_event_bus, get_service)

            self.event_bus = get_event_bus()
            self.main_window.event_bus = self.event_bus
            logger.info(f"✅ EventBus 연결됨: {id(self.event_bus)}")
            self.file_scan_service = get_service(IFileScanService)
            self.main_window.file_scan_service = self.file_scan_service
            logger.info(f"✅ FileScanService 연결됨: {id(self.file_scan_service)}")
            self.media_data_service = get_service(IMediaDataService)
            self.main_window.media_data_service = self.media_data_service
            logger.info(f"✅ MediaDataService 연결됨: {id(self.media_data_service)}")
            self.tmdb_search_service = get_service(ITMDBSearchService)
            self.main_window.tmdb_search_service = self.tmdb_search_service
            logger.info(f"✅ TMDBSearchService 연결됨: {id(self.tmdb_search_service)}")
            self.ui_update_service = get_service(IUIUpdateService)
            self.main_window.ui_update_service = self.ui_update_service
            logger.info(f"✅ UIUpdateService 연결됨: {id(self.ui_update_service)}")
            self._init_safety_system()
            logger.info("✅ Safety System 초기화 완료")
            self._init_command_system()
            logger.info("✅ Command System 초기화 완료")
            # Journal 시스템 제거됨
            self._init_undo_redo_system()
            logger.info("✅ Undo/Redo System 초기화 완료")
            self.ui_update_service.initialize(self.main_window)
            logger.info("✅ UIUpdateService 초기화 완료")
            self.event_handler_manager = EventHandlerManager(self.main_window, self.event_bus)
            self.main_window.event_handler_manager = self.event_handler_manager
            self.event_handler_manager.setup_event_subscriptions()
            from src.gui.handlers.tmdb_search_handler import TMDBSearchHandler

            self.main_window.tmdb_search_handler = TMDBSearchHandler(self.main_window)
            if not (
                hasattr(self.main_window, "anime_data_manager")
                and self.main_window.anime_data_manager
            ):
                logger.info("❌ anime_data_manager가 없습니다")
                return
            logger.info(f"🔍 anime_data_manager 존재: {self.main_window.anime_data_manager}")
            logger.info(
                f"🔍 tmdb_search_handler 존재: {hasattr(self.main_window, 'tmdb_search_handler')}"
            )
            if not hasattr(self.main_window, "tmdb_search_handler"):
                logger.info("❌ tmdb_search_handler가 없습니다")
                return
            self.main_window.anime_data_manager.tmdb_search_requested.connect(
                self.main_window.tmdb_search_handler.on_tmdb_search_requested
            )
            logger.info("✅ TMDB 검색 시그널-슬롯 연결 완료")
            logger.info("✅ TMDB Search Handler 초기화 완료")
            try:
                logger.info("🔧 FileOrganizationHandler 초기화 시작...")
                FileOrganizationHandler = None
                import_errors = []
                try:
                    from src.gui.handlers.file_organization_handler import \
                        FileOrganizationHandler

                    logger.info("✅ 방법 1: 직접 import 성공")
                except ImportError as ie1:
                    import_errors.append(f"직접 import 실패: {ie1}")
                    try:
                        import sys

                        if "src" not in sys.path:
                            sys.path.insert(0, "src")
                        from gui.handlers.file_organization_handler import \
                            FileOrganizationHandler

                        logger.info("✅ 방법 2: sys.path 추가 후 import 성공")
                    except ImportError as ie2:
                        import_errors.append(f"sys.path 추가 후 import 실패: {ie2}")
                        try:
                            import importlib.util

                            spec = importlib.util.spec_from_file_location(
                                "file_organization_handler",
                                "src/gui/handlers/file_organization_handler.py",
                            )
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            FileOrganizationHandler = module.FileOrganizationHandler
                            logger.info("✅ 방법 3: 절대 경로 import 성공")
                        except Exception as ie3:
                            import_errors.append(f"절대 경로 import 실패: {ie3}")
                if FileOrganizationHandler is None:
                    logger.info("❌ 모든 import 방법 실패:")
                    for error in import_errors:
                        logger.info(f"   {error}")
                    raise ImportError("FileOrganizationHandler를 import할 수 없습니다")
                self.main_window.file_organization_handler = FileOrganizationHandler(
                    self.main_window
                )
                logger.info("✅ FileOrganizationHandler 인스턴스 생성 완료")
                try:
                    self.main_window.file_organization_handler.init_preflight_system()
                    logger.info("✅ FileOrganizationHandler 초기화 및 Preflight System 완료")
                except Exception as e:
                    logger.info(f"⚠️ Preflight System 초기화 실패 (기본 기능은 사용 가능): {e}")
                    logger.info("✅ FileOrganizationHandler 기본 초기화 완료")
                if not hasattr(self.main_window, "file_organization_handler"):
                    logger.info("❌ file_organization_handler 속성 설정 실패")
                    return
                logger.info(
                    f"✅ file_organization_handler 속성 설정됨: {type(self.main_window.file_organization_handler)}"
                )
            except Exception as e:
                logger.info(f"❌ FileOrganizationHandler 초기화 실패: {e}")
                import traceback

                traceback.print_exc()
                self.main_window.file_organization_handler = None
            self.status_bar_manager = StatusBarManager(self.main_window)
            self.main_window.status_bar_manager = self.status_bar_manager
            logger.info("✅ Status Bar Manager 초기화 완료")
            logger.info("✅ 새로운 아키텍처 컴포넌트 초기화 완료")
        except Exception as e:
            logger.info(f"❌ 새로운 아키텍처 초기화 실패: {e}")
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
            logger.info("✅ Safety System Manager 초기화 완료")
        except Exception as e:
            logger.info(f"⚠️ Safety System 초기화 실패: {e}")
            self.main_window.safety_system_manager = None

    def _init_command_system(self) -> None:
        """Command System 초기화"""
        try:
            from src.gui.managers.command_system_manager import \
                CommandSystemManager

            self.main_window.command_system_manager = CommandSystemManager(self.main_window)
            logger.info("✅ Command System Manager 초기화 완료")
        except Exception as e:
            logger.info(f"⚠️ Command System 초기화 실패: {e}")
            self.main_window.command_system_manager = None

    # Journal 시스템 제거됨

    def _init_undo_redo_system(self) -> None:
        """Undo/Redo System 초기화"""
        try:
            logger.info("✅ Undo/Redo System 초기화 완료 (CommandSystemManager에서 처리)")
        except Exception as e:
            logger.info(f"⚠️ Undo/Redo System 초기화 실패: {e}")

    def _init_ui_state_management(self) -> None:
        """UI 상태 관리 및 마이그레이션 초기화"""
        try:
            self.ui_state_manager = UIStateManager(self.main_window)
            self.main_window.ui_state_manager = self.ui_state_manager
            logger.info("✅ UI State Manager 초기화 완료")
            self.ui_migration_manager = UIMigrationManager(self.main_window)
            self.main_window.ui_migration_manager = self.ui_migration_manager
            logger.info("✅ UI Migration Manager 초기화 완료")
            self.ui_state_manager.restore_ui_state()
            logger.info("✅ UI 상태 복원 완료")
            self._handle_ui_migration()
        except Exception as e:
            logger.info(f"❌ UI 상태 관리 초기화 실패: {e}")

    def _handle_ui_migration(self) -> None:
        """UI 마이그레이션 상태 확인 및 처리"""
        try:
            migration_info = self.ui_migration_manager.get_migration_info()
            current_version = migration_info["current_version"]
            logger.info(f"📋 현재 UI 버전: {current_version}")
            if current_version == "1.0":
                if not self.ui_migration_manager.is_migration_available():
                    logger.info("⚠️ UI v2 마이그레이션이 불가능합니다.")
                    return
                logger.info("🔄 UI v2 마이그레이션이 가능합니다.")
                return
            if current_version != "2.0":
                return
            logger.info("✅ UI v2가 이미 활성화되어 있습니다.")
            is_valid, errors = self.ui_migration_manager.validate_v2_layout()
            if not is_valid:
                logger.info(f"⚠️ UI v2 레이아웃 검증 실패: {errors}")
                return
            logger.info("✅ UI v2 레이아웃 검증 완료")
        except Exception as e:
            logger.info(f"❌ UI 마이그레이션 처리 실패: {e}")

    def _init_accessibility_and_i18n(self) -> None:
        """접근성 및 국제화 관리자 초기화"""
        try:
            self.accessibility_manager = AccessibilityManager(self.main_window)
            self.main_window.accessibility_manager = self.accessibility_manager
            self.accessibility_manager.initialize(self.main_window)
            logger.info("✅ 접근성 관리자 초기화 완료")
            self.i18n_manager = I18nManager(self.main_window)
            self.main_window.i18n_manager = self.i18n_manager
            self.i18n_manager.initialize_with_system_language()
            self.i18n_manager.language_changed.connect(self.main_window.on_language_changed)
            logger.info("✅ 국제화 관리자 초기화 완료")
        except Exception as e:
            logger.info(f"❌ 접근성 및 국제화 관리자 초기화 실패: {e}")

    def apply_settings_to_ui(self) -> None:
        """설정을 UI 컴포넌트에 적용"""
        try:
            if not self.settings_manager:
                return
            if hasattr(self.settings_manager, "config"):
                config = self.settings_manager.config
                app_settings = config.application
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
                tmdb_config = self.settings_manager.config.services.tmdb_api
                self.main_window.tmdb_language = tmdb_config.get("language", "ko-KR")
            logger.info("✅ UI 설정 적용 완료")
        except Exception as e:
            logger.info(f"⚠️ UI 설정 적용 실패: {e}")
