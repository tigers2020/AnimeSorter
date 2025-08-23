"""
구조화된 로깅 시스템

JSON 형태의 구조화된 로그, 로그 레벨별 필터링, 로그 로테이션, 성능 로깅을 포함합니다.
"""

import json
import logging
import logging.handlers
import sys
import time
import traceback
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QMutex, QMutexLocker, QObject, pyqtSignal


class LogLevel:
    """로그 레벨 상수"""

    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogCategory:
    """로그 카테고리 상수"""

    SYSTEM = "system"
    USER = "user"
    PERFORMANCE = "performance"
    SECURITY = "security"
    NETWORK = "network"
    DATABASE = "database"
    FILE_OPERATION = "file_operation"
    TMDB = "tmdb"
    UI = "ui"
    BACKGROUND = "background"


class PerformanceMetric:
    """성능 메트릭 데이터 클래스"""

    def __init__(
        self,
        operation: str,
        start_time: float,
        end_time: float,
        success: bool,
        metadata: dict[str, Any] | None = None,
    ):
        self.operation = operation
        self.start_time = start_time
        self.end_time = end_time
        self.duration = end_time - start_time
        self.success = success
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "operation": self.operation,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "success": self.success,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class StructuredFormatter(logging.Formatter):
    """구조화된 JSON 로그 포맷터"""

    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_category: bool = True,
        include_thread: bool = True,
        include_process: bool = True,
    ):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_category = include_timestamp
        self.include_thread = include_thread
        self.include_process = include_process

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 형식으로 포맷"""
        log_entry = {
            "message": record.getMessage(),
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "module": record.module,
        }

        if self.include_timestamp:
            log_entry["timestamp"] = datetime.fromtimestamp(record.created).isoformat()

        if self.include_level:
            log_entry["level"] = record.levelname
            log_entry["level_number"] = record.levelno

        if self.include_category and hasattr(record, "category"):
            log_entry["category"] = record.category

        if self.include_thread and hasattr(record, "threadName"):
            log_entry["thread"] = record.threadName

        if self.include_process and hasattr(record, "process"):
            log_entry["process"] = record.process

        # 예외 정보가 있으면 추가
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # 추가 필드가 있으면 추가
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """향상된 로그 로테이션 핸들러"""

    def __init__(
        self,
        filename: str,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        encoding: str = "utf-8",
    ):
        super().__init__(filename, maxBytes=max_bytes, backupCount=backup_count, encoding=encoding)
        self.filename = filename
        self.max_bytes = max_bytes
        self.backup_count = backup_count

    def do_rollover(self) -> None:
        """로그 로테이션 수행"""
        if self.stream:
            self.stream.close()
            self.stream = None  # type: ignore[assignment]

        # 기존 백업 파일들을 한 단계씩 이동
        for i in range(self.backup_count - 1, 0, -1):
            sfn = Path(f"{self.filename}.{i}")
            dfn = Path(f"{self.filename}.{i + 1}")
            if sfn.exists():
                if dfn.exists():
                    dfn.unlink()
                sfn.rename(dfn)

        # 현재 로그 파일을 .1로 이동
        dfn = Path(f"{self.filename}.1")
        if dfn.exists():
            dfn.unlink()
        if Path(self.filename).exists():
            Path(self.filename).rename(dfn)

        # 새 로그 파일 생성
        if not self.delay:
            self.stream = self._open()


class PerformanceLogger:
    """성능 로깅 전용 클래스"""

    def __init__(self, logger: "StructuredLogger"):
        self.logger = logger
        self.metrics: list[PerformanceMetric] = []
        self._lock = QMutex()

    @contextmanager
    def measure(
        self,
        operation: str,
        category: str = LogCategory.PERFORMANCE,
        metadata: dict[str, Any] | None = None,
    ):
        """성능 측정을 위한 컨텍스트 매니저"""
        start_time = time.time()
        success = False

        try:
            yield
            success = True
        except Exception:
            success = False
            raise
        finally:
            end_time = time.time()
            metric = PerformanceMetric(operation, start_time, end_time, success, metadata)

            with QMutexLocker(self._lock):
                self.metrics.append(metric)

            # 성능 로그 기록
            level = LogLevel.INFO if success else LogLevel.WARNING
            self.logger.log(
                level,
                f"성능 측정 완료: {operation}",
                category=category,
                extra_fields={"performance_metric": metric.to_dict()},
            )

    def performance_decorator(
        self, operation: str | None = None, category: str = LogCategory.PERFORMANCE
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """성능 측정을 위한 데코레이터"""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                op_name = operation or f"{func.__module__}.{func.__name__}"
                with self.measure(op_name, category):
                    return func(*args, **kwargs)

            return wrapper

        return decorator

    def get_performance_summary(
        self, operation: str | None = None, time_range: timedelta | None = None
    ) -> dict[str, Any]:
        """성능 요약 통계 반환"""
        with QMutexLocker(self._lock):
            metrics = self.metrics.copy()

        if operation:
            metrics = [m for m in metrics if m.operation == operation]

        if time_range:
            cutoff_time = datetime.now() - time_range
            metrics = [m for m in metrics if m.timestamp > cutoff_time]

        if not metrics:
            return {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "average_duration": 0.0,
                "min_duration": 0.0,
                "max_duration": 0.0,
            }

        successful = [m for m in metrics if m.success]
        failed = [m for m in metrics if not m.success]
        durations = [m.duration for m in metrics]

        return {
            "total_operations": len(metrics),
            "successful_operations": len(successful),
            "failed_operations": len(failed),
            "success_rate": len(successful) / len(metrics) * 100,
            "average_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "total_duration": sum(durations),
        }

    def clear_metrics(self) -> None:
        """성능 메트릭 초기화"""
        with QMutexLocker(self._lock):
            self.metrics.clear()


class StructuredLogger(QObject):
    """구조화된 로깅 시스템의 메인 클래스"""

    # 시그널 정의
    log_message = pyqtSignal(str, str, str)  # level, category, message
    performance_metric = pyqtSignal(dict)  # PerformanceMetric

    def __init__(
        self,
        name: str = "AnimeSorter",
        log_dir: str | None = None,
        log_level: int = LogLevel.INFO,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_console: bool = True,
        enable_file: bool = True,
    ):
        super().__init__()

        self.name = name
        self.log_level = log_level
        self.max_file_size = max_file_size
        self.backup_count = backup_count

        # 로그 디렉토리 설정
        if log_dir is None:
            self.log_dir = Path.home() / ".animesorter" / "logs"
        elif isinstance(log_dir, str):
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 로거 설정
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # 콘솔 핸들러
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = StructuredFormatter(
                include_timestamp=True,
                include_level=True,
                include_category=True,
                include_thread=False,
                include_process=False,
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(log_level)
            self.logger.addHandler(console_handler)

        # 파일 핸들러
        if enable_file:
            # 일반 로그 파일
            general_log_file = self.log_dir / f"{name.lower()}.log"
            general_handler = RotatingFileHandler(
                str(general_log_file), max_bytes=max_file_size, backup_count=backup_count
            )
            general_formatter = StructuredFormatter()
            general_handler.setFormatter(general_formatter)
            general_handler.setLevel(log_level)
            self.logger.addHandler(general_handler)

            # 에러 로그 파일
            error_log_file = self.log_dir / f"{name.lower()}_error.log"
            error_handler = RotatingFileHandler(
                str(error_log_file), max_bytes=max_file_size, backup_count=backup_count
            )
            error_formatter = StructuredFormatter()
            error_handler.setFormatter(error_formatter)
            error_handler.setLevel(LogLevel.ERROR)
            self.logger.addHandler(error_handler)

            # 성능 로그 파일
            performance_log_file = self.log_dir / f"{name.lower()}_performance.log"
            performance_handler = RotatingFileHandler(
                str(performance_log_file), max_bytes=max_file_size, backup_count=backup_count
            )
            performance_formatter = StructuredFormatter()
            performance_handler.setFormatter(performance_formatter)
            performance_handler.setLevel(LogLevel.INFO)
            self.logger.addHandler(performance_handler)

        # 성능 로거 초기화
        self.performance_logger = PerformanceLogger(self)

        # 로그 레벨별 메서드들
        self.trace = lambda msg, **kwargs: self.log(LogLevel.TRACE, msg, **kwargs)
        self.debug = lambda msg, **kwargs: self.log(LogLevel.DEBUG, msg, **kwargs)
        self.info = lambda msg, **kwargs: self.log(LogLevel.INFO, msg, **kwargs)
        self.warning = lambda msg, **kwargs: self.log(LogLevel.WARNING, msg, **kwargs)
        self.error = lambda msg, **kwargs: self.log(LogLevel.ERROR, msg, **kwargs)
        self.critical = lambda msg, **kwargs: self.log(LogLevel.CRITICAL, msg, **kwargs)

    def log(
        self,
        level: int,
        message: str,
        category: str = LogCategory.SYSTEM,
        extra_fields: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """로그 메시지 기록"""
        # LogRecord에 추가 필드 설정
        record = self.logger.makeRecord(self.logger.name, level, "", 0, message, (), None)

        # category 속성 설정 (안전한 방법)
        if hasattr(record, "category"):
            record.category = category

        # extra_fields와 kwargs를 로그 메시지에 포함
        all_extra = {}
        if extra_fields:
            all_extra.update(extra_fields)
        if kwargs:
            all_extra.update(kwargs)

        # 로그 기록
        self.logger.handle(record)

        # 시그널 발생
        level_name = logging.getLevelName(level)
        self.log_message.emit(level_name, category, message)

    def log_exception(
        self,
        exception: Exception,
        message: str | None = None,
        category: str = LogCategory.SYSTEM,
        level: int = LogLevel.ERROR,
    ) -> None:
        """예외 정보와 함께 로그 기록"""
        exc_info = sys.exc_info()
        if exc_info[0] is None:
            exc_info = (type(exception), exception, exception.__traceback__)  # type: ignore[assignment]
        else:
            # 타입 안전성을 위해 명시적 캐스팅
            exc_info = (exc_info[0], exc_info[1], exc_info[2])  # type: ignore[assignment]

        extra_fields = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": "".join(traceback.format_exception(*exc_info)),
        }

        self.log(level, message or str(exception), category, extra_fields)

    def set_level(self, level: int) -> None:
        """로그 레벨 설정"""
        self.log_level = level
        self.logger.setLevel(level)

        # 모든 핸들러의 레벨도 업데이트
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)

    def get_log_files(self) -> list[Path]:
        """로그 파일 목록 반환"""
        log_files = []
        for file_path in self.log_dir.glob("*.log*"):
            log_files.append(file_path)
        return sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)

    def get_log_content(self, file_path: str | Path, max_lines: int | None = None) -> str:
        """로그 파일 내용 읽기"""
        file_path = Path(file_path)
        if not file_path.exists():
            return ""

        try:
            with file_path.open(encoding="utf-8") as f:
                if max_lines:
                    lines = f.readlines()[-max_lines:]
                    return "".join(lines)
                return f.read()
        except Exception as e:
            return f"로그 파일 읽기 실패: {e}"

    def clear_logs(self, keep_recent: int = 1) -> None:
        """오래된 로그 파일 정리"""
        log_files = self.get_log_files()

        # 최신 파일들을 제외하고 삭제
        for file_path in log_files[keep_recent:]:
            try:
                file_path.unlink()
                self.info(f"로그 파일 삭제: {file_path.name}", category=LogCategory.SYSTEM)
            except Exception as e:
                self.error(
                    f"로그 파일 삭제 실패: {file_path.name}",
                    category=LogCategory.SYSTEM,
                    error=str(e),
                )

    def export_logs(
        self,
        output_path: str | Path,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        level: int | None = None,
        category: str | None = None,
    ) -> bool:
        """로그 내보내기"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            exported_logs = []

            for log_file in self.get_log_files():
                content = self.get_log_content(log_file)

                # JSON 라인별 파싱 및 필터링
                for line in content.strip().split("\n"):
                    if not line.strip():
                        continue

                    try:
                        log_entry = json.loads(line)

                        # 시간 필터링
                        if start_time and "timestamp" in log_entry:
                            entry_time = datetime.fromisoformat(log_entry["timestamp"])
                            if entry_time < start_time:
                                continue

                        if end_time and "timestamp" in log_entry:
                            entry_time = datetime.fromisoformat(log_entry["timestamp"])
                            if entry_time > end_time:
                                continue

                        # 레벨 필터링
                        if level and log_entry.get("level_number", 0) < level:
                            continue

                        # 카테고리 필터링
                        if category and log_entry.get("category") != category:
                            continue

                        exported_logs.append(log_entry)

                    except json.JSONDecodeError:
                        continue

            # JSON 파일로 저장
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(exported_logs, f, ensure_ascii=False, indent=2, default=str)

            self.info(
                f"로그 내보내기 완료: {len(exported_logs)}개 항목",
                category=LogCategory.SYSTEM,
                output_path=str(output_path),
            )
            return True

        except Exception as e:
            self.error("로그 내보내기 실패", category=LogCategory.SYSTEM, error=str(e))
            return False


# 전역 로거 인스턴스
_global_logger: StructuredLogger | None = None


def get_logger(name: str = "AnimeSorter", **kwargs: Any) -> StructuredLogger:
    """전역 로거 인스턴스 반환"""
    global _global_logger

    if _global_logger is None:
        _global_logger = StructuredLogger(name, **kwargs)

    return _global_logger


def initialize_logging(name: str = "AnimeSorter", **kwargs) -> StructuredLogger:
    """로깅 시스템 초기화"""
    global _global_logger

    if _global_logger is not None:
        _global_logger.logger.warning("로깅 시스템이 이미 초기화되었습니다.")
        return _global_logger

    _global_logger = StructuredLogger(name, **kwargs)
    _global_logger.info("로깅 시스템 초기화 완료", category=LogCategory.SYSTEM)

    return _global_logger


def get_performance_logger() -> PerformanceLogger:
    """성능 로거 반환"""
    logger = get_logger()
    return logger.performance_logger


# 편의 함수들
def trace(message: str, **kwargs: Any) -> None:
    """TRACE 레벨 로그"""
    logger = get_logger()
    logger.trace(message, **kwargs)


def debug(message: str, **kwargs: Any) -> None:
    """DEBUG 레벨 로그"""
    logger = get_logger()
    logger.debug(message, **kwargs)


def info(message: str, **kwargs: Any) -> None:
    """INFO 레벨 로그"""
    logger = get_logger()
    logger.info(message, **kwargs)


def warning(message: str, **kwargs: Any) -> None:
    """WARNING 레벨 로그"""
    logger = get_logger()
    logger.warning(message, **kwargs)


def error(message: str, **kwargs: Any) -> None:
    """ERROR 레벨 로그"""
    logger = get_logger()
    logger.error(message, **kwargs)


def critical(message: str, **kwargs: Any) -> None:
    """CRITICAL 레벨 로그"""
    logger = get_logger()
    logger.critical(message, **kwargs)


def log_exception(exception: Exception, message: str | None = None, **kwargs: Any) -> None:
    """예외 정보와 함께 로그 기록"""
    logger = get_logger()
    logger.log_exception(exception, message, **kwargs)


def performance_measure(
    operation: str, category: str = LogCategory.PERFORMANCE
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """성능 측정 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            performance_logger = get_performance_logger()
            with performance_logger.measure(operation, category):
                return func(*args, **kwargs)

        return wrapper

    return decorator
