"""
단일 파일 처리 파이프라인

스트리밍 파이프라인에서 각 파일을 처리하는 핵심 로직을 담당합니다.
파일명 정제 → 메타데이터 검색 → 경로 결정 → 파일 이동의 순서로 처리합니다.
"""

import asyncio
import logging
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .events import FileProcessedEvent, ProgressEvent, EventType
from .event_queue import EventQueue
from .cancellation import CancellationManager, CancelledError
from .error_logger import log_error, ErrorSeverity

logger = logging.getLogger(__name__)


class FileProcessingError(Exception):
    """파일 처리 중 발생하는 오류"""
    def __init__(self, message: str, file_path: Path, step: str, original_error: Optional[Exception] = None):
        self.message = message
        self.file_path = file_path
        self.step = step
        self.original_error = original_error
        super().__init__(f"{step}: {message} (File: {file_path})")


class FilenameCleaningError(FileProcessingError):
    """파일명 정제 중 발생하는 오류"""
    pass


class MetadataSearchError(FileProcessingError):
    """메타데이터 검색 중 발생하는 오류"""
    pass


class PathDeterminationError(FileProcessingError):
    """경로 결정 중 발생하는 오류"""
    pass


class FileMoveError(FileProcessingError):
    """파일 이동 중 발생하는 오류"""
    pass


class SingleFileProcessor:
    """
    단일 파일 처리 파이프라인
    
    각 파일에 대해 다음 단계를 순차적으로 실행합니다:
    1. 파일명 정제
    2. 메타데이터 검색
    3. 이동 경로 결정
    4. 파일 이동
    5. UI 이벤트 생성
    """
    
    def __init__(
        self,
        file_cleaner,
        metadata_provider,
        path_planner,
        file_manager,
        event_queue: EventQueue,
        cancellation_manager: Optional[CancellationManager] = None
    ):
        """
        SingleFileProcessor 초기화
        
        Args:
            file_cleaner: 파일명 정제기
            metadata_provider: 메타데이터 제공자
            path_planner: 경로 계획자
            file_manager: 파일 관리자 (스캔 전용 모드에서는 None 가능)
            event_queue: 이벤트 큐
            cancellation_manager: 취소 관리자 (옵션)
        """
        self.file_cleaner = file_cleaner
        self.metadata_provider = metadata_provider
        self.path_planner = path_planner
        self.file_manager = file_manager
        self.event_queue = event_queue
        self.cancellation_manager = cancellation_manager
        
    async def process_single_file(
        self,
        file_path: Path,
        target_dir: Path,
        progress_callback: Optional[callable] = None
    ) -> FileProcessedEvent:
        """
        단일 파일 처리 파이프라인 실행
        
        Args:
            file_path: 처리할 파일 경로
            target_dir: 대상 디렉토리
            progress_callback: 진행률 콜백 함수 (옵션)
            
        Returns:
            FileProcessedEvent: 처리 결과 이벤트
            
        Raises:
            CancelledError: 처리 중 취소된 경우
            FileProcessingError: 처리 중 오류 발생 시
        """
        start_time = time.time()
        event = FileProcessedEvent(
            file_path=file_path,
            event_type=EventType.FILE_STARTED,
            timestamp=start_time,
            success=False,
            error_message="",
            metadata=None,
            target_path=None,
            processing_time=0.0
        )
        
        try:
            logger.info(f"Processing file: {file_path}")
            
            # 취소 상태 확인
            if self.cancellation_manager:
                self.cancellation_manager.check_cancellation()
            
            # 1단계: 파일명 정제
            if progress_callback:
                progress_callback(f"정제 중: {file_path.name}")
                
            clean_result = await self._clean_filename(file_path)
            if not clean_result:
                raise FilenameCleaningError(
                    "파일명 정제 결과가 없습니다",
                    file_path,
                    "파일명 정제"
                )
                
            logger.debug(f"Cleaned filename: {clean_result}")
            
            # 취소 상태 확인
            if self.cancellation_manager:
                self.cancellation_manager.check_cancellation()
            
            # 2단계: 메타데이터 검색
            if progress_callback:
                progress_callback(f"메타데이터 검색 중: {clean_result.get('title', file_path.name)}")
                
            metadata = await self._search_metadata(clean_result)
            if metadata:
                logger.info(f"Metadata found for: {file_path.name}")
                event.metadata = metadata
            else:
                logger.warning(f"No metadata found for: {file_path.name}")
                
            # 취소 상태 확인
            if self.cancellation_manager:
                self.cancellation_manager.check_cancellation()
            
            # 3단계: 이동 경로 결정
            if progress_callback:
                progress_callback(f"경로 결정 중: {file_path.name}")
                
            target_path = await self._determine_path(file_path, metadata, target_dir)
            if not target_path:
                raise PathDeterminationError(
                    "이동 경로를 결정할 수 없습니다",
                    file_path,
                    "경로 결정"
                )
                
            event.target_path = target_path
            logger.debug(f"Target path: {target_path}")
            
            # 취소 상태 확인
            if self.cancellation_manager:
                self.cancellation_manager.check_cancellation()
            
            # 4단계: 파일 이동
            if progress_callback:
                progress_callback(f"파일 이동 중: {file_path.name}")
                
            move_success = await self._move_file(file_path, target_path)
            if not move_success:
                raise FileMoveError(
                    "파일 이동에 실패했습니다",
                    file_path,
                    "파일 이동"
                )
                
            # 성공 처리
            processing_time = time.time() - start_time
            event.success = True
            event.event_type = EventType.FILE_PROCESSED
            event.processing_time = processing_time
            event.error_message = ""
            
            logger.info(f"File processed successfully: {file_path.name} -> {target_path}")
            
        except CancelledError:
            # 취소 처리
            processing_time = time.time() - start_time
            event.success = False
            event.event_type = EventType.FILE_ERROR
            event.processing_time = processing_time
            event.error_message = "파일 처리가 취소되었습니다."
            
            logger.info(f"File processing cancelled: {file_path}")
            raise
            
        except FileProcessingError as e:
            # 파일 처리 오류
            processing_time = time.time() - start_time
            event.success = False
            event.event_type = EventType.FILE_ERROR
            event.processing_time = processing_time
            event.error_message = str(e)
            
            logger.error(f"File processing error for {file_path}: {e}")
            if e.original_error:
                logger.error(f"Original error: {e.original_error}")
                logger.error(f"Stack trace: {traceback.format_exc()}")
                
            # 상세 오류 로깅
            log_error(
                file_path=file_path,
                error=e,
                processing_step=e.step,
                context={
                    'processing_time': processing_time,
                    'event_type': event.event_type.value
                },
                severity=ErrorSeverity.MEDIUM
            )
                
        except Exception as e:
            # 예상치 못한 오류
            processing_time = time.time() - start_time
            event.success = False
            event.event_type = EventType.FILE_ERROR
            event.processing_time = processing_time
            event.error_message = f"예상치 못한 오류: {str(e)}"
            
            logger.error(f"Unexpected error processing file {file_path}: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # 상세 오류 로깅
            log_error(
                file_path=file_path,
                error=e,
                processing_step="예상치 못한 오류",
                context={
                    'processing_time': processing_time,
                    'event_type': event.event_type.value,
                    'error_type': type(e).__name__
                },
                severity=ErrorSeverity.HIGH
            )
            
        finally:
            # 이벤트 큐에 결과 전송
            try:
                await self.event_queue.put(event)
            except Exception as e:
                logger.error(f"Failed to send event to queue: {e}")
                
                # 이벤트 큐 오류 로깅
                log_error(
                    file_path=file_path,
                    error=e,
                    processing_step="이벤트 큐 전송",
                    context={
                        'event_type': event.event_type.value,
                        'event_success': event.success
                    },
                    severity=ErrorSeverity.LOW
                )
            
            # 진행률 콜백 호출
            if progress_callback:
                try:
                    progress_callback(f"완료: {file_path.name}")
                except Exception as e:
                    logger.error(f"Progress callback failed: {e}")
                    
                    # 콜백 오류 로깅
                    log_error(
                        file_path=file_path,
                        error=e,
                        processing_step="진행률 콜백",
                        context={
                            'callback_type': type(progress_callback).__name__
                        },
                        severity=ErrorSeverity.LOW
                    )
                
        return event
        
    async def process_file_scan_only(
        self,
        file_path: Path,
        progress_callback: Optional[callable] = None
    ) -> tuple:
        """
        단일 파일 스캔 처리 (파일 이동 없음)
        
        Args:
            file_path: 스캔할 파일 경로
            progress_callback: 진행률 콜백 함수 (옵션)
            
        Returns:
            tuple: (clean_result, metadata) 스캔 결과
            
        Raises:
            CancelledError: 처리 중 취소된 경우
            FileProcessingError: 처리 중 오류 발생 시
        """
        try:
            logger.info(f"Scanning file: {file_path}")
            
            # 취소 상태 확인
            if self.cancellation_manager:
                self.cancellation_manager.check_cancellation()
            
            # 1단계: 파일명 정제
            if progress_callback:
                progress_callback(f"정제 중: {file_path.name}")
                
            clean_result = await self._clean_filename(file_path)
            if not clean_result:
                raise FilenameCleaningError(
                    "파일명 정제 결과가 없습니다",
                    file_path,
                    "파일명 정제"
                )
                
            logger.debug(f"Cleaned filename: {clean_result}")
            
            # 취소 상태 확인
            if self.cancellation_manager:
                self.cancellation_manager.check_cancellation()
            
            # 2단계: 메타데이터 검색
            if progress_callback:
                progress_callback(f"메타데이터 검색 중: {clean_result.get('title', file_path.name)}")
                
            metadata = await self._search_metadata(clean_result)
            if metadata:
                logger.info(f"Metadata found for: {file_path.name}")
            else:
                logger.warning(f"No metadata found for: {file_path.name}")
                
            return clean_result, metadata
            
        except CancelledError:
            logger.info(f"File scanning cancelled: {file_path}")
            raise
        except FileProcessingError as e:
            logger.error(f"File scanning error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error scanning file {file_path}: {e}")
            raise
            
    async def _clean_filename(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        파일명 정제
        
        Args:
            file_path: 파일 경로
            
        Returns:
            Dict or None: 정제된 파일 정보 또는 None (실패)
            
        Raises:
            FilenameCleaningError: 파일명 정제 중 오류 발생 시
        """
        try:
            if hasattr(self.file_cleaner, 'clean_filename'):
                result = await self.file_cleaner.clean_filename(file_path)
            else:
                # 동기 메서드인 경우
                result = self.file_cleaner.clean_filename(file_path)
                
            if not result:
                logger.warning(f"Filename cleaning returned no result for: {file_path}")
                return None
                
            return result
            
        except Exception as e:
            error_msg = f"파일명 정제 중 오류 발생: {str(e)}"
            logger.error(f"{error_msg} for {file_path}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # 상세 오류 로깅
            log_error(
                file_path=file_path,
                error=e,
                processing_step="파일명 정제",
                context={
                    'file_cleaner_type': type(self.file_cleaner).__name__,
                    'has_async_method': hasattr(self.file_cleaner, 'clean_filename')
                },
                severity=ErrorSeverity.MEDIUM
            )
            
            raise FilenameCleaningError(error_msg, file_path, "파일명 정제", e)
            
    async def _search_metadata(self, clean_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        메타데이터 검색
        
        Args:
            clean_result: 정제된 파일 정보
            
        Returns:
            Dict or None: 메타데이터 또는 None (검색 실패)
            
        Raises:
            MetadataSearchError: 메타데이터 검색 중 오류 발생 시
        """
        try:
            title = clean_result.get('title', '')
            year = clean_result.get('year')
            
            if not title:
                logger.warning("No title available for metadata search")
                return None
                
            if hasattr(self.metadata_provider, 'search'):
                metadata = await self.metadata_provider.search(title, year)
            else:
                # 동기 메서드인 경우
                metadata = self.metadata_provider.search(title, year)
                
            return metadata
            
        except Exception as e:
            error_msg = f"메타데이터 검색 중 오류 발생: {str(e)}"
            logger.error(f"{error_msg} for title: {clean_result.get('title', 'Unknown')}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # 상세 오류 로깅
            log_error(
                file_path=Path(""),  # 파일 경로는 컨텍스트에서 제공
                error=e,
                processing_step="메타데이터 검색",
                context={
                    'title': clean_result.get('title', ''),
                    'year': clean_result.get('year'),
                    'metadata_provider_type': type(self.metadata_provider).__name__,
                    'has_async_method': hasattr(self.metadata_provider, 'search')
                },
                severity=ErrorSeverity.MEDIUM
            )
            
            raise MetadataSearchError(error_msg, Path(""), "메타데이터 검색", e)
            
    async def _determine_path(
        self,
        file_path: Path,
        metadata: Optional[Dict[str, Any]],
        target_dir: Path
    ) -> Optional[Path]:
        """
        이동 경로 결정
        
        Args:
            file_path: 원본 파일 경로
            metadata: 메타데이터 (옵션)
            target_dir: 대상 디렉토리
            
        Returns:
            Path or None: 대상 경로 또는 None (실패)
            
        Raises:
            PathDeterminationError: 경로 결정 중 오류 발생 시
        """
        # 스캔 전용 모드에서는 경로 결정을 건너뜀
        if self.path_planner is None:
            logger.debug(f"Path planner is None, skipping path determination for: {file_path}")
            return None
            
        try:
            if hasattr(self.path_planner, 'determine_path'):
                target_path = await self.path_planner.determine_path(
                    file_path, metadata, target_dir
                )
            else:
                # 동기 메서드인 경우
                target_path = self.path_planner.determine_path(
                    file_path, metadata, target_dir
                )
                
            if not target_path:
                logger.warning(f"Path planner returned no target path for: {file_path}")
                return None
                
            return target_path
            
        except Exception as e:
            error_msg = f"경로 결정 중 오류 발생: {str(e)}"
            logger.error(f"{error_msg} for {file_path}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # 상세 오류 로깅
            log_error(
                file_path=file_path,
                error=e,
                processing_step="경로 결정",
                context={
                    'target_dir': str(target_dir),
                    'has_metadata': metadata is not None,
                    'path_planner_type': type(self.path_planner).__name__,
                    'has_async_method': hasattr(self.path_planner, 'determine_path')
                },
                severity=ErrorSeverity.MEDIUM
            )
            
            raise PathDeterminationError(error_msg, file_path, "경로 결정", e)
            
    async def _move_file(self, source_path: Path, target_path: Path) -> bool:
        """
        파일 이동
        
        Args:
            source_path: 원본 파일 경로
            target_path: 대상 파일 경로
            
        Returns:
            bool: 이동 성공 여부
            
        Raises:
            FileMoveError: 파일 이동 중 오류 발생 시
        """
        # 스캔 전용 모드에서는 파일 이동을 건너뜀
        if self.file_manager is None:
            logger.debug(f"File manager is None, skipping file move for: {source_path}")
            return True
            
        try:
            if hasattr(self.file_manager, 'move_file'):
                success = await self.file_manager.move_file(source_path, target_path)
            else:
                # 동기 메서드인 경우
                success = self.file_manager.move_file(source_path, target_path)
                
            if not success:
                logger.error(f"File move operation returned False for: {source_path} -> {target_path}")
                return False
                
            return True
            
        except Exception as e:
            error_msg = f"파일 이동 중 오류 발생: {str(e)}"
            logger.error(f"{error_msg} for {source_path} -> {target_path}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # 상세 오류 로깅
            log_error(
                file_path=source_path,
                error=e,
                processing_step="파일 이동",
                context={
                    'source_path': str(source_path),
                    'target_path': str(target_path),
                    'file_manager_type': type(self.file_manager).__name__,
                    'has_async_method': hasattr(self.file_manager, 'move_file')
                },
                severity=ErrorSeverity.HIGH  # 파일 이동 오류는 높은 심각도
            )
            
            raise FileMoveError(error_msg, source_path, "파일 이동", e)


# 편의 함수
async def process_single_file(
    file_path: Path,
    target_dir: Path,
    file_cleaner,
    metadata_provider,
    path_planner,
    file_manager,
    event_queue: EventQueue,
    progress_callback: Optional[callable] = None
) -> FileProcessedEvent:
    """
    단일 파일 처리 편의 함수
    
    Args:
        file_path: 처리할 파일 경로
        target_dir: 대상 디렉토리
        file_cleaner: 파일명 정제기
        metadata_provider: 메타데이터 제공자
        path_planner: 경로 계획자
        file_manager: 파일 관리자
        event_queue: 이벤트 큐
        progress_callback: 진행률 콜백 함수 (옵션)
        
    Returns:
        FileProcessedEvent: 처리 결과 이벤트
    """
    processor = SingleFileProcessor(
        file_cleaner,
        metadata_provider,
        path_planner,
        file_manager,
        event_queue
    )
    
    return await processor.process_single_file(
        file_path, target_dir, progress_callback
    ) 