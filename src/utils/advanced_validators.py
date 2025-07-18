"""
고급 입력 검증 시스템

기본 검증 시스템을 확장하여 더 강력한 보안과 검증 기능을 제공하는 모듈입니다.
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

from .validators import InputValidator, ValidationError
from ..utils.logger import get_logger


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_value: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None


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
                
            # 매직 바이트 읽기
            with open(file_path, 'rb') as f:
                header = f.read(16)  # 첫 16바이트 읽기
                
            # 매직 바이트 기반 파일 타입 확인
            detected_type = None
            for magic_bytes, extension in self.magic_bytes.items():
                if header.startswith(magic_bytes):
                    detected_type = extension
                    break
                    
            # MIME 타입 확인
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # 파일 확장자 확인
            file_extension = file_path.suffix.lower()
            
            # 고급 매직 라이브러리 사용 (가능한 경우)
            if MAGIC_AVAILABLE and not detected_type:
                try:
                    magic_instance = magic.Magic(mime=True)
                    mime_detected = magic_instance.from_file(str(file_path))
                    if mime_detected:
                        # MIME 타입을 확장자로 변환
                        for ext, mime in mimetypes.types_map.items():
                            if mime == mime_detected:
                                detected_type = ext
                                break
                except Exception as e:
                    warnings.append(f"고급 파일 타입 감지 실패: {str(e)}")
            
            # 타입 일치성 검증
            if detected_type and file_extension:
                if detected_type != file_extension:
                    warnings.append(f"파일 확장자와 실제 타입이 일치하지 않습니다: {file_extension} vs {detected_type}")
                    
            # 허용된 타입 검증
            if allowed_types:
                if detected_type and detected_type not in allowed_types:
                    errors.append(f"허용되지 않는 파일 타입입니다: {detected_type}")
                elif file_extension and file_extension not in allowed_types:
                    errors.append(f"허용되지 않는 파일 확장자입니다: {file_extension}")
                    
            # 파일 크기 경고
            if file_size > 100 * 1024 * 1024:  # 100MB
                warnings.append("파일 크기가 큽니다")
                
            is_valid = len(errors) == 0
            
            metadata = {
                'detected_type': detected_type,
                'mime_type': mime_type,
                'file_extension': file_extension,
                'file_size': file_size,
                'magic_bytes': header[:8].hex(),
                'magic_library_available': MAGIC_AVAILABLE
            }
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                sanitized_value=str(file_path) if is_valid else None,
                metadata=metadata
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
            require_uppercase: 대문자 포함 필요 여부
            require_lowercase: 소문자 포함 필요 여부
            require_digits: 숫자 포함 필요 여부
            require_special: 특수문자 포함 필요 여부
            check_security: 보안 패턴 검증 여부
            
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
                
            # 보안 패턴 검증
            if check_security:
                # 명령어 인젝션 패턴 검증
                for pattern in self.command_injection_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        errors.append(f"명령어 인젝션 패턴이 감지되었습니다: {pattern}")
                        break
                        
                # XSS 패턴 검증
                for pattern in self.xss_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        errors.append(f"XSS 패턴이 감지되었습니다: {pattern}")
                        break
                        
                # SQL 인젝션 패턴 검증
                sql_patterns = [
                    r"';?\s*(DROP|DELETE|UPDATE|INSERT|CREATE|ALTER|TRUNCATE)",
                    r"'\s*OR\s*'1'='1",
                    r"'\s*OR\s*1=1",
                    r"admin'--",
                    r"'\s*UNION\s*SELECT"
                ]
                for pattern in sql_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        errors.append(f"SQL 인젝션 패턴이 감지되었습니다: {pattern}")
                        break
                
            # 연속 문자 검증
            if re.search(r'(.)\1{3,}', value):  # 4개 이상 연속된 동일 문자
                warnings.append("연속된 동일 문자가 많습니다")
                
            # 패턴 검증
            if re.search(r'(123|abc|qwe|asd)', value.lower()):
                warnings.append("일반적인 패턴이 감지되었습니다")
                
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                sanitized_value=value if is_valid else None
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"복잡성 검증 중 오류 발생: {str(e)}"],
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
            if not isinstance(value, str):
                return ValidationResult(
                    is_valid=False,
                    errors=["값은 문자열이어야 합니다"],
                    warnings=warnings
                )
                
            # 정규식 패턴 컴파일
            try:
                compiled_pattern = re.compile(pattern, flags)
            except re.error as e:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"잘못된 정규식 패턴입니다: {str(e)}"],
                    warnings=warnings
                )
                
            # 패턴 매칭 검증
            if not compiled_pattern.match(value):
                errors.append(f"값이 패턴과 일치하지 않습니다: {pattern}")
                
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                sanitized_value=value if is_valid else None
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
            items: 검증할 항목 목록 (name, value, options)
            
        Returns:
            Dict[str, ValidationResult]: 검증 결과 딕셔너리
        """
        results = {}
        
        for name, value, options in items:
            try:
                # 검증 타입에 따른 검증 함수 호출
                validation_type = options.get('type', 'string')
                
                if validation_type == 'path':
                    results[name] = self.validate_path_security(value, options.get('strict', True))
                elif validation_type == 'file_type':
                    results[name] = self.validate_file_type(value, options.get('allowed_types'))
                elif validation_type == 'complexity':
                    results[name] = self.validate_input_complexity(
                        value,
                        min_length=options.get('min_length', 1),
                        max_length=options.get('max_length', 1000),
                        require_uppercase=options.get('require_uppercase', False),
                        require_lowercase=options.get('require_lowercase', False),
                        require_digits=options.get('require_digits', False),
                        require_special=options.get('require_special', False)
                    )
                elif validation_type == 'regex':
                    results[name] = self.validate_regex_pattern(
                        value,
                        options.get('pattern', ''),
                        options.get('flags', 0)
                    )
                else:
                    # 기본 문자열 검증
                    results[name] = self.validate_input_complexity(
                        value,
                        min_length=options.get('min_length', 1),
                        max_length=options.get('max_length', 1000)
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
        캐시를 사용한 검증 (성능 최적화)
        
        Args:
            value: 검증할 값
            validation_type: 검증 타입
            **options: 검증 옵션
            
        Returns:
            ValidationResult: 검증 결과
        """
        # 캐시 키 생성
        cache_key = f"{validation_type}:{hash(value)}:{hash(str(options))}"
        
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]
            
        # 검증 수행
        if validation_type == 'path':
            result = self.validate_path_security(value, options.get('strict', True))
        elif validation_type == 'complexity':
            result = self.validate_input_complexity(value, **options)
        elif validation_type == 'regex':
            result = self.validate_regex_pattern(value, options.get('pattern', ''))
        else:
            result = self.validate_input_complexity(value)
            
        # 결과 캐싱
        self._validation_cache[cache_key] = result
        return result
        
    def clear_cache(self):
        """검증 캐시 정리"""
        self._validation_cache.clear()
        self.validate_with_cache.cache_clear()


# 전역 고급 검증기 인스턴스
advanced_validator = AdvancedValidator()


# 편의 함수들
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