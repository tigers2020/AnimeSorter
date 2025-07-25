from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QProgressBar, QLabel, QTextEdit, QGroupBox,
    QHBoxLayout, QFrame, QGridLayout, QScrollArea, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ErrorInfo:
    """에러 정보를 저장하는 데이터 클래스"""
    timestamp: datetime
    file_path: str
    error_type: str
    error_message: str
    step: str  # 에러가 발생한 단계 (파일명 정제, 메타데이터 검색, 파일 이동 등)

class ProgressStep(QFrame):
    """개별 진행 단계를 표시하는 위젯"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.is_active = False
        self.is_completed = False
        self._setup_ui()
        
    def _setup_ui(self):
        """UI 설정"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # 상태 아이콘 (텍스트로 대체)
        self.status_label = QLabel("⭕")  # ⭕ ⏳ ✅ ❌
        self.status_label.setFixedWidth(20)
        layout.addWidget(self.status_label)
        
        # 제목
        self.title_label = QLabel(self.title)
        layout.addWidget(self.title_label)
        
        # 진행률
        self.progress_label = QLabel("0%")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.progress_label)
        
        layout.addStretch()
        
        # 스타일 설정
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setObjectName("progress-step")
        self._update_style()
        
    def _update_style(self):
        """스타일 업데이트"""
        if self.is_completed:
            self.status_label.setText("✅")
        elif self.is_active:
            self.status_label.setText("⏳")
        else:
            self.status_label.setText("⭕")
            
    def set_active(self, active: bool):
        """활성 상태 설정"""
        self.is_active = active
        if active:
            self.is_completed = False
        self._update_style()
        
    def set_completed(self, completed: bool):
        """완료 상태 설정"""
        self.is_completed = completed
        if completed:
            self.is_active = False
        self._update_style()
        
    def set_progress(self, percent: int):
        """진행률 설정"""
        self.progress_label.setText(f"{percent}%")

class SpeedMeter(QWidget):
    """실시간 처리 속도 표시 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed_history: List[float] = []
        self.max_history = 10
        self._setup_ui()
        
    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 제목
        title = QLabel("처리 속도")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 속도 표시
        self.speed_label = QLabel("0 파일/초")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.speed_label)
        
        # 평균 속도
        self.avg_speed_label = QLabel("평균: 0 파일/초")
        self.avg_speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avg_speed_label.setFont(QFont("Arial", 8))
        layout.addWidget(self.avg_speed_label)
        
        self.setObjectName("speed-meter")
        
    def update_speed(self, files_per_second: float):
        """속도 업데이트"""
        self.speed_history.append(files_per_second)
        if len(self.speed_history) > self.max_history:
            self.speed_history.pop(0)
            
        # 현재 속도
        self.speed_label.setText(f"{files_per_second:.1f} 파일/초")
        
        # 평균 속도
        if self.speed_history:
            avg_speed = sum(self.speed_history) / len(self.speed_history)
            self.avg_speed_label.setText(f"평균: {avg_speed:.1f} 파일/초")

class ETAWidget(QWidget):
    """예상 완료 시간 표시 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_time = None
        self.total_items = 0
        self.completed_items = 0
        self._setup_ui()
        
    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 제목
        title = QLabel("예상 완료")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # ETA 표시
        self.eta_label = QLabel("--:--")
        self.eta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.eta_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.eta_label)
        
        # 경과 시간
        self.elapsed_label = QLabel("경과: 00:00")
        self.elapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.elapsed_label.setFont(QFont("Arial", 8))
        layout.addWidget(self.elapsed_label)
        
        self.setObjectName("eta-widget")
        
    def start_tracking(self, total_items: int):
        """추적 시작"""
        self.start_time = time.time()
        self.total_items = total_items
        self.completed_items = 0
        
    def update_progress(self, completed_items: int):
        """진행 상황 업데이트"""
        self.completed_items = completed_items
        
        if self.start_time and self.total_items > 0:
            elapsed = time.time() - self.start_time
            
            if completed_items > 0:
                # 평균 처리 시간 계산
                avg_time_per_item = elapsed / completed_items
                remaining_items = self.total_items - completed_items
                eta_seconds = remaining_items * avg_time_per_item
                
                # ETA 계산
                eta_time = time.time() + eta_seconds
                eta_str = time.strftime("%H:%M", time.localtime(eta_time))
                self.eta_label.setText(eta_str)
                
                # 경과 시간
                elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed))
                self.elapsed_label.setText(f"경과: {elapsed_str}")
            else:
                self.eta_label.setText("--:--")
                self.elapsed_label.setText("경과: 00:00")

class ErrorDisplayWidget(QWidget):
    """에러 메시지를 표시하는 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.errors: List[ErrorInfo] = []
        self._setup_ui()
        
    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 헤더
        header_layout = QHBoxLayout()
        
        # 에러 카운터
        self.error_count_label = QLabel("에러: 0개")
        self.error_count_label.setStyleSheet("color: red; font-weight: bold;")
        header_layout.addWidget(self.error_count_label)
        
        header_layout.addStretch()
        
        # 에러 목록 지우기 버튼
        self.clear_button = QPushButton("지우기")
        self.clear_button.clicked.connect(self.clear_errors)
        self.clear_button.setMaximumWidth(60)
        header_layout.addWidget(self.clear_button)
        
        layout.addLayout(header_layout)
        
        # 에러 목록 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(120)
        
        self.error_container = QWidget()
        self.error_layout = QVBoxLayout(self.error_container)
        self.error_layout.setSpacing(2)
        
        scroll_area.setWidget(self.error_container)
        layout.addWidget(scroll_area)
        
        self.setObjectName("error-display")
        
    def add_error(self, error_info: ErrorInfo):
        """에러 추가"""
        self.errors.append(error_info)
        self._update_error_display()
        
    def clear_errors(self):
        """에러 목록 지우기"""
        self.errors.clear()
        self._update_error_display()
        
    def _update_error_display(self):
        """에러 디스플레이 업데이트"""
        # 기존 에러 위젯들 제거
        for i in reversed(range(self.error_layout.count())):
            child = self.error_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
                
        # 에러 카운터 업데이트
        self.error_count_label.setText(f"에러: {len(self.errors)}개")
        
        # 최근 에러들 표시 (최대 10개)
        recent_errors = self.errors[-10:] if len(self.errors) > 10 else self.errors
        
        for error in recent_errors:
            error_widget = self._create_error_widget(error)
            self.error_layout.addWidget(error_widget)
            
        # 더 많은 에러가 있으면 표시
        if len(self.errors) > 10:
            more_label = QLabel(f"... 및 {len(self.errors) - 10}개 더")
            more_label.setStyleSheet("color: gray; font-style: italic;")
            self.error_layout.addWidget(more_label)
            
    def _create_error_widget(self, error: ErrorInfo) -> QWidget:
        """개별 에러 위젯 생성"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.StyledPanel)
        widget.setStyleSheet("""
            QFrame {
                background-color: #fff0f0;
                border: 1px solid #ffcccc;
                border-radius: 3px;
                padding: 2px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 3, 5, 3)
        
        # 에러 헤더
        header_layout = QHBoxLayout()
        
        # 타임스탬프
        time_str = error.timestamp.strftime("%H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: gray; font-size: 10px;")
        header_layout.addWidget(time_label)
        
        # 단계
        step_label = QLabel(f"[{error.step}]")
        step_label.setStyleSheet("color: #cc6600; font-weight: bold; font-size: 10px;")
        header_layout.addWidget(step_label)
        
        header_layout.addStretch()
        
        # 에러 타입
        type_label = QLabel(error.error_type)
        type_label.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
        header_layout.addWidget(type_label)
        
        layout.addLayout(header_layout)
        
        # 파일 경로
        file_label = QLabel(f"파일: {error.file_path}")
        file_label.setStyleSheet("color: #333; font-size: 10px;")
        file_label.setWordWrap(True)
        layout.addWidget(file_label)
        
        # 에러 메시지
        message_label = QLabel(error.error_message)
        message_label.setStyleSheet("color: #cc0000; font-size: 10px;")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        return widget

class StatusPanel(QWidget):
    """상태 표시 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress_steps: Dict[str, ProgressStep] = {}
        self.current_step = None
        self.speed_meter = SpeedMeter()
        self.eta_widget = ETAWidget()
        self.error_display = ErrorDisplayWidget()
        self._setup_ui()
        
    def _setup_ui(self):
        """UI 요소 생성 및 배치"""
        layout = QVBoxLayout(self)
        
        # 메인 진행률 그룹
        self.main_progress_group = QGroupBox("작업 진행률")
        main_layout = QVBoxLayout(self.main_progress_group)
        
        # 메인 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        main_layout.addWidget(self.progress_bar)
        
        # 상태 메시지
        self.status_label = QLabel("준비")
        main_layout.addWidget(self.status_label)
        
        layout.addWidget(self.main_progress_group)
        
        # 단계별 진행률 그룹
        self.steps_group = QGroupBox("작업 단계")
        steps_layout = QVBoxLayout(self.steps_group)
        
        # 진행 단계들
        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setSpacing(2)
        steps_layout.addWidget(self.steps_container)
        
        layout.addWidget(self.steps_group)
        
        # 통계 정보 그룹
        self.stats_group = QGroupBox("실시간 통계")
        stats_layout = QHBoxLayout(self.stats_group)
        
        # 속도계
        stats_layout.addWidget(self.speed_meter)
        
        # ETA 위젯
        stats_layout.addWidget(self.eta_widget)
        
        layout.addWidget(self.stats_group)
        
        # 벤치마크 정보
        self.benchmark_label = QLabel("")
        layout.addWidget(self.benchmark_label)
        
        # 에러 디스플레이 그룹
        self.error_group = QGroupBox("에러 목록")
        error_layout = QVBoxLayout(self.error_group)
        error_layout.addWidget(self.error_display)
        layout.addWidget(self.error_group)
        
        # 로그 영역
        self.log_group = QGroupBox("작업 로그")
        log_layout = QVBoxLayout(self.log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(self.log_group)
        
        # 초기 단계 설정
        self._setup_default_steps()
        
    def _setup_default_steps(self):
        """기본 작업 단계 설정"""
        steps = [
            "파일 스캔",
            "파일명 정제", 
            "메타데이터 검색",
            "파일 이동"
        ]
        
        for step in steps:
            step_widget = ProgressStep(step)
            self.progress_steps[step] = step_widget
            self.steps_layout.addWidget(step_widget)
        
    def set_progress(self, value: int, message: str = None):
        """진행률 및 상태 메시지 설정"""
        self.progress_bar.setValue(value)
        if message is not None:
            self.status_label.setText(message)
        
    def set_status(self, text: str):
        """상태 메시지 설정"""
        self.status_label.setText(text)
        
    def log_message(self, message: str):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
    def log_error(self, file_path: str, error_type: str, error_message: str, step: str):
        """에러 로그 추가"""
        error_info = ErrorInfo(
            timestamp=datetime.now(),
            file_path=file_path,
            error_type=error_type,
            error_message=error_message,
            step=step
        )
        
        # 에러 디스플레이에 추가
        self.error_display.add_error(error_info)
        
        # 일반 로그에도 추가
        self.log_message(f"❌ [{step}] {file_path}: {error_message}")
        
    def clear_errors(self):
        """에러 목록 지우기"""
        self.error_display.clear_errors()
        
    def get_error_count(self) -> int:
        """에러 개수 반환"""
        return len(self.error_display.errors)
        
    def set_step_active(self, step_name: str, active: bool = True):
        """특정 단계를 활성화/비활성화"""
        if step_name in self.progress_steps:
            self.progress_steps[step_name].set_active(active)
            if active:
                self.current_step = step_name
                
    def set_step_completed(self, step_name: str, completed: bool = True):
        """특정 단계를 완료 상태로 설정"""
        if step_name in self.progress_steps:
            self.progress_steps[step_name].set_completed(completed)
            
    def set_step_progress(self, step_name: str, percent: int):
        """특정 단계의 진행률 설정"""
        if step_name in self.progress_steps:
            self.progress_steps[step_name].set_progress(percent)
            
    def update_speed(self, files_per_second: float):
        """처리 속도 업데이트"""
        self.speed_meter.update_speed(files_per_second)
        
    def start_tracking(self, total_items: int):
        """ETA 추적 시작"""
        self.eta_widget.start_tracking(total_items)
        
    def update_progress(self, completed_items: int):
        """진행 상황 업데이트 (ETA 계산용)"""
        self.eta_widget.update_progress(completed_items)

    def set_benchmark_info(self, benchmark: dict):
        """
        벤치마크 정보(파일 수, 소요 시간, 속도 등)를 요약 표시
        Args:
            benchmark: {"total": int, "elapsed": float, "speed": float, ...}
        """
        if not benchmark:
            self.benchmark_label.setText("")
            return
        msg = f"[벤치마크] 파일 {benchmark.get('total','?')}개, {benchmark.get('elapsed','?'):.2f}s, {benchmark.get('speed','?'):.2f}개/초"
        self.benchmark_label.setText(msg) 