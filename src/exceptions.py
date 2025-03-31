"""
애플리케이션 예외 정의 모듈

애플리케이션에서 사용하는 사용자 정의 예외 클래스
"""

class AnimeSorterError(Exception):
    """애니메이션 정렬기 기본 예외"""
    pass


class ConfigError(AnimeSorterError):
    """설정 관련 오류"""
    pass


class FileCleanerError(AnimeSorterError):
    """파일명 정제 오류"""
    pass


class CacheError(AnimeSorterError):
    """캐시 데이터베이스 오류"""
    pass


class MetadataError(AnimeSorterError):
    """메타데이터 검색 오류"""
    pass


class TMDBApiError(MetadataError):
    """TMDB API 오류"""
    
    def __init__(self, message, status_code=None, reason=None):
        self.status_code = status_code
        self.reason = reason
        super().__init__(f"{message} (Status: {status_code}, Reason: {reason})")


class FileManagerError(AnimeSorterError):
    """파일 관리 오류"""
    pass


class NetworkError(AnimeSorterError):
    """네트워크 관련 오류"""
    pass 