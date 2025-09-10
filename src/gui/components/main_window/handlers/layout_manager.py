"""
MainWindow 레이아웃 매니저

MainWindow의 레이아웃 관련 메서드들을 관리하는 핸들러 클래스입니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDockWidget, QTextEdit


class MainWindowLayoutManager:
    """MainWindow의 레이아웃 관련 메서드들을 관리하는 핸들러"""

    def __init__(self, main_window):
        """
        MainWindowLayoutManager 초기화

        Args:
            main_window: MainWindow 인스턴스
        """
        self.main_window = main_window

    def update_layout_on_resize(self):
        """윈도우 크기 변경 시 레이아웃 업데이트"""
        try:
            if hasattr(self.main_window, "central_triple_layout"):
                self.main_window.central_triple_layout.adjust_layout_for_window_size()
                logger.info("✅ 레이아웃 크기 조정 완료")
            else:
                logger.info("⚠️ central_triple_layout이 초기화되지 않음")
        except Exception as e:
            logger.info("⚠️ 레이아웃 크기 조정 실패: %s", e)

    def setup_log_dock(self):
        """로그 도킹 위젯 설정"""
        try:
            self.main_window.log_dock = QDockWidget("로그", self.main_window)
            self.main_window.log_dock.setAllowedAreas(
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea
            )
            self.main_window.log_text_edit = QTextEdit()
            self.main_window.log_text_edit.setReadOnly(True)
            self.main_window.log_text_edit.setMaximumHeight(200)
            self.main_window.log_dock.setWidget(self.main_window.log_text_edit)
            self.main_window.addDockWidget(Qt.BottomDockWidgetArea, self.main_window.log_dock)
            self.main_window.log_dock.hide()
            logger.info("✅ 로그 도킹 위젯 설정 완료")
        except Exception as e:
            logger.info("⚠️ 로그 도킹 위젯 설정 실패: %s", e)

    def toggle_log_dock(self):
        """로그 도킹 위젯 토글"""
        try:
            if hasattr(self.main_window, "log_dock"):
                if self.main_window.log_dock.isVisible():
                    self.main_window.log_dock.hide()
                    logger.info("📝 로그 도킹 위젯 숨김")
                else:
                    self.main_window.log_dock.show()
                    logger.info("📝 로그 도킹 위젯 표시")
            else:
                logger.info("⚠️ log_dock이 초기화되지 않음")
        except Exception as e:
            logger.info("⚠️ 로그 도킹 위젯 토글 실패: %s", e)

    def show_log_dock(self):
        """로그 도킹 위젯 표시"""
        try:
            if hasattr(self.main_window, "log_dock"):
                self.main_window.log_dock.show()
                logger.info("📝 로그 도킹 위젯 표시")
            else:
                logger.info("⚠️ log_dock이 초기화되지 않음")
        except Exception as e:
            logger.info("⚠️ 로그 도킹 위젯 표시 실패: %s", e)

    def hide_log_dock(self):
        """로그 도킹 위젯 숨김"""
        try:
            if hasattr(self.main_window, "log_dock"):
                self.main_window.log_dock.hide()
                logger.info("📝 로그 도킹 위젯 숨김")
            else:
                logger.info("⚠️ log_dock이 초기화되지 않음")
        except Exception as e:
            logger.info("⚠️ 로그 도킹 위젯 숨김 실패: %s", e)

    def add_log_message(self, message: str, level: str = "INFO"):
        """로그 메시지 추가"""
        try:
            if hasattr(self.main_window, "log_text_edit"):
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                formatted_message = f"[{timestamp}] [{level}] {message}"
                self.main_window.log_text_edit.append(formatted_message)
                self.main_window.log_text_edit.verticalScrollBar().setValue(
                    self.main_window.log_text_edit.verticalScrollBar().maximum()
                )
            else:
                logger.info("⚠️ log_text_edit이 초기화되지 않음")
        except Exception as e:
            logger.info("⚠️ 로그 메시지 추가 실패: %s", e)

    def clear_log(self):
        """로그 내용 지우기"""
        try:
            if hasattr(self.main_window, "log_text_edit"):
                self.main_window.log_text_edit.clear()
                logger.info("🧹 로그 내용 지우기 완료")
            else:
                logger.info("⚠️ log_text_edit이 초기화되지 않음")
        except Exception as e:
            logger.info("⚠️ 로그 내용 지우기 실패: %s", e)
