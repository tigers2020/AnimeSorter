import pytest
from src.anime_file_sorter.core.cleaner import guess_and_clean, clean_title

@pytest.mark.parametrize("filename,expected", [
    ("Bleach 11th TV [BDRip].mkv", "Bleach"),
    ("[SubsPlease] One Piece - 1071 [1080p].mkv", "One Piece"),
    ("Attack on Titan S04E01 (2020) [WEB-DL].mp4", "Attack On Titan"),
])
def test_clean_title(filename, expected):
    # clean_title은 아직 정규식 미구현이므로, guess_and_clean에서 clean_title 적용 후 결과 확인
    meta = guess_and_clean(filename)
    assert meta.get('clean_title', '').lower() == expected.lower() 