"""
리팩토링된 메인 윈도우 - AnimeSorter의 주요 GUI 인터페이스
컴포넌트 기반 아키텍처로 재구성되어 가독성과 유지보수성이 향상되었습니다.
"""

import os
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView  # Added for QHeaderView
from PyQt5.QtWidgets import QMainWindow, QMessageBox

# New Architecture Components
# UI Command Bridge
# Local imports
from core.settings_manager import SettingsManager
from core.tmdb_client import TMDBClient

# Phase 10.1: 접근성 관리 시스템
# Phase 10.2: 국제화 관리 시스템
# Phase 1: 메인 윈도우 분할 - 기능별 클래스 분리
from .components.main_window_coordinator import MainWindowCoordinator
# UI Components
from .components.settings_dialog import SettingsDialog
# Phase 8: UI 상태 관리 및 마이그레이션
# UI Components
# Event Handler Manager
# UI Initializer
# Data Models
from .managers.anime_data_manager import AnimeDataManager
from .managers.file_processing_manager import FileProcessingManager
from .managers.tmdb_manager import TMDBManager

# Table Models


class MainWindow(QMainWindow):
    """AnimeSorter 메인 윈도우 (리팩토링된 버전)"""

    def __init__(self):
        super().__init__()

        # 기본 설정
        self.setWindowTitle("AnimeSorter")
        self.setGeometry(100, 100, 1600, 900)

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

        # 설정 관리자 초기화
        self.settings_manager = SettingsManager()

        # 모든 컴포넌트 초기화 (조율자를 통해)
        self.coordinator.initialize_all_components()

        # 데이터 매니저들 초기화 (핸들러 초기화 전에 먼저 실행)
        self.init_data_managers()

        # MainWindow 핸들러들 초기화
        self._initialize_handlers()

        # 기본 연결 설정
        self.setup_connections()

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

        # TMDB 검색 다이얼로그 초기화
        self.tmdb_search_dialogs = {}

        # 그룹별 TMDB 검색 다이얼로그 저장
        self.tmdb_search_dialogs = {}

        # 파일 관리자 초기화
        self.file_manager = None

        # 포스터 캐시 초기화
        self.poster_cache = {}

        # 접근성 및 국제화 관리자 (조율자에서 관리됨)
        self.accessibility_manager = None
        self.i18n_manager = None

        # MainWindow 핸들러들 초기화
        self.file_handler = None
        self.session_manager = None
        self.menu_action_handler = None
        self.layout_manager = None
        self.tmdb_search_handler = None

    def _initialize_handlers(self):
        """MainWindow 핸들러들을 초기화합니다."""
        try:
            # Python 경로에 src 디렉토리 추가
            import sys
            from pathlib import Path

            src_dir = Path(__file__).parent.parent.parent
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))

            from gui.components.main_window.handlers.file_handler import \
                MainWindowFileHandler
            from gui.components.main_window.handlers.layout_manager import \
                MainWindowLayoutManager
            from gui.components.main_window.handlers.menu_action_handler import \
                MainWindowMenuActionHandler
            from gui.components.main_window.handlers.session_manager import \
                MainWindowSessionManager

            # MainWindowFileHandler 초기화
            if hasattr(self, "file_processing_manager") and hasattr(self, "anime_data_manager"):
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

            # MainWindowSessionManager 초기화
            if hasattr(self, "settings_manager"):
                self.session_manager = MainWindowSessionManager(
                    main_window=self, settings_manager=self.settings_manager
                )
                print("✅ MainWindowSessionManager 초기화 완료")
            else:
                print("⚠️ MainWindowSessionManager 초기화 실패: SettingsManager가 없습니다")

            # MainWindowMenuActionHandler 초기화
            self.menu_action_handler = MainWindowMenuActionHandler(main_window=self)
            print("✅ MainWindowMenuActionHandler 초기화 완료")

            # MainWindowLayoutManager 초기화
            self.layout_manager = MainWindowLayoutManager(main_window=self)
            print("✅ MainWindowLayoutManager 초기화 완료")

            # TMDBSearchHandler 초기화
            try:
                from gui.handlers.tmdb_search_handler import TMDBSearchHandler

                self.tmdb_search_handler = TMDBSearchHandler(main_window=self)
                print("✅ TMDBSearchHandler 초기화 완료")

                # TMDB 검색 시그널 연결
                if hasattr(self, "anime_data_manager") and self.anime_data_manager:
                    self.anime_data_manager.tmdb_search_requested.connect(
                        self.tmdb_search_handler.on_tmdb_search_requested
                    )
                    print("✅ TMDB 검색 시그널-슬롯 연결 완료")
                else:
                    print("⚠️ anime_data_manager가 없어서 TMDB 검색 시그널 연결 실패")

            except Exception as tmdb_error:
                print(f"⚠️ TMDBSearchHandler 초기화 실패: {tmdb_error}")
                self.tmdb_search_handler = None

        except Exception as e:
            print(f"❌ MainWindow 핸들러 초기화 중 오류: {e}")

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

            from gui.view_models.main_window_view_model_new import \
                MainWindowViewModelNew

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
        if hasattr(self, "menu_action_handler") and self.menu_action_handler:
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
            print("⚠️ MainWindowFileHandler가 초기화되지 않았습니다. 핸들러를 다시 초기화합니다.")
            try:
                self._initialize_handlers()
                if self.file_handler:
                    self.file_handler.process_selected_files(file_paths)
                else:
                    print("❌ MainWindowFileHandler 초기화 실패")
            except Exception as e:
                print(f"❌ MainWindowFileHandler 재초기화 실패: {e}")

    def start_scan(self):
        """스캔 시작 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.start_scan()
        else:
            print("⚠️ MainWindowFileHandler가 초기화되지 않았습니다. 핸들러를 다시 초기화합니다.")
            try:
                self._initialize_handlers()
                if self.file_handler:
                    self.file_handler.start_scan()
                else:
                    print("❌ MainWindowFileHandler 초기화 실패")
            except Exception as e:
                print(f"❌ MainWindowFileHandler 재초기화 실패: {e}")

    def scan_directory(self, directory_path: str):
        """디렉토리 스캔 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.scan_directory(directory_path)
        else:
            print("⚠️ MainWindowFileHandler가 초기화되지 않았습니다. 핸들러를 다시 초기화합니다.")
            try:
                self._initialize_handlers()
                if self.file_handler:
                    self.file_handler.scan_directory(directory_path)
                else:
                    print("❌ MainWindowFileHandler 초기화 실패")
            except Exception as e:
                print(f"❌ MainWindowFileHandler 재초기화 실패: {e}")

    def _scan_directory_legacy(self, directory_path: str):
        """기존 방식 디렉토리 스캔 (폴백용) - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler._scan_directory_legacy(directory_path)
        else:
            print("⚠️ MainWindowFileHandler가 초기화되지 않았습니다. 핸들러를 다시 초기화합니다.")
            try:
                self._initialize_handlers()
                if self.file_handler:
                    self.file_handler._scan_directory_legacy(directory_path)
                else:
                    print("❌ MainWindowFileHandler 초기화 실패")
            except Exception as e:
                print(f"❌ MainWindowFileHandler 재초기화 실패: {e}")

    def stop_scan(self):
        """스캔 중지 - MainWindowFileHandler로 위임"""
        if self.file_handler:
            self.file_handler.stop_scan()
        else:
            print("⚠️ MainWindowFileHandler가 초기화되지 않았습니다. 핸들러를 다시 초기화합니다.")
            try:
                self._initialize_handlers()
                if self.file_handler:
                    self.file_handler.stop_scan()
                else:
                    print("❌ MainWindowFileHandler 초기화 실패")
            except Exception as e:
                print(f"❌ MainWindowFileHandler 재초기화 실패: {e}")

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
        """로그 Dock 설정 - MainWindowLayoutManager로 위임"""
        if hasattr(self, "layout_manager") and self.layout_manager:
            self.layout_manager.setup_log_dock()
        else:
            print("⚠️ MainWindowLayoutManager가 초기화되지 않았습니다")

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
                self.settings_manager.save_settings()

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
