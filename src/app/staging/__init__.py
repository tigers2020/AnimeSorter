"""
스테이징 모듈

파일 작업을 안전하게 수행하기 위한 스테이징 디렉토리 시스템
Phase 3 요구사항: 모든 파일 조작 전 스테이징 디렉토리에서 준비
"""

import logging

logger = logging.getLogger(__name__)
# StagingManager는 새로운 서비스 아키텍처로 대체됨
# from .staging_manager import ...

# 임시로 기본 클래스들 정의
from dataclasses import dataclass
from typing import Protocol


class IStagingManager(Protocol):
    """스테이징 관리자 인터페이스"""

    def stage_file(self, file_path: str) -> str:
        """파일을 스테이징"""
        ...

    def commit_staged_files(self) -> bool:
        """스테이징된 파일들을 커밋"""
        ...

    def rollback_staged_files(self) -> bool:
        """스테이징된 파일들을 롤백"""
        ...


@dataclass
class StagedFile:
    """스테이징된 파일 정보"""

    original_path: str
    staged_path: str
    status: str = "staged"


class StagingConfiguration:
    """스테이징 설정"""

    def __init__(self):
        self.staging_dir = "staging"
        self.max_retries = 3


class StagingManager:
    """스테이징 관리자 (임시 구현)"""

    def __init__(self, config: StagingConfiguration = None):
        self.config = config or StagingConfiguration()

    def stage_file(self, file_path: str) -> str:
        """파일을 스테이징"""
        return file_path

    def commit_staged_files(self) -> bool:
        """스테이징된 파일들을 커밋"""
        return True

    def rollback_staged_files(self) -> bool:
        """스테이징된 파일들을 롤백"""
        return True


__all__ = ["StagingManager", "IStagingManager", "StagingConfiguration", "StagedFile"]
