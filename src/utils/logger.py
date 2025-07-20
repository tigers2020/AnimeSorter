"""
AnimeSorter 로깅 시스템

로테이팅 로그 핸들러와 구조화된 로깅 포맷을 제공하는 고급 로깅 시스템입니다.
멀티프로세싱 환경에서 QueueHandler를 사용하여 데드락을 방지합니다.
"""

import logging
import logging.handlers
import os
import sys
import multiprocessing
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from src.exceptions import ConfigError


class AnimeSorterFormatter(logging.Formatter):
    """AnimeSorter 전용 로그 포맷터"""
    
    def __init__(self, include_timestamp: bool = True, include_module: bool = True):
        """
        포맷터 초기화
        
        Args:
            include_timestamp: 타임스탬프 포함 여부
            include_module: 모듈명 포함 여부
        """
        self.include_timestamp = include_timestamp
        self.include_module = include_module
        
        # 기본 포맷 구성
        format_parts = []
        
        if include_timestamp:
            format_parts.append("%(asctime)s")
        
        format_parts.append("[%(levelname)s]")
        
        if include_module:
            format_parts.append("%(name)s")
        
        format_parts.append("- %(message)s")
        
        super().__init__(" ".join(format_parts), datefmt="%Y-%m-%d %H:%M:%S")
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드 포맷팅"""
        # 예외 정보가 있는 경우 추가
        if record.exc_info:
            # 원본 포맷 적용
            formatted = super().format(record)
            # 예외 정보 추가
            formatted += f"\n{self.formatException(record.exc_info)}"
            return formatted
        
        return super().format(record)


class QueueLogListener:
    """Queue 기반 로그 리스너 (멀티프로세싱 안전)"""
    
    def __init__(self, log_dir: Path, max_file_size: int = 5 * 1024 * 1024, backup_count: int = 3):
        """
        Queue 로그 리스너 초기화
        
        Args:
            log_dir: 로그 디렉토리
            max_file_size: 최대 파일 크기
            backup_count: 백업 파일 개수
        """
        self.log_dir = log_dir
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.queue = multiprocessing.Queue(-1)
        self.listener = None
        
    def start(self):
        """리스너 시작"""
        # 파일 핸들러들 생성
        main_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "animesorter.log",
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        main_handler.setFormatter(AnimeSorterFormatter(include_timestamp=True, include_module=True))
        
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "animesorter_error.log",
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(AnimeSorterFormatter(include_timestamp=True, include_module=True))
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(AnimeSorterFormatter(include_timestamp=True, include_module=False))
        
        # 리스너 생성 및 시작
        self.listener = logging.handlers.QueueListener(
            self.queue,
            main_handler,
            error_handler,
            console_handler,
            respect_handler_level=True
        )
        self.listener.start()
        
    def stop(self):
        """리스너 중지"""
        if self.listener:
            self.listener.stop()
            
    def get_queue(self):
        """로그 큐 반환"""
        return self.queue


class AnimeSorterLogger:
    """AnimeSorter 로깅 시스템 관리 클래스"""
    
    def __init__(self, 
                 log_dir: str | Path = "logs",
                 max_file_size: int = 5 * 1024 * 1024,  # 5MB
                 backup_count: int = 3,
                 log_level: str = "INFO",
                 use_queue_handler: bool = True):
        """
        로거 초기화
        
        Args:
            log_dir: 로그 파일 저장 디렉토리
            max_file_size: 최대 로그 파일 크기 (바이트)
            backup_count: 백업 파일 개수
            log_level: 로그 레벨
            use_queue_handler: QueueHandler 사용 여부 (멀티프로세싱 환경)
        """
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.use_queue_handler = use_queue_handler
        
        # 로그 디렉토리 생성
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Queue 리스너 (멀티프로세싱 환경용)
        self.queue_listener = None
        
        # 루트 로거 설정
        self._setup_root_logger()
        
        # 로거 인스턴스 캐시
        self._loggers: Dict[str, logging.Logger] = {}
    
    def _setup_root_logger(self) -> None:
        """루트 로거 설정"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # 기존 핸들러 제거 및 닫기
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
        
        if self.use_queue_handler and multiprocessing.current_process().name == 'MainProcess':
            # 메인 프로세스에서 Queue 리스너 시작
            self.queue_listener = QueueLogListener(self.log_dir, self.max_file_size, self.backup_count)
            self.queue_listener.start()
            
            # 메인 프로세스용 핸들러 (콘솔 출력)
            console_handler = self._create_console_handler()
            root_logger.addHandler(console_handler)
            
        elif self.use_queue_handler:
            # 워커 프로세스에서 QueueHandler 사용
            if hasattr(self, 'queue_listener') and self.queue_listener:
                queue_handler = logging.handlers.QueueHandler(self.queue_listener.get_queue())
                root_logger.addHandler(queue_handler)
            else:
                # Queue 리스너가 없는 경우 기본 핸들러 사용
                self._setup_default_handlers(root_logger)
        else:
            # QueueHandler 사용하지 않는 경우 기본 핸들러 사용
            self._setup_default_handlers(root_logger)
    
    def _setup_default_handlers(self, root_logger: logging.Logger) -> None:
        """기본 핸들러 설정"""
        # 콘솔 핸들러 추가
        console_handler = self._create_console_handler()
        root_logger.addHandler(console_handler)
        
        # 파일 핸들러 추가
        file_handler = self._create_file_handler("animesorter.log")
        root_logger.addHandler(file_handler)
        
        # 에러 로그 핸들러 추가
        error_handler = self._create_file_handler("animesorter_error.log", level=logging.ERROR)
        root_logger.addHandler(error_handler)
    
    def _create_console_handler(self) -> logging.StreamHandler:
        """콘솔 핸들러 생성"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        
        # 콘솔용 포맷터 (간단한 형태)
        console_formatter = AnimeSorterFormatter(include_timestamp=True, include_module=False)
        console_handler.setFormatter(console_formatter)
        
        return console_handler
    
    def _create_file_handler(self, filename: str, level: Optional[int] = None) -> logging.handlers.RotatingFileHandler:
        """로테이팅 파일 핸들러 생성"""
        log_file = self.log_dir / filename
        
        # 로테이팅 핸들러 생성
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        
        file_handler.setLevel(level or self.log_level)
        
        # 파일용 포맷터 (상세한 형태)
        file_formatter = AnimeSorterFormatter(include_timestamp=True, include_module=True)
        file_handler.setFormatter(file_formatter)
        
        return file_handler
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        특정 모듈용 로거 가져오기
        
        Args:
            name: 로거 이름 (보통 __name__ 사용)
            
        Returns:
            logging.Logger: 로거 인스턴스
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def set_log_level(self, level: str) -> None:
        """
        로그 레벨 설정
        
        Args:
            level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        try:
            new_level = getattr(logging, level.upper())
            self.log_level = new_level
            
            # 모든 핸들러의 레벨 업데이트
            root_logger = logging.getLogger()
            for handler in root_logger.handlers:
                if not isinstance(handler, logging.handlers.RotatingFileHandler) or \
                   "error" not in handler.baseFilename:
                    handler.setLevel(new_level)
            
            root_logger.setLevel(new_level)
            
        except AttributeError:
            raise ConfigError(f"Invalid log level: {level}")
    
    def add_custom_handler(self, handler: logging.Handler) -> None:
        """
        사용자 정의 핸들러 추가
        
        Args:
            handler: 추가할 로그 핸들러
        """
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
    
    def remove_handler(self, handler: logging.Handler) -> None:
        """
        핸들러 제거
        
        Args:
            handler: 제거할 로그 핸들러
        """
        root_logger = logging.getLogger()
        root_logger.removeHandler(handler)
    
    def get_log_files(self) -> Dict[str, Path]:
        """
        현재 로그 파일 목록 조회
        
        Returns:
            dict: 로그 파일명과 경로
        """
        log_files = {}
        
        for file_path in self.log_dir.glob("*.log*"):
            log_files[file_path.name] = file_path
        
        return log_files
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """
        오래된 로그 파일 정리
        
        Args:
            days: 보관할 일수
            
        Returns:
            int: 삭제된 파일 수
        """
        import time
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        deleted_count = 0
        
        for file_path in self.log_dir.glob("*.log*"):
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except OSError as e:
                    logging.warning(f"Failed to delete old log file {file_path}: {e}")
        
        return deleted_count
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        로그 통계 정보 조회
        
        Returns:
            dict: 로그 통계 정보
        """
        stats = {
            'log_directory': str(self.log_dir),
            'total_files': 0,
            'total_size': 0,
            'files': {}
        }
        
        for file_path in self.log_dir.glob("*.log*"):
            try:
                file_size = file_path.stat().st_size
                stats['total_files'] += 1
                stats['total_size'] += file_size
                stats['files'][file_path.name] = {
                    'size': file_size,
                    'size_mb': round(file_size / (1024 * 1024), 2),
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
            except OSError:
                continue
        
        return stats
    
    def archive_logs(self, archive_name: Optional[str] = None) -> Path:
        """
        로그 파일 아카이브 생성
        
        Args:
            archive_name: 아카이브 파일명 (None이면 자동 생성)
            
        Returns:
            Path: 아카이브 파일 경로
        """
        import zipfile
        import tempfile
        
        if archive_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"animesorter_logs_{timestamp}.zip"
        
        archive_path = self.log_dir / archive_name
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in self.log_dir.glob("*.log*"):
                if file_path != archive_path:
                    zipf.write(file_path, file_path.name)
        
        return archive_path


# 전역 로거 인스턴스
_global_logger: Optional[AnimeSorterLogger] = None

def initialize_logging(log_dir: str | Path = "logs", 
                      log_level: str = "INFO",
                      max_file_size: int = 5 * 1024 * 1024,
                      backup_count: int = 3) -> AnimeSorterLogger:
    """
    전역 로깅 시스템 초기화 (싱글톤 패턴)
    
    Args:
        log_dir: 로그 디렉토리
        log_level: 로그 레벨
        max_file_size: 최대 파일 크기
        backup_count: 백업 파일 개수
        
    Returns:
        AnimeSorterLogger: 초기화된 로거 인스턴스
    """
    global _global_logger
    
    if _global_logger is None:
        _global_logger = AnimeSorterLogger(
            log_dir=log_dir,
            log_level=log_level,
            max_file_size=max_file_size,
            backup_count=backup_count
        )
    
    return _global_logger

def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거 반환 (전역 로거 사용)
    
    Args:
        name: 로거 이름 (보통 __name__)
        
    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    global _global_logger
    
    if _global_logger is None:
        # 전역 로거가 초기화되지 않은 경우 기본 설정으로 초기화
        initialize_logging()
    
    return _global_logger.get_logger(name)

def set_log_level(level: str) -> None:
    """전역 로그 레벨 설정"""
    global _global_logger
    
    if _global_logger is not None:
        _global_logger.set_log_level(level)

def get_log_stats() -> Dict[str, Any]:
    """로그 통계 반환"""
    global _global_logger
    
    if _global_logger is not None:
        return _global_logger.get_log_stats()
    
    return {}

# 사용 예시를 위한 데코레이터
def log_function_call(logger_name: str = None):
    """
    함수 호출을 로깅하는 데코레이터
    
    Args:
        logger_name: 로거 이름 (None이면 함수 모듈명 사용)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            
            # 함수 호출 로깅
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} returned {result}")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} raised {type(e).__name__}: {e}")
                raise
        
        return wrapper
    return decorator 