"""
pytest 설정 파일

테스트에 필요한 공통 픽스처들을 정의합니다.
"""

import sys
from pathlib import Path

import pytest

# src 디렉토리를 Python 경로에 추가
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_file_path(tmp_path):
    """테스트용 샘플 파일 경로를 생성합니다."""
    test_file = tmp_path / "test_anime.mkv"
    test_file.write_text("test content")
    return test_file


@pytest.fixture
def sample_directory(tmp_path):
    """테스트용 샘플 디렉토리를 생성합니다."""
    anime_dir = tmp_path / "anime"
    anime_dir.mkdir()

    # 샘플 파일들 생성
    (anime_dir / "anime_01.mkv").write_text("episode 1")
    (anime_dir / "anime_02.mkv").write_text("episode 2")
    (anime_dir / "anime_01.srt").write_text("subtitle 1")

    return anime_dir
