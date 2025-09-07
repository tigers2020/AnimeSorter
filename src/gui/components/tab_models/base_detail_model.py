"""
기본 상세 모델 클래스 - Phase 2.2 결과 뷰 컴포넌트 분할
탭별 상세 모델의 공통 기능을 제공하는 기본 클래스입니다.
"""

from typing import Any

from PyQt5.QtGui import QColor, QFont

from src.base_table_model import BaseTableModel


class BaseDetailModel(BaseTableModel):
    """기본 상세 모델 클래스"""

    # 컬럼 헤더 정의
    COLUMNS = ["파일명", "시즌", "에피소드", "해상도"]

    def _get_display_data(self, row_data: dict[str, Any], column: int) -> str:
        """표시 데이터 반환"""
        if column == 0:  # 파일명
            return row_data.get("filename", "파일명 없음")
        if column == 1:  # 시즌
            return str(row_data.get("season", "N/A"))
        if column == 2:  # 에피소드
            return str(row_data.get("episode", "N/A"))
        if column == 3:  # 해상도
            return row_data.get("resolution", "N/A")
        return ""

    def _get_tooltip_data(self, row_data: dict[str, Any], column: int) -> str:
        """툴팁 데이터 반환"""
        if column == 0:  # 파일명
            full_path = row_data.get("full_path", "경로 없음")
            file_size = row_data.get("file_size", "크기 알 수 없음")
            return f"파일명: {row_data.get('filename', '파일명 없음')}\n전체 경로: {full_path}\n파일 크기: {file_size}"
        if column == 1:  # 시즌
            return f"시즌: {row_data.get('season', 'N/A')}"
        if column == 2:  # 에피소드
            return f"에피소드: {row_data.get('episode', 'N/A')}"
        if column == 3:  # 해상도
            return f"해상도: {row_data.get('resolution', 'N/A')}"
        return ""

    def _get_font_role(self, row_data: dict[str, Any], column: int) -> QFont:
        """폰트 역할 반환"""
        font = QFont()
        if column == 0:  # 파일명은 굵게
            font.setBold(True)
        return font

    def _get_background_role(self, row_data: dict[str, Any], column: int) -> QColor:
        """배경 역할 반환"""
        # 상태에 따른 배경색 설정
        status = row_data.get("status", "unknown")
        if status == "error":
            return QColor(255, 200, 200)  # 연한 빨강
        if status == "warning":
            return QColor(255, 255, 200)  # 연한 노랑
        if status == "success":
            return QColor(200, 255, 200)  # 연한 초록
        return QColor(255, 255, 255)  # 기본 흰색

    def _get_foreground_role(self, row_data: dict[str, Any], column: int) -> QColor:
        """전경 역할 반환"""
        # 상태에 따른 텍스트색 설정
        status = row_data.get("status", "unknown")
        if status == "error":
            return QColor(200, 0, 0)  # 진한 빨강
        if status == "warning":
            return QColor(150, 150, 0)  # 진한 노랑
        if status == "success":
            return QColor(0, 150, 0)  # 진한 초록
        return QColor(0, 0, 0)  # 기본 검정

    def _get_column_key(self, column: int) -> str:
        """컬럼 인덱스에 해당하는 키 반환"""
        keys = ["filename", "season", "episode", "resolution"]
        if 0 <= column < len(keys):
            return keys[column]
        return ""

    def _get_sort_key(self, row_data: dict[str, Any], column: int) -> Any:
        """정렬 키 반환"""
        if column == 0:  # 파일명
            return row_data.get("filename", "").lower()
        if column == 1:  # 시즌
            season = row_data.get("season", 0)
            return int(season) if isinstance(season, int | str) and str(season).isdigit() else 0
        if column == 2:  # 에피소드
            episode = row_data.get("episode", 0)
            return int(episode) if isinstance(episode, int | str) and str(episode).isdigit() else 0
        if column == 3:  # 해상도
            return row_data.get("resolution", "")
        return ""

    def _matches_filter(self, item: dict[str, Any]) -> bool:
        """필터 매칭 확인 - 상세 모델 전용 로직"""
        if not self._current_filter:
            return True

        # 파일명, 시즌, 에피소드, 해상도에서 검색
        searchable_fields = [
            str(item.get("filename", "")),
            str(item.get("season", "")),
            str(item.get("episode", "")),
            str(item.get("resolution", "")),
        ]

        return any(self._current_filter in field.lower() for field in searchable_fields)
