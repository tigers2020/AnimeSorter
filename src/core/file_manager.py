"""
파일 관리자

스트리밍 파이프라인에서 파일 이동, 자막 파일 처리, 오류 처리 및 재시도 메커니즘을 제공합니다.
"""

import asyncio
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# 지원하는 비디오 파일 확장자
VIDEO_EXTENSIONS = [
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v", ".flv", 
    ".webm", ".ts", ".mts", ".m2ts", ".vob", ".ogv", ".3gp",
    ".asf", ".rm", ".rmvb", ".divx", ".xvid", ".mpg", ".mpeg"
]

# 지원하는 자막 파일 확장자
SUBTITLE_EXTENSIONS = [
    ".srt", ".ass", ".ssa", ".sub", ".idx", ".smi", ".vtt",
    ".txt", ".sami", ".rt", ".stl", ".ttml", ".dfxp"
]


class FileManager:
    """
    파일 관리자
    
    파일 이동, 자막 파일 처리, 오류 처리 및 재시도 메커니즘을 제공합니다.
    """
    
    def __init__(
        self,
        overwrite_existing: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        FileManager 초기화
        
        Args:
            overwrite_existing: 기존 파일 덮어쓰기 여부 (기본값: False)
            max_retries: 최대 재시도 횟수 (기본값: 3)
            retry_delay: 재시도 간격 (초) (기본값: 1.0)
        """
        self.overwrite_existing = overwrite_existing
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(__name__)
        
    async def move_file(
        self, 
        source_path: Union[str, Path], 
        target_path: Union[str, Path]
    ) -> bool:
        """
        파일 이동 (비동기)
        
        Args:
            source_path: 원본 파일 경로
            target_path: 대상 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        source_path = Path(source_path)
        target_path = Path(target_path)
        
        # 대상 디렉토리 생성
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 자막 파일 찾기
        subtitle_files = self.find_subtitle_files(source_path)
        
        # 메인 파일 이동
        success = await self._move_single_file(source_path, target_path)
        
        if success:
            # 자막 파일들 이동
            for subtitle_file in subtitle_files:
                subtitle_target = self._get_subtitle_target_path(
                    subtitle_file, target_path
                )
                await self._move_single_file(subtitle_file, subtitle_target)
                
        return success
        
    async def _move_single_file(
        self, 
        source_path: Path, 
        target_path: Path
    ) -> bool:
        """
        단일 파일 이동 (재시도 메커니즘 포함)
        
        Args:
            source_path: 원본 파일 경로
            target_path: 대상 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                # 대상 파일이 이미 존재하는지 확인
                if target_path.exists() and not self.overwrite_existing:
                    # 파일명 충돌 해결
                    target_path = self._resolve_filename_conflict(target_path)
                    
                # 파일 이동
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._move_file_sync, source_path, target_path)
                
                self.logger.info(f"Successfully moved: {source_path.name} -> {target_path}")
                return True
                
            except FileExistsError as e:
                self.logger.warning(f"File already exists: {target_path}")
                return False
                
            except PermissionError as e:
                retries += 1
                last_error = e
                self.logger.warning(
                    f"Permission error moving {source_path.name} (attempt {retries}/{self.max_retries}): {e}"
                )
                
            except OSError as e:
                retries += 1
                last_error = e
                self.logger.warning(
                    f"OS error moving {source_path.name} (attempt {retries}/{self.max_retries}): {e}"
                )
                
            except Exception as e:
                retries += 1
                last_error = e
                self.logger.error(
                    f"Unexpected error moving {source_path.name} (attempt {retries}/{self.max_retries}): {e}"
                )
                
            if retries < self.max_retries:
                # 지수 백오프
                wait_time = self.retry_delay * (2 ** (retries - 1))
                self.logger.info(f"Retrying in {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
                
        # 모든 재시도 실패
        self.logger.error(f"Failed to move {source_path.name} after {self.max_retries} attempts: {last_error}")
        return False
        
    def _move_file_sync(self, source_path: Path, target_path: Path) -> None:
        """
        동기 파일 이동 (스레드 풀에서 실행)
        
        Args:
            source_path: 원본 파일 경로
            target_path: 대상 파일 경로
            
        Raises:
            FileExistsError: 대상 파일이 이미 존재하고 덮어쓰기가 비활성화된 경우
            PermissionError: 권한 오류
            OSError: 기타 OS 오류
        """
        # 대상 파일이 이미 존재하는지 확인
        if target_path.exists() and not self.overwrite_existing:
            raise FileExistsError(f"Target file already exists: {target_path}")
            
        # shutil.move 사용 (크로스 디바이스 이동 지원)
        shutil.move(str(source_path), str(target_path))
        
    def find_subtitle_files(self, video_file: Path) -> List[Path]:
        """
        비디오 파일과 연관된 자막 파일 찾기
        
        Args:
            video_file: 비디오 파일 경로
            
        Returns:
            List[Path]: 발견된 자막 파일 경로 목록
        """
        subtitle_files = []
        base_name = video_file.stem
        parent_dir = video_file.parent
        
        for ext in SUBTITLE_EXTENSIONS:
            # 기본 자막 (video.srt)
            subtitle_path = parent_dir / f"{base_name}{ext}"
            if subtitle_path.exists():
                subtitle_files.append(subtitle_path)
                
            # 언어 코드가 포함된 자막 (video.ko.srt, video.en.srt)
            for lang_code in ["ko", "en", "jp", "zh", "kr"]:
                lang_subtitle_path = parent_dir / f"{base_name}.{lang_code}{ext}"
                if lang_subtitle_path.exists():
                    subtitle_files.append(lang_subtitle_path)
                    
        return subtitle_files
        
    def _get_subtitle_target_path(self, subtitle_file: Path, video_target: Path) -> Path:
        """
        자막 파일의 대상 경로 결정
        
        Args:
            subtitle_file: 자막 파일 경로
            video_target: 비디오 파일 대상 경로
            
        Returns:
            Path: 자막 파일 대상 경로
        """
        # 언어 코드가 포함된 경우 유지
        if "." in subtitle_file.stem:
            # video.ko.srt -> video_target.ko.srt
            lang_part = subtitle_file.suffixes[-2] if len(subtitle_file.suffixes) > 1 else ""
            if lang_part.startswith(".") and lang_part[1:] in ["ko", "en", "jp", "zh", "kr"]:
                return video_target.with_suffix(f"{lang_part}{subtitle_file.suffix}")
                
        # 기본 자막 (video.srt -> video_target.srt)
        return video_target.with_suffix(subtitle_file.suffix)
        
    def _resolve_filename_conflict(self, target_path: Path) -> Path:
        """
        파일명 충돌 해결
        
        Args:
            target_path: 원본 대상 경로
            
        Returns:
            Path: 충돌이 해결된 대상 경로
        """
        counter = 1
        original_stem = target_path.stem
        original_suffix = target_path.suffix
        
        while target_path.exists():
            new_name = f"{original_stem} ({counter}){original_suffix}"
            target_path = target_path.parent / new_name
            counter += 1
            
        return target_path
        
    async def check_disk_space(self, source_path: Path, target_dir: Path) -> bool:
        """
        파일 이동을 위한 충분한 디스크 공간이 있는지 확인
        
        Args:
            source_path: 이동할 파일 경로
            target_dir: 대상 디렉토리 경로
            
        Returns:
            bool: 충분한 공간이 있으면 True
        """
        try:
            # 파일 크기 확인
            file_size = source_path.stat().st_size
            
            # 대상 디스크 여유 공간 확인
            loop = asyncio.get_running_loop()
            
            def _check_space():
                target_free_space = shutil.disk_usage(target_dir).free
                # 버퍼 공간 추가 (10MB)
                required_space = file_size + (10 * 1024 * 1024)
                return target_free_space >= required_space
                
            return await loop.run_in_executor(None, _check_space)
            
        except Exception as e:
            self.logger.error(f"Error checking disk space: {e}")
            # 오류 발생 시 기본적으로 진행
            return True
            
    async def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        파일 정보 조회
        
        Args:
            file_path: 파일 경로
            
        Returns:
            dict: 파일 정보
        """
        try:
            loop = asyncio.get_running_loop()
            
            def _get_info():
                stat = file_path.stat()
                return {
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "created": stat.st_ctime,
                    "is_file": file_path.is_file(),
                    "is_dir": file_path.is_dir(),
                    "exists": file_path.exists()
                }
                
            return await loop.run_in_executor(None, _get_info)
            
        except Exception as e:
            self.logger.error(f"Error getting file info for {file_path}: {e}")
            return {}
            
    def is_video_file(self, file_path: Path) -> bool:
        """
        비디오 파일 여부 확인
        
        Args:
            file_path: 파일 경로
            
        Returns:
            bool: 비디오 파일이면 True
        """
        return file_path.suffix.lower() in VIDEO_EXTENSIONS
        
    def is_subtitle_file(self, file_path: Path) -> bool:
        """
        자막 파일 여부 확인
        
        Args:
            file_path: 파일 경로
            
        Returns:
            bool: 자막 파일이면 True
        """
        return file_path.suffix.lower() in SUBTITLE_EXTENSIONS 