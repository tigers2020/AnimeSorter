"""
오른쪽 패널 컴포넌트
결과 뷰와 하단 액션을 포함하는 오른쪽 패널을 관리합니다.
로그 기능은 LogDock으로 이동되었습니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class RightPanel(QWidget):
    """메인 윈도우 오른쪽 패널"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        bottom_actions = self.create_bottom_actions()
        layout.addWidget(bottom_actions)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def create_bottom_actions(self):
        """하단 액션 생성"""
        bottom = QWidget()
        layout = QHBoxLayout(bottom)
        layout.setContentsMargins(0, 0, 0, 0)
        self.lblShowing = QLabel("")
        layout.addWidget(self.lblShowing)
        layout.addStretch(1)
        return bottom

    def setup_connections(self):
        """시그널/슬롯 연결 설정"""

    def update_showing_info(self, text: str):
        """표시 정보 업데이트"""
        self.lblShowing.setText(text)

    def add_activity_log(self, message: str):
        """활동 로그에 메시지 추가 (LogDock으로 리다이렉트)"""
        if hasattr(self.parent(), "log_dock") and self.parent().log_dock:
            self.parent().log_dock.add_activity_log(message)
        else:
            logger.info("[활동] %s", message)

    def add_error_log(self, message: str):
        """오류 로그에 메시지 추가 (LogDock으로 리다이렉트)"""
        if hasattr(self.parent(), "log_dock") and self.parent().log_dock:
            self.parent().log_dock.add_error_log(message)
        else:
            logger.info("[오류] %s", message)

    def clear_logs(self):
        """로그 초기화 (LogDock으로 리다이렉트)"""
        if hasattr(self.parent(), "log_dock") and self.parent().log_dock:
            self.parent().log_dock.clear_logs()
        else:
            logger.info("[로그] 로그 클리어 요청됨")
