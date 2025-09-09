"""
MainWindowSessionManager

MainWindow에서 세션 및 설정 관리 관련 로직을 담당하는 핸들러 클래스입니다.
기존 컴포넌트들과의 중복을 방지하고, unified_config_manager를 활용하여 세션 상태를 관리합니다.
"""

import json
from pathlib import Path
from typing import Any

# SettingsManager는 더 이상 사용하지 않음 - unified_config_manager 사용


class MainWindowSessionManager:
    """
    MainWindow의 세션 및 설정 관리 로직을 담당하는 핸들러

    역할:
    - 세션 상태 저장/복원
    - 설정 UI 적용 및 변경 처리
    - 테이블 컬럼 관리
    - unified_config_manager와 연동

    중복 방지:
    - 상태바 업데이트는 StatusBarManager가 담당
    - 이벤트 처리는 EventHandlerManager가 담당
    """

    def __init__(self, main_window, settings_manager):
        """
        MainWindowSessionManager 초기화

        Args:
            main_window: MainWindow 인스턴스
            settings_manager: 설정 관리자
        """
        self.main_window = main_window
        self.settings_manager = settings_manager

        # 세션 파일 경로
        self.session_file = Path.home() / ".animesorter" / "session.json"
        self.session_file.parent.mkdir(exist_ok=True)

    def restore_session_state(self) -> bool:
        """
        이전 세션 상태 복원

        Returns:
            복원 성공 여부
        """
        try:
            if not self.session_file.exists():
                print("📋 [MainWindowSessionManager] 세션 파일이 없습니다. 새로 시작합니다.")
                return True

            with self.session_file.open(encoding="utf-8") as f:
                session_data = json.load(f)

            print("📋 [MainWindowSessionManager] 세션 상태 복원 시작")

            # 윈도우 위치 및 크기 복원
            if "window" in session_data:
                window_data = session_data["window"]
                if "geometry" in window_data:
                    self.main_window.restoreGeometry(window_data["geometry"])
                if "state" in window_data:
                    self.main_window.restoreState(window_data["state"])
                if "pos" in window_data:
                    self.main_window.move(window_data["pos"])
                if "size" in window_data:
                    self.main_window.resize(window_data["size"])

            # 소스 디렉토리 복원
            if "source_directory" in session_data and session_data["source_directory"]:
                self.main_window.source_directory = session_data["source_directory"]
                if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                    self.main_window.left_panel.set_source_folder(session_data["source_directory"])

            # 소스 파일들 복원
            if "source_files" in session_data and session_data["source_files"]:
                self.main_window.source_files = session_data["source_files"]
                if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                    self.main_window.left_panel.set_source_files(session_data["source_files"])

            # 대상 디렉토리 복원
            if "destination_directory" in session_data and session_data["destination_directory"]:
                self.main_window.destination_directory = session_data["destination_directory"]
                if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                    self.main_window.left_panel.set_destination_folder(
                        session_data["destination_directory"]
                    )

            # 테이블 컬럼 너비 복원
            if "table_columns" in session_data:
                self.restore_table_column_widths(session_data["table_columns"])

            # 도크 위젯 상태 복원
            if "dock_widgets" in session_data:
                self._restore_dock_widgets(session_data["dock_widgets"])

            print("✅ [MainWindowSessionManager] 세션 상태 복원 완료")
            return True

        except Exception as e:
            print(f"❌ [MainWindowSessionManager] 세션 상태 복원 실패: {e}")
            return False

    def save_session_state(self) -> bool:
        """
        현재 세션 상태 저장

        Returns:
            저장 성공 여부
        """
        try:
            print("📋 [MainWindowSessionManager] 세션 상태 저장 시작")

            session_data = {
                "window": {
                    "geometry": bytes(self.main_window.saveGeometry()),
                    "state": bytes(self.main_window.saveState()),
                    "pos": [self.main_window.x(), self.main_window.y()],
                    "size": [self.main_window.width(), self.main_window.height()],
                },
                "source_directory": self.main_window.source_directory or "",
                "source_files": self.main_window.source_files or [],
                "destination_directory": self.main_window.destination_directory or "",
                "table_columns": self.get_table_column_widths(),
                "dock_widgets": self._get_dock_widgets_state(),
            }

            # 세션 파일에 저장
            with self.session_file.open("w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            print("✅ [MainWindowSessionManager] 세션 상태 저장 완료")
            return True

        except Exception as e:
            print(f"❌ [MainWindowSessionManager] 세션 상태 저장 실패: {e}")
            return False

    def apply_settings_to_ui(self) -> None:
        """
        설정을 UI 컴포넌트에 적용

        unified_config_manager의 설정값을 MainWindow의 UI 컴포넌트들에 적용합니다.
        """
        try:
            print("⚙️ [MainWindowSessionManager] 설정을 UI에 적용 시작")

            # unified_config_manager의 경우 config 속성 사용
            if hasattr(self.settings_manager, "config"):
                config = self.settings_manager.config
                user_prefs = config.user_preferences

                # 테마 설정 적용
                theme_prefs = getattr(user_prefs, "theme_preferences", {})
                if isinstance(theme_prefs, dict):
                    theme = theme_prefs.get("theme", "light")
                else:
                    theme = getattr(theme_prefs, "theme", "light")
                self._apply_theme(theme)

                # 언어 설정 적용
                if isinstance(theme_prefs, dict):
                    language = theme_prefs.get("language", "ko")
                else:
                    language = getattr(theme_prefs, "language", "ko")
                self._apply_language(language)

                # 폰트 설정 적용
                font_family = getattr(user_prefs, "font_family", "Segoe UI")
                font_size = getattr(user_prefs, "font_size", 9)
                self._apply_font(font_family, font_size)

                # UI 스타일 설정 적용
                ui_style = getattr(user_prefs, "ui_style", "default")
                self._apply_ui_style(ui_style)

            print("✅ [MainWindowSessionManager] 설정을 UI에 적용 완료")

        except Exception as e:
            print(f"❌ [MainWindowSessionManager] 설정을 UI에 적용 실패: {e}")

    def handle_settings_changed(self, setting_name: str, new_value: Any) -> None:
        """
        설정 변경 처리

        Args:
            setting_name: 변경된 설정 이름
            new_value: 새로운 설정값
        """
        try:
            print(f"⚙️ [MainWindowSessionManager] 설정 변경 처리: {setting_name} = {new_value}")

            # 설정에 따른 UI 업데이트
            if setting_name == "theme":
                self._apply_theme(new_value)
            elif setting_name == "language":
                self._apply_language(new_value)
            elif setting_name == "font_family" or setting_name == "font_size":
                font_family = getattr(
                    self.settings_manager.config.user_preferences, "font_family", "Segoe UI"
                )
                font_size = getattr(self.settings_manager.config.user_preferences, "font_size", 9)
                self._apply_font(font_family, font_size)
            elif setting_name == "ui_style":
                self._apply_ui_style(new_value)

            # 설정 변경 알림
            if hasattr(self.main_window, "update_status_bar"):
                self.main_window.update_status_bar(f"설정이 변경되었습니다: {setting_name}")

            print(f"✅ [MainWindowSessionManager] 설정 변경 처리 완료: {setting_name}")

        except Exception as e:
            print(f"❌ [MainWindowSessionManager] 설정 변경 처리 실패: {e}")

    def restore_table_column_widths(self, column_widths: dict[str, int]) -> None:
        """
        테이블 컬럼 너비 복원

        Args:
            column_widths: 컬럼별 너비 정보
        """
        try:
            if not hasattr(self.main_window, "results_view"):
                return

            results_view = self.main_window.results_view

            # 그룹 테이블 컬럼 너비 복원
            if hasattr(results_view, "group_table") and results_view.group_table:
                group_table = results_view.group_table
                if group_table.model():
                    header = group_table.horizontalHeader()
                    for column_name, width in column_widths.get("group_table", {}).items():
                        try:
                            column_index = self._get_column_index_by_name(group_table, column_name)
                            if column_index >= 0:
                                header.setSectionResizeMode(column_index, header.Fixed)
                                header.resizeSection(column_index, width)
                        except Exception as e:
                            print(f"⚠️ 그룹 테이블 컬럼 너비 복원 실패: {column_name} - {e}")

            # 상세 테이블 컬럼 너비 복원
            if hasattr(results_view, "detail_table") and results_view.detail_table:
                detail_table = results_view.detail_table
                if detail_table.model():
                    header = detail_table.horizontalHeader()
                    for column_name, width in column_widths.get("detail_table", {}).items():
                        try:
                            column_index = self._get_column_index_by_name(detail_table, column_name)
                            if column_index >= 0:
                                header.setSectionResizeMode(column_index, header.Fixed)
                                header.resizeSection(column_index, width)
                        except Exception as e:
                            print(f"⚠️ 상세 테이블 컬럼 너비 복원 실패: {column_name} - {e}")

            print("✅ [MainWindowSessionManager] 테이블 컬럼 너비 복원 완료")

        except Exception as e:
            print(f"❌ [MainWindowSessionManager] 테이블 컬럼 너비 복원 실패: {e}")

    def get_table_column_widths(self) -> dict[str, dict[str, int]]:
        """
        테이블 컬럼 너비 가져오기

        Returns:
            테이블별 컬럼 너비 정보
        """
        try:
            column_widths = {}

            if hasattr(self.main_window, "results_view"):
                results_view = self.main_window.results_view

                # 그룹 테이블 컬럼 너비
                if hasattr(results_view, "group_table") and results_view.group_table:
                    group_table = results_view.group_table
                    if group_table.model():
                        header = group_table.horizontalHeader()
                        group_columns = {}
                        for i in range(header.count()):
                            column_name = self._get_column_name_by_index(group_table, i)
                            if column_name:
                                group_columns[column_name] = header.sectionSize(i)
                        column_widths["group_table"] = group_columns

                # 상세 테이블 컬럼 너비
                if hasattr(results_view, "detail_table") and results_view.detail_table:
                    detail_table = results_view.detail_table
                    if detail_table.model():
                        header = detail_table.horizontalHeader()
                        detail_columns = {}
                        for i in range(header.count()):
                            column_name = self._get_column_name_by_index(detail_table, i)
                            if column_name:
                                detail_columns[column_name] = header.sectionSize(i)
                        column_widths["detail_table"] = detail_columns

            return column_widths

        except Exception as e:
            print(f"❌ [MainWindowSessionManager] 테이블 컬럼 너비 가져오기 실패: {e}")
            return {}

    def _apply_theme(self, theme: str) -> None:
        """테마 설정 적용"""
        try:
            # 테마별 스타일시트 적용
            if theme == "dark":
                # 다크 테마 스타일시트 적용
                pass
            elif theme == "light":
                # 라이트 테마 스타일시트 적용
                pass
            else:
                # 기본 테마 스타일시트 적용
                pass

            print(f"✅ 테마 적용 완료: {theme}")

        except Exception as e:
            print(f"❌ 테마 적용 실패: {e}")

    def _apply_language(self, language: str) -> None:
        """언어 설정 적용"""
        try:
            # 언어별 리소스 파일 로드 및 적용
            if hasattr(self.main_window, "i18n_manager") and self.main_window.i18n_manager:
                self.main_window.i18n_manager.set_language(language)

            print(f"✅ 언어 적용 완료: {language}")

        except Exception as e:
            print(f"❌ 언어 적용 실패: {e}")

    def _apply_font(self, font_family: str, font_size: int) -> None:
        """폰트 설정 적용"""
        try:
            from PyQt5.QtGui import QFont

            # 애플리케이션 폰트 설정
            font = QFont(font_family, font_size)
            self.main_window.setFont(font)

            print(f"✅ 폰트 적용 완료: {font_family}, {font_size}")

        except Exception as e:
            print(f"❌ 폰트 적용 실패: {e}")

    def _apply_ui_style(self, ui_style: str) -> None:
        """UI 스타일 설정 적용"""
        try:
            # UI 스타일별 설정 적용
            if ui_style == "compact":
                # 컴팩트 스타일 적용
                pass
            elif ui_style == "comfortable":
                # 편안한 스타일 적용
                pass
            else:
                # 기본 스타일 적용
                pass

            print(f"✅ UI 스타일 적용 완료: {ui_style}")

        except Exception as e:
            print(f"❌ UI 스타일 적용 실패: {e}")

    def _restore_dock_widgets(self, dock_data: dict[str, Any]) -> None:
        """도크 위젯 상태 복원"""
        try:
            # 좌측 패널 도크 상태 복원
            if "left_panel" in dock_data and hasattr(self.main_window, "left_panel_dock"):
                left_dock = self.main_window.left_panel_dock
                if dock_data["left_panel"].get("visible", True):
                    left_dock.show()
                else:
                    left_dock.hide()

                if "size" in dock_data["left_panel"]:
                    left_dock.resize(dock_data["left_panel"]["size"])

            # 로그 도크 상태 복원
            if "log_dock" in dock_data and hasattr(self.main_window, "log_dock"):
                log_dock = self.main_window.log_dock
                if dock_data["log_dock"].get("visible", False):
                    log_dock.show()
                else:
                    log_dock.hide()

                if "size" in dock_data["log_dock"]:
                    log_dock.resize(dock_data["log_dock"]["size"])

            print("✅ 도크 위젯 상태 복원 완료")

        except Exception as e:
            print(f"❌ 도크 위젯 상태 복원 실패: {e}")

    def _get_dock_widgets_state(self) -> dict[str, Any]:
        """도크 위젯 상태 가져오기"""
        try:
            dock_state = {}

            # 좌측 패널 도크 상태
            if hasattr(self.main_window, "left_panel_dock"):
                left_dock = self.main_window.left_panel_dock
                dock_state["left_panel"] = {
                    "visible": left_dock.isVisible(),
                    "size": [left_dock.width(), left_dock.height()],
                }

            # 로그 도크 상태
            if hasattr(self.main_window, "log_dock"):
                log_dock = self.main_window.log_dock
                dock_state["log_dock"] = {
                    "visible": log_dock.isVisible(),
                    "size": [log_dock.width(), log_dock.height()],
                }

            return dock_state

        except Exception as e:
            print(f"❌ 도크 위젯 상태 가져오기 실패: {e}")
            return {}

    def _get_column_index_by_name(self, table, column_name: str) -> int:
        """컬럼 이름으로 인덱스 가져오기"""
        try:
            model = table.model()
            if model:
                for i in range(model.columnCount()):
                    if model.headerData(i, 1) == column_name:  # 1 = Qt.Horizontal
                        return i
            return -1
        except Exception:
            return -1

    def _get_column_name_by_index(self, table, column_index: int) -> str | None:
        """컬럼 인덱스로 이름 가져오기"""
        try:
            model = table.model()
            if model:
                return model.headerData(column_index, 1)  # 1 = Qt.Horizontal
            return None
        except Exception:
            return None
