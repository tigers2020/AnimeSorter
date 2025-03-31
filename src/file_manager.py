"""
파일 관리 모듈

파일 스캔, 분류 및 이동 관리
"""

import asyncio
import errno
import os
import re
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import aiofiles
import aiofiles.os
from loguru import logger

from src.exceptions import FileManagerError


# 지원하는 비디오 파일 확장자
VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v", ".flv"]

# 지원하는 자막 파일 확장자
SUBTITLE_EXTENSIONS = [".srt", ".ass", ".ssa", ".sub", ".idx", ".smi", ".vtt"]


class FileManager:
    """파일 스캔 및 이동 관리 클래스"""
    
    def __init__(
        self, 
        source_dir: str | Path, 
        target_dir: str | Path, 
        folder_template: str = "{title} ({year})",
        keep_original_name: bool = True,
        overwrite_existing: bool = False
    ):
        """
        FileManager 초기화
        
        Args:
            source_dir: 소스 디렉토리 경로
            target_dir: 대상 디렉토리 경로
            folder_template: 폴더 이름 템플릿
            keep_original_name: 원본 파일명 유지 여부
            overwrite_existing: 기존 파일 덮어쓰기 여부
        """
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.folder_template = folder_template
        self.keep_original_name = keep_original_name
        self.overwrite_existing = overwrite_existing
        
    async def scan_directory(self, directory: str | Path = None, recursive: bool = True) -> List[Path]:
        """
        디렉토리에서 비디오 파일 스캔
        
        Args:
            directory: 스캔할 디렉토리 (기본값: source_dir)
            recursive: 하위 디렉토리 포함 여부
            
        Returns:
            List[Path]: 발견된 비디오 파일 경로 목록
        """
        directory = Path(directory or self.source_dir)
        
        if not directory.exists():
            raise FileManagerError(f"디렉토리를 찾을 수 없습니다: {directory}")
            
        video_files = []
        
        # 비동기 파일 스캔을 위한 함수
        async def _scan_dir(path: Path):
            try:
                # 디렉토리 내용 나열
                entries = list(path.iterdir())
                
                # 비디오 파일 찾기
                for entry in entries:
                    if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                        video_files.append(entry)
                        
                    # 재귀적으로 하위 디렉토리 탐색
                    if recursive and entry.is_dir():
                        await _scan_dir(entry)
            except PermissionError:
                logger.warning(f"접근 권한 없음: {path}")
            except Exception as e:
                logger.error(f"디렉토리 스캔 오류 {path}: {e}")
                
        await _scan_dir(directory)
        return video_files
        
    def find_subtitle_files(self, video_file: Path) -> List[Path]:
        """
        비디오 파일과 연관된 자막 파일 찾기
        
        Args:
            video_file: 비디오 파일 경로
            
        Returns:
            List[Path]: 발견된 자막 파일 경로 목록
        """
        subtitle_files = []
        
        # 동일한 이름의 다른 확장자 파일 검색
        base_name = video_file.stem
        parent_dir = video_file.parent
        
        for ext in SUBTITLE_EXTENSIONS:
            # 기본 자막 (video.srt)
            subtitle_path = parent_dir / f"{base_name}{ext}"
            if subtitle_path.exists():
                subtitle_files.append(subtitle_path)
                
            # 언어 코드가 포함된 자막 (video.ko.srt, video.en.srt)
            for lang_code in ["ko", "en", "jp", "zh"]:
                lang_subtitle_path = parent_dir / f"{base_name}.{lang_code}{ext}"
                if lang_subtitle_path.exists():
                    subtitle_files.append(lang_subtitle_path)
                    
        return subtitle_files
        
    def get_target_path(self, metadata: Dict, source_file: Path) -> Path:
        """
        메타데이터를 기반으로 대상 경로 결정
        
        Args:
            metadata: 미디어 메타데이터
            source_file: 원본 파일 경로
            
        Returns:
            Path: 대상 파일 경로
        """
        # TV 시리즈와 영화 구분
        is_tv = metadata.get("media_type") == "tv" or "number_of_seasons" in metadata
        
        # 기본 정보 추출
        if is_tv:
            title = metadata.get("name", "Unknown TV Show")
            year = None
            if "first_air_date" in metadata and metadata["first_air_date"]:
                try:
                    year = int(metadata["first_air_date"].split("-")[0])
                except (ValueError, IndexError):
                    pass
        else:
            title = metadata.get("title", "Unknown Movie")
            year = None
            if "release_date" in metadata and metadata["release_date"]:
                try:
                    year = int(metadata["release_date"].split("-")[0])
                except (ValueError, IndexError):
                    pass
                    
        # 경로에 사용할 수 없는 문자 제거
        safe_title = self._sanitize_filename(title)
        
        # 폴더 템플릿 적용
        folder_name = self.folder_template.format(
            title=safe_title,
            year=year or "",
            type="TV Show" if is_tv else "Movie"
        ).strip()
        
        # 끝에 불필요한 괄호 제거
        folder_name = re.sub(r'\(\s*\)$', '', folder_name).strip()
        
        # 시즌 정보 추출 (TV 시리즈인 경우)
        season_folder = ""
        if is_tv and "season_number" in metadata:
            season_num = metadata.get("season_number", 1)
            season_folder = f"Season {season_num}"
            
        # 최종 대상 폴더 경로 구성
        if is_tv and season_folder:
            target_dir = self.target_dir / folder_name / season_folder
        else:
            target_dir = self.target_dir / folder_name
            
        # 파일명 결정
        if self.keep_original_name:
            # 원본 파일명 유지
            target_filename = source_file.name
        else:
            # 메타데이터 기반 파일명 생성
            if is_tv and "episode_number" in metadata:
                episode_num = metadata.get("episode_number", 1)
                episode_title = metadata.get("episode_name", "")
                
                if episode_title:
                    safe_episode_title = self._sanitize_filename(episode_title)
                    target_filename = f"S{metadata.get('season_number', 1):02d}E{episode_num:02d} - {safe_episode_title}{source_file.suffix}"
                else:
                    target_filename = f"S{metadata.get('season_number', 1):02d}E{episode_num:02d}{source_file.suffix}"
            else:
                target_filename = f"{safe_title}{source_file.suffix}"
                
        return target_dir / target_filename
        
    async def process_file(self, file_path: Path, metadata: Dict) -> bool:
        """
        파일 처리 (대상 경로 결정 및 파일 이동)
        
        Args:
            file_path: 처리할 파일 경로
            metadata: 미디어 메타데이터
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 대상 경로 결정
            target_path = self.get_target_path(metadata, file_path)
            
            # 디스크 공간 확인
            if not self.check_disk_space(file_path, target_path.parent):
                raise FileManagerError(f"대상 디스크에 충분한 공간이 없습니다: {target_path.parent}")
            
            # 대상 디렉토리 생성
            os.makedirs(target_path.parent, exist_ok=True)
            
            # 자막 파일 찾기
            subtitle_files = self.find_subtitle_files(file_path)
            
            # 파일 이동
            await self._move_file(file_path, target_path)
            
            # 자막 파일 이동
            for subtitle_file in subtitle_files:
                # 자막 파일의 대상 경로 결정
                if self.keep_original_name:
                    sub_target_path = target_path.parent / subtitle_file.name
                else:
                    # 비디오 파일명과 동일하게 하되 확장자만 변경
                    sub_target_path = target_path.with_suffix(subtitle_file.suffix)
                    
                    # 언어 코드가 포함된 경우 유지
                    if "." in subtitle_file.stem and not subtitle_file.stem.startswith(file_path.stem):
                        lang_part = subtitle_file.stem.replace(file_path.stem, "")
                        sub_target_path = target_path.with_suffix(f"{lang_part}{subtitle_file.suffix}")
                        
                await self._move_file(subtitle_file, sub_target_path)
                
            logger.info(f"파일 이동 완료: {file_path} -> {target_path}")
            return True
        except FileExistsError as e:
            logger.warning(str(e))
            return False
        except PermissionError:
            logger.error(f"파일 접근 권한 없음: {file_path}")
            return False
        except OSError as e:
            if e.errno == errno.ENOSPC:  # 디스크 공간 부족
                logger.error(f"파일 이동을 위한 디스크 공간 부족: {file_path}")
            elif e.errno == errno.ENAMETOOLONG:  # 경로 길이 초과
                logger.error(f"경로가 너무 깁니다: {file_path}")
            else:
                logger.error(f"파일 처리 중 OS 오류: {e}")
            return False
        except Exception as e:
            logger.error(f"파일 처리 중 예상치 못한 오류: {e}", exc_info=True)
            return False
            
    async def _move_file(self, source: Path, target: Path) -> None:
        """
        파일 이동 (비동기)
        
        Args:
            source: 원본 파일 경로
            target: 대상 파일 경로
            
        Raises:
            FileExistsError: 대상 파일이 이미 존재하고 덮어쓰기가 비활성화된 경우
        """
        # 대상 파일이 이미 존재하는지 확인
        if target.exists() and not self.overwrite_existing:
            raise FileExistsError(f"대상 파일이 이미 존재합니다: {target}")
            
        # 비동기 파일 이동
        loop = asyncio.get_running_loop()
        
        # 복사 후 원본 삭제 방식으로 이동 (다른 드라이브 간 이동 지원)
        if not await loop.run_in_executor(None, lambda: os.path.samefile(source.parent, target.parent)):
            # 파일 복사
            await loop.run_in_executor(None, shutil.copy2, source, target)
            # 원본 파일 삭제
            await loop.run_in_executor(None, os.unlink, source)
        else:
            # 같은 드라이브 내 이동
            await loop.run_in_executor(None, shutil.move, source, target)
            
    def check_disk_space(self, file_path: Path, target_dir: Path) -> bool:
        """
        파일 이동을 위한 충분한 디스크 공간이 있는지 확인
        
        Args:
            file_path: 이동할 파일 경로
            target_dir: 대상 디렉토리 경로
            
        Returns:
            bool: 충분한 공간이 있으면 True
        """
        try:
            # 파일 크기 확인
            file_size = file_path.stat().st_size
            
            # 대상 디스크 여유 공간 확인
            target_free_space = shutil.disk_usage(target_dir).free
            
            # 버퍼 공간 추가 (10MB)
            required_space = file_size + (10 * 1024 * 1024)
            
            return target_free_space >= required_space
        except Exception as e:
            logger.error(f"디스크 공간 확인 오류: {e}")
            # 오류 발생 시 기본적으로 진행
            return True
            
    async def process_files(
        self, 
        files: List[Path], 
        metadata_map: Dict[Path, Dict], 
        progress_callback: Optional[Callable[[int, int, Path], None]] = None
    ) -> Tuple[int, int]:
        """
        여러 파일 일괄 처리
        
        Args:
            files: 처리할 파일 목록
            metadata_map: 파일별 메타데이터 맵
            progress_callback: 진행 상황 콜백 함수 (완료 수, 전체 수, 현재 파일)
            
        Returns:
            Tuple[int, int]: (성공 수, 전체 수)
        """
        total = len(files)
        success_count = 0
        
        for i, file_path in enumerate(files):
            if file_path in metadata_map:
                if await self.process_file(file_path, metadata_map[file_path]):
                    success_count += 1
                    
            # 진행 상황 보고
            if progress_callback:
                progress_callback(i + 1, total, file_path)
                
        return success_count, total
            
    def _sanitize_filename(self, filename: str) -> str:
        """
        파일명에서 사용할 수 없는 문자 제거
        
        Args:
            filename: 원본 파일명
            
        Returns:
            str: 정제된 파일명
        """
        # 경로에 사용할 수 없는 문자 제거/대체
        invalid_chars = r'[\/:*?"<>|]'
        return re.sub(invalid_chars, '', filename) 