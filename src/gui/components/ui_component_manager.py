"""
UI 컴포넌트 관리 로직을 담당하는 클래스
MainWindow의 UI 컴포넌트 생성, 설정, 연결 로직을 분리하여 가독성과 유지보수성을 향상시킵니다.
"""

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QHeaderView, QMainWindow

from src.gui.components.log_dock import LogDock
from src.gui.handlers.event_handler_manager import EventHandlerManager
from src.gui.initializers.ui_initializer import UIInitializer
from src.gui.managers.status_bar_manager import StatusBarManager

if TYPE_CHECKING:
    from src.gui.components.accessibility_manager import AccessibilityManager
    from src.gui.components.i18n_manager import I18nManager
    from src.gui.components.ui_migration_manager import UIMigrationManager
    from src.gui.components.ui_state_manager import UIStateManager
    from src.gui.managers.anime_data_manager import AnimeDataManager
    from src.gui.managers.file_processing_manager import FileProcessingManager
    from src.gui.managers.tmdb_manager import TMDBManager


class UIComponentManager:
    """UI 컴포넌트 관리를 담당하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.log_dock: LogDock | None = None
        self.ui_initializer: UIInitializer | None = None
        self.event_handler_manager: EventHandlerManager | None = None
        self.status_bar_manager: StatusBarManager | None = None
        self.accessibility_manager: AccessibilityManager | None = None
        self.i18n_manager: I18nManager | None = None
        self.ui_state_manager: UIStateManager | None = None
        self.ui_migration_manager: UIMigrationManager | None = None

        # 데이터 관리자들
        self.anime_data_manager: AnimeDataManager | None = None
        self.file_processing_manager: FileProcessingManager | None = None
        self.tmdb_manager: TMDBManager | None = None

        # TMDB 검색 다이얼로그 저장
        self.tmdb_search_dialogs = {}

        # 포스터 캐시
        self.poster_cache = {}

    def setup_all_components(self):
        """모든 UI 컴포넌트를 설정하고 연결"""
        try:
            print("🔧 UI 컴포넌트 설정 시작...")

            # 1. 로그 Dock 설정
            self._setup_log_dock()

            # 2. UI 초기화
            self._setup_ui_initializer()

            # 3. 이벤트 핸들러 관리자 설정
            self._setup_event_handler_manager()

            # 4. 상태바 관리자 설정
            self._setup_status_bar_manager()

            # 5. 접근성 및 국제화 관리자 설정
            self._setup_accessibility_and_i18n()

            # 6. UI 상태 관리 및 마이그레이션 설정
            self._setup_ui_state_management()

            # 7. 시그널/슬롯 연결 설정
            self._setup_connections()

            print("✅ UI 컴포넌트 설정 완료!")

        except Exception as e:
            print(f"❌ UI 컴포넌트 설정 실패: {e}")
            import traceback

            traceback.print_exc()

    def _setup_log_dock(self):
        """로그 Dock 설정"""
        try:
            # LogDock 생성
            self.log_dock = LogDock(self.main_window)
            self.main_window.log_dock = self.log_dock

            # 하단 영역에 추가
            from PyQt5.QtCore import Qt

            self.main_window.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)

            # 기본 상태: 숨김 (접힘)
            self.log_dock.setVisible(False)

            # Dock 상태 로드
            self.log_dock.load_dock_state()

            print("✅ 로그 Dock 설정 완료")

        except Exception as e:
            print(f"❌ 로그 Dock 설정 실패: {e}")
            self.log_dock = None

    def _setup_ui_initializer(self):
        """UI 초기화 설정"""
        try:
            self.ui_initializer = UIInitializer(self.main_window)
            self.main_window.ui_initializer = self.ui_initializer

            # UI 초기화 실행 (MainWindowInitializer와 중복될 수 있지만 안전하게 실행)
            self.ui_initializer.init_ui()

            print("✅ UI 초기화 설정 및 실행 완료")

        except Exception as e:
            print(f"❌ UI 초기화 설정 실패: {e}")
            self.ui_initializer = None

    def _setup_event_handler_manager(self):
        """이벤트 핸들러 관리자 설정"""
        try:
            if hasattr(self.main_window, "event_bus") and self.main_window.event_bus:
                self.event_handler_manager = EventHandlerManager(
                    self.main_window, self.main_window.event_bus
                )
                self.main_window.event_handler_manager = self.event_handler_manager

                # 이벤트 구독 설정
                self.event_handler_manager.setup_event_subscriptions()

                print("✅ 이벤트 핸들러 관리자 설정 완료")
            else:
                print("⚠️ EventBus가 초기화되지 않아 이벤트 핸들러 관리자를 설정할 수 없습니다.")

        except Exception as e:
            print(f"❌ 이벤트 핸들러 관리자 설정 실패: {e}")
            self.event_handler_manager = None

    def _setup_status_bar_manager(self):
        """상태바 관리자 설정"""
        try:
            self.status_bar_manager = StatusBarManager(self.main_window)
            self.main_window.status_bar_manager = self.status_bar_manager

            print("✅ 상태바 관리자 설정 완료")

        except Exception as e:
            print(f"❌ 상태바 관리자 설정 실패: {e}")
            self.status_bar_manager = None

    def _setup_accessibility_and_i18n(self):
        """접근성 및 국제화 관리자 설정"""
        try:
            # 접근성 관리자 설정
            if (
                hasattr(self.main_window, "accessibility_manager")
                and self.main_window.accessibility_manager
            ):
                self.accessibility_manager = self.main_window.accessibility_manager
                print("✅ 접근성 관리자 설정 완료")

            # 국제화 관리자 설정
            if hasattr(self.main_window, "i18n_manager") and self.main_window.i18n_manager:
                self.i18n_manager = self.main_window.i18n_manager
                print("✅ 국제화 관리자 설정 완료")

        except Exception as e:
            print(f"❌ 접근성 및 국제화 관리자 설정 실패: {e}")

    def _setup_ui_state_management(self):
        """UI 상태 관리 및 마이그레이션 설정"""
        try:
            # UI 상태 관리자 설정
            if hasattr(self.main_window, "ui_state_manager") and self.main_window.ui_state_manager:
                self.ui_state_manager = self.main_window.ui_state_manager
                print("✅ UI 상태 관리자 설정 완료")

            # UI 마이그레이션 관리자 설정
            if (
                hasattr(self.main_window, "ui_migration_manager")
                and self.main_window.ui_migration_manager
            ):
                self.ui_migration_manager = self.main_window.ui_migration_manager
                print("✅ UI 마이그레이션 관리자 설정 완료")

        except Exception as e:
            print(f"❌ UI 상태 관리 및 마이그레이션 설정 실패: {e}")

    def _setup_connections(self):
        """시그널/슬롯 연결 설정"""
        try:
            # 툴바 연결 (안전하게 연결)
            if hasattr(self.main_window, "main_toolbar") and self.main_window.main_toolbar:
                # 기본 툴바의 경우 이미 액션들이 연결되어 있음
                pass

            # 패널 연결 (패널이 존재하는 경우에만)
            if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                try:
                    self.main_window.left_panel.source_folder_selected.connect(
                        self.main_window.on_source_folder_selected
                    )
                    self.main_window.left_panel.source_files_selected.connect(
                        self.main_window.on_source_files_selected
                    )
                    self.main_window.left_panel.destination_folder_selected.connect(
                        self.main_window.on_destination_folder_selected
                    )
                    # self.main_window.left_panel.scan_started.connect(self.main_window.on_scan_started)  # MainWindowCoordinator에서 처리됨
                    self.main_window.left_panel.scan_paused.connect(self.main_window.on_scan_paused)
                    self.main_window.left_panel.settings_opened.connect(
                        self.main_window.on_settings_opened
                    )
                    self.main_window.left_panel.completed_cleared.connect(
                        self.main_window.on_completed_cleared
                    )
                except Exception as e:
                    print(f"⚠️ 패널 연결 실패: {e}")

            # 결과 뷰 연결
            if hasattr(self.main_window, "results_view") and self.main_window.results_view:
                try:
                    self.main_window.results_view.group_selected.connect(
                        self.main_window.on_group_selected
                    )
                except Exception as e:
                    print(f"⚠️ 결과 뷰 연결 실패: {e}")

            print("✅ 시그널/슬롯 연결 설정 완료")

        except Exception as e:
            print(f"❌ 시그널/슬롯 연결 설정 실패: {e}")

    def setup_log_dock(self):
        """로그 Dock 설정 (Phase 5) - 기존 메서드와의 호환성을 위한 래퍼"""
        self._setup_log_dock()

    def add_activity_log(self, message: str):
        """활동 로그 추가 (LogDock으로 리다이렉트)"""
        if self.log_dock:
            self.log_dock.add_activity_log(message)
        else:
            # 폴백: 콘솔에 출력
            print(f"[활동] {message}")

    def add_error_log(self, message: str):
        """오류 로그 추가 (LogDock으로 리다이렉트)"""
        if self.log_dock:
            self.log_dock.add_error_log(message)
        else:
            # 폴백: 콘솔에 출력
            print(f"[오류] {message}")

    def clear_logs(self):
        """로그 초기화 (LogDock으로 리다이렉트)"""
        if self.log_dock:
            self.log_dock.clear_logs()
        else:
            # 폴백: 콘솔에 출력
            print("[로그] 로그 클리어 요청됨")

    def toggle_log_dock(self):
        """로그 Dock 가시성 토글"""
        if self.log_dock:
            self.log_dock.toggle_visibility()

    def show_log_dock(self):
        """로그 Dock 표시"""
        if self.log_dock:
            self.log_dock.show_log_dock()

    def hide_log_dock(self):
        """로그 Dock 숨김"""
        if self.log_dock:
            self.log_dock.hide_log_dock()

    def update_layout_on_resize(self):
        """크기 변경 시 레이아웃 업데이트"""
        try:
            # 현재 윈도우 크기
            window_width = self.main_window.width()

            # 3열 레이아웃 반응형 처리
            if hasattr(self.main_window, "central_triple_layout"):
                self.main_window.central_triple_layout.handle_responsive_layout(window_width)

            # 좌측 도크 반응형 처리 (<1280px에서 자동 접힘)
            if window_width < 1280:
                if (
                    hasattr(self.main_window, "left_panel_dock")
                    and self.main_window.left_panel_dock.isVisible()
                ):
                    self.main_window.left_panel_dock.hide()
            else:
                if (
                    hasattr(self.main_window, "left_panel_dock")
                    and not self.main_window.left_panel_dock.isVisible()
                    and (
                        not hasattr(self.main_window, "_user_dock_toggle")
                        or not self.main_window._user_dock_toggle
                    )
                ):
                    # 사용자가 수동으로 숨기지 않았다면 다시 표시
                    self.main_window.left_panel_dock.show()

            # 왼쪽 패널 크기 조정 (기존 로직)
            if hasattr(self.main_window, "left_panel"):
                # 윈도우가 작을 때는 왼쪽 패널을 더 작게
                if window_width < 1400:
                    self.main_window.left_panel.setMaximumWidth(350)
                else:
                    self.main_window.left_panel.setMaximumWidth(450)

            # 결과 뷰의 테이블 컬럼 크기 조정
            if hasattr(self.main_window, "results_view") and hasattr(
                self.main_window.results_view, "group_table"
            ):
                self._adjust_table_columns()

        except Exception as e:
            print(f"⚠️ 레이아웃 업데이트 실패: {e}")

    def _adjust_table_columns(self):
        """테이블 컬럼 크기를 윈도우 크기에 맞게 조정"""
        try:
            if not hasattr(self.main_window, "results_view"):
                return

            # 그룹 테이블 컬럼 조정
            if hasattr(self.main_window.results_view, "group_table"):
                group_table = self.main_window.results_view.group_table
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
            if hasattr(self.main_window.results_view, "detail_table"):
                detail_table = self.main_window.results_view.detail_table
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

        except Exception as e:
            print(f"⚠️ 테이블 컬럼 조정 실패: {e}")

    def restore_table_column_widths(self):
        """테이블 컬럼 너비 복원"""
        try:
            if (
                not hasattr(self.main_window, "settings_manager")
                or not self.main_window.settings_manager
            ):
                return

            settings = self.main_window.settings_manager.settings
            column_widths = getattr(settings, "table_column_widths", {})

            if (
                column_widths
                and hasattr(self.main_window, "central_triple_layout")
                and hasattr(self.main_window.central_triple_layout, "results_view")
            ):
                results_view = self.main_window.central_triple_layout.results_view

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

            if hasattr(self.main_window, "central_triple_layout") and hasattr(
                self.main_window.central_triple_layout, "results_view"
            ):
                results_view = self.main_window.central_triple_layout.results_view

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
