"""
ErrorBus 시스템

애플리케이션 전체의 에러 처리를 위한 전용 이벤트 버스입니다.
예외를 이벤트로 변환하고, 사용자 메시지와 개발자 로그를 분리하며,
에러 복구 전략을 제공합니다.
"""

import logging
import sys
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from PyQt5.QtCore import QObject, pyqtSignal


class ErrorSeverity(Enum):
    """에러 심각도"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """에러 카테고리"""

    VALIDATION = "validation"
    FILE_OPERATION = "file_operation"
    NETWORK = "network"
    PERMISSION = "permission"
    CONFIGURATION = "configuration"
    UI = "ui"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorRecoveryStrategy(Enum):
    """에러 복구 전략"""

    RETRY = "retry"
    FALLBACK = "fallback"
    USER_INTERVENTION = "user_intervention"
    IGNORE = "ignore"
    TERMINATE = "terminate"


@dataclass
class ErrorContext:
    """에러 컨텍스트 정보"""

    timestamp: datetime = field(default_factory=datetime.now)
    user_id: str | None = None
    session_id: str | None = None
    operation: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    function_name: str | None = None
    module_name: str | None = None
    additional_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorEvent:
    """에러 이벤트"""

    id: str = field(default_factory=lambda: str(uuid4()))
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.UNKNOWN
    title: str = ""
    user_message: str = ""
    developer_message: str = ""
    exception: Exception | None = None
    traceback: str | None = None
    context: ErrorContext = field(default_factory=ErrorContext)
    recovery_strategy: ErrorRecoveryStrategy = ErrorRecoveryStrategy.IGNORE
    retry_count: int = 0
    max_retries: int = 3
    is_recovered: bool = False
    recovery_notes: str = ""


class ErrorHandler(ABC):
    """에러 핸들러 인터페이스"""

    @abstractmethod
    def handle_error(self, error_event: ErrorEvent) -> bool:
        """에러 처리"""


class LoggingErrorHandler(ErrorHandler):
    """로깅 에러 핸들러"""

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

    def handle_error(self, error_event: ErrorEvent) -> bool:
        """에러를 로그로 기록"""
        try:
            # 로그 레벨 결정
            log_level = self._get_log_level(error_event.severity)

            # 로그 메시지 구성
            log_message = self._format_log_message(error_event)

            # 로그 기록
            self.logger.log(log_level, log_message)

            return True

        except Exception as e:
            # 핸들러 자체에서 에러가 발생한 경우
            print(f"❌ 로깅 에러 핸들러 실패: {e}")
            return False

    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """심각도에 따른 로그 레벨 반환"""
        level_mapping = {
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }
        return level_mapping.get(severity, logging.ERROR)

    def _format_log_message(self, error_event: ErrorEvent) -> str:
        """로그 메시지 포맷팅"""
        parts = [
            f"[{error_event.category.value.upper()}] {error_event.title}",
            f"사용자 메시지: {error_event.user_message}",
            f"개발자 메시지: {error_event.developer_message}",
        ]

        if error_event.exception:
            parts.append(f"예외: {type(error_event.exception).__name__}: {error_event.exception}")

        if error_event.context.operation:
            parts.append(f"작업: {error_event.context.operation}")

        if error_event.context.file_path:
            parts.append(f"파일: {error_event.context.file_path}")

        if error_event.context.line_number:
            parts.append(f"라인: {error_event.context.line_number}")

        if error_event.recovery_strategy != ErrorRecoveryStrategy.IGNORE:
            parts.append(f"복구 전략: {error_event.recovery_strategy.value}")

        return " | ".join(parts)


class UserNotificationErrorHandler(ErrorHandler):
    """사용자 알림 에러 핸들러"""

    def __init__(self, notification_callback: Callable[[ErrorEvent], None] | None = None):
        self.notification_callback = notification_callback

    def handle_error(self, error_event: ErrorEvent) -> bool:
        """사용자에게 에러 알림"""
        try:
            if self.notification_callback:
                self.notification_callback(error_event)
            else:
                # 기본 콘솔 출력
                print(f"🚨 {error_event.title}")
                print(f"   {error_event.user_message}")

                if error_event.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
                    print(f"   복구 전략: {error_event.recovery_strategy.value}")

            return True

        except Exception as e:
            print(f"❌ 사용자 알림 에러 핸들러 실패: {e}")
            return False


class ErrorRecoveryHandler(ErrorHandler):
    """에러 복구 핸들러"""

    def __init__(self) -> None:
        self.recovery_strategies: dict[ErrorRecoveryStrategy, Callable[[ErrorEvent], bool]] = {}
        self._register_default_strategies()

    def handle_error(self, error_event: ErrorEvent) -> bool:
        """에러 복구 시도"""
        try:
            if error_event.is_recovered:
                return True

            strategy = error_event.recovery_strategy
            if strategy in self.recovery_strategies:
                recovery_func = self.recovery_strategies[strategy]
                success = recovery_func(error_event)

                if success:
                    error_event.is_recovered = True
                    error_event.recovery_notes = f"자동 복구 성공: {strategy.value}"
                    print(f"✅ 에러 자동 복구 성공: {error_event.title}")
                else:
                    error_event.recovery_notes = f"자동 복구 실패: {strategy.value}"
                    print(f"❌ 에러 자동 복구 실패: {error_event.title}")

                return success

            return False

        except Exception as e:
            print(f"❌ 에러 복구 핸들러 실패: {e}")
            return False

    def _register_default_strategies(self) -> None:
        """기본 복구 전략 등록"""
        self.recovery_strategies[ErrorRecoveryStrategy.RETRY] = self._retry_strategy
        self.recovery_strategies[ErrorRecoveryStrategy.FALLBACK] = self._fallback_strategy
        self.recovery_strategies[ErrorRecoveryStrategy.IGNORE] = self._ignore_strategy

    def _retry_strategy(self, error_event: ErrorEvent) -> bool:
        """재시도 전략"""
        if error_event.retry_count < error_event.max_retries:
            error_event.retry_count += 1
            print(f"🔄 재시도 {error_event.retry_count}/{error_event.max_retries}")
            return True
        return False

    def _fallback_strategy(self, error_event: ErrorEvent) -> bool:
        """대체 방법 전략"""
        print("🔄 대체 방법 시도")
        return True

    def _ignore_strategy(self, error_event: ErrorEvent) -> bool:
        """무시 전략"""
        print("⏭️ 에러 무시됨")
        return True

    def register_strategy(
        self, strategy: ErrorRecoveryStrategy, handler: Callable[[ErrorEvent], bool]
    ) -> None:
        """사용자 정의 복구 전략 등록"""
        self.recovery_strategies[strategy] = handler


class ErrorBus(QObject):
    """에러 처리 전용 이벤트 버스"""

    # 시그널 정의
    error_occurred = pyqtSignal(object)  # ErrorEvent
    error_recovered = pyqtSignal(object)  # ErrorEvent
    error_unrecoverable = pyqtSignal(object)  # ErrorEvent

    def __init__(self) -> None:
        super().__init__()
        self.handlers: list[ErrorHandler] = []
        self.error_history: list[ErrorEvent] = []
        self.max_history_size = 1000

        # 기본 핸들러 등록
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """기본 에러 핸들러 등록"""
        self.add_handler(LoggingErrorHandler())
        self.add_handler(UserNotificationErrorHandler())
        self.add_handler(ErrorRecoveryHandler())

    def add_handler(self, handler: ErrorHandler) -> None:
        """에러 핸들러 추가"""
        if handler not in self.handlers:
            self.handlers.append(handler)
            print(f"✅ 에러 핸들러 추가: {handler.__class__.__name__}")

    def remove_handler(self, handler: ErrorHandler) -> None:
        """에러 핸들러 제거"""
        if handler in self.handlers:
            self.handlers.remove(handler)
            print(f"✅ 에러 핸들러 제거: {handler.__class__.__name__}")

    def handle_exception(
        self,
        exception: Exception,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        title: str = "",
        user_message: str = "",
        developer_message: str = "",
        recovery_strategy: ErrorRecoveryStrategy = ErrorRecoveryStrategy.IGNORE,
        context: ErrorContext | None = None,
        **kwargs: Any,
    ) -> ErrorEvent:
        """예외를 ErrorEvent로 변환하여 처리"""

        # ErrorEvent 생성
        error_event = ErrorEvent(
            severity=severity,
            category=category,
            title=title or f"{type(exception).__name__} 발생",
            user_message=user_message or str(exception),
            developer_message=developer_message
            or f"예외 타입: {type(exception).__name__}, 메시지: {str(exception)}",
            exception=exception,
            traceback=traceback.format_exc(),
            context=context or ErrorContext(),
            recovery_strategy=recovery_strategy,
            **kwargs,
        )

        # 컨텍스트 정보 자동 채우기
        self._fill_context_info(error_event)

        # 에러 처리
        self._process_error(error_event)

        return error_event

    def _fill_context_info(self, error_event: ErrorEvent) -> None:
        """컨텍스트 정보 자동 채우기"""
        if not error_event.context.function_name:
            # 현재 스택 프레임에서 함수명 추출
            try:
                frame = sys._getframe(2)  # handle_exception 호출자
                error_event.context.function_name = frame.f_code.co_name
                error_event.context.module_name = frame.f_globals.get("__name__", "unknown")
                error_event.context.line_number = frame.f_lineno
            except Exception:
                pass

    def _process_error(self, error_event: ErrorEvent) -> None:
        """에러 처리 파이프라인"""
        try:
            # 에러 히스토리에 추가
            self._add_to_history(error_event)

            # 시그널 발생
            self.error_occurred.emit(error_event)

            # 모든 핸들러에 에러 전달
            for handler in self.handlers:
                try:
                    handler.handle_error(error_event)
                except Exception as e:
                    print(f"⚠️ 핸들러 {handler.__class__.__name__} 실행 실패: {e}")

            # 복구 결과에 따른 시그널 발생
            if error_event.is_recovered:
                self.error_recovered.emit(error_event)
            elif error_event.recovery_strategy == ErrorRecoveryStrategy.TERMINATE:
                self.error_unrecoverable.emit(error_event)

        except Exception as e:
            print(f"❌ 에러 처리 파이프라인 실패: {e}")

    def _add_to_history(self, error_event: ErrorEvent) -> None:
        """에러 히스토리에 추가"""
        self.error_history.append(error_event)

        # 히스토리 크기 제한
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)

    def get_error_history(
        self,
        severity: ErrorSeverity | None = None,
        category: ErrorCategory | None = None,
        limit: int | None = None,
    ) -> list[ErrorEvent]:
        """에러 히스토리 조회"""
        filtered_history = self.error_history

        if severity:
            filtered_history = [e for e in filtered_history if e.severity == severity]

        if category:
            filtered_history = [e for e in filtered_history if e.category == category]

        if limit:
            filtered_history = filtered_history[-limit:]

        return filtered_history

    def get_error_statistics(self) -> dict[str, Any]:
        """에러 통계 반환"""
        if not self.error_history:
            return {"total_errors": 0}

        total_errors = len(self.error_history)
        severity_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        recovery_counts = {"recovered": 0, "unrecovered": 0}

        for error in self.error_history:
            # 심각도별 카운트
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # 카테고리별 카운트
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

            # 복구 상태별 카운트
            if error.is_recovered:
                recovery_counts["recovered"] += 1
            else:
                recovery_counts["unrecovered"] += 1

        return {
            "total_errors": total_errors,
            "severity_distribution": severity_counts,
            "category_distribution": category_counts,
            "recovery_distribution": recovery_counts,
            "recovery_rate": (
                (recovery_counts["recovered"] / total_errors) * 100 if total_errors > 0 else 0
            ),
        }

    def clear_history(self):
        """에러 히스토리 초기화"""
        self.error_history.clear()
        print("✅ 에러 히스토리 초기화 완료")

    def export_history(self, file_path: str | Path, format: str = "json") -> bool:
        """에러 히스토리 내보내기"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == "json":
                import json

                # datetime 객체와 enum을 문자열로 변환
                export_data = []
                for error in self.error_history:
                    error_dict = error.__dict__.copy()
                    error_dict["context"] = error.context.__dict__.copy()
                    error_dict["context"]["timestamp"] = error.context.timestamp.isoformat()
                    error_dict["exception"] = str(error.exception) if error.exception else None

                    # enum 값들을 문자열로 변환
                    error_dict["severity"] = error.severity.value
                    error_dict["category"] = error.category.value
                    error_dict["recovery_strategy"] = error.recovery_strategy.value

                    export_data.append(error_dict)

                with file_path.open("w", encoding="utf-8") as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

            elif format.lower() == "csv":
                import csv

                with file_path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    # 헤더 작성
                    writer.writerow(
                        [
                            "ID",
                            "Timestamp",
                            "Severity",
                            "Category",
                            "Title",
                            "User Message",
                            "Developer Message",
                            "Recovery Strategy",
                            "Is Recovered",
                            "Retry Count",
                        ]
                    )

                    # 데이터 작성
                    for error in self.error_history:
                        writer.writerow(
                            [
                                error.id,
                                error.context.timestamp.isoformat(),
                                error.severity.value,
                                error.category.value,
                                error.title,
                                error.user_message,
                                error.developer_message,
                                error.recovery_strategy.value,
                                error.is_recovered,
                                error.retry_count,
                            ]
                        )

            print(f"✅ 에러 히스토리 내보내기 완료: {file_path}")
            return True

        except Exception as e:
            print(f"❌ 에러 히스토리 내보내기 실패: {e}")
            return False


# 전역 ErrorBus 인스턴스
error_bus = ErrorBus()


# 편의 함수들
def handle_exception(exception: Exception, **kwargs: Any) -> ErrorEvent:
    """전역 예외 처리 함수"""
    return error_bus.handle_exception(exception, **kwargs)


def log_error(title: str, message: str, **kwargs: Any) -> ErrorEvent:
    """에러 로깅 편의 함수"""
    return error_bus.handle_exception(
        Exception(message), title=title, user_message=message, developer_message=message, **kwargs
    )


def log_warning(title: str, message: str, **kwargs: Any) -> ErrorEvent:
    """경고 로깅 편의 함수"""
    return error_bus.handle_exception(
        Exception(message),
        severity=ErrorSeverity.WARNING,
        title=title,
        user_message=message,
        developer_message=message,
        **kwargs,
    )
