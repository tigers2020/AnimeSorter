"""
오른쪽 패널 컴포넌트
결과 뷰와 하단 액션을 포함하는 오른쪽 패널을 관리합니다.
로그 기능은 LogDock으로 이동되었습니다.
"""

from PyQt5.QtWidgets import (QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout,
                             QWidget)


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

        # 로그 탭은 LogDock으로 이동되었으므로 제거
        # 이제 ResultsView가 이 공간을 사용합니다

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

    def setup_connections(self):
        """시그널/슬롯 연결 설정"""
        # 현재는 연결할 시그널이 없음

    def update_showing_info(self, text: str):
        """표시 정보 업데이트"""
        self.lblShowing.setText(text)

    # 로그 관련 메서드들은 LogDock으로 이동되었습니다
    # 기존 코드와의 호환성을 위해 빈 메서드로 유지
    def add_activity_log(self, message: str):
        """활동 로그에 메시지 추가 (LogDock으로 리다이렉트)"""
        # MainWindow에서 LogDock으로 리다이렉트하도록 처리
        if hasattr(self.parent(), "log_dock") and self.parent().log_dock:
            self.parent().log_dock.add_activity_log(message)
        else:
            # 폴백: 콘솔에 출력
            print(f"[활동] {message}")

    def add_error_log(self, message: str):
        """오류 로그에 메시지 추가 (LogDock으로 리다이렉트)"""
        # MainWindow에서 LogDock으로 리다이렉트하도록 처리
        if hasattr(self.parent(), "log_dock") and self.parent().log_dock:
            self.parent().log_dock.add_error_log(message)
        else:
            # 폴백: 콘솔에 출력
            print(f"[오류] {message}")

    def clear_logs(self):
        """로그 초기화 (LogDock으로 리다이렉트)"""
        # MainWindow에서 LogDock으로 리다이렉트하도록 처리
        if hasattr(self.parent(), "log_dock") and self.parent().log_dock:
            self.parent().log_dock.clear_logs()
        else:
            # 폴백: 콘솔에 출력
            print("[로그] 로그 클리어 요청됨")
