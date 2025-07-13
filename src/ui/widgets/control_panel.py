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
        
        # 스캔 버튼
        self.scan_button = QPushButton("파일 스캔")
        self.scan_button.setToolTip("소스 폴더의 파일들을 스캔합니다")
        
        # 동기화 버튼
        self.sync_button = QPushButton("메타데이터 동기화")
        self.sync_button.setToolTip("TMDB API를 통해 파일 메타데이터를 가져옵니다")
        self.sync_button.setEnabled(False)
        
        # 이동 버튼
        self.move_button = QPushButton("파일 이동")
        self.move_button.setToolTip("파일들을 지정된 위치로 이동합니다")
        self.move_button.setEnabled(False)
        
        # 레이아웃에 추가
        layout.addWidget(self.scan_button)
        layout.addWidget(self.sync_button)
        layout.addWidget(self.move_button)
        layout.addStretch() 