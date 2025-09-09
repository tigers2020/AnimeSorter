"""
리팩토링된 메인 윈도우 - AnimeSorter의 주요 GUI 인터페이스
컴포넌트 기반 아키텍처로 재구성되어 가독성과 유지보수성이 향상되었습니다.
"""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHeaderView,  # Added for QHeaderView
    QMainWindow,
    QMessageBox,
)

# New Architecture Components
# UI Command Bridge
# Local imports
from src.core.tmdb_client import TMDBClient
from src.core.unified_config import unified_config_manager
from src.core.unified_event_system import get_unified_event_bus

# Phase 10.1: 접근성 관리 시스템
# Phase 10.2: 국제화 관리 시스템
# Phase 1: 메인 윈도우 분할 - 기능별 클래스 분리
from src.gui.components.main_window_coordinator import MainWindowCoordinator
from src.gui.components.message_log_controller import MessageLogController

# UI Components
from src.gui.components.settings_dialog import SettingsDialog

# New Controllers for Refactoring
from src.gui.components.theme_controller import ThemeController

# Theme Engine Integration
from src.gui.components.theme_manager import ThemeManager
from src.gui.components.ui_state_controller import UIStateController

# Phase 8: UI 상태 관리 및 마이그레이션
# UI Components
# Event Handler Manager
# UI Initializer
# Data Models
from src.gui.managers.anime_data_manager import AnimeDataManager
from src.gui.managers.file_processing_manager import FileProcessingManager
from src.gui.managers.tmdb_manager import TMDBManager
from src.gui.theme.engine.variable_loader import VariableLoader as TokenLoader

# Table Models


class MainWindow(QMainWindow):
    """AnimeSorter 메인 윈도우 (리팩토링된 버전)"""

    def __init__(self):
        super().__init__()

        # 기본 설정
        self.setWindowTitle("AnimeSorter")
        self.setGeometry(100, 100, 1600, 900)

        # 중앙 위젯 및 레이아웃 설정
        from PyQt5.QtWidgets import QVBoxLayout, QWidget

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.parent_layout = QVBoxLayout(self.central_widget)
        self.parent_layout.setContentsMargins(0, 0, 0, 0)
        self.parent_layout.setSpacing(0)

        # Phase 1: 메인 윈도우 분할 - 기능별 클래스 분리
        # 메인 윈도우 조율자 초기화
        self.coordinator = MainWindowCoordinator(self)

        # 기본 상태 초기화
        self.scanning = False
        self.progress = 0
        self.source_files = []
        self.source_directory = ""
        self.destination_directory = ""

        # UI 컴포넌트 속성 초기화
        self.status_progress = None  # 상태바 진행률 표시기

        # 설정 관리자 초기화 (unified_config_manager 사용)
        self.settings_manager = unified_config_manager
        # 통합 이벤트 시스템 초기화
        self.unified_event_bus = get_unified_event_bus()

        # 테마 엔진 초기화
        self.theme_manager = ThemeManager()
        # 테마 디렉토리 경로 설정
        theme_dir = Path(__file__).parent.parent.parent / "data" / "theme"
        self.token_loader = TokenLoader(theme_dir)

        # 모든 컴포넌트 초기화 (조율자를 통해)
        self.coordinator.initialize_all_components()

        # New Controllers Initialization
        self._init_new_controllers()
        self._setup_new_controllers()
        self._connect_new_controller_signals()

        # 초기 테마 적용 (UI 컴포넌트 초기화 전에)
        self._apply_theme()

        # 기본 연결 설정 (초기화 완료 전에 먼저 실행)
        self.setup_connections()

        # 테마 변경 시그널 연결
        self._connect_theme_signals()

        # 통합 이벤트 시스템 연결
        self._connect_unified_event_system()

        # MainWindow 핸들러들 초기화 (Coordinator 초기화 완료 후 실행)
        print("🔧 MainWindow 핸들러들 초기화 시작...")
        try:
            self._initialize_handlers()
            print("✅ MainWindow 핸들러들 초기화 완료")
        except Exception as e:
            print(f"❌ MainWindow 핸들러들 초기화 실패: {e}")
            import traceback

            traceback.print_exc()

        # 설정을 UI에 적용
        print("🔧 설정을 UI에 적용 시작...")
        try:
            self.apply_settings_to_ui()
            print("✅ 설정을 UI에 적용 완료")
        except Exception as e:
            print(f"❌ 설정을 UI에 적용 실패: {e}")
            import traceback

            traceback.print_exc()

        # 데이터 매니저들 초기화 (MainWindowCoordinator에서 이미 초기화되었을 수 있음)
        if not hasattr(self, "anime_data_manager") or not hasattr(self, "file_processing_manager"):
            self.init_data_managers()
        else:
            print("✅ 데이터 매니저들이 이미 MainWindowCoordinator에서 초기화됨")

        self.current_scan_id = None
        self.current_organization_id = None
        self.current_tmdb_search_id = None

    def _schedule_handler_initialization(self):
        """핸들러 초기화를 이벤트 루프 후에 예약합니다"""
        from PyQt5.QtCore import QTimer

        def delayed_handler_init():
            print("🔧 MainWindow 핸들러들 지연 초기화 시작...")
            try:
                self._initialize_handlers()
                print("✅ MainWindow 핸들러들 지연 초기화 완료")
            except Exception as e:
                print(f"❌ MainWindow 핸들러들 지연 초기화 실패: {e}")
                import traceback

                traceback.print_exc()

        # 이벤트 루프 시작 후에 핸들러 초기화 실행
        QTimer.singleShot(100, delayed_handler_init)

        # 테마 모니터링 위젯 초기화
        self.theme_monitor_widget = None

    def publish_event(self, event):
        """통합 이벤트 시스템을 통해 이벤트를 발행합니다"""
        try:
            if self.unified_event_bus:
                return self.unified_event_bus.publish(event)
            print("⚠️ 통합 이벤트 버스가 초기화되지 않았습니다")
            return False
        except Exception as e:
            print(f"❌ 이벤트 발행 실패: {e}")
            return False

    def _apply_theme(self):
        """테마를 적용합니다 (Theme Controller를 통해)"""
        try:
            if hasattr(self, "theme_controller"):
                self.theme_controller.apply_theme(main_window=self)
            else:
                print("⚠️ ThemeController가 초기화되지 않음")
        except Exception as e:
            print(f"❌ 테마 적용 중 오류 발생: {e}")

    def _connect_theme_signals(self):
        """테마 변경 시그널을 연결합니다"""
        try:
            # 테마 변경 시그널 연결
            self.theme_manager.theme_changed.connect(self._on_theme_changed)
            self.theme_manager.icon_theme_changed.connect(self._on_icon_theme_changed)
            print("✅ 테마 변경 시그널 연결 완료")
        except Exception as e:
            print(f"❌ 테마 시그널 연결 실패: {e}")

    def _connect_unified_event_system(self):
        """통합 이벤트 시스템을 연결합니다"""
        try:
            # 이벤트 버스 시그널 연결
            self.unified_event_bus.event_published.connect(self._on_event_published)
            self.unified_event_bus.event_handled.connect(self._on_event_handled)
            self.unified_event_bus.event_failed.connect(self._on_event_failed)

            print("✅ 통합 이벤트 시스템 연결 완료")
        except Exception as e:
            print(f"❌ 통합 이벤트 시스템 연결 실패: {e}")

    def _init_new_controllers(self):
        """새로운 컨트롤러들을 초기화합니다"""
        try:
            # Theme Controller 초기화
            self.theme_controller = ThemeController(self.theme_manager, self.settings_manager)

            # UI State Controller 초기화
            self.ui_state_controller = UIStateController(self.settings_manager)

            # Message Log Controller 초기화
            self.message_log_controller = MessageLogController()

            print("✅ 새로운 컨트롤러들 초기화 완료")
        except Exception as e:
            print(f"❌ 새로운 컨트롤러 초기화 실패: {e}")

    def _setup_new_controllers(self):
        """새로운 컨트롤러들을 설정합니다"""
        try:
            # Theme Controller 설정
            self.theme_controller.setup()

            # UI State Controller 설정
            self.ui_state_controller.setup()

            # Message Log Controller 설정
            self.message_log_controller.setup()

            print("✅ 새로운 컨트롤러들 설정 완료")
        except Exception as e:
            print(f"❌ 새로운 컨트롤러 설정 실패: {e}")

    def _connect_new_controller_signals(self):
        """새로운 컨트롤러들의 시그널을 연결합니다"""
        try:
            # Theme Controller 시그널 연결
            self.theme_controller.theme_applied.connect(self._on_theme_controller_theme_applied)
            self.theme_controller.theme_detection_failed.connect(
                self._on_theme_controller_detection_failed
            )
            self.theme_controller.system_theme_changed.connect(
                self._on_theme_controller_system_theme_changed
            )

            # UI State Controller 시그널 연결
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

            # Message Log Controller 시그널 연결
            self.message_log_controller.message_shown.connect(
                self._on_message_log_controller_message_shown
            )
            self.message_log_controller.log_added.connect(self._on_message_log_controller_log_added)
            self.message_log_controller.status_updated.connect(
                self._on_message_log_controller_status_updated
            )

            print("✅ 새로운 컨트롤러 시그널 연결 완료")
        except Exception as e:
            print(f"❌ 새로운 컨트롤러 시그널 연결 실패: {e}")

    def _on_theme_changed(self, theme: str):
        """테마가 변경되었을 때 호출됩니다"""
        try:
            print(f"🎨 테마 변경: {theme}")
            # 여기에 테마 변경 시 추가적인 UI 업데이트 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ 테마 변경 처리 중 오류: {e}")

    def _on_icon_theme_changed(self, icon_theme: str):
        """아이콘 테마가 변경되었을 때 호출됩니다"""
        try:
            print(f"🖼️ 아이콘 테마 변경: {icon_theme}")
            # 여기에 아이콘 테마 변경 시 추가적인 UI 업데이트 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ 아이콘 테마 변경 처리 중 오류: {e}")

    def _on_event_published(self, event):
        """이벤트가 발행되었을 때 호출됩니다"""
        try:
            print(
                f"📢 이벤트 발행: {event.__class__.__name__} (source: {event.source}, priority: {event.priority})"
            )
            # 여기에 이벤트 발행 시 추가적인 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ 이벤트 발행 처리 중 오류: {e}")

    def _on_event_handled(self, event_type: str, handler_name: str):
        """이벤트가 처리되었을 때 호출됩니다"""
        try:
            print(f"✅ 이벤트 처리: {event_type} -> {handler_name}")
            # 여기에 이벤트 처리 완료 시 추가적인 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ 이벤트 처리 완료 처리 중 오류: {e}")

    def _on_event_failed(self, event_type: str, handler_name: str, error: str):
        """이벤트 처리에 실패했을 때 호출됩니다"""
        try:
            print(f"❌ 이벤트 처리 실패: {event_type} -> {handler_name} - {error}")
            # 여기에 이벤트 처리 실패 시 추가적인 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ 이벤트 처리 실패 처리 중 오류: {e}")

    # New Controller Signal Handlers
    def _on_theme_controller_theme_applied(self, theme: str):
        """Theme Controller의 테마 적용 시그널을 처리합니다"""
        try:
            print(f"🎨 Theme Controller: 테마 적용됨 - {theme}")
            # 여기에 테마 적용 후 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ Theme Controller 테마 적용 처리 중 오류: {e}")

    def _on_theme_controller_detection_failed(self, error: str):
        """Theme Controller의 테마 감지 실패 시그널을 처리합니다"""
        try:
            print(f"⚠️ Theme Controller: 테마 감지 실패 - {error}")
            # 여기에 테마 감지 실패 시 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ Theme Controller 테마 감지 실패 처리 중 오류: {e}")

    def _on_theme_controller_system_theme_changed(self, theme: str):
        """Theme Controller의 시스템 테마 변경 시그널을 처리합니다"""
        try:
            print(f"🔄 Theme Controller: 시스템 테마 변경됨 - {theme}")
            # 여기에 시스템 테마 변경 시 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ Theme Controller 시스템 테마 변경 처리 중 오류: {e}")

    def _on_ui_state_controller_state_saved(self, state_type: str):
        """UI State Controller의 상태 저장 시그널을 처리합니다"""
        try:
            print(f"💾 UI State Controller: 상태 저장됨 - {state_type}")
            # 여기에 상태 저장 후 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ UI State Controller 상태 저장 처리 중 오류: {e}")

    def _on_ui_state_controller_state_restored(self, state_type: str):
        """UI State Controller의 상태 복원 시그널을 처리합니다"""
        try:
            print(f"📂 UI State Controller: 상태 복원됨 - {state_type}")
            # 여기에 상태 복원 후 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ UI State Controller 상태 복원 처리 중 오류: {e}")

    def _on_ui_state_controller_accessibility_changed(self, mode: str):
        """UI State Controller의 접근성 모드 변경 시그널을 처리합니다"""
        try:
            print(f"♿ UI State Controller: 접근성 모드 변경됨 - {mode}")
            # 여기에 접근성 모드 변경 시 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ UI State Controller 접근성 모드 변경 처리 중 오류: {e}")

    def _on_ui_state_controller_high_contrast_changed(self, enabled: bool):
        """UI State Controller의 고대비 모드 변경 시그널을 처리합니다"""
        try:
            print(f"🌓 UI State Controller: 고대비 모드 변경됨 - {enabled}")
            # 여기에 고대비 모드 변경 시 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ UI State Controller 고대비 모드 변경 처리 중 오류: {e}")

    def _on_ui_state_controller_language_changed(self, language: str):
        """UI State Controller의 언어 변경 시그널을 처리합니다"""
        try:
            print(f"🌐 UI State Controller: 언어 변경됨 - {language}")
            # 여기에 언어 변경 시 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ UI State Controller 언어 변경 처리 중 오류: {e}")

    def _on_message_log_controller_message_shown(self, message_type: str, message: str):
        """Message Log Controller의 메시지 표시 시그널을 처리합니다"""
        try:
            print(f"💬 Message Log Controller: 메시지 표시됨 - {message_type}: {message}")
            # 여기에 메시지 표시 후 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ Message Log Controller 메시지 표시 처리 중 오류: {e}")

    def _on_message_log_controller_log_added(self, log_type: str, content: str):
        """Message Log Controller의 로그 추가 시그널을 처리합니다"""
        try:
            print(f"📝 Message Log Controller: 로그 추가됨 - {log_type}: {content}")
            # 여기에 로그 추가 후 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ Message Log Controller 로그 추가 처리 중 오류: {e}")

    def _on_message_log_controller_status_updated(self, status: str):
        """Message Log Controller의 상태 업데이트 시그널을 처리합니다"""
        try:
            print(f"📊 Message Log Controller: 상태 업데이트됨 - {status}")
            # 여기에 상태 업데이트 후 추가 로직을 구현할 수 있습니다
        except Exception as e:
            print(f"❌ Message Log Controller 상태 업데이트 처리 중 오류: {e}")

    def _initialize_handlers(self):
        """MainWindow 핸들러들을 초기화합니다."""
        try:
            # MainWindowFileHandler 초기화 (필수)
            if hasattr(self, "file_processing_manager") and hasattr(self, "anime_data_manager"):
                from src.gui.components.main_window.handlers.file_handler import (
                    MainWindowFileHandler,
                )

                self.file_handler = MainWindowFileHandler(
                    main_window=self,
                    file_processing_manager=self.file_processing_manager,
                    anime_data_manager=self.anime_data_manager,
                    file_parser=getattr(self, "file_parser", None),
                    file_scan_service=getattr(self, "file_scan_service", None),
                )
                print("✅ MainWindowFileHandler 초기화 완료")
            else:
                print("⚠️ MainWindowFileHandler 초기화 실패: 필요한 매니저들이 없습니다")
                self.file_handler = None

            # MainWindowLayoutManager 초기화
            from src.gui.components.main_window.handlers.layout_manager import (
                MainWindowLayoutManager,
            )

            self.layout_manager = MainWindowLayoutManager(main_window=self)
            print("✅ MainWindowLayoutManager 초기화 완료")

            # MainWindowMenuActionHandler 초기화
            from src.gui.components.main_window.handlers.menu_action_handler import (
                MainWindowMenuActionHandler,
            )

            self.menu_action_handler = MainWindowMenuActionHandler(main_window=self)
            print("✅ MainWindowMenuActionHandler 초기화 완료")

            # MainWindowSessionManager 초기화
            if hasattr(self, "settings_manager"):
                from src.gui.components.main_window.handlers.session_manager import (
                    MainWindowSessionManager,
                )

                self.session_manager = MainWindowSessionManager(
                    main_window=self, settings_manager=self.settings_manager
                )
                print("✅ MainWindowSessionManager 초기화 완료")
            else:
                print("⚠️ MainWindowSessionManager 초기화 실패: unified_config_manager가 없습니다")
                self.session_manager = None

            print("✅ MainWindow 핸들러들 초기화 완료")
            return True

        except Exception as e:
            print(f"❌ MainWindow 핸들러 초기화 중 오류: {e}")
            return False

    def init_core_components(self):
        """핵심 컴포넌트 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_core_components()
        print("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_new_architecture(self):
        """새로운 아키텍처 컴포넌트 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_new_architecture()
        print("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_ui_state_management(self):
        """Phase 8: UI 상태 관리 및 마이그레이션 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_ui_state_management()
        print("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_safety_system(self):
        """Safety System 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_safety_system()
        print("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_command_system(self):
        """Command System 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_command_system()
        print("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_journal_system(self):
        """Journal System 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_journal_system()
        print("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

    def init_undo_redo_system(self):
        """Undo/Redo System 초기화 (조율자에 위임)"""
        if hasattr(self, "coordinator") and self.coordinator:
            return self.coordinator.initializer.initialize_undo_redo_system()
        print("⚠️ 조율자가 초기화되지 않았습니다.")
        return False

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

            from src.gui.view_models.main_window_view_model_new import MainWindowViewModelNew

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
        api_key = unified_config_manager.get("services", "tmdb_api", {}).get("api_key", "")
        self.tmdb_manager = TMDBManager(api_key=api_key)

    def apply_settings_to_ui(self):
        """설정을 UI 컴포넌트에 적용 - MainWindowSessionManager로 위임"""
        if self.session_manager:
            self.session_manager.apply_settings_to_ui()
        else:
            print("⚠️ MainWindowSessionManager가 초기화되지 않았습니다")

    def initialize_data(self):
        """초기 데이터 설정"""
        # 빈 리스트로 초기화 (실제 파일 스캔 결과로 대체)
        self.scanning = False
        self.progress = 0

        # 파일 시스템 관련 변수 초기화
        self.source_directory = None
        self.source_files = []
        self.destination_directory = None

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
                    # self.left_panel.scan_started.connect(self.on_scan_started)  # MainWindowCoordinator에서 처리됨
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
        """툴바에서 스캔 요청 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_scan_requested()
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_preview_requested(self):
        """툴바에서 미리보기 요청 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_preview_requested()
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_organize_requested(self):
        """툴바에서 정리 실행 요청 처리 - MainWindowMenuActionHandler로 위임"""
        print("🗂️ 툴바에서 정리 요청됨")
        print("📍 호출 스택:")
        import traceback

        for line in traceback.format_stack()[-3:-1]:  # 마지막 2줄만 표시
            print(f"   {line.strip()}")

        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            print("✅ MainWindowMenuActionHandler 존재함")
            self.menu_action_handler.on_organize_requested()
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_search_text_changed(self, text: str):
        """툴바에서 검색 텍스트 변경 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_search_text_changed(text)
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_settings_requested(self):
        """툴바에서 설정 요청 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_settings_requested()
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    # 패널 시그널 핸들러 메서드들
    def on_scan_started(self):
        """스캔 시작 처리 - MainWindowMenuActionHandler로 위임"""
        # TMDB 검색 상태 초기화 (새로운 스캔에서 다시 검색할 수 있도록)
        if hasattr(self, "tmdb_search_handler") and self.tmdb_search_handler:
            self.tmdb_search_handler.reset_for_new_scan()

        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_scan_started()
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_scan_paused(self):
        """스캔 일시정지 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_scan_paused()
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_settings_opened(self):
        """설정 열기 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_settings_opened()
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_completed_cleared(self):
        """완료된 항목 정리 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_completed_cleared()
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_source_folder_selected(self, folder_path: str):
        """소스 폴더 선택 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_source_folder_selected(folder_path)
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_source_files_selected(self, file_paths: list[str]):
        """소스 파일 선택 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_source_files_selected(file_paths)
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

    def on_destination_folder_selected(self, folder_path: str):
        """대상 폴더 선택 처리 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_destination_folder_selected(folder_path)
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

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
        """테이블 컬럼 너비 복원 - MainWindowSessionManager로 위임"""
        if self.session_manager:
            # 기존 설정에서 컬럼 너비 가져오기
            settings = self.settings_manager.settings
            column_widths = getattr(settings, "table_column_widths", {})
            self.session_manager.restore_table_column_widths(column_widths)
        else:
            print("⚠️ MainWindowSessionManager가 초기화되지 않았습니다")

    def get_table_column_widths(self):
        """테이블 컬럼 너비 가져오기 - MainWindowSessionManager로 위임"""
        if self.session_manager:
            return self.session_manager.get_table_column_widths()
        print("⚠️ MainWindowSessionManager가 초기화되지 않았습니다")
        return {}

    def process_selected_files(self, file_paths: list[str]):
        """선택된 파일들을 처리하고 메타데이터 검색 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.process_selected_files(file_paths)
        else:
            print("⚠️ MainWindowFileHandler가 초기화되지 않았습니다")

    def start_scan(self):
        """스캔 시작 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.start_scan()
        else:
            print("⚠️ MainWindowFileHandler가 초기화되지 않았습니다")

    def scan_directory(self, directory_path: str):
        """디렉토리 스캔 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.scan_directory(directory_path)
        else:
            print("⚠️ MainWindowFileHandler가 초기화되지 않았습니다")

    def _scan_directory_legacy(self, directory_path: str):
        """기존 방식 디렉토리 스캔 (폴백용) - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler._scan_directory_legacy(directory_path)
        else:
            print("⚠️ MainWindowFileHandler가 초기화되지 않았습니다")

    def stop_scan(self):
        """스캔 중지 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.stop_scan()
        else:
            print("⚠️ MainWindowFileHandler가 초기화되지 않았습니다")

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
            if hasattr(self, "tmdb_client"):
                api_key = self.settings_manager.config.services.tmdb_api.api_key
                if api_key and (not self.tmdb_client or self.tmdb_client.api_key != api_key):
                    self.tmdb_client = TMDBClient(api_key=api_key)
                    print("✅ TMDBClient 재초기화 완료")

            # FileManager 설정 업데이트
            if self.settings_manager and self.file_manager:
                dest_root = self.settings_manager.config.application.destination_root
                safe_mode = self.settings_manager.config.application.safe_mode
                naming_scheme = self.settings_manager.config.application.naming_scheme

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
        """이전 세션 상태 복원 - MainWindowSessionManager로 위임"""
        if self.session_manager:
            self.session_manager.restore_session_state()
        else:
            print("⚠️ MainWindowSessionManager가 초기화되지 않았습니다")

    def save_session_state(self):
        """현재 세션 상태 저장 - MainWindowSessionManager로 위임"""
        if self.session_manager:
            self.session_manager.save_session_state()
        else:
            print("⚠️ MainWindowSessionManager가 초기화되지 않았습니다")

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

                # TMDB 검색 시작
                if hasattr(self, "tmdb_search_handler") and self.tmdb_search_handler:
                    print("🚀 TMDB 검색 시작!")
                    self.tmdb_search_handler.start_tmdb_search_for_groups()
                else:
                    print("⚠️ TMDBSearchHandler가 초기화되지 않았습니다")
        except Exception as e:
            print(f"⚠️ 결과 표시 업데이트 실패: {e}")

    # TMDB 검색 관련 메서드들은 TMDBSearchHandler에서 처리됩니다

    # 파일 정리 관련 메서드들은 FileOrganizationHandler에서 처리됩니다

    def on_group_selected(self, group_info: dict):
        """그룹 선택 시 상세 파일 목록 업데이트 - MainWindowMenuActionHandler로 위임"""
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
            self.menu_action_handler.on_group_selected(group_info)
        else:
            print("⚠️ MainWindowMenuActionHandler가 초기화되지 않았습니다")

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
        """크기 변경 시 레이아웃 업데이트 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.update_layout_on_resize()
        else:
            print("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

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
            # UI 상태 저장 (UIStateController에 위임)
            if hasattr(self, "ui_state_controller") and self.ui_state_controller:
                self.ui_state_controller.save_session_state()
                print("✅ 프로그램 종료 시 UI 상태 저장 완료")
            else:
                print("⚠️ UIStateController가 초기화되지 않았습니다")
        except Exception as e:
            print(f"⚠️ 프로그램 종료 시 상태 저장 실패: {e}")

        # 기본 종료 처리
        super().closeEvent(event)

    def setup_log_dock(self):
        """로그 Dock 설정 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.setup_log_dock()
        else:
            print("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

    def toggle_log_dock(self):
        """로그 Dock 가시성 토글 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.toggle_log_dock()
        else:
            print("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

    def show_log_dock(self):
        """로그 Dock 표시 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.show_log_dock()
        else:
            print("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

    def hide_log_dock(self):
        """로그 Dock 숨김 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.hide_log_dock()
        else:
            print("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

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
                self.settings_manager.save_config()

                # 접근성 설정 적용
                if hasattr(self, "accessibility_manager"):
                    high_contrast = getattr(
                        self.settings_manager.config.user_preferences, "high_contrast_mode", False
                    )
                    if high_contrast != self.accessibility_manager.high_contrast_mode:
                        if high_contrast:
                            self.accessibility_manager.toggle_high_contrast_mode()
                        print(f"✅ 고대비 모드: {'활성화' if high_contrast else '비활성화'}")

                    keyboard_nav = getattr(
                        self.settings_manager.config.user_preferences, "keyboard_navigation", True
                    )
                    self.accessibility_manager.set_keyboard_navigation(keyboard_nav)

                    screen_reader = getattr(
                        self.settings_manager.config.user_preferences, "screen_reader_support", True
                    )
                    self.accessibility_manager.set_screen_reader_support(screen_reader)

                # 언어 설정 적용
                if hasattr(self, "i18n_manager"):
                    new_language = getattr(
                        self.settings_manager.config.user_preferences, "language", "ko"
                    )
                    if new_language != self.i18n_manager.get_current_language():
                        self.i18n_manager.set_language(new_language)
                        print(f"✅ 언어가 '{new_language}'로 변경되었습니다.")

                print("✅ 설정이 저장되고 적용되었습니다.")
        except Exception as e:
            print(f"❌ 설정 다이얼로그 표시 실패: {e}")
            QMessageBox.critical(self, "오류", f"설정 다이얼로그를 열 수 없습니다:\n{e}")

    def show_theme_monitor(self):
        """테마 모니터링 위젯 표시"""
        try:
            if not self.theme_monitor_widget:
                from src.gui.theme.theme_monitor_widget import ThemeMonitorWidget

                self.theme_monitor_widget = ThemeMonitorWidget(self.theme_manager, self)

            if self.theme_monitor_widget.isVisible():
                self.theme_monitor_widget.raise_()
                self.theme_monitor_widget.activateWindow()
            else:
                self.theme_monitor_widget.show()

            print("✅ 테마 모니터링 위젯이 표시되었습니다.")

        except Exception as e:
            print(f"❌ 테마 모니터링 위젯 표시 실패: {e}")
            QMessageBox.critical(self, "오류", f"테마 모니터링 위젯을 열 수 없습니다:\n{e}")

    # ===== 새로 추가된 컨트롤러 관리 메서드들 =====

    def _init_new_controllers(self):
        """새로 생성한 컨트롤러들을 초기화합니다"""
        try:
            # 테마 컨트롤러 초기화 (theme_manager가 초기화된 후에 호출됨)
            self.theme_controller = None

            # UI 상태 컨트롤러 초기화
            self.ui_state_controller = None

            # 메시지 로그 컨트롤러 초기화
            self.message_log_controller = None

            print("✅ 새 컨트롤러 초기화 준비 완료")

        except Exception as e:
            print(f"❌ 새 컨트롤러 초기화 실패: {e}")

    def _setup_new_controllers(self):
        """새 컨트롤러들을 설정합니다 (theme_manager 초기화 후 호출)"""
        try:
            # 테마 컨트롤러 설정
            from src.gui.components.theme_controller import ThemeController

            self.theme_controller = ThemeController(
                theme_manager=self.theme_manager, settings_manager=self.settings_manager
            )

            # UI 상태 컨트롤러 설정
            from src.gui.components.ui_state_controller import UIStateController

            self.ui_state_controller = UIStateController(
                main_window=self, settings_manager=self.settings_manager
            )

            # 메시지 로그 컨트롤러 설정
            from src.gui.components.message_log_controller import MessageLogController

            self.message_log_controller = MessageLogController(main_window=self)

            print("✅ 새 컨트롤러 설정 완료")

        except Exception as e:
            print(f"❌ 새 컨트롤러 설정 실패: {e}")

    def _connect_new_controller_signals(self):
        """새 컨트롤러들의 시그널을 연결합니다"""
        try:
            if not hasattr(self, "theme_controller") or not self.theme_controller:
                self._setup_new_controllers()

            # 테마 컨트롤러 시그널 연결
            if self.theme_controller:
                self.theme_controller.theme_applied.connect(self._on_theme_applied)
                self.theme_controller.theme_detection_failed.connect(
                    self._on_theme_detection_failed
                )
                self.theme_controller.system_theme_changed.connect(self._on_system_theme_changed)

            # UI 상태 컨트롤러 시그널 연결
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

            # 메시지 로그 컨트롤러 시그널 연결
            if self.message_log_controller:
                self.message_log_controller.message_shown.connect(self._on_message_shown)
                self.message_log_controller.log_added.connect(self._on_log_added)
                self.message_log_controller.status_updated.connect(self._on_status_updated)

            print("✅ 새 컨트롤러 시그널 연결 완료")

        except Exception as e:
            print(f"❌ 새 컨트롤러 시그널 연결 실패: {e}")

    def _on_theme_applied(self, theme_name: str):
        """테마 적용 완료 시 호출됩니다"""
        try:
            print(f"🎨 테마 적용 완료: {theme_name}")
            # TODO: 테마 적용 후 추가 작업

        except Exception as e:
            print(f"❌ 테마 적용 완료 처리 실패: {e}")

    def _on_theme_detection_failed(self, error: str):
        """테마 감지 실패 시 호출됩니다"""
        try:
            print(f"⚠️ 테마 감지 실패: {error}")
            if self.message_log_controller:
                self.message_log_controller.show_error_message("테마 감지 실패", error)

        except Exception as e:
            print(f"❌ 테마 감지 실패 처리 실패: {e}")

    def _on_system_theme_changed(self, theme_name: str):
        """시스템 테마 변경 시 호출됩니다"""
        try:
            print(f"🔄 시스템 테마 변경: {theme_name}")
            # TODO: 시스템 테마 변경 처리

        except Exception as e:
            print(f"❌ 시스템 테마 변경 처리 실패: {e}")

    def _on_state_saved(self, state_type: str):
        """상태 저장 완료 시 호출됩니다"""
        try:
            print(f"✅ 상태 저장 완료: {state_type}")
            if self.message_log_controller:
                self.message_log_controller.show_success_message(f"{state_type} 상태 저장 완료")

        except Exception as e:
            print(f"❌ 상태 저장 완료 처리 실패: {e}")

    def _on_state_restored(self, state_type: str):
        """상태 복원 완료 시 호출됩니다"""
        try:
            print(f"✅ 상태 복원 완료: {state_type}")
            if self.message_log_controller:
                self.message_log_controller.show_success_message(f"{state_type} 상태 복원 완료")

        except Exception as e:
            print(f"❌ 상태 복원 완료 처리 실패: {e}")

    def _on_accessibility_mode_changed(self, enabled: bool):
        """접근성 모드 변경 시 호출됩니다"""
        try:
            print(f"🔧 접근성 모드 변경: {'활성화' if enabled else '비활성화'}")
            # TODO: 접근성 모드 변경 처리

        except Exception as e:
            print(f"❌ 접근성 모드 변경 처리 실패: {e}")

    def _on_high_contrast_mode_changed(self, enabled: bool):
        """고대비 모드 변경 시 호출됩니다"""
        try:
            print(f"🔧 고대비 모드 변경: {'활성화' if enabled else '비활성화'}")
            # TODO: 고대비 모드 변경 처리

        except Exception as e:
            print(f"❌ 고대비 모드 변경 처리 실패: {e}")

    def _on_language_changed(self, language_code: str):
        """언어 변경 시 호출됩니다"""
        try:
            print(f"🌍 언어가 {language_code}로 변경되었습니다")
            # TODO: 언어 변경 처리

        except Exception as e:
            print(f"❌ 언어 변경 처리 실패: {e}")

    def _on_message_shown(self, message_type: str, message: str):
        """메시지 표시 시 호출됩니다"""
        try:
            print(f"📢 메시지 표시: [{message_type}] {message}")
            # TODO: 메시지 표시 후 처리

        except Exception as e:
            print(f"❌ 메시지 표시 처리 실패: {e}")

    def _on_log_added(self, log_type: str, log_message: str):
        """로그 추가 시 호출됩니다"""
        try:
            print(f"✅ 로그 추가: [{log_type}] {log_message}")
            # TODO: 로그 추가 후 처리

        except Exception as e:
            print(f"❌ 로그 추가 처리 실패: {e}")

    def start_tmdb_search_direct(self):
        """TMDB 검색을 직접 시작"""
        try:
            if not hasattr(self, "tmdb_search_handler") or not self.tmdb_search_handler:
                print("❌ TMDB 검색 핸들러가 초기화되지 않았습니다")
                return

            print("🔍 TMDB 검색 직접 시작")
            self.tmdb_search_handler.start_tmdb_search_for_groups()

        except Exception as e:
            print(f"❌ TMDB 검색 직접 시작 실패: {e}")

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
            print(f"❌ 파일 정보 가져오기 실패: {e}")
            return "파일 정보 없음"

    def show_tmdb_dialog_for_group(self, group_id: str):
        """특정 그룹에 대한 TMDB 검색 다이얼로그 표시"""
        try:
            if not hasattr(self, "anime_data_manager") or not self.anime_data_manager:
                print("❌ 애니메이션 데이터 관리자가 초기화되지 않았습니다")
                return

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
            # 파일 정보 가져오기
            file_info = self._get_group_file_info(group_items)
            print(f"🔍 TMDB 다이얼로그 표시: {group_title} (그룹 {group_id})")

            # 먼저 TMDB 검색을 실행하여 결과 개수 확인
            if not self.tmdb_client:
                print("❌ TMDB 클라이언트가 초기화되지 않았습니다")
                return

            print(f"🔍 TMDB API 호출 시작: {group_title}")
            search_results = self.tmdb_client.search_anime(group_title)
            print(f"🔍 TMDB API 호출 완료: {len(search_results)}개 결과")

            # 자동 선택 로직
            if len(search_results) == 1:
                # 결과가 1개면 자동 선택
                selected_anime = search_results[0]
                print(f"✅ 검색 결과 1개 - 자동 선택: {selected_anime.name}")
                try:
                    self._on_tmdb_anime_selected(group_id, selected_anime)
                    # 자동 선택 후 다음 그룹 처리
                    if hasattr(self, "tmdb_search_handler") and self.tmdb_search_handler:
                        self.tmdb_search_handler.process_next_tmdb_group()
                    return
                except Exception as e:
                    print(f"❌ 자동 선택 실패: {e}")
                    # 자동 선택 실패 시 다이얼로그 표시
                    print("🔄 자동 선택 실패 - 다이얼로그 표시로 전환")
            elif len(search_results) == 0:
                # 결과가 없으면 제목을 단어별로 줄여가며 재검색
                print("🔍 검색 결과 없음 - 제목 단어별 재검색 시작")
                self._try_progressive_search(group_id, group_title)
                return

            # TMDBSearchDialog 직접 생성
            from src.gui.components.tmdb_search_dialog import TMDBSearchDialog

            dialog = TMDBSearchDialog(
                group_title, self.tmdb_client, self, file_info, group_title, search_results
            )
            dialog.anime_selected.connect(
                lambda anime: self._on_tmdb_anime_selected(group_id, anime)
            )

            # 다이얼로그가 닫힐 때 다음 그룹을 처리하도록 연결
            dialog.finished.connect(self._on_tmdb_dialog_finished)

            # 다이얼로그 표시
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()

            print(f"✅ TMDB 검색 다이얼로그 표시됨: {group_title}")

        except Exception as e:
            print(f"❌ TMDB 다이얼로그 표시 실패: {e}")

    def _try_progressive_search(self, group_id: str, original_title: str):
        """제목을 단어별로 줄여가며 재검색"""
        try:
            # 제목을 단어별로 분리
            words = original_title.split()
            if len(words) <= 1:
                print("❌ 더 이상 줄일 단어가 없습니다")
                # 최종적으로 다이얼로그 표시
                self._show_final_dialog(group_id, original_title, [])
                return

            # 마지막 단어 제거
            shortened_title = " ".join(words[:-1])
            print(f"🔍 단축 제목으로 재검색: '{shortened_title}'")

            # 재검색 실행
            search_results = self.tmdb_client.search_anime(shortened_title)
            print(f"🔍 재검색 완료: {len(search_results)}개 결과")

            if len(search_results) == 1:
                # 결과가 1개면 자동 선택
                selected_anime = search_results[0]
                print(f"✅ 재검색 결과 1개 - 자동 선택: {selected_anime.name}")
                try:
                    self._on_tmdb_anime_selected(group_id, selected_anime)
                    # 자동 선택 후 다음 그룹 처리
                    if hasattr(self, "tmdb_search_handler") and self.tmdb_search_handler:
                        self.tmdb_search_handler.process_next_tmdb_group()
                    return
                except Exception as e:
                    print(f"❌ 재검색 자동 선택 실패: {e}")
                    # 자동 선택 실패 시 다이얼로그 표시
                    self._show_final_dialog(group_id, shortened_title, search_results)
                    return
            elif len(search_results) == 0:
                # 여전히 결과가 없으면 더 줄여서 재검색
                self._try_progressive_search(group_id, shortened_title)
                return
            # 여러 결과가 있으면 다이얼로그 표시
            print(f"🔍 재검색 결과 {len(search_results)}개 - 다이얼로그 표시")
            self._show_final_dialog(group_id, shortened_title, search_results)
            return

        except Exception as e:
            print(f"❌ 단계적 검색 실패: {e}")
            # 최종적으로 다이얼로그 표시
            self._show_final_dialog(group_id, original_title, [])

    def _show_final_dialog(self, group_id: str, title: str, search_results: list):
        """최종 다이얼로그 표시"""
        try:
            from src.gui.components.tmdb_search_dialog import TMDBSearchDialog

            # 파일 정보 가져오기
            file_info = ""
            try:
                if hasattr(self, "anime_data_manager") and self.anime_data_manager:
                    grouped_items = self.anime_data_manager.get_grouped_items()
                    if group_id in grouped_items:
                        file_info = self._get_group_file_info(grouped_items[group_id])
            except Exception as e:
                print(f"❌ 파일 정보 가져오기 실패: {e}")

            dialog = TMDBSearchDialog(
                title, self.tmdb_client, self, file_info, title, search_results
            )
            dialog.anime_selected.connect(
                lambda anime: self._on_tmdb_anime_selected(group_id, anime)
            )

            # 다이얼로그가 닫힐 때 다음 그룹을 처리하도록 연결
            dialog.finished.connect(self._on_tmdb_dialog_finished)

            # 다이얼로그 표시
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()

            print(f"✅ 최종 TMDB 검색 다이얼로그 표시됨: {title}")

        except Exception as e:
            print(f"❌ 최종 다이얼로그 표시 실패: {e}")

    def _on_tmdb_anime_selected(self, group_id: str, tmdb_anime):
        """TMDB 애니메이션 선택 처리"""
        try:
            # 데이터 관리자에 TMDB 매치 결과 설정
            self.anime_data_manager.set_tmdb_match_for_group(group_id, tmdb_anime)

            # 그룹 모델 업데이트
            if hasattr(self, "grouped_model"):
                grouped_items = self.anime_data_manager.get_grouped_items()
                self.grouped_model.set_grouped_items(grouped_items)

            # 상태바 업데이트
            self.update_status_bar(f"✅ {tmdb_anime.name} 매치 완료")

            print(f"✅ TMDB 매치 완료: 그룹 {group_id} → {tmdb_anime.name}")

        except Exception as e:
            print(f"❌ TMDB 애니메이션 선택 처리 실패: {e}")

    def _on_tmdb_dialog_finished(self, result):
        """TMDB 다이얼로그가 닫힐 때 호출"""
        try:
            print(f"🔍 TMDB 다이얼로그 닫힘: {result}")

            # 다음 그룹 처리
            if hasattr(self, "tmdb_search_handler") and self.tmdb_search_handler:
                self.tmdb_search_handler.process_next_tmdb_group()

        except Exception as e:
            print(f"❌ TMDB 다이얼로그 완료 처리 실패: {e}")

    def _on_status_updated(self, message: str, progress: int):
        """상태 업데이트 시 호출됩니다"""
        try:
            print(f"🔄 상태 업데이트: {message} ({progress}%)")
            # TODO: 상태 업데이트 후 처리

        except Exception as e:
            print(f"❌ 상태 업데이트 처리 실패: {e}")

    # ===== 새 컨트롤러를 통한 기능 제공 메서드들 =====

    def show_error_message(
        self, message: str, details: str = "", error_type: str = "error"
    ) -> bool:
        """에러 메시지를 표시합니다 (새 컨트롤러 사용)"""
        if self.message_log_controller:
            return self.message_log_controller.show_error_message(message, details, error_type)
        # 기존 방식으로 폴백
        print(f"❌ {message}")
        if details:
            print(f"   상세: {details}")
        return True

    def show_success_message(
        self, message: str, details: str = "", auto_clear: bool = True
    ) -> bool:
        """성공 메시지를 표시합니다 (새 컨트롤러 사용)"""
        if self.message_log_controller:
            return self.message_log_controller.show_success_message(message, details, auto_clear)
        # 기존 방식으로 폴백
        print(f"✅ {message}")
        if details:
            print(f"   상세: {details}")
        return True

    def show_info_message(self, message: str, details: str = "", auto_clear: bool = True) -> bool:
        """정보 메시지를 표시합니다 (새 컨트롤러 사용)"""
        if self.message_log_controller:
            return self.message_log_controller.show_info_message(message, details, auto_clear)
        # 기존 방식으로 폴백
        print(f"ℹ️ {message}")
        if details:
            print(f"   상세: {details}")
        return True
