"""
사용자 친화적 오류 메시지 시스템

기술적 오류를 사용자가 이해하기 쉬운 메시지로 변환하고,
오류 복구 방법을 제안하는 시스템입니다.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

from src.exceptions import AnimeSorterError


class Language(Enum):
    """지원 언어"""
    KOREAN = "ko"
    ENGLISH = "en"


@dataclass
class ErrorContext:
    """오류 컨텍스트 정보"""
    operation: str  # 수행 중이던 작업
    file_path: Optional[str] = None  # 관련 파일 경로
    line_number: Optional[int] = None  # 오류 발생 라인
    function_name: Optional[str] = None  # 함수명
    additional_info: Optional[Dict[str, Any]] = None  # 추가 정보


@dataclass
class UserFriendlyError:
    """사용자 친화적 오류 정보"""
    title: str  # 오류 제목
    message: str  # 사용자 메시지
    suggestions: List[str]  # 복구 제안 목록
    technical_details: Optional[str] = None  # 기술적 세부사항 (개발자용)
    severity: str = "error"  # 오류 심각도 (error, warning, info)


class ErrorMessageTranslator:
    """오류 메시지 번역 및 변환 클래스"""
    
    def __init__(self, language: Language = Language.KOREAN):
        """
        번역기 초기화
        
        Args:
            language: 기본 언어
        """
        self.language = language
        self.logger = logging.getLogger("animesorter.error_messages")
        
        # 오류 패턴 매핑
        self._error_patterns = self._initialize_error_patterns()
        
        # 다국어 메시지
        self._messages = self._initialize_messages()
        
    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """오류 패턴 초기화"""
        return {
            "file_not_found": {
                "patterns": [
                    r"\[Errno 2\] No such file or directory: (.+)",
                    r"FileNotFoundError: (.+)",
                    r"파일을 찾을 수 없습니다: (.+)"
                ],
                "error_type": "FileNotFoundError"
            },
            "permission_denied": {
                "patterns": [
                    r"\[Errno 13\] Permission denied: (.+)",
                    r"PermissionError: (.+)",
                    r"권한이 거부되었습니다: (.+)"
                ],
                "error_type": "PermissionError"
            },
            "network_error": {
                "patterns": [
                    r"ConnectionError: (.+)",
                    r"TimeoutError: (.+)",
                    r"requests\.exceptions\.(.+)",
                    r"네트워크 연결 오류: (.+)"
                ],
                "error_type": "NetworkError"
            },
            "api_error": {
                "patterns": [
                    r"API key is invalid",
                    r"Rate limit exceeded",
                    r"API 호출 실패: (.+)",
                    r"인증 실패: (.+)"
                ],
                "error_type": "TMDBApiError"
            },
            "json_error": {
                "patterns": [
                    r"JSONDecodeError: (.+)",
                    r"Expecting value: line (\d+) column (\d+)",
                    r"JSON 파싱 오류: (.+)"
                ],
                "error_type": "ValidationError"
            },
            "database_error": {
                "patterns": [
                    r"sqlite3\.(.+)",
                    r"DatabaseError: (.+)",
                    r"데이터베이스 오류: (.+)"
                ],
                "error_type": "CacheError"
            },
            "validation_error": {
                "patterns": [
                    r"ValidationError: (.+)",
                    r"Invalid format: (.+)",
                    r"유효성 검사 실패: (.+)"
                ],
                "error_type": "ValidationError"
            },
            "config_error": {
                "patterns": [
                    r"ConfigError: (.+)",
                    r"설정 파일 오류: (.+)",
                    r"Configuration error: (.+)"
                ],
                "error_type": "ConfigError"
            }
        }
    
    def _initialize_messages(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """다국어 메시지 초기화"""
        return {
            "file_not_found": {
                "ko": {
                    "title": "파일을 찾을 수 없습니다",
                    "message": "요청하신 파일 '{file_path}'을(를) 찾을 수 없습니다.",
                    "suggestions": [
                        "파일 경로가 올바른지 확인해주세요.",
                        "파일이 삭제되었거나 이동되었을 수 있습니다.",
                        "파일명의 대소문자를 확인해주세요."
                    ]
                },
                "en": {
                    "title": "File Not Found",
                    "message": "The requested file '{file_path}' could not be found.",
                    "suggestions": [
                        "Please check if the file path is correct.",
                        "The file may have been deleted or moved.",
                        "Please check the case sensitivity of the filename."
                    ]
                }
            },
            "permission_denied": {
                "ko": {
                    "title": "권한이 거부되었습니다",
                    "message": "파일 '{file_path}'에 접근할 권한이 없습니다.",
                    "suggestions": [
                        "관리자 권한으로 프로그램을 실행해보세요.",
                        "파일의 읽기/쓰기 권한을 확인해주세요.",
                        "파일이 다른 프로그램에서 사용 중인지 확인해주세요."
                    ]
                },
                "en": {
                    "title": "Permission Denied",
                    "message": "You don't have permission to access the file '{file_path}'.",
                    "suggestions": [
                        "Try running the program with administrator privileges.",
                        "Check the read/write permissions of the file.",
                        "Check if the file is being used by another program."
                    ]
                }
            },
            "network_error": {
                "ko": {
                    "title": "네트워크 연결 오류",
                    "message": "인터넷 연결에 문제가 있습니다: {error_details}",
                    "suggestions": [
                        "인터넷 연결을 확인해주세요.",
                        "방화벽 설정을 확인해주세요.",
                        "잠시 후 다시 시도해주세요."
                    ]
                },
                "en": {
                    "title": "Network Connection Error",
                    "message": "There is a problem with your internet connection: {error_details}",
                    "suggestions": [
                        "Please check your internet connection.",
                        "Check your firewall settings.",
                        "Please try again later."
                    ]
                }
            },
            "api_error": {
                "ko": {
                    "title": "API 호출 오류",
                    "message": "TMDB API 호출 중 오류가 발생했습니다: {error_details}",
                    "suggestions": [
                        "API 키가 올바른지 확인해주세요.",
                        "인터넷 연결을 확인해주세요.",
                        "API 사용량 한도를 확인해주세요."
                    ]
                },
                "en": {
                    "title": "API Call Error",
                    "message": "An error occurred while calling the TMDB API: {error_details}",
                    "suggestions": [
                        "Please check if your API key is correct.",
                        "Check your internet connection.",
                        "Check your API usage limits."
                    ]
                }
            },
            "json_error": {
                "ko": {
                    "title": "데이터 형식 오류",
                    "message": "데이터 형식이 올바르지 않습니다: {error_details}",
                    "suggestions": [
                        "파일이 손상되었을 수 있습니다.",
                        "다른 파일로 다시 시도해보세요.",
                        "프로그램을 다시 시작해보세요."
                    ]
                },
                "en": {
                    "title": "Data Format Error",
                    "message": "The data format is incorrect: {error_details}",
                    "suggestions": [
                        "The file may be corrupted.",
                        "Try with a different file.",
                        "Try restarting the program."
                    ]
                }
            },
            "database_error": {
                "ko": {
                    "title": "데이터베이스 오류",
                    "message": "캐시 데이터베이스에 문제가 있습니다: {error_details}",
                    "suggestions": [
                        "캐시를 초기화해보세요.",
                        "프로그램을 다시 시작해보세요.",
                        "설정 파일을 확인해주세요."
                    ]
                },
                "en": {
                    "title": "Database Error",
                    "message": "There is a problem with the cache database: {error_details}",
                    "suggestions": [
                        "Try clearing the cache.",
                        "Try restarting the program.",
                        "Check the configuration file."
                    ]
                }
            },
            "validation_error": {
                "ko": {
                    "title": "입력 검증 오류",
                    "message": "입력값이 올바르지 않습니다: {error_details}",
                    "suggestions": [
                        "입력값을 다시 확인해주세요.",
                        "필수 항목이 모두 입력되었는지 확인해주세요.",
                        "입력 형식을 확인해주세요."
                    ]
                },
                "en": {
                    "title": "Input Validation Error",
                    "message": "The input value is incorrect: {error_details}",
                    "suggestions": [
                        "Please check your input again.",
                        "Make sure all required fields are filled.",
                        "Check the input format."
                    ]
                }
            },
            "config_error": {
                "ko": {
                    "title": "설정 오류",
                    "message": "설정에 문제가 있습니다: {error_details}",
                    "suggestions": [
                        "설정 파일을 확인해주세요.",
                        "기본 설정으로 초기화해보세요.",
                        "프로그램을 다시 설치해보세요."
                    ]
                },
                "en": {
                    "title": "Configuration Error",
                    "message": "There is a problem with the configuration: {error_details}",
                    "suggestions": [
                        "Please check the configuration file.",
                        "Try resetting to default settings.",
                        "Try reinstalling the program."
                    ]
                }
            },
            "unknown_error": {
                "ko": {
                    "title": "알 수 없는 오류",
                    "message": "예상치 못한 오류가 발생했습니다: {error_details}",
                    "suggestions": [
                        "프로그램을 다시 시작해보세요.",
                        "로그 파일을 확인해주세요.",
                        "개발자에게 문의해주세요."
                    ]
                },
                "en": {
                    "title": "Unknown Error",
                    "message": "An unexpected error occurred: {error_details}",
                    "suggestions": [
                        "Try restarting the program.",
                        "Check the log file.",
                        "Please contact the developer."
                    ]
                }
            }
        }
    
    def translate_error(self, error: Exception, context: Optional[ErrorContext] = None) -> UserFriendlyError:
        """
        오류를 사용자 친화적 메시지로 변환
        
        Args:
            error: 발생한 오류
            context: 오류 컨텍스트 정보
            
        Returns:
            UserFriendlyError: 사용자 친화적 오류 정보
        """
        error_message = str(error)
        error_type = type(error).__name__
        
        # 오류 패턴 매칭
        matched_pattern = self._match_error_pattern(error_message, error_type)
        
        if matched_pattern:
            return self._create_user_friendly_error(matched_pattern, error_message, context)
        else:
            return self._create_unknown_error(error_message, context)
    
    def _match_error_pattern(self, error_message: str, error_type: str) -> Optional[str]:
        """오류 패턴 매칭"""
        for pattern_key, pattern_info in self._error_patterns.items():
            # 오류 타입 매칭
            if pattern_info["error_type"] == error_type:
                return pattern_key
            
            # 패턴 매칭
            for pattern in pattern_info["patterns"]:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return pattern_key
        
        return None
    
    def _create_user_friendly_error(self, pattern_key: str, error_message: str, context: Optional[ErrorContext]) -> UserFriendlyError:
        """사용자 친화적 오류 생성"""
        lang_code = self.language.value
        messages = self._messages.get(pattern_key, self._messages["unknown_error"])
        lang_messages = messages.get(lang_code, messages["en"])
        
        # 메시지 템플릿 변수 치환
        message = lang_messages["message"]
        if "{file_path}" in message and context and context.file_path:
            message = message.replace("{file_path}", context.file_path)
        if "{error_details}" in message:
            # 오류 메시지에서 중요한 부분만 추출
            error_details = self._extract_error_details(error_message)
            message = message.replace("{error_details}", error_details)
        
        return UserFriendlyError(
            title=lang_messages["title"],
            message=message,
            suggestions=lang_messages["suggestions"],
            technical_details=error_message if self.language == Language.ENGLISH else None,
            severity=self._get_error_severity(pattern_key)
        )
    
    def _create_unknown_error(self, error_message: str, context: Optional[ErrorContext]) -> UserFriendlyError:
        """알 수 없는 오류 생성"""
        lang_code = self.language.value
        messages = self._messages["unknown_error"]
        lang_messages = messages.get(lang_code, messages["en"])
        
        error_details = self._extract_error_details(error_message)
        message = lang_messages["message"].replace("{error_details}", error_details)
        
        return UserFriendlyError(
            title=lang_messages["title"],
            message=message,
            suggestions=lang_messages["suggestions"],
            technical_details=error_message if self.language == Language.ENGLISH else None,
            severity="error"
        )
    
    def _extract_error_details(self, error_message: str) -> str:
        """오류 메시지에서 중요한 세부사항 추출"""
        # 파일 경로 추출
        file_match = re.search(r"['\"]([^'\"]*\.(?:mp4|mkv|avi|mov|wmv))['\"]", error_message)
        if file_match:
            return f"파일: {file_match.group(1)}"
        
        # API 키 관련 오류
        if "API key" in error_message:
            return "API 키 인증 실패"
        
        # 네트워크 오류
        if "Connection" in error_message or "Timeout" in error_message:
            return "네트워크 연결 실패"
        
        # 기본적으로 첫 100자만 반환
        return error_message[:100] + ("..." if len(error_message) > 100 else "")
    
    def _get_error_severity(self, pattern_key: str) -> str:
        """오류 심각도 결정"""
        severity_map = {
            "file_not_found": "warning",
            "permission_denied": "error",
            "network_error": "warning",
            "api_error": "warning",
            "json_error": "error",
            "database_error": "error",
            "validation_error": "warning",
            "config_error": "error"
        }
        return severity_map.get(pattern_key, "error")
    
    def set_language(self, language: Language) -> None:
        """언어 설정 변경"""
        self.language = language
    
    def get_supported_languages(self) -> List[Language]:
        """지원 언어 목록 반환"""
        return list(Language)
    
    def format_error_for_logging(self, error: Exception, context: Optional[ErrorContext] = None) -> str:
        """로깅용 오류 메시지 포맷팅"""
        parts = []
        
        if context:
            parts.append(f"Operation: {context.operation}")
            if context.file_path:
                parts.append(f"File: {context.file_path}")
            if context.function_name:
                parts.append(f"Function: {context.function_name}")
            if context.line_number:
                parts.append(f"Line: {context.line_number}")
        
        parts.append(f"Error: {type(error).__name__}: {str(error)}")
        
        return " | ".join(parts)


# 전역 번역기 인스턴스
_translator_instance: Optional[ErrorMessageTranslator] = None


def get_error_translator(language: Language = Language.KOREAN) -> ErrorMessageTranslator:
    """
    오류 번역기 가져오기
    
    Args:
        language: 언어 설정
        
    Returns:
        ErrorMessageTranslator: 번역기 인스턴스
    """
    global _translator_instance
    
    if _translator_instance is None:
        _translator_instance = ErrorMessageTranslator(language)
    elif _translator_instance.language != language:
        _translator_instance.set_language(language)
    
    return _translator_instance


def translate_error(error: Exception, context: Optional[ErrorContext] = None, language: Language = Language.KOREAN) -> UserFriendlyError:
    """
    오류를 사용자 친화적 메시지로 변환 (편의 함수)
    
    Args:
        error: 발생한 오류
        context: 오류 컨텍스트 정보
        language: 언어 설정
        
    Returns:
        UserFriendlyError: 사용자 친화적 오류 정보
    """
    translator = get_error_translator(language)
    return translator.translate_error(error, context)


def format_error_for_logging(error: Exception, context: Optional[ErrorContext] = None) -> str:
    """
    로깅용 오류 메시지 포맷팅 (편의 함수)
    
    Args:
        error: 발생한 오류
        context: 오류 컨텍스트 정보
        
    Returns:
        str: 포맷팅된 오류 메시지
    """
    translator = get_error_translator()
    return translator.format_error_for_logging(error, context)


# 사용 예시를 위한 데코레이터
def handle_errors(language: Language = Language.KOREAN, log_error: bool = True):
    """
    오류 처리 데코레이터
    
    Args:
        language: 오류 메시지 언어
        log_error: 오류 로깅 여부
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 오류 컨텍스트 생성
                context = ErrorContext(
                    operation=f"Function call: {func.__name__}",
                    function_name=func.__name__
                )
                
                # 사용자 친화적 오류 생성
                user_error = translate_error(e, context, language)
                
                # 로깅
                if log_error:
                    logger = logging.getLogger("animesorter.error_handler")
                    logger.error(format_error_for_logging(e, context))
                
                # 사용자에게 오류 표시 (UI에서 처리)
                raise AnimeSorterError(user_error.message, user_error.technical_details)
        
        return wrapper
    return decorator 