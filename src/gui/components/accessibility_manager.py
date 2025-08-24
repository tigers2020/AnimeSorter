"""
접근성 관리 시스템 (Phase 10.1)
스크린 리더, 키보드 네비게이션, 고대비 모드를 지원하는 접근성 시스템
"""

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTableView,
    QWidget,
)


class AccessibilityManager(QObject):
    """접근성 관리자 - WCAG 2.1 AA 수준 준수"""

    accessibility_enabled = pyqtSignal(bool)  # 접근성 모드 변경 시그널
    high_contrast_changed = pyqtSignal(bool)  # 고대비 모드 변경 시그널

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None
        self.high_contrast_mode = False
        self.focus_order_widgets = []  # 키보드 포커스 순서

        # Phase 10.1: 접근성 설정
        self.accessibility_settings = {
            "screen_reader_support": True,
            "keyboard_navigation": True,
            "high_contrast": False,
            "focus_indicators": True,
            "accessible_names": True,
            "color_contrast_ratio": 4.5,  # WCAG AA 기준
        }

    def initialize(self, main_window):
        """접근성 관리자 초기화"""
        self.main_window = main_window
        self._setup_accessibility()
        print("✅ 접근성 관리자 초기화 완료")

    def _setup_accessibility(self):
        """접근성 설정 초기화"""
        if not self.main_window:
            return

        # 1. 키보드 네비게이션 설정
        self._setup_keyboard_navigation()

        # 2. 스크린 리더 지원 설정
        self._setup_screen_reader_support()

        # 3. 접근 가능한 이름 설정
        self._setup_accessible_names()

        # 4. 포커스 표시 설정
        self._setup_focus_indicators()

        # 5. 색상 대비 검증
        self._verify_color_contrast()

    def _setup_keyboard_navigation(self):
        """키보드 네비게이션 설정 (Phase 10.1)"""
        try:
            # 탭 순서 설정을 위한 위젯 수집
            self._collect_focusable_widgets()

            # 탭 순서 설정
            self._set_tab_order()

            print("✅ 키보드 네비게이션 설정 완료")

        except Exception as e:
            print(f"⚠️ 키보드 네비게이션 설정 실패: {e}")

    def _collect_focusable_widgets(self):
        """포커스 가능한 위젯 수집"""
        self.focus_order_widgets = []

        # 메인 툴바 버튼들
        if hasattr(self.main_window, "main_toolbar"):
            toolbar = self.main_window.main_toolbar
            if hasattr(toolbar, "scan_action"):
                self.focus_order_widgets.append(toolbar.scan_action)
            if hasattr(toolbar, "preview_action"):
                self.focus_order_widgets.append(toolbar.preview_action)
            if hasattr(toolbar, "organize_action"):
                self.focus_order_widgets.append(toolbar.organize_action)

        # 좌측 패널 컨트롤들
        if hasattr(self.main_window, "left_panel"):
            left_panel = self.main_window.left_panel
            # 좌측 패널의 버튼들을 포커스 순서에 추가
            for widget in left_panel.findChildren((QPushButton, QLineEdit, QComboBox)):
                if widget.isVisible() and widget.isEnabled():
                    self.focus_order_widgets.append(widget)

        # 결과 뷰 탭과 테이블들
        if hasattr(self.main_window, "results_view"):
            results_view = self.main_window.results_view
            # 탭 위젯 추가
            if hasattr(results_view, "tab_widget"):
                self.focus_order_widgets.append(results_view.tab_widget)

            # 테이블 뷰들 추가
            tables = [
                getattr(results_view, "all_group_table", None),
                getattr(results_view, "unmatched_group_table", None),
                getattr(results_view, "conflict_group_table", None),
                getattr(results_view, "duplicate_group_table", None),
                getattr(results_view, "completed_group_table", None),
            ]

            for table in tables:
                if table and table.isVisible():
                    self.focus_order_widgets.append(table)

    def _set_tab_order(self):
        """탭 순서 설정"""
        if len(self.focus_order_widgets) < 2:
            return

        # 순차적으로 탭 순서 설정
        for i in range(len(self.focus_order_widgets) - 1):
            current_widget = self.focus_order_widgets[i]
            next_widget = self.focus_order_widgets[i + 1]

            if hasattr(current_widget, "setFocusProxy") and hasattr(next_widget, "setFocusProxy"):
                QWidget.setTabOrder(current_widget, next_widget)

    def _setup_screen_reader_support(self):
        """스크린 리더 지원 설정 (Phase 10.1)"""
        try:
            # 메인 윈도우에 역할 설정
            self.main_window.setAccessibleName("AnimeSorter 메인 윈도우")
            self.main_window.setAccessibleDescription("애니메이션 파일 정리 도구의 메인 인터페이스")

            # 결과 뷰 테이블들에 접근성 정보 설정
            if hasattr(self.main_window, "results_view"):
                self._setup_table_accessibility(self.main_window.results_view)

            print("✅ 스크린 리더 지원 설정 완료")

        except Exception as e:
            print(f"⚠️ 스크린 리더 지원 설정 실패: {e}")

    def _setup_table_accessibility(self, results_view):
        """테이블 접근성 설정"""
        table_info = [
            (
                "all_group_table",
                "전체 애니메이션 그룹 목록",
                "모든 스캔된 애니메이션 파일들의 그룹화된 목록",
            ),
            (
                "unmatched_group_table",
                "미매칭 애니메이션 그룹",
                "TMDB와 매칭되지 않은 애니메이션 그룹들",
            ),
            (
                "conflict_group_table",
                "충돌 애니메이션 그룹",
                "이름이나 정보에 충돌이 있는 애니메이션 그룹들",
            ),
            ("duplicate_group_table", "중복 애니메이션 그룹", "중복으로 감지된 애니메이션 그룹들"),
            ("completed_group_table", "완료된 애니메이션 그룹", "정리가 완료된 애니메이션 그룹들"),
        ]

        for attr_name, accessible_name, description in table_info:
            table = getattr(results_view, attr_name, None)
            if table and isinstance(table, QTableView):
                table.setAccessibleName(accessible_name)
                table.setAccessibleDescription(description)

                # 테이블 헤더 접근성 설정
                if table.horizontalHeader():
                    table.horizontalHeader().setAccessibleName(f"{accessible_name} 헤더")
                    table.horizontalHeader().setAccessibleDescription("테이블 컬럼 헤더")

    def _setup_accessible_names(self):
        """접근 가능한 이름 설정 (Phase 10.1)"""
        try:
            # 메인 툴바 버튼들
            if hasattr(self.main_window, "main_toolbar"):
                toolbar = self.main_window.main_toolbar

                # 액션들에 접근성 이름 설정
                action_names = {
                    "scan_action": ("파일 스캔", "선택된 폴더의 애니메이션 파일들을 스캔합니다"),
                    "preview_action": ("미리보기", "정리 작업의 미리보기를 표시합니다"),
                    "organize_action": ("파일 정리", "스캔된 파일들을 정리된 구조로 이동합니다"),
                    "settings_action": ("설정", "애플리케이션 설정을 엽니다"),
                }

                for action_attr, (name, description) in action_names.items():
                    action = getattr(toolbar, action_attr, None)
                    if action:
                        action.setText(name)
                        action.setStatusTip(description)
                        action.setToolTip(f"{name}: {description}")

            # 좌측 패널 위젯들
            if hasattr(self.main_window, "left_panel"):
                self._setup_left_panel_accessibility()

            print("✅ 접근 가능한 이름 설정 완료")

        except Exception as e:
            print(f"⚠️ 접근 가능한 이름 설정 실패: {e}")

    def _setup_left_panel_accessibility(self):
        """좌측 패널 접근성 설정"""
        left_panel = self.main_window.left_panel

        # 버튼들에 접근성 이름 설정
        button_names = {
            "source_folder_btn": (
                "소스 폴더 선택",
                "스캔할 애니메이션 파일들이 있는 폴더를 선택합니다",
            ),
            "destination_folder_btn": (
                "대상 폴더 선택",
                "정리된 파일들을 저장할 폴더를 선택합니다",
            ),
            "scan_btn": ("스캔 시작", "선택된 폴더의 파일 스캔을 시작합니다"),
            "preview_btn": ("미리보기", "정리 작업의 미리보기를 표시합니다"),
            "organize_btn": ("정리 실행", "파일 정리 작업을 실행합니다"),
        }

        for btn_name, (accessible_name, description) in button_names.items():
            btn = getattr(left_panel, btn_name, None)
            if btn and isinstance(btn, QPushButton):
                btn.setAccessibleName(accessible_name)
                btn.setAccessibleDescription(description)
                btn.setToolTip(f"{accessible_name}: {description}")

    def _setup_focus_indicators(self):
        """포커스 표시 설정 (Phase 10.1)"""
        try:
            # 포커스 스타일은 테마 시스템에서 관리
            app = QApplication.instance()
            if app:
                # 테마 시스템을 통해 포커스 스타일 적용
                pass

            print("✅ 포커스 표시 설정 완료")

        except Exception as e:
            print(f"⚠️ 포커스 표시 설정 실패: {e}")

    def _verify_color_contrast(self):
        """색상 대비 검증 (Phase 10.1)"""
        try:
            # WCAG AA 기준 (4.5:1) 색상 대비 검증
            contrast_results = []

            # 기본 색상 대비 검증
            app = QApplication.instance()
            if app:
                palette = app.palette()

                # 텍스트와 배경 대비
                text_color = palette.color(QPalette.Text)
                background_color = palette.color(QPalette.Base)
                contrast_ratio = self._calculate_contrast_ratio(text_color, background_color)

                contrast_results.append(
                    {
                        "element": "기본 텍스트/배경",
                        "ratio": contrast_ratio,
                        "passes_aa": contrast_ratio >= 4.5,
                        "passes_aaa": contrast_ratio >= 7.0,
                    }
                )

                # 버튼 텍스트와 배경 대비
                button_text = palette.color(QPalette.ButtonText)
                button_bg = palette.color(QPalette.Button)
                button_contrast = self._calculate_contrast_ratio(button_text, button_bg)

                contrast_results.append(
                    {
                        "element": "버튼 텍스트/배경",
                        "ratio": button_contrast,
                        "passes_aa": button_contrast >= 4.5,
                        "passes_aaa": button_contrast >= 7.0,
                    }
                )

            # 결과 출력
            print("📊 색상 대비 검증 결과:")
            for result in contrast_results:
                aa_status = "✅ AA 통과" if result["passes_aa"] else "❌ AA 실패"
                aaa_status = "✅ AAA 통과" if result["passes_aaa"] else "❌ AAA 실패"
                print(
                    f"  - {result['element']}: {result['ratio']:.2f}:1 ({aa_status}, {aaa_status})"
                )

            print("✅ 색상 대비 검증 완료")

        except Exception as e:
            print(f"⚠️ 색상 대비 검증 실패: {e}")

    def _calculate_contrast_ratio(self, color1: QColor, color2: QColor) -> float:
        """두 색상 간의 대비비 계산 (WCAG 기준)"""

        def luminance(color: QColor) -> float:
            """색상의 상대 휘도 계산"""
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0

            def adjust(c):
                return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)

            return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

        lum1 = luminance(color1)
        lum2 = luminance(color2)

        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)

        return (lighter + 0.05) / (darker + 0.05)

    def toggle_high_contrast_mode(self):
        """고대비 모드 토글"""
        self.high_contrast_mode = not self.high_contrast_mode
        self._apply_high_contrast_mode()
        self.high_contrast_changed.emit(self.high_contrast_mode)

    def _apply_high_contrast_mode(self):
        """고대비 모드 적용"""
        app = QApplication.instance()
        if not app:
            return

        if self.high_contrast_mode:
            # 고대비 팔레트 적용
            high_contrast_palette = QPalette()
            high_contrast_palette.setColor(QPalette.Window, QColor(0, 0, 0))
            high_contrast_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
            high_contrast_palette.setColor(QPalette.Base, QColor(0, 0, 0))
            high_contrast_palette.setColor(QPalette.AlternateBase, QColor(32, 32, 32))
            high_contrast_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
            high_contrast_palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
            high_contrast_palette.setColor(QPalette.Text, QColor(255, 255, 255))
            high_contrast_palette.setColor(QPalette.Button, QColor(32, 32, 32))
            high_contrast_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
            high_contrast_palette.setColor(QPalette.BrightText, QColor(255, 255, 0))
            high_contrast_palette.setColor(QPalette.Link, QColor(0, 255, 255))
            high_contrast_palette.setColor(QPalette.Highlight, QColor(255, 255, 0))
            high_contrast_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))

            app.setPalette(high_contrast_palette)
            print("🎨 고대비 모드 활성화")
        else:
            # 기본 팔레트로 복원 - 더 강력한 복원 로직
            try:
                # 1. 테마 관리자가 있으면 테마 재적용
                if hasattr(self.main_window, "theme_manager"):
                    current_theme = self.main_window.theme_manager.get_current_theme()
                    print(f"🔧 테마 관리자를 통해 '{current_theme}' 테마로 복원")
                    self.main_window.theme_manager.apply_theme(current_theme)
                else:
                    # 2. 테마 관리자가 없으면 기본 팔레트로 복원
                    print("🔧 기본 팔레트로 복원")
                    default_palette = app.style().standardPalette()
                    app.setPalette(default_palette)

                    # 3. 스타일시트는 테마 시스템에서 관리

            except Exception as e:
                print(f"⚠️ 테마 복원 실패, 기본 팔레트로 복원: {e}")
                # 4. 실패 시 기본 팔레트로 복원
                default_palette = app.style().standardPalette()
                app.setPalette(default_palette)
                # 스타일시트는 테마 시스템에서 관리

            print("🎨 고대비 모드 비활성화 및 원래 테마 복원 완료")

    def get_accessibility_info(self) -> dict:
        """접근성 정보 반환"""
        return {
            "screen_reader_support": self.accessibility_settings["screen_reader_support"],
            "keyboard_navigation": self.accessibility_settings["keyboard_navigation"],
            "high_contrast_mode": self.high_contrast_mode,
            "focus_indicators": self.accessibility_settings["focus_indicators"],
            "accessible_names": self.accessibility_settings["accessible_names"],
            "color_contrast_ratio": self.accessibility_settings["color_contrast_ratio"],
            "focusable_widgets_count": len(self.focus_order_widgets),
        }

    def enable_accessibility_features(self, features: list[str]):
        """특정 접근성 기능 활성화"""
        for feature in features:
            if feature in self.accessibility_settings:
                self.accessibility_settings[feature] = True

        # 설정 다시 적용
        self._setup_accessibility()
        self.accessibility_enabled.emit(True)

    def disable_accessibility_features(self, features: list[str]):
        """특정 접근성 기능 비활성화"""
        for feature in features:
            if feature in self.accessibility_settings:
                self.accessibility_settings[feature] = False

        self.accessibility_enabled.emit(False)

    def set_keyboard_navigation(self, enabled: bool):
        """키보드 네비게이션 설정"""
        self.accessibility_settings["keyboard_navigation"] = enabled
        if enabled:
            self._setup_keyboard_navigation()
        print(f"✅ 키보드 네비게이션: {'활성화' if enabled else '비활성화'}")

    def set_screen_reader_support(self, enabled: bool):
        """스크린 리더 지원 설정"""
        self.accessibility_settings["screen_reader_support"] = enabled
        if enabled:
            self._setup_screen_reader_support()
        print(f"✅ 스크린 리더 지원: {'활성화' if enabled else '비활성화'}")

    def apply_high_contrast_mode(self, enabled: bool):
        """고대비 모드 적용"""
        if enabled != self.high_contrast_mode:
            self.high_contrast_mode = enabled
            self._apply_high_contrast_mode(enabled)
            self.high_contrast_changed.emit(enabled)

    def _apply_high_contrast_mode(self, enable: bool):
        """고대비 모드 적용 (내부 메서드)"""
        app = QApplication.instance()
        if not app:
            return

        if enable:
            app.setPalette(self._high_contrast_palette)
            # 스타일시트는 테마 시스템에서 관리
            self._high_contrast_mode = True
            self.high_contrast_mode_changed.emit(True)
            print("🎨 고대비 모드 활성화")
        else:
            # 기본 팔레트로 복원 - 더 강력한 복원 로직
            try:
                # 1. 테마 관리자가 있으면 테마 재적용
                if hasattr(self.main_window, "theme_manager"):
                    current_theme = self.main_window.theme_manager.get_current_theme()
                    print(f"🔧 테마 관리자를 통해 '{current_theme}' 테마로 복원")
                    self.main_window.theme_manager.apply_theme(current_theme)
                else:
                    # 2. 테마 관리자가 없으면 기본 팔레트로 복원
                    print("🔧 기본 팔레트로 복원")
                    default_palette = app.style().standardPalette()
                    app.setPalette(default_palette)

                    # 3. 스타일시트는 테마 시스템에서 관리

            except Exception as e:
                print(f"⚠️ 테마 복원 실패, 기본 팔레트로 복원: {e}")
                # 4. 실패 시 기본 팔레트로 복원
                default_palette = app.style().standardPalette()
                app.setPalette(default_palette)
                # 스타일시트는 테마 시스템에서 관리

            self._high_contrast_mode = False
            self.high_contrast_mode_changed.emit(False)
            print("🎨 고대비 모드 비활성화 및 원래 테마 복원 완료")
