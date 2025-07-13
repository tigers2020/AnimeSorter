from pathlib import Path
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt

class FileListTable(QTableWidget):
    """파일 목록 테이블 위젯"""
    
    COLUMNS = [
        ("파일명", 250),
        ("파일 형식", 80),
        ("제목", 200),
        ("시즌", 60),
        ("에피소드", 80),
        ("장르", 100),
        ("포스터", 200),
        ("줄거리", 400),
        ("이동 위치", 200)
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.file_paths = []  # 파일 경로 저장
        
    def _setup_ui(self):
        """UI 초기화"""
        # 컬럼 설정
        self.setColumnCount(len(self.COLUMNS))
        headers = []
        for i, (name, width) in enumerate(self.COLUMNS):
            if i != 0:
                self.setColumnWidth(i, width)
            headers.append(name)
        self.setHorizontalHeaderLabels(headers)
        
        # 테이블 설정
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # stretch 모드 제거, 0번 컬럼도 Interactive로 (폭은 add_file에서만 관리)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.verticalHeader().setVisible(False)
        
    def clear_files(self):
        """파일 목록 초기화"""
        self.setRowCount(0)
        self.file_paths.clear()
        
    def add_file(self, file_path: Path):
        """
        파일 추가
        
        Args:
            file_path: 파일 경로
        """
        row = self.rowCount()
        self.insertRow(row)
        self.file_paths.append(file_path)
        
        # 파일명과 확장자만 초기 표시
        self.setItem(row, 0, QTableWidgetItem(file_path.name))
        self.setItem(row, 1, QTableWidgetItem(file_path.suffix[1:] if file_path.suffix else ""))
        
        # 나머지 컬럼은 빈 값으로 초기화
        for i in range(2, len(self.COLUMNS)):
            self.setItem(row, i, QTableWidgetItem(""))
            
        # 파일명 컬럼 너비를 가장 긴 파일명에 맞게 자동 조정
        max_len = max(len(self.item(r, 0).text()) for r in range(self.rowCount()))
        # 1자 ≈ 7px, 여유 12px, 최소 80, 최대 360
        new_width = max(80, min(360, int(max_len * 7 + 12)))
        self.setColumnWidth(0, new_width)
            
    def update_clean_info(self, row: int, clean_result):
        """
        정제된 정보로 행 업데이트
        
        Args:
            row: 행 인덱스
            clean_result: 정제 결과
        """
        self.setItem(row, 2, QTableWidgetItem(clean_result.title))
        self.setItem(row, 3, QTableWidgetItem(str(clean_result.season)))
        self.setItem(row, 4, QTableWidgetItem(str(clean_result.episode) if clean_result.episode else "")) 

    def update_metadata_info(self, row: int, metadata: dict):
        """
        TMDB 등 메타데이터로 행의 장르/포스터/줄거리/이동 위치 컬럼을 갱신
        Args:
            row: 행 인덱스
            metadata: TMDB 등에서 받은 메타데이터 dict
        """
        # 장르
        genres = metadata.get("genres")
        if isinstance(genres, list):
            genre_str = ", ".join([g["name"] if isinstance(g, dict) else str(g) for g in genres])
        else:
            genre_str = str(genres) if genres else ""
        self.setItem(row, 5, QTableWidgetItem(genre_str))
        # 포스터 (URL 텍스트)
        poster_path = metadata.get("poster_path")
        if poster_path:
            poster_url = f"https://image.tmdb.org/t/p/w185{poster_path}"
        else:
            poster_url = ""
        self.setItem(row, 6, QTableWidgetItem(poster_url))
        # 줄거리
        overview = metadata.get("overview") or ""
        self.setItem(row, 7, QTableWidgetItem(overview))
        # 이동 위치
        target_path = metadata.get("target_path") or ""
        self.setItem(row, 8, QTableWidgetItem(str(target_path))) 