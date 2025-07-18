"""
입력 검증 시스템

사용자 입력에 대한 검증을 수행하여 보안을 강화하는 모듈입니다.
"""

import os
import re
import pathlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse
import hashlib

from ..exceptions import ValidationError
from ..utils.logger import get_logger


class InputValidator:
    """입력 검증기"""
    
    def __init__(self):
        """InputValidator 초기화"""
        self.logger = get_logger(__name__)
        
    def validate_file_path(self, file_path: Union[str, Path], must_exist: bool = False) -> Path:
        """
        파일 경로 검증
        
        Args:
            file_path: 검증할 파일 경로
            must_exist: 파일이 반드시 존재해야 하는지 여부
            
        Returns:
            Path: 검증된 파일 경로
            
        Raises:
            ValidationError: 검증 실패 시
        """
        try:
            # 문자열을 Path 객체로 변환
            if isinstance(file_path, str):
                path = Path(file_path)
            else:
                path = file_path
                
            # 절대 경로로 변환
            path = path.resolve()
            
            # 경로 구성 요소 검증
            self._validate_path_components(path)
            
            # 존재 여부 검증
            if must_exist and not path.exists():
                raise ValidationError(f"파일이 존재하지 않습니다: {path}")
                
            # 안전한 경로인지 검증
            self._validate_path_safety(path)
            
            return path
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"파일 경로 검증 실패: {str(e)}") from e
            
    def validate_directory_path(self, dir_path: Union[str, Path], must_exist: bool = False) -> Path:
        """
        디렉토리 경로 검증
        
        Args:
            dir_path: 검증할 디렉토리 경로
            must_exist: 디렉토리가 반드시 존재해야 하는지 여부
            
        Returns:
            Path: 검증된 디렉토리 경로
            
        Raises:
            ValidationError: 검증 실패 시
        """
        try:
            path = self.validate_file_path(dir_path, must_exist)
            
            # 디렉토리인지 확인
            if must_exist and not path.is_dir():
                raise ValidationError(f"디렉토리가 아닙니다: {path}")
                
            return path
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"디렉토리 경로 검증 실패: {str(e)}") from e
            
    def validate_api_key(self, api_key: str, key_type: str = "tmdb") -> str:
        """
        API 키 검증
        
        Args:
            api_key: 검증할 API 키
            key_type: API 키 타입 (tmdb, etc.)
            
        Returns:
            str: 검증된 API 키
            
        Raises:
            ValidationError: 검증 실패 시
        """
        if not api_key or not isinstance(api_key, str):
            raise ValidationError("API 키는 비어있지 않은 문자열이어야 합니다.")
            
        # 공백 제거
        api_key = api_key.strip()
        
        if not api_key:
            raise ValidationError("API 키는 공백만으로 구성될 수 없습니다.")
            
        # 길이 검증
        if len(api_key) < 10:
            raise ValidationError("API 키가 너무 짧습니다.")
            
        if len(api_key) > 1000:
            raise ValidationError("API 키가 너무 깁니다.")
            
        # TMDB API 키 형식 검증
        if key_type.lower() == "tmdb":
            self._validate_tmdb_api_key(api_key)
            
        # 특수 문자 검증
        if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
            raise ValidationError("API 키에 허용되지 않는 문자가 포함되어 있습니다.")
            
        return api_key
        
    def validate_url(self, url: str, allowed_schemes: Optional[List[str]] = None) -> str:
        """
        URL 검증
        
        Args:
            url: 검증할 URL
            allowed_schemes: 허용된 스키마 목록
            
        Returns:
            str: 검증된 URL
            
        Raises:
            ValidationError: 검증 실패 시
        """
        if not url or not isinstance(url, str):
            raise ValidationError("URL은 비어있지 않은 문자열이어야 합니다.")
            
        # 공백 제거
        url = url.strip()
        
        if not url:
            raise ValidationError("URL은 공백만으로 구성될 수 없습니다.")
            
        try:
            parsed = urlparse(url)
            
            # 스키마 검증
            if not parsed.scheme:
                raise ValidationError("URL에 스키마가 없습니다.")
                
            # 기본 허용 스키마 설정
            if allowed_schemes is None:
                allowed_schemes = ["http", "https"]
                
            if parsed.scheme not in allowed_schemes:
                raise ValidationError(f"허용되지 않는 스키마입니다: {parsed.scheme}")
                
            # 네트워크 위치 검증
            if not parsed.netloc:
                raise ValidationError("URL에 네트워크 위치가 없습니다.")
                
            # 포트 검증 (있다면)
            if parsed.port and (parsed.port < 1 or parsed.port > 65535):
                raise ValidationError("잘못된 포트 번호입니다.")
                
            return url
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"URL 검증 실패: {str(e)}") from e
            
    def validate_filename(self, filename: str, allow_extensions: Optional[List[str]] = None) -> str:
        """
        파일명 검증
        
        Args:
            filename: 검증할 파일명
            allow_extensions: 허용된 확장자 목록
            
        Returns:
            str: 검증된 파일명
            
        Raises:
            ValidationError: 검증 실패 시
        """
        if not filename or not isinstance(filename, str):
            raise ValidationError("파일명은 비어있지 않은 문자열이어야 합니다.")
            
        # 공백 제거
        filename = filename.strip()
        
        if not filename:
            raise ValidationError("파일명은 공백만으로 구성될 수 없습니다.")
            
        # 길이 검증
        if len(filename) > 255:
            raise ValidationError("파일명이 너무 깁니다.")
            
        # 위험한 문자 검증
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in dangerous_chars:
            if char in filename:
                raise ValidationError(f"파일명에 허용되지 않는 문자가 포함되어 있습니다: {char}")
                
        # 명령어 인젝션 방지
        command_chars = [';', '&', '|', '`', '$', '(', ')']
        for char in command_chars:
            if char in filename:
                raise ValidationError(f"파일명에 명령어 실행 문자가 포함되어 있습니다: {char}")
                
        # 확장자 검증
        if allow_extensions:
            file_ext = Path(filename).suffix.lower()
            if file_ext and file_ext not in allow_extensions:
                raise ValidationError(f"허용되지 않는 파일 확장자입니다: {file_ext}")
                
        return filename
        
    def validate_config_value(self, key: str, value: Any, expected_type: type) -> Any:
        """
        설정값 검증
        
        Args:
            key: 설정 키
            value: 검증할 값
            expected_type: 예상 타입
            
        Returns:
            Any: 검증된 값
            
        Raises:
            ValidationError: 검증 실패 시
        """
        if not isinstance(value, expected_type):
            raise ValidationError(f"설정 '{key}'의 타입이 잘못되었습니다. 예상: {expected_type.__name__}, 실제: {type(value).__name__}")
            
        # 타입별 추가 검증
        if expected_type == str:
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"설정 '{key}'는 비어있지 않은 문자열이어야 합니다.")
                
        elif expected_type == int:
            if not isinstance(value, int) or value < 0:
                raise ValidationError(f"설정 '{key}'는 0 이상의 정수여야 합니다.")
                
        elif expected_type == bool:
            if not isinstance(value, bool):
                raise ValidationError(f"설정 '{key}'는 불린 값이어야 합니다.")
                
        elif expected_type == list:
            if not isinstance(value, list):
                raise ValidationError(f"설정 '{key}'는 리스트여야 합니다.")
                
        return value
        
    def validate_sql_query(self, query: str) -> str:
        """
        SQL 쿼리 검증 (기본적인 SQL 인젝션 방지)
        
        Args:
            query: 검증할 SQL 쿼리
            
        Returns:
            str: 검증된 SQL 쿼리
            
        Raises:
            ValidationError: 검증 실패 시
        """
        if not query or not isinstance(query, str):
            raise ValidationError("SQL 쿼리는 비어있지 않은 문자열이어야 합니다.")
            
        # 공백 제거
        query = query.strip()
        
        if not query:
            raise ValidationError("SQL 쿼리는 공백만으로 구성될 수 없습니다.")
            
        # 위험한 키워드 검증
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 'TRUNCATE',
            'EXEC', 'EXECUTE', 'UNION', 'SCRIPT', '--', '/*', '*/', 'OR', 'AND'
        ]
        
        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise ValidationError(f"SQL 쿼리에 위험한 키워드가 포함되어 있습니다: {keyword}")
                
        # 세미콜론 검증
        if ';' in query:
            raise ValidationError("SQL 쿼리에 세미콜론이 포함되어 있습니다.")
            
        # SQL 인젝션 패턴 검증
        injection_patterns = [
            "' OR '1'='1",
            "' OR 1=1",
            "'; DROP TABLE",
            "'; INSERT INTO",
            "'; UPDATE",
            "admin'--",
            "1' UNION SELECT"
        ]
        
        for pattern in injection_patterns:
            if pattern.upper() in query_upper:
                raise ValidationError(f"SQL 인젝션 패턴이 감지되었습니다: {pattern}")
                
        return query
        
    def validate_json_data(self, data: Dict[str, Any], required_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        JSON 데이터 검증
        
        Args:
            data: 검증할 JSON 데이터
            required_keys: 필수 키 목록
            
        Returns:
            Dict[str, Any]: 검증된 JSON 데이터
            
        Raises:
            ValidationError: 검증 실패 시
        """
        if not isinstance(data, dict):
            raise ValidationError("JSON 데이터는 딕셔너리여야 합니다.")
            
        # 필수 키 검증
        if required_keys:
            for key in required_keys:
                if key not in data:
                    raise ValidationError(f"필수 키가 누락되었습니다: {key}")
                    
        # 키 이름 검증
        for key in data.keys():
            if not isinstance(key, str):
                raise ValidationError("JSON 키는 문자열이어야 합니다.")
                
            if not key.strip():
                raise ValidationError("JSON 키는 공백만으로 구성될 수 없습니다.")
                
        return data
        
    def _validate_path_components(self, path: Path) -> None:
        """경로 구성 요소 검증"""
        # 경로 구성 요소 검증
        for part in path.parts:
            if not part or part == '.' or part == '..':
                continue
                
            # Windows 드라이브 문자는 허용 (C:, D: 등)
            if len(part) == 2 and part.endswith(':') and part[0].isalpha():
                continue
                
            # 길이 검증
            if len(part) > 255:
                raise ValidationError(f"경로 구성 요소가 너무 깁니다: {part}")
                
            # 위험한 문자 검증
            dangerous_chars = ['<', '>', '"', '|', '?', '*']
            for char in dangerous_chars:
                if char in part:
                    raise ValidationError(f"경로에 허용되지 않는 문자가 포함되어 있습니다: {char}")
                    
    def _validate_path_safety(self, path: Path) -> None:
        """경로 안전성 검증"""
        # 현재 작업 디렉토리 기준으로 상대 경로 검증
        try:
            current_dir = Path.cwd().resolve()
            path.resolve().relative_to(current_dir)
        except ValueError:
            # 절대 경로이거나 현재 디렉토리 외부인 경우
            self.logger.warning(f"경로가 현재 디렉토리 외부에 있습니다: {path}")
            
    def _validate_tmdb_api_key(self, api_key: str) -> None:
        """TMDB API 키 형식 검증"""
        # TMDB API 키는 보통 32자리 영숫자
        if not re.match(r'^[a-f0-9]{32}$', api_key):
            raise ValidationError("TMDB API 키 형식이 올바르지 않습니다.")
            
    def sanitize_filename(self, filename: str) -> str:
        """
        파일명 정제 (위험한 문자 제거)
        
        Args:
            filename: 정제할 파일명
            
        Returns:
            str: 정제된 파일명
        """
        # 위험한 문자를 안전한 문자로 대체
        replacements = {
            '<': '_',
            '>': '_',
            ':': '_',
            '"': '_',
            '|': '_',
            '?': '_',
            '*': '_',
            '\\': '_',
            '/': '_'
        }
        
        sanitized = filename
        for dangerous, safe in replacements.items():
            sanitized = sanitized.replace(dangerous, safe)
            
        # 연속된 언더스코어 제거 (2개 이상을 1개로)
        sanitized = re.sub(r'__+', '_', sanitized)
        
        # 앞뒤 공백 및 언더스코어 제거
        sanitized = sanitized.strip(' _')
        
        return sanitized if sanitized else "unnamed"
        
    def validate_file_size(self, file_path: Path, max_size_mb: int = 1000) -> bool:
        """
        파일 크기 검증
        
        Args:
            file_path: 검증할 파일 경로
            max_size_mb: 최대 파일 크기 (MB)
            
        Returns:
            bool: 검증 결과
            
        Raises:
            ValidationError: 검증 실패 시
        """
        try:
            if not file_path.exists():
                raise ValidationError(f"파일이 존재하지 않습니다: {file_path}")
                
            file_size = file_path.stat().st_size
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if file_size > max_size_bytes:
                raise ValidationError(f"파일 크기가 너무 큽니다: {file_size / (1024*1024):.1f}MB > {max_size_mb}MB")
                
            return True
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"파일 크기 검증 실패: {str(e)}") from e


# 전역 검증기 인스턴스
validator = InputValidator()


# 편의 함수들
def validate_file_path(file_path: Union[str, Path], must_exist: bool = False) -> Path:
    """파일 경로 검증 편의 함수"""
    return validator.validate_file_path(file_path, must_exist)


def validate_directory_path(dir_path: Union[str, Path], must_exist: bool = False) -> Path:
    """디렉토리 경로 검증 편의 함수"""
    return validator.validate_directory_path(dir_path, must_exist)


def validate_api_key(api_key: str, key_type: str = "tmdb") -> str:
    """API 키 검증 편의 함수"""
    return validator.validate_api_key(api_key, key_type)


def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> str:
    """URL 검증 편의 함수"""
    return validator.validate_url(url, allowed_schemes)


def validate_filename(filename: str, allow_extensions: Optional[List[str]] = None) -> str:
    """파일명 검증 편의 함수"""
    return validator.validate_filename(filename, allow_extensions)


def sanitize_filename(filename: str) -> str:
    """파일명 정제 편의 함수"""
    return validator.sanitize_filename(filename)


# 고급 검증 기능 import
try:
    from .advanced_validators import (
        AdvancedValidator, ValidationResult,
        validate_path_security, validate_file_type, validate_input_complexity,
        validate_regex_pattern, validate_batch
    )
    ADVANCED_VALIDATION_AVAILABLE = True
except ImportError:
    ADVANCED_VALIDATION_AVAILABLE = False
    # 고급 검증 기능이 없을 때의 대체 함수들
    def validate_path_security(path, strict=True):
        """경로 보안 검증 (기본 버전)"""
        from dataclasses import dataclass
        from typing import List, Optional, Any, Dict
        
        @dataclass
        class ValidationResult:
            is_valid: bool
            errors: List[str]
            warnings: List[str]
            sanitized_value: Optional[Any] = None
            metadata: Optional[Dict[str, Any]] = None
        
        # 기본 경로 검증
        try:
            validator.validate_file_path(path, must_exist=False)
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[str(e)], warnings=[])
    
    def validate_file_type(file_path, allowed_types=None):
        """파일 타입 검증 (기본 버전)"""
        from dataclasses import dataclass
        from typing import List, Optional, Any, Dict
        
        @dataclass
        class ValidationResult:
            is_valid: bool
            errors: List[str]
            warnings: List[str]
            sanitized_value: Optional[Any] = None
            metadata: Optional[Dict[str, Any]] = None
        
        try:
            validator.validate_file_path(file_path, must_exist=True)
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[str(e)], warnings=[])
    
    def validate_input_complexity(value, **options):
        """입력 복잡성 검증 (기본 버전)"""
        from dataclasses import dataclass
        from typing import List, Optional, Any, Dict
        
        @dataclass
        class ValidationResult:
            is_valid: bool
            errors: List[str]
            warnings: List[str]
            sanitized_value: Optional[Any] = None
            metadata: Optional[Dict[str, Any]] = None
        
        try:
            if not isinstance(value, str):
                return ValidationResult(is_valid=False, errors=["값은 문자열이어야 합니다"], warnings=[])
            
            min_length = options.get('min_length', 1)
            max_length = options.get('max_length', 1000)
            
            if len(value) < min_length:
                return ValidationResult(is_valid=False, errors=[f"최소 길이 {min_length}자 미만입니다"], warnings=[])
            elif len(value) > max_length:
                return ValidationResult(is_valid=False, errors=[f"최대 길이 {max_length}자를 초과합니다"], warnings=[])
            
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[str(e)], warnings=[])
    
    def validate_regex_pattern(value, pattern, flags=0):
        """정규식 패턴 검증 (기본 버전)"""
        from dataclasses import dataclass
        from typing import List, Optional, Any, Dict
        import re
        
        @dataclass
        class ValidationResult:
            is_valid: bool
            errors: List[str]
            warnings: List[str]
            sanitized_value: Optional[Any] = None
            metadata: Optional[Dict[str, Any]] = None
        
        try:
            compiled_pattern = re.compile(pattern, flags)
            if compiled_pattern.match(value):
                return ValidationResult(is_valid=True, errors=[], warnings=[])
            else:
                return ValidationResult(is_valid=False, errors=["패턴과 일치하지 않습니다"], warnings=[])
        except re.error as e:
            return ValidationResult(is_valid=False, errors=[f"잘못된 정규식: {str(e)}"], warnings=[])
    
    def validate_batch(items):
        """배치 검증 (기본 버전)"""
        results = {}
        for name, value, options in items:
            results[name] = validate_input_complexity(value, **options)
        return results 