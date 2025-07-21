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
        
        # 이동 버튼만 남김
        self.move_button = QPushButton("파일 이동")
        self.move_button.setToolTip("파일들을 지정된 위치로 이동합니다")
        self.move_button.setEnabled(False)
        
        # 레이아웃에 추가
        layout.addWidget(self.move_button)
        layout.addStretch() 