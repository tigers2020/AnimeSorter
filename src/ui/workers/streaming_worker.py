"""
스트리밍 파이프라인 워커

PyQt 워커를 사용하여 스트리밍 파이프라인을 UI와 통합합니다.
"""

import asyncio
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool
from PyQt6.QtWidgets import QApplication

from src.core.streaming_pipeline import StreamingPipeline, ProcessingResult
from src.plugin.tmdb.provider import TMDBProvider
from src.core.async_file_manager import AsyncFileManager
from src.utils.logger import get_logger

class StreamingWorkerSignals(QObject):
    """스트리밍 워커 시그널"""
    
    # 진행 상황 시그널
    progress = pyqtSignal(int, int, str)  # current, total, message
    file_processed = pyqtSignal(object)   # ProcessingResult
    
    # 에러 시그널
    error = pyqtSignal(str, str, str)     # file_path, error_type, error_message
    
    # 완료 시그널
    finished = pyqtSignal(dict)           # final_stats
    cancelled = pyqtSignal()
    
    # 로그 시그널
    log = pyqtSignal(str)                 # log_message
    
    # 포스터 시그널
    poster_ready = pyqtSignal(str, str)   # file_path, poster_url

class StreamingWorker(QRunnable):
    """스트리밍 파이프라인 워커"""
    
    def __init__(self, 
                 file_paths: List[Path],
                 tmdb_provider: TMDBProvider,
                 target_directory: Path,
                 folder_template: str = "{title} ({year})"):
        """
        StreamingWorker 초기화
        
        Args:
            file_paths: 처리할 파일 경로 목록
            tmdb_provider: TMDB 메타데이터 제공자
            target_directory: 대상 디렉토리
            folder_template: 폴더 이름 템플릿
        """
        super().__init__()
        self.file_paths = file_paths
        self.tmdb_provider = tmdb_provider
        self.target_directory = target_directory
        self.folder_template = folder_template
        
        # 시그널 설정
        self.signals = StreamingWorkerSignals()
        
        # 취소 플래그
        self._cancelled = False
        
        # 로거
        self.logger = get_logger(__name__)
        
    def run(self):
        """워커 실행 (별도 스레드에서 호출됨)"""
        try:
            # 비동기 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 스트리밍 파이프라인 실행
            loop.run_until_complete(self._run_pipeline())
            
        except Exception as e:
            self.logger.error(f"스트리밍 워커 실행 중 오류: {e}")
            self.signals.error.emit("", "WorkerError", str(e))
        finally:
            # 이벤트 루프 정리
            try:
                loop.close()
            except:
                pass
                
    async def _run_pipeline(self):
        """스트리밍 파이프라인 실행"""
        try:
            # 파일 관리자 초기화
            file_manager = AsyncFileManager()
            
            # 스트리밍 파이프라인 생성
            pipeline = StreamingPipeline(
                tmdb_provider=self.tmdb_provider,
                file_manager=file_manager,
                target_directory=self.target_directory,
                folder_template=self.folder_template
            )
            
            self.logger.info(f"스트리밍 파이프라인 시작: {len(self.file_paths)}개 파일")
            
            # 파일별 처리
            for i, file_path in enumerate(self.file_paths):
                if self._cancelled:
                    break
                    
                try:
                    # 파일 처리
                    self.logger.info(f"[스트리밍] 파일 처리 시작 ({i+1}/{len(self.file_paths)}): {file_path.name}")
                    result = await pipeline.process_single_file(file_path)
                    
                    # 진행 상황 콜백
                    try:
                        message = f"처리 중: {file_path.name}"
                        if result.success:
                            message += " ✅"
                        else:
                            message += f" ❌ ({result.error_message})"
                            
                        self.signals.progress.emit(i + 1, len(self.file_paths), message)
                        self.signals.file_processed.emit(result)
                        
                        # 포스터 시그널 (메타데이터가 있고 포스터가 있는 경우)
                        if result.success and result.metadata and result.metadata.get("poster_path"):
                            poster_url = f"https://image.tmdb.org/t/p/w185{result.metadata['poster_path']}"
                            self.signals.poster_ready.emit(str(result.file_path), poster_url)
                        
                        # 로그 시그널
                        if result.success:
                            self.signals.log.emit(f"✅ {result.file_path.name} 처리 완료")
                        else:
                            self.signals.log.emit(f"❌ {result.file_path.name} 처리 실패: {result.error_message}")
                            
                    except Exception as callback_error:
                        self.logger.error(f"콜백 실행 중 오류: {callback_error}")
                    
                    # 에러 콜백
                    if not result.success:
                        try:
                            self.signals.error.emit(str(file_path), "ProcessingError", result.error_message or "Unknown error")
                        except Exception as callback_error:
                            self.logger.error(f"에러 콜백 실행 중 오류: {callback_error}")
                    
                    # 비동기 이벤트 루프에 제어권 양보 (UI 응답성 보장)
                    await asyncio.sleep(0)
                    
                except asyncio.CancelledError:
                    self.logger.info("스트리밍 파이프라인이 취소되었습니다.")
                    break
                except Exception as e:
                    self.logger.error(f"파일 처리 중 예외 발생: {file_path} - {e}")
                    
                    # 에러 결과 생성
                    error_result = ProcessingResult(
                        file_path=file_path,
                        clean_result=None,
                        metadata=None,
                        target_path=None,
                        success=False,
                        error_message=f"처리 중 예외 발생: {str(e)}"
                    )
                    
                    try:
                        self.signals.error.emit(str(file_path), "Exception", str(e))
                        self.signals.file_processed.emit(error_result)
                    except Exception as callback_error:
                        self.logger.error(f"에러 콜백 실행 중 오류: {callback_error}")
            
            # 완료 시그널
            if not self._cancelled:
                final_stats = {"total_files": len(self.file_paths), "completed": True}
                self.signals.finished.emit(final_stats)
            else:
                self.signals.cancelled.emit()
                
        except Exception as e:
            self.logger.error(f"워커 초기화 중 오류: {e}")
            self.signals.error.emit("", "WorkerError", str(e))
            
    def cancel(self):
        """작업 취소"""
        self._cancelled = True
        self.logger.info("스트리밍 워커 취소 요청됨")

class StreamingWorkerManager:
    """스트리밍 워커 관리자"""
    
    def __init__(self):
        """StreamingWorkerManager 초기화"""
        self.current_worker = None
        self.thread_pool = QThreadPool.globalInstance()
        self.logger = get_logger(__name__)
        
    def start_processing(self, 
                        file_paths: List[Path],
                        tmdb_provider: TMDBProvider,
                        target_directory: Path,
                        folder_template: str = "{title} ({year})",
                        progress_callback=None,
                        error_callback=None,
                        finished_callback=None,
                        cancelled_callback=None,
                        log_callback=None,
                        poster_callback=None) -> StreamingWorker:
        """
        스트리밍 처리 시작
        
        Args:
            file_paths: 처리할 파일 경로 목록
            tmdb_provider: TMDB 메타데이터 제공자
            target_directory: 대상 디렉토리
            folder_template: 폴더 이름 템플릿
            progress_callback: 진행 상황 콜백
            error_callback: 에러 콜백
            finished_callback: 완료 콜백
            cancelled_callback: 취소 콜백
            log_callback: 로그 콜백
            poster_callback: 포스터 콜백
            
        Returns:
            StreamingWorker: 생성된 워커 인스턴스
        """
        # 기존 워커가 있으면 취소
        if self.current_worker:
            self.current_worker.cancel()
            
        # 새 워커 생성
        worker = StreamingWorker(
            file_paths=file_paths,
            tmdb_provider=tmdb_provider,
            target_directory=target_directory,
            folder_template=folder_template
        )
        
        # 시그널 연결
        if progress_callback:
            worker.signals.progress.connect(progress_callback)
        if error_callback:
            worker.signals.error.connect(error_callback)
        if finished_callback:
            worker.signals.finished.connect(finished_callback)
        if cancelled_callback:
            worker.signals.cancelled.connect(cancelled_callback)
        if log_callback:
            worker.signals.log.connect(log_callback)
        if poster_callback:
            worker.signals.poster_ready.connect(poster_callback)
            
        # 워커 시작
        self.thread_pool.start(worker)
        self.current_worker = worker
        
        self.logger.info(f"스트리밍 처리 시작: {len(file_paths)}개 파일")
        return worker
        
    def cancel_processing(self):
        """현재 처리 취소"""
        if self.current_worker:
            self.current_worker.cancel()
            self.logger.info("스트리밍 처리 취소 요청됨")
            
    def is_processing(self) -> bool:
        """현재 처리 중인지 확인"""
        return self.current_worker is not None and not self.current_worker._cancelled 