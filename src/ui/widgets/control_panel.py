from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton

class ControlPanel(QWidget):
    """컨트롤 패널 위젯"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 이동 버튼
        self.move_button = QPushButton("파일 이동")
        self.move_button.setToolTip("파일들을 지정된 위치로 이동합니다")
        self.move_button.setEnabled(False)
        
        # 취소 버튼 추가
        self.cancel_button = QPushButton("취소")
        self.cancel_button.setToolTip("진행 중인 작업을 취소합니다")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: 1px solid #dc3545;
                border-radius: 4px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
                border-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                border-color: #6c757d;
                color: #adb5bd;
            }
        """)
        
        # 레이아웃에 추가
        layout.addWidget(self.move_button)
        layout.addWidget(self.cancel_button)
        layout.addStretch()
        
    def set_processing_state(self, is_processing: bool):
        """처리 상태에 따라 버튼 활성화/비활성화"""
        self.move_button.setEnabled(not is_processing)
        self.cancel_button.setEnabled(is_processing)
        
        if is_processing:
            self.move_button.setText("처리 중...")
        else:
            self.move_button.setText("파일 이동") 