from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QProgressBar, QLabel, QTextEdit, QGroupBox
)

class StatusPanel(QWidget):
    """상태 표시 패널"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """UI 요소 생성 및 배치"""
        layout = QVBoxLayout(self)
        
        # 그룹 박스
        self.group_box = QGroupBox("작업 상태")
        group_layout = QVBoxLayout(self.group_box)
        
        # 진행 상태 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        group_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("준비")
        group_layout.addWidget(self.status_label)
        
        # 벤치마크 정보 표시
        self.benchmark_label = QLabel("")
        group_layout.addWidget(self.benchmark_label)
        
        # 로그 영역
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        group_layout.addWidget(self.log_text)
        
        layout.addWidget(self.group_box)
        
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
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        ) 

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