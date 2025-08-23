"""
좌측 패널 Dock 컴포넌트 - Phase 2 UI/UX 리팩토링
기존 LeftPanel을 QDockWidget으로 래핑하여 접힘/전개가 가능하도록 합니다.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDockWidget

from .left_panel import LeftPanel


class LeftPanelDock(QDockWidget):
    """좌측 패널을 Dock으로 만든 컴포넌트"""

    def __init__(self, parent=None):
        super().__init__("🚀 빠른 작업 & 📊 통계", parent)
        self.setObjectName("left_panel_dock")  # objectName 설정
        self.init_ui()
        self.setup_dock_properties()

    def init_ui(self):
        """UI 초기화"""
        # 기존 LeftPanel을 내부 위젯으로 사용
        self.left_panel = LeftPanel()

        # Dock 위젯의 중앙 위젯으로 설정
        self.setWidget(self.left_panel)

    def setup_dock_properties(self):
        """Dock 속성 설정"""
        # 기본 크기 설정
        self.setMinimumWidth(220)
        self.setMaximumWidth(500)
        self.resize(280, 600)  # 기본 너비 280px

        # Dock 기능 설정
        self.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable  # 이동 가능
            | QDockWidget.DockWidgetClosable  # 떠다닐 수 있음  # 닫기 가능
        )

        # 기본 위치 설정 (왼쪽)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # Dock 제목 설정
        self.setWindowTitle("🚀 빠른 작업 & 📊 통계")

        # 접힘/펼침 상태 설정
        self.setVisible(True)  # 기본적으로 보임

        # Dock 위치 변경 시 시그널 연결
        self.dockLocationChanged.connect(self.on_dock_location_changed)

    def on_dock_location_changed(self, area):
        """Dock 위치 변경 시 처리"""
        # 위치에 따른 추가 설정이 필요한 경우 여기에 구현

    # LeftPanel의 모든 시그널을 외부로 노출
    @property
    def source_folder_selected(self):
        """소스 폴더 선택 시그널"""
        return self.left_panel.source_folder_selected

    @property
    def source_files_selected(self):
        """소스 파일 선택 시그널"""
        return self.left_panel.source_files_selected

    @property
    def destination_folder_selected(self):
        """대상 폴더 선택 시그널"""
        return self.left_panel.destination_folder_selected

    @property
    def scan_started(self):
        """스캔 시작 시그널"""
        return self.left_panel.scan_started

    @property
    def scan_paused(self):
        """스캔 일시정지 시그널"""
        return self.left_panel.scan_paused

    @property
    def settings_opened(self):
        """설정 열기 시그널"""
        return self.left_panel.settings_opened

    @property
    def completed_cleared(self):
        """완료된 항목 정리 시그널"""
        return self.left_panel.completed_cleared

    # LeftPanel의 모든 메서드를 외부로 노출
    def update_scan_button_state(self, has_source: bool):
        """스캔 시작 버튼 활성화 상태 업데이트"""
        self.left_panel.update_scan_button_state(has_source)

    def update_stats(self, total: int, parsed: int, pending: int, groups: int = 0):
        """통계 업데이트"""
        self.left_panel.update_stats(total, parsed, pending, groups)

    def update_source_directory_display(self, directory: str):
        """소스 디렉토리 표시 업데이트"""
        self.left_panel.update_source_directory_display(directory)

    def update_destination_directory_display(self, directory: str):
        """대상 디렉토리 표시 업데이트"""
        self.left_panel.update_destination_directory_display(directory)

    def update_source_files_display(self, file_count: int):
        """소스 파일 수 표시 업데이트"""
        self.left_panel.update_source_files_display(file_count)

    def open_settings(self):
        """설정 열기"""
        self.left_panel.open_settings()

    def start_scan(self):
        """스캔 시작"""
        self.left_panel.start_scan()

    def stop_scan(self):
        """스캔 중지"""
        self.left_panel.stop_scan()

    def clear_completed(self):
        """완료된 항목 정리"""
        self.left_panel.clear_completed()

    # Dock 상태 관리 메서드
    def save_dock_state(self):
        """Dock 상태 저장"""
        return {
            "visible": self.isVisible(),
            "floating": self.isFloating(),
            "geometry": self.geometry().getRect(),
            "area": self.parent().dockWidgetArea(self) if self.parent() else Qt.LeftDockWidgetArea,
        }

    def restore_dock_state(self, state):
        """Dock 상태 복원"""
        if state.get("visible", True):
            self.setVisible(True)
        else:
            self.setVisible(False)

        if state.get("floating", False):
            self.setFloating(True)

        geometry = state.get("geometry")
        if geometry:
            self.setGeometry(*geometry)

        area = state.get("area", Qt.LeftDockWidgetArea)
        if self.parent():
            self.parent().addDockWidget(area, self)
