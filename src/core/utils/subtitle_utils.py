"""
자막 파일 관련 유틸리티 함수들
"""

import logging
from pathlib import Path

from src.core.constants import SUBTITLE_EXTENSIONS, VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)


def find_subtitle_files(video_file_path: str | Path) -> list[str]:
    """
    비디오 파일과 연관된 자막 파일들을 찾습니다.

    Args:
        video_file_path: 비디오 파일 경로

    Returns:
        연관된 자막 파일 경로들의 리스트
    """
    try:
        video_path = Path(video_file_path)
        video_name = video_path.stem
        video_dir = video_path.parent
        subtitle_files = []
        for file_path in video_dir.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in SUBTITLE_EXTENSIONS:
                continue
            subtitle_name = file_path.stem
            if subtitle_name == video_name:
                subtitle_files.append(str(file_path))
                continue
            if subtitle_name.startswith(f"{video_name}."):
                subtitle_files.append(str(file_path))
                continue
            if video_name in subtitle_name and subtitle_name != video_name:
                subtitle_files.append(str(file_path))
                continue
        logger.debug(f"자막 파일 검색: {video_file_path} -> {len(subtitle_files)}개 발견")
        return subtitle_files
    except Exception as e:
        logger.error(f"자막 파일 검색 실패: {video_file_path} - {e}")
        return []


def is_video_file(file_path: str | Path) -> bool:
    """
    파일이 비디오 파일인지 확인합니다.

    Args:
        file_path: 확인할 파일 경로

    Returns:
        비디오 파일이면 True, 아니면 False
    """
    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS


def is_subtitle_file(file_path: str | Path) -> bool:
    """
    파일이 자막 파일인지 확인합니다.

    Args:
        file_path: 확인할 파일 경로

    Returns:
        자막 파일이면 True, 아니면 False
    """
    return Path(file_path).suffix.lower() in SUBTITLE_EXTENSIONS


def get_subtitle_destination_path(
    video_source: str | Path, video_destination: str | Path, subtitle_source: str | Path
) -> Path:
    """
    자막 파일의 목적지 경로를 계산합니다.

    Args:
        video_source: 원본 비디오 파일 경로
        video_destination: 목적지 비디오 파일 경로
        subtitle_source: 원본 자막 파일 경로

    Returns:
        자막 파일의 목적지 경로
    """
    video_source = Path(video_source)
    video_destination = Path(video_destination)
    subtitle_source = Path(subtitle_source)
    video_dest_dir = video_destination.parent
    subtitle_name = subtitle_source.name
    return video_dest_dir / subtitle_name
