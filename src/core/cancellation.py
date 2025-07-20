"""
스트리밍 파이프라인 취소 신호 처리

스트리밍 파이프라인에서 안전한 취소 기능을 제공합니다.
현재 진행 중인 작업을 안전하게 중단하고 리소스를 정리합니다.
"""

import asyncio
import logging
from asyncio import CancelledError
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class CancellationReason(Enum):
    """취소 이유"""
    USER_REQUEST = "user_request"
    ERROR_THRESHOLD = "error_threshold"
    TIMEOUT = "timeout"
    SYSTEM_SHUTDOWN = "system_shutdown"
    MEMORY_LIMIT = "memory_limit"
    UNKNOWN = "unknown"


@dataclass
class CancellationInfo:
    """취소 정보"""
    reason: CancellationReason
    message: str
    timestamp: datetime = None
    context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class CancellationManager:
    """
    취소 관리자
    
    스트리밍 파이프라인의 안전한 취소를 관리합니다.
    """
    
    def __init__(self):
        """CancellationManager 초기화"""
        self._cancelled = False
        self._cancellation_info: Optional[CancellationInfo] = None
        self._active_tasks: Set[asyncio.Task] = set()
        self._cleanup_callbacks: Set[callable] = set()
        self.logger = logging.getLogger(__name__)
        
    @property
    def is_cancelled(self) -> bool:
        """취소 상태 확인"""
        return self._cancelled
        
    @property
    def cancellation_info(self) -> Optional[CancellationInfo]:
        """취소 정보 반환"""
        return self._cancellation_info
        
    def cancel(
        self, 
        reason: CancellationReason = CancellationReason.USER_REQUEST,
        message: str = "사용자 요청으로 취소됨",
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        파이프라인 취소
        
        Args:
            reason: 취소 이유
            message: 취소 메시지
            context: 추가 컨텍스트 정보
        """
        if self._cancelled:
            return
            
        self._cancelled = True
        self._cancellation_info = CancellationInfo(
            reason=reason,
            message=message,
            context=context
        )
        
        self.logger.info(f"파이프라인 취소 요청: {reason.value} - {message}")
        
        # 활성 태스크들 취소
        self._cancel_active_tasks()
        
        # 정리 콜백 실행
        self._run_cleanup_callbacks()
        
    def _cancel_active_tasks(self) -> None:
        """활성 태스크들 취소"""
        for task in self._active_tasks:
            if not task.done():
                task.cancel()
                self.logger.debug(f"태스크 취소: {task.get_name()}")
                
    def _run_cleanup_callbacks(self) -> None:
        """정리 콜백 실행"""
        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # 비동기 콜백은 이벤트 루프에서 실행
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 이미 실행 중인 루프에서는 create_task로 실행
                        loop.create_task(callback())
                    else:
                        # 루프가 실행되지 않으면 run_until_complete로 실행
                        loop.run_until_complete(callback())
                else:
                    # 동기 콜백은 직접 실행
                    callback()
            except Exception as e:
                self.logger.error(f"정리 콜백 실행 오류: {e}")
                
    def register_task(self, task: asyncio.Task) -> None:
        """태스크 등록"""
        self._active_tasks.add(task)
        
    def unregister_task(self, task: asyncio.Task) -> None:
        """태스크 등록 해제"""
        self._active_tasks.discard(task)
        
    def register_cleanup_callback(self, callback: callable) -> None:
        """정리 콜백 등록"""
        self._cleanup_callbacks.add(callback)
        
    def unregister_cleanup_callback(self, callback: callable) -> None:
        """정리 콜백 등록 해제"""
        self._cleanup_callbacks.discard(callback)
        
    def check_cancellation(self) -> None:
        """취소 상태 확인 및 예외 발생"""
        if self._cancelled:
            raise CancelledError(f"파이프라인이 취소됨: {self._cancellation_info.message}")
            
    async def wait_for_cancellation(self, timeout: Optional[float] = None) -> None:
        """
        취소 대기
        
        Args:
            timeout: 타임아웃 (초)
        """
        if timeout is None:
            while not self._cancelled:
                await asyncio.sleep(0.1)
        else:
            start_time = asyncio.get_event_loop().time()
            while not self._cancelled:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    break
                await asyncio.sleep(0.1)
                
        self.check_cancellation()
        
    def get_active_task_count(self) -> int:
        """활성 태스크 수 반환"""
        return len([task for task in self._active_tasks if not task.done()])
        
    def get_cancellation_summary(self) -> Dict[str, Any]:
        """취소 요약 정보 반환"""
        if not self._cancelled:
            return {"cancelled": False}
            
        return {
            "cancelled": True,
            "reason": self._cancellation_info.reason.value,
            "message": self._cancellation_info.message,
            "timestamp": self._cancellation_info.timestamp.isoformat(),
            "context": self._cancellation_info.context,
            "active_tasks": self.get_active_task_count()
        }


class CancellableTask:
    """
    취소 가능한 태스크 래퍼
    
    취소 관리자와 통합된 태스크를 제공합니다.
    """
    
    def __init__(self, cancellation_manager: CancellationManager):
        """
        CancellableTask 초기화
        
        Args:
            cancellation_manager: 취소 관리자
        """
        self.cancellation_manager = cancellation_manager
        self.task: Optional[asyncio.Task] = None
        
    async def run(self, coro, *args, **kwargs):
        """
        코루틴 실행
        
        Args:
            coro: 실행할 코루틴
            *args: 위치 인자
            **kwargs: 키워드 인자
            
        Returns:
            코루틴 결과
            
        Raises:
            CancelledError: 취소된 경우
        """
        # 취소 상태 확인
        self.cancellation_manager.check_cancellation()
        
        # 태스크 생성 및 등록
        self.task = asyncio.create_task(coro(*args, **kwargs))
        self.cancellation_manager.register_task(self.task)
        
        try:
            # 태스크 실행
            result = await self.task
            return result
        except CancelledError:
            # 태스크가 취소된 경우
            self.cancellation_manager.check_cancellation()
            raise
        finally:
            # 태스크 등록 해제
            if self.task:
                self.cancellation_manager.unregister_task(self.task)
                
    def cancel(self) -> None:
        """태스크 취소"""
        if self.task and not self.task.done():
            self.task.cancel()


# 취소 가능한 컨텍스트 매니저
class CancellableContext:
    """
    취소 가능한 컨텍스트 매니저
    
    with 문에서 사용할 수 있는 취소 가능한 컨텍스트를 제공합니다.
    """
    
    def __init__(self, cancellation_manager: CancellationManager):
        """
        CancellableContext 초기화
        
        Args:
            cancellation_manager: 취소 관리자
        """
        self.cancellation_manager = cancellation_manager
        
    async def __aenter__(self):
        """컨텍스트 진입"""
        self.cancellation_manager.check_cancellation()
        return self.cancellation_manager
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 종료"""
        if exc_type is CancelledError:
            # 취소된 경우 정리 작업 수행
            self.cancellation_manager._run_cleanup_callbacks()
            return True  # 예외 무시
        return False


# 취소 가능한 제너레이터
async def cancellable_generator(
    generator_func,
    cancellation_manager: CancellationManager,
    *args, **kwargs
):
    """
    취소 가능한 제너레이터
    
    Args:
        generator_func: 제너레이터 함수
        cancellation_manager: 취소 관리자
        *args: 위치 인자
        **kwargs: 키워드 인자
        
    Yields:
        제너레이터 값
    """
    async for item in generator_func(*args, **kwargs):
        # 각 반복마다 취소 상태 확인
        cancellation_manager.check_cancellation()
        yield item


# 취소 가능한 파이프라인 데코레이터
def cancellable_pipeline(cancellation_manager: CancellationManager):
    """
    취소 가능한 파이프라인 데코레이터
    
    Args:
        cancellation_manager: 취소 관리자
        
    Returns:
        데코레이터 함수
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                # 취소 상태 확인
                cancellation_manager.check_cancellation()
                
                # 함수 실행
                result = await func(*args, **kwargs)
                
                # 결과 반환 전 취소 상태 재확인
                cancellation_manager.check_cancellation()
                
                return result
                
            except CancelledError:
                # 취소된 경우 정리 작업 수행
                cancellation_manager._run_cleanup_callbacks()
                raise
                
        return wrapper
    return decorator


# 취소 가능한 파일 처리
async def process_file_with_cancellation(
    file_path: Path,
    processor_func,
    cancellation_manager: CancellationManager,
    *args, **kwargs
):
    """
    취소 가능한 파일 처리
    
    Args:
        file_path: 처리할 파일 경로
        processor_func: 처리 함수
        cancellation_manager: 취소 관리자
        *args: 위치 인자
        **kwargs: 키워드 인자
        
    Returns:
        처리 결과
    """
    try:
        # 파일 처리 시작 전 취소 상태 확인
        cancellation_manager.check_cancellation()
        
        # 파일 처리
        result = await processor_func(file_path, *args, **kwargs)
        
        # 처리 완료 후 취소 상태 재확인
        cancellation_manager.check_cancellation()
        
        return result
        
    except CancelledError:
        logger.info(f"파일 처리 취소됨: {file_path}")
        raise
    except Exception as e:
        logger.error(f"파일 처리 오류: {file_path} - {e}")
        raise 