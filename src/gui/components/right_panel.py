"""
오른쪽 패널 컴포넌트
결과 뷰, 하단 액션, 로그 탭, 수동 매칭을 포함하는 오른쪽 패널을 관리합니다.
"""

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


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

        # 하단 액션
        bottom_actions = self.create_bottom_actions()
        layout.addWidget(bottom_actions)

        # 로그 탭
        log_tabs = self.create_log_tabs()
        layout.addWidget(log_tabs)

        # 크기 정책 설정
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def create_bottom_actions(self):
        """하단 액션 생성"""
        bottom = QWidget()
        layout = QHBoxLayout(bottom)
        layout.setContentsMargins(0, 0, 0, 0)

        # 표시 정보
        self.lblShowing = QLabel("")
        layout.addWidget(self.lblShowing)
        layout.addStretch(1)

        return bottom

    def create_log_tabs(self):
        """로그 탭 생성"""
        tab_widget = QTabWidget()

        # 활동 로그
        self.txtLog = QTextEdit()
        self.txtLog.setReadOnly(True)
        self.txtLog.setMinimumHeight(100)  # 최소 높이만 설정
        self.txtLog.setText(
            "애니메이션 파일 정리 시스템이 준비되었습니다.\n활동 로그가 여기에 표시됩니다."
        )

        # 오류 로그
        self.txtErr = QTextEdit()
        self.txtErr.setReadOnly(True)
        self.txtErr.setMinimumHeight(100)  # 최소 높이만 설정
        self.txtErr.setText("오류 로그가 여기에 표시됩니다.")

        tab_widget.addTab(self.txtLog, "📝 활동 로그")
        tab_widget.addTab(self.txtErr, "⚠️ 오류 로그")

        # 탭 위젯의 크기 정책 설정
        tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        return tab_widget

    def setup_connections(self):
        """시그널/슬롯 연결 설정"""
        # 현재는 연결할 시그널이 없음

    def update_showing_info(self, text: str):
        """표시 정보 업데이트"""
        self.lblShowing.setText(text)

    def add_activity_log(self, message: str):
        """활동 로그에 메시지 추가"""
        from PyQt5.QtCore import QDateTime

        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        log_entry = f"[{timestamp}] {message}"
        self.txtLog.append(log_entry)

        # 스크롤을 맨 아래로
        scrollbar = self.txtLog.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_error_log(self, message: str):
        """오류 로그에 메시지 추가"""
        from PyQt5.QtCore import QDateTime

        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        log_entry = f"[{timestamp}] {message}"
        self.txtErr.append(log_entry)

        # 스크롤을 맨 아래로
        scrollbar = self.txtErr.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_logs(self):
        """로그 초기화"""
        self.txtLog.clear()
        self.txtErr.clear()
