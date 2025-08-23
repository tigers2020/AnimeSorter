"""
UI 마이그레이션 관리자 - Phase 8 UI/UX 리팩토링
UI v1과 v2 간의 마이그레이션 전략을 구현합니다.
기존 레이아웃을 유지하면서 신규 레이아웃으로 전환할 수 있도록 합니다.
"""

import logging
from typing import Any

from PyQt5.QtCore import QObject, QSettings, pyqtSignal
from PyQt5.QtWidgets import QDockWidget, QMainWindow


class UIMigrationManager(QObject):
    """UI 마이그레이션 관리자 - v1/v2 레이아웃 전환 관리"""

    migration_started = pyqtSignal(str)  # 마이그레이션 시작 시그널
    migration_completed = pyqtSignal(str)  # 마이그레이션 완료 시그널
    migration_failed = pyqtSignal(str, str)  # 마이그레이션 실패 시그널 (버전, 에러)

    def __init__(self, main_window: QMainWindow, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # QSettings 인스턴스
        self.settings = QSettings("AnimeSorter", "UI_Migration")

        # 마이그레이션 관련 키들
        self.migration_keys = {
            "ui_version": "ui/version",
            "migration_status": "ui/migration_status",
            "v1_layout_backup": "ui/v1_layout_backup",
            "v2_layout_preferences": "ui/v2_layout_preferences",
            "migration_timestamp": "ui/migration_timestamp",
            "rollback_available": "ui/rollback_available",
        }

        # UI 버전들
        self.UI_V1 = "1.0"
        self.UI_V2 = "2.0"

        # 마이그레이션 상태
        self.migration_statuses = {
            "not_started": "not_started",
            "in_progress": "in_progress",
            "completed": "completed",
            "failed": "failed",
            "rolled_back": "rolled_back",
        }

        self.logger.info("UI Migration Manager 초기화 완료")

    def get_current_ui_version(self) -> str:
        """현재 UI 버전 반환"""
        return self.settings.value(self.migration_keys["ui_version"], self.UI_V1)

    def get_migration_status(self) -> str:
        """마이그레이션 상태 반환"""
        return self.settings.value(
            self.migration_keys["migration_status"], self.migration_statuses["not_started"]
        )

    def is_migration_available(self) -> bool:
        """마이그레이션이 가능한지 확인"""
        current_version = self.get_current_ui_version()
        return current_version == self.UI_V1

    def can_rollback(self) -> bool:
        """롤백이 가능한지 확인"""
        return self.settings.value(self.migration_keys["rollback_available"], False)

    def start_migration_to_v2(self) -> bool:
        """UI v2로 마이그레이션 시작"""
        try:
            if not self.is_migration_available():
                self.logger.warning(
                    "마이그레이션이 불가능합니다. 이미 v2이거나 상태가 올바르지 않습니다."
                )
                return False

            self.logger.info("UI v2 마이그레이션 시작")
            self.migration_started.emit(self.UI_V2)

            # 마이그레이션 상태를 진행 중으로 설정
            self.settings.setValue(
                self.migration_keys["migration_status"], self.migration_statuses["in_progress"]
            )

            # 1. v1 레이아웃 백업
            if not self._backup_v1_layout():
                raise Exception("v1 레이아웃 백업 실패")

            # 2. v2 레이아웃 적용
            if not self._apply_v2_layout():
                raise Exception("v2 레이아웃 적용 실패")

            # 3. 마이그레이션 완료
            self.settings.setValue(self.migration_keys["ui_version"], self.UI_V2)
            self.settings.setValue(
                self.migration_keys["migration_status"], self.migration_statuses["completed"]
            )
            self.settings.setValue(
                self.migration_keys["migration_timestamp"], self._get_current_timestamp()
            )
            self.settings.setValue(self.migration_keys["rollback_available"], True)

            self.settings.sync()

            self.logger.info("UI v2 마이그레이션 완료")
            self.migration_completed.emit(self.UI_V2)
            return True

        except Exception as e:
            self.logger.error(f"UI v2 마이그레이션 실패: {e}")
            self.settings.setValue(
                self.migration_keys["migration_status"], self.migration_statuses["failed"]
            )
            self.settings.sync()
            self.migration_failed.emit(self.UI_V2, str(e))
            return False

    def rollback_to_v1(self) -> bool:
        """UI v1으로 롤백"""
        try:
            if not self.can_rollback():
                self.logger.warning("롤백이 불가능합니다. 백업이 없거나 이미 v1입니다.")
                return False

            self.logger.info("UI v1으로 롤백 시작")

            # 1. v1 레이아웃 복원
            if not self._restore_v1_layout():
                raise Exception("v1 레이아웃 복원 실패")

            # 2. 버전을 v1으로 되돌리기
            self.settings.setValue(self.migration_keys["ui_version"], self.UI_V1)
            self.settings.setValue(
                self.migration_keys["migration_status"], self.migration_statuses["rolled_back"]
            )

            self.settings.sync()

            self.logger.info("UI v1 롤백 완료")
            return True

        except Exception as e:
            self.logger.error(f"UI v1 롤백 실패: {e}")
            return False

    def _backup_v1_layout(self) -> bool:
        """v1 레이아웃 백업"""
        try:
            self.logger.debug("v1 레이아웃 백업 시작")

            v1_layout = {}

            # 1. 윈도우 기하학 백업
            geometry = self.main_window.geometry()
            v1_layout["window_geometry"] = {
                "x": geometry.x(),
                "y": geometry.y(),
                "width": geometry.width(),
                "height": geometry.height(),
            }

            # 2. 윈도우 상태 백업
            v1_layout["window_state"] = self.main_window.saveState()

            # 3. 도크 레이아웃 백업
            v1_layout["dock_layouts"] = self._backup_dock_layouts()

            # 4. 기존 테이블 상태 백업 (v1에서 사용하던 방식)
            v1_layout["table_states"] = self._backup_v1_table_states()

            # 백업 저장
            self.settings.setValue(self.migration_keys["v1_layout_backup"], v1_layout)

            self.logger.debug("v1 레이아웃 백업 완료")
            return True

        except Exception as e:
            self.logger.error(f"v1 레이아웃 백업 실패: {e}")
            return False

    def _backup_dock_layouts(self) -> dict[str, Any]:
        """도크 레이아웃 백업"""
        dock_layouts = {}

        try:
            for dock in self.main_window.findChildren(QDockWidget):
                dock_name = dock.objectName()
                if dock_name:
                    dock_state = {
                        "visible": dock.isVisible(),
                        "floating": dock.isFloating(),
                        "geometry": {
                            "x": dock.geometry().x(),
                            "y": dock.geometry().y(),
                            "width": dock.geometry().width(),
                            "height": dock.geometry().height(),
                        },
                        "allowed_areas": int(dock.allowedAreas()),
                        "features": int(dock.features()),
                        "dock_widget_area": self.main_window.dockWidgetArea(dock),
                    }
                    dock_layouts[dock_name] = dock_state
        except Exception as e:
            self.logger.warning(f"도크 레이아웃 백업 중 일부 실패: {e}")

        return dock_layouts

    def _backup_v1_table_states(self) -> dict[str, Any]:
        """v1 테이블 상태 백업 (기존 방식)"""
        table_states = {}

        try:
            # 기존 v1 방식의 테이블 상태 백업
            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view

                # 그룹 테이블
                if hasattr(results_view, "group_table"):
                    group_table = results_view.group_table
                    if group_table and group_table.model():
                        widths = {}
                        for i in range(group_table.model().columnCount()):
                            widths[i] = group_table.columnWidth(i)
                        table_states["group_table"] = widths

                # 상세 테이블
                if hasattr(results_view, "detail_table"):
                    detail_table = results_view.detail_table
                    if detail_table and detail_table.model():
                        widths = {}
                        for i in range(detail_table.model().columnCount()):
                            widths[i] = detail_table.columnWidth(i)
                        table_states["detail_table"] = widths
        except Exception as e:
            self.logger.warning(f"v1 테이블 상태 백업 중 일부 실패: {e}")

        return table_states

    def _apply_v2_layout(self) -> bool:
        """v2 레이아웃 적용"""
        try:
            self.logger.debug("v2 레이아웃 적용 시작")

            # 1. 기존 v1 레이아웃 정리
            self._cleanup_v1_layout()

            # 2. v2 레이아웃 초기화
            if not self._initialize_v2_layout():
                raise Exception("v2 레이아웃 초기화 실패")

            # 3. v2 기본 설정 적용
            self._apply_v2_defaults()

            self.logger.debug("v2 레이아웃 적용 완료")
            return True

        except Exception as e:
            self.logger.error(f"v2 레이아웃 적용 실패: {e}")
            return False

    def _cleanup_v1_layout(self):
        """v1 레이아웃 정리"""
        try:
            # 기존 v1 방식의 위젯들 정리
            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view

                # 기존 v1 테이블들 정리
                if hasattr(results_view, "group_table"):
                    results_view.group_table = None
                if hasattr(results_view, "detail_table"):
                    results_view.detail_table = None

                # 기존 v1 레이아웃 정리
                if hasattr(results_view, "layout"):
                    layout = results_view.layout()
                    if layout:
                        # 기존 위젯들 제거
                        while layout.count():
                            item = layout.takeAt(0)
                            if item.widget():
                                item.widget().deleteLater()

            self.logger.debug("v1 레이아웃 정리 완료")

        except Exception as e:
            self.logger.warning(f"v1 레이아웃 정리 중 일부 실패: {e}")

    def _initialize_v2_layout(self) -> bool:
        """v2 레이아웃 초기화"""
        try:
            # ResultsView가 이미 v2로 초기화되어 있는지 확인
            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view

                # v2 구조 확인 (5개 탭 구조)
                if (
                    hasattr(results_view, "all_tab")
                    and hasattr(results_view, "unmatched_tab")
                    and hasattr(results_view, "conflict_tab")
                    and hasattr(results_view, "duplicate_tab")
                    and hasattr(results_view, "completed_tab")
                ):
                    self.logger.debug("v2 레이아웃이 이미 초기화되어 있습니다.")
                    return True

                # v2 레이아웃이 없다면 초기화 필요
                self.logger.warning(
                    "v2 레이아웃이 초기화되지 않았습니다. 수동 초기화가 필요합니다."
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"v2 레이아웃 초기화 실패: {e}")
            return False

    def _apply_v2_defaults(self):
        """v2 기본 설정 적용"""
        try:
            # v2 기본 설정들을 적용
            v2_preferences = {
                "default_tab": "unmatched",  # 기본 활성 탭
                "splitter_ratios": [0.6, 0.4],  # 기본 스플리터 비율
                "column_auto_resize": True,  # 컬럼 자동 크기 조정
                "show_search_widgets": True,  # 검색 위젯 표시
                "enable_advanced_splitters": True,  # 고급 스플리터 활성화
            }

            self.settings.setValue(self.migration_keys["v2_layout_preferences"], v2_preferences)

            self.logger.debug("v2 기본 설정 적용 완료")

        except Exception as e:
            self.logger.warning(f"v2 기본 설정 적용 중 일부 실패: {e}")

    def _restore_v1_layout(self) -> bool:
        """v1 레이아웃 복원"""
        try:
            self.logger.debug("v1 레이아웃 복원 시작")

            # 백업된 v1 레이아웃 가져오기
            v1_layout = self.settings.value(self.migration_keys["v1_layout_backup"], {})
            if not v1_layout:
                raise Exception("v1 레이아웃 백업이 없습니다.")

            # 1. 윈도우 기하학 복원
            if "window_geometry" in v1_layout:
                geo = v1_layout["window_geometry"]
                self.main_window.setGeometry(geo["x"], geo["y"], geo["width"], geo["height"])

            # 2. 윈도우 상태 복원
            if "window_state" in v1_layout:
                self.main_window.restoreState(v1_layout["window_state"])

            # 3. 도크 레이아웃 복원
            if "dock_layouts" in v1_layout:
                self._restore_dock_layouts(v1_layout["dock_layouts"])

            # 4. 테이블 상태 복원
            if "table_states" in v1_layout:
                self._restore_v1_table_states(v1_layout["table_states"])

            self.logger.debug("v1 레이아웃 복원 완료")
            return True

        except Exception as e:
            self.logger.error(f"v1 레이아웃 복원 실패: {e}")
            return False

    def _restore_dock_layouts(self, dock_layouts: dict[str, Any]):
        """도크 레이아웃 복원"""
        try:
            for dock_name, dock_state in dock_layouts.items():
                dock = self.main_window.findChild(QDockWidget, dock_name)
                if dock:
                    try:
                        # 도크 가시성 복원
                        dock.setVisible(dock_state.get("visible", True))

                        # 도크 위치/크기 복원
                        if "geometry" in dock_state:
                            geo = dock_state["geometry"]
                            dock.setGeometry(geo["x"], geo["y"], geo["width"], geo["height"])

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
                                self.logger.warning(f"도크 features 복원 실패: {e}")

                        # 도크 영역 복원
                        if "dock_widget_area" in dock_state:
                            area = dock_state["dock_widget_area"]
                            self.main_window.addDockWidget(area, dock)

                    except Exception as e:
                        self.logger.warning(f"도크 {dock_name} 복원 실패: {e}")

            self.logger.debug("도크 레이아웃 복원 완료")

        except Exception as e:
            self.logger.error(f"도크 레이아웃 복원 실패: {e}")

    def _restore_v1_table_states(self, table_states: dict[str, Any]):
        """v1 테이블 상태 복원"""
        try:
            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view

                # 그룹 테이블 복원
                if "group_table" in table_states and hasattr(results_view, "group_table"):
                    group_table = results_view.group_table
                    if group_table and group_table.model():
                        widths = table_states["group_table"]
                        for col, width in widths.items():
                            if col < group_table.model().columnCount():
                                group_table.setColumnWidth(col, width)

                # 상세 테이블 복원
                if "detail_table" in table_states and hasattr(results_view, "detail_table"):
                    detail_table = results_view.detail_table
                    if detail_table and detail_table.model():
                        widths = table_states["detail_table"]
                        for col, width in widths.items():
                            if col < detail_table.model().columnCount():
                                detail_table.setColumnWidth(col, width)

            self.logger.debug("v1 테이블 상태 복원 완료")

        except Exception as e:
            self.logger.error(f"v1 테이블 상태 복원 실패: {e}")

    def _get_current_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime

        return datetime.now().isoformat()

    def get_migration_info(self) -> dict[str, Any]:
        """마이그레이션 정보 반환"""
        return {
            "current_version": self.get_current_ui_version(),
            "migration_status": self.get_migration_status(),
            "can_migrate": self.is_migration_available(),
            "can_rollback": self.can_rollback(),
            "migration_timestamp": self.settings.value(self.migration_keys["migration_timestamp"]),
            "v2_preferences": self.settings.value(self.migration_keys["v2_layout_preferences"], {}),
        }

    def reset_migration_state(self):
        """마이그레이션 상태 초기화"""
        try:
            for key in self.migration_keys.values():
                self.settings.remove(key)

            self.settings.sync()
            self.logger.info("마이그레이션 상태 초기화 완료")

        except Exception as e:
            self.logger.error(f"마이그레이션 상태 초기화 실패: {e}")

    def validate_v2_layout(self) -> tuple[bool, list[str]]:
        """v2 레이아웃 유효성 검증"""
        errors = []

        try:
            if not hasattr(self.main_window, "results_view"):
                errors.append("ResultsView가 초기화되지 않았습니다.")
                return False, errors

            results_view = self.main_window.results_view

            # 필수 탭들 확인
            required_tabs = [
                "all_tab",
                "unmatched_tab",
                "conflict_tab",
                "duplicate_tab",
                "completed_tab",
            ]
            for tab_name in required_tabs:
                if not hasattr(results_view, tab_name):
                    errors.append(f"필수 탭 {tab_name}이 없습니다.")

            # 필수 테이블들 확인
            required_tables = [
                "all_group_table",
                "unmatched_group_table",
                "conflict_group_table",
                "duplicate_group_table",
                "completed_group_table",
            ]
            for table_name in required_tables:
                if not hasattr(results_view, table_name):
                    errors.append(f"필수 테이블 {table_name}이 없습니다.")

            # 필터 관리자 확인
            if not hasattr(results_view, "filter_manager"):
                errors.append("필터 관리자가 초기화되지 않았습니다.")

            return len(errors) == 0, errors

        except Exception as e:
            errors.append(f"v2 레이아웃 검증 중 오류 발생: {e}")
            return False, errors
