"""
스트리밍 파이프라인용 파일 정제기

기존 FileCleaner를 래핑하여 스트리밍 파이프라인에서 사용할 수 있도록 합니다.
비동기 처리와 에러 핸들링을 포함합니다.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.utils.file_cleaner import FileCleaner, CleanResult

logger = logging.getLogger(__name__)


class StreamingFileCleaner:
    """
    스트리밍 파이프라인용 파일 정제기
    
    기존 FileCleaner를 래핑하여 스트리밍 파이프라인에서 사용할 수 있도록 합니다.
    비동기 처리와 에러 핸들링을 포함합니다.
    """
    
    def __init__(self):
        """
        StreamingFileCleaner 초기화
        """
        self.logger = logging.getLogger(__name__)
        
    async def clean_filename(
        self, 
        file_path: Union[str, Path], 
        include_file_info: bool = False
    ) -> CleanResult:
        """
        파일명 정제 (비동기)
        
        Args:
            file_path: 파일 경로
            include_file_info: 파일 정보 포함 여부 (기본값: False)
            
        Returns:
            CleanResult: 정제된 결과
            
        Raises:
            Exception: 파일 정제 중 오류 발생 시
        """
        try:
            self.logger.debug(f"Cleaning filename: {file_path}")
            
            # FileCleaner의 정적 메서드를 직접 호출
            from src.utils.file_cleaner import FileCleaner
            
            # CPU 바운드 작업을 스레드 풀에서 실행
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, 
                FileCleaner.clean_filename, 
                file_path, 
                include_file_info
            )
            
            # 결과가 None인지 확인
            if result is None:
                self.logger.warning(f"FileCleaner returned None for: {file_path}")
                return self._create_fallback_result(file_path, "FileCleaner returned None")
            
            self.logger.debug(f"Successfully cleaned filename: {file_path} -> {result.title}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to clean filename: {file_path}", exc_info=True)
            # 오류 발생 시 기본 결과 반환
            return self._create_fallback_result(file_path, str(e))
    
    def clean_filename_sync(
        self, 
        file_path: Union[str, Path], 
        include_file_info: bool = False
    ) -> CleanResult:
        """
        파일명 정제 (동기)
        
        Args:
            file_path: 파일 경로
            include_file_info: 파일 정보 포함 여부 (기본값: False)
            
        Returns:
            CleanResult: 정제된 결과
        """
        try:
            self.logger.debug(f"Cleaning filename (sync): {file_path}")
            
            # FileCleaner의 정적 메서드를 직접 호출
            from src.utils.file_cleaner import FileCleaner
            
            result = FileCleaner.clean_filename(file_path, include_file_info=include_file_info)
            
            # 결과가 None인지 확인
            if result is None:
                self.logger.warning(f"FileCleaner returned None for: {file_path}")
                return self._create_fallback_result(file_path, "FileCleaner returned None")
            
            self.logger.debug(f"Successfully cleaned filename (sync): {file_path} -> {result.title}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to clean filename (sync): {file_path}", exc_info=True)
            return self._create_fallback_result(file_path, str(e))
    
    def _create_fallback_result(self, file_path: Union[str, Path], error_msg: str) -> CleanResult:
        """
        오류 발생 시 기본 결과 생성
        
        Args:
            file_path: 파일 경로
            error_msg: 오류 메시지
            
        Returns:
            CleanResult: 기본 결과
        """
        file_path = Path(file_path)
        
        # 파일명에서 확장자 제거
        title = file_path.stem
        
        # 기본 정제 (특수문자 제거, 공백 정리)
        title = self._basic_clean(title)
        
        return CleanResult(
            title=title,
            original_filename=str(file_path),
            is_anime=True,
            extra_info={
                'error': error_msg,
                'fallback': True
            }
        )
    
    def _basic_clean(self, title: str) -> str:
        """
        기본 정제 (특수문자 제거, 공백 정리)
        
        Args:
            title: 정제할 제목
            
        Returns:
            str: 정제된 제목
        """
        import re
        
        # 릴리즈 그룹 제거 [Group]
        title = re.sub(r'\[[^\]]*\]', '', title)
        
        # 해상도 정보 제거 (720p, 1080p 등)
        title = re.sub(r'\b(480p|720p|1080p|2160p|4K)\b', '', title, flags=re.IGNORECASE)
        
        # 코덱 정보 제거 (x264, x265 등)
        title = re.sub(r'\b(x264|x265|HEVC|AVC|FLAC|AAC)\b', '', title, flags=re.IGNORECASE)
        
        # 시즌/에피소드 패턴 제거
        title = re.sub(r'\bS\d{1,2}E\d{1,2}\b', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\b\d{1,2}x\d{1,2}\b', '', title)
        
        # 연도 패턴 제거 (괄호 안의 4자리 숫자)
        title = re.sub(r'\(\d{4}\)', '', title)
        title = re.sub(r'\[\d{4}\]', '', title)
        
        # 특수문자 제거 및 공백 정리
        title = re.sub(r'[^\w\s가-힣]', ' ', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    async def batch_clean(
        self, 
        file_paths: list[Union[str, Path]], 
        include_file_info: bool = False
    ) -> Dict[Path, CleanResult]:
        """
        여러 파일 일괄 정제 (비동기)
        
        Args:
            file_paths: 파일 경로 목록
            include_file_info: 파일 정보 포함 여부 (기본값: False)
            
        Returns:
            Dict[Path, CleanResult]: 파일별 정제 결과
        """
        results = {}
        
        # 동시에 처리할 수 있는 파일 수 제한
        semaphore = asyncio.Semaphore(10)
        
        async def clean_single_file(file_path: Union[str, Path]) -> tuple[Path, CleanResult]:
            async with semaphore:
                result = await self.clean_filename(file_path, include_file_info)
                return Path(file_path), result
        
        # 모든 파일을 동시에 처리
        tasks = [clean_single_file(fp) for fp in file_paths]
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 수집
        for result in completed_results:
            if isinstance(result, Exception):
                self.logger.error(f"Batch clean error: {result}")
                continue
                
            file_path, clean_result = result
            results[file_path] = clean_result
        
        return results
    
    def get_cleaner_stats(self) -> Dict[str, Any]:
        """
        정제기 통계 정보 반환
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        return {
            'cleaner_type': 'StreamingFileCleaner',
            'backend': 'FileCleaner (Anitopy + GuessIt)',
            'supports_async': True,
            'supports_batch': True
        } 