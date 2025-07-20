"""
스트리밍 파일 이터레이터

비디오 파일을 스트리밍 방식으로 순회하는 제너레이터를 제공합니다.
메모리 효율적인 파일 스캔을 위해 제너레이터 패턴을 사용합니다.
"""

import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator, Set

# 지원하는 비디오 파일 확장자
VIDEO_EXTENSIONS: Set[str] = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.flv', 
    '.webm', '.ts', '.mts', '.m2ts', '.3gp', '.ogv', '.rmvb',
    '.asf', '.divx', '.xvid', '.h264', '.h265', '.hevc'
}

logger = logging.getLogger(__name__)


async def iter_files(src_dir: Path, recursive: bool = True) -> AsyncGenerator[Path, None]:
    """
    비디오 파일을 스트리밍 방식으로 순회하는 제너레이터
    
    Args:
        src_dir: 스캔할 디렉토리 경로
        recursive: 하위 디렉토리 포함 여부 (기본값: True)
        
    Yields:
        Path: 비디오 파일 경로
        
    Raises:
        FileNotFoundError: 디렉토리가 존재하지 않는 경우
        PermissionError: 디렉토리 접근 권한이 없는 경우
    """
    if not src_dir.exists():
        raise FileNotFoundError(f"Directory does not exist: {src_dir}")
    
    if not src_dir.is_dir():
        raise ValueError(f"Path is not a directory: {src_dir}")
    
    logger.info(f"Starting file scan in: {src_dir}")
    logger.debug(f"Recursive mode: {recursive}")
    logger.debug(f"Supported video extensions: {VIDEO_EXTENSIONS}")
    
    try:
        if recursive:
            # 재귀적으로 모든 파일 스캔
            for file_path in src_dir.rglob("*"):
                if await _is_video_file(file_path):
                    yield file_path
                    # UI 응답성을 위한 짧은 지연
                    await asyncio.sleep(0.001)
        else:
            # 현재 디렉토리만 스캔
            for file_path in src_dir.iterdir():
                if file_path.is_file() and await _is_video_file(file_path):
                    yield file_path
                    await asyncio.sleep(0.001)
                    
    except PermissionError as e:
        logger.error(f"Permission denied accessing directory: {src_dir}")
        raise
    except Exception as e:
        logger.error(f"Error during file scanning: {e}")
        raise


async def _is_video_file(file_path: Path) -> bool:
    """
    파일이 비디오 파일인지 확인
    
    Args:
        file_path: 확인할 파일 경로
        
    Returns:
        bool: 비디오 파일 여부
    """
    if not file_path.is_file():
        return False
    
    # 파일 확장자 확인
    extension = file_path.suffix.lower()
    if extension not in VIDEO_EXTENSIONS:
        return False
    
    # 파일 크기 확인 (0바이트 파일 제외)
    try:
        if file_path.stat().st_size == 0:
            logger.debug(f"Skipping zero-size file: {file_path}")
            return False
    except (OSError, PermissionError) as e:
        logger.warning(f"Cannot access file {file_path}: {e}")
        return False
    
    return True


def get_video_extensions() -> Set[str]:
    """
    지원하는 비디오 파일 확장자 목록 반환
    
    Returns:
        Set[str]: 비디오 파일 확장자 집합
    """
    return VIDEO_EXTENSIONS.copy()


def add_video_extension(extension: str) -> None:
    """
    새로운 비디오 파일 확장자 추가
    
    Args:
        extension: 추가할 확장자 (예: '.xyz')
    """
    if not extension.startswith('.'):
        extension = '.' + extension
    
    VIDEO_EXTENSIONS.add(extension.lower())
    logger.info(f"Added video extension: {extension}")


def remove_video_extension(extension: str) -> None:
    """
    비디오 파일 확장자 제거
    
    Args:
        extension: 제거할 확장자 (예: '.xyz')
    """
    if not extension.startswith('.'):
        extension = '.' + extension
    
    VIDEO_EXTENSIONS.discard(extension.lower())
    logger.info(f"Removed video extension: {extension}")


async def count_video_files(src_dir: Path, recursive: bool = True) -> int:
    """
    디렉토리 내 비디오 파일 개수 계산
    
    Args:
        src_dir: 스캔할 디렉토리 경로
        recursive: 하위 디렉토리 포함 여부
        
    Returns:
        int: 비디오 파일 개수
    """
    count = 0
    async for _ in iter_files(src_dir, recursive):
        count += 1
    return count


async def get_video_files_list(src_dir: Path, recursive: bool = True) -> list[Path]:
    """
    비디오 파일 목록을 리스트로 반환 (메모리 사용량 주의)
    
    Args:
        src_dir: 스캔할 디렉토리 경로
        recursive: 하위 디렉토리 포함 여부
        
    Returns:
        list[Path]: 비디오 파일 경로 목록
    """
    files = []
    async for file_path in iter_files(src_dir, recursive):
        files.append(file_path)
    return files 