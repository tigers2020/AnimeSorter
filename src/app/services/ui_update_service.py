"""
UI 업데이트 서비스

EventBus를 통해 UI 업데이트 이벤트를 처리하는 서비스
"""

import logging
from typing import Any, Protocol

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QLabel, QMainWindow, QProgressBar, QStatusBar

from src.app.events import TypedEventBus
from src.app.ui_events import (
    ErrorMessageEvent,
    FileCountUpdateEvent,
    MemoryUsageUpdateEvent,
    MenuStateUpdateEvent,
    ProgressUpdateEvent,
    StatusBarUpdateEvent,
    SuccessMessageEvent,
    WindowTitleUpdateEvent,
)


class IUIUpdateService(Protocol):
    """UI 업데이트 서비스 인터페이스"""

    def initialize(self, main_window: QMainWindow) -> None:
        """서비스 초기화"""
        ...

    def dispose(self) -> None:
        """서비스 정리"""
        ...


class UIUpdateService(QObject):
    """UI 업데이트 서비스 구현"""

    # Qt 시그널 정의 (메인 스레드에서 UI 업데이트용)
    _status_bar_update_signal = pyqtSignal(str, object)  # message, progress
    _progress_update_signal = pyqtSignal(int, int, str)  # current, total, message
    _file_count_update_signal = pyqtSignal(int, int, int)  # count, processed, failed
    _memory_update_signal = pyqtSignal(float, object)  # memory_mb, cpu_percent
    _error_message_signal = pyqtSignal(str, str, str)  # message, details, error_type
    _success_message_signal = pyqtSignal(str, str, bool)  # message, details, auto_clear
    _window_title_signal = pyqtSignal(str, str)  # title, subtitle
    _menu_state_signal = pyqtSignal(str, bool, object, str)  # action_name, enabled, checked, text

    def __init__(self, event_bus: TypedEventBus, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)

        # UI 요소 참조들
        self.main_window: QMainWindow | None = None
        self.status_bar: QStatusBar | None = None
        self.status_label: QLabel | None = None
        self.status_progress: QProgressBar | None = None
        self.status_file_count: QLabel | None = None
        self.status_memory: QLabel | None = None

        # 자동 클리어용 타이머
        self.clear_timer = QTimer()
        self.clear_timer.timeout.connect(self._clear_status_message)
        self.clear_timer.setSingleShot(True)

        # 이벤트 구독 설정
        self._setup_event_subscriptions()
        self._connect_signals()

    def initialize(self, main_window: QMainWindow) -> None:
        """서비스 초기화"""
        self.main_window = main_window
        self._setup_ui_references()
        self.logger.info("UIUpdateService 초기화 완료")

    def dispose(self) -> None:
        """서비스 정리"""
        try:
            # 타이머 정리
            if self.clear_timer.isActive():
                self.clear_timer.stop()

            # 이벤트 구독 해제
            self._unsubscribe_events()

            # 참조 해제
            self.main_window = None
            self.status_bar = None
            self.status_label = None
            self.status_progress = None
            self.status_file_count = None
            self.status_memory = None

            self.logger.debug("UIUpdateService 정리 완료")
        except Exception as e:
            self.logger.error(f"UIUpdateService 정리 실패: {e}")

    def _setup_ui_references(self) -> None:
        """UI 요소 참조 설정"""
        if not self.main_window:
            return

        # 상태바 관련 요소들 찾기
        self.status_bar = self.main_window.statusBar()

        # 상태바의 자식 위젯들 찾기
        if self.status_bar:
            for child in self.status_bar.children():
                if isinstance(child, QLabel):
                    # 첫 번째 QLabel을 상태 메시지용으로 사용
                    if self.status_label is None:
                        self.status_label = child
                    # 이름으로 구분하여 다른 라벨들 찾기
                    elif hasattr(child, "objectName"):
                        name = child.objectName()
                        if "file" in name.lower() or "count" in name.lower():
                            self.status_file_count = child
                        elif "memory" in name.lower():
                            self.status_memory = child
                elif isinstance(child, QProgressBar):
                    self.status_progress = child

    def _setup_event_subscriptions(self) -> None:
        """이벤트 구독 설정"""
        # UI 업데이트 이벤트들 구독
        self.event_bus.subscribe(StatusBarUpdateEvent, self._on_status_bar_update, weak_ref=False)
        self.event_bus.subscribe(ProgressUpdateEvent, self._on_progress_update, weak_ref=False)
        self.event_bus.subscribe(FileCountUpdateEvent, self._on_file_count_update, weak_ref=False)
        self.event_bus.subscribe(MemoryUsageUpdateEvent, self._on_memory_update, weak_ref=False)
        self.event_bus.subscribe(ErrorMessageEvent, self._on_error_message, weak_ref=False)
        self.event_bus.subscribe(SuccessMessageEvent, self._on_success_message, weak_ref=False)
        self.event_bus.subscribe(
            WindowTitleUpdateEvent, self._on_window_title_update, weak_ref=False
        )
        self.event_bus.subscribe(MenuStateUpdateEvent, self._on_menu_state_update, weak_ref=False)

    def _unsubscribe_events(self) -> None:
        """이벤트 구독 해제"""
        # EventBus가 자동으로 약한 참조 정리를 하므로 explicit unsubscribe는 생략
        # dispose시에는 weak_ref=False로 등록했으므로 수동 해제 필요할 수 있음

    def _connect_signals(self) -> None:
        """Qt 시그널 연결"""
        self._status_bar_update_signal.connect(self._handle_status_bar_update)
        self._progress_update_signal.connect(self._handle_progress_update)
        self._file_count_update_signal.connect(self._handle_file_count_update)
        self._memory_update_signal.connect(self._handle_memory_update)
        self._error_message_signal.connect(self._handle_error_message)
        self._success_message_signal.connect(self._handle_success_message)
        self._window_title_signal.connect(self._handle_window_title_update)
        self._menu_state_signal.connect(self._handle_menu_state_update)

    # === 이벤트 핸들러들 ===

    def _on_status_bar_update(self, event: StatusBarUpdateEvent) -> None:
        """상태바 업데이트 이벤트 처리"""
        self._status_bar_update_signal.emit(event.message, event.progress)

        # 자동 클리어 설정
        if event.clear_after and event.clear_after > 0:
            self.clear_timer.start(int(event.clear_after * 1000))

    def _on_progress_update(self, event: ProgressUpdateEvent) -> None:
        """진행률 업데이트 이벤트 처리"""
        message = event.message or ""
        self._progress_update_signal.emit(event.current, event.total, message)

    def _on_file_count_update(self, event: FileCountUpdateEvent) -> None:
        """파일 수 업데이트 이벤트 처리"""
        self._file_count_update_signal.emit(event.count, event.processed, event.failed)

    def _on_memory_update(self, event: MemoryUsageUpdateEvent) -> None:
        """메모리 사용량 업데이트 이벤트 처리"""
        self._memory_update_signal.emit(event.memory_mb, event.cpu_percent)

    def _on_error_message(self, event: ErrorMessageEvent) -> None:
        """오류 메시지 이벤트 처리"""
        details = event.details or ""
        self._error_message_signal.emit(event.message, details, event.error_type)

    def _on_success_message(self, event: SuccessMessageEvent) -> None:
        """성공 메시지 이벤트 처리"""
        details = event.details or ""
        self._success_message_signal.emit(event.message, details, event.auto_clear)

    def _on_window_title_update(self, event: WindowTitleUpdateEvent) -> None:
        """윈도우 타이틀 업데이트 이벤트 처리"""
        subtitle = event.subtitle or ""
        self._window_title_signal.emit(event.title, subtitle)

    def _on_menu_state_update(self, event: MenuStateUpdateEvent) -> None:
        """메뉴 상태 업데이트 이벤트 처리"""
        text = event.text or ""
        self._menu_state_signal.emit(event.action_name, event.enabled, event.checked, text)

    # === Qt 시그널 핸들러들 (메인 스레드에서 실행) ===

    def _handle_status_bar_update(self, message: str, progress: Any) -> None:
        """상태바 업데이트 처리 (메인 스레드)"""
        if self.status_label:
            self.status_label.setText(message)

        if progress is not None and self.status_progress:
            self.status_progress.setValue(int(progress))

    def _handle_progress_update(self, current: int, total: int, message: str) -> None:
        """진행률 업데이트 처리 (메인 스레드)"""
        if self.status_progress:
            if total > 0:
                percentage = int((current / total) * 100)
                self.status_progress.setValue(percentage)
            else:
                self.status_progress.setValue(0)

        if message and self.status_label:
            progress_text = f"{message} ({current}/{total})" if total > 0 else message
            self.status_label.setText(progress_text)

    def _handle_file_count_update(self, count: int, processed: int, failed: int) -> None:
        """파일 수 업데이트 처리 (메인 스레드)"""
        if self.status_file_count:
            if processed > 0 or failed > 0:
                text = f"파일: {count} (처리: {processed}, 실패: {failed})"
            else:
                text = f"파일: {count}"
            self.status_file_count.setText(text)

    def _handle_memory_update(self, memory_mb: float, cpu_percent: Any) -> None:
        """메모리 사용량 업데이트 처리 (메인 스레드)"""
        if self.status_memory:
            if cpu_percent is not None:
                text = f"메모리: {memory_mb:.1f}MB (CPU: {cpu_percent:.1f}%)"
            else:
                text = f"메모리: {memory_mb:.1f}MB"
            self.status_memory.setText(text)

    def _handle_error_message(self, message: str, details: str, error_type: str) -> None:
        """오류 메시지 처리 (메인 스레드)"""
        if self.status_label:
            if error_type == "warning":
                prefix = "⚠️ "
            elif error_type == "info":
                prefix = "ℹ️ "
            else:
                prefix = "❌ "

            display_message = f"{prefix}{message}"
            if details:
                display_message += f": {details}"

            self.status_label.setText(display_message)

        # 로그에도 기록
        if error_type == "warning":
            self.logger.warning(f"{message}: {details}")
        elif error_type == "info":
            self.logger.info(f"{message}: {details}")
        else:
            self.logger.error(f"{message}: {details}")

    def _handle_success_message(self, message: str, details: str, auto_clear: bool) -> None:
        """성공 메시지 처리 (메인 스레드)"""
        if self.status_label:
            display_message = f"✅ {message}"
            if details:
                display_message += f": {details}"
            self.status_label.setText(display_message)

        # 자동 클리어
        if auto_clear:
            self.clear_timer.start(3000)  # 3초 후 클리어

        self.logger.info(f"{message}: {details}")

    def _handle_window_title_update(self, title: str, subtitle: str) -> None:
        """윈도우 타이틀 업데이트 처리 (메인 스레드)"""
        if self.main_window:
            full_title = f"{title} - {subtitle}" if subtitle else title
            self.main_window.setWindowTitle(full_title)

    def _handle_menu_state_update(
        self, action_name: str, enabled: bool, checked: Any, text: str
    ) -> None:
        """메뉴 상태 업데이트 처리 (메인 스레드)"""
        # MainWindow에서 메뉴 액션을 찾아서 업데이트
        if self.main_window:
            action = self.main_window.findChild(QObject, action_name)
            if action and hasattr(action, "setEnabled"):
                action.setEnabled(enabled)
                if checked is not None and hasattr(action, "setChecked"):
                    action.setChecked(bool(checked))
                if text and hasattr(action, "setText"):
                    action.setText(text)

    def _clear_status_message(self) -> None:
        """상태 메시지 클리어"""
        if self.status_label:
            self.status_label.setText("준비")
