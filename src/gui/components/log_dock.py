"""
로그 Dock 컴포넌트 - Phase 5 UI/UX 리팩토링
기존 로그 위젯을 Bottom Dock으로 이동하여 사용자 경험을 향상시킵니다.
"""

from pathlib import Path

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import (
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class LogDock(QDockWidget):
    """하단 로그 Dock 위젯"""

    def __init__(self, parent=None):
        super().__init__("📝 로그", parent)
        self.setObjectName("log_dock")  # objectName 설정
        self.init_ui()
        self.setup_dock_properties()
        self.setup_connections()

    def init_ui(self):
        """UI 초기화"""
        # 중앙 위젯 생성
        central_widget = QWidget()
        self.setWidget(central_widget)

        # 메인 레이아웃
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # 로그 탭 위젯
        self.log_tabs = self.create_log_tabs()
        layout.addWidget(self.log_tabs)

        # 하단 컨트롤 패널
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)

    def create_log_tabs(self):
        """로그 탭 생성"""
        tab_widget = QTabWidget()

        # 활동 로그
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMinimumHeight(120)
        self.txt_log.setMaximumHeight(200)
        self.txt_log.setText(
            "애니메이션 파일 정리 시스템이 준비되었습니다.\n활동 로그가 여기에 표시됩니다."
        )

        # 오류 로그
        self.txt_err = QTextEdit()
        self.txt_err.setReadOnly(True)
        self.txt_err.setMinimumHeight(120)
        self.txt_err.setMaximumHeight(200)
        self.txt_err.setText("오류 로그가 여기에 표시됩니다.")

        # 탭 추가
        tab_widget.addTab(self.txt_log, "📝 활동 로그")
        tab_widget.addTab(self.txt_err, "⚠️ 오류 로그")

        # 탭 위젯 크기 정책
        tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        return tab_widget

    def create_control_panel(self):
        """컨트롤 패널 생성"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 로그 통계 정보
        self.lbl_log_count = QLabel("활동: 0 | 오류: 0")
        # 스타일은 테마 시스템에서 관리
        layout.addWidget(self.lbl_log_count)

        layout.addStretch(1)

        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # 로그 클리어 버튼
        self.btn_clear_logs = QToolButton()
        self.btn_clear_logs.setToolTip("모든 로그 클리어")
        self.btn_clear_logs.setText("🗑️")
        # 스타일은 테마 시스템에서 관리
        layout.addWidget(self.btn_clear_logs)

        # 로그 내보내기 버튼
        self.btn_export_logs = QToolButton()
        self.btn_export_logs.setToolTip("로그 내보내기")
        self.btn_export_logs.setText("📤")
        # 스타일은 테마 시스템에서 관리
        layout.addWidget(self.btn_export_logs)

        return panel

    def setup_dock_properties(self):
        """Dock 속성 설정"""
        # 기본 위치: 하단
        self.setAllowedAreas(Qt.BottomDockWidgetArea)

        # Dock 크기 설정
        self.setMinimumHeight(150)
        self.setMaximumHeight(300)
        self.resize(800, 200)

        # Dock 기능 설정
        self.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )

        # 기본 상태: 접힘 (사용자가 필요할 때 펼침)
        self.setVisible(False)

        # Dock 제목 설정
        self.setWindowTitle("📝 로그")

    def setup_connections(self):
        """시그널/슬롯 연결"""
        self.btn_clear_logs.clicked.connect(self.clear_logs)
        self.btn_export_logs.clicked.connect(self.export_logs)

    def add_activity_log(self, message: str):
        """활동 로그에 메시지 추가"""
        from PyQt5.QtCore import QDateTime

        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        log_entry = f"[{timestamp}] {message}"
        self.txt_log.append(log_entry)

        # 스크롤을 맨 아래로
        scrollbar = self.txt_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # 로그 통계 업데이트
        self.update_log_stats()

    def add_error_log(self, message: str):
        """오류 로그에 메시지 추가"""
        from PyQt5.QtCore import QDateTime

        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        log_entry = f"[{timestamp}] {message}"
        self.txt_err.append(log_entry)

        # 스크롤을 맨 아래로
        scrollbar = self.txt_err.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # 로그 통계 업데이트
        self.update_log_stats()

    def clear_logs(self):
        """모든 로그 클리어"""
        self.txt_log.clear()
        self.txt_err.clear()

        # 초기 메시지 설정
        self.txt_log.setText(
            "애니메이션 파일 정리 시스템이 준비되었습니다.\n활동 로그가 여기에 표시됩니다."
        )
        self.txt_err.setText("오류 로그가 여기에 표시됩니다.")

        # 로그 통계 업데이트
        self.update_log_stats()

    def export_logs(self):
        """로그 내보내기"""

        from PyQt5.QtCore import QDateTime
        from PyQt5.QtWidgets import QFileDialog

        # 파일명 생성
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_hhmmss")
        default_filename = f"animesorter_logs_{timestamp}.txt"

        # 파일 저장 다이얼로그
        file_path, _ = QFileDialog.getSaveFileName(
            self, "로그 내보내기", default_filename, "텍스트 파일 (*.txt)"
        )

        if file_path:
            try:
                with Path(file_path).open("w", encoding="utf-8") as f:
                    f.write("=== AnimeSorter 로그 내보내기 ===\n")
                    f.write(
                        f"내보낸 시간: {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')}\n\n"
                    )

                    f.write("--- 활동 로그 ---\n")
                    f.write(self.txt_log.toPlainText())
                    f.write("\n\n")

                    f.write("--- 오류 로그 ---\n")
                    f.write(self.txt_err.toPlainText())

                # 성공 메시지
                self.add_activity_log(f"✅ 로그 내보내기 완료: {Path(file_path).name}")

            except Exception as e:
                self.add_error_log(f"❌ 로그 내보내기 실패: {str(e)}")

    def update_log_stats(self):
        """로그 통계 업데이트"""
        # 활동 로그 줄 수 계산
        activity_lines = len(self.txt_log.toPlainText().split("\n")) - 1
        error_lines = len(self.txt_err.toPlainText().split("\n")) - 1

        # 통계 표시 업데이트
        self.lbl_log_count.setText(f"활동: {activity_lines} | 오류: {error_lines}")

    def save_dock_state(self):
        """Dock 상태 저장"""
        try:
            settings = QSettings()
            settings.beginGroup("LogDock")

            # Dock 상태 저장
            settings.setValue("visible", self.isVisible())
            settings.setValue("floating", self.isFloating())
            settings.setValue("geometry", self.geometry())
            settings.setValue("dock_area", self.parent().dockWidgetArea(self))

            settings.endGroup()

        except Exception as e:
            print(f"❌ 로그 Dock 상태 저장 실패: {e}")

    def load_dock_state(self):
        """Dock 상태 로드"""
        try:
            settings = QSettings()
            settings.beginGroup("LogDock")

            # 저장된 상태 로드
            visible = settings.value("visible", False, type=bool)
            floating = settings.value("floating", False, type=bool)
            geometry = settings.value("geometry")
            dock_area = settings.value("dock_area", Qt.BottomDockWidgetArea, type=int)

            settings.endGroup()

            # 상태 적용
            if geometry:
                self.setGeometry(geometry)

            if floating:
                self.setFloating(True)

            # Dock 영역 설정
            if self.parent():
                self.parent().addDockWidget(Qt.DockWidgetArea(dock_area), self)

            # 가시성 설정
            self.setVisible(visible)

        except Exception as e:
            print(f"❌ 로그 Dock 상태 로드 실패: {e}")
            # 기본값으로 설정
            self.setVisible(False)

    def toggle_visibility(self):
        """가시성 토글"""
        self.setVisible(not self.isVisible())

        # 상태 저장
        self.save_dock_state()

    def show_log_dock(self):
        """로그 Dock 표시"""
        self.setVisible(True)
        self.raise_()
        self.activateWindow()

        # 상태 저장
        self.save_dock_state()

    def hide_log_dock(self):
        """로그 Dock 숨김"""
        self.setVisible(False)

        # 상태 저장
        self.save_dock_state()
