"""
기본 그룹 모델 클래스 - Phase 2.2 결과 뷰 컴포넌트 분할
탭별 모델의 공통 기능을 제공하는 기본 클래스입니다.
"""

from typing import Any

from PyQt5.QtGui import QColor, QFont

from src.base_table_model import BaseTableModel


class BaseGroupModel(BaseTableModel):
    """기본 그룹 모델 클래스"""

    # 컬럼 헤더 정의
    COLUMNS = ["제목", "최종 이동 경로", "시즌", "에피소드 수", "최고 해상도", "상태"]

    def _get_display_data(self, row_data: dict[str, Any], column: int) -> str:
        """표시 데이터 반환"""
        if column == 0:  # 제목
            return row_data.get("title", "제목 없음")
        if column == 1:  # 최종 이동 경로
            return row_data.get("final_path", "경로 없음")
        if column == 2:  # 시즌
            return str(row_data.get("season", "N/A"))
        if column == 3:  # 에피소드 수
            return str(row_data.get("episode_count", 0))
        if column == 4:  # 최고 해상도
            return row_data.get("max_resolution", "N/A")
        if column == 5:  # 상태
            return row_data.get("status", "알 수 없음")
        return ""

    def _get_tooltip_data(self, row_data: dict[str, Any], column: int) -> str:
        """툴팁 데이터 반환"""
        if column == 0:  # 제목
            return f"제목: {row_data.get('title', '제목 없음')}\n원제: {row_data.get('original_title', 'N/A')}"
        if column == 1:  # 최종 이동 경로
            return f"최종 이동 경로: {row_data.get('final_path', '경로 없음')}"
        if column == 2:  # 시즌
            return f"시즌: {row_data.get('season', 'N/A')}"
        if column == 3:  # 에피소드 수
            return f"에피소드 수: {row_data.get('episode_count', 0)}"
        if column == 4:  # 최고 해상도
            return f"최고 해상도: {row_data.get('max_resolution', 'N/A')}"
        if column == 5:  # 상태
            return f"상태: {row_data.get('status', '알 수 없음')}"
        return ""

    def _get_font_role(self, row_data: dict[str, Any], column: int) -> QFont:
        """폰트 역할 반환"""
        font = QFont()
        if column == 0:  # 제목은 굵게
            font.setBold(True)
        return font

    def _get_background_role(self, row_data: dict[str, Any], column: int) -> QColor:
        """배경 역할 반환"""
        # 상태에 따른 배경색 설정
        status = row_data.get("status", "unknown")
        if status == "completed":
            return QColor(200, 255, 200)  # 연한 초록
        if status == "conflict":
            return QColor(255, 200, 200)  # 연한 빨강
        if status == "duplicate":
            return QColor(255, 255, 200)  # 연한 노랑
        if status == "unmatched":
            return QColor(200, 200, 255)  # 연한 파랑
        return QColor(255, 255, 255)  # 기본 흰색

    def _get_foreground_role(self, row_data: dict[str, Any], column: int) -> QColor:
        """전경 역할 반환"""
        # 상태에 따른 텍스트색 설정
        status = row_data.get("status", "unknown")
        if status == "completed":
            return QColor(0, 150, 0)  # 진한 초록
        if status == "conflict":
            return QColor(200, 0, 0)  # 진한 빨강
        if status == "duplicate":
            return QColor(150, 150, 0)  # 진한 노랑
        if status == "unmatched":
            return QColor(0, 0, 150)  # 진한 파랑
        return QColor(0, 0, 0)  # 기본 검정

    def _get_column_key(self, column: int) -> str:
        """컬럼 인덱스에 해당하는 키 반환"""
        keys = ["title", "final_path", "season", "episode_count", "max_resolution", "status"]
        if 0 <= column < len(keys):
            return keys[column]
        return ""

    def _get_sort_key(self, row_data: dict[str, Any], column: int) -> Any:
        """정렬 키 반환"""
        if column == 0:  # 제목
            return row_data.get("title", "").lower()
        if column == 1:  # 최종 이동 경로
            return row_data.get("final_path", "").lower()
        if column == 2:  # 시즌
            season = row_data.get("season", 0)
            return int(season) if isinstance(season, int | str) and str(season).isdigit() else 0
        if column == 3:  # 에피소드 수
            episode_count = row_data.get("episode_count", 0)
            return (
                int(episode_count)
                if isinstance(episode_count, int | str) and str(episode_count).isdigit()
                else 0
            )
        if column == 4:  # 최고 해상도
            return row_data.get("max_resolution", "")
        if column == 5:  # 상태
            return row_data.get("status", "")
        return ""

    def _matches_filter(self, item: dict[str, Any]) -> bool:
        """필터 매칭 확인 - 그룹 모델 전용 로직"""
        if not self._current_filter:
            return True

        # 제목, 경로, 시즌, 상태에서 검색
        searchable_fields = [
            str(item.get("title", "")),
            str(item.get("final_path", "")),
            str(item.get("season", "")),
            str(item.get("status", "")),
        ]

        return any(self._current_filter in field.lower() for field in searchable_fields)
