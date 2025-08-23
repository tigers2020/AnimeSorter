"""
메뉴 및 툴바 관리 로직을 담당하는 클래스
MainWindow의 메뉴 및 툴바 생성, 설정, 관리 로직을 분리하여 가독성과 유지보수성을 향상시킵니다.
"""

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction, QMainWindow, QMenu, QMenuBar, QToolBar


class MenuToolbarManager:
    """메뉴 및 툴바 관리를 담당하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.menu_bar: Optional[QMenuBar] = None
        self.main_toolbar: Optional[QToolBar] = None

        # 메뉴 액션들
        self.file_menu: Optional[QMenu] = None
        self.edit_menu: Optional[QMenu] = None
        self.view_menu: Optional[QMenu] = None
        self.tools_menu: Optional[QMenu] = None
        self.help_menu: Optional[QMenu] = None

        # 툴바 액션들
        self.scan_action: Optional[QAction] = None
        self.preview_action: Optional[QAction] = None
        self.organize_action: Optional[QAction] = None
        self.settings_action: Optional[QAction] = None
        self.help_action: Optional[QAction] = None

    def setup_all_menus_and_toolbars(self):
        """모든 메뉴와 툴바를 설정하고 연결"""
        try:
            print("🔧 메뉴 및 툴바 설정 시작...")

            # 1. 메뉴바 생성
            self._setup_menu_bar()

            # 2. 메인 툴바 생성
            self._setup_main_toolbar()

            # 3. 액션 연결
            self._connect_actions()

            print("✅ 메뉴 및 툴바 설정 완료!")

        except Exception as e:
            print(f"❌ 메뉴 및 툴바 설정 실패: {e}")
            import traceback

            traceback.print_exc()

    def _setup_menu_bar(self):
        """메뉴바 생성 및 설정"""
        try:
            # 메뉴바 생성
            self.menu_bar = self.main_window.menuBar()

            # 파일 메뉴
            self._create_file_menu()

            # 편집 메뉴
            self._create_edit_menu()

            # 보기 메뉴
            self._create_view_menu()

            # 도구 메뉴
            self._create_tools_menu()

            # 도움말 메뉴
            self._create_help_menu()

            print("✅ 메뉴바 설정 완료")

        except Exception as e:
            print(f"❌ 메뉴바 설정 실패: {e}")

    def _create_file_menu(self):
        """파일 메뉴 생성"""
        try:
            self.file_menu = self.menu_bar.addMenu("파일(&F)")

            # 파일 선택 액션
            choose_files_action = QAction("파일 선택(&O)", self.main_window)
            choose_files_action.setShortcut(QKeySequence.Open)
            choose_files_action.setStatusTip("애니메이션 파일들을 선택합니다")
            choose_files_action.triggered.connect(self.main_window.choose_files)
            self.file_menu.addAction(choose_files_action)

            # 폴더 선택 액션
            choose_folder_action = QAction("폴더 선택(&F)", self.main_window)
            choose_folder_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
            choose_folder_action.setStatusTip("애니메이션 파일이 있는 폴더를 선택합니다")
            choose_folder_action.triggered.connect(self.main_window.choose_folder)
            self.file_menu.addAction(choose_folder_action)

            self.file_menu.addSeparator()

            # 결과 내보내기 액션
            export_action = QAction("결과 내보내기(&E)", self.main_window)
            export_action.setShortcut(QKeySequence("Ctrl+E"))
            export_action.setStatusTip("스캔 결과를 CSV 파일로 내보냅니다")
            export_action.triggered.connect(self.main_window.export_results)
            self.file_menu.addAction(export_action)

            self.file_menu.addSeparator()

            # 종료 액션
            exit_action = QAction("종료(&X)", self.main_window)
            exit_action.setShortcut(QKeySequence.Quit)
            exit_action.setStatusTip("애플리케이션을 종료합니다")
            exit_action.triggered.connect(self.main_window.close)
            self.file_menu.addAction(exit_action)

        except Exception as e:
            print(f"❌ 파일 메뉴 생성 실패: {e}")

    def _create_edit_menu(self):
        """편집 메뉴 생성"""
        try:
            self.edit_menu = self.menu_bar.addMenu("편집(&E)")

            # 완료된 항목 정리 액션
            clear_completed_action = QAction("완료된 항목 정리(&C)", self.main_window)
            clear_completed_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
            clear_completed_action.setStatusTip("완료된 항목들을 목록에서 제거합니다")
            clear_completed_action.triggered.connect(self.main_window.clear_completed)
            self.edit_menu.addAction(clear_completed_action)

            # 필터 초기화 액션
            reset_filters_action = QAction("필터 초기화(&R)", self.main_window)
            reset_filters_action.setShortcut(QKeySequence("Ctrl+R"))
            reset_filters_action.setStatusTip("적용된 모든 필터를 초기화합니다")
            reset_filters_action.triggered.connect(self.main_window.reset_filters)
            self.edit_menu.addAction(reset_filters_action)

        except Exception as e:
            print(f"❌ 편집 메뉴 생성 실패: {e}")

    def _create_view_menu(self):
        """보기 메뉴 생성"""
        try:
            self.view_menu = self.menu_bar.addMenu("보기(&V)")

            # 로그 Dock 토글 액션
            toggle_log_action = QAction("로그 표시(&L)", self.main_window)
            toggle_log_action.setShortcut(QKeySequence("Ctrl+Shift+L"))
            toggle_log_action.setStatusTip("로그 Dock을 표시하거나 숨깁니다")
            toggle_log_action.triggered.connect(self.main_window.toggle_log_dock)
            self.view_menu.addAction(toggle_log_action)

            # 상태바 토글 액션
            toggle_statusbar_action = QAction("상태바 표시(&S)", self.main_window)
            toggle_statusbar_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
            toggle_statusbar_action.setStatusTip("상태바를 표시하거나 숨깁니다")
            toggle_statusbar_action.triggered.connect(self._toggle_statusbar)
            self.view_menu.addAction(toggle_statusbar_action)

        except Exception as e:
            print(f"❌ 보기 메뉴 생성 실패: {e}")

    def _create_tools_menu(self):
        """도구 메뉴 생성"""
        try:
            self.tools_menu = self.menu_bar.addMenu("도구(&T)")

            # 설정 액션
            settings_action = QAction("설정(&S)", self.main_window)
            settings_action.setShortcut(QKeySequence("Ctrl+,"))
            settings_action.setStatusTip("애플리케이션 설정을 엽니다")
            settings_action.triggered.connect(self.main_window.show_settings_dialog)
            self.tools_menu.addAction(settings_action)

            self.tools_menu.addSeparator()

            # 접근성 모드 토글 액션
            accessibility_action = QAction("접근성 모드(&A)", self.main_window)
            accessibility_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
            accessibility_action.setStatusTip("접근성 모드를 활성화하거나 비활성화합니다")
            accessibility_action.triggered.connect(self.main_window.toggle_accessibility_mode)
            self.tools_menu.addAction(accessibility_action)

            # 고대비 모드 토글 액션
            high_contrast_action = QAction("고대비 모드(&H)", self.main_window)
            high_contrast_action.setShortcut(QKeySequence("Ctrl+Shift+H"))
            high_contrast_action.setStatusTip("고대비 모드를 활성화하거나 비활성화합니다")
            high_contrast_action.triggered.connect(self.main_window.toggle_high_contrast_mode)
            self.tools_menu.addAction(high_contrast_action)

        except Exception as e:
            print(f"❌ 도구 메뉴 생성 실패: {e}")

    def _create_help_menu(self):
        """도움말 메뉴 생성"""
        try:
            self.help_menu = self.menu_bar.addMenu("도움말(&H)")

            # 사용법 액션
            help_action = QAction("사용법(&H)", self.main_window)
            help_action.setShortcut(QKeySequence.HelpContents)
            help_action.setStatusTip("AnimeSorter 사용법을 표시합니다")
            help_action.triggered.connect(self.main_window.show_help)
            self.help_menu.addAction(help_action)

            self.help_menu.addSeparator()

            # 정보 액션
            about_action = QAction("정보(&A)", self.main_window)
            about_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
            about_action.setStatusTip("AnimeSorter 정보를 표시합니다")
            about_action.triggered.connect(self.main_window.show_about)
            self.help_menu.addAction(about_action)

        except Exception as e:
            print(f"❌ 도움말 메뉴 생성 실패: {e}")

    def _setup_main_toolbar(self):
        """메인 툴바 생성 및 설정"""
        try:
            # 메인 툴바 생성
            self.main_toolbar = QToolBar("메인 툴바", self.main_window)
            self.main_toolbar.setObjectName("main_toolbar")
            self.main_window.addToolBar(self.main_toolbar)

            # 스캔 액션
            self.scan_action = QAction("🔍 스캔", self.main_window)
            self.scan_action.setStatusTip("선택된 폴더의 애니메이션 파일들을 스캔합니다")
            self.scan_action.setShortcut(QKeySequence("F5"))
            self.scan_action.triggered.connect(self.main_window.on_scan_requested)
            self.main_toolbar.addAction(self.scan_action)

            # 미리보기 액션
            self.preview_action = QAction("👁️ 미리보기", self.main_window)
            self.preview_action.setStatusTip("정리 작업의 미리보기를 표시합니다")
            self.preview_action.setShortcut(QKeySequence("F8"))
            self.preview_action.triggered.connect(self.main_window.on_preview_requested)
            self.main_toolbar.addAction(self.preview_action)

            # 정리 실행 액션
            self.organize_action = QAction("🚀 정리", self.main_window)
            self.organize_action.setStatusTip("스캔된 파일들을 정리된 구조로 이동합니다")
            self.organize_action.setShortcut(QKeySequence("F7"))
            self.organize_action.triggered.connect(self.main_window.on_organize_requested)
            self.main_toolbar.addAction(self.organize_action)

            self.main_toolbar.addSeparator()

            # 설정 액션
            self.settings_action = QAction("⚙️ 설정", self.main_window)
            self.settings_action.setStatusTip("애플리케이션 설정을 엽니다")
            self.settings_action.setShortcut(QKeySequence("Ctrl+,"))
            self.settings_action.triggered.connect(self.main_window.on_settings_requested)
            self.main_toolbar.addAction(self.settings_action)

            # 도움말 액션
            self.help_action = QAction("❓ 도움말", self.main_window)
            self.help_action.setStatusTip("AnimeSorter 사용법을 표시합니다")
            self.help_action.setShortcut(QKeySequence("F1"))
            self.help_action.triggered.connect(self.main_window.show_help)
            self.main_toolbar.addAction(self.help_action)

            # 초기 상태 설정
            self.set_organize_enabled(False)

            print("✅ 메인 툴바 설정 완료")

        except Exception as e:
            print(f"❌ 메인 툴바 설정 실패: {e}")

    def _connect_actions(self):
        """액션들을 메인 윈도우에 연결"""
        try:
            # 메인 윈도우에 툴바 액션들 저장
            self.main_window.scan_action = self.scan_action
            self.main_window.preview_action = self.preview_action
            self.main_window.organize_action = self.organize_action
            self.main_window.settings_action = self.settings_action
            self.main_window.help_action = self.help_action

            print("✅ 액션 연결 완료")

        except Exception as e:
            print(f"❌ 액션 연결 실패: {e}")

    # ==================== 툴바 상태 관리 메서드들 ====================

    def set_organize_enabled(self, enabled: bool):
        """정리 실행 버튼 활성화/비활성화 설정"""
        try:
            if self.organize_action:
                self.organize_action.setEnabled(enabled)
                if enabled:
                    self.organize_action.setStatusTip("스캔된 파일들을 정리된 구조로 이동합니다")
                else:
                    self.organize_action.setStatusTip("정리할 파일이 없습니다")
        except Exception as e:
            print(f"⚠️ 정리 실행 버튼 상태 설정 실패: {e}")

    def set_scan_enabled(self, enabled: bool):
        """스캔 버튼 활성화/비활성화 설정"""
        try:
            if self.scan_action:
                self.scan_action.setEnabled(enabled)
                if enabled:
                    self.scan_action.setStatusTip("선택된 폴더의 애니메이션 파일들을 스캔합니다")
                else:
                    self.scan_action.setStatusTip("스캔할 파일이나 폴더를 선택해주세요")
        except Exception as e:
            print(f"⚠️ 스캔 버튼 상태 설정 실패: {e}")

    def set_preview_enabled(self, enabled: bool):
        """미리보기 버튼 활성화/비활성화 설정"""
        try:
            if self.preview_action:
                self.preview_action.setEnabled(enabled)
                if enabled:
                    self.preview_action.setStatusTip("정리 작업의 미리보기를 표시합니다")
                else:
                    self.preview_action.setStatusTip("미리보기할 정리 작업이 없습니다")
        except Exception as e:
            print(f"⚠️ 미리보기 버튼 상태 설정 실패: {e}")

    def reset_filters(self):
        """필터 초기화"""
        try:
            # 여기서는 툴바의 필터 관련 상태만 초기화
            # 실제 필터 초기화는 MainWindow에서 처리
            print("🔧 툴바 필터 초기화 완료")
        except Exception as e:
            print(f"⚠️ 툴바 필터 초기화 실패: {e}")

    # ==================== 메뉴 상태 관리 메서드들 ====================

    def _toggle_statusbar(self):
        """상태바 표시/숨김 토글"""
        try:
            if hasattr(self.main_window, "statusBar"):
                status_bar = self.main_window.statusBar()
                if status_bar.isVisible():
                    status_bar.hide()
                    print("🔧 상태바 숨김")
                else:
                    status_bar.show()
                    print("🔧 상태바 표시")
        except Exception as e:
            print(f"⚠️ 상태바 토글 실패: {e}")

    def update_menu_states(self):
        """메뉴 상태 업데이트"""
        try:
            # 현재 상태에 따라 메뉴 항목들의 활성화/비활성화 설정
            has_groups = False
            if (
                hasattr(self.main_window, "anime_data_manager")
                and self.main_window.anime_data_manager is not None
                and hasattr(self.main_window.anime_data_manager, "get_grouped_items")
            ):
                try:
                    grouped_items = self.main_window.anime_data_manager.get_grouped_items()
                    has_groups = len(grouped_items) > 0 and any(
                        group_id != "ungrouped" for group_id in grouped_items
                    )
                except Exception as e:
                    print(f"⚠️ 그룹 항목 조회 실패: {e}")
                    has_groups = False

            # 파일 메뉴 상태 업데이트
            if self.file_menu:
                for action in self.file_menu.actions():
                    if "내보내기" in action.text():
                        action.setEnabled(has_groups)
                    elif "선택" in action.text():
                        action.setEnabled(True)  # 항상 활성화

            # 편집 메뉴 상태 업데이트
            if self.edit_menu:
                for action in self.edit_menu.actions():
                    if "정리" in action.text():
                        action.setEnabled(has_groups)
                    elif "필터" in action.text():
                        action.setEnabled(True)  # 항상 활성화

            # 도구 메뉴 상태 업데이트
            if self.tools_menu:
                for action in self.tools_menu.actions():
                    if "설정" in action.text():
                        action.setEnabled(True)  # 항상 활성화

            print("✅ 메뉴 상태 업데이트 완료")

        except Exception as e:
            print(f"⚠️ 메뉴 상태 업데이트 실패: {e}")

    # ==================== 단축키 관리 메서드들 ====================

    def setup_shortcuts(self):
        """단축키 설정"""
        try:
            # 기본 단축키들은 이미 액션 생성 시 설정됨
            # 추가 단축키가 필요한 경우 여기서 설정

            print("✅ 단축키 설정 완료")

        except Exception as e:
            print(f"⚠️ 단축키 설정 실패: {e}")

    def get_shortcut_summary(self) -> str:
        """단축키 요약 반환"""
        try:
            shortcuts = []

            if self.scan_action and self.scan_action.shortcut():
                shortcuts.append(f"스캔: {self.scan_action.shortcut().toString()}")

            if self.preview_action and self.preview_action.shortcut():
                shortcuts.append(f"미리보기: {self.preview_action.shortcut().toString()}")

            if self.organize_action and self.organize_action.shortcut():
                shortcuts.append(f"정리: {self.organize_action.shortcut().toString()}")

            if self.settings_action and self.settings_action.shortcut():
                shortcuts.append(f"설정: {self.settings_action.shortcut().toString()}")

            if self.help_action and self.help_action.shortcut():
                shortcuts.append(f"도움말: {self.help_action.shortcut().toString()}")

            return "\n".join(shortcuts) if shortcuts else "설정된 단축키가 없습니다."

        except Exception as e:
            print(f"⚠️ 단축키 요약 생성 실패: {e}")
            return "단축키 정보를 가져올 수 없습니다."

    # ==================== 툴바 커스터마이징 메서드들 ====================

    def set_toolbar_style(self, style: str):
        """툴바 스타일 설정"""
        try:
            if self.main_toolbar:
                if style == "icons_only":
                    self.main_toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
                elif style == "text_only":
                    self.main_toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
                elif style == "text_beside_icon":
                    self.main_toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
                elif style == "text_under_icon":
                    self.main_toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
                else:
                    self.main_toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

                print(f"✅ 툴바 스타일을 '{style}'로 설정 완료")
        except Exception as e:
            print(f"⚠️ 툴바 스타일 설정 실패: {e}")

    def set_toolbar_orientation(self, orientation: str):
        """툴바 방향 설정"""
        try:
            if self.main_toolbar:
                if orientation == "horizontal":
                    self.main_toolbar.setOrientation(Qt.Horizontal)
                elif orientation == "vertical":
                    self.main_toolbar.setOrientation(Qt.Vertical)
                else:
                    self.main_toolbar.setOrientation(Qt.Horizontal)

                print(f"✅ 툴바 방향을 '{orientation}'로 설정 완료")
        except Exception as e:
            print(f"⚠️ 툴바 방향 설정 실패: {e}")

    def toggle_toolbar_visibility(self):
        """툴바 가시성 토글"""
        try:
            if self.main_toolbar:
                if self.main_toolbar.isVisible():
                    self.main_toolbar.hide()
                    print("🔧 툴바 숨김")
                else:
                    self.main_toolbar.show()
                    print("🔧 툴바 표시")
        except Exception as e:
            print(f"⚠️ 툴바 가시성 토글 실패: {e}")

    def show_toolbar(self):
        """툴바 표시"""
        try:
            if self.main_toolbar:
                self.main_toolbar.show()
                print("🔧 툴바 표시")
        except Exception as e:
            print(f"⚠️ 툴바 표시 실패: {e}")

    def hide_toolbar(self):
        """툴바 숨김"""
        try:
            if self.main_toolbar:
                self.main_toolbar.hide()
                print("🔧 툴바 숨김")
        except Exception as e:
            print(f"⚠️ 툴바 숨김 실패: {e}")
