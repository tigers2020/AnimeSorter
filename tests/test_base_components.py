#!/usr/bin/env python3
"""
베이스 컴포넌트 클래스들에 대한 단위 테스트
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))


class TestBaseTableModel:
    """BaseTableModel 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        from gui.components.tab_models.base_table_model import BaseTableModel

        # 직접 인스턴스화할 수 있지만 추상 메서드 호출 시 NotImplementedError 발생
        model = BaseTableModel()
        assert model is not None

        # 추상 메서드 호출 시 NotImplementedError 발생 확인
        with pytest.raises(NotImplementedError):
            model._get_display_data({}, 0)


class TestBaseDetailModel:
    """BaseDetailModel 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        from gui.components.tab_models.base_detail_model import BaseDetailModel

        model = BaseDetailModel()
        assert model is not None
        assert ["파일명", "시즌", "에피소드", "해상도"] == model.COLUMNS

    def test_display_data(self):
        """표시 데이터 반환 테스트"""
        from gui.components.tab_models.base_detail_model import BaseDetailModel

        model = BaseDetailModel()
        test_data = {"filename": "test.mp4", "season": 1, "episode": 12, "resolution": "1080p"}

        # 파일명 컬럼
        assert model._get_display_data(test_data, 0) == "test.mp4"
        # 시즌 컬럼
        assert model._get_display_data(test_data, 1) == "1"
        # 에피소드 컬럼
        assert model._get_display_data(test_data, 2) == "12"
        # 해상도 컬럼
        assert model._get_display_data(test_data, 3) == "1080p"

    def test_tooltip_data(self):
        """툴팁 데이터 반환 테스트"""
        from gui.components.tab_models.base_detail_model import BaseDetailModel

        model = BaseDetailModel()
        test_data = {
            "filename": "test.mp4",
            "full_path": "/path/to/test.mp4",
            "file_size": "1.2GB",
            "season": 1,
            "episode": 12,
            "resolution": "1080p",
        }

        tooltip = model._get_tooltip_data(test_data, 0)
        assert "test.mp4" in tooltip
        assert "/path/to/test.mp4" in tooltip
        assert "1.2GB" in tooltip

    def test_font_role(self):
        """폰트 역할 반환 테스트"""
        from gui.components.tab_models.base_detail_model import BaseDetailModel

        model = BaseDetailModel()
        test_data = {"filename": "test.mp4"}

        font = model._get_font_role(test_data, 0)
        assert font.bold() is True

        font = model._get_font_role(test_data, 1)
        assert font.bold() is False

    def test_background_role(self):
        """배경 역할 반환 테스트"""
        from gui.components.tab_models.base_detail_model import BaseDetailModel

        model = BaseDetailModel()

        # 성공 상태
        color = model._get_background_role({"status": "success"}, 0)
        assert color.red() == 200
        assert color.green() == 255
        assert color.blue() == 200

        # 에러 상태
        color = model._get_background_role({"status": "error"}, 0)
        assert color.red() == 255
        assert color.green() == 200
        assert color.blue() == 200

    def test_foreground_role(self):
        """전경 역할 반환 테스트"""
        from gui.components.tab_models.base_detail_model import BaseDetailModel

        model = BaseDetailModel()

        # 성공 상태
        color = model._get_foreground_role({"status": "success"}, 0)
        assert color.red() == 0
        assert color.green() == 150
        assert color.blue() == 0

        # 에러 상태
        color = model._get_foreground_role({"status": "error"}, 0)
        assert color.red() == 200
        assert color.green() == 0
        assert color.blue() == 0

    def test_column_key(self):
        """컬럼 키 반환 테스트"""
        from gui.components.tab_models.base_detail_model import BaseDetailModel

        model = BaseDetailModel()

        assert model._get_column_key(0) == "filename"
        assert model._get_column_key(1) == "season"
        assert model._get_column_key(2) == "episode"
        assert model._get_column_key(3) == "resolution"
        assert model._get_column_key(4) == ""

    def test_sort_key(self):
        """정렬 키 반환 테스트"""
        from gui.components.tab_models.base_detail_model import BaseDetailModel

        model = BaseDetailModel()
        test_data = {"filename": "test.mp4", "season": "1", "episode": "12", "resolution": "1080p"}

        # 파일명 정렬 키
        sort_key = model._get_sort_key(test_data, 0)
        assert sort_key == "test.mp4"

        # 시즌 정렬 키
        sort_key = model._get_sort_key(test_data, 1)
        assert sort_key == 1

        # 에피소드 정렬 키
        sort_key = model._get_sort_key(test_data, 2)
        assert sort_key == 12

    def test_filter_matching(self):
        """필터 매칭 테스트"""
        from gui.components.tab_models.base_detail_model import BaseDetailModel

        model = BaseDetailModel()
        test_data = {"filename": "test.mp4", "season": "1", "episode": "12", "resolution": "1080p"}

        # 필터 설정
        model._current_filter = "test"
        assert model._matches_filter(test_data) is True

        # 해상도로 검색
        model._current_filter = "1080"
        assert model._matches_filter(test_data) is True

        # 존재하지 않는 텍스트로 검색
        model._current_filter = "nonexistent"
        assert model._matches_filter(test_data) is False


class TestBaseGroupModel:
    """BaseGroupModel 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        from gui.components.tab_models.base_group_model import BaseGroupModel

        model = BaseGroupModel()
        assert model is not None
        assert [
            "제목",
            "최종 이동 경로",
            "시즌",
            "에피소드 수",
            "최고 해상도",
            "상태",
        ] == model.COLUMNS

    def test_display_data(self):
        """표시 데이터 반환 테스트"""
        from gui.components.tab_models.base_group_model import BaseGroupModel

        model = BaseGroupModel()
        test_data = {
            "title": "Test Anime",
            "final_path": "/path/to/anime",
            "season": 1,
            "episode_count": 12,
            "max_resolution": "1080p",
            "status": "completed",
        }

        # 제목 컬럼
        assert model._get_display_data(test_data, 0) == "Test Anime"
        # 최종 이동 경로 컬럼
        assert model._get_display_data(test_data, 1) == "/path/to/anime"
        # 시즌 컬럼
        assert model._get_display_data(test_data, 2) == "1"
        # 에피소드 수 컬럼
        assert model._get_display_data(test_data, 3) == "12"
        # 최고 해상도 컬럼
        assert model._get_display_data(test_data, 4) == "1080p"
        # 상태 컬럼
        assert model._get_display_data(test_data, 5) == "completed"

    def test_tooltip_data(self):
        """툴팁 데이터 반환 테스트"""
        from gui.components.tab_models.base_group_model import BaseGroupModel

        model = BaseGroupModel()
        test_data = {
            "title": "Test Anime",
            "original_title": "Test Anime Original",
            "final_path": "/path/to/anime",
            "season": 1,
            "episode_count": 12,
            "max_resolution": "1080p",
            "status": "completed",
        }

        tooltip = model._get_tooltip_data(test_data, 0)
        assert "Test Anime" in tooltip
        assert "Test Anime Original" in tooltip

    def test_background_role(self):
        """배경 역할 반환 테스트"""
        from gui.components.tab_models.base_group_model import BaseGroupModel

        model = BaseGroupModel()

        # 완료 상태
        color = model._get_background_role({"status": "completed"}, 0)
        assert color.red() == 200
        assert color.green() == 255
        assert color.blue() == 200

        # 충돌 상태
        color = model._get_background_role({"status": "conflict"}, 0)
        assert color.red() == 255
        assert color.green() == 200
        assert color.blue() == 200

    def test_foreground_role(self):
        """전경 역할 반환 테스트"""
        from gui.components.tab_models.base_group_model import BaseGroupModel

        model = BaseGroupModel()

        # 완료 상태
        color = model._get_foreground_role({"status": "completed"}, 0)
        assert color.red() == 0
        assert color.green() == 150
        assert color.blue() == 0

        # 충돌 상태
        color = model._get_foreground_role({"status": "conflict"}, 0)
        assert color.red() == 200
        assert color.green() == 0
        assert color.blue() == 0

    def test_column_key(self):
        """컬럼 키 반환 테스트"""
        from gui.components.tab_models.base_group_model import BaseGroupModel

        model = BaseGroupModel()

        assert model._get_column_key(0) == "title"
        assert model._get_column_key(1) == "final_path"
        assert model._get_column_key(2) == "season"
        assert model._get_column_key(3) == "episode_count"
        assert model._get_column_key(4) == "max_resolution"
        assert model._get_column_key(5) == "status"
        assert model._get_column_key(6) == ""

    def test_sort_key(self):
        """정렬 키 반환 테스트"""
        from gui.components.tab_models.base_group_model import BaseGroupModel

        model = BaseGroupModel()
        test_data = {
            "title": "Test Anime",
            "final_path": "/path/to/anime",
            "season": "1",
            "episode_count": "12",
            "max_resolution": "1080p",
            "status": "completed",
        }

        # 제목 정렬 키
        sort_key = model._get_sort_key(test_data, 0)
        assert sort_key == "test anime"

        # 시즌 정렬 키
        sort_key = model._get_sort_key(test_data, 2)
        assert sort_key == 1

        # 에피소드 수 정렬 키
        sort_key = model._get_sort_key(test_data, 3)
        assert sort_key == 12

    def test_filter_matching(self):
        """필터 매칭 테스트"""
        from gui.components.tab_models.base_group_model import BaseGroupModel

        model = BaseGroupModel()
        test_data = {
            "title": "Test Anime",
            "final_path": "/path/to/anime",
            "season": "1",
            "status": "completed",
        }

        # 제목으로 검색
        model._current_filter = "test"
        assert model._matches_filter(test_data) is True

        # 경로로 검색
        model._current_filter = "path"
        assert model._matches_filter(test_data) is True

        # 상태로 검색
        model._current_filter = "completed"
        assert model._matches_filter(test_data) is True

        # 존재하지 않는 텍스트로 검색
        model._current_filter = "nonexistent"
        assert model._matches_filter(test_data) is False


if __name__ == "__main__":
    pytest.main([__file__])
