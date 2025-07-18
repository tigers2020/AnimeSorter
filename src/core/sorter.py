"""
파일 정렬 시스템

비동기 파일 관리자를 사용하여 애니메이션 파일을 정리하고 이동하는 모듈입니다.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass

from .async_file_manager import AsyncFileManager, FileOperation
from ..utils.file_cleaner import FileCleaner, CleanResult
from ..utils.logger import get_logger
from ..exceptions import FileManagerError, FileCleanerError


@dataclass
class SortResult:
    """정렬 결과"""
    total_files: int
    processed_files: int
    failed_files: int
    errors: List[str]
    processing_time: float


class AnimeSorter:
    """애니메이션 파일 정렬기"""
    
    def __init__(self, max_workers: int = 4):
        """
        AnimeSorter 초기화
        
        Args:
            max_workers: 최대 워커 스레드 수
        """
        self.max_workers = max_workers
        self.logger = get_logger(__name__)
        self.file_cleaner = FileCleaner()
        
    async def sort_files(
        self,
        source_dir: Path,
        target_dir: Path,
        file_patterns: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> SortResult:
        """
        파일들을 정렬하여 이동
        
        Args:
            source_dir: 소스 디렉토리
            target_dir: 대상 디렉토리
            file_patterns: 처리할 파일 패턴 (예: ["*.mp4", "*.mkv"])
            progress_callback: 진행 상황 콜백 함수
            
        Returns:
            SortResult: 정렬 결과
        """
        import time
        start_time = time.time()
        
        try:
            # 파일 목록 수집
            files = await self._collect_files(source_dir, file_patterns)
            total_files = len(files)
            
            if total_files == 0:
                self.logger.info("처리할 파일이 없습니다.")
                return SortResult(
                    total_files=0,
                    processed_files=0,
                    failed_files=0,
                    errors=[],
                    processing_time=time.time() - start_time
                )
                
            self.logger.info(f"총 {total_files}개 파일을 처리합니다.")
            
            # 파일 작업 목록 생성
            operations = await self._create_file_operations(files, target_dir)
            
            # 비동기 파일 관리자로 처리
            async with AsyncFileManager(max_workers=self.max_workers) as file_manager:
                results = await file_manager.process_files_batch(operations, progress_callback)
                
            processing_time = time.time() - start_time
            
            self.logger.info(
                f"파일 정렬 완료: {results['completed']}/{results['total']} 성공, "
                f"처리 시간: {processing_time:.2f}초"
            )
            
            return SortResult(
                total_files=results['total'],
                processed_files=results['completed'],
                failed_files=results['failed'],
                errors=[],  # TODO: 실제 오류 메시지 수집
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"파일 정렬 중 오류 발생: {e}")
            raise FileManagerError(f"파일 정렬 실패: {str(e)}") from e
            
    async def _collect_files(
        self, 
        source_dir: Path, 
        file_patterns: Optional[List[str]] = None
    ) -> List[Path]:
        """처리할 파일 목록 수집"""
        if not source_dir.exists():
            raise FileManagerError(f"소스 디렉토리가 존재하지 않습니다: {source_dir}")
            
        if file_patterns is None:
            file_patterns = ["*.mp4", "*.mkv", "*.avi", "*.mov", "*.wmv"]
            
        files = []
        for pattern in file_patterns:
            files.extend(source_dir.rglob(pattern))
            
        return sorted(files)
        
    async def _create_file_operations(
        self, 
        files: List[Path], 
        target_dir: Path
    ) -> List[FileOperation]:
        """파일 작업 목록 생성"""
        operations = []
        
        for file_path in files:
            try:
                # 파일명 정제
                clean_result = self.file_cleaner.clean_filename(file_path)
                
                # 대상 경로 생성
                target_path = self._create_target_path(clean_result, target_dir, file_path)
                
                # 파일 작업 생성
                operation = FileOperation(
                    source=file_path,
                    target=target_path,
                    operation_type="move",
                    metadata={
                        "original_name": file_path.name,
                        "clean_title": clean_result.title,
                        "year": clean_result.year,
                        "season": clean_result.season,
                        "episode": clean_result.episode,
                        "is_movie": clean_result.is_movie
                    }
                )
                
                operations.append(operation)
                
            except FileCleanerError as e:
                self.logger.warning(f"파일명 정제 실패: {file_path}, 오류: {e}")
                # 정제 실패 시 원본 이름으로 이동
                target_path = target_dir / file_path.name
                operation = FileOperation(
                    source=file_path,
                    target=target_path,
                    operation_type="move",
                    metadata={"error": str(e)}
                )
                operations.append(operation)
                
        return operations
        
    def _create_target_path(self, clean_result: CleanResult, target_dir: Path, original_file: Path) -> Path:
        """대상 경로 생성"""
        # 기본 폴더명 생성
        if clean_result.year:
            folder_name = f"{clean_result.title} ({clean_result.year})"
        else:
            folder_name = clean_result.title
            
        # 시즌 정보 추가
        if clean_result.season > 1:
            folder_name += f" Season {clean_result.season}"
            
        # 안전한 폴더명으로 변환
        safe_folder_name = self._sanitize_filename(folder_name)
        
        # 대상 디렉토리 경로
        if clean_result.is_movie:
            # 영화: 직접 대상 디렉토리
            final_target_dir = target_dir / safe_folder_name
        else:
            # TV 시리즈: 시즌 폴더 추가
            season_folder = f"Season {clean_result.season:02d}"
            final_target_dir = target_dir / safe_folder_name / season_folder
            
        # 파일명 결정
        if clean_result.episode:
            # 에피소드 정보가 있는 경우
            episode_filename = f"S{clean_result.season:02d}E{clean_result.episode:02d}{original_file.suffix}"
        else:
            # 에피소드 정보가 없는 경우 원본 파일명 유지
            episode_filename = original_file.name
            
        return final_target_dir / episode_filename
        
    def _sanitize_filename(self, filename: str) -> str:
        """파일명에서 사용할 수 없는 문자 제거"""
        import re
        # 경로에 사용할 수 없는 문자 제거/대체
        invalid_chars = r'[\/:*?"<>|]'
        return re.sub(invalid_chars, '', filename)
        
    async def cleanup_source_directories(self, source_dir: Path) -> int:
        """소스 디렉토리의 빈 폴더 정리"""
        async with AsyncFileManager(max_workers=self.max_workers) as file_manager:
            cleaned_count = await file_manager.cleanup_empty_directories(source_dir)
            self.logger.info(f"빈 디렉토리 {cleaned_count}개 정리 완료")
            return cleaned_count


# 편의 함수
async def sort_anime_files(
    source_dir: str | Path,
    target_dir: str | Path,
    file_patterns: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> SortResult:
    """
    애니메이션 파일 정렬 편의 함수
    
    Args:
        source_dir: 소스 디렉토리 경로
        target_dir: 대상 디렉토리 경로
        file_patterns: 처리할 파일 패턴
        progress_callback: 진행 상황 콜백 함수
        
    Returns:
        SortResult: 정렬 결과
    """
    sorter = AnimeSorter()
    return await sorter.sort_files(
        Path(source_dir),
        Path(target_dir),
        file_patterns,
        progress_callback
    ) 