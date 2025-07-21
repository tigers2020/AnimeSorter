"""
스트리밍 파이프라인 모듈

파일 하나씩 처리하여 파일명 정제 → 메타데이터 검색 → 파일 이동 → UI 업데이트를
순차적으로 수행하는 스트리밍 파이프라인을 구현합니다.
"""

import asyncio
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from src.utils.file_cleaner import FileCleaner, CleanResult
from src.plugin.tmdb.provider import TMDBProvider
from src.core.async_file_manager import AsyncFileManager, FileOperation
from src.utils.logger import get_logger

@dataclass
class ProcessingResult:
    """파일 처리 결과"""
    file_path: Path
    clean_result: Optional[CleanResult]
    metadata: Optional[Dict[str, Any]]
    target_path: Optional[Path]
    success: bool
    error_message: Optional[str] = None
    processing_time: float = 0.0

class StreamingPipeline:
    """스트리밍 파일 처리 파이프라인"""
    
    def __init__(self, 
                 tmdb_provider: TMDBProvider,
                 file_manager: AsyncFileManager,
                 target_directory: Path,
                 folder_template: str = "{title} ({year})"):
        """
        StreamingPipeline 초기화
        
        Args:
            tmdb_provider: TMDB 메타데이터 제공자
            file_manager: 비동기 파일 관리자
            target_directory: 대상 디렉토리
            folder_template: 폴더 이름 템플릿
        """
        self.tmdb_provider = tmdb_provider
        self.file_manager = file_manager
        self.target_directory = target_directory
        self.folder_template = folder_template
        self.logger = get_logger(__name__)
        
        # 현재 메타데이터 (포스터 다운로드용)
        self._current_metadata = None
        
    async def process_single_file(self, file_path: Path) -> ProcessingResult:
        """
        단일 파일 처리
        
        Args:
            file_path: 처리할 파일 경로
            
        Returns:
            ProcessingResult: 처리 결과
        """
        start_time = time.time()
        result = ProcessingResult(
            file_path=file_path,
            clean_result=None,
            metadata=None,
            target_path=None,
            success=False
        )
        
        try:
            # 파일 존재 확인
            if not file_path.exists():
                result.error_message = f"파일이 존재하지 않습니다: {file_path}"
                return result
                
            # 1단계: 파일명 정제
            self.logger.info(f"[스트리밍] 파일명 정제 시작: {file_path.name}")
            try:
                clean_result = await self._clean_filename(file_path)
                if not clean_result:
                    result.error_message = "파일명 정제 실패 - 정제 결과가 None입니다"
                    return result
                if not clean_result.title:
                    result.error_message = "파일명 정제 실패 - 제목을 추출할 수 없습니다"
                    return result
                result.clean_result = clean_result
                self.logger.info(f"[스트리밍] 파일명 정제 완료: {clean_result.title}")
            except Exception as e:
                result.error_message = f"파일명 정제 중 오류: {str(e)}"
                self.logger.error(f"파일명 정제 실패: {file_path} - {e}")
                return result
            
            # 2단계: 메타데이터 검색 (즉시 실행)
            self.logger.info(f"[스트리밍] 메타데이터 검색 시작: {clean_result.title}")
            try:
                metadata = await self._search_metadata(clean_result)
                result.metadata = metadata
                # 현재 메타데이터 설정 (포스터 다운로드용)
                self._set_current_metadata(metadata)
                if metadata:
                    self.logger.info(f"[스트리밍] 메타데이터 검색 완료: {metadata.get('title', 'Unknown')}")
                else:
                    self.logger.info(f"[스트리밍] 메타데이터 검색 실패: {clean_result.title} - 메타데이터를 찾을 수 없습니다")
            except Exception as e:
                result.error_message = f"메타데이터 검색 중 오류: {str(e)}"
                self.logger.error(f"메타데이터 검색 실패: {clean_result.title} - {e}")
                # 메타데이터 검색 실패는 치명적이지 않으므로 계속 진행
                result.metadata = None
                self._set_current_metadata(None)
            
            # 3단계: 대상 경로 결정
            try:
                target_path = self._determine_target_path(file_path, clean_result, metadata)
                if not target_path:
                    result.error_message = "대상 경로 결정 실패 - 경로를 생성할 수 없습니다"
                    return result
                result.target_path = target_path
                self.logger.info(f"[스트리밍] 대상 경로 결정 완료: {target_path}")
            except Exception as e:
                result.error_message = f"대상 경로 결정 중 오류: {str(e)}"
                self.logger.error(f"대상 경로 결정 실패: {file_path} - {e}")
                return result
            
            # 4단계: 파일 이동
            try:
                success = await self._move_file(file_path, target_path)
                result.success = success
                if not success:
                    result.error_message = "파일 이동 실패 - 이동 작업이 실패했습니다"
                    return result
                self.logger.info(f"[스트리밍] 파일 이동 완료: {file_path} -> {target_path}")
            except Exception as e:
                result.error_message = f"파일 이동 중 오류: {str(e)}"
                self.logger.error(f"파일 이동 실패: {file_path} -> {target_path} - {e}")
                return result
                
        except Exception as e:
            result.error_message = f"파일 처리 중 예상치 못한 오류: {str(e)}"
            self.logger.error(f"파일 처리 중 오류 발생: {file_path} - {e}")
            
        finally:
            result.processing_time = time.time() - start_time
            
        return result
        
    async def _clean_filename(self, file_path: Path) -> Optional[CleanResult]:
        """파일명 정제 (비동기 래퍼)"""
        try:
            # CPU 바운드 작업을 스레드 풀에서 실행
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as executor:
                clean_result = await loop.run_in_executor(
                    executor, 
                    FileCleaner.clean_filename, 
                    file_path
                )
            return clean_result
        except Exception as e:
            self.logger.error(f"파일명 정제 실패: {file_path} - {e}")
            return None
            
    async def _search_metadata(self, clean_result: CleanResult) -> Optional[Dict[str, Any]]:
        """메타데이터 검색"""
        try:
            if not clean_result.title:
                return None
                
            # TMDB 검색
            metadata = await self.tmdb_provider.search(
                clean_result.title, 
                clean_result.year
            )
            return metadata
        except Exception as e:
            self.logger.error(f"메타데이터 검색 실패: {clean_result.title} - {e}")
            return None
            
    def _determine_target_path(self, 
                             source_path: Path, 
                             clean_result: CleanResult, 
                             metadata: Optional[Dict[str, Any]]) -> Optional[Path]:
        """대상 경로 결정"""
        try:
            # 기본 정보 추출
            title = clean_result.title
            year = clean_result.year or metadata.get("year") if metadata else None
            
            # 폴더명 생성
            folder_name = self.folder_template.format(
                title=title,
                year=year or "",
                type="TV Show" if metadata and metadata.get("media_type") == "tv" else "Movie"
            ).strip()
            
            # 경로에 사용할 수 없는 문자 제거
            folder_name = self._sanitize_filename(folder_name)
            
            # 시즌 정보 추가 (TV 시리즈인 경우)
            if metadata and metadata.get("media_type") == "tv" and clean_result.season > 1:
                folder_name = f"{folder_name}/Season {clean_result.season}"
                
            # 최종 대상 경로
            target_dir = self.target_directory / folder_name
            target_path = target_dir / source_path.name
            
            return target_path
            
        except Exception as e:
            self.logger.error(f"대상 경로 결정 실패: {source_path} - {e}")
            return None
            
    async def _move_file(self, source_path: Path, target_path: Path) -> bool:
        """파일 이동"""
        try:
            # 대상 디렉토리 생성
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 이동 작업 생성
            operation = FileOperation(
                source=source_path,
                target=target_path,
                operation_type="move"
            )
            
            # 파일 이동 실행
            results = await self.file_manager.process_files_batch([operation])
            success = results.get("completed", 0) > 0
            
            if success:
                # 포스터 및 설명 파일 저장 (비동기로 실행, 결과 대기하지 않음)
                asyncio.create_task(self._save_metadata_files(target_path.parent))
                
            return success
            
        except Exception as e:
            self.logger.error(f"파일 이동 실패: {source_path} -> {target_path} - {e}")
            return False
            
    async def _save_metadata_files(self, target_dir: Path):
        """메타데이터 파일 저장 (포스터, 설명 등)"""
        try:
            # 현재 처리 중인 파일의 메타데이터 가져오기
            if not hasattr(self, '_current_metadata') or not self._current_metadata:
                return
                
            metadata = self._current_metadata
            
            # 1. 포스터 저장
            poster_path = metadata.get("poster_path")
            if poster_path:
                poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}"
                poster_file = target_dir / "poster.jpg"
                
                if not poster_file.exists():
                    try:
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            async with session.get(poster_url, timeout=10) as response:
                                if response.status == 200:
                                    content = await response.read()
                                    with open(poster_file, "wb") as f:
                                        f.write(content)
                                    self.logger.debug(f"포스터 저장 완료: {poster_file}")
                                else:
                                    self.logger.warning(f"포스터 다운로드 실패: {poster_url} ({response.status})")
                    except Exception as e:
                        self.logger.error(f"포스터 저장 오류: {poster_url} - {e}")
                        
            # 2. 설명 저장
            overview = metadata.get("overview")
            if overview:
                desc_file = target_dir / "description.txt"
                if not desc_file.exists():
                    try:
                        with open(desc_file, "w", encoding="utf-8") as f:
                            f.write(overview)
                        self.logger.debug(f"설명 저장 완료: {desc_file}")
                    except Exception as e:
                        self.logger.error(f"설명 저장 오류: {desc_file} - {e}")
                        
        except Exception as e:
            self.logger.error(f"메타데이터 파일 저장 중 오류: {e}")
            
    def _set_current_metadata(self, metadata: Optional[Dict[str, Any]]):
        """현재 처리 중인 파일의 메타데이터 설정"""
        self._current_metadata = metadata
        
    def _sanitize_filename(self, filename: str) -> str:
        """파일명에서 사용할 수 없는 문자 제거"""
        import re
        # 경로에 사용할 수 없는 문자 제거/대체
        invalid_chars = r'[\/:*?"<>|]'
        return re.sub(invalid_chars, '', filename) 