"""
AnimeSorter 예외 계층 구조

이 모듈은 애플리케이션 전반에서 사용되는 예외 클래스들을 정의합니다.
체계적인 오류 처리를 위해 계층 구조로 설계되었습니다.
"""

from typing import Optional


class AnimeSorterError(Exception):
    """
    AnimeSorter 애플리케이션의 기본 예외 클래스
    
    모든 애플리케이션 예외는 이 클래스를 상속받아야 합니다.
    """
    
    def __init__(self, message: str, details: Optional[str] = None):
        """
        예외 초기화
        
        Args:
            message: 사용자에게 표시할 오류 메시지
            details: 개발자를 위한 상세 오류 정보 (옵션)
        """
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """문자열 표현"""
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ConfigError(AnimeSorterError):
    """
    설정 관련 오류
    
    설정 파일 로드, 파싱, 검증 실패 시 발생합니다.
    """
    
    def __init__(self, message: str, config_file: Optional[str] = None, details: Optional[str] = None):
        """
        ConfigError 초기화
        
        Args:
            message: 오류 메시지
            config_file: 문제가 발생한 설정 파일 경로 (옵션)
            details: 상세 오류 정보 (옵션)
        """
        self.config_file = config_file
        if config_file:
            message = f"{message} (Config file: {config_file})"
        super().__init__(message, details)


class FileCleanerError(AnimeSorterError):
    """
    파일명 정제 오류
    
    파일명 파싱, 정규식 매칭, 메타데이터 추출 실패 시 발생합니다.
    """
    
    def __init__(self, message: str, filename: Optional[str] = None, details: Optional[str] = None):
        """
        FileCleanerError 초기화
        
        Args:
            message: 오류 메시지
            filename: 문제가 발생한 파일명 (옵션)
            details: 상세 오류 정보 (옵션)
        """
        self.filename = filename
        if filename:
            message = f"{message} (Filename: {filename})"
        super().__init__(message, details)


class TMDBApiError(AnimeSorterError):
    """
    TMDB API 오류
    
    API 요청 실패, 응답 파싱 오류, 인증 실패 등이 발생할 때 사용됩니다.
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 endpoint: Optional[str] = None, details: Optional[str] = None):
        """
        TMDBApiError 초기화
        
        Args:
            message: 오류 메시지
            status_code: HTTP 상태 코드 (옵션)
            endpoint: 요청한 API 엔드포인트 (옵션)
            details: 상세 오류 정보 (옵션)
        """
        self.status_code = status_code
        self.endpoint = endpoint
        
        # 메시지 구성
        error_parts = [message]
        if status_code:
            error_parts.append(f"Status: {status_code}")
        if endpoint:
            error_parts.append(f"Endpoint: {endpoint}")
        
        formatted_message = " | ".join(error_parts)
        super().__init__(formatted_message, details)


class FileManagerError(AnimeSorterError):
    """
    파일 관리 오류
    
    파일 이동, 복사, 삭제, 권한 오류 등이 발생할 때 사용됩니다.
    """
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 operation: Optional[str] = None, details: Optional[str] = None):
        """
        FileManagerError 초기화
        
        Args:
            message: 오류 메시지
            file_path: 문제가 발생한 파일 경로 (옵션)
            operation: 수행하려던 작업 (옵션)
            details: 상세 오류 정보 (옵션)
        """
        self.file_path = file_path
        self.operation = operation
        
        # 메시지 구성
        error_parts = [message]
        if operation:
            error_parts.append(f"Operation: {operation}")
        if file_path:
            error_parts.append(f"File: {file_path}")
        
        formatted_message = " | ".join(error_parts)
        super().__init__(formatted_message, details)


class NetworkError(AnimeSorterError):
    """
    네트워크 관련 오류
    
    연결 실패, 타임아웃, DNS 오류 등이 발생할 때 사용됩니다.
    """
    
    def __init__(self, message: str, url: Optional[str] = None, 
                 timeout: Optional[float] = None, details: Optional[str] = None):
        """
        NetworkError 초기화
        
        Args:
            message: 오류 메시지
            url: 요청한 URL (옵션)
            timeout: 타임아웃 설정 (옵션)
            details: 상세 오류 정보 (옵션)
        """
        self.url = url
        self.timeout = timeout
        
        # 메시지 구성
        error_parts = [message]
        if url:
            error_parts.append(f"URL: {url}")
        if timeout:
            error_parts.append(f"Timeout: {timeout}s")
        
        formatted_message = " | ".join(error_parts)
        super().__init__(formatted_message, details)


class CacheError(AnimeSorterError):
    """
    캐시 데이터베이스 오류
    
    캐시 저장, 조회, 삭제 실패 시 발생합니다.
    """
    
    def __init__(self, message: str, cache_key: Optional[str] = None, 
                 operation: Optional[str] = None, details: Optional[str] = None):
        """
        CacheError 초기화
        
        Args:
            message: 오류 메시지
            cache_key: 문제가 발생한 캐시 키 (옵션)
            operation: 수행하려던 캐시 작업 (옵션)
            details: 상세 오류 정보 (옵션)
        """
        self.cache_key = cache_key
        self.operation = operation
        
        # 메시지 구성
        error_parts = [message]
        if operation:
            error_parts.append(f"Operation: {operation}")
        if cache_key:
            error_parts.append(f"Key: {cache_key}")
        
        formatted_message = " | ".join(error_parts)
        super().__init__(formatted_message, details)


class ValidationError(AnimeSorterError):
    """
    데이터 검증 오류
    
    입력 데이터 검증 실패, 형식 오류 등이 발생할 때 사용됩니다.
    """
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[str] = None, details: Optional[str] = None):
        """
        ValidationError 초기화
        
        Args:
            message: 오류 메시지
            field: 검증 실패한 필드명 (옵션)
            value: 검증 실패한 값 (옵션)
            details: 상세 오류 정보 (옵션)
        """
        self.field = field
        self.value = value
        
        # 메시지 구성
        error_parts = [message]
        if field:
            error_parts.append(f"Field: {field}")
        if value:
            error_parts.append(f"Value: {value}")
        
        formatted_message = " | ".join(error_parts)
        super().__init__(formatted_message, details)


# 예외 계층 구조를 명확히 하기 위한 타입 힌트
__all__ = [
    'AnimeSorterError',
    'ConfigError', 
    'FileCleanerError',
    'TMDBApiError',
    'FileManagerError',
    'NetworkError',
    'CacheError',
    'ValidationError'
] 