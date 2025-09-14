"""
UI 컴포넌트 관리 로직을 담당하는 클래스
MainWindow의 UI 컴포넌트 생성, 설정, 연결 로직을 분리하여 가독성과 유지보수성을 향상시킵니다.
"""

import logging

logger = logging.getLogger(__name__)

from PyQt5.QtWidgets import QHeaderView, QMainWindow

from src.gui.base_classes import StateInitializationMixin
from src.gui.components.log_dock import LogDock
from src.gui.handlers.event_handler_manager import EventHandlerManager
from src.gui.initializers.ui_initializer import UIInitializer
from src.gui.managers.status_bar_manager import StatusBarManager


class UIComponentManager(StateInitializationMixin):
    """UI 컴포넌트 관리를 담당하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        super().__init__()
        self.main_window = main_window
        self.initialize_state()

    def _get_default_state_config(self):
        """Get the default state configuration for UIComponentManager."""
        return {
            "managers": {
                "log_dock": None,
                "ui_initializer": None,
                "event_handler_manager": None,
                "status_bar_manager": None,
                "accessibility_manager": None,
                "i18n_manager": None,
                "ui_state_manager": None,
                "ui_migration_manager": None,
                "anime_data_manager": None,
                "file_organization_service": None,
                "tmdb_manager": None,
            },
            "collections": {"tmdb_search_dialogs": "dict", "poster_cache": "dict"},
            "strings": {},
            "flags": {},
            "config": {},
        }

    def setup_all_components(self):
        """모든 UI 컴포넌트를 설정하고 연결"""
        try:
            logger.info("🔧 UI 컴포넌트 설정 시작...")
            self._setup_log_dock()
            self._setup_ui_initializer()
            self._setup_event_handler_manager()
            self._setup_status_bar_manager()
            self._setup_accessibility_and_i18n()
            self._setup_ui_state_management()
            self._setup_connections()
            logger.info("✅ UI 컴포넌트 설정 완료!")
        except Exception as e:
            logger.info("❌ UI 컴포넌트 설정 실패: %s", e)
            import traceback

            traceback.print_exc()

    def _setup_log_dock(self):
        """로그 Dock 설정"""
        try:
            self.log_dock = LogDock(self.main_window)
            self.main_window.log_dock = self.log_dock
            from PyQt5.QtCore import Qt

            self.main_window.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
            self.log_dock.setVisible(False)
            self.log_dock.load_dock_state()
            logger.info("✅ 로그 Dock 설정 완료")
        except Exception as e:
            logger.info("❌ 로그 Dock 설정 실패: %s", e)
            self.log_dock = None

    def _setup_ui_initializer(self):
        """UI 초기화 설정"""
        try:
            self.ui_initializer = UIInitializer(self.main_window)
            self.main_window.ui_initializer = self.ui_initializer
            self.ui_initializer.init_ui()
            logger.info("✅ UI 초기화 설정 및 실행 완료")
        except Exception as e:
            logger.info("❌ UI 초기화 설정 실패: %s", e)
            self.ui_initializer = None

    def _setup_event_handler_manager(self):
        """이벤트 핸들러 관리자 설정"""
        try:
            if hasattr(self.main_window, "event_bus") and self.main_window.event_bus:
                self.event_handler_manager = EventHandlerManager(
                    self.main_window, self.main_window.event_bus
                )
                self.main_window.event_handler_manager = self.event_handler_manager
                self.event_handler_manager.setup_event_subscriptions()
                logger.info("✅ 이벤트 핸들러 관리자 설정 완료")
            else:
                logger.info(
                    "⚠️ EventBus가 초기화되지 않아 이벤트 핸들러 관리자를 설정할 수 없습니다."
                )
        except Exception as e:
            logger.info("❌ 이벤트 핸들러 관리자 설정 실패: %s", e)
            self.event_handler_manager = None

    def _setup_status_bar_manager(self):
        """상태바 관리자 설정"""
        try:
            self.status_bar_manager = StatusBarManager(self.main_window)
            self.main_window.status_bar_manager = self.status_bar_manager
            logger.info("✅ 상태바 관리자 설정 완료")
        except Exception as e:
            logger.info("❌ 상태바 관리자 설정 실패: %s", e)
            self.status_bar_manager = None

    def _setup_accessibility_and_i18n(self):
        """접근성 및 국제화 관리자 설정"""
        try:
            if (
                hasattr(self.main_window, "accessibility_manager")
                and self.main_window.accessibility_manager
            ):
                self.accessibility_manager = self.main_window.accessibility_manager
                logger.info("✅ 접근성 관리자 설정 완료")
            if hasattr(self.main_window, "i18n_manager") and self.main_window.i18n_manager:
                self.i18n_manager = self.main_window.i18n_manager
                logger.info("✅ 국제화 관리자 설정 완료")
        except Exception as e:
            logger.info("❌ 접근성 및 국제화 관리자 설정 실패: %s", e)

    def _setup_ui_state_management(self):
        """UI 상태 관리 및 마이그레이션 설정"""
        try:
            if hasattr(self.main_window, "ui_state_manager") and self.main_window.ui_state_manager:
                self.ui_state_manager = self.main_window.ui_state_manager
                logger.info("✅ UI 상태 관리자 설정 완료")
            if (
                hasattr(self.main_window, "ui_migration_manager")
                and self.main_window.ui_migration_manager
            ):
                self.ui_migration_manager = self.main_window.ui_migration_manager
                logger.info("✅ UI 마이그레이션 관리자 설정 완료")
        except Exception as e:
            logger.info("❌ UI 상태 관리 및 마이그레이션 설정 실패: %s", e)

    def _setup_connections(self):
        """시그널/슬롯 연결 설정"""
        try:
            if hasattr(self.main_window, "main_toolbar") and self.main_window.main_toolbar:
                pass
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
                    self.main_window.left_panel.scan_paused.connect(self.main_window.on_scan_paused)
                    self.main_window.left_panel.settings_opened.connect(
                        self.main_window.on_settings_opened
                    )
                    self.main_window.left_panel.completed_cleared.connect(
                        self.main_window.on_completed_cleared
                    )
                except Exception as e:
                    logger.info("⚠️ 패널 연결 실패: %s", e)
            if hasattr(self.main_window, "results_view") and self.main_window.results_view:
                try:
                    self.main_window.results_view.group_selected.connect(
                        self.main_window.on_group_selected
                    )
                except Exception as e:
                    logger.info("⚠️ 결과 뷰 연결 실패: %s", e)
            logger.info("✅ 시그널/슬롯 연결 설정 완료")
        except Exception as e:
            logger.info("❌ 시그널/슬롯 연결 설정 실패: %s", e)

    def setup_log_dock(self):
        """로그 Dock 설정 (Phase 5) - 기존 메서드와의 호환성을 위한 래퍼"""
        self._setup_log_dock()

    def add_activity_log(self, message: str):
        """활동 로그 추가 (LogDock으로 리다이렉트)"""
        if self.log_dock:
            self.log_dock.add_activity_log(message)
        else:
            logger.info("[활동] %s", message)

    def add_error_log(self, message: str):
        """오류 로그 추가 (LogDock으로 리다이렉트)"""
        if self.log_dock:
            self.log_dock.add_error_log(message)
        else:
            logger.info("[오류] %s", message)

    def clear_logs(self):
        """로그 초기화 (LogDock으로 리다이렉트)"""
        if self.log_dock:
            self.log_dock.clear_logs()
        else:
            logger.info("[로그] 로그 클리어 요청됨")

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
            window_width = self.main_window.width()
            if hasattr(self.main_window, "central_triple_layout"):
                self.main_window.central_triple_layout.handle_responsive_layout(window_width)
            if window_width < 1280:
                if (
                    hasattr(self.main_window, "left_panel_dock")
                    and self.main_window.left_panel_dock.isVisible()
                ):
                    self.main_window.left_panel_dock.hide()
            elif (
                hasattr(self.main_window, "left_panel_dock")
                and not self.main_window.left_panel_dock.isVisible()
                and (
                    not hasattr(self.main_window, "_user_dock_toggle")
                    or not self.main_window._user_dock_toggle
                )
            ):
                self.main_window.left_panel_dock.show()
            if hasattr(self.main_window, "left_panel"):
                if window_width < 1400:
                    self.main_window.left_panel.setMaximumWidth(350)
                else:
                    self.main_window.left_panel.setMaximumWidth(450)
            if hasattr(self.main_window, "results_view") and hasattr(
                self.main_window.results_view, "group_table"
            ):
                self._adjust_table_columns()
        except Exception as e:
            logger.info("⚠️ 레이아웃 업데이트 실패: %s", e)

    def _adjust_table_columns(self):
        """테이블 컬럼 크기를 윈도우 크기에 맞게 조정"""
        try:
            if not hasattr(self.main_window, "results_view"):
                return
            if hasattr(self.main_window.results_view, "group_table"):
                group_table = self.main_window.results_view.group_table
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
            if hasattr(self.main_window.results_view, "detail_table"):
                detail_table = self.main_window.results_view.detail_table
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
        except Exception as e:
            logger.info("⚠️ 테이블 컬럼 조정 실패: %s", e)

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
                if hasattr(results_view, "group_table") and results_view.group_table:
                    table = results_view.group_table
                    for col_str, width in column_widths.items():
                        try:
                            col = int(col_str)
                            if col < table.model().columnCount():
                                table.setColumnWidth(col, width)
                        except (ValueError, TypeError) as e:
                            logger.info("⚠️ 컬럼 인덱스 변환 실패: %s -> %s", col_str, e)
                            continue
                if hasattr(results_view, "detail_table") and results_view.detail_table:
                    table = results_view.detail_table
                    for col_str, width in column_widths.items():
                        try:
                            col = int(col_str)
                            if col < table.model().columnCount():
                                table.setColumnWidth(col, width)
                        except (ValueError, TypeError) as e:
                            logger.info("⚠️ 컬럼 인덱스 변환 실패: %s -> %s", col_str, e)
                            continue
                logger.info("✅ 테이블 컬럼 너비 복원 완료")
        except Exception as e:
            logger.info("⚠️ 테이블 컬럼 너비 복원 실패: %s", e)

    def get_table_column_widths(self):
        """테이블 컬럼 너비 가져오기"""
        try:
            column_widths = {}
            if hasattr(self.main_window, "central_triple_layout") and hasattr(
                self.main_window.central_triple_layout, "results_view"
            ):
                results_view = self.main_window.central_triple_layout.results_view
                if hasattr(results_view, "group_table") and results_view.group_table:
                    table = results_view.group_table
                    for i in range(table.model().columnCount()):
                        column_widths[str(i)] = table.columnWidth(i)
                if hasattr(results_view, "detail_table") and results_view.detail_table:
                    table = results_view.detail_table
                    for i in range(table.model().columnCount()):
                        column_widths[str(i)] = table.columnWidth(i)
            return column_widths
        except Exception as e:
            logger.info("⚠️ 테이블 컬럼 너비 가져오기 실패: %s", e)
            return {}
