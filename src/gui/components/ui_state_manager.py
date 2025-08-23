"""
UI 상태 관리자 - Phase 8 UI/UX 리팩토링
QSettings를 사용하여 UI 상태를 저장/복원하는 기능을 제공합니다.
창 크기/위치, 도크 배치, 탭, 컬럼 폭, 스플리터 비율, 검색어 등을 관리합니다.
"""

import logging

from PyQt5.QtCore import QObject, QSettings, pyqtSignal
from PyQt5.QtWidgets import (QDockWidget, QMainWindow, QSplitter, QTableView,
                             QTabWidget)


class UIStateManager(QObject):
    """UI 상태 관리자 - QSettings 기반 상태 저장/복원"""

    state_restored = pyqtSignal()  # 상태 복원 완료 시그널
    state_saved = pyqtSignal()  # 상태 저장 완료 시그널

    def __init__(self, main_window: QMainWindow, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # QSettings 인스턴스
        self.settings = QSettings("AnimeSorter", "UI_State")

        # UI 상태 키들 (기존 설정과 충돌 방지)
        self.state_keys = {
            "window_geometry": "ui_v2/window_geometry",
            "window_state": "ui_v2/window_state",
            "dock_layouts": "ui_v2/dock_layouts",
            "tab_states": "ui_v2/tab_states",
            "column_widths": "ui_v2/column_widths",
            "splitter_ratios": "ui_v2/splitter_ratios",
            "search_terms": "ui_v2/search_terms",
            "active_tab": "ui_v2/active_tab",
            "ui_version": "ui_v2/version",
            # 3열 레이아웃 관련 키들 추가
            "triple_layout_detail_visible": "ui_v2/triple_layout/detail_visible",
            "triple_layout_file_visible": "ui_v2/triple_layout/file_visible",
            "triple_layout_splitter_sizes": "ui_v2/triple_layout/splitter_sizes",
            "triple_layout_user_toggles": "ui_v2/triple_layout/user_toggles",
            "triple_layout_breakpoint_state": "ui_v2/triple_layout/breakpoint_state",
        }

        # UI 버전 관리
        self.current_ui_version = "2.0"

        self.logger.info("UI State Manager 초기화 완료")

    def save_ui_state(self):
        """현재 UI 상태를 QSettings에 저장"""
        try:
            self.logger.info("UI 상태 저장 시작")

            # 1. 윈도우 기하학 및 상태 저장
            self._save_window_state()

            # 2. 도크 레이아웃 저장
            self._save_dock_layouts()

            # 3. 탭 상태 저장
            self._save_tab_states()

            # 4. 컬럼 폭 저장
            self._save_column_widths()

            # 5. 스플리터 비율 저장
            self._save_splitter_ratios()

            # 6. 검색어 저장
            self._save_search_terms()

            # 7. 활성 탭 저장
            self._save_active_tab()

            # 8. 3열 레이아웃 상태 저장
            self._save_triple_layout_state()

            # 9. UI 버전 저장
            self.settings.setValue(self.state_keys["ui_version"], self.current_ui_version)

            # 설정 동기화
            self.settings.sync()

            self.logger.info("UI 상태 저장 완료")
            self.state_saved.emit()

        except Exception as e:
            self.logger.error(f"UI 상태 저장 실패: {e}")

    def restore_ui_state(self):
        """QSettings에서 UI 상태 복원"""
        try:
            self.logger.info("UI 상태 복원 시작")

            # 1. 윈도우 기하학 및 상태 복원
            self._restore_window_state()

            # 2. 도크 레이아웃 복원
            self._restore_dock_layouts()

            # 3. 탭 상태 복원
            self._restore_tab_states()

            # 4. 컬럼 폭 복원
            self._restore_column_widths()

            # 5. 스플리터 비율 복원
            self._restore_splitter_ratios()

            # 6. 검색어 복원
            self._restore_search_terms()

            # 7. 활성 탭 복원
            self._restore_active_tab()

            # 8. 3열 레이아웃 상태 복원
            self._restore_triple_layout_state()

            self.logger.info("UI 상태 복원 완료")
            self.state_restored.emit()

        except Exception as e:
            self.logger.error(f"UI 상태 복원 실패: {e}")

    def _save_triple_layout_state(self):
        """3열 레이아웃 상태 저장"""
        try:
            if hasattr(self.main_window, "central_triple_layout"):
                layout = self.main_window.central_triple_layout

                # 패널 가시성 상태 저장
                self.settings.setValue(
                    self.state_keys["triple_layout_detail_visible"], layout.detail_visible
                )
                self.settings.setValue(
                    self.state_keys["triple_layout_file_visible"], layout.file_visible
                )

                # 스플리터 크기 저장
                splitter_sizes = layout.get_splitter_sizes()
                self.settings.setValue(
                    self.state_keys["triple_layout_splitter_sizes"], splitter_sizes
                )

                # 사용자 토글 상태 저장
                user_toggles = {
                    "detail_toggle": getattr(layout, "_user_detail_toggle", False),
                    "file_toggle": getattr(layout, "_user_file_toggle", False),
                }
                self.settings.setValue(self.state_keys["triple_layout_user_toggles"], user_toggles)

                # 브레이크포인트 상태 저장
                window_width = self.main_window.width()
                breakpoint_state = {
                    "window_width": window_width,
                    "current_breakpoint": self._get_current_breakpoint(window_width),
                }
                self.settings.setValue(
                    self.state_keys["triple_layout_breakpoint_state"], breakpoint_state
                )

                self.logger.debug("3열 레이아웃 상태 저장 완료")

        except Exception as e:
            self.logger.error(f"3열 레이아웃 상태 저장 실패: {e}")

    def _restore_triple_layout_state(self):
        """3열 레이아웃 상태 복원"""
        try:
            if hasattr(self.main_window, "central_triple_layout"):
                layout = self.main_window.central_triple_layout

                # 패널 가시성 상태 복원
                detail_visible = self.settings.value(
                    self.state_keys["triple_layout_detail_visible"], True, type=bool
                )
                file_visible = self.settings.value(
                    self.state_keys["triple_layout_file_visible"], True, type=bool
                )

                # 사용자 토글 상태 복원
                user_toggles = self.settings.value(
                    self.state_keys["triple_layout_user_toggles"],
                    {"detail_toggle": False, "file_toggle": False},
                )

                # 사용자 토글 상태 설정
                layout._user_detail_toggle = user_toggles.get("detail_toggle", False)
                layout._user_file_toggle = user_toggles.get("file_toggle", False)

                # 스플리터 크기 복원
                splitter_sizes = self.settings.value(
                    self.state_keys["triple_layout_splitter_sizes"], None
                )
                if splitter_sizes:
                    try:
                        # 문자열 리스트를 정수 리스트로 변환
                        if isinstance(splitter_sizes, list):
                            # 각 요소를 정수로 변환
                            int_sizes = []
                            for size in splitter_sizes:
                                if isinstance(size, str | int | float):
                                    int_sizes.append(int(size))
                                else:
                                    raise ValueError(f"Invalid size type: {type(size)}")
                            layout.set_splitter_sizes(int_sizes)
                        else:
                            self.logger.warning(
                                f"Splitter sizes is not a list: {type(splitter_sizes)}"
                            )
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"스플리터 크기 변환 실패: {e}, 기본값 사용")

                # 브레이크포인트 상태 복원
                breakpoint_state = self.settings.value(
                    self.state_keys["triple_layout_breakpoint_state"], None
                )

                # 현재 윈도우 크기에 따른 레이아웃 조정
                current_width = self.main_window.width()
                if breakpoint_state:
                    saved_width = breakpoint_state.get("window_width", current_width)
                    # 윈도우 크기가 크게 변경된 경우에만 브레이크포인트 적용
                    if abs(current_width - saved_width) > 100:
                        layout.handle_responsive_layout(current_width)
                    else:
                        # 크기가 비슷하면 저장된 상태 그대로 복원
                        layout.set_detail_visible(detail_visible, False)
                        layout.set_file_visible(file_visible, False)
                else:
                    # 저장된 상태가 없으면 현재 크기에 맞게 조정
                    layout.handle_responsive_layout(current_width)

                self.logger.debug("3열 레이아웃 상태 복원 완료")

        except Exception as e:
            self.logger.error(f"3열 레이아웃 상태 복원 실패: {e}")

    def _get_current_breakpoint(self, window_width: int) -> str:
        """현재 브레이크포인트 반환"""
        if window_width >= 1600:
            return "3column"
        if 1400 <= window_width < 1600:
            return "2column_file_hidden"
        if 1280 <= window_width < 1400:
            return "1column_detail_hidden"
        return "mobile"

    def _save_window_state(self):
        """윈도우 상태 저장"""
        try:
            # 윈도우 기하학 저장
            geometry = self.main_window.geometry()
            geometry_str = f"{geometry.x()},{geometry.y()},{geometry.width()},{geometry.height()}"
            self.settings.setValue(self.state_keys["window_geometry"], geometry_str)

            # 윈도우 상태 저장 (최소화, 최대화 등)
            window_state = self.main_window.saveState()
            self.settings.setValue(self.state_keys["window_state"], window_state)

            self.logger.debug("윈도우 상태 저장 완료")

        except Exception as e:
            self.logger.error(f"윈도우 상태 저장 실패: {e}")

    def _restore_window_state(self):
        """윈도우 상태 복원"""
        try:
            # 윈도우 기하학 복원
            geometry_str = self.settings.value(self.state_keys["window_geometry"])
            if geometry_str:
                try:
                    x, y, width, height = map(int, geometry_str.split(","))
                    self.main_window.setGeometry(x, y, width, height)
                    self.logger.debug("윈도우 기하학 복원 완료")
                except (ValueError, IndexError):
                    self.logger.warning("윈도우 기하학 복원 실패, 기본값 사용")

            # 윈도우 상태 복원
            window_state = self.settings.value(self.state_keys["window_state"])
            if window_state:
                self.main_window.restoreState(window_state)
                self.logger.debug("윈도우 상태 복원 완료")

        except Exception as e:
            self.logger.error(f"윈도우 상태 복원 실패: {e}")

    def _save_dock_layouts(self):
        """도크 레이아웃 저장"""
        try:
            dock_layouts = {}

            # 모든 도크 위젯의 상태 저장
            for dock in self.main_window.findChildren(QDockWidget):
                dock_name = dock.objectName()
                if dock_name:
                    dock_state = {
                        "visible": dock.isVisible(),
                        "floating": dock.isFloating(),
                        "geometry": f"{dock.geometry().x()},{dock.geometry().y()},{dock.geometry().width()},{dock.geometry().height()}",
                        "allowed_areas": int(dock.allowedAreas()),
                        "features": int(dock.features()),
                    }
                    dock_layouts[dock_name] = dock_state

            self.settings.setValue(self.state_keys["dock_layouts"], dock_layouts)
            self.logger.debug(f"도크 레이아웃 저장 완료: {len(dock_layouts)}개 도크")

        except Exception as e:
            self.logger.error(f"도크 레이아웃 저장 실패: {e}")

    def _restore_dock_layouts(self):
        """도크 레이아웃 복원"""
        try:
            dock_layouts = self.settings.value(self.state_keys["dock_layouts"], {})

            for dock_name, dock_state in dock_layouts.items():
                dock = self.main_window.findChild(QDockWidget, dock_name)
                if dock:
                    try:
                        # 도크 가시성 복원
                        dock.setVisible(dock_state.get("visible", True))

                        # 도크 위치/크기 복원
                        if "geometry" in dock_state:
                            geo_parts = dock_state["geometry"].split(",")
                            if len(geo_parts) == 4:
                                x, y, width, height = map(int, geo_parts)
                                dock.setGeometry(x, y, width, height)

                        # 도크 특성 복원
                        if "features" in dock_state:
                            try:
                                features = dock_state["features"]
                                # 정수를 QDockWidget.DockWidgetFeatures로 변환
                                if isinstance(features, int):
                                    dock.setFeatures(QDockWidget.DockWidgetFeatures(features))
                                else:
                                    dock.setFeatures(features)
                            except Exception as e:
                                self.logger.warning(f"도크 {dock_name} features 복원 실패: {e}")

                    except Exception as e:
                        self.logger.warning(f"도크 {dock_name} 복원 실패: {e}")

            self.logger.debug(f"도크 레이아웃 복원 완료: {len(dock_layouts)}개 도크")

        except Exception as e:
            self.logger.error(f"도크 레이아웃 복원 실패: {e}")

    def _save_tab_states(self):
        """탭 상태 저장"""
        try:
            tab_states = {}

            # ResultsView의 탭 상태 저장
            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view
                if isinstance(results_view, QTabWidget):
                    tab_states["results_view"] = {
                        "current_index": results_view.currentIndex(),
                        "tab_enabled": [
                            results_view.isTabEnabled(i) for i in range(results_view.count())
                        ],
                    }

            self.settings.setValue(self.state_keys["tab_states"], tab_states)
            self.logger.debug("탭 상태 저장 완료")

        except Exception as e:
            self.logger.error(f"탭 상태 저장 실패: {e}")

    def _restore_tab_states(self):
        """탭 상태 복원"""
        try:
            tab_states = self.settings.value(self.state_keys["tab_states"], {})

            # ResultsView의 탭 상태 복원
            if "results_view" in tab_states and hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view
                if isinstance(results_view, QTabWidget):
                    state = tab_states["results_view"]

                    # 활성 탭 복원
                    if "current_index" in state:
                        current_index = state["current_index"]
                        if 0 <= current_index < results_view.count():
                            results_view.setCurrentIndex(current_index)

                    # 탭 활성화 상태 복원
                    if "tab_enabled" in state:
                        for i, enabled in enumerate(state["tab_enabled"]):
                            if i < results_view.count():
                                results_view.setTabEnabled(i, enabled)

            self.logger.debug("탭 상태 복원 완료")

        except Exception as e:
            self.logger.error(f"탭 상태 복원 실패: {e}")

    def _save_column_widths(self):
        """컬럼 폭 저장"""
        try:
            column_widths = {}

            # ResultsView의 모든 테이블 컬럼 폭 저장
            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view

                # 그룹 테이블들
                group_tables = [
                    ("all_group", getattr(results_view, "all_group_table", None)),
                    ("unmatched_group", getattr(results_view, "unmatched_group_table", None)),
                    ("conflict_group", getattr(results_view, "conflict_group_table", None)),
                    ("duplicate_group", getattr(results_view, "duplicate_group_table", None)),
                    ("completed_group", getattr(results_view, "completed_group_table", None)),
                ]

                for table_name, table in group_tables:
                    if table and isinstance(table, QTableView):
                        widths = {}
                        for i in range(table.model().columnCount() if table.model() else 0):
                            widths[i] = table.columnWidth(i)
                        column_widths[table_name] = widths

                # 상세 테이블들
                detail_tables = [
                    ("all_detail", getattr(results_view, "all_detail_table", None)),
                    ("unmatched_detail", getattr(results_view, "unmatched_detail_table", None)),
                    ("conflict_detail", getattr(results_view, "conflict_detail_table", None)),
                    ("duplicate_detail", getattr(results_view, "duplicate_detail_table", None)),
                    ("completed_detail", getattr(results_view, "completed_detail_table", None)),
                ]

                for table_name, table in detail_tables:
                    if table and isinstance(table, QTableView):
                        widths = {}
                        for i in range(table.model().columnCount() if table.model() else 0):
                            widths[i] = table.columnWidth(i)
                        column_widths[table_name] = widths

            self.settings.setValue(self.state_keys["column_widths"], column_widths)
            self.logger.debug(f"컬럼 폭 저장 완료: {len(column_widths)}개 테이블")

        except Exception as e:
            self.logger.error(f"컬럼 폭 저장 실패: {e}")

    def _restore_column_widths(self):
        """컬럼 폭 복원"""
        try:
            column_widths = self.settings.value(self.state_keys["column_widths"], {})

            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view

                # 그룹 테이블들 복원
                group_tables = [
                    ("all_group", getattr(results_view, "all_group_table", None)),
                    ("unmatched_group", getattr(results_view, "unmatched_group_table", None)),
                    ("conflict_group", getattr(results_view, "conflict_group_table", None)),
                    ("duplicate_group", getattr(results_view, "duplicate_group_table", None)),
                    ("completed_group", getattr(results_view, "completed_group_table", None)),
                ]

                for table_name, table in group_tables:
                    if table and table_name in column_widths:
                        widths = column_widths[table_name]
                        for col, width in widths.items():
                            if col < table.model().columnCount() if table.model() else 0:
                                table.setColumnWidth(col, width)

                # 상세 테이블들 복원
                detail_tables = [
                    ("all_detail", getattr(results_view, "all_detail_table", None)),
                    ("unmatched_detail", getattr(results_view, "unmatched_detail_table", None)),
                    ("conflict_detail", getattr(results_view, "conflict_detail_table", None)),
                    ("duplicate_detail", getattr(results_view, "duplicate_detail_table", None)),
                    ("completed_detail", getattr(results_view, "completed_detail_table", None)),
                ]

                for table_name, table in detail_tables:
                    if table and table_name in column_widths:
                        widths = column_widths[table_name]
                        for col, width in widths.items():
                            if col < table.model().columnCount() if table.model() else 0:
                                table.setColumnWidth(col, width)

            self.logger.debug(f"컬럼 폭 복원 완료: {len(column_widths)}개 테이블")

        except Exception as e:
            self.logger.error(f"컬럼 폭 복원 실패: {e}")

    def _save_splitter_ratios(self):
        """스플리터 비율 저장"""
        try:
            splitter_ratios = {}

            # 메인 스플리터
            if hasattr(self.main_window, "main_splitter"):
                main_splitter = self.main_window.main_splitter
                if isinstance(main_splitter, QSplitter):
                    splitter_ratios["main_splitter"] = main_splitter.sizes()

            # ResultsView의 스플리터들
            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view

                splitters = [
                    ("all_splitter", getattr(results_view, "all_splitter", None)),
                    ("unmatched_splitter", getattr(results_view, "unmatched_splitter", None)),
                    ("conflict_splitter", getattr(results_view, "conflict_splitter", None)),
                    ("duplicate_splitter", getattr(results_view, "duplicate_splitter", None)),
                    ("completed_splitter", getattr(results_view, "completed_splitter", None)),
                ]

                for splitter_name, splitter in splitters:
                    if splitter and isinstance(splitter, QSplitter):
                        splitter_ratios[splitter_name] = splitter.sizes()

            self.settings.setValue(self.state_keys["splitter_ratios"], splitter_ratios)
            self.logger.debug(f"스플리터 비율 저장 완료: {len(splitter_ratios)}개 스플리터")

        except Exception as e:
            self.logger.error(f"스플리터 비율 저장 실패: {e}")

    def _restore_splitter_ratios(self):
        """스플리터 비율 복원"""
        try:
            splitter_ratios = self.settings.value(self.state_keys["splitter_ratios"], {})

            # 메인 스플리터 복원
            if "main_splitter" in splitter_ratios and hasattr(self.main_window, "main_splitter"):
                main_splitter = self.main_window.main_splitter
                if isinstance(main_splitter, QSplitter):
                    sizes = splitter_ratios["main_splitter"]
                    if len(sizes) == main_splitter.count():
                        main_splitter.setSizes(sizes)

            # ResultsView의 스플리터들 복원
            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view

                splitters = [
                    ("all_splitter", getattr(results_view, "all_splitter", None)),
                    ("unmatched_splitter", getattr(results_view, "unmatched_splitter", None)),
                    ("conflict_splitter", getattr(results_view, "conflict_splitter", None)),
                    ("duplicate_splitter", getattr(results_view, "duplicate_splitter", None)),
                    ("completed_splitter", getattr(results_view, "completed_splitter", None)),
                ]

                for splitter_name, splitter in splitters:
                    if splitter and splitter_name in splitter_ratios:
                        sizes = splitter_ratios[splitter_name]
                        if len(sizes) == splitter.count():
                            splitter.setSizes(sizes)

            self.logger.debug(f"스플리터 비율 복원 완료: {len(splitter_ratios)}개 스플리터")

        except Exception as e:
            self.logger.error(f"스플리터 비율 복원 실패: {e}")

    def _save_search_terms(self):
        """검색어 저장"""
        try:
            search_terms = {}

            # ResultsView의 검색어 저장
            if hasattr(self.main_window, "results_view") and hasattr(
                self.main_window.results_view, "filter_manager"
            ):
                filter_manager = self.main_window.results_view.filter_manager
                if hasattr(filter_manager, "filter_proxies"):
                    for tab_name, proxy in filter_manager.filter_proxies.items():
                        search_text = proxy.get_search_text()
                        if search_text:
                            search_terms[tab_name] = search_text

            self.settings.setValue(self.state_keys["search_terms"], search_terms)
            self.logger.debug(f"검색어 저장 완료: {len(search_terms)}개 탭")

        except Exception as e:
            self.logger.error(f"검색어 저장 실패: {e}")

    def _restore_search_terms(self):
        """검색어 복원"""
        try:
            search_terms = self.settings.value(self.state_keys["search_terms"], {})

            # ResultsView의 검색어 복원
            if hasattr(self.main_window, "results_view") and hasattr(
                self.main_window.results_view, "filter_manager"
            ):
                filter_manager = self.main_window.results_view.filter_manager
                if hasattr(filter_manager, "search_widgets"):
                    for tab_name, search_text in search_terms.items():
                        search_widget = filter_manager.get_search_widget(tab_name)
                        if search_widget:
                            search_widget.set_search_text(search_text)

            self.logger.debug(f"검색어 복원 완료: {len(search_terms)}개 탭")

        except Exception as e:
            self.logger.error(f"검색어 복원 실패: {e}")

    def _save_active_tab(self):
        """활성 탭 저장"""
        try:
            active_tab = 0  # 기본값

            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view
                if isinstance(results_view, QTabWidget):
                    active_tab = results_view.currentIndex()

            self.settings.setValue(self.state_keys["active_tab"], active_tab)
            self.logger.debug(f"활성 탭 저장 완료: {active_tab}")

        except Exception as e:
            self.logger.error(f"활성 탭 저장 실패: {e}")

    def _restore_active_tab(self):
        """활성 탭 복원"""
        try:
            active_tab = self.settings.value(self.state_keys["active_tab"], 0)

            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view
                if isinstance(results_view, QTabWidget) and 0 <= active_tab < results_view.count():
                    results_view.setCurrentIndex(active_tab)
                    self.logger.debug(f"활성 탭 복원 완료: {active_tab}")

        except Exception as e:
            self.logger.error(f"활성 탭 복원 실패: {e}")

    def clear_ui_state(self):
        """UI 상태 초기화"""
        try:
            for key in self.state_keys.values():
                self.settings.remove(key)

            self.settings.sync()
            self.logger.info("UI 상태 초기화 완료")

        except Exception as e:
            self.logger.error(f"UI 상태 초기화 실패: {e}")

    def get_ui_version(self) -> str:
        """저장된 UI 버전 반환"""
        return self.settings.value(self.state_keys["ui_version"], "1.0")

    def is_ui_v2_enabled(self) -> bool:
        """UI v2가 활성화되어 있는지 확인"""
        return self.get_ui_version() == "2.0"
