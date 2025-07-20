"""
스트리밍 파이프라인 오류 처리 및 로깅

스트리밍 파이프라인에서 발생하는 다양한 오류를 처리하고
적절한 로깅을 제공합니다.
"""

import asyncio
import logging
import traceback
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union, List

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """오류 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(Enum):
    """오류 타입"""
    FILE_ACCESS = "file_access"
    NETWORK = "network"
    API = "api"
    PARSING = "parsing"
    VALIDATION = "validation"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class PipelineError:
    """파이프라인 오류 정보"""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    file_path: Optional[Path] = None
    original_exception: Optional[Exception] = None
    timestamp: datetime = None
    context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class StreamingErrorHandler:
    """
    스트리밍 파이프라인 오류 처리기
    
    다양한 오류 타입을 처리하고 적절한 로깅을 제공합니다.
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        StreamingErrorHandler 초기화
        
        Args:
            log_file: 오류 로그 파일 경로 (옵션)
        """
        self.log_file = log_file
        self.error_count = 0
        self.error_history: List[PipelineError] = []
        self.logger = logging.getLogger(__name__)
        
        # 오류 로그 파일 설정
        if log_file:
            self._setup_error_log_file()
            
    def _setup_error_log_file(self):
        """오류 로그 파일 설정"""
        try:
            # 로그 디렉토리 생성
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 핸들러 추가
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.ERROR)
            
            # 포맷터 설정
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # 로거에 핸들러 추가
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"오류 로그 파일 설정 실패: {e}")
            
    def handle_error(
        self,
        error: Exception,
        error_type: ErrorType = ErrorType.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        file_path: Optional[Path] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PipelineError:
        """
        오류 처리
        
        Args:
            error: 발생한 예외
            error_type: 오류 타입
            severity: 오류 심각도
            file_path: 관련 파일 경로 (옵션)
            context: 추가 컨텍스트 정보 (옵션)
            
        Returns:
            PipelineError: 처리된 오류 정보
        """
        # 오류 메시지 생성
        message = self._create_error_message(error, error_type, file_path)
        
        # PipelineError 생성
        pipeline_error = PipelineError(
            error_type=error_type,
            severity=severity,
            message=message,
            file_path=file_path,
            original_exception=error,
            context=context
        )
        
        # 오류 기록
        self._log_error(pipeline_error)
        
        # 오류 통계 업데이트
        self.error_count += 1
        self.error_history.append(pipeline_error)
        
        return pipeline_error
        
    def _create_error_message(
        self, 
        error: Exception, 
        error_type: ErrorType, 
        file_path: Optional[Path]
    ) -> str:
        """오류 메시지 생성"""
        base_message = f"{error_type.value.upper()} 오류: {str(error)}"
        
        if file_path:
            base_message += f" (파일: {file_path.name})"
            
        return base_message
        
    def _log_error(self, pipeline_error: PipelineError):
        """오류 로깅"""
        try:
            # 로그 레벨 결정
            log_level = self._get_log_level(pipeline_error.severity)
            
            # 로그 메시지 생성
            log_message = self._create_log_message(pipeline_error)
            
            # 로깅
            self.logger.log(log_level, log_message)
            
            # 스택 트레이스 로깅 (HIGH 이상)
            if pipeline_error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                if pipeline_error.original_exception:
                    self.logger.debug(
                        f"스택 트레이스:\n{traceback.format_exc()}"
                    )
                    
        except Exception as e:
            print(f"오류 로깅 실패: {e}")
            
    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """심각도에 따른 로그 레벨 반환"""
        severity_map = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        return severity_map.get(severity, logging.ERROR)
        
    def _create_log_message(self, pipeline_error: PipelineError) -> str:
        """로그 메시지 생성"""
        message_parts = [
            f"[{pipeline_error.error_type.value.upper()}]",
            f"[{pipeline_error.severity.value.upper()}]",
            pipeline_error.message
        ]
        
        if pipeline_error.context:
            context_str = ", ".join([f"{k}={v}" for k, v in pipeline_error.context.items()])
            message_parts.append(f"(컨텍스트: {context_str})")
            
        return " ".join(message_parts)
        
    def get_error_summary(self) -> Dict[str, Any]:
        """오류 요약 정보 반환"""
        if not self.error_history:
            return {"total_errors": 0, "error_types": {}}
            
        # 오류 타입별 통계
        error_types = {}
        for error in self.error_history:
            error_type = error.error_type.value
            if error_type not in error_types:
                error_types[error_type] = 0
            error_types[error_type] += 1
            
        # 심각도별 통계
        severity_counts = {}
        for error in self.error_history:
            severity = error.severity.value
            if severity not in severity_counts:
                severity_counts[severity] = 0
            severity_counts[severity] += 1
            
        return {
            "total_errors": self.error_count,
            "error_types": error_types,
            "severity_counts": severity_counts,
            "first_error": self.error_history[0].timestamp.isoformat() if self.error_history else None,
            "last_error": self.error_history[-1].timestamp.isoformat() if self.error_history else None
        }
        
    def clear_error_history(self):
        """오류 히스토리 초기화"""
        self.error_history.clear()
        self.error_count = 0
        
    def should_continue_processing(self, error_count: int, max_errors: int = 10) -> bool:
        """
        오류 수에 따른 처리 계속 여부 결정
        
        Args:
            error_count: 현재까지의 오류 수
            max_errors: 최대 허용 오류 수
            
        Returns:
            bool: 처리 계속 여부
        """
        return error_count < max_errors
        
    def get_critical_errors(self) -> List[PipelineError]:
        """CRITICAL 심각도의 오류들 반환"""
        return [error for error in self.error_history if error.severity == ErrorSeverity.CRITICAL]
        
    def get_errors_by_type(self, error_type: ErrorType) -> List[PipelineError]:
        """특정 타입의 오류들 반환"""
        return [error for error in self.error_history if error.error_type == error_type]


# 편의 함수들
def classify_error(error: Exception) -> ErrorType:
    """예외를 오류 타입으로 분류"""
    error_str = str(error).lower()
    
    # 파일 접근 오류
    if any(keyword in error_str for keyword in ['permission', 'access', 'file', 'directory', 'path']):
        return ErrorType.FILE_ACCESS
        
    # 네트워크 오류
    if any(keyword in error_str for keyword in ['connection', 'timeout', 'network', 'http', 'request']):
        return ErrorType.NETWORK
        
    # API 오류
    if any(keyword in error_str for keyword in ['api', 'rate limit', 'quota', 'authentication']):
        return ErrorType.API
        
    # 파싱 오류
    if any(keyword in error_str for keyword in ['parse', 'json', 'xml', 'format', 'syntax']):
        return ErrorType.PARSING
        
    # 검증 오류
    if any(keyword in error_str for keyword in ['validation', 'invalid', 'required', 'missing']):
        return ErrorType.VALIDATION
        
    # 시스템 오류
    if any(keyword in error_str for keyword in ['memory', 'disk', 'system', 'resource']):
        return ErrorType.SYSTEM
        
    return ErrorType.UNKNOWN


def determine_severity(error: Exception, error_type: ErrorType) -> ErrorSeverity:
    """오류 심각도 결정"""
    error_str = str(error).lower()
    
    # CRITICAL: 시스템 레벨 오류
    if any(keyword in error_str for keyword in ['memory', 'disk full', 'system crash']):
        return ErrorSeverity.CRITICAL
        
    # HIGH: 중요한 기능 실패
    if error_type in [ErrorType.API, ErrorType.NETWORK]:
        return ErrorSeverity.HIGH
        
    # MEDIUM: 일반적인 오류
    if error_type in [ErrorType.FILE_ACCESS, ErrorType.PARSING, ErrorType.VALIDATION]:
        return ErrorSeverity.MEDIUM
        
    # LOW: 경고 수준
    return ErrorSeverity.LOW


# 비동기 오류 처리 데코레이터
def handle_async_errors(error_handler: StreamingErrorHandler):
    """비동기 함수 오류 처리 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_type = classify_error(e)
                severity = determine_severity(e, error_type)
                
                # 파일 경로 추출 (첫 번째 Path 인자)
                file_path = None
                for arg in args:
                    if isinstance(arg, Path):
                        file_path = arg
                        break
                        
                # 오류 처리
                pipeline_error = error_handler.handle_error(
                    error=e,
                    error_type=error_type,
                    severity=severity,
                    file_path=file_path
                )
                
                # 오류 재발생 (필요한 경우)
                if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                    raise e
                    
                return None
                
        return wrapper
    return decorator 