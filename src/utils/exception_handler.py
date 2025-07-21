"""
전역 예외 처리 시스템

sys.excepthook과 비동기 예외 처리기를 구현하여 애플리케이션 크래시를 방지하고
예상치 못한 오류를 안전하게 처리하는 시스템입니다.
"""

import sys
import os
import traceback
import threading
import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager

from ..exceptions import AnimeSorterError
from .error_messages import translate_error, ErrorContext, Language
from .logger import get_logger


class GlobalExceptionHandler:
    """전역 예외 처리기 클래스"""
    
    def __init__(self, 
                 crash_reports_dir: str | Path = "crash_reports",
                 enable_crash_reports: bool = True,
                 enable_user_friendly_errors: bool = True,
                 language: Language = Language.KOREAN):
        """
        전역 예외 처리기 초기화
        
        Args:
            crash_reports_dir: 크래시 리포트 저장 디렉토리
            enable_crash_reports: 크래시 리포트 생성 여부
            enable_user_friendly_errors: 사용자 친화적 오류 메시지 사용 여부
            language: 오류 메시지 언어
        """
        self.crash_reports_dir = Path(crash_reports_dir)
        self.enable_crash_reports = enable_crash_reports
        self.enable_user_friendly_errors = enable_user_friendly_errors
        self.language = language
        
        # 로거 설정
        self.logger = get_logger("animesorter.exception_handler")
        
        # 크래시 리포트 디렉토리 생성
        if self.enable_crash_reports:
            self.crash_reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 원본 예외 처리기 저장
        self._original_excepthook = sys.excepthook
        self._original_async_exception_handler = None
        
        # 예외 처리 통계
        self._exception_count = 0
        self._last_exception_time = None
        
        # 사용자 정의 예외 처리 콜백
        self._exception_callbacks: Dict[str, Callable] = {}
        
    def install(self) -> None:
        """전역 예외 처리기 설치"""
        # sys.excepthook 설정
        sys.excepthook = self._handle_exception
        
        # 비동기 예외 처리기 설정
        if hasattr(asyncio, 'get_event_loop'):
            try:
                loop = asyncio.get_event_loop()
                self._original_async_exception_handler = loop.get_exception_handler()
                loop.set_exception_handler(self._handle_async_exception)
            except RuntimeError:
                # 이벤트 루프가 없는 경우 무시
                pass
        
        # 스레드 예외 처리기 설정
        threading.excepthook = self._handle_thread_exception
        
        self.logger.info("전역 예외 처리기가 설치되었습니다.")
        
    def uninstall(self) -> None:
        """전역 예외 처리기 제거"""
        # sys.excepthook 복원
        sys.excepthook = self._original_excepthook
        
        # 비동기 예외 처리기 복원
        if self._original_async_exception_handler is not None:
            try:
                loop = asyncio.get_event_loop()
                loop.set_exception_handler(self._original_async_exception_handler)
            except RuntimeError:
                pass
        
        # 스레드 예외 처리기 복원
        threading.excepthook = None
        
        self.logger.info("전역 예외 처리기가 제거되었습니다.")
        
    def _handle_exception(self, exc_type: type, exc_value: Exception, exc_traceback: traceback) -> None:
        """
        동기 예외 처리
        
        Args:
            exc_type: 예외 타입
            exc_value: 예외 값
            exc_traceback: 트레이스백
        """
        # 예외 통계 업데이트
        self._exception_count += 1
        self._last_exception_time = time.time()
        
        # 예외 정보 수집
        exception_info = self._collect_exception_info(exc_type, exc_value, exc_traceback)
        
        # 로깅
        self._log_exception(exception_info)
        
        # 크래시 리포트 생성
        if self.enable_crash_reports:
            self._create_crash_report(exception_info)
        
        # 사용자 친화적 오류 메시지 생성
        if self.enable_user_friendly_errors:
            self._show_user_friendly_error(exc_value, exception_info)
        
        # 사용자 정의 콜백 실행
        self._execute_exception_callbacks(exception_info)
        
        # 원본 예외 처리기 호출 (선택적)
        if self._should_call_original_handler(exc_type, exc_value):
            self._original_excepthook(exc_type, exc_value, exc_traceback)
        
    def _handle_async_exception(self, loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
        """
        비동기 예외 처리
        
        Args:
            loop: 이벤트 루프
            context: 예외 컨텍스트
        """
        exception = context.get('exception')
        if exception is None:
            return
        
        # 예외 통계 업데이트
        self._exception_count += 1
        self._last_exception_time = time.time()
        
        # 예외 정보 수집
        exception_info = self._collect_async_exception_info(loop, context)
        
        # 로깅
        self._log_exception(exception_info)
        
        # 크래시 리포트 생성
        if self.enable_crash_reports:
            self._create_crash_report(exception_info)
        
        # 사용자 친화적 오류 메시지 생성
        if self.enable_user_friendly_errors:
            self._show_user_friendly_error(exception, exception_info)
        
        # 사용자 정의 콜백 실행
        self._execute_exception_callbacks(exception_info)
        
    def _handle_thread_exception(self, args: threading.ExceptHookArgs) -> None:
        """
        스레드 예외 처리
        
        Args:
            args: 예외 훅 인수
        """
        # 예외 통계 업데이트
        self._exception_count += 1
        self._last_exception_time = time.time()
        
        # 예외 정보 수집
        exception_info = self._collect_thread_exception_info(args)
        
        # 로깅
        self._log_exception(exception_info)
        
        # 크래시 리포트 생성
        if self.enable_crash_reports:
            self._create_crash_report(exception_info)
        
        # 사용자 친화적 오류 메시지 생성
        if self.enable_user_friendly_errors:
            self._show_user_friendly_error(args.exc_value, exception_info)
        
        # 사용자 정의 콜백 실행
        self._execute_exception_callbacks(exception_info)
        
    def _collect_exception_info(self, exc_type: type, exc_value: Exception, exc_traceback: traceback) -> Dict[str, Any]:
        """동기 예외 정보 수집"""
        return {
            'timestamp': datetime.now().isoformat(),
            'exception_type': exc_type.__name__,
            'exception_message': str(exc_value),
            'traceback': traceback.format_exception(exc_type, exc_value, exc_traceback),
            'thread_id': threading.get_ident(),
            'thread_name': threading.current_thread().name,
            'exception_category': 'synchronous',
            'system_info': self._get_system_info()
        }
        
    def _collect_async_exception_info(self, loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> Dict[str, Any]:
        """비동기 예외 정보 수집"""
        exception = context.get('exception')
        return {
            'timestamp': datetime.now().isoformat(),
            'exception_type': type(exception).__name__ if exception else 'Unknown',
            'exception_message': str(exception) if exception else 'No exception',
            'traceback': traceback.format_exception(type(exception), exception, exception.__traceback__) if exception else [],
            'async_context': context,
            'thread_id': threading.get_ident(),
            'thread_name': threading.current_thread().name,
            'exception_category': 'asynchronous',
            'system_info': self._get_system_info()
        }
        
    def _collect_thread_exception_info(self, args: threading.ExceptHookArgs) -> Dict[str, Any]:
        """스레드 예외 정보 수집"""
        return {
            'timestamp': datetime.now().isoformat(),
            'exception_type': type(args.exc_value).__name__,
            'exception_message': str(args.exc_value),
            'traceback': traceback.format_exception(type(args.exc_value), args.exc_value, args.exc_traceback),
            'thread_id': getattr(args, 'thread_id', getattr(args, 'thread', None)),
            'thread_name': getattr(args, 'thread_name', getattr(args, 'thread', 'Unknown')),
            'exception_category': 'thread',
            'system_info': self._get_system_info()
        }
        
    def _get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 수집"""
        return {
            'platform': sys.platform,
            'python_version': sys.version,
            'executable': sys.executable,
            'argv': sys.argv,
            'cwd': os.getcwd(),
            'environment': dict(os.environ)
        }
        
    def _log_exception(self, exception_info: Dict[str, Any]) -> None:
        """예외 로깅"""
        log_message = f"예외 발생: {exception_info['exception_type']}: {exception_info['exception_message']}"
        log_message += f" (카테고리: {exception_info['exception_category']})"
        
        self.logger.error(log_message, exc_info=True)
        
        # 상세 정보 로깅
        self.logger.debug(f"예외 상세 정보: {json.dumps(exception_info, indent=2, ensure_ascii=False)}")
        
    def _create_crash_report(self, exception_info: Dict[str, Any]) -> Optional[Path]:
        """크래시 리포트 생성"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crash_report_{timestamp}_{exception_info['exception_type']}.json"
            report_path = self.crash_reports_dir / filename
            
            # 민감한 정보 제거
            safe_exception_info = self._sanitize_exception_info(exception_info)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(safe_exception_info, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"크래시 리포트가 생성되었습니다: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"크래시 리포트 생성 실패: {e}")
            return None
            
    def _sanitize_exception_info(self, exception_info: Dict[str, Any]) -> Dict[str, Any]:
        """예외 정보에서 민감한 정보 제거"""
        sanitized = exception_info.copy()
        
        # 환경 변수에서 민감한 정보 제거
        if 'system_info' in sanitized and 'environment' in sanitized['system_info']:
            env = sanitized['system_info']['environment'].copy()
            sensitive_keys = ['API_KEY', 'PASSWORD', 'SECRET', 'TOKEN', 'CREDENTIAL']
            
            for key in env:
                if any(sensitive in key.upper() for sensitive in sensitive_keys):
                    env[key] = '***REDACTED***'
            
            sanitized['system_info']['environment'] = env
        
        return sanitized
        
    def _show_user_friendly_error(self, exception: Exception, exception_info: Dict[str, Any]) -> None:
        """사용자 친화적 오류 메시지 표시"""
        try:
            # 오류 컨텍스트 생성
            context = ErrorContext(
                operation=f"예외 처리: {exception_info['exception_category']}",
                function_name=exception_info.get('thread_name', 'Unknown'),
                additional_info={
                    'exception_count': self._exception_count,
                    'timestamp': exception_info['timestamp']
                }
            )
            
            # 사용자 친화적 오류 메시지 생성
            user_error = translate_error(exception, context, self.language)
            
            # 콘솔에 오류 메시지 출력
            print(f"\n{'='*50}")
            print(f"오류가 발생했습니다: {user_error.title}")
            print(f"{'='*50}")
            print(f"{user_error.message}")
            print()
            
            if user_error.suggestions:
                print("해결 방법:")
                for i, suggestion in enumerate(user_error.suggestions, 1):
                    print(f"  {i}. {suggestion}")
                print()
            
            if user_error.technical_details:
                print(f"기술적 세부사항: {user_error.technical_details}")
                print()
            
            print(f"{'='*50}\n")
            
        except Exception as e:
            self.logger.error(f"사용자 친화적 오류 메시지 생성 실패: {e}")
            
    def _execute_exception_callbacks(self, exception_info: Dict[str, Any]) -> None:
        """사용자 정의 예외 처리 콜백 실행"""
        for callback_name, callback in self._exception_callbacks.items():
            try:
                callback(exception_info)
            except Exception as e:
                self.logger.error(f"예외 처리 콜백 '{callback_name}' 실행 실패: {e}")
                
    def _should_call_original_handler(self, exc_type: type, exc_value: Exception) -> bool:
        """원본 예외 처리기 호출 여부 결정"""
        # 시스템 종료 예외는 원본 처리기로 전달
        if exc_type in (SystemExit, KeyboardInterrupt):
            return True
        
        # 개발 모드에서는 모든 예외를 원본 처리기로 전달
        if os.getenv('ANIMESORTER_DEBUG') == '1':
            return True
        
        return False
        
    def add_exception_callback(self, name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        예외 처리 콜백 추가
        
        Args:
            name: 콜백 이름
            callback: 콜백 함수
        """
        self._exception_callbacks[name] = callback
        self.logger.debug(f"예외 처리 콜백 '{name}'이 추가되었습니다.")
        
    def remove_exception_callback(self, name: str) -> None:
        """
        예외 처리 콜백 제거
        
        Args:
            name: 콜백 이름
        """
        if name in self._exception_callbacks:
            del self._exception_callbacks[name]
            self.logger.debug(f"예외 처리 콜백 '{name}'이 제거되었습니다.")
            
    def get_exception_stats(self) -> Dict[str, Any]:
        """예외 처리 통계 조회"""
        return {
            'total_exceptions': self._exception_count,
            'last_exception_time': self._last_exception_time,
            'crash_reports_enabled': self.enable_crash_reports,
            'user_friendly_errors_enabled': self.enable_user_friendly_errors,
            'language': self.language.value,
            'callback_count': len(self._exception_callbacks)
        }
        
    def cleanup_old_crash_reports(self, days: int = 30) -> int:
        """
        오래된 크래시 리포트 정리
        
        Args:
            days: 보관할 일수
            
        Returns:
            int: 삭제된 파일 수
        """
        if not self.enable_crash_reports:
            return 0
            
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        deleted_count = 0
        
        for report_file in self.crash_reports_dir.glob("crash_report_*.json"):
            if report_file.stat().st_mtime < cutoff_time:
                try:
                    report_file.unlink()
                    deleted_count += 1
                except OSError as e:
                    self.logger.warning(f"크래시 리포트 삭제 실패 {report_file}: {e}")
        
        if deleted_count > 0:
            self.logger.info(f"{deleted_count}개의 오래된 크래시 리포트가 삭제되었습니다.")
        
        return deleted_count


# 전역 예외 처리기 인스턴스
_exception_handler_instance: Optional[GlobalExceptionHandler] = None


def install_global_exception_handler(crash_reports_dir: str | Path = "crash_reports",
                                   enable_crash_reports: bool = True,
                                   enable_user_friendly_errors: bool = True,
                                   language: Language = Language.KOREAN) -> GlobalExceptionHandler:
    """
    전역 예외 처리기 설치 (편의 함수)
    
    Args:
        crash_reports_dir: 크래시 리포트 저장 디렉토리
        enable_crash_reports: 크래시 리포트 생성 여부
        enable_user_friendly_errors: 사용자 친화적 오류 메시지 사용 여부
        language: 오류 메시지 언어
        
    Returns:
        GlobalExceptionHandler: 설치된 예외 처리기 인스턴스
    """
    global _exception_handler_instance
    
    if _exception_handler_instance is None:
        _exception_handler_instance = GlobalExceptionHandler(
            crash_reports_dir=crash_reports_dir,
            enable_crash_reports=enable_crash_reports,
            enable_user_friendly_errors=enable_user_friendly_errors,
            language=language
        )
        _exception_handler_instance.install()
    
    return _exception_handler_instance


def get_exception_handler() -> Optional[GlobalExceptionHandler]:
    """
    전역 예외 처리기 가져오기 (편의 함수)
    
    Returns:
        GlobalExceptionHandler: 예외 처리기 인스턴스 (설치되지 않은 경우 None)
    """
    return _exception_handler_instance


def uninstall_global_exception_handler() -> None:
    """전역 예외 처리기 제거 (편의 함수)"""
    global _exception_handler_instance
    
    if _exception_handler_instance is not None:
        _exception_handler_instance.uninstall()
        _exception_handler_instance = None


@contextmanager
def exception_handler_context(crash_reports_dir: str | Path = "crash_reports",
                             enable_crash_reports: bool = True,
                             enable_user_friendly_errors: bool = True,
                             language: Language = Language.KOREAN):
    """
    예외 처리기 컨텍스트 매니저
    
    Args:
        crash_reports_dir: 크래시 리포트 저장 디렉토리
        enable_crash_reports: 크래시 리포트 생성 여부
        enable_user_friendly_errors: 사용자 친화적 오류 메시지 사용 여부
        language: 오류 메시지 언어
    """
    handler = install_global_exception_handler(
        crash_reports_dir=crash_reports_dir,
        enable_crash_reports=enable_crash_reports,
        enable_user_friendly_errors=enable_user_friendly_errors,
        language=language
    )
    
    try:
        yield handler
    finally:
        uninstall_global_exception_handler()


# 사용 예시를 위한 데코레이터
def safe_execution(enable_crash_reports: bool = True,
                  enable_user_friendly_errors: bool = True,
                  language: Language = Language.KOREAN):
    """
    안전한 실행을 위한 데코레이터
    
    Args:
        enable_crash_reports: 크래시 리포트 생성 여부
        enable_user_friendly_errors: 사용자 친화적 오류 메시지 사용 여부
        language: 오류 메시지 언어
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 예외 정보 수집
                exc_type, exc_value, exc_traceback = sys.exc_info()
                exception_info = {
                    'timestamp': datetime.now().isoformat(),
                    'exception_type': exc_type.__name__,
                    'exception_message': str(exc_value),
                    'traceback': traceback.format_exception(exc_type, exc_value, exc_traceback),
                    'thread_id': threading.get_ident(),
                    'thread_name': threading.current_thread().name,
                    'exception_category': 'decorator',
                    'system_info': {
                        'platform': sys.platform,
                        'python_version': sys.version,
                        'executable': sys.executable,
                        'argv': sys.argv,
                        'cwd': os.getcwd()
                    }
                }
                
                # 크래시 리포트 생성
                if enable_crash_reports:
                    crash_reports_dir = Path("crash_reports")
                    crash_reports_dir.mkdir(exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"crash_report_{timestamp}_{exception_info['exception_type']}.json"
                    report_path = crash_reports_dir / filename
                    
                    with open(report_path, 'w', encoding='utf-8') as f:
                        json.dump(exception_info, f, indent=2, ensure_ascii=False)
                
                # 사용자 친화적 오류 메시지 표시
                if enable_user_friendly_errors:
                    print(f"\n{'='*50}")
                    print(f"오류가 발생했습니다: {exception_info['exception_type']}")
                    print(f"{'='*50}")
                    print(f"오류 내용: {exception_info['exception_message']}")
                    print(f"{'='*50}\n")
                
                # 예외를 다시 발생시킴
                raise
        return wrapper
    return decorator 