"""
리팩토링된 메인 윈도우

이벤트 버스, 컨트롤러, 서비스, 뷰모델 패턴을 사용하여 구현된 깔끔한 아키텍처
"""

import logging
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QVBoxLayout, QWidget

from .components.left_panel import LeftPanel
from .components.main_toolbar import MainToolbar
from .components.right_panel import RightPanel
from .controllers.file_processing_controller import FileProcessingController
from .controllers.organize_controller import OrganizeController
from .controllers.tmdb_controller import TMDBController
from .controllers.window_manager import WindowManager
from .core.command_invoker import CommandInvoker
from .core.component_factory import ComponentFactory
from .core.event_bus import EventBus
from .view_models.detail_view_model import DetailViewModel
from .view_models.file_list_view_model import FileListViewModel
from .view_models.main_window_view_model import MainWindowViewModel


class MainWindow(QMainWindow):
    """리팩토링된 메인 윈도우"""

    def __init__(self):
        super().__init__()

        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        self.logger.info("MainWindow 초기화 시작")

        # 핵심 컴포넌트들
        self.event_bus: EventBus | None = None
        self.component_factory: ComponentFactory | None = None
        self.command_invoker: CommandInvoker | None = None

        # 컨트롤러들
        self.window_manager: WindowManager | None = None
        self.file_processing_controller: FileProcessingController | None = None
        self.tmdb_controller: TMDBController | None = None
        self.organize_controller: OrganizeController | None = None

        # 뷰모델들
        self.main_window_view_model: MainWindowViewModel | None = None
        self.file_list_view_model: FileListViewModel | None = None
        self.detail_view_model: DetailViewModel | None = None

        # UI 컴포넌트들
        self.toolbar: MainToolbar | None = None
        self.left_panel: LeftPanel | None = None
        self.right_panel: RightPanel | None = None

        # 초기화
        self._initialize_architecture()
        self._setup_ui()
        self._connect_signals()
        self._start_services()

        self.logger.info("MainWindow 초기화 완료")

    def _initialize_architecture(self):
        """아키텍처 초기화"""
        # 1. 이벤트 버스 생성
        self.event_bus = EventBus()

        # 2. 컴포넌트 팩토리 생성
        self.component_factory = ComponentFactory(self.event_bus)

        # 3. 명령 실행기 생성
        self.command_invoker = CommandInvoker()

        # 4. 컨트롤러들 생성
        self.window_manager = self.component_factory.create_controller("window_manager")
        self.file_processing_controller = self.component_factory.create_controller(
            "file_processing_controller"
        )
        self.tmdb_controller = self.component_factory.create_controller("tmdb_controller")
        self.organize_controller = self.component_factory.create_controller("organize_controller")

        # 5. 뷰모델들 생성
        self.main_window_view_model = self.component_factory.create_view_model(
            "main_window_view_model"
        )
        self.file_list_view_model = self.component_factory.create_view_model("file_list_view_model")
        self.detail_view_model = self.component_factory.create_view_model("detail_view_model")

        self.logger.info("아키텍처 초기화 완료")

    def _setup_ui(self):
        """UI 설정"""
        # 윈도우 기본 설정
        self.setWindowTitle("AnimeSorter - 리팩토링 버전")
        self.setGeometry(100, 100, 1400, 900)

        # 중앙 위젯 생성
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 툴바 생성
        self.toolbar = MainToolbar(self.event_bus, self.command_invoker)
        main_layout.addWidget(self.toolbar)

        # 스플리터 생성 (좌우 패널)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 좌측 패널 생성
        self.left_panel = LeftPanel(
            self.event_bus, self.file_list_view_model, self.detail_view_model
        )
        splitter.addWidget(self.left_panel)

        # 우측 패널 생성
        self.right_panel = RightPanel(self.event_bus)
        splitter.addWidget(self.right_panel)

        # 스플리터 비율 설정
        splitter.setSizes([800, 400])

        # 윈도우 매니저로 UI 설정 위임
        self.window_manager.setup_window_ui(self)

        self.logger.info("UI 설정 완료")

    def _connect_signals(self):
        """시그널 연결"""
        # 뷰모델 시그널 연결
        if self.main_window_view_model:
            self.main_window_view_model.ui_state_changed.connect(self._on_ui_state_changed)
            self.main_window_view_model.status_message_changed.connect(
                self._on_status_message_changed
            )
            self.main_window_view_model.error_message_changed.connect(
                self._on_error_message_changed
            )

        if self.file_list_view_model:
            self.file_list_view_model.data_changed.connect(self._on_file_list_data_changed)
            self.file_list_view_model.selection_changed.connect(
                self._on_file_list_selection_changed
            )

        if self.detail_view_model:
            self.detail_view_model.detail_changed.connect(self._on_detail_changed)

        # 이벤트 버스 연결
        if self.event_bus:
            self.event_bus.subscribe("command_executed", self._on_command_executed)
            self.event_bus.subscribe("command_failed", self._on_command_failed)

        self.logger.info("시그널 연결 완료")

    def _start_services(self):
        """서비스 시작"""
        # 서비스들 시작
        file_service = self.component_factory.get_service("file_service")
        metadata_service = self.component_factory.get_service("metadata_service")
        state_service = self.component_factory.get_service("state_service")

        if file_service:
            file_service.start()
        if metadata_service:
            metadata_service.start()
        if state_service:
            state_service.start()

        self.logger.info("서비스 시작 완료")

    # === 시그널 핸들러 ===

    def _on_ui_state_changed(self):
        """UI 상태 변경 처리"""
        if self.toolbar:
            self.toolbar.update_button_states()

    def _on_status_message_changed(self):
        """상태 메시지 변경 처리"""
        if self.right_panel:
            self.right_panel.update_status_message()

    def _on_error_message_changed(self):
        """오류 메시지 변경 처리"""
        if self.right_panel:
            self.right_panel.update_error_message()

    def _on_file_list_data_changed(self):
        """파일 리스트 데이터 변경 처리"""
        if self.left_panel:
            self.left_panel.refresh_file_list()

    def _on_file_list_selection_changed(self):
        """파일 리스트 선택 변경 처리"""
        if self.left_panel:
            self.left_panel.update_selection()

    def _on_detail_changed(self):
        """상세 정보 변경 처리"""
        if self.left_panel:
            self.left_panel.refresh_detail_view()

    def _on_command_executed(self, command_info):
        """명령 실행 완료 처리"""
        self.logger.info(f"명령 실행 완료: {command_info.get('command_name')}")

    def _on_command_failed(self, command_info):
        """명령 실행 실패 처리"""
        self.logger.error(
            f"명령 실행 실패: {command_info.get('command_name')} - {command_info.get('error')}"
        )

    # === 공개 메서드 ===

    def get_event_bus(self):
        """이벤트 버스 반환"""
        return self.event_bus

    def get_component_factory(self):
        """컴포넌트 팩토리 반환"""
        return self.component_factory

    def get_command_invoker(self):
        """명령 실행기 반환"""
        return self.command_invoker

    def closeEvent(self, event):
        """윈도우 종료 이벤트"""
        self.logger.info("MainWindow 종료 시작")

        try:
            # 서비스들 정지
            file_service = self.component_factory.get_service("file_service")
            metadata_service = self.component_factory.get_service("metadata_service")
            state_service = self.component_factory.get_service("state_service")

            if file_service and file_service.is_running:
                file_service.stop()
            if metadata_service and metadata_service.is_running:
                metadata_service.stop()
            if state_service and state_service.is_running:
                state_service.stop()

            # 컨트롤러들 정리
            if self.window_manager:
                self.window_manager.cleanup()
            if self.file_processing_controller:
                self.file_processing_controller.cleanup()
            if self.tmdb_controller:
                self.tmdb_controller.cleanup()
            if self.organize_controller:
                self.organize_controller.cleanup()

            # 뷰모델들 정리
            if self.main_window_view_model:
                self.main_window_view_model.cleanup()
            if self.file_list_view_model:
                self.file_list_view_model.cleanup()
            if self.detail_view_model:
                self.detail_view_model.cleanup()

            # 컴포넌트 팩토리 정리
            if self.component_factory:
                self.component_factory.cleanup_all()

            self.logger.info("MainWindow 종료 완료")
            event.accept()

        except Exception as e:
            self.logger.error(f"MainWindow 종료 중 오류: {e}")
            event.accept()


def main():
    """메인 함수"""
    app = QApplication(sys.argv)

    # High DPI 설정
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()

    # 애플리케이션 실행
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
