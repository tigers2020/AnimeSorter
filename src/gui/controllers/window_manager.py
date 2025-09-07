"""
윈도우 매니저

메인 윈도우의 UI 구성 및 레이아웃 관리를 담당하는 컨트롤러
"""

import logging
from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction,
    QFrame,
    QLabel,
    QMainWindow,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.interfaces.i_controller import IController
from src.interfaces.i_event_bus import Event, IEventBus


class WindowManager(IController):
    """
    윈도우 매니저 컨트롤러

    메인 윈도우의 생성, 레이아웃, 메뉴바, 상태바 관리
    """

    def __init__(self, event_bus: IEventBus, main_window: QMainWindow):
        super().__init__(event_bus)
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # UI 컴포넌트들
        self.central_widget = None
        self.splitter = None
        self.status_bar = None
        self.menu_bar = None

        # 상태바 위젯들
        self.status_label = None
        self.status_progress = None
        self.status_file_count = None
        self.status_memory = None

        # 메뉴 액션들
        self.menu_actions: dict[str, QAction] = {}

        # 설정
        self.config = {
            "window_title": "AnimeSorter v2.0.0 - 애니메이션 파일 정리 도구",
            "window_geometry": (100, 100, 1400, 900),
            "min_size": (1000, 700),
            "splitter_sizes": [400, 1000],
            "splitter_stretch": [0, 1],
        }

        self.logger.info("WindowManager 초기화 완료")

    def initialize(self) -> None:
        """윈도우 매니저 초기화"""
        try:
            self._setup_window_properties()
            self._create_menu_bar()
            self._create_central_widget()
            self._create_status_bar()
            self._setup_event_subscriptions()

            self.logger.info("WindowManager 초기화 완료")

        except Exception as e:
            self.logger.error(f"WindowManager 초기화 실패: {e}")
            raise

    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            # 이벤트 구독 해제
            self.event_bus.clear_subscribers()

            # 메뉴 액션 정리
            self.menu_actions.clear()

            self.logger.info("WindowManager 정리 완료")

        except Exception as e:
            self.logger.error(f"WindowManager 정리 실패: {e}")

    def handle_event(self, event: Event) -> None:
        """이벤트 처리"""
        try:
            if event.type == "status_update":
                self._handle_status_update(event.data)
            elif event.type == "progress_update":
                self._handle_progress_update(event.data)
            elif event.type == "file_count_update":
                self._handle_file_count_update(event.data)
            elif event.type == "memory_update":
                self._handle_memory_update(event.data)
            elif event.type == "menu_action_trigger":
                self._handle_menu_action(event.data)
            elif event.type == "window_state_save":
                self._save_window_state()
            elif event.type == "window_state_restore":
                self._restore_window_state(event.data)

        except Exception as e:
            self.logger.error(f"이벤트 처리 실패: {event.type} - {e}")

    def _setup_window_properties(self) -> None:
        """윈도우 기본 속성 설정"""
        # 윈도우 제목 설정
        self.main_window.setWindowTitle(self.config["window_title"])

        # 윈도우 크기 및 위치 설정
        x, y, width, height = self.config["window_geometry"]
        self.main_window.setGeometry(x, y, width, height)

        # 최소 크기 설정
        min_width, min_height = self.config["min_size"]
        self.main_window.setMinimumSize(min_width, min_height)

        # 아이콘 설정
        self.main_window.setWindowIcon(QIcon("🎬"))

        self.logger.debug("윈도우 속성 설정 완료")

    def _create_menu_bar(self) -> None:
        """메뉴바 생성"""
        self.menu_bar = self.main_window.menuBar()

        # 파일 메뉴
        self._create_file_menu()

        # 편집 메뉴
        self._create_edit_menu()

        # 도구 메뉴
        self._create_tools_menu()

        # 도움말 메뉴
        self._create_help_menu()

        self.logger.debug("메뉴바 생성 완료")

    def _create_file_menu(self) -> None:
        """파일 메뉴 생성"""
        file_menu = self.menu_bar.addMenu("파일(&F)")

        # 파일 선택
        self.menu_actions["open_files"] = file_menu.addAction("파일 선택(&O)")
        self.menu_actions["open_files"].setShortcut("Ctrl+O")
        self.menu_actions["open_files"].setStatusTip("애니메이션 파일을 선택합니다")
        self.menu_actions["open_files"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "open_files")
        )

        # 폴더 선택
        self.menu_actions["open_folder"] = file_menu.addAction("폴더 선택(&F)")
        self.menu_actions["open_folder"].setShortcut("Ctrl+Shift+O")
        self.menu_actions["open_folder"].setStatusTip("애니메이션 파일이 있는 폴더를 선택합니다")
        self.menu_actions["open_folder"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "open_folder")
        )

        file_menu.addSeparator()

        # 내보내기
        self.menu_actions["export"] = file_menu.addAction("결과 내보내기(&E)")
        self.menu_actions["export"].setShortcut("Ctrl+E")
        self.menu_actions["export"].setStatusTip("스캔 결과를 CSV 파일로 내보냅니다")
        self.menu_actions["export"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "export")
        )

        file_menu.addSeparator()

        # 종료
        self.menu_actions["exit"] = file_menu.addAction("종료(&X)")
        self.menu_actions["exit"].setShortcut("Ctrl+Q")
        self.menu_actions["exit"].setStatusTip("애플리케이션을 종료합니다")
        self.menu_actions["exit"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "exit")
        )

    def _create_edit_menu(self) -> None:
        """편집 메뉴 생성"""
        edit_menu = self.menu_bar.addMenu("편집(&E)")

        # 설정
        self.menu_actions["settings"] = edit_menu.addAction("설정(&S)")
        self.menu_actions["settings"].setShortcut("Ctrl+,")
        self.menu_actions["settings"].setStatusTip("애플리케이션 설정을 변경합니다")
        self.menu_actions["settings"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "settings")
        )

        edit_menu.addSeparator()

        # 필터 초기화
        self.menu_actions["reset_filters"] = edit_menu.addAction("필터 초기화(&R)")
        self.menu_actions["reset_filters"].setShortcut("Ctrl+R")
        self.menu_actions["reset_filters"].setStatusTip("모든 필터를 초기화합니다")
        self.menu_actions["reset_filters"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "reset_filters")
        )

    def _create_tools_menu(self) -> None:
        """도구 메뉴 생성"""
        tools_menu = self.menu_bar.addMenu("도구(&T)")

        # 스캔 시작/중지
        self.menu_actions["start_scan"] = tools_menu.addAction("스캔 시작(&S)")
        self.menu_actions["start_scan"].setShortcut("F5")
        self.menu_actions["start_scan"].setStatusTip("파일 스캔을 시작합니다")
        self.menu_actions["start_scan"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "start_scan")
        )

        self.menu_actions["stop_scan"] = tools_menu.addAction("스캔 중지(&P)")
        self.menu_actions["stop_scan"].setShortcut("F6")
        self.menu_actions["stop_scan"].setStatusTip("파일 스캔을 중지합니다")
        self.menu_actions["stop_scan"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "stop_scan")
        )

        tools_menu.addSeparator()

        # 정리 실행
        self.menu_actions["organize"] = tools_menu.addAction("정리 실행(&C)")
        self.menu_actions["organize"].setShortcut("F7")
        self.menu_actions["organize"].setStatusTip("파일 정리를 실행합니다")
        self.menu_actions["organize"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "organize")
        )

        # 시뮬레이션
        self.menu_actions["simulate"] = tools_menu.addAction("시뮬레이션(&M)")
        self.menu_actions["simulate"].setShortcut("F8")
        self.menu_actions["simulate"].setStatusTip("파일 정리를 시뮬레이션합니다")
        self.menu_actions["simulate"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "simulate")
        )

    def _create_help_menu(self) -> None:
        """도움말 메뉴 생성"""
        help_menu = self.menu_bar.addMenu("도움말(&H)")

        # 정보
        self.menu_actions["about"] = help_menu.addAction("정보(&A)")
        self.menu_actions["about"].setStatusTip("AnimeSorter에 대한 정보를 표시합니다")
        self.menu_actions["about"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "about")
        )

        # 사용법
        self.menu_actions["help"] = help_menu.addAction("사용법(&H)")
        self.menu_actions["help"].setShortcut("F1")
        self.menu_actions["help"].setStatusTip("사용법을 표시합니다")
        self.menu_actions["help"].triggered.connect(
            lambda: self.event_bus.publish("menu_action", "help")
        )

    def _create_central_widget(self) -> None:
        """중앙 위젯 생성"""
        self.central_widget = QWidget()
        self.main_window.setCentralWidget(self.central_widget)

        # 메인 레이아웃
        main_layout = QVBoxLayout(self.central_widget)

        # 툴바 영역은 이벤트로 추가 요청
        self.event_bus.publish("toolbar_container_ready", main_layout)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        main_layout.addWidget(line)

        # 스플리터 생성
        self.splitter = QSplitter(Qt.Horizontal)

        # 왼쪽 패널 컨테이너
        self.event_bus.publish("left_panel_container_ready", self.splitter)

        # 오른쪽 패널 컨테이너
        self.event_bus.publish("right_panel_container_ready", self.splitter)

        # 스플리터 설정
        self.splitter.setSizes(self.config["splitter_sizes"])
        self.splitter.setStretchFactor(0, self.config["splitter_stretch"][0])
        self.splitter.setStretchFactor(1, self.config["splitter_stretch"][1])

        main_layout.addWidget(self.splitter)

        self.logger.debug("중앙 위젯 생성 완료")

    def _create_status_bar(self) -> None:
        """상태바 생성"""
        self.status_bar = self.main_window.statusBar()

        # 기본 상태 메시지
        self.status_label = QLabel("준비됨")
        self.status_bar.addWidget(self.status_label)

        # 진행률 표시
        self.status_bar.addPermanentWidget(QLabel("진행률:"))
        self.status_progress = QProgressBar()
        self.status_progress.setMaximumWidth(200)
        self.status_progress.setMaximumHeight(20)
        self.status_bar.addPermanentWidget(self.status_progress)

        # 파일 수 표시
        self.status_file_count = QLabel("파일: 0")
        self.status_bar.addPermanentWidget(self.status_file_count)

        # 메모리 사용량 표시
        self.status_memory = QLabel("메모리: 0MB")
        self.status_bar.addPermanentWidget(self.status_memory)

        # 초기 상태 설정
        self.update_status("애플리케이션이 준비되었습니다")

        self.logger.debug("상태바 생성 완료")

    def _setup_event_subscriptions(self) -> None:
        """이벤트 구독 설정"""
        self.event_bus.subscribe("status_update", self.handle_event)
        self.event_bus.subscribe("progress_update", self.handle_event)
        self.event_bus.subscribe("file_count_update", self.handle_event)
        self.event_bus.subscribe("memory_update", self.handle_event)
        self.event_bus.subscribe("window_state_save", self.handle_event)
        self.event_bus.subscribe("window_state_restore", self.handle_event)

    def update_status(self, message: str, progress: int | None = None) -> None:
        """
        상태바 업데이트

        Args:
            message: 상태 메시지
            progress: 진행률 (0-100)
        """
        if self.status_label:
            self.status_label.setText(message)

        if progress is not None and self.status_progress:
            self.status_progress.setValue(progress)

        self.logger.debug(f"상태 업데이트: {message} ({progress}%)")

    def update_file_count(self, count: int) -> None:
        """파일 수 업데이트"""
        if self.status_file_count:
            self.status_file_count.setText(f"파일: {count}")

    def update_memory_usage(self, memory_mb: float) -> None:
        """메모리 사용량 업데이트"""
        if self.status_memory:
            self.status_memory.setText(f"메모리: {memory_mb:.1f}MB")

    def set_menu_action_enabled(self, action_name: str, enabled: bool) -> None:
        """메뉴 액션 활성화/비활성화"""
        if action_name in self.menu_actions:
            self.menu_actions[action_name].setEnabled(enabled)

    def get_window_geometry(self) -> tuple:
        """윈도우 기하학 정보 반환"""
        geometry = self.main_window.geometry()
        return (geometry.x(), geometry.y(), geometry.width(), geometry.height())

    def set_window_geometry(self, x: int, y: int, width: int, height: int) -> None:
        """윈도우 기하학 설정"""
        self.main_window.setGeometry(x, y, width, height)

    def get_splitter_sizes(self) -> list:
        """스플리터 크기 반환"""
        return self.splitter.sizes() if self.splitter else []

    def set_splitter_sizes(self, sizes: list) -> None:
        """스플리터 크기 설정"""
        if self.splitter:
            self.splitter.setSizes(sizes)

    def _handle_status_update(self, data: dict) -> None:
        """상태 업데이트 처리"""
        message = data.get("message", "")
        progress = data.get("progress")
        self.update_status(message, progress)

    def _handle_progress_update(self, data: dict) -> None:
        """진행률 업데이트 처리"""
        progress = data.get("value", 0)
        if self.status_progress:
            self.status_progress.setValue(progress)

    def _handle_file_count_update(self, data: dict) -> None:
        """파일 수 업데이트 처리"""
        count = data.get("count", 0)
        self.update_file_count(count)

    def _handle_memory_update(self, data: dict) -> None:
        """메모리 사용량 업데이트 처리"""
        memory_mb = data.get("memory_mb", 0.0)
        self.update_memory_usage(memory_mb)

    def _handle_menu_action(self, action_name: str) -> None:
        """메뉴 액션 처리"""
        # 해당 액션에 대한 이벤트 발행
        self.event_bus.publish(f"menu_{action_name}_triggered")

    def _save_window_state(self) -> None:
        """윈도우 상태 저장"""
        state = {
            "geometry": self.get_window_geometry(),
            "splitter_sizes": self.get_splitter_sizes(),
        }
        self.event_bus.publish("window_state_data", state)

    def _restore_window_state(self, state: dict) -> None:
        """윈도우 상태 복원"""
        if "geometry" in state:
            x, y, w, h = state["geometry"]
            self.set_window_geometry(x, y, w, h)

        if "splitter_sizes" in state:
            self.set_splitter_sizes(state["splitter_sizes"])

    def configure(self, config: dict[str, Any]) -> None:
        """설정 업데이트"""
        self.config.update(config)

        # 설정 적용
        if self._is_initialized:
            if "window_title" in config:
                self.main_window.setWindowTitle(config["window_title"])

            if "splitter_sizes" in config and self.splitter:
                self.splitter.setSizes(config["splitter_sizes"])
