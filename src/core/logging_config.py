"""
로깅 시스템 설정 및 구성 모듈

AnimeSorter 애플리케이션의 전역 로깅 시스템을 설정하고 관리합니다.
"""

import logging

logger = logging.getLogger(__name__)
from pathlib import Path

from src.core.structured_logging import (LogCategory, LogLevel,
                                         StructuredLogger, get_logger,
                                         initialize_logging)

_global_logger: StructuredLogger | None = None


class LoggingConfig:
    """로깅 시스템 설정 클래스"""

    DEFAULT_LOG_LEVEL = LogLevel.INFO
    DEFAULT_LOG_DIR = Path.home() / ".animesorter" / "logs"
    DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024
    DEFAULT_BACKUP_COUNT = 5
    PRINT_TO_LOG_LEVEL_MAPPING = {
        "🔧": LogLevel.DEBUG,
        "✅": LogLevel.INFO,
        "ℹ️": LogLevel.INFO,
        "📝": LogLevel.INFO,
        "⚠️": LogLevel.WARNING,
        "🚨": LogLevel.WARNING,
        "❌": LogLevel.ERROR,
        "💥": LogLevel.ERROR,
        "🔥": LogLevel.CRITICAL,
        "🎯": LogLevel.DEBUG,
        "🚀": LogLevel.INFO,
        "🏁": LogLevel.INFO,
    }
    PATH_TO_CATEGORY_MAPPING = {
        "main_window": LogCategory.UI,
        "gui": LogCategory.UI,
        "managers": LogCategory.SYSTEM,
        "services": LogCategory.SYSTEM,
        "tmdb": LogCategory.TMDB,
        "file_operation": LogCategory.FILE_OPERATION,
        "file_parser": LogCategory.FILE_OPERATION,
        "network": LogCategory.NETWORK,
        "database": LogCategory.DATABASE,
        "security": LogCategory.SECURITY,
        "performance": LogCategory.PERFORMANCE,
        "background": LogCategory.BACKGROUND,
    }

    @classmethod
    def get_log_level_from_print_content(cls, content: str) -> int:
        """print() 문 내용을 기반으로 로그 레벨 결정"""
        content = content.strip()
        for emoji, level in cls.PRINT_TO_LOG_LEVEL_MAPPING.items():
            if emoji in content:
                return level
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in ["error", "failed", "실패", "오류", "에러"]):
            return LogLevel.ERROR
        if any(keyword in content_lower for keyword in ["warning", "경고", "주의"]):
            return LogLevel.WARNING
        if any(keyword in content_lower for keyword in ["debug", "디버그", "초기화", "설정"]):
            return LogLevel.DEBUG
        if any(keyword in content_lower for keyword in ["success", "완료", "성공"]):
            return LogLevel.INFO
        return LogLevel.INFO

    @classmethod
    def get_category_from_file_path(cls, file_path: str) -> str:
        """파일 경로를 기반으로 로그 카테고리 결정"""
        file_path_lower = file_path.lower()
        for keyword, category in cls.PATH_TO_CATEGORY_MAPPING.items():
            if keyword in file_path_lower:
                return category
        return LogCategory.SYSTEM

    @classmethod
    def initialize_application_logging(
        cls,
        log_level: int = None,
        log_dir: str = None,
        enable_console: bool = True,
        enable_file: bool = True,
    ) -> StructuredLogger:
        """애플리케이션 로깅 시스템 초기화"""
        if log_level is None:
            log_level = cls.DEFAULT_LOG_LEVEL
        if log_dir is None:
            log_dir = str(cls.DEFAULT_LOG_DIR)
        logger = initialize_logging(
            name="AnimeSorter",
            log_level=log_level,
            log_dir=log_dir,
            max_file_size=cls.DEFAULT_MAX_FILE_SIZE,
            backup_count=cls.DEFAULT_BACKUP_COUNT,
            enable_console=enable_console,
            enable_file=enable_file,
        )
        cls._setup_python_logging_integration(logger)
        return logger

    @classmethod
    def _setup_python_logging_integration(cls, structured_logger: StructuredLogger):
        """Python 표준 logging 시스템과 통합"""
        root_logger = logging.getLogger()
        root_logger.setLevel(structured_logger.log_level)
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        for handler in structured_logger.logger.handlers:
            root_logger.addHandler(handler)
        structured_logger.info(
            "로깅 시스템 통합 완료",
            category=LogCategory.SYSTEM,
            extra={
                "log_level": structured_logger.log_level,
                "log_dir": str(structured_logger.log_dir),
                "handlers_count": len(structured_logger.logger.handlers),
            },
        )


def get_application_logger() -> StructuredLogger:
    """애플리케이션 전역 로거 반환"""
    return get_logger("AnimeSorter")


def setup_logging_for_module(module_name: str) -> StructuredLogger:
    """모듈별 로거 설정"""
    return get_logger(f"AnimeSorter.{module_name}")


def initialize_global_logging(**kwargs) -> StructuredLogger:
    """전역 로깅 시스템 초기화"""
    global _global_logger
    if _global_logger is None:
        _global_logger = LoggingConfig.initialize_application_logging(**kwargs)
    return _global_logger


def get_global_logger() -> StructuredLogger:
    """전역 로거 반환"""
    global _global_logger
    if _global_logger is None:
        _global_logger = initialize_global_logging()
    return _global_logger
