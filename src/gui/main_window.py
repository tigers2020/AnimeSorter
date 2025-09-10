"""
리팩토링된 메인 윈도우 - AnimeSorter의 주요 GUI 인터페이스
컴포넌트 기반 아키텍처로 재구성되어 가독성과 유지보수성이 향상되었습니다.
"""

import logging
from pathlib import Path

from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import QHeaderView, QMainWindow, QMessageBox

from src.core.tmdb_client import TMDBClient
from src.core.unified_config import unified_config_manager
from src.core.unified_event_system import get_unified_event_bus
from src.gui.components.dialogs.settings_dialog import SettingsDialog
from src.gui.components.main_window_coordinator import MainWindowCoordinator
from src.gui.components.managers.theme_manager import ThemeManager
from src.gui.components.message_log_controller import MessageLogController
from src.gui.components.theme_controller import ThemeController
from src.gui.components.ui_state_controller import UIStateController
from src.gui.managers.anime_data_manager import AnimeDataManager
from src.gui.managers.tmdb_manager import TMDBManager
from src.gui.theme.engine.variable_loader import VariableLoader as TokenLoader


class MainWindow(QMainWindow):
    """AnimeSorter 메인 윈도우 (리팩토링된 버전)"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnimeSorter")
        self.setGeometry(100, 100, 1600, 900)
        from PyQt5.QtWidgets import QVBoxLayout, QWidget

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.parent_layout = QVBoxLayout(self.central_widget)
        self.parent_layout.setContentsMargins(0, 0, 0, 0)
        self.parent_layout.setSpacing(0)
        self.coordinator = MainWindowCoordinator(self)
        self.scanning = False
        self.progress = 0
        self.source_files = []
        self.source_directory = ""
        self.destination_directory = ""
        self.status_progress = None
        self.settings_manager = unified_config_manager
        self.unified_event_bus = get_unified_event_bus()
        self.theme_manager = ThemeManager()
        self.session_manager = None  # MainWindowSessionManager로 초기화됨
        theme_dir = Path(__file__).parent.parent.parent / "data" / "theme"
        self.token_loader = TokenLoader(theme_dir)
        self.coordinator.initialize_all_components()
        self._init_new_controllers()
        self._setup_new_controllers()
        self._connect_new_controller_signals()
        self._apply_theme()
        self.setup_connections()
        self._connect_theme_signals()
        self._connect_unified_event_system()
        logger.info("🔧 MainWindow 핸들러들 초기화 시작...")
        try:
            self._initialize_handlers()
            logger.info("✅ MainWindow 핸들러들 초기화 완료")
        except Exception as e:
            logger.error("❌ MainWindow 핸들러들 초기화 실패: %s", e)
            import traceback

            traceback.print_exc()
        logger.info("🔧 설정을 UI에 적용 시작...")
        try:
            self.apply_settings_to_ui()
            logger.info("✅ 설정을 UI에 적용 완료")
        except Exception as e:
            logger.error("❌ 설정을 UI에 적용 실패: %s", e)
            import traceback

            traceback.print_exc()
        if not hasattr(self, "anime_data_manager") or not hasattr(self, "file_processing_manager"):
            self.init_data_managers()
        else:
            logger.info("✅ 데이터 매니저들이 이미 MainWindowCoordinator에서 초기화됨")
        self.current_scan_id = None
        self.current_organization_id = None
        self.current_tmdb_search_id = None

    def _schedule_handler_initialization(self):
        """핸들러 초기화를 이벤트 루프 후에 예약합니다"""
        from PyQt5.QtCore import QTimer

        def delayed_handler_init():
            logger.info("🔧 MainWindow 핸들러들 지연 초기화 시작...")
            try:
                self._initialize_handlers()
                logger.info("✅ MainWindow 핸들러들 지연 초기화 완료")
            except Exception as e:
                logger.info(f"❌ MainWindow 핸들러들 지연 초기화 실패: {e}")
                import traceback

                traceback.print_exc()

        QTimer.singleShot(100, delayed_handler_init)
        self.theme_monitor_widget = None

    def publish_event(self, event):
        """통합 이벤트 시스템을 통해 이벤트를 발행합니다"""
        try:
            if self.unified_event_bus:
                return self.unified_event_bus.publish(event)
            logger.info("⚠️ 통합 이벤트 버스가 초기화되지 않았습니다")
            return False
        except Exception as e:
            logger.info(f"❌ 이벤트 발행 실패: {e}")
            return False

    def _apply_theme(self):
        """테마를 적용합니다 (Theme Controller를 통해)"""
        try:
            if hasattr(self, "theme_controller"):
                self.theme_controller.apply_theme(main_window=self)
            else:
                logger.info("⚠️ ThemeController가 초기화되지 않음")
        except Exception as e:
            logger.info(f"❌ 테마 적용 중 오류 발생: {e}")

    def _connect_theme_signals(self):
        """테마 변경 시그널을 연결합니다"""
        try:
            self.theme_manager.theme_changed.connect(self._on_theme_changed)
            self.theme_manager.icon_theme_changed.connect(self._on_icon_theme_changed)
            logger.info("✅ 테마 변경 시그널 연결 완료")
        except Exception as e:
            logger.info(f"❌ 테마 시그널 연결 실패: {e}")

    def _connect_unified_event_system(self):
        """통합 이벤트 시스템을 연결합니다"""
        try:
            self.unified_event_bus.event_published.connect(self._on_event_published)
            self.unified_event_bus.event_handled.connect(self._on_event_handled)
            self.unified_event_bus.event_failed.connect(self._on_event_failed)
            logger.info("✅ 통합 이벤트 시스템 연결 완료")
        except Exception as e:
            logger.info(f"❌ 통합 이벤트 시스템 연결 실패: {e}")

    def _init_new_controllers(self):
        """새로운 컨트롤러들을 초기화합니다"""
        try:
            self.theme_controller = ThemeController(self.theme_manager, self.settings_manager)
            self.ui_state_controller = UIStateController(self.settings_manager)
            self.message_log_controller = MessageLogController()
            logger.info("✅ 새로운 컨트롤러들 초기화 완료")
        except Exception as e:
            logger.info(f"❌ 새로운 컨트롤러 초기화 실패: {e}")

    def _setup_new_controllers(self):
        """새로운 컨트롤러들을 설정합니다"""
        try:
            self.theme_controller.setup()
            self.ui_state_controller.setup()
            self.message_log_controller.setup()
            logger.info("✅ 새로운 컨트롤러들 설정 완료")
        except Exception as e:
            logger.info(f"❌ 새로운 컨트롤러 설정 실패: {e}")

    def _connect_new_controller_signals(self):
        """새로운 컨트롤러들의 시그널을 연결합니다"""
        try:
            self.theme_controller.theme_applied.connect(self._on_theme_controller_theme_applied)
            self.theme_controller.theme_detection_failed.connect(
                self._on_theme_controller_detection_failed
            )
            self.theme_controller.system_theme_changed.connect(
                self._on_theme_controller_system_theme_changed
            )
            self.ui_state_controller.state_saved.connect(self._on_ui_state_controller_state_saved)
            self.ui_state_controller.state_restored.connect(
                self._on_ui_state_controller_state_restored
            )
            self.ui_state_controller.accessibility_mode_changed.connect(
                self._on_ui_state_controller_accessibility_changed
            )
            self.ui_state_controller.high_contrast_mode_changed.connect(
                self._on_ui_state_controller_high_contrast_changed
            )
            self.ui_state_controller.language_changed.connect(
                self._on_ui_state_controller_language_changed
            )
            self.message_log_controller.message_shown.connect(
                self._on_message_log_controller_message_shown
            )
            self.message_log_controller.log_added.connect(self._on_message_log_controller_log_added)
            self.message_log_controller.status_updated.connect(
                self._on_message_log_controller_status_updated
            )
            logger.info("✅ 새로운 컨트롤러 시그널 연결 완료")
        except Exception as e:
            logger.info(f"❌ 새로운 컨트롤러 시그널 연결 실패: {e}")

    def _on_theme_changed(self, theme: str):
        """테마가 변경되었을 때 호출됩니다"""
        try:
            logger.info(f"🎨 테마 변경: {theme}")
        except Exception as e:
            logger.info(f"❌ 테마 변경 처리 중 오류: {e}")

    def _on_icon_theme_changed(self, icon_theme: str):
        """아이콘 테마가 변경되었을 때 호출됩니다"""
        try:
            logger.info(f"🖼️ 아이콘 테마 변경: {icon_theme}")
        except Exception as e:
            logger.info(f"❌ 아이콘 테마 변경 처리 중 오류: {e}")

    def _on_event_published(self, event):
        """이벤트가 발행되었을 때 호출됩니다"""
        try:
            logger.info(
                f"📢 이벤트 발행: {event.__class__.__name__} (source: {event.source}, priority: {event.priority})"
            )
        except Exception as e:
            logger.info(f"❌ 이벤트 발행 처리 중 오류: {e}")

    def _on_event_handled(self, event_type: str, handler_name: str):
        """이벤트가 처리되었을 때 호출됩니다"""
        try:
            logger.info(f"✅ 이벤트 처리: {event_type} -> {handler_name}")
        except Exception as e:
            logger.info(f"❌ 이벤트 처리 완료 처리 중 오류: {e}")

    def _on_event_failed(self, event_type: str, handler_name: str, error: str):
        """이벤트 처리에 실패했을 때 호출됩니다"""
        try:
            logger.info(f"❌ 이벤트 처리 실패: {event_type} -> {handler_name} - {error}")
        except Exception as e:
            logger.info(f"❌ 이벤트 처리 실패 처리 중 오류: {e}")

    def _on_theme_controller_theme_applied(self, theme: str):
        """Theme Controller의 테마 적용 시그널을 처리합니다"""
        try:
            logger.info(f"🎨 Theme Controller: 테마 적용됨 - {theme}")
        except Exception as e:
            logger.info(f"❌ Theme Controller 테마 적용 처리 중 오류: {e}")

    def _on_theme_controller_detection_failed(self, error: str):
        """Theme Controller의 테마 감지 실패 시그널을 처리합니다"""
        try:
            logger.info(f"⚠️ Theme Controller: 테마 감지 실패 - {error}")
        except Exception as e:
            logger.info(f"❌ Theme Controller 테마 감지 실패 처리 중 오류: {e}")

    def _on_theme_controller_system_theme_changed(self, theme: str):
        """Theme Controller의 시스템 테마 변경 시그널을 처리합니다"""
        try:
            logger.info(f"🔄 Theme Controller: 시스템 테마 변경됨 - {theme}")
        except Exception as e:
            logger.info(f"❌ Theme Controller 시스템 테마 변경 처리 중 오류: {e}")

    def _on_ui_state_controller_state_saved(self, state_type: str):
        """UI State Controller의 상태 저장 시그널을 처리합니다"""
        try:
            logger.info(f"💾 UI State Controller: 상태 저장됨 - {state_type}")
        except Exception as e:
            logger.info(f"❌ UI State Controller 상태 저장 처리 중 오류: {e}")

    def _on_ui_state_controller_state_restored(self, state_type: str):
        """UI State Controller의 상태 복원 시그널을 처리합니다"""
        try:
            logger.info(f"📂 UI State Controller: 상태 복원됨 - {state_type}")
        except Exception as e:
            logger.info(f"❌ UI State Controller 상태 복원 처리 중 오류: {e}")

    def _on_ui_state_controller_accessibility_changed(self, mode: str):
        """UI State Controller의 접근성 모드 변경 시그널을 처리합니다"""
        try:
            logger.info(f"♿ UI State Controller: 접근성 모드 변경됨 - {mode}")
        except Exception as e:
            logger.info(f"❌ UI State Controller 접근성 모드 변경 처리 중 오류: {e}")

    def _on_ui_state_controller_high_contrast_changed(self, enabled: bool):
        """UI State Controller의 고대비 모드 변경 시그널을 처리합니다"""
        try:
            logger.info(f"🌓 UI State Controller: 고대비 모드 변경됨 - {enabled}")
        except Exception as e:
            logger.info(f"❌ UI State Controller 고대비 모드 변경 처리 중 오류: {e}")

    def _on_ui_state_controller_language_changed(self, language: str):
        """UI State Controller의 언어 변경 시그널을 처리합니다"""
        try:
            logger.info(f"🌐 UI State Controller: 언어 변경됨 - {language}")
        except Exception as e:
            logger.info(f"❌ UI State Controller 언어 변경 처리 중 오류: {e}")

    def _on_message_log_controller_message_shown(self, message_type: str, message: str):
        """Message Log Controller의 메시지 표시 시그널을 처리합니다"""
        try:
            logger.info(f"💬 Message Log Controller: 메시지 표시됨 - {message_type}: {message}")
        except Exception as e:
            logger.info(f"❌ Message Log Controller 메시지 표시 처리 중 오류: {e}")

    def _on_message_log_controller_log_added(self, log_type: str, content: str):
        """Message Log Controller의 로그 추가 시그널을 처리합니다"""
        try:
            logger.info(f"📝 Message Log Controller: 로그 추가됨 - {log_type}: {content}")
        except Exception as e:
            logger.info(f"❌ Message Log Controller 로그 추가 처리 중 오류: {e}")

    def _on_message_log_controller_status_updated(self, status: str):
        """Message Log Controller의 상태 업데이트 시그널을 처리합니다"""
        try:
            logger.info(f"📊 Message Log Controller: 상태 업데이트됨 - {status}")
        except Exception as e:
            logger.info(f"❌ Message Log Controller 상태 업데이트 처리 중 오류: {e}")

    def _initialize_handlers(self):
        """MainWindow 핸들러들을 초기화합니다."""
        try:
            # MainWindowFileHandler 초기화
            if hasattr(self, "file_organization_service") and hasattr(self, "anime_data_manager"):
                from src.gui.components.main_window.handlers.file_handler import \
                    MainWindowFileHandler

                self.file_handler = MainWindowFileHandler(
                    main_window=self,
                    file_organization_service=self.file_organization_service,
                    file_parser=getattr(self, "file_parser", None),
                    file_scan_service=getattr(self, "file_scan_service", None),
                )
                logger.info("✅ MainWindowFileHandler 초기화 완료")
            else:
                logger.info("⚠️ MainWindowFileHandler 초기화 실패: 필요한 매니저들이 없습니다")
                self.file_handler = None

            # MainWindowLayoutManager 초기화
            from src.gui.components.main_window.handlers.layout_manager import \
                MainWindowLayoutManager

            self.layout_manager = MainWindowLayoutManager(main_window=self)
            logger.info("✅ MainWindowLayoutManager 초기화 완료")

            # MainWindowMenuActionHandler 초기화
            from src.gui.components.main_window.handlers.menu_action_handler import \
                MainWindowMenuActionHandler

            self.menu_action_handler = MainWindowMenuActionHandler(main_window=self)
            logger.info("✅ MainWindowMenuActionHandler 초기화 완료")

            # FileOrganizationHandler 초기화 (중요: 파일 정리 기능)
            try:
                logger.info("🔧 FileOrganizationHandler 초기화 시작...")
                from src.gui.handlers.file_organization_handler import \
                    FileOrganizationHandler

                logger.info("✅ FileOrganizationHandler import 성공")
                self.file_organization_handler = FileOrganizationHandler(main_window=self)
                logger.info("✅ FileOrganizationHandler 초기화 완료")
            except Exception as e:
                logger.error(f"❌ FileOrganizationHandler 초기화 실패: {e}")
                import traceback

                logger.error(
                    f"❌ FileOrganizationHandler 초기화 실패 상세: {traceback.format_exc()}"
                )
                self.file_organization_handler = None

            # MainWindowSessionManager 초기화
            try:
                if hasattr(self, "settings_manager"):
                    from src.gui.components.main_window.handlers.session_manager import \
                        MainWindowSessionManager

                    self.session_manager = MainWindowSessionManager(
                        main_window=self, unified_config_manager=self.settings_manager
                    )
                    logger.info("✅ MainWindowSessionManager 초기화 완료")
                else:
                    logger.info(
                        "⚠️ MainWindowSessionManager 초기화 실패: unified_config_manager가 없습니다"
                    )
                    self.session_manager = None
            except Exception as e:
                logger.error(f"❌ MainWindowSessionManager 초기화 실패: {e}")
                self.session_manager = None

            logger.info("✅ MainWindow 핸들러들 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"❌ MainWindow 핸들러 초기화 중 오류: {e}")
            import traceback

            traceback.print_exc()
            return False

    def init_core_components(self):
        """핵심 컴포넌트 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_core_components()
        logger.info("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_new_architecture(self):
        """새로운 아키텍처 컴포넌트 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_new_architecture()
        logger.info("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_ui_state_management(self):
        """Phase 8: UI 상태 관리 및 마이그레이션 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_ui_state_management()
        logger.info("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_safety_system(self):
        """Safety System 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_safety_system()
        logger.info("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_command_system(self):
        """Command System 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_command_system()
        logger.info("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    # Journal 시스템 제거됨

    def init_undo_redo_system(self):
        """Undo/Redo System 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_undo_redo_system()
        logger.info("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_view_model(self):
        """ViewModel 초기화"""
        try:
            import sys
            from pathlib import Path

            src_dir = Path(__file__).parent.parent
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))
            from src.gui.view_models.main_window_view_model_new import \
                MainWindowViewModelNew

            logger.info("📋 [MainWindow] ViewModel 초기화 시작...")
            self.view_model = MainWindowViewModelNew()
            logger.info(f"✅ [MainWindow] ViewModel 생성됨: {id(self.view_model)}")
            if self.event_bus:
                logger.info("🔗 [MainWindow] ViewModel과 EventBus 연결 중...")
            logger.info("✅ [MainWindow] ViewModel 초기화 완료")
        except Exception as e:
            logger.info(f"❌ [MainWindow] ViewModel 초기화 실패: {e}")
            import traceback

            traceback.print_exc()
            self.view_model = None

    def init_data_managers(self):
        """데이터 관리자 초기화"""
        self.anime_data_manager = AnimeDataManager(tmdb_client=self.tmdb_client)
        from src.core.services.unified_file_organization_service import (
            FileOrganizationConfig, UnifiedFileOrganizationService)

        config = FileOrganizationConfig(safe_mode=True, backup_before_operation=True)
        self.file_organization_service = UnifiedFileOrganizationService(config)
        api_key = unified_config_manager.get("services", "tmdb_api", {}).get("api_key", "")
        self.tmdb_manager = TMDBManager(api_key=api_key)

    def apply_settings_to_ui(self):
        """설정을 UI 컴포넌트에 적용 - MainWindowSessionManager로 위임"""
        if self.session_manager:
            self.session_manager.apply_settings_to_ui()
        else:
            logger.info("⚠️ MainWindowSessionManager가 초기화되지 않았습니다")

    def initialize_data(self):
        """초기 데이터 설정"""
        self.scanning = False
        self.progress = 0
        self.source_directory = None
        self.source_files = []
        self.destination_directory = None

    def setup_connections(self):
        """시그널/슬롯 연결 설정"""
        try:
            if hasattr(self, "main_toolbar") and self.main_toolbar:
                pass
            if hasattr(self, "left_panel") and self.left_panel:
                try:
                    self.left_panel.source_folder_selected.connect(self.on_source_folder_selected)
                    self.left_panel.source_files_selected.connect(self.on_source_files_selected)
                    self.left_panel.destination_folder_selected.connect(
                        self.on_destination_folder_selected
                    )
                    self.left_panel.scan_paused.connect(self.on_scan_paused)
                    self.left_panel.settings_opened.connect(self.on_settings_opened)
                    self.left_panel.completed_cleared.connect(self.on_completed_cleared)
                except Exception as e:
                    logger.info(f"⚠️ 패널 연결 실패: {e}")
            if hasattr(self, "results_view") and self.results_view:
                try:
                    self.results_view.group_selected.connect(self.on_group_selected)
                except Exception as e:
                    logger.info(f"⚠️ 결과 뷰 연결 실패: {e}")
            logger.info("✅ 시그널/슬롯 연결 설정 완료")
        except Exception as e:
            logger.info(f"❌ 시그널/슬롯 연결 설정 실패: {e}")

    def on_scan_requested(self):
        """툴바에서 스캔 요청 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_scan_requested()
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_preview_requested(self):
        """툴바에서 미리보기 요청 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_preview_requested()
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_organize_requested(self):
        """툴바에서 정리 실행 요청 처리 - MainWindowMenuActionHandler로 위임"""
        logger.info("🗂️ 툴바에서 정리 요청됨")
        logger.info("📍 호출 스택:")
        import traceback

        for line in traceback.format_stack()[-3:-1]:
            logger.info(f"   {line.strip()}")
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            logger.info("✅ MainWindowMenuActionHandler 존재함")
            self.menu_action_handler.on_organize_requested()
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_search_text_changed(self, text: str):
        """툴바에서 검색 텍스트 변경 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_search_text_changed(text)
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_settings_requested(self):
        """툴바에서 설정 요청 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_settings_requested()
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_scan_started(self):
        """스캔 시작 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "tmdb_search_handler") and self.tmdb_search_handler:
            self.tmdb_search_handler.reset_for_new_scan()
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_scan_started()
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_scan_paused(self):
        """스캔 일시정지 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_scan_paused()
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_settings_opened(self):
        """설정 열기 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_settings_opened()
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_completed_cleared(self):
        """완료된 항목 정리 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_completed_cleared()
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_source_folder_selected(self, folder_path: str):
        """소스 폴더 선택 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_source_folder_selected(folder_path)
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_source_files_selected(self, file_paths: list[str]):
        """소스 파일 선택 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_source_files_selected(file_paths)
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_destination_folder_selected(self, folder_path: str):
        """대상 폴더 선택 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_destination_folder_selected(folder_path)
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def update_scan_button_state(self):
        """스캔 시작 버튼 활성화 상태 업데이트"""
        has_source = (
            self.source_directory
            and Path(self.source_directory).exists()
            or self.source_directory
            and len(self.source_files) > 0
        )
        self.left_panel.update_scan_button_state(has_source)
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

    def restore_table_column_widths(self):
        """테이블 컬럼 너비 복원 - MainWindowSessionManager로 위임"""
        if self.session_manager:
            settings = self.settings_manager.settings
            column_widths = getattr(settings, "table_column_widths", {})
            self.session_manager.restore_table_column_widths(column_widths)
        else:
            logger.info("⚠️ MainWindowSessionManager가 초기화되지 않았습니다")

    def get_table_column_widths(self):
        """테이블 컬럼 너비 가져오기 - MainWindowSessionManager로 위임"""
        if self.session_manager:
            return self.session_manager.get_table_column_widths()
        logger.info("⚠️ MainWindowSessionManager가 초기화되지 않았습니다")
        return {}

    def process_selected_files(self, file_paths: list[str]):
        """선택된 파일들을 처리하고 메타데이터 검색 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.process_selected_files(file_paths)
        else:
            logger.info("⚠️ MainWindowFileHandler가 초기화되지 않았습니다")

    def start_scan(self):
        """스캔 시작 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.start_scan()
        else:
            logger.info("⚠️ MainWindowFileHandler가 초기화되지 않았습니다")

    def scan_directory(self, directory_path: str):
        """디렉토리 스캔 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.scan_directory(directory_path)
        else:
            logger.info("⚠️ MainWindowFileHandler가 초기화되지 않았습니다")

    def stop_scan(self):
        """스캔 중지 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.stop_scan()
        else:
            logger.info("⚠️ MainWindowFileHandler가 초기화되지 않았습니다")

    def clear_completed(self):
        """완료된 항목 정리"""
        self.anime_data_manager.clear_completed_items()
        stats = self.anime_data_manager.get_stats()
        self.left_panel.update_stats(stats["total"], stats["parsed"], stats["pending"])
        self.update_status_bar("완료된 항목이 정리되었습니다")

    def reset_filters(self):
        """필터 초기화"""
        self.main_toolbar.reset_filters()
        self.update_status_bar("필터가 초기화되었습니다")

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
            self.apply_settings_to_ui()
            if hasattr(self, "tmdb_client"):
                api_key = self.settings_manager.config.services.tmdb_api.api_key
                if api_key and (not self.tmdb_client or self.tmdb_client.api_key != api_key):
                    self.tmdb_client = TMDBClient(api_key=api_key)
                    logger.info("✅ TMDBClient 재초기화 완료")
        except Exception as e:
            logger.info(f"⚠️ 설정 변경 처리 실패: {e}")

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
        """이전 세션 상태 복원 - MainWindowSessionManager로 위임"""
        if self.session_manager:
            self.session_manager.restore_session_state()
        else:
            logger.info("⚠️ MainWindowSessionManager가 초기화되지 않았습니다")

    def save_session_state(self):
        """현재 세션 상태 저장 - MainWindowSessionManager로 위임"""
        if self.session_manager:
            self.session_manager.save_session_state()
        else:
            logger.info("⚠️ MainWindowSessionManager가 초기화되지 않았습니다")

    def update_results_display(self):
        """결과 표시 업데이트"""
        try:
            logger.info(
                f'🔍 [update_results_display] anime_data_manager 존재: {hasattr(self, "anime_data_manager")}'
            )
            if hasattr(self, "anime_data_manager") and self.anime_data_manager:
                logger.info(
                    f"🔍 [update_results_display] anime_data_manager.items 개수: {len(self.anime_data_manager.items)}"
                )
                grouped_items = self.anime_data_manager.get_grouped_items()
                logger.info(f"🔍 [update_results_display] grouped_items: {len(grouped_items)}개")
                logger.info(
                    f'🔍 [update_results_display] grouped_model 존재: {hasattr(self, "grouped_model")}'
                )

                if hasattr(self, "grouped_model") and self.grouped_model:
                    self.grouped_model.set_grouped_items(grouped_items)
                    logger.info("✅ grouped_model에 데이터 설정 완료")
                else:
                    logger.warning("⚠️ grouped_model이 초기화되지 않았습니다")

                stats = self.anime_data_manager.get_stats()
                group_count = len(grouped_items)
                self.update_status_bar(
                    f"총 {stats['total']}개 파일이 {group_count}개 그룹으로 분류되었습니다"
                )
                has_groups = len(grouped_items) > 0 and any(
                    group_id != "ungrouped" for group_id in grouped_items
                )
                has_destination = (
                    self.destination_directory and Path(self.destination_directory).exists()
                )
                self.main_toolbar.set_organize_enabled(has_groups and has_destination)
                logger.info(f"✅ {group_count}개 그룹 표시 완료")
                if hasattr(self, "tmdb_search_handler") and self.tmdb_search_handler:
                    logger.info("🚀 TMDB 검색 시작!")
                    self.tmdb_search_handler.start_tmdb_search_for_groups()
                else:
                    logger.info("⚠️ TMDBSearchHandler가 초기화되지 않았습니다")
            else:
                logger.warning("❌ anime_data_manager가 초기화되지 않았습니다")
        except Exception as e:
            logger.error(f"❌ 결과 표시 업데이트 실패: {e}")
            import traceback

            traceback.print_exc()

    def on_group_selected(self, group_info: dict):
        """그룹 선택 시 상세 파일 목록 업데이트 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_group_selected(group_info)
        else:
            logger.info("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def update_status_bar(self, message, progress=None):
        """상태바 업데이트 - StatusBarManager로 위임"""
        if hasattr(self, "status_bar_manager") and self.status_bar_manager:
            self.status_bar_manager.update_status_bar(message, progress)
        else:
            if hasattr(self, "status_label"):
                self.status_label.setText(message)
            if progress is not None and hasattr(self, "status_progress"):
                self.status_progress.setValue(progress)

    def update_progress(self, current: int, total: int, message: str = ""):
        """진행률 업데이트 - StatusBarManager로 위임"""
        if hasattr(self, "status_bar_manager") and self.status_bar_manager:
            self.status_bar_manager.update_progress(current, total, message)
        elif total > 0:
            progress = int(current / total * 100)
            self.update_status_bar(f"{message} ({current}/{total})", progress)
        else:
            self.update_status_bar(message)

    def on_resize_event(self, event):
        """윈도우 크기 변경 이벤트 처리"""
        super().resizeEvent(event)
        self.update_layout_on_resize()

    def update_layout_on_resize(self):
        """크기 변경 시 레이아웃 업데이트 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.update_layout_on_resize()
        else:
            logger.info("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

    def adjust_table_columns(self):
        """테이블 컬럼 크기를 윈도우 크기에 맞게 조정"""
        if not hasattr(self, "results_view"):
            return
        if hasattr(self.results_view, "group_table"):
            group_table = self.results_view.group_table
            if group_table.model():
                header = group_table.horizontalHeader()
                model = group_table.model()
                if hasattr(model, "get_column_widths"):
                    column_widths = model.get_column_widths()
                    stretch_columns = model.get_stretch_columns()
                    for col in range(header.count()):
                        if col in stretch_columns:
                            header.setSectionResizeMode(col, QHeaderView.Stretch)
                        else:
                            header.setSectionResizeMode(col, QHeaderView.Fixed)
                            if col in column_widths:
                                header.resizeSection(col, column_widths[col])
        if hasattr(self.results_view, "detail_table"):
            detail_table = self.results_view.detail_table
            if detail_table.model():
                header = detail_table.horizontalHeader()
                model = detail_table.model()
                if hasattr(model, "get_column_widths"):
                    column_widths = model.get_column_widths()
                    stretch_columns = model.get_stretch_columns()
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
            if hasattr(self, "ui_state_controller") and self.ui_state_controller:
                self.ui_state_controller.save_session_state()
                logger.info("✅ 프로그램 종료 시 UI 상태 저장 완료")
            else:
                logger.info("⚠️ UIStateController가 초기화되지 않았습니다")
        except Exception as e:
            logger.info(f"⚠️ 프로그램 종료 시 상태 저장 실패: {e}")
        super().closeEvent(event)

    def setup_log_dock(self):
        """로그 Dock 설정 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.setup_log_dock()
        else:
            logger.info("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

    def toggle_log_dock(self):
        """로그 Dock 가시성 토글 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.toggle_log_dock()
        else:
            logger.info("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

    def show_log_dock(self):
        """로그 Dock 표시 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.show_log_dock()
        else:
            logger.info("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

    def hide_log_dock(self):
        """로그 Dock 숨김 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.hide_log_dock()
        else:
            logger.info("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

    def toggle_accessibility_mode(self):
        """접근성 모드 토글"""
        if hasattr(self, "accessibility_manager"):
            features = ["screen_reader_support", "keyboard_navigation", "focus_indicators"]
            current_info = self.accessibility_manager.get_accessibility_info()
            if current_info["screen_reader_support"]:
                self.accessibility_manager.disable_accessibility_features(features)
                logger.info("🔧 접근성 모드 비활성화")
            else:
                self.accessibility_manager.enable_accessibility_features(features)
                logger.info("🔧 접근성 모드 활성화")

    def toggle_high_contrast_mode(self):
        """고대비 모드 토글"""
        if hasattr(self, "accessibility_manager"):
            self.accessibility_manager.toggle_high_contrast_mode()

    def get_accessibility_info(self) -> dict:
        """접근성 정보 반환"""
        if hasattr(self, "accessibility_manager"):
            return self.accessibility_manager.get_accessibility_info()
        return {}

    def on_language_changed(self, language_code: str):
        """언어 변경 이벤트 처리"""
        logger.info(f"🌍 언어가 {language_code}로 변경되었습니다")
        self._update_ui_texts()
        if hasattr(self, "status_bar_manager") and self.status_bar_manager:
            language_name = self.i18n_manager.get_language_name(language_code)
            self.status_bar_manager.update_status_bar(f"언어가 {language_name}로 변경되었습니다")

    def _update_ui_texts(self):
        """UI 텍스트 업데이트 (번역 적용)"""
        try:
            if not hasattr(self, "i18n_manager"):
                return
            tr = self.i18n_manager.tr
            self.setWindowTitle(tr("main_window_title", "AnimeSorter"))
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
            logger.info("✅ UI 텍스트 업데이트 완료")
        except Exception as e:
            logger.info(f"⚠️ UI 텍스트 업데이트 실패: {e}")

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
                self.settings_manager.save_config()
                if hasattr(self, "accessibility_manager"):
                    high_contrast = getattr(
                        self.settings_manager.config.user_preferences, "high_contrast_mode", False
                    )
                    if high_contrast != self.accessibility_manager.high_contrast_mode:
                        if high_contrast:
                            self.accessibility_manager.toggle_high_contrast_mode()
                        logger.info(f"✅ 고대비 모드: {'활성화' if high_contrast else '비활성화'}")
                    keyboard_nav = getattr(
                        self.settings_manager.config.user_preferences, "keyboard_navigation", True
                    )
                    self.accessibility_manager.set_keyboard_navigation(keyboard_nav)
                    screen_reader = getattr(
                        self.settings_manager.config.user_preferences, "screen_reader_support", True
                    )
                    self.accessibility_manager.set_screen_reader_support(screen_reader)
                if hasattr(self, "i18n_manager"):
                    new_language = getattr(
                        self.settings_manager.config.user_preferences, "language", "ko"
                    )
                    if new_language != self.i18n_manager.get_current_language():
                        self.i18n_manager.set_language(new_language)
                        logger.info(f"✅ 언어가 '{new_language}'로 변경되었습니다.")
                logger.info("✅ 설정이 저장되고 적용되었습니다.")
        except Exception as e:
            logger.info(f"❌ 설정 다이얼로그 표시 실패: {e}")
            QMessageBox.critical(self, "오류", f"설정 다이얼로그를 열 수 없습니다:\n{e}")

    def show_theme_monitor(self):
        """테마 모니터링 위젯 표시"""
        try:
            if not self.theme_monitor_widget:
                from src.gui.theme.theme_monitor_widget import \
                    ThemeMonitorWidget

                self.theme_monitor_widget = ThemeMonitorWidget(self.theme_manager, self)
            if self.theme_monitor_widget.isVisible():
                self.theme_monitor_widget.raise_()
                self.theme_monitor_widget.activateWindow()
            else:
                self.theme_monitor_widget.show()
            logger.info("✅ 테마 모니터링 위젯이 표시되었습니다.")
        except Exception as e:
            logger.info(f"❌ 테마 모니터링 위젯 표시 실패: {e}")
            QMessageBox.critical(self, "오류", f"테마 모니터링 위젯을 열 수 없습니다:\n{e}")

    def _init_new_controllers(self):
        """새로 생성한 컨트롤러들을 초기화합니다"""
        try:
            self.theme_controller = None
            self.ui_state_controller = None
            self.message_log_controller = None
            logger.info("✅ 새 컨트롤러 초기화 준비 완료")
        except Exception as e:
            logger.info(f"❌ 새 컨트롤러 초기화 실패: {e}")

    def _setup_new_controllers(self):
        """새 컨트롤러들을 설정합니다 (theme_manager 초기화 후 호출)"""
        try:
            from src.gui.components.theme_controller import ThemeController

            self.theme_controller = ThemeController(
                theme_manager=self.theme_manager, settings_manager=self.settings_manager
            )
            from src.gui.components.ui_state_controller import \
                UIStateController

            self.ui_state_controller = UIStateController(
                main_window=self, settings_manager=self.settings_manager
            )
            from src.gui.components.message_log_controller import \
                MessageLogController

            self.message_log_controller = MessageLogController(main_window=self)
            logger.info("✅ 새 컨트롤러 설정 완료")
        except Exception as e:
            logger.info(f"❌ 새 컨트롤러 설정 실패: {e}")

    def _connect_new_controller_signals(self):
        """새 컨트롤러들의 시그널을 연결합니다"""
        try:
            if not hasattr(self, "theme_controller") or not self.theme_controller:
                self._setup_new_controllers()
            if self.theme_controller:
                self.theme_controller.theme_applied.connect(self._on_theme_applied)
                self.theme_controller.theme_detection_failed.connect(
                    self._on_theme_detection_failed
                )
                self.theme_controller.system_theme_changed.connect(self._on_system_theme_changed)
            if self.ui_state_controller:
                self.ui_state_controller.state_saved.connect(self._on_state_saved)
                self.ui_state_controller.state_restored.connect(self._on_state_restored)
                self.ui_state_controller.accessibility_mode_changed.connect(
                    self._on_accessibility_mode_changed
                )
                self.ui_state_controller.high_contrast_mode_changed.connect(
                    self._on_high_contrast_mode_changed
                )
                self.ui_state_controller.language_changed.connect(self._on_language_changed)
            if self.message_log_controller:
                self.message_log_controller.message_shown.connect(self._on_message_shown)
                self.message_log_controller.log_added.connect(self._on_log_added)
                self.message_log_controller.status_updated.connect(self._on_status_updated)
            logger.info("✅ 새 컨트롤러 시그널 연결 완료")
        except Exception as e:
            logger.info(f"❌ 새 컨트롤러 시그널 연결 실패: {e}")

    def _on_theme_applied(self, theme_name: str):
        """테마 적용 완료 시 호출됩니다"""
        try:
            logger.info(f"🎨 테마 적용 완료: {theme_name}")
        except Exception as e:
            logger.info(f"❌ 테마 적용 완료 처리 실패: {e}")

    def _on_theme_detection_failed(self, error: str):
        """테마 감지 실패 시 호출됩니다"""
        try:
            logger.info(f"⚠️ 테마 감지 실패: {error}")
            if self.message_log_controller:
                self.message_log_controller.show_error_message("테마 감지 실패", error)
        except Exception as e:
            logger.info(f"❌ 테마 감지 실패 처리 실패: {e}")

    def _on_system_theme_changed(self, theme_name: str):
        """시스템 테마 변경 시 호출됩니다"""
        try:
            logger.info(f"🔄 시스템 테마 변경: {theme_name}")
        except Exception as e:
            logger.info(f"❌ 시스템 테마 변경 처리 실패: {e}")

    def _on_state_saved(self, state_type: str):
        """상태 저장 완료 시 호출됩니다"""
        try:
            logger.info(f"✅ 상태 저장 완료: {state_type}")
            if self.message_log_controller:
                self.message_log_controller.show_success_message(f"{state_type} 상태 저장 완료")
        except Exception as e:
            logger.info(f"❌ 상태 저장 완료 처리 실패: {e}")

    def _on_state_restored(self, state_type: str):
        """상태 복원 완료 시 호출됩니다"""
        try:
            logger.info(f"✅ 상태 복원 완료: {state_type}")
            if self.message_log_controller:
                self.message_log_controller.show_success_message(f"{state_type} 상태 복원 완료")
        except Exception as e:
            logger.info(f"❌ 상태 복원 완료 처리 실패: {e}")

    def _on_accessibility_mode_changed(self, enabled: bool):
        """접근성 모드 변경 시 호출됩니다"""
        try:
            logger.info(f"🔧 접근성 모드 변경: {'활성화' if enabled else '비활성화'}")
        except Exception as e:
            logger.info(f"❌ 접근성 모드 변경 처리 실패: {e}")

    def _on_high_contrast_mode_changed(self, enabled: bool):
        """고대비 모드 변경 시 호출됩니다"""
        try:
            logger.info(f"🔧 고대비 모드 변경: {'활성화' if enabled else '비활성화'}")
        except Exception as e:
            logger.info(f"❌ 고대비 모드 변경 처리 실패: {e}")

    def _on_language_changed(self, language_code: str):
        """언어 변경 시 호출됩니다"""
        try:
            logger.info(f"🌍 언어가 {language_code}로 변경되었습니다")
        except Exception as e:
            logger.info(f"❌ 언어 변경 처리 실패: {e}")

    def _on_message_shown(self, message_type: str, message: str):
        """메시지 표시 시 호출됩니다"""
        try:
            logger.info(f"📢 메시지 표시: [{message_type}] {message}")
        except Exception as e:
            logger.info(f"❌ 메시지 표시 처리 실패: {e}")

    def _on_log_added(self, log_type: str, log_message: str):
        """로그 추가 시 호출됩니다"""
        try:
            logger.info(f"✅ 로그 추가: [{log_type}] {log_message}")
        except Exception as e:
            logger.info(f"❌ 로그 추가 처리 실패: {e}")

    def start_tmdb_search_direct(self):
        """TMDB 검색을 직접 시작"""
        try:
            if not hasattr(self, "tmdb_search_handler") or not self.tmdb_search_handler:
                logger.info("❌ TMDB 검색 핸들러가 초기화되지 않았습니다")
                return
            logger.info("🔍 TMDB 검색 직접 시작")
            self.tmdb_search_handler.start_tmdb_search_for_groups()
        except Exception as e:
            logger.info(f"❌ TMDB 검색 직접 시작 실패: {e}")

    def _get_group_file_info(self, group_items):
        """그룹의 파일 정보를 가져오는 함수"""
        try:
            file_names = []
            for item in group_items:
                if hasattr(item, "filename") and item.filename:
                    file_names.append(item.filename)
                elif hasattr(item, "sourcePath") and item.sourcePath:
                    from pathlib import Path

                    file_names.append(Path(item.sourcePath).name)
            if file_names:
                if len(file_names) == 1:
                    return file_names[0]
                return f"{file_names[0]} (+{len(file_names) - 1}개 파일)"
            return "파일 정보 없음"
        except Exception as e:
            logger.info(f"❌ 파일 정보 가져오기 실패: {e}")
            return "파일 정보 없음"

    def show_tmdb_dialog_for_group(self, group_id: str):
        """특정 그룹에 대한 TMDB 검색 다이얼로그 표시"""
        try:
            if not hasattr(self, "anime_data_manager") or not self.anime_data_manager:
                logger.info("❌ 애니메이션 데이터 관리자가 초기화되지 않았습니다")
                return
            grouped_items = self.anime_data_manager.get_grouped_items()
            if group_id not in grouped_items:
                logger.info(f"❌ 그룹 {group_id}를 찾을 수 없습니다")
                return
            group_items = grouped_items[group_id]
            if not group_items:
                logger.info(f"❌ 그룹 {group_id}에 아이템이 없습니다")
                return
            group_title = group_items[0].title or group_items[0].detectedTitle or "Unknown"
            file_info = self._get_group_file_info(group_items)
            logger.info(f"🔍 TMDB 다이얼로그 표시: {group_title} (그룹 {group_id})")
            if not self.tmdb_client:
                logger.info("❌ TMDB 클라이언트가 초기화되지 않았습니다")
                return
            logger.info(f"🔍 TMDB API 호출 시작: {group_title}")
            search_results = self.tmdb_client.search_anime(group_title)
            logger.info(f"🔍 TMDB API 호출 완료: {len(search_results)}개 결과")
            if len(search_results) == 1:
                selected_anime = search_results[0]
                logger.info(f"✅ 검색 결과 1개 - 자동 선택: {selected_anime.name}")
                try:
                    self._on_tmdb_anime_selected(group_id, selected_anime)
                    if hasattr(self, "tmdb_search_handler") and self.tmdb_search_handler:
                        self.tmdb_search_handler.process_next_tmdb_group()
                    return
                except Exception as e:
                    logger.info(f"❌ 자동 선택 실패: {e}")
                    logger.info("🔄 자동 선택 실패 - 다이얼로그 표시로 전환")
            elif len(search_results) == 0:
                logger.info("🔍 검색 결과 없음 - 제목 단어별 재검색 시작")
                self._try_progressive_search(group_id, group_title)
                return
            from src.gui.components.dialogs.tmdb_search_dialog import \
                TMDBSearchDialog

            dialog = TMDBSearchDialog(
                group_title, self.tmdb_client, self, file_info, group_title, search_results
            )
            dialog.anime_selected.connect(
                lambda anime: self._on_tmdb_anime_selected(group_id, anime)
            )
            dialog.finished.connect(self._on_tmdb_dialog_finished)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            logger.info(f"✅ TMDB 검색 다이얼로그 표시됨: {group_title}")
        except Exception as e:
            logger.info(f"❌ TMDB 다이얼로그 표시 실패: {e}")

    def _try_progressive_search(self, group_id: str, original_title: str):
        """제목을 단어별로 줄여가며 재검색"""
        try:
            # 제목 정규화 (괄호 안의 연도 정보 제거 등)
            normalized_title = self._normalize_title_for_search(original_title)
            words = normalized_title.split()
            if len(words) <= 1:
                logger.info("❌ 더 이상 줄일 단어가 없습니다")
                self._show_final_dialog(group_id, original_title, [])
                return
            shortened_title = " ".join(words[:-1])
            logger.info(f"🔍 단축 제목으로 재검색: '{shortened_title}'")
            search_results = self.tmdb_client.search_anime(shortened_title)
            logger.info(f"🔍 재검색 완료: {len(search_results)}개 결과")
            if len(search_results) == 1:
                selected_anime = search_results[0]
                logger.info(f"✅ 재검색 결과 1개 - 자동 선택: {selected_anime.name}")
                try:
                    self._on_tmdb_anime_selected(group_id, selected_anime)
                    if hasattr(self, "tmdb_search_handler") and self.tmdb_search_handler:
                        self.tmdb_search_handler.process_next_tmdb_group()
                    return
                except Exception as e:
                    logger.info(f"❌ 재검색 자동 선택 실패: {e}")
                    self._show_final_dialog(group_id, shortened_title, search_results)
                    return
            elif len(search_results) == 0:
                self._try_progressive_search(group_id, shortened_title)
                return
            else:
                logger.info(f"🔍 재검색 결과 {len(search_results)}개 - 다이얼로그 표시")
                self._show_final_dialog(group_id, shortened_title, search_results)
                return
        except Exception as e:
            logger.info(f"❌ 단계적 검색 실패: {e}")
            self._show_final_dialog(group_id, original_title, [])

    def _normalize_title_for_search(self, title: str) -> str:
        """TMDB 검색을 위한 제목 정규화"""
        import re

        if not title:
            return ""

        # 괄호 안의 연도 정보 제거 (예: (2010Q3), (2023), (2024Q1) 등)
        title = re.sub(r"\(\d{4}(?:Q[1-4])?\)\s*", "", title)

        # 추가 정보 제거 (ext, special, ova, oad 등)
        additional_patterns = [
            r"\b(?:ext|special|ova|oad|movie|film)\b",
            r"\b(?:complete|full|uncut|director's cut)\b",
        ]
        for pattern in additional_patterns:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        # 공백 정리
        title = re.sub(r"\s+", " ", title).strip()

        return title

    def _show_final_dialog(self, group_id: str, title: str, search_results: list):
        """최종 다이얼로그 표시"""
        try:
            from src.gui.components.dialogs.tmdb_search_dialog import \
                TMDBSearchDialog

            file_info = ""
            try:
                if hasattr(self, "anime_data_manager") and self.anime_data_manager:
                    grouped_items = self.anime_data_manager.get_grouped_items()
                    if group_id in grouped_items:
                        file_info = self._get_group_file_info(grouped_items[group_id])
            except Exception as e:
                logger.info(f"❌ 파일 정보 가져오기 실패: {e}")
            dialog = TMDBSearchDialog(
                title, self.tmdb_client, self, file_info, title, search_results
            )
            dialog.anime_selected.connect(
                lambda anime: self._on_tmdb_anime_selected(group_id, anime)
            )
            dialog.finished.connect(self._on_tmdb_dialog_finished)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            logger.info(f"✅ 최종 TMDB 검색 다이얼로그 표시됨: {title}")
        except Exception as e:
            logger.info(f"❌ 최종 다이얼로그 표시 실패: {e}")

    def _on_tmdb_anime_selected(self, group_id: str, tmdb_anime):
        """TMDB 애니메이션 선택 처리"""
        try:
            self.anime_data_manager.set_tmdb_match_for_group(group_id, tmdb_anime)
            if hasattr(self, "grouped_model"):
                grouped_items = self.anime_data_manager.get_grouped_items()
                self.grouped_model.set_grouped_items(grouped_items)
            self.update_status_bar(f"✅ {tmdb_anime.name} 매치 완료")
            logger.info(f"✅ TMDB 매치 완료: 그룹 {group_id} → {tmdb_anime.name}")
        except Exception as e:
            logger.info(f"❌ TMDB 애니메이션 선택 처리 실패: {e}")

    def _on_tmdb_dialog_finished(self, result):
        """TMDB 다이얼로그가 닫힐 때 호출"""
        try:
            logger.info(f"🔍 TMDB 다이얼로그 닫힘: {result}")
            if hasattr(self, "tmdb_search_handler") and self.tmdb_search_handler:
                self.tmdb_search_handler.process_next_tmdb_group()
        except Exception as e:
            logger.info(f"❌ TMDB 다이얼로그 완료 처리 실패: {e}")

    def _on_status_updated(self, message: str, progress: int):
        """상태 업데이트 시 호출됩니다"""
        try:
            logger.info(f"🔄 상태 업데이트: {message} ({progress}%)")
        except Exception as e:
            logger.info(f"❌ 상태 업데이트 처리 실패: {e}")

    def show_error_message(
        self, message: str, details: str = "", error_type: str = "error"
    ) -> bool:
        """에러 메시지를 표시합니다 (새 컨트롤러 사용)"""
        if self.message_log_controller:
            return self.message_log_controller.show_error_message(message, details, error_type)
        logger.info(f"❌ {message}")
        if details:
            logger.info(f"   상세: {details}")
        return True

    def show_success_message(
        self, message: str, details: str = "", auto_clear: bool = True
    ) -> bool:
        """성공 메시지를 표시합니다 (새 컨트롤러 사용)"""
        if self.message_log_controller:
            return self.message_log_controller.show_success_message(message, details, auto_clear)
        logger.info(f"✅ {message}")
        if details:
            logger.info(f"   상세: {details}")
        return True

    def show_info_message(self, message: str, details: str = "", auto_clear: bool = True) -> bool:
        """정보 메시지를 표시합니다 (새 컨트롤러 사용)"""
        if self.message_log_controller:
            return self.message_log_controller.show_info_message(message, details, auto_clear)
        logger.info(f"ℹ️ {message}")
        if details:
            logger.info(f"   상세: {details}")
        return True
