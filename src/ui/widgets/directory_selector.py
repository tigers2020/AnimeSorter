from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
)

class DirectorySelector(QWidget):
    """디렉토리 선택 위젯"""
    
    def __init__(self, label: str, parent=None, is_target=False, source_selector=None):
        """
        Args:
            label: 레이블 텍스트
            parent: 부모 위젯
            is_target: 대상 폴더 선택기 여부
            source_selector: 소스 폴더 선택기 참조
        """
        super().__init__(parent)
        self.label_text = label
        self.is_target = is_target
        self.source_selector = source_selector
        self._setup_ui()
        self._create_connections()
        
    def _setup_ui(self):
        """UI 요소 생성 및 배치"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(self.label_text)
        self.path_edit = QLineEdit()
        self.browse_button = QPushButton("찾아보기...")
        
        layout.addWidget(self.label)
        layout.addWidget(self.path_edit)
        layout.addWidget(self.browse_button)
        
    def _create_connections(self):
        """시그널-슬롯 연결"""
        self.browse_button.clicked.connect(self._select_directory)
        
    def _select_directory(self):
        """디렉토리 선택 대화상자"""
        dir_path = QFileDialog.getExistingDirectory(
            self, f"{self.label_text} 선택",
            self.path_edit.text() or str(Path.home())
        )
        if dir_path:
            self.path_edit.setText(dir_path)
            # 소스 폴더가 선택되었을 때 대상 폴더 자동 설정
            if not self.is_target and self.parent():
                source_path = Path(dir_path)
                target_path = source_path.parent / "target"
                # MainWindow를 통해 target_selector 찾기
                main_window = self.window()
                if hasattr(main_window, 'target_selector'):
                    main_window.target_selector.set_path(str(target_path))
            
    def get_path(self) -> str:
        """선택된 경로 반환"""
        return self.path_edit.text()
        
    def set_path(self, path: str):
        """경로 설정"""
        self.path_edit.setText(path) 