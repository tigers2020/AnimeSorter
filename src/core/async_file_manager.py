"""
비동기 파일 관리 시스템

aiofiles를 사용하여 파일 I/O를 비동기로 처리하는 모듈입니다.
"""

import os
import shutil
import asyncio
import aiofiles
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from src.utils.logger import get_logger
from src.exceptions import FileManagerError


@dataclass
class FileOperation:
    """파일 작업 정보"""
    source: Path
    target: Path
    operation_type: str  # "move", "copy", "delete"
    size: int = 0
    metadata: Optional[Dict[str, Any]] = None


class AsyncFileManager:
    """비동기 파일 관리자"""
    
    def __init__(self, max_workers: int = 4, chunk_size: int = 1024 * 1024):
        """
        AsyncFileManager 초기화
        
        Args:
            max_workers: 최대 워커 스레드 수
            chunk_size: 파일 복사 시 청크 크기 (바이트)
        """
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = get_logger(__name__)
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        self.executor.shutdown(wait=True)
        
    async def move_file(self, source: Path, target: Path, overwrite: bool = False) -> bool:
        """
        파일을 비동기로 이동
        
        Args:
            source: 원본 파일 경로
            target: 대상 파일 경로
            overwrite: 기존 파일 덮어쓰기 여부
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 대상 디렉토리 생성
            await self._ensure_directory(target.parent)
            
            # 파일 크기 확인
            file_size = await self._get_file_size(source)
            
            # 기존 파일 확인
            if target.exists() and not overwrite:
                raise FileManagerError(f"대상 파일이 이미 존재합니다: {target}")
                
            # 같은 드라이브인지 확인
            if await self._is_same_drive(source.parent, target.parent):
                # 같은 드라이브: os.rename 사용
                await self._move_file_same_drive(source, target)
            else:
                # 다른 드라이브: 복사 후 삭제
                await self._move_file_cross_drive(source, target)
                
            self.logger.info(f"파일 이동 완료: {source} -> {target}")
            return True
            
        except Exception as e:
            self.logger.error(f"파일 이동 실패: {source} -> {target}, 오류: {e}")
            raise FileManagerError(f"파일 이동 실패: {str(e)}") from e
            
    async def copy_file(self, source: Path, target: Path, overwrite: bool = False) -> bool:
        """
        파일을 비동기로 복사
        
        Args:
            source: 원본 파일 경로
            target: 대상 파일 경로
            overwrite: 기존 파일 덮어쓰기 여부
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 대상 디렉토리 생성
            await self._ensure_directory(target.parent)
            
            # 기존 파일 확인
            if target.exists() and not overwrite:
                raise FileManagerError(f"대상 파일이 이미 존재합니다: {target}")
                
            # 파일 복사
            await self._copy_file_async(source, target)
            
            self.logger.info(f"파일 복사 완료: {source} -> {target}")
            return True
            
        except Exception as e:
            self.logger.error(f"파일 복사 실패: {source} -> {target}, 오류: {e}")
            raise FileManagerError(f"파일 복사 실패: {str(e)}") from e
            
    async def delete_file(self, file_path: Path) -> bool:
        """
        파일을 비동기로 삭제
        
        Args:
            file_path: 삭제할 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        try:
            if not file_path.exists():
                self.logger.warning(f"삭제할 파일이 존재하지 않습니다: {file_path}")
                return False
                
            # 파일 삭제
            await self._delete_file_async(file_path)
            
            self.logger.info(f"파일 삭제 완료: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"파일 삭제 실패: {file_path}, 오류: {e}")
            raise FileManagerError(f"파일 삭제 실패: {str(e)}") from e
            
    async def process_files_batch(
        self, 
        operations: List[FileOperation], 
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, int]:
        """
        여러 파일 작업을 배치로 처리
        
        Args:
            operations: 파일 작업 목록
            progress_callback: 진행 상황 콜백 함수
            
        Returns:
            Dict[str, int]: 처리 결과 통계
        """
        total_operations = len(operations)
        completed = 0
        failed = 0
        results = {"total": total_operations, "completed": 0, "failed": 0}
        
        # 세마포어로 동시 작업 수 제한
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_operation(operation: FileOperation):
            nonlocal completed, failed
            
            async with semaphore:
                try:
                    if operation.operation_type == "move":
                        success = await self.move_file(operation.source, operation.target)
                    elif operation.operation_type == "copy":
                        success = await self.copy_file(operation.source, operation.target)
                    elif operation.operation_type == "delete":
                        success = await self.delete_file(operation.source)
                    else:
                        raise FileManagerError(f"지원하지 않는 작업 타입: {operation.operation_type}")
                        
                    if success:
                        completed += 1
                        results["completed"] = completed
                    else:
                        failed += 1
                        results["failed"] = failed
                        
                except Exception as e:
                    failed += 1
                    results["failed"] = failed
                    self.logger.error(f"작업 실패: {operation.operation_type} {operation.source}, 오류: {e}")
                    
                # 진행 상황 콜백
                if progress_callback:
                    current = completed + failed
                    progress_callback(current, total_operations, f"처리 중: {operation.source.name}")
                    
        # 모든 작업을 동시에 시작
        tasks = [process_operation(op) for op in operations]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
        
    async def _ensure_directory(self, directory: Path) -> None:
        """디렉토리 존재 확인 및 생성"""
        if not directory.exists():
            await self._create_directory_async(directory)
            
    async def _create_directory_async(self, directory: Path) -> None:
        """디렉토리를 비동기로 생성"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, directory.mkdir, True)
        
    async def _get_file_size(self, file_path: Path) -> int:
        """파일 크기를 비동기로 조회"""
        loop = asyncio.get_running_loop()
        stat = await loop.run_in_executor(self.executor, file_path.stat)
        return stat.st_size
        
    async def _is_same_drive(self, path1: Path, path2: Path) -> bool:
        """두 경로가 같은 드라이브에 있는지 확인"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor, 
            lambda: os.path.samefile(path1, path2)
        )
        
    async def _move_file_same_drive(self, source: Path, target: Path) -> None:
        """같은 드라이브 내 파일 이동"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, source.rename, target)
        
    async def _move_file_cross_drive(self, source: Path, target: Path) -> None:
        """다른 드라이브 간 파일 이동 (복사 후 삭제)"""
        # 파일 복사
        await self._copy_file_async(source, target)
        # 원본 파일 삭제
        await self._delete_file_async(source)
        
    async def _copy_file_async(self, source: Path, target: Path) -> None:
        """파일을 비동기로 복사"""
        async with aiofiles.open(source, 'rb') as src_file:
            async with aiofiles.open(target, 'wb') as dst_file:
                while True:
                    chunk = await src_file.read(self.chunk_size)
                    if not chunk:
                        break
                    await dst_file.write(chunk)
                    
    async def _delete_file_async(self, file_path: Path) -> None:
        """파일을 비동기로 삭제"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, file_path.unlink)
        
    async def get_directory_size(self, directory: Path) -> int:
        """디렉토리 크기를 비동기로 계산"""
        total_size = 0
        
        async def calculate_size(path: Path):
            nonlocal total_size
            try:
                if path.is_file():
                    size = await self._get_file_size(path)
                    total_size += size
                elif path.is_dir():
                    async for item in self._scan_directory_async(path):
                        await calculate_size(item)
            except Exception as e:
                self.logger.warning(f"크기 계산 중 오류: {path}, {e}")
                
        await calculate_size(directory)
        return total_size
        
    async def _scan_directory_async(self, directory: Path):
        """디렉토리를 비동기로 스캔"""
        loop = asyncio.get_running_loop()
        entries = await loop.run_in_executor(self.executor, list, directory.iterdir())
        
        for entry in entries:
            yield entry
            
    async def cleanup_empty_directories(self, directory: Path) -> int:
        """빈 디렉토리를 비동기로 정리"""
        cleaned_count = 0
        
        async def cleanup_recursive(path: Path):
            nonlocal cleaned_count
            try:
                if path.is_dir():
                    # 하위 디렉토리 먼저 정리
                    async for item in self._scan_directory_async(path):
                        if item.is_dir():
                            await cleanup_recursive(item)
                            
                    # 현재 디렉토리가 비어있는지 확인
                    entries = list(path.iterdir())
                    if not entries:
                        await self._delete_directory_async(path)
                        cleaned_count += 1
                        self.logger.info(f"빈 디렉토리 삭제: {path}")
            except Exception as e:
                self.logger.warning(f"디렉토리 정리 중 오류: {path}, {e}")
                
        await cleanup_recursive(directory)
        return cleaned_count
        
    async def _delete_directory_async(self, directory: Path) -> None:
        """디렉토리를 비동기로 삭제"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, directory.rmdir) 