"""
통합 입력 검증 시스템

기본 검증과 고급 검증 기능을 모두 포함하는 통합 검증 모듈입니다.
"""

import os
import re
import hashlib
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable
from dataclasses import dataclass
from functools import lru_cache
import json
import yaml
from urllib.parse import urlparse, parse_qs

# 매직 바이트 검증을 위한 선택적 import
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

from src.utils.logger import get_logger


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_value: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None


class ValidationError(Exception):
    """검증 오류"""
    pass


class InputValidator:
    """기본 입력 검증기"""
    
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
            path = Path(file_path)
            
            # 경로 구성 요소 검증
            self._validate_path_components(path)
            
            # 경로 안전성 검증
            self._validate_path_safety(path)
            
            # 파일 존재 여부 검증
            if must_exist and not path.exists():
                raise ValidationError(f"파일이 존재하지 않습니다: {path}")
                
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
            path = Path(dir_path)
            
            # 경로 구성 요소 검증
            self._validate_path_components(path)
            
            # 경로 안전성 검증
            self._validate_path_safety(path)
            
            # 디렉토리 존재 여부 검증
            if must_exist and not path.exists():
                raise ValidationError(f"디렉토리가 존재하지 않습니다: {path}")
            elif must_exist and not path.is_dir():
                raise ValidationError(f"경로가 디렉토리가 아닙니다: {path}")
                
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
            key_type: API 키 타입
            
        Returns:
            str: 검증된 API 키
            
        Raises:
            ValidationError: 검증 실패 시
        """
        if not api_key or not isinstance(api_key, str):
            raise ValidationError("API 키는 비어있지 않은 문자열이어야 합니다")
            
        api_key = api_key.strip()
        
        if not api_key:
            raise ValidationError("API 키는 비어있지 않은 문자열이어야 합니다")
            
        # API 키 타입별 검증
        if key_type == "tmdb":
            self._validate_tmdb_api_key(api_key)
        elif key_type == "anidb":
            if len(api_key) < 8:
                raise ValidationError("AniDB API 키는 최소 8자 이상이어야 합니다")
        else:
            # 기본 검증: 최소 길이
            if len(api_key) < 4:
                raise ValidationError("API 키는 최소 4자 이상이어야 합니다")
                
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
            raise ValidationError("URL은 비어있지 않은 문자열이어야 합니다")
            
        url = url.strip()
        
        if not url:
            raise ValidationError("URL은 비어있지 않은 문자열이어야 합니다")
            
        try:
            parsed = urlparse(url)
            
            # 스키마 검증
            if not parsed.scheme:
                raise ValidationError("URL에 스키마가 없습니다")
                
            if allowed_schemes and parsed.scheme not in allowed_schemes:
                raise ValidationError(f"허용되지 않는 스키마입니다: {parsed.scheme}")
                
            # 기본 스키마 검증
            if parsed.scheme not in ['http', 'https', 'ftp', 'file']:
                raise ValidationError(f"지원되지 않는 스키마입니다: {parsed.scheme}")
                
            # 네트워크 URL의 경우 호스트 검증
            if parsed.scheme in ['http', 'https', 'ftp']:
                if not parsed.netloc:
                    raise ValidationError("네트워크 URL에 호스트가 없습니다")
                    
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
            raise ValidationError("파일명은 비어있지 않은 문자열이어야 합니다")
            
        filename = filename.strip()
        
        if not filename:
            raise ValidationError("파일명은 비어있지 않은 문자열이어야 합니다")
            
        # 위험한 문자 검증
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in dangerous_chars:
            if char in filename:
                raise ValidationError(f"파일명에 위험한 문자가 포함되어 있습니다: {char}")
                
        # 확장자 검증
        if allow_extensions:
            file_ext = Path(filename).suffix.lower()
            if file_ext and file_ext not in allow_extensions:
                raise ValidationError(f"허용되지 않는 확장자입니다: {file_ext}")
                
        return filename
        
    def validate_config_value(self, key: str, value: Any, expected_type: type) -> Any:
        """
        설정 값 검증
        
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
            raise ValidationError(f"설정 '{key}'의 타입이 올바르지 않습니다. 예상: {expected_type.__name__}, 실제: {type(value).__name__}")
            
        return value
        
    def validate_sql_query(self, query: str) -> str:
        """
        SQL 쿼리 검증 (기본)
        
        Args:
            query: 검증할 SQL 쿼리
            
        Returns:
            str: 검증된 SQL 쿼리
            
        Raises:
            ValidationError: 검증 실패 시
        """
        if not query or not isinstance(query, str):
            raise ValidationError("SQL 쿼리는 비어있지 않은 문자열이어야 합니다")
            
        query = query.strip()
        
        if not query:
            raise ValidationError("SQL 쿼리는 비어있지 않은 문자열이어야 합니다")
            
        # 기본적인 위험한 키워드 검증
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER']
        query_upper = query.upper()
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                self.logger.warning(f"SQL 쿼리에 위험한 키워드가 포함되어 있습니다: {keyword}")
                
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
            raise ValidationError("데이터는 딕셔너리여야 합니다")
            
        # 필수 키 검증
        if required_keys:
            missing_keys = [key for key in required_keys if key not in data]
            if missing_keys:
                raise ValidationError(f"필수 키가 누락되었습니다: {missing_keys}")
                
        return data
        
    def _validate_path_components(self, path: Path) -> None:
        """경로 구성 요소 검증"""
        try:
            # 경로 구성 요소가 너무 깊은지 확인
            if len(path.parts) > 50:
                raise ValidationError("경로가 너무 깊습니다")
                
            # 각 구성 요소의 길이 확인
            for part in path.parts:
                if len(part) > 255:
                    raise ValidationError(f"경로 구성 요소가 너무 깁니다: {part}")
                    
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"경로 구성 요소 검증 실패: {str(e)}") from e
            
    def _validate_path_safety(self, path: Path) -> None:
        """경로 안전성 검증"""
        try:
            path_str = str(path)
            
            # 경로 순회 공격 패턴 검증
            traversal_patterns = [
                r'\.\./', r'\.\.\\', r'\.\.//', r'\.\.\\\\',
                r'%2e%2e%2f', r'%2e%2e%5c',  # URL 인코딩된 경로 순회
            ]
            
            for pattern in traversal_patterns:
                if re.search(pattern, path_str, re.IGNORECASE):
                    raise ValidationError(f"경로 순회 공격 패턴이 감지되었습니다: {pattern}")
                    
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"경로 안전성 검증 실패: {str(e)}") from e
            
    def _validate_tmdb_api_key(self, api_key: str) -> None:
        """TMDB API 키 검증"""
        # TMDB API 키는 보통 32자 길이의 16진수 문자열
        if len(api_key) != 32:
            raise ValidationError("TMDB API 키는 32자 길이여야 합니다")
            
        # 16진수 문자만 포함하는지 확인
        if not re.match(r'^[a-fA-F0-9]{32}$', api_key):
            raise ValidationError("TMDB API 키는 16진수 문자만 포함해야 합니다")
            
    def sanitize_filename(self, filename: str) -> str:
        """
        파일명 정제
        
        Args:
            filename: 정제할 파일명
            
        Returns:
            str: 정제된 파일명
        """
        if not filename:
            return "unnamed"
            
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


class AdvancedValidator(InputValidator):
    """고급 입력 검증기"""
    
    def __init__(self):
        """AdvancedValidator 초기화"""
        super().__init__()
        self.logger = get_logger(__name__)
        
        # 검증 패턴 정의
        self._init_validation_patterns()
        
        # 검증 결과 캐시
        self._validation_cache = {}
        
    def _init_validation_patterns(self):
        """검증 패턴 초기화"""
        # 경로 순회 공격 패턴
        self.path_traversal_patterns = [
            r'\.\./', r'\.\.\\', r'\.\.//', r'\.\.\\\\',
            r'%2e%2e%2f', r'%2e%2e%5c',  # URL 인코딩된 경로 순회
            r'\.\.%2f', r'\.\.%5c',      # 부분 URL 인코딩
            r'\.\.%252f', r'\.\.%255c',  # 이중 URL 인코딩
        ]
        
        # 명령어 인젝션 패턴
        self.command_injection_patterns = [
            r'[;&|`$()]',  # 기본 명령어 구분자
            r'\$\{.*\}',   # 변수 확장
            r'`.*`',       # 백틱 명령어
            r'\(.*\)',     # 서브셸
            r'\|\s*\w+',   # 파이프 명령어
        ]
        
        # XSS 패턴
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>',
            r'javascript:', r'vbscript:', r'data:',
            r'on\w+\s*=',  # 이벤트 핸들러
        ]
        
        # 파일 확장자별 매직 바이트
        self.magic_bytes = {
            b'\x89PNG\r\n\x1a\n': '.png',
            b'\xff\xd8\xff': '.jpg',
            b'GIF87a': '.gif',
            b'GIF89a': '.gif',
            b'%PDF': '.pdf',
            b'PK\x03\x04': '.zip',
            b'Rar!': '.rar',
            b'\x1f\x8b\x08': '.gz',
            b'\x00\x00\x01\x00': '.ico',
            b'BM': '.bmp',
            b'RIFF': '.wav',
            b'ID3': '.mp3',
            b'\x00\x00\x00\x20ftyp': '.mp4',
            b'\x00\x00\x00\x18ftyp': '.mp4',
            b'\x00\x00\x00\x1cftyp': '.mp4',
        }
        
    def validate_path_security(self, path: Union[str, Path], strict: bool = True) -> ValidationResult:
        """
        고급 경로 보안 검증
        
        Args:
            path: 검증할 경로
            strict: 엄격한 검증 모드
            
        Returns:
            ValidationResult: 검증 결과
        """
        errors = []
        warnings = []
        
        try:
            path_str = str(path)
            
            # 1. 경로 순회 공격 검증
            for pattern in self.path_traversal_patterns:
                if re.search(pattern, path_str, re.IGNORECASE):
                    errors.append(f"경로 순회 공격 패턴 감지: {pattern}")
                    
            # 2. 절대 경로 검증
            if os.path.isabs(path_str):
                if strict:
                    warnings.append("절대 경로 사용 (보안상 주의 필요)")
                    
            # 3. 위험한 디렉토리 검증
            dangerous_dirs = [
                '/etc', '/var', '/usr', '/bin', '/sbin',  # Unix
                'C:\\Windows', 'C:\\System32', 'C:\\Program Files',  # Windows
            ]
            
            for dangerous_dir in dangerous_dirs:
                if dangerous_dir.lower() in path_str.lower():
                    errors.append(f"위험한 디렉토리 접근 시도: {dangerous_dir}")
                    
            # 4. 숨겨진 파일 검증
            if path_str.startswith('.'):
                warnings.append("숨겨진 파일/디렉토리 접근")
                
            # 5. 경로 길이 검증
            if len(path_str) > 4096:  # 일반적인 파일 시스템 제한
                errors.append("경로가 너무 깁니다")
                
            # 6. 특수 문자 검증
            special_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07',
                           '\x08', '\x09', '\x0a', '\x0b', '\x0c', '\x0d', '\x0e', '\x0f']
            for char in special_chars:
                if char in path_str:
                    errors.append(f"제어 문자가 포함되어 있습니다: {repr(char)}")
                    
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                sanitized_value=str(path) if is_valid else None
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"경로 검증 중 오류 발생: {str(e)}"],
                warnings=warnings
            )
            
    def validate_file_type(self, file_path: Path, allowed_types: Optional[List[str]] = None) -> ValidationResult:
        """
        파일 타입 검증 (매직 바이트 기반)
        
        Args:
            file_path: 검증할 파일 경로
            allowed_types: 허용된 파일 타입 목록
            
        Returns:
            ValidationResult: 검증 결과
        """
        errors = []
        warnings = []
        
        try:
            if not file_path.exists():
                return ValidationResult(
                    is_valid=False,
                    errors=["파일이 존재하지 않습니다"],
                    warnings=warnings
                )
                
            # 파일 크기 확인
            file_size = file_path.stat().st_size
            if file_size == 0:
                return ValidationResult(
                    is_valid=False,
                    errors=["빈 파일입니다"],
                    warnings=warnings
                )
                
            # 매직 바이트 검증
            detected_type = None
            
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(16)  # 첫 16바이트 읽기
                    
                # 매직 바이트 패턴 매칭
                for magic_bytes, file_ext in self.magic_bytes.items():
                    if header.startswith(magic_bytes):
                        detected_type = file_ext
                        break
                        
                # python-magic 라이브러리 사용 (가능한 경우)
                if MAGIC_AVAILABLE and not detected_type:
                    try:
                        mime_type = magic.from_file(str(file_path), mime=True)
                        detected_type = mimetypes.guess_extension(mime_type)
                    except Exception:
                        pass
                        
            except Exception as e:
                warnings.append(f"파일 타입 감지 실패: {str(e)}")
                
            # 확장자 기반 검증
            file_ext = file_path.suffix.lower()
            if not detected_type and file_ext:
                detected_type = file_ext
                
            # 허용된 타입 검증
            if allowed_types and detected_type:
                if detected_type not in allowed_types:
                    errors.append(f"허용되지 않는 파일 타입입니다: {detected_type}")
                    
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                sanitized_value=detected_type,
                metadata={'file_size': file_size, 'extension': file_ext}
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"파일 타입 검증 중 오류 발생: {str(e)}"],
                warnings=warnings
            )
            
    def validate_input_complexity(self, value: str, min_length: int = 1, max_length: int = 1000,
                                require_uppercase: bool = False, require_lowercase: bool = False,
                                require_digits: bool = False, require_special: bool = False,
                                check_security: bool = True) -> ValidationResult:
        """
        입력 복잡성 검증
        
        Args:
            value: 검증할 값
            min_length: 최소 길이
            max_length: 최대 길이
            require_uppercase: 대문자 필수 여부
            require_lowercase: 소문자 필수 여부
            require_digits: 숫자 필수 여부
            require_special: 특수문자 필수 여부
            check_security: 보안 검사 여부
            
        Returns:
            ValidationResult: 검증 결과
        """
        errors = []
        warnings = []
        
        try:
            if not isinstance(value, str):
                return ValidationResult(
                    is_valid=False,
                    errors=["값은 문자열이어야 합니다"],
                    warnings=warnings
                )
                
            # 길이 검증
            if len(value) < min_length:
                errors.append(f"최소 길이 {min_length}자 미만입니다")
            elif len(value) > max_length:
                errors.append(f"최대 길이 {max_length}자를 초과합니다")
                
            # 복잡성 검증
            if require_uppercase and not re.search(r'[A-Z]', value):
                errors.append("대문자가 포함되어야 합니다")
                
            if require_lowercase and not re.search(r'[a-z]', value):
                errors.append("소문자가 포함되어야 합니다")
                
            if require_digits and not re.search(r'\d', value):
                errors.append("숫자가 포함되어야 합니다")
                
            if require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', value):
                errors.append("특수문자가 포함되어야 합니다")
                
            # 보안 검사
            if check_security:
                # 명령어 인젝션 검사
                for pattern in self.command_injection_patterns:
                    if re.search(pattern, value):
                        errors.append(f"명령어 인젝션 패턴 감지: {pattern}")
                        
                # XSS 검사
                for pattern in self.xss_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        errors.append(f"XSS 패턴 감지: {pattern}")
                        
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                sanitized_value=value if len(errors) == 0 else None
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"입력 복잡성 검증 중 오류 발생: {str(e)}"],
                warnings=warnings
            )
            
    def validate_regex_pattern(self, value: str, pattern: str, flags: int = 0) -> ValidationResult:
        """
        정규식 패턴 검증
        
        Args:
            value: 검증할 값
            pattern: 정규식 패턴
            flags: 정규식 플래그
            
        Returns:
            ValidationResult: 검증 결과
        """
        errors = []
        warnings = []
        
        try:
            # 정규식 컴파일
            compiled_pattern = re.compile(pattern, flags)
            
            # 패턴 매칭
            if compiled_pattern.match(value):
                return ValidationResult(
                    is_valid=True,
                    errors=errors,
                    warnings=warnings,
                    sanitized_value=value
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    errors=["패턴과 일치하지 않습니다"],
                    warnings=warnings
                )
                
        except re.error as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"잘못된 정규식: {str(e)}"],
                warnings=warnings
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"정규식 검증 중 오류 발생: {str(e)}"],
                warnings=warnings
            )
            
    def validate_batch(self, items: List[Tuple[str, Any, Dict[str, Any]]]) -> Dict[str, ValidationResult]:
        """
        배치 검증
        
        Args:
            items: 검증할 항목 목록 (이름, 값, 옵션)
            
        Returns:
            Dict[str, ValidationResult]: 검증 결과 딕셔너리
        """
        results = {}
        
        for name, value, options in items:
            try:
                if isinstance(value, str):
                    results[name] = self.validate_input_complexity(value, **options)
                else:
                    results[name] = ValidationResult(
                        is_valid=False,
                        errors=["문자열이 아닌 값은 지원하지 않습니다"],
                        warnings=[]
                    )
            except Exception as e:
                results[name] = ValidationResult(
                    is_valid=False,
                    errors=[f"배치 검증 중 오류 발생: {str(e)}"],
                    warnings=[]
                )
                
        return results
        
    @lru_cache(maxsize=1000)
    def validate_with_cache(self, value: str, validation_type: str, **options) -> ValidationResult:
        """
        캐시를 사용한 검증
        
        Args:
            value: 검증할 값
            validation_type: 검증 타입
            **options: 검증 옵션
            
        Returns:
            ValidationResult: 검증 결과
        """
        if validation_type == "complexity":
            return self.validate_input_complexity(value, **options)
        elif validation_type == "path_security":
            return self.validate_path_security(value, **options)
        elif validation_type == "regex":
            return self.validate_regex_pattern(value, **options)
        else:
            return ValidationResult(
                is_valid=False,
                errors=[f"지원되지 않는 검증 타입: {validation_type}"],
                warnings=[]
            )
            
    def clear_cache(self):
        """검증 캐시 초기화"""
        self.validate_with_cache.cache_clear()
        self._validation_cache.clear()


# 전역 검증기 인스턴스
validator = InputValidator()
advanced_validator = AdvancedValidator()


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


# 고급 검증 편의 함수들
def validate_path_security(path: Union[str, Path], strict: bool = True) -> ValidationResult:
    """경로 보안 검증 편의 함수"""
    return advanced_validator.validate_path_security(path, strict)


def validate_file_type(file_path: Path, allowed_types: Optional[List[str]] = None) -> ValidationResult:
    """파일 타입 검증 편의 함수"""
    return advanced_validator.validate_file_type(file_path, allowed_types)


def validate_input_complexity(value: str, **options) -> ValidationResult:
    """입력 복잡성 검증 편의 함수"""
    return advanced_validator.validate_input_complexity(value, **options)


def validate_regex_pattern(value: str, pattern: str, flags: int = 0) -> ValidationResult:
    """정규식 패턴 검증 편의 함수"""
    return advanced_validator.validate_regex_pattern(value, pattern, flags)


def validate_batch(items: List[Tuple[str, Any, Dict[str, Any]]]) -> Dict[str, ValidationResult]:
    """배치 검증 편의 함수"""
    return advanced_validator.validate_batch(items) 