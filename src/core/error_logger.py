"""
상세 오류 로깅 시스템

파일 처리 과정에서 발생하는 오류를 상세하게 로깅하는 시스템을 제공합니다.
오류 정보, 파일명, 함수명, 스택 트레이스 등을 포함한 구조화된 로깅을 지원합니다.
"""

import logging
import traceback
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class ErrorSeverity(Enum):
    """오류 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """오류 카테고리"""
    FILENAME_CLEANING = "filename_cleaning"
    METADATA_SEARCH = "metadata_search"
    PATH_DETERMINATION = "path_determination"
    FILE_MOVE = "file_move"
    NETWORK = "network"
    PERMISSION = "permission"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """오류 정보"""
    timestamp: datetime
    file_path: str
    error_type: str
    error_message: str
    error_category: ErrorCategory
    severity: ErrorSeverity
    function_name: str
    stack_trace: str
    context: Dict[str, Any]
    processing_step: str
    original_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['error_category'] = self.error_category.value
        data['severity'] = self.severity.value
        return data


class ErrorLogger:
    """
    상세 오류 로거
    
    파일 처리 과정에서 발생하는 오류를 상세하게 로깅합니다.
    """
    
    def __init__(self, log_file: Optional[Path] = None, max_errors: int = 1000):
        """
        ErrorLogger 초기화
        
        Args:
            log_file: 로그 파일 경로 (None이면 기본 경로 사용)
            max_errors: 최대 저장 오류 수
        """
        self.log_file = log_file or Path("logs/errors.log")
        self.max_errors = max_errors
        self.errors: List[ErrorInfo] = []
        
        # 로그 디렉토리 생성
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 로거 설정
        self._setup_logger()
        
    def _setup_logger(self):
        """로거 설정"""
        # 파일 핸들러
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.ERROR)
        
        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # 로거에 핸들러 추가
        self.logger = logging.getLogger('error_logger')
        self.logger.setLevel(logging.ERROR)
        self.logger.addHandler(file_handler)
        
    def log_error(
        self,
        file_path: Path,
        error: Exception,
        processing_step: str,
        context: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> ErrorInfo:
        """
        오류 로깅
        
        Args:
            file_path: 오류가 발생한 파일 경로
            error: 발생한 오류
            processing_step: 처리 단계
            context: 추가 컨텍스트 정보
            severity: 오류 심각도
            
        Returns:
            ErrorInfo: 로깅된 오류 정보
        """
        # 오류 카테고리 결정
        error_category = self._determine_error_category(error, processing_step)
        
        # 오류 정보 생성
        error_info = ErrorInfo(
            timestamp=datetime.now(),
            file_path=str(file_path),
            error_type=type(error).__name__,
            error_message=str(error),
            error_category=error_category,
            severity=severity,
            function_name=self._get_calling_function(),
            stack_trace=traceback.format_exc(),
            context=context or {},
            processing_step=processing_step,
            original_error=str(error) if error else None
        )
        
        # 오류 목록에 추가
        self.errors.append(error_info)
        
        # 최대 오류 수 제한
        if len(self.errors) > self.max_errors:
            self.errors.pop(0)
        
        # 로그 파일에 기록
        self._write_to_log_file(error_info)
        
        # 콘솔에 출력
        self._log_to_console(error_info)
        
        return error_info
        
    def _determine_error_category(self, error: Exception, processing_step: str) -> ErrorCategory:
        """오류 카테고리 결정"""
        error_type = type(error).__name__.lower()
        step_lower = processing_step.lower()
        
        # 처리 단계 기반 분류
        if "clean" in step_lower or "filename" in step_lower:
            return ErrorCategory.FILENAME_CLEANING
        elif "metadata" in step_lower or "search" in step_lower:
            return ErrorCategory.METADATA_SEARCH
        elif "path" in step_lower or "determine" in step_lower:
            return ErrorCategory.PATH_DETERMINATION
        elif "move" in step_lower or "file" in step_lower:
            return ErrorCategory.FILE_MOVE
            
        # 오류 타입 기반 분류
        if "permission" in error_type or "access" in error_type:
            return ErrorCategory.PERMISSION
        elif "network" in error_type or "connection" in error_type:
            return ErrorCategory.NETWORK
        elif "validation" in error_type or "value" in error_type:
            return ErrorCategory.VALIDATION
            
        return ErrorCategory.UNKNOWN
        
    def _get_calling_function(self) -> str:
        """호출 함수명 가져오기"""
        try:
            # 스택 트레이스에서 호출 함수명 추출
            stack = traceback.extract_stack()
            if len(stack) >= 3:
                return stack[-3].name
        except:
            pass
        return "unknown"
        
    def _write_to_log_file(self, error_info: ErrorInfo):
        """로그 파일에 기록"""
        try:
            # JSON 형태로 로그 파일에 추가
            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(error_info.to_dict(), f, ensure_ascii=False, indent=2)
                f.write('\n---\n')
        except Exception as e:
            # 로그 파일 쓰기 실패 시 콘솔에 출력
            print(f"Failed to write to log file: {e}")
            
    def _log_to_console(self, error_info: ErrorInfo):
        """콘솔에 로그 출력"""
        log_message = (
            f"ERROR [{error_info.error_category.value.upper()}] "
            f"File: {error_info.file_path} | "
            f"Step: {error_info.processing_step} | "
            f"Message: {error_info.error_message}"
        )
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
            
    def get_errors_by_category(self, category: ErrorCategory) -> List[ErrorInfo]:
        """카테고리별 오류 조회"""
        return [error for error in self.errors if error.error_category == category]
        
    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[ErrorInfo]:
        """심각도별 오류 조회"""
        return [error for error in self.errors if error.severity == severity]
        
    def get_errors_by_file(self, file_path: Path) -> List[ErrorInfo]:
        """파일별 오류 조회"""
        return [error for error in self.errors if error.file_path == str(file_path)]
        
    def get_error_summary(self) -> Dict[str, Any]:
        """오류 요약 정보"""
        total_errors = len(self.errors)
        
        # 카테고리별 통계
        category_stats = {}
        for category in ErrorCategory:
            count = len(self.get_errors_by_category(category))
            if count > 0:
                category_stats[category.value] = count
                
        # 심각도별 통계
        severity_stats = {}
        for severity in ErrorSeverity:
            count = len(self.get_errors_by_severity(severity))
            if count > 0:
                severity_stats[severity.value] = count
                
        return {
            'total_errors': total_errors,
            'category_stats': category_stats,
            'severity_stats': severity_stats,
            'latest_error': self.errors[-1].to_dict() if self.errors else None
        }
        
    def clear_errors(self):
        """오류 목록 초기화"""
        self.errors.clear()
        
    def export_errors(self, export_file: Path) -> bool:
        """오류 목록을 파일로 내보내기"""
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump([error.to_dict() for error in self.errors], f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Failed to export errors: {e}")
            return False


# 전역 오류 로거 인스턴스
_global_error_logger: Optional[ErrorLogger] = None


def get_error_logger() -> ErrorLogger:
    """전역 오류 로거 인스턴스 반환"""
    global _global_error_logger
    if _global_error_logger is None:
        _global_error_logger = ErrorLogger()
    return _global_error_logger


def log_error(
    file_path: Path,
    error: Exception,
    processing_step: str,
    context: Optional[Dict[str, Any]] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
) -> ErrorInfo:
    """
    전역 오류 로깅 함수
    
    Args:
        file_path: 오류가 발생한 파일 경로
        error: 발생한 오류
        processing_step: 처리 단계
        context: 추가 컨텍스트 정보
        severity: 오류 심각도
        
    Returns:
        ErrorInfo: 로깅된 오류 정보
    """
    return get_error_logger().log_error(file_path, error, processing_step, context, severity) 