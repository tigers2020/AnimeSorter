"""
메인 스트리밍 파이프라인

스트리밍 파일 이터레이터, 단일 파일 처리기, 이벤트 큐를 통합하여
전체 파일 처리 파이프라인을 관리합니다.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .events import (
    FileProcessedEvent, ProgressEvent, PipelineEvent, 
    EventType, ProcessingStatus
)
from .event_queue import EventQueue
from .streaming_file_iterator import iter_files
from .single_file_processor import SingleFileProcessor
from .cancellation import CancellationManager, CancelledError, CancellationReason

logger = logging.getLogger(__name__)


class StreamingPipeline:
    """
    메인 스트리밍 파이프라인
    
    파일을 하나씩 스트리밍 방식으로 처리하여 메모리 효율성과
    실시간 UI 업데이트를 제공합니다.
    """
    
    def __init__(
        self,
        file_cleaner,
        metadata_provider,
        path_planner,
        file_manager,
        event_queue: EventQueue,
        max_concurrent_files: int = 1
    ):
        """
        StreamingPipeline 초기화
        
        Args:
            file_cleaner: 파일명 정제기
            metadata_provider: 메타데이터 제공자
            path_planner: 경로 계획자
            file_manager: 파일 관리자
            event_queue: 이벤트 큐
            max_concurrent_files: 최대 동시 처리 파일 수 (기본값: 1)
        """
        self.file_cleaner = file_cleaner
        self.metadata_provider = metadata_provider
        self.path_planner = path_planner
        self.file_manager = file_manager
        self.event_queue = event_queue
        self.max_concurrent_files = max_concurrent_files
        
        # 파이프라인 상태
        self._running = False
        self._cancelled = False
        self._stats = {
            'total_files': 0,
            'processed_files': 0,
            'successful_files': 0,
            'failed_files': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 취소 관리자
        self.cancellation_manager = CancellationManager()
        
        # 리소스 정리 콜백 등록
        self.cancellation_manager.register_cleanup_callback(self._cleanup_resources)
        
        # 단일 파일 처리기 (스캔 전용 모드에서는 file_manager가 None일 수 있음)
        self.single_file_processor = SingleFileProcessor(
            file_cleaner=file_cleaner,
            metadata_provider=metadata_provider,
            path_planner=path_planner,
            file_manager=file_manager,  # None일 수 있음 (스캔 전용 모드)
            event_queue=event_queue,
            cancellation_manager=self.cancellation_manager
        )
        
    async def run(
        self, 
        source_dir: Path, 
        target_dir: Path,
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        스트리밍 파이프라인 실행
        
        Args:
            source_dir: 소스 디렉토리
            target_dir: 대상 디렉토리
            recursive: 하위 디렉토리 포함 여부
            
        Returns:
            Dict[str, Any]: 처리 결과 통계
            
        Raises:
            FileNotFoundError: 소스 디렉토리가 존재하지 않는 경우
            PermissionError: 디렉토리 접근 권한이 없는 경우
            CancelledError: 파이프라인이 취소된 경우
        """
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
            
        if not source_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {source_dir}")
            
        # 파이프라인 시작
        self._running = True
        self._cancelled = False
        self._stats['start_time'] = time.time()
        self._stats['total_files'] = 0
        self._stats['processed_files'] = 0
        self._stats['successful_files'] = 0
        self._stats['failed_files'] = 0
        
        logger.info(f"Starting streaming pipeline: {source_dir} -> {target_dir}")
        
        # 파이프라인 시작 이벤트
        await self.event_queue.put(
            PipelineEvent.pipeline_started(0)  # 파일 수는 나중에 업데이트
        )
        
        try:
            # 취소 상태 확인
            self.cancellation_manager.check_cancellation()
            
            # 파일 수 계산 (진행률 표시용)
            file_count = await self._count_files(source_dir, recursive)
            self._stats['total_files'] = file_count
            
            logger.info(f"Found {file_count} files to process")
            
            # 취소 상태 재확인
            self.cancellation_manager.check_cancellation()
            
            # 스트리밍 파이프라인 실행
            if self.max_concurrent_files == 1:
                # 순차 처리
                await self._run_sequential(source_dir, target_dir, recursive)
            else:
                # 병렬 처리
                await self._run_parallel(source_dir, target_dir, recursive)
                
        except CancelledError:
            logger.info("Pipeline cancelled by user")
            self._cancelled = True
            await self.event_queue.put(
                PipelineEvent.pipeline_cancelled("User cancelled")
            )
            raise
        except asyncio.CancelledError:
            logger.info("Pipeline cancelled by asyncio")
            self._cancelled = True
            await self.event_queue.put(
                PipelineEvent.pipeline_cancelled("Asyncio cancelled")
            )
            raise
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            await self.event_queue.put(
                PipelineEvent.pipeline_error(str(e))
            )
            raise
        finally:
            # 파이프라인 종료
            self._running = False
            self._stats['end_time'] = time.time()
            
            # 파이프라인 완료 이벤트
            await self.event_queue.put(
                PipelineEvent.pipeline_completed(self._stats.copy())
            )
            
            logger.info(f"Pipeline completed. Stats: {self._stats}")
            
        return self._stats.copy()
        
    async def run_scan_only(
        self, 
        source_dir: Path,
        scan_callback=None,
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        스트리밍 파이프라인 실행 (스캔 전용)
        
        Args:
            source_dir: 소스 디렉토리
            scan_callback: 파일 스캔 완료 시 호출할 콜백 함수
            recursive: 하위 디렉토리 포함 여부
            
        Returns:
            Dict[str, Any]: 스캔 결과 통계
            
        Raises:
            FileNotFoundError: 소스 디렉토리가 존재하지 않는 경우
            PermissionError: 디렉토리 접근 권한이 없는 경우
            CancelledError: 파이프라인이 취소된 경우
        """
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
            
        if not source_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {source_dir}")
            
        # 파이프라인 시작
        self._running = True
        self._cancelled = False
        self._stats['start_time'] = time.time()
        self._stats['total_files'] = 0
        self._stats['processed_files'] = 0
        self._stats['successful_files'] = 0
        self._stats['failed_files'] = 0
        
        logger.info(f"Starting streaming scan pipeline: {source_dir}")
        
        # 파이프라인 시작 이벤트
        await self.event_queue.put(
            PipelineEvent.pipeline_started(0)  # 파일 수는 나중에 업데이트
        )
        
        try:
            # 취소 상태 확인
            self.cancellation_manager.check_cancellation()
            
            # 파일 수 계산 (진행률 표시용)
            file_count = await self._count_files(source_dir, recursive)
            self._stats['total_files'] = file_count
            
            logger.info(f"Found {file_count} files to scan")
            
            # 취소 상태 재확인
            self.cancellation_manager.check_cancellation()
            
            # 스트리밍 스캔 실행
            if self.max_concurrent_files == 1:
                # 순차 스캔
                await self._run_scan_sequential(source_dir, recursive, scan_callback)
            else:
                # 병렬 스캔
                await self._run_scan_parallel(source_dir, recursive, scan_callback)
                
        except CancelledError:
            logger.info("Scan pipeline cancelled by user")
            self._cancelled = True
            await self.event_queue.put(
                PipelineEvent.pipeline_cancelled("User cancelled")
            )
            raise
        except asyncio.CancelledError:
            logger.info("Scan pipeline cancelled by asyncio")
            self._cancelled = True
            await self.event_queue.put(
                PipelineEvent.pipeline_cancelled("Asyncio cancelled")
            )
            raise
        except Exception as e:
            logger.error(f"Scan pipeline error: {e}")
            await self.event_queue.put(
                PipelineEvent.pipeline_error(str(e))
            )
            raise
        finally:
            # 파이프라인 종료
            self._running = False
            self._stats['end_time'] = time.time()
            
            # 파이프라인 완료 이벤트
            await self.event_queue.put(
                PipelineEvent.pipeline_completed(self._stats.copy())
            )
            
            logger.info(f"Scan pipeline completed. Stats: {self._stats}")
            
        return self._stats.copy()
        
    async def _run_scan_sequential(
        self, 
        source_dir: Path, 
        recursive: bool,
        scan_callback=None
    ):
        """순차 스캔 방식"""
        async for file_path in iter_files(source_dir, recursive):
            # 취소 상태 확인
            self.cancellation_manager.check_cancellation()
            
            if self._cancelled:
                break
                
            try:
                # 파일 스캔 처리 (파일 이동 없음)
                clean_result, metadata = await self.single_file_processor.process_file_scan_only(file_path)
                
                # 스캔 완료 이벤트
                await self.event_queue.put(
                    FileProcessedEvent.file_processed(
                        file_path=str(file_path),
                        clean_result=clean_result,
                        metadata=metadata,
                        status=ProcessingStatus.SUCCESS
                    )
                )
                
                # 진행률 업데이트
                self._stats['processed_files'] += 1
                self._stats['successful_files'] += 1
                
                await self.event_queue.put(
                    ProgressEvent.progress_updated(
                        current=self._stats['processed_files'],
                        total=self._stats['total_files'],
                        message=f"스캔 완료: {file_path.name}"
                    )
                )
                
                # 스캔 콜백 호출
                if scan_callback:
                    scan_callback(file_path, clean_result, metadata)
                    
            except Exception as e:
                logger.error(f"Error scanning file {file_path}: {e}")
                self._stats['processed_files'] += 1
                self._stats['failed_files'] += 1
                
                # 오류 이벤트
                await self.event_queue.put(
                    FileProcessedEvent.file_processed(
                        file_path=str(file_path),
                        clean_result=None,
                        metadata=None,
                        status=ProcessingStatus.FAILED,
                        error=str(e)
                    )
                )
                
    async def _run_scan_parallel(
        self, 
        source_dir: Path, 
        recursive: bool,
        scan_callback=None
    ):
        """병렬 스캔 방식"""
        semaphore = asyncio.Semaphore(self.max_concurrent_files)
        
        async def scan_file_with_semaphore(file_path: Path):
            async with semaphore:
                # 취소 상태 확인
                self.cancellation_manager.check_cancellation()
                
                if self._cancelled:
                    return
                    
                try:
                    # 파일 스캔 처리 (파일 이동 없음)
                    clean_result, metadata = await self.single_file_processor.process_file_scan_only(file_path)
                    
                    # 스캔 완료 이벤트
                    await self.event_queue.put(
                        FileProcessedEvent.file_processed(
                            file_path=str(file_path),
                            clean_result=clean_result,
                            metadata=metadata,
                            status=ProcessingStatus.SUCCESS
                        )
                    )
                    
                    # 진행률 업데이트
                    self._stats['processed_files'] += 1
                    self._stats['successful_files'] += 1
                    
                    await self.event_queue.put(
                        ProgressEvent.progress_updated(
                            current=self._stats['processed_files'],
                            total=self._stats['total_files'],
                            message=f"스캔 완료: {file_path.name}"
                        )
                    )
                    
                    # 스캔 콜백 호출
                    if scan_callback:
                        scan_callback(file_path, clean_result, metadata)
                        
                except Exception as e:
                    logger.error(f"Error scanning file {file_path}: {e}")
                    self._stats['processed_files'] += 1
                    self._stats['failed_files'] += 1
                    
                    # 오류 이벤트
                    await self.event_queue.put(
                        FileProcessedEvent.file_processed(
                            file_path=str(file_path),
                            clean_result=None,
                            metadata=None,
                            status=ProcessingStatus.FAILED,
                            error=str(e)
                        )
                    )
        
        # 병렬 스캔 실행
        tasks = []
        async for file_path in iter_files(source_dir, recursive):
            if self._cancelled:
                break
            task = asyncio.create_task(scan_file_with_semaphore(file_path))
            tasks.append(task)
            
        # 모든 태스크 완료 대기
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _run_sequential(
        self, 
        source_dir: Path, 
        target_dir: Path, 
        recursive: bool
    ):
        """순차 처리 방식"""
        async for file_path in iter_files(source_dir, recursive):
            # 취소 상태 확인
            self.cancellation_manager.check_cancellation()
            
            if self._cancelled:
                break
                
            try:
                # 단일 파일 처리
                result = await self.single_file_processor.process_single_file(
                    file_path, target_dir
                )
                
                # 통계 업데이트
                self._stats['processed_files'] += 1
                if result.success:
                    self._stats['successful_files'] += 1
                else:
                    self._stats['failed_files'] += 1
                    
                # 진행률 업데이트
                progress = (self._stats['processed_files'] / self._stats['total_files']) * 100
                await self.event_queue.put(
                    ProgressEvent(
                        current_index=self._stats['processed_files'],
                        total_files=self._stats['total_files'],
                        processed_files=self._stats['processed_files'],
                        successful_files=self._stats['successful_files'],
                        failed_files=self._stats['failed_files'],
                        current_file=file_path,
                        message=f"Processing {file_path.name}"
                    )
                )
                
            except CancelledError:
                logger.info(f"File processing cancelled: {file_path}")
                self._cancelled = True
                break
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                self._stats['processed_files'] += 1
                self._stats['failed_files'] += 1
                
                # 오류 이벤트
                await self.event_queue.put(
                    FileProcessedEvent(
                        file_path=file_path,
                        success=False,
                        error_message=str(e)
                    )
                )
                
    async def _run_parallel(
        self, 
        source_dir: Path, 
        target_dir: Path, 
        recursive: bool
    ):
        """병렬 처리 방식"""
        semaphore = asyncio.Semaphore(self.max_concurrent_files)
        
        async def process_file_with_semaphore(file_path: Path):
            async with semaphore:
                # 취소 상태 확인
                self.cancellation_manager.check_cancellation()
                
                if self._cancelled:
                    return
                    
                try:
                    result = await self.single_file_processor.process_single_file(
                        file_path, target_dir
                    )
                    
                    # 통계 업데이트 (스레드 안전하게)
                    self._stats['processed_files'] += 1
                    if result.success:
                        self._stats['successful_files'] += 1
                    else:
                        self._stats['failed_files'] += 1
                        
                except CancelledError:
                    logger.info(f"File processing cancelled: {file_path}")
                    self._cancelled = True
                    return
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    self._stats['processed_files'] += 1
                    self._stats['failed_files'] += 1
                    
        # 모든 파일을 동시에 처리
        tasks = []
        async for file_path in iter_files(source_dir, recursive):
            # 취소 상태 확인
            self.cancellation_manager.check_cancellation()
            
            if self._cancelled:
                break
                
            task = asyncio.create_task(
                process_file_with_semaphore(file_path)
            )
            tasks.append(task)
            
        # 모든 태스크 완료 대기
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def _count_files(self, source_dir: Path, recursive: bool) -> int:
        """파일 수 계산"""
        count = 0
        async for _ in iter_files(source_dir, recursive):
            count += 1
        return count
        
    def cancel(self):
        """파이프라인 취소"""
        self._cancelled = True
        self.cancellation_manager.cancel(
            reason=CancellationReason.USER_REQUEST,
            message="사용자 요청으로 파이프라인이 취소되었습니다."
        )
        logger.info("Pipeline cancellation requested")
        
    async def _cleanup_resources(self):
        """리소스 정리"""
        try:
            logger.info("Cleaning up pipeline resources...")
            
            # 메타데이터 제공자 정리
            if hasattr(self.metadata_provider, 'close'):
                try:
                    await self.metadata_provider.close()
                    logger.debug("Metadata provider closed")
                except Exception as e:
                    logger.warning(f"Error closing metadata provider: {e}")
                    
            # 파일 관리자 정리 (스캔 전용 모드에서는 None일 수 있음)
            if self.file_manager is not None and hasattr(self.file_manager, 'close'):
                try:
                    await self.file_manager.close()
                    logger.debug("File manager closed")
                except Exception as e:
                    logger.warning(f"Error closing file manager: {e}")
                    
            # 이벤트 큐 정리
            if hasattr(self.event_queue, 'close'):
                try:
                    await self.event_queue.close()
                    logger.debug("Event queue closed")
                except Exception as e:
                    logger.warning(f"Error closing event queue: {e}")
                    
            logger.info("Pipeline resources cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
            
    async def close(self):
        """파이프라인 종료 및 리소스 정리"""
        try:
            if self._running:
                self.cancel()
                
            await self._cleanup_resources()
            logger.info("Pipeline closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing pipeline: {e}")
            
    def __del__(self):
        """소멸자에서 리소스 정리"""
        try:
            if self._running:
                logger.warning("Pipeline destroyed while running, attempting cleanup")
                # 비동기 정리는 소멸자에서 할 수 없으므로 경고만 출력
        except Exception:
            pass
        
    @property
    def is_running(self) -> bool:
        """파이프라인 실행 중 여부"""
        return self._running
        
    @property
    def stats(self) -> Dict[str, Any]:
        """현재 통계"""
        return self._stats.copy() 