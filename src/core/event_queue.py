"""
UI 이벤트 큐 시스템

스트리밍 파이프라인에서 발생하는 이벤트를 UI로 전달하는 큐 시스템을 제공합니다.
스레드 안전한 이벤트 처리와 UI 업데이트를 담당합니다.
"""

import asyncio
import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Union
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread

from .events import FileProcessedEvent, ProgressEvent, PipelineEvent, MetadataEvent, EventType

logger = logging.getLogger(__name__)


class EventQueue:
    """
    스레드 안전한 이벤트 큐
    
    백그라운드 스레드에서 발생하는 이벤트를 메인 UI 스레드로 전달합니다.
    """
    
    def __init__(self, maxsize: int = 1000):
        """
        EventQueue 초기화
        
        Args:
            maxsize: 큐 최대 크기 (기본값: 1000)
        """
        self._queue = queue.Queue(maxsize=maxsize)
        self._listeners: List[Callable] = []
        self._running = False
        self._lock = threading.Lock()
        
    def put(self, event: Union[FileProcessedEvent, ProgressEvent, PipelineEvent, MetadataEvent]) -> None:
        """
        이벤트를 큐에 추가
        
        Args:
            event: 추가할 이벤트 객체
        """
        try:
            self._queue.put_nowait(event)
            logger.debug(f"Event queued: {event.event_type}")
        except queue.Full:
            logger.warning("Event queue is full, dropping oldest event")
            try:
                # 가장 오래된 이벤트 제거
                self._queue.get_nowait()
                self._queue.put_nowait(event)
            except queue.Empty:
                logger.error("Failed to add event to queue")
                
    def get(self, timeout: Optional[float] = None) -> Optional[Union[FileProcessedEvent, ProgressEvent, PipelineEvent, MetadataEvent]]:
        """
        큐에서 이벤트를 가져옴
        
        Args:
            timeout: 대기 시간 (초)
            
        Returns:
            이벤트 객체 또는 None (타임아웃)
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def add_listener(self, callback: Callable) -> None:
        """
        이벤트 리스너 추가
        
        Args:
            callback: 이벤트 처리 콜백 함수
        """
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)
                
    def remove_listener(self, callback: Callable) -> None:
        """
        이벤트 리스너 제거
        
        Args:
            callback: 제거할 콜백 함수
        """
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)
                
    def notify_listeners(self, event: Union[FileProcessedEvent, ProgressEvent, PipelineEvent, MetadataEvent]) -> None:
        """
        모든 리스너에게 이벤트 알림
        
        Args:
            event: 알릴 이벤트
        """
        with self._lock:
            listeners = self._listeners.copy()
            
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
                
    def start(self) -> None:
        """이벤트 큐 시작"""
        with self._lock:
            self._running = True
        logger.info("Event queue started")
        
    def stop(self) -> None:
        """이벤트 큐 중지"""
        with self._lock:
            self._running = False
        logger.info("Event queue stopped")
        
    def is_running(self) -> bool:
        """실행 상태 확인"""
        with self._lock:
            return self._running
            
    def clear(self) -> None:
        """큐 내용 비우기"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        logger.info("Event queue cleared")


class QtEventQueue(QObject):
    """
    PyQt6 기반 이벤트 큐
    
    Qt 시그널을 사용하여 메인 스레드에서 UI 업데이트를 처리합니다.
    """
    
    # Qt 시그널 정의
    file_processed = pyqtSignal(object)  # FileProcessedEvent
    progress_updated = pyqtSignal(object)  # ProgressEvent
    pipeline_event = pyqtSignal(object)  # PipelineEvent
    metadata_event = pyqtSignal(object)  # MetadataEvent
    
    def __init__(self, parent=None):
        """
        QtEventQueue 초기화
        
        Args:
            parent: 부모 QObject
        """
        super().__init__(parent)
        self._event_queue = EventQueue()
        self._timer = QTimer()
        self._timer.timeout.connect(self._process_events)
        self._timer.setInterval(50)  # 50ms 간격으로 이벤트 처리
        
    def start(self) -> None:
        """이벤트 큐 시작"""
        self._event_queue.start()
        self._timer.start()
        logger.info("Qt event queue started")
        
    def stop(self) -> None:
        """이벤트 큐 중지"""
        self._timer.stop()
        self._event_queue.stop()
        logger.info("Qt event queue stopped")
        
    def close(self) -> None:
        """이벤트 큐 종료 (stop과 동일)"""
        self.stop()
        
    def put(self, event: Union[FileProcessedEvent, ProgressEvent, PipelineEvent, MetadataEvent]) -> None:
        """
        이벤트를 큐에 추가
        
        Args:
            event: 추가할 이벤트
        """
        self._event_queue.put(event)
        
    def _process_events(self) -> None:
        """타이머에 의해 호출되는 이벤트 처리 메서드"""
        while True:
            event = self._event_queue.get(timeout=0.001)  # 1ms 타임아웃
            if event is None:
                break
                
            # 이벤트 타입에 따라 적절한 시그널 발생
            if isinstance(event, FileProcessedEvent):
                self.file_processed.emit(event)
            elif isinstance(event, ProgressEvent):
                self.progress_updated.emit(event)
            elif isinstance(event, PipelineEvent):
                self.pipeline_event.emit(event)
            elif isinstance(event, MetadataEvent):
                self.metadata_event.emit(event)
            else:
                logger.warning(f"Unknown event type: {type(event)}")
                
    def connect_file_processed(self, slot: Callable) -> None:
        """파일 처리 완료 시그널 연결"""
        self.file_processed.connect(slot)
        
    def connect_progress_updated(self, slot: Callable) -> None:
        """진행률 업데이트 시그널 연결"""
        self.progress_updated.connect(slot)
        
    def connect_pipeline_event(self, slot: Callable) -> None:
        """파이프라인 이벤트 시그널 연결"""
        self.pipeline_event.connect(slot)
        
    def connect_metadata_event(self, slot: Callable) -> None:
        """메타데이터 이벤트 시그널 연결"""
        self.metadata_event.connect(slot)


class AsyncEventQueue:
    """
    비동기 이벤트 큐
    
    asyncio 기반 애플리케이션에서 사용할 수 있는 이벤트 큐입니다.
    """
    
    def __init__(self):
        """AsyncEventQueue 초기화"""
        self._queue = asyncio.Queue()
        self._listeners: List[Callable] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    async def put(self, event: Union[FileProcessedEvent, ProgressEvent, PipelineEvent, MetadataEvent]) -> None:
        """
        이벤트를 큐에 추가 (비동기)
        
        Args:
            event: 추가할 이벤트
        """
        await self._queue.put(event)
        logger.debug(f"Async event queued: {event.event_type}")
        
    async def get(self) -> Union[FileProcessedEvent, ProgressEvent, PipelineEvent, MetadataEvent]:
        """
        큐에서 이벤트를 가져옴 (비동기)
        
        Returns:
            이벤트 객체
        """
        return await self._queue.get()
        
    def add_listener(self, callback: Callable) -> None:
        """
        비동기 이벤트 리스너 추가
        
        Args:
            callback: 비동기 콜백 함수
        """
        if callback not in self._listeners:
            self._listeners.append(callback)
            
    async def start(self) -> None:
        """비동기 이벤트 큐 시작"""
        self._running = True
        self._task = asyncio.create_task(self._event_loop())
        logger.info("Async event queue started")
        
    async def stop(self) -> None:
        """비동기 이벤트 큐 중지"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Async event queue stopped")
        
    async def _event_loop(self) -> None:
        """이벤트 처리 루프"""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._notify_listeners(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in async event loop: {e}")
                
    async def _notify_listeners(self, event: Union[FileProcessedEvent, ProgressEvent, PipelineEvent, MetadataEvent]) -> None:
        """
        모든 리스너에게 이벤트 알림 (비동기)
        
        Args:
            event: 알릴 이벤트
        """
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"Error in async event listener: {e}") 