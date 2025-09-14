"""
메시지 및 로그 컨트롤러 - MainWindow에서 메시지 및 로그 관리 기능을 분리

MainWindow의 메시지 표시 및 로그 관리 책임을 담당하는 전용 클래스입니다.
- 사용자 메시지 표시 (에러, 성공, 정보)
- 로그 도킹 위젯 관리
- 활동 로그 및 에러 로그 관리
- 상태바 메시지 관리
"""

import logging
from datetime import datetime
from typing import Any

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class MessageLogController(QObject):
    """메시지 및 로그 관리 전용 컨트롤러"""

    message_shown = pyqtSignal(str, str)
    log_added = pyqtSignal(str, str)
    logs_cleared = pyqtSignal()
    status_updated = pyqtSignal(str, int)

    def __init__(self, main_window: QMainWindow):
        super().__init__()
        self.main_window = main_window
        self.log_dock = None
        self.activity_log_widget = None
        self.error_log_widget = None
        self.status_bar = None
        self.progress_bar = None
        self.auto_clear_messages = True
        self.message_timeout = 5000
        self.max_log_entries = 1000
        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self._clear_status_message)
        logger.info("MessageLogController 초기화 완료")

    def setup_log_dock(self) -> bool:
        """로그 도킹 위젯을 설정합니다"""
        try:
            if self.log_dock is not None:
                logger.debug("로그 도킹 위젯이 이미 설정되어 있습니다.")
                return True
            self.log_dock = QDockWidget("로그", self.main_window)
            self.log_dock.setObjectName("logDockWidget")
            self.log_dock.setAllowedAreas(2)
            log_container = QWidget()
            log_layout = QVBoxLayout(log_container)
            activity_label = QLabel("활동 로그")
            activity_label.setObjectName("activityLogLabel")
            self.activity_log_widget = QTextEdit()
            self.activity_log_widget.setObjectName("activityLogWidget")
            self.activity_log_widget.setMaximumHeight(200)
            self.activity_log_widget.setReadOnly(True)
            error_label = QLabel("에러 로그")
            error_label.setObjectName("errorLogLabel")
            self.error_log_widget = QTextEdit()
            self.error_log_widget.setObjectName("errorLogWidget")
            self.error_log_widget.setMaximumHeight(200)
            self.error_log_widget.setReadOnly(True)
            button_layout = QHBoxLayout()
            clear_activity_btn = QPushButton("활동 로그 지우기")
            clear_activity_btn.setObjectName("clearActivityLogButton")
            clear_activity_btn.clicked.connect(self.clear_activity_log)
            clear_error_btn = QPushButton("에러 로그 지우기")
            clear_error_btn.setObjectName("clearErrorLogButton")
            clear_error_btn.clicked.connect(self.clear_error_log)
            clear_all_btn = QPushButton("모든 로그 지우기")
            clear_all_btn.setObjectName("clearAllLogsButton")
            clear_all_btn.clicked.connect(self.clear_logs)
            button_layout.addWidget(clear_activity_btn)
            button_layout.addWidget(clear_error_btn)
            button_layout.addWidget(clear_all_btn)
            log_layout.addWidget(activity_label)
            log_layout.addWidget(self.activity_log_widget)
            log_layout.addWidget(error_label)
            log_layout.addWidget(self.error_log_widget)
            log_layout.addLayout(button_layout)
            self.log_dock.setWidget(log_container)
            self.main_window.addDockWidget(2, self.log_dock)
            self.add_activity_log("로그 시스템 초기화 완료")
            logger.info("✅ 로그 도킹 위젯 설정 완료")
            return True
        except Exception as e:
            logger.error(f"❌ 로그 도킹 위젯 설정 실패: {e}")
            return False

    def show_error_message(
        self, message: str, details: str = "", error_type: str = "error"
    ) -> bool:
        """에러 메시지를 표시합니다"""
        try:
            status_message = f"❌ {message}"
            self.update_status_bar(status_message)
            log_message = f"[{error_type.upper()}] {message}"
            if details:
                log_message += f" - {details}"
            self.add_error_log(log_message)
            if error_type == "critical":
                QMessageBox.critical(self.main_window, "심각한 오류", f"{message}\n\n{details}")
            elif error_type == "warning":
                QMessageBox.warning(self.main_window, "경고", f"{message}\n\n{details}")
            else:
                QMessageBox.information(self.main_window, "오류", f"{message}\n\n{details}")
            logger.error(f"사용자에게 에러 메시지 표시: {message}")
            self.message_shown.emit("error", message)
            return True
        except Exception as e:
            logger.error(f"에러 메시지 표시 실패: {e}")
            return False

    def show_success_message(
        self, message: str, details: str = "", auto_clear: bool = True
    ) -> bool:
        """성공 메시지를 표시합니다"""
        try:
            status_message = f"✅ {message}"
            self.update_status_bar(status_message)
            log_message = f"[SUCCESS] {message}"
            if details:
                log_message += f" - {details}"
            self.add_activity_log(log_message)
            if auto_clear and self.auto_clear_messages:
                self.message_timer.start(self.message_timeout)
            logger.info(f"사용자에게 성공 메시지 표시: {message}")
            self.message_shown.emit("success", message)
            return True
        except Exception as e:
            logger.error(f"성공 메시지 표시 실패: {e}")
            return False

    def show_info_message(self, message: str, details: str = "", auto_clear: bool = True) -> bool:
        """정보 메시지를 표시합니다"""
        try:
            status_message = f"ℹ️ {message}"
            self.update_status_bar(status_message)
            log_message = f"[INFO] {message}"
            if details:
                log_message += f" - {details}"
            self.add_activity_log(log_message)
            if auto_clear and self.auto_clear_messages:
                self.message_timer.start(self.message_timeout)
            logger.info(f"사용자에게 정보 메시지 표시: {message}")
            self.message_shown.emit("info", message)
            return True
        except Exception as e:
            logger.error(f"정보 메시지 표시 실패: {e}")
            return False

    def add_activity_log(self, message: str) -> bool:
        """활동 로그에 메시지를 추가합니다"""
        try:
            if not self.activity_log_widget:
                logger.warning("활동 로그 위젯이 설정되지 않았습니다.")
                return False
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            self.activity_log_widget.append(formatted_message)
            self._limit_log_entries(self.activity_log_widget)
            self.activity_log_widget.verticalScrollBar().setValue(
                self.activity_log_widget.verticalScrollBar().maximum()
            )
            logger.debug(f"활동 로그 추가: {message}")
            self.log_added.emit("activity", message)
            return True
        except Exception as e:
            logger.error(f"활동 로그 추가 실패: {e}")
            return False

    def add_error_log(self, message: str) -> bool:
        """에러 로그에 메시지를 추가합니다"""
        try:
            if not self.error_log_widget:
                logger.warning("에러 로그 위젯이 설정되지 않았습니다.")
                return False
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            self.error_log_widget.append(formatted_message)
            self._limit_log_entries(self.error_log_widget)
            self.error_log_widget.verticalScrollBar().setValue(
                self.error_log_widget.verticalScrollBar().maximum()
            )
            logger.debug(f"에러 로그 추가: {message}")
            self.log_added.emit("error", message)
            return False
        except Exception as e:
            logger.error(f"에러 로그 추가 실패: {e}")
            return False

    def clear_activity_log(self) -> bool:
        """활동 로그를 지웁니다"""
        try:
            if self.activity_log_widget:
                self.activity_log_widget.clear()
                self.add_activity_log("활동 로그가 지워졌습니다.")
                logger.info("활동 로그 지우기 완료")
                return True
            return False
        except Exception as e:
            logger.error(f"활동 로그 지우기 실패: {e}")
            return False

    def clear_error_log(self) -> bool:
        """에러 로그를 지웁니다"""
        try:
            if self.error_log_widget:
                self.error_log_widget.clear()
                self.add_activity_log("에러 로그가 지워졌습니다.")
                logger.info("에러 로그 지우기 완료")
                return True
            return False
        except Exception as e:
            logger.error(f"에러 로그 지우기 실패: {e}")
            return False

    def clear_logs(self) -> bool:
        """모든 로그를 지웁니다"""
        try:
            self.clear_activity_log()
            self.clear_error_log()
            self.logs_cleared.emit()
            logger.info("모든 로그 지우기 완료")
            return True
        except Exception as e:
            logger.error(f"모든 로그 지우기 실패: {e}")
            return False

    def toggle_log_dock(self) -> bool:
        """로그 도킹 위젯을 토글합니다"""
        try:
            if not self.log_dock:
                return self.setup_log_dock()
            if self.log_dock.isVisible():
                self.log_dock.hide()
                self.add_activity_log("로그 도킹 위젯 숨김")
            else:
                self.log_dock.show()
                self.add_activity_log("로그 도킹 위젯 표시")
            return True
        except Exception as e:
            logger.error(f"로그 도킹 위젯 토글 실패: {e}")
            return False

    def show_log_dock(self):
        """로그 도킹 위젯을 표시합니다"""
        try:
            if not self.log_dock:
                self.setup_log_dock()
            else:
                self.log_dock.show()
                self.add_activity_log("로그 도킹 위젯 표시")
        except Exception as e:
            logger.warning(f"로그 도킹 위젯 표시 실패: {e}")

    def hide_log_dock(self):
        """로그 도킹 위젯을 숨깁니다"""
        try:
            if self.log_dock:
                self.log_dock.hide()
                self.add_activity_log("로그 도킹 위젯 숨김")
        except Exception as e:
            logger.warning(f"로그 도킹 위젯 숨김 실패: {e}")

    def update_status_bar(self, message: str, progress: int | None = None) -> bool:
        """상태바를 업데이트합니다"""
        try:
            if not self.status_bar:
                self.status_bar = self.main_window.statusBar()
            if self.status_bar:
                self.status_bar.showMessage(message)
                if progress is not None:
                    self._update_progress_bar(progress)
                self.status_updated.emit(message, progress or 0)
                return True
            return False
        except Exception as e:
            logger.error(f"상태바 업데이트 실패: {e}")
            return False

    def update_progress(self, current: int, total: int, message: str = "") -> bool:
        """진행률을 업데이트합니다"""
        try:
            if total > 0:
                progress_percent = int(current / total * 100)
                progress_message = f"{message} ({current}/{total}, {progress_percent}%)"
                return self.update_status_bar(progress_message, progress_percent)
            return self.update_status_bar(message)
        except Exception as e:
            logger.error(f"진행률 업데이트 실패: {e}")
            return False

    def _update_progress_bar(self, progress: int):
        """프로그레스바를 업데이트합니다"""
        try:
            if not self.progress_bar:
                self.progress_bar = QProgressBar()
                self.progress_bar.setObjectName("statusProgressBar")
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setVisible(False)
                if self.status_bar:
                    self.status_bar.addPermanentWidget(self.progress_bar)
            if self.progress_bar:
                self.progress_bar.setValue(progress)
                self.progress_bar.setVisible(progress > 0)
        except Exception as e:
            logger.warning(f"프로그레스바 업데이트 실패: {e}")

    def _clear_status_message(self):
        """상태바 메시지를 지웁니다"""
        try:
            if self.status_bar:
                self.status_bar.clearMessage()
            if self.progress_bar:
                self.progress_bar.setVisible(False)
        except Exception as e:
            logger.warning(f"상태바 메시지 지우기 실패: {e}")

    def _limit_log_entries(self, log_widget: QTextEdit):
        """로그 항목 수를 제한합니다"""
        try:
            if not log_widget:
                return
            text = log_widget.toPlainText()
            lines = text.split("\n")
            if len(lines) > self.max_log_entries:
                lines = lines[-self.max_log_entries :]
                log_widget.setPlainText("\n".join(lines))
        except Exception as e:
            logger.warning(f"로그 항목 수 제한 실패: {e}")

    def set_auto_clear_messages(self, enabled: bool):
        """메시지 자동 지우기 설정"""
        self.auto_clear_messages = enabled
        logger.debug(f"메시지 자동 지우기: {'활성화' if enabled else '비활성화'}")

    def set_message_timeout(self, timeout_ms: int):
        """메시지 자동 지우기 타임아웃 설정"""
        self.message_timeout = timeout_ms
        logger.debug(f"메시지 자동 지우기 타임아웃: {timeout_ms}ms")

    def set_max_log_entries(self, max_entries: int):
        """최대 로그 항목 수 설정"""
        self.max_log_entries = max_entries
        logger.debug(f"최대 로그 항목 수: {max_entries}")

    def get_log_statistics(self) -> dict[str, Any]:
        """로그 통계를 반환합니다"""
        try:
            activity_count = 0
            error_count = 0
            if self.activity_log_widget:
                activity_text = self.activity_log_widget.toPlainText()
                activity_count = len([line for line in activity_text.split("\n") if line.strip()])
            if self.error_log_widget:
                error_text = self.error_log_widget.toPlainText()
                error_count = len([line for line in error_text.split("\n") if line.strip()])
            return {
                "activity_log_count": activity_count,
                "error_log_count": error_count,
                "total_log_count": activity_count + error_count,
                "max_log_entries": self.max_log_entries,
                "auto_clear_enabled": self.auto_clear_messages,
                "message_timeout": self.message_timeout,
            }
        except Exception as e:
            logger.error(f"로그 통계 조회 실패: {e}")
            return {}

    def cleanup(self):
        """리소스 정리"""
        try:
            if self.message_timer:
                self.message_timer.stop()
            if self.log_dock:
                self.log_dock.close()
                self.log_dock = None
            logger.info("MessageLogController 정리 완료")
        except Exception as e:
            logger.error(f"MessageLogController 정리 실패: {e}")

    def __str__(self) -> str:
        return f"MessageLogController(auto_clear={self.auto_clear_messages})"

    def __repr__(self) -> str:
        return (
            f"MessageLogController(main_window={self.main_window}, max_logs={self.max_log_entries})"
        )
