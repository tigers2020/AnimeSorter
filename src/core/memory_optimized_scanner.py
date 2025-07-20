"""
메모리 최적화 파일 스캐너

제너레이터 패턴을 사용하여 대용량 파일 목록을 메모리 효율적으로 처리하는 모듈입니다.
"""

import os
import asyncio
from pathlib import Path
from typing import Generator, AsyncGenerator, List, Set, Optional, Callable
from dataclasses import dataclass
import psutil
import gc

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.logger import get_logger
from exceptions import FileManagerError


@dataclass
class ScanResult:
    """스캔 결과"""
    file_path: Path
    file_size: int
    file_type: str  # "video", "subtitle", "other"
    metadata: Optional[dict] = None


class MemoryOptimizedScanner:
    """메모리 최적화 파일 스캐너"""
    
    def __init__(self, 
                 video_extensions: Optional[Set[str]] = None,
                 subtitle_extensions: Optional[Set[str]] = None,
                 max_memory_usage: float = 0.8,  # 최대 메모리 사용률 (80%)
                 batch_size: int = 1000):
        """
        MemoryOptimizedScanner 초기화
        
        Args:
            video_extensions: 비디오 파일 확장자 집합
            subtitle_extensions: 자막 파일 확장자 집합
            max_memory_usage: 최대 메모리 사용률 (0.0-1.0)
            batch_size: 배치 처리 크기
        """
        self.video_extensions = video_extensions or {
            '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.flv', '.webm'
        }
        self.subtitle_extensions = subtitle_extensions or {
            '.srt', '.ass', '.ssa', '.sub', '.idx', '.smi', '.vtt'
        }
        self.max_memory_usage = max_memory_usage
        self.batch_size = batch_size
        self.logger = get_logger(__name__)
        
    def scan_directory_generator(self, 
                               directory: Path, 
                               recursive: bool = True,
                               progress_callback: Optional[Callable[[int, str], None]] = None) -> Generator[ScanResult, None, None]:
        """
        디렉토리를 제너레이터로 스캔 (메모리 효율적)
        
        Args:
            directory: 스캔할 디렉토리
            recursive: 하위 디렉토리 포함 여부
            progress_callback: 진행 상황 콜백
            
        Yields:
            ScanResult: 파일 스캔 결과
        """
        if not directory.exists():
            raise FileManagerError(f"디렉토리가 존재하지 않습니다: {directory}")
            
        processed_count = 0
        
        try:
            # os.scandir()를 사용한 최적화된 스캔
            stack = [directory]
            
            while stack:
                # 메모리 사용량 확인
                if self._check_memory_usage():
                    self.logger.warning("메모리 사용량이 높습니다. 가비지 컬렉션을 실행합니다.")
                    gc.collect()
                    
                current_dir = stack.pop()
                
                try:
                    with os.scandir(current_dir) as entries:
                        for entry in entries:
                            if entry.is_dir(follow_symlinks=False) and recursive:
                                stack.append(Path(entry.path))
                            elif entry.is_file(follow_symlinks=False):
                                file_path = Path(entry.path)
                                
                                # 파일 타입 결정
                                file_type = self._determine_file_type(file_path)
                                
                                # 파일 크기 조회 (에러 처리 포함)
                                try:
                                    file_size = entry.stat().st_size
                                except (OSError, PermissionError):
                                    file_size = 0
                                    self.logger.warning(f"파일 크기 조회 실패: {file_path}")
                                
                                # 스캔 결과 생성
                                result = ScanResult(
                                    file_path=file_path,
                                    file_size=file_size,
                                    file_type=file_type
                                )
                                
                                processed_count += 1
                                
                                # 진행 상황 콜백
                                if progress_callback and processed_count % 100 == 0:
                                    progress_callback(processed_count, f"스캔 중: {file_path.name}")
                                
                                yield result
                                
                                # 배치 크기만큼 처리 후 메모리 정리
                                if processed_count % self.batch_size == 0:
                                    gc.collect()
                                    
                except (PermissionError, OSError) as e:
                    self.logger.warning(f"디렉토리 접근 실패: {current_dir} - {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"파일 스캔 중 오류 발생: {e}")
            raise FileManagerError(f"파일 스캔 실패: {str(e)}") from e
            
    async def scan_directory_async_generator(self, 
                                           directory: Path, 
                                           recursive: bool = True,
                                           progress_callback: Optional[Callable[[int, str], None]] = None) -> AsyncGenerator[ScanResult, None]:
        """
        디렉토리를 비동기 제너레이터로 스캔
        
        Args:
            directory: 스캔할 디렉토리
            recursive: 하위 디렉토리 포함 여부
            progress_callback: 진행 상황 콜백
            
        Yields:
            ScanResult: 파일 스캔 결과
        """
        loop = asyncio.get_running_loop()
        
        # 동기 제너레이터를 비동기로 변환
        sync_generator = self.scan_directory_generator(directory, recursive, progress_callback)
        
        try:
            while True:
                # 비동기 이벤트 루프에 제어권 양보
                await asyncio.sleep(0)
                
                # 동기 제너레이터에서 다음 항목 가져오기
                result = await loop.run_in_executor(None, self._get_next_from_generator, sync_generator)
                
                if result is None:  # 제너레이터 종료
                    break
                    
                yield result
                
        except Exception as e:
            self.logger.error(f"비동기 파일 스캔 중 오류 발생: {e}")
            raise FileManagerError(f"비동기 파일 스캔 실패: {str(e)}") from e
            
    def _get_next_from_generator(self, generator: Generator) -> Optional[ScanResult]:
        """제너레이터에서 다음 항목을 안전하게 가져오기"""
        try:
            return next(generator)
        except StopIteration:
            return None
            
    def _determine_file_type(self, file_path: Path) -> str:
        """파일 타입 결정"""
        extension = file_path.suffix.lower()
        
        if extension in self.video_extensions:
            return "video"
        elif extension in self.subtitle_extensions:
            return "subtitle"
        else:
            return "other"
            
    def _check_memory_usage(self) -> bool:
        """메모리 사용량 확인"""
        try:
            process = psutil.Process()
            memory_percent = process.memory_percent()
            return memory_percent > (self.max_memory_usage * 100)
        except Exception as e:
            self.logger.warning(f"메모리 사용량 확인 실패: {e}")
            return False
            
    def get_memory_stats(self) -> dict:
        """메모리 사용량 통계 반환"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,  # RSS (MB)
                "vms_mb": memory_info.vms / 1024 / 1024,  # VMS (MB)
                "percent": process.memory_percent(),
                "available_mb": psutil.virtual_memory().available / 1024 / 1024
            }
        except Exception as e:
            self.logger.warning(f"메모리 통계 조회 실패: {e}")
            return {"error": str(e)}
            
    def scan_with_filter(self, 
                        directory: Path, 
                        file_types: Optional[List[str]] = None,
                        min_size: int = 0,
                        max_size: Optional[int] = None,
                        recursive: bool = True) -> Generator[ScanResult, None, None]:
        """
        필터 조건을 적용한 파일 스캔
        
        Args:
            directory: 스캔할 디렉토리
            file_types: 포함할 파일 타입 목록 (None이면 모든 타입)
            min_size: 최소 파일 크기 (바이트)
            max_size: 최대 파일 크기 (바이트, None이면 제한 없음)
            recursive: 하위 디렉토리 포함 여부
            
        Yields:
            ScanResult: 필터링된 파일 스캔 결과
        """
        for result in self.scan_directory_generator(directory, recursive):
            # 파일 타입 필터
            if file_types and result.file_type not in file_types:
                continue
                
            # 파일 크기 필터
            if result.file_size < min_size:
                continue
                
            if max_size and result.file_size > max_size:
                continue
                
            yield result
            
    async def scan_with_metadata(self, 
                                directory: Path,
                                metadata_provider: Optional[Callable] = None,
                                recursive: bool = True) -> AsyncGenerator[ScanResult, None]:
        """
        메타데이터와 함께 파일 스캔
        
        Args:
            directory: 스캔할 디렉토리
            metadata_provider: 메타데이터 제공 함수
            recursive: 하위 디렉토리 포함 여부
            
        Yields:
            ScanResult: 메타데이터가 포함된 스캔 결과
        """
        async for result in self.scan_directory_async_generator(directory, recursive):
            # 메타데이터 제공자가 있으면 메타데이터 추가
            if metadata_provider and result.file_type == "video":
                try:
                    metadata = await metadata_provider(result.file_path)
                    result.metadata = metadata
                except Exception as e:
                    self.logger.warning(f"메타데이터 조회 실패: {result.file_path} - {e}")
                    
            yield result


class StreamingFileProcessor:
    """스트리밍 파일 처리기"""
    
    def __init__(self, scanner: MemoryOptimizedScanner):
        """
        StreamingFileProcessor 초기화
        
        Args:
            scanner: 메모리 최적화 스캐너
        """
        self.scanner = scanner
        self.logger = get_logger(__name__)
        
    async def process_files_streaming(self, 
                                    directory: Path,
                                    processor_func: Callable[[ScanResult], any],
                                    batch_size: int = 100,
                                    progress_callback: Optional[Callable[[int, str], None]] = None) -> List[any]:
        """
        파일을 스트리밍 방식으로 처리
        
        Args:
            directory: 처리할 디렉토리
            processor_func: 파일 처리 함수
            batch_size: 배치 크기
            progress_callback: 진행 상황 콜백
            
        Returns:
            List[any]: 처리 결과 목록
        """
        results = []
        batch = []
        processed_count = 0
        
        async for scan_result in self.scanner.scan_directory_async_generator(directory):
            try:
                # 파일 처리
                result = await processor_func(scan_result)
                batch.append(result)
                processed_count += 1
                
                # 배치 크기에 도달하면 결과 저장
                if len(batch) >= batch_size:
                    results.extend(batch)
                    batch = []
                    
                    # 진행 상황 콜백
                    if progress_callback:
                        progress_callback(processed_count, f"처리 중: {scan_result.file_path.name}")
                        
                    # 메모리 정리
                    gc.collect()
                    
            except Exception as e:
                self.logger.error(f"파일 처리 실패: {scan_result.file_path} - {e}")
                continue
                
        # 남은 배치 처리
        if batch:
            results.extend(batch)
            
        return results 