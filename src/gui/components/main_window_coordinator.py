"""
메인 윈도우 조율자 클래스
MainWindow의 모든 관리자들을 조율하여 전체적인 초기화와 관리를 담당합니다.
"""

import logging
from typing import Any

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)
from src.gui.components.main_window_initializer import MainWindowInitializer

# 삭제된 Manager들은 새로운 서비스 아키텍처로 대체됨
# from src.gui.components.managers.event_handler_manager_ui import EventHandlerManagerUI
# from src.gui.components.ui_component_manager import UIComponentManager


# 임시 구현체들
class UIComponentManager:
    """UI 컴포넌트 관리자 (임시 구현)"""

    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("UI 컴포넌트 관리자 초기화 (임시 구현)")

    def setup_all_components(self):
        """모든 UI 컴포넌트 설정 (임시 구현)"""
        self.logger.info("UI 컴포넌트 설정 완료 (임시 구현)")

    def initialize_components(self):
        """UI 컴포넌트 초기화 (임시 구현)"""
        self.logger.info("UI 컴포넌트 초기화 완료 (임시 구현)")

    def cleanup_components(self):
        """UI 컴포넌트 정리 (임시 구현)"""
        self.logger.info("UI 컴포넌트 정리 완료 (임시 구현)")


class EventHandlerManagerUI:
    """이벤트 핸들러 관리자 UI (임시 구현)"""

    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("이벤트 핸들러 관리자 UI 초기화 (임시 구현)")

    def setup_event_handlers(self):
        """이벤트 핸들러 설정 (임시 구현)"""
        self.logger.info("이벤트 핸들러 설정 완료 (임시 구현)")

    def cleanup_event_handlers(self):
        """이벤트 핸들러 정리 (임시 구현)"""
        self.logger.info("이벤트 핸들러 정리 완료 (임시 구현)")


class MainWindowCoordinator:
    """메인 윈도우의 모든 관리자들을 조율하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.initializer: MainWindowInitializer | None = None
        # 삭제된 Manager들은 새로운 서비스 아키텍처로 대체됨
        self.ui_component_manager: Any | None = None
        self.event_handler_manager: Any | None = None
        self.initialization_complete = False
        self.initialization_steps = []
        self.lazy_init_timer = QTimer()
        self.lazy_init_timer.setSingleShot(True)
        self.lazy_init_timer.timeout.connect(self._perform_lazy_initialization)

    def initialize_all_components(self):
        """모든 컴포넌트를 초기화"""
        try:
            logger.info("🚀 MainWindowCoordinator: 전체 컴포넌트 초기화 시작...")
            self._initialize_initializer()
            self._initialize_ui_component_manager()
            self._initialize_event_handler_manager()
            self._initialize_tmdb_search_handler()
            self._initialize_menu_toolbar_manager()
            self._setup_lazy_initialization()
            self.initialization_complete = True
            self._log_initialization_summary()
            logger.info("✅ MainWindowCoordinator: 전체 컴포넌트 초기화 완료!")
        except Exception as e:
            logger.error("❌ MainWindowCoordinator: 전체 컴포넌트 초기화 실패: %s", e)
            import traceback

            traceback.print_exc()

    def _initialize_initializer(self):
        """초기화 관리자 생성 및 실행"""
        try:
            logger.info("🔧 MainWindowCoordinator: 초기화 관리자 생성 중...")
            logger.info("🔧 MainWindowInitializer 생성 중...")
            self.initializer = MainWindowInitializer(self.main_window)
            logger.info("✅ MainWindowInitializer 생성 완료")
            logger.info("🔧 _init_core_components() 호출...")
            self.initializer._init_core_components()
            logger.info("✅ _init_core_components() 완료")
            logger.info("🔧 _init_data_managers() 호출...")
            self.initializer._init_data_managers()
            logger.info("✅ _init_data_managers() 완료")
            logger.info("🔧 _init_new_architecture() 호출...")
            self.initializer._init_new_architecture()
            logger.info("✅ _init_new_architecture() 완료")
            logger.info("🔧 _init_safety_system() 호출...")
            self.initializer._init_safety_system()
            logger.info("✅ _init_safety_system() 완료")
            logger.info("🔧 _init_ui_state_management() 호출...")
            self.initializer._init_ui_state_management()
            logger.info("✅ _init_ui_state_management() 완료")
            logger.info("🔧 _init_accessibility_and_i18n() 호출...")
            self.initializer._init_accessibility_and_i18n()
            logger.info("✅ _init_accessibility_and_i18n() 완료")
            self.initialization_steps.append("✅ 초기화 관리자 완료")
            logger.info("✅ MainWindowCoordinator: 초기화 관리자 생성 완료")
        except Exception as e:
            logger.error("❌ MainWindowCoordinator: 초기화 관리자 생성 실패: %s", e)
            raise

    def _initialize_ui_component_manager(self):
        """UI 컴포넌트 관리자 생성 및 실행"""
        try:
            logger.info("🔧 MainWindowCoordinator: UI 컴포넌트 관리자 생성 중...")
            self.ui_component_manager = UIComponentManager(self.main_window)
            self.ui_component_manager.setup_all_components()
            self._create_main_ui_components()
            self.initialization_steps.append("✅ UI 컴포넌트 관리자 완료")
            logger.info("✅ MainWindowCoordinator: UI 컴포넌트 관리자 생성 완료")
        except Exception as e:
            logger.error("❌ MainWindowCoordinator: UI 컴포넌트 관리자 생성 실패: %s", e)
            raise

    def _create_main_ui_components(self):
        """메인 UI 컴포넌트들 생성"""
        try:
            logger.info("🔧 MainWindowCoordinator: 메인 UI 컴포넌트 생성 중...")

            # 메뉴바 생성
            self._create_menu_bar()

            # 메인 툴바 생성 (임시로 건너뛰기)
            try:
                from src.gui.components.main_toolbar import MainToolbar

                self.main_window.main_toolbar = MainToolbar(self.main_window)
                self.main_window.addToolBar(self.main_window.main_toolbar)
                logger.info("✅ 메인 툴바 생성 완료")
            except Exception as e:
                logger.warning(f"⚠️ 메인 툴바 생성 실패: {e}")
                # 툴바 없이 계속 진행

            # 왼쪽 패널 생성
            from src.gui.components.panels.left_panel_dock import LeftPanelDock

            self.main_window.left_panel = LeftPanelDock(self.main_window)
            self.main_window.addDockWidget(Qt.LeftDockWidgetArea, self.main_window.left_panel)

            # 중앙 레이아웃 생성
            from src.gui.components.central_triple_layout import \
                CentralTripleLayout

            self.main_window.central_layout = CentralTripleLayout(self.main_window)

            # 중앙 위젯을 CentralTripleLayout으로 직접 설정
            self.main_window.setCentralWidget(self.main_window.central_layout)

            # 로그 도크 생성
            from src.gui.components.log_dock import LogDock

            self.main_window.log_dock = LogDock(self.main_window)
            self.main_window.addDockWidget(Qt.BottomDockWidgetArea, self.main_window.log_dock)

            # 결과 뷰 생성
            from src.gui.components.results_view import ResultsView

            self.main_window.results_view = ResultsView(self.main_window)

            logger.info("✅ MainWindowCoordinator: 메인 UI 컴포넌트 생성 완료")

        except Exception as e:
            logger.error("❌ MainWindowCoordinator: 메인 UI 컴포넌트 생성 실패: %s", e)
            import traceback

            traceback.print_exc()

    def _create_menu_bar(self):
        """메뉴바 생성"""
        try:
            menubar = self.main_window.menuBar()

            # 파일 메뉴
            file_menu = menubar.addMenu("파일")
            file_menu.addAction("폴더 열기", self._on_open_folder)
            file_menu.addAction("파일 열기", self._on_open_files)
            file_menu.addSeparator()
            file_menu.addAction("종료", self.main_window.close)

            # 편집 메뉴
            edit_menu = menubar.addMenu("편집")
            edit_menu.addAction("설정", self._on_open_settings)

            # 보기 메뉴
            view_menu = menubar.addMenu("보기")
            view_menu.addAction("왼쪽 패널", self._toggle_left_panel)
            view_menu.addAction("로그 패널", self._toggle_log_panel)

            # 도움말 메뉴
            help_menu = menubar.addMenu("도움말")
            help_menu.addAction("정보", self._on_show_about)

            logger.info("✅ 메뉴바 생성 완료")

        except Exception as e:
            logger.error(f"❌ 메뉴바 생성 실패: {e}")

    def _on_open_folder(self):
        """폴더 열기"""
        from PyQt5.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self.main_window, "폴더 선택")
        if folder:
            logger.info(f"선택된 폴더: {folder}")
            self.main_window.statusBar().showMessage(f"폴더가 선택되었습니다: {folder}")

    def _on_open_files(self):
        """파일 열기"""
        from PyQt5.QtWidgets import QFileDialog

        files, _ = QFileDialog.getOpenFileNames(
            self.main_window,
            "애니메이션 파일 선택",
            "",
            "비디오 파일 (*.mp4 *.mkv *.avi *.mov);;모든 파일 (*)",
        )
        if files:
            logger.info(f"선택된 파일들: {files}")
            self.main_window.statusBar().showMessage(f"{len(files)}개 파일이 선택되었습니다.")

    def _on_open_settings(self):
        """설정 열기"""
        try:
            from src.gui.components.dialogs.settings_dialog import \
                SettingsDialog

            dialog = SettingsDialog(self.main_window)
            dialog.exec_()
        except Exception as e:
            logger.error(f"설정 다이얼로그 열기 실패: {e}")
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.information(self.main_window, "설정", "설정 기능을 준비 중입니다.")

    def _on_show_about(self):
        """정보 표시"""
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.about(
            self.main_window,
            "AnimeSorter 정보",
            "AnimeSorter v1.0\n\n"
            "애니메이션 파일을 정리하고 관리하는 도구입니다.\n\n"
            "Manager 클래스 통합 리팩토링 완료!",
        )

    def _toggle_left_panel(self):
        """왼쪽 패널 토글"""
        if hasattr(self.main_window, "left_panel"):
            self.main_window.left_panel.setVisible(not self.main_window.left_panel.isVisible())

    def _toggle_log_panel(self):
        """로그 패널 토글"""
        if hasattr(self.main_window, "log_dock"):
            self.main_window.log_dock.setVisible(not self.main_window.log_dock.isVisible())

    def _initialize_event_handler_manager(self):
        """이벤트 핸들러 관리자 생성 및 실행"""
        try:
            logger.info("🔧 MainWindowCoordinator: 이벤트 핸들러 관리자 생성 중...")
            self.event_handler_manager = EventHandlerManagerUI(self.main_window)
            self._connect_event_handlers()
            self.initialization_steps.append("✅ 이벤트 핸들러 관리자 완료")
            logger.info("✅ MainWindowCoordinator: 이벤트 핸들러 관리자 생성 완료")
        except Exception as e:
            logger.error("❌ MainWindowCoordinator: 이벤트 핸들러 관리자 생성 실패: %s", e)

    def _initialize_tmdb_search_handler(self):
        """TMDB 검색 핸들러 초기화"""
        try:
            logger.info("🔧 MainWindowCoordinator: TMDB 검색 핸들러 초기화 중...")
            if not hasattr(self.main_window, "tmdb_client") or not self.main_window.tmdb_client:
                logger.info(
                    "⚠️ TMDB 클라이언트가 초기화되지 않았습니다. TMDB 검색 핸들러를 건너뜁니다."
                )
                return
            from src.gui.handlers.tmdb_search_handler import TMDBSearchHandler

            self.main_window.tmdb_search_handler = TMDBSearchHandler(self.main_window)
            if (
                hasattr(self.main_window, "anime_data_manager")
                and self.main_window.anime_data_manager
            ):
                self.main_window.anime_data_manager.tmdb_search_requested.connect(
                    self.main_window.tmdb_search_handler.on_tmdb_search_requested
                )
                logger.info("✅ TMDB 검색 시그널-슬롯 연결 완료")
            else:
                logger.info("⚠️ AnimeDataManager가 없어 TMDB 검색 시그널 연결을 건너뜁니다.")
            self.initialization_steps.append("✅ TMDB 검색 핸들러 초기화 완료")
            logger.info("✅ MainWindowCoordinator: TMDB 검색 핸들러 초기화 완료")
        except Exception as e:
            logger.error("❌ MainWindowCoordinator: TMDB 검색 핸들러 초기화 실패: %s", e)
            raise

    def _initialize_menu_toolbar_manager(self):
        """메뉴 및 툴바 관리자 생성 및 실행"""
        try:
            logger.info("🔧 MainWindowCoordinator: 메뉴 및 툴바 관리자 생성 중...")
            self.initialization_steps.append("✅ 메뉴 및 툴바 관리자 완료")
            logger.info("✅ MainWindowCoordinator: 메뉴 및 툴바 관리자 생성 완료")
        except Exception as e:
            logger.error("❌ MainWindowCoordinator: 메뉴 및 툴바 관리자 생성 실패: %s", e)
            raise

    def _connect_event_handlers(self):
        """이벤트 핸들러들을 메인 윈도우에 연결"""
        try:
            if hasattr(self.main_window, "main_toolbar"):
                toolbar = self.main_window.main_toolbar
                if hasattr(toolbar, "scan_action"):
                    toolbar.scan_action.triggered.connect(
                        self.event_handler_manager.on_scan_requested
                    )
                if hasattr(toolbar, "preview_action"):
                    toolbar.preview_action.triggered.connect(
                        self.event_handler_manager.on_preview_requested
                    )
                if hasattr(toolbar, "settings_action"):
                    toolbar.settings_action.triggered.connect(
                        self.event_handler_manager.on_settings_requested
                    )
            if hasattr(self.main_window, "left_panel"):
                left_panel = self.main_window.left_panel
                if hasattr(left_panel, "scan_started"):
                    left_panel.scan_started.connect(self.event_handler_manager.on_scan_started)
                if hasattr(left_panel, "scan_paused"):
                    left_panel.scan_paused.connect(self.event_handler_manager.on_scan_paused)
                if hasattr(left_panel, "settings_opened"):
                    left_panel.settings_opened.connect(
                        self.event_handler_manager.on_settings_opened
                    )
                if hasattr(left_panel, "completed_cleared"):
                    left_panel.completed_cleared.connect(
                        self.event_handler_manager.on_completed_cleared
                    )
                if hasattr(left_panel, "source_folder_selected"):
                    left_panel.source_folder_selected.connect(
                        self.event_handler_manager.on_source_folder_selected
                    )
                if hasattr(left_panel, "source_files_selected"):
                    left_panel.source_files_selected.connect(
                        self.event_handler_manager.on_source_files_selected
                    )
                if hasattr(left_panel, "destination_folder_selected"):
                    left_panel.destination_folder_selected.connect(
                        self.event_handler_manager.on_destination_folder_selected
                    )
            logger.info("✅ MainWindowCoordinator: 이벤트 핸들러 연결 완료")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: 이벤트 핸들러 연결 실패: %s", e)

    def _setup_lazy_initialization(self):
        """지연 초기화 설정"""
        try:
            self.lazy_init_timer.start(100)
            logger.info("✅ MainWindowCoordinator: 지연 초기화 설정 완료")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: 지연 초기화 설정 실패: %s", e)

    def _perform_lazy_initialization(self):
        """지연 초기화 실행"""
        try:
            logger.info("🔧 MainWindowCoordinator: 지연 초기화 실행 중...")
            self._update_ui_states()
            self._update_menu_states()
            self._apply_initial_settings()
            self._emit_initialization_complete()
            logger.info("✅ MainWindowCoordinator: 지연 초기화 완료")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: 지연 초기화 실패: %s", e)

    def _update_ui_states(self):
        """UI 상태 업데이트"""
        try:
            logger.info("✅ MainWindowCoordinator: UI 상태 업데이트 완료")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: UI 상태 업데이트 실패: %s", e)

    def _update_menu_states(self):
        """메뉴 상태 업데이트"""
        try:
            logger.info("✅ MainWindowCoordinator: 메뉴 상태 업데이트 완료")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: 메뉴 상태 업데이트 실패: %s", e)

    def _apply_initial_settings(self):
        """초기 설정 적용"""
        try:
            settings = type(
                "Settings",
                (),
                {
                    "window_geometry": None,
                    "theme": "light",
                    "language": "ko",
                    "window_state": None,
                    "dock_widget_states": {},
                },
            )()
            if hasattr(self.main_window, "settings_manager") and hasattr(
                self.main_window.settings_manager, "config"
            ):
                user_prefs = self.main_window.settings_manager.config.user_preferences
                theme_prefs = getattr(user_prefs, "theme_preferences", {})
                if isinstance(theme_prefs, dict):
                    settings = type(
                        "Settings",
                        (),
                        {
                            "window_geometry": user_prefs.gui_state.get("window_geometry", None),
                            "theme": theme_prefs.get("theme", "light"),
                            "language": theme_prefs.get("language", "ko"),
                            "window_state": user_prefs.gui_state.get("window_state", None),
                            "dock_widget_states": user_prefs.gui_state.get(
                                "dock_widget_states", {}
                            ),
                        },
                    )()
                else:
                    settings = type(
                        "Settings",
                        (),
                        {
                            "window_geometry": user_prefs.gui_state.get("window_geometry", None),
                            "theme": getattr(theme_prefs, "theme", "light"),
                            "language": getattr(theme_prefs, "language", "ko"),
                            "window_state": user_prefs.gui_state.get("window_state", None),
                            "dock_widget_states": user_prefs.gui_state.get(
                                "dock_widget_states", {}
                            ),
                        },
                    )()
            if hasattr(settings, "window_geometry") and settings.window_geometry:
                try:
                    from PyQt5.QtCore import QByteArray

                    if isinstance(settings.window_geometry, str):
                        geometry_bytes = settings.window_geometry.encode("utf-8")
                        geometry_bytearray = QByteArray(geometry_bytes)
                        self.main_window.restoreGeometry(geometry_bytearray)
                    else:
                        self.main_window.restoreGeometry(settings.window_geometry)
                except Exception as e:
                    logger.warning("⚠️ 윈도우 geometry 복원 실패: %s", e)
            if hasattr(settings, "window_state") and settings.window_state:
                try:
                    from PyQt5.QtCore import QByteArray

                    if isinstance(settings.window_state, str):
                        state_bytes = settings.window_state.encode("utf-8")
                        state_bytearray = QByteArray(state_bytes)
                        self.main_window.restoreState(state_bytearray)
                    else:
                        self.main_window.restoreState(settings.window_state)
                except Exception as e:
                    logger.warning("⚠️ 윈도우 state 복원 실패: %s", e)
            if hasattr(settings, "dock_widget_states"):
                self._restore_dock_widget_states(settings.dock_widget_states)
            logger.info("✅ MainWindowCoordinator: 초기 설정 적용 완료")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: 초기 설정 적용 실패: %s", e)

    def _restore_dock_widget_states(self, dock_states: dict[str, Any]):
        """Dock 위젯 상태 복원"""
        try:
            for dock_name, state in dock_states.items():
                if hasattr(self.main_window, dock_name):
                    dock = getattr(self.main_window, dock_name)
                    if hasattr(dock, "restoreState"):
                        dock.restoreState(state)
            logger.info("✅ MainWindowCoordinator: Dock 위젯 상태 복원 완료")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: Dock 위젯 상태 복원 실패: %s", e)

    def _emit_initialization_complete(self):
        """초기화 완료 이벤트 발생"""
        try:
            if hasattr(self.main_window, "initialization_complete"):
                self.main_window.initialization_complete.emit()
            logger.info("✅ MainWindowCoordinator: 초기화 완료 이벤트 발생")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: 초기화 완료 이벤트 발생 실패: %s", e)

    def _log_initialization_summary(self):
        """초기화 요약 로그 출력"""
        try:
            logger.info("\n" + "=" * 60)
            logger.info("🎯 MainWindowCoordinator 초기화 요약")
            logger.info("=" * 60)
            for step in self.initialization_steps:
                logger.info("  %s", step)
            logger.info("\n📊 총 초기화 단계: %d개", len(self.initialization_steps))
            logger.info("🔧 초기화 완료: %s", self.initialization_complete)
            logger.info("=" * 60 + "\n")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: 초기화 요약 로그 출력 실패: %s", e)

    def get_initialization_status(self) -> dict[str, Any]:
        """초기화 상태 반환"""
        return {
            "complete": self.initialization_complete,
            "steps": self.initialization_steps.copy(),
            "total_steps": len(self.initialization_steps),
        }

    def is_fully_initialized(self) -> bool:
        """완전히 초기화되었는지 확인"""
        return self.initialization_complete and len(self.initialization_steps) >= 4

    def get_component_status(self) -> dict[str, bool]:
        """각 컴포넌트의 상태 반환"""
        return {
            "initializer": self.initializer is not None,
            "ui_component_manager": self.ui_component_manager is not None,
            "event_handler_manager": self.event_handler_manager is not None,
            "menu_toolbar_manager": self.menu_toolbar_manager is not None,
        }

    def refresh_ui_states(self):
        """UI 상태 새로고침"""
        try:
            logger.info("🔧 MainWindowCoordinator: UI 상태 새로고침 중...")
            self._update_ui_states()
            self._update_menu_states()
            logger.info("✅ MainWindowCoordinator: UI 상태 새로고침 완료")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: UI 상태 새로고침 실패: %s", e)

    def cleanup(self):
        """정리 작업 수행"""
        try:
            logger.info("🧹 MainWindowCoordinator: 정리 작업 시작...")
            if self.lazy_init_timer.isActive():
                self.lazy_init_timer.stop()
            if self.initializer and hasattr(self.initializer, "cleanup"):
                self.initializer.cleanup()
            if self.ui_component_manager and hasattr(self.ui_component_manager, "cleanup"):
                self.ui_component_manager.cleanup()
            if self.event_handler_manager and hasattr(self.event_handler_manager, "cleanup"):
                self.event_handler_manager.cleanup()
            if self.menu_toolbar_manager and hasattr(self.menu_toolbar_manager, "cleanup"):
                self.menu_toolbar_manager.cleanup()
            logger.info("✅ MainWindowCoordinator: 정리 작업 완료")
        except Exception as e:
            logger.warning("⚠️ MainWindowCoordinator: 정리 작업 실패: %s", e)

    def diagnose_initialization_issues(self) -> list[str]:
        """초기화 문제 진단"""
        issues = []
        try:
            component_status = self.get_component_status()
            for component_name, is_initialized in component_status.items():
                if not is_initialized:
                    issues.append(f"❌ {component_name}가 초기화되지 않음")
            if len(self.initialization_steps) < 4:
                issues.append(
                    f"⚠️ 초기화 단계가 부족함 (현재: {len(self.initialization_steps)}개, 필요: 4개)"
                )
            if not self.initialization_complete:
                issues.append("❌ 전체 초기화가 완료되지 않음")
            return issues
        except Exception as e:
            issues.append(f"❌ 진단 중 오류 발생: {e}")
            return issues

    def get_detailed_status_report(self) -> str:
        """상세 상태 보고서 생성"""
        try:
            report = []
            report.append("=" * 60)
            report.append("📊 MainWindowCoordinator 상세 상태 보고서")
            report.append("=" * 60)
            report.append(f"🔧 초기화 완료: {self.initialization_complete}")
            report.append(f"📋 초기화 단계: {len(self.initialization_steps)}개")
            component_status = self.get_component_status()
            report.append("\n📦 컴포넌트 상태:")
            for component_name, is_initialized in component_status.items():
                status_icon = "✅" if is_initialized else "❌"
                report.append(
                    f"  {status_icon} {component_name}: {'초기화됨' if is_initialized else '초기화 안됨'}"
                )
            report.append("\n🔍 초기화 단계 상세:")
            for i, step in enumerate(self.initialization_steps, 1):
                report.append(f"  {i}. {step}")
            issues = self.diagnose_initialization_issues()
            if issues:
                report.append("\n⚠️ 발견된 문제들:")
                for issue in issues:
                    report.append(f"  {issue}")
            else:
                report.append("\n✅ 문제 없음")
            report.append("=" * 60)
            return "\n".join(report)
        except Exception as e:
            return f"상세 상태 보고서 생성 실패: {e}"
