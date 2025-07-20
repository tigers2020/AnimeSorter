"""
스트리밍 파이프라인 이벤트 시스템

파일 처리 과정에서 발생하는 이벤트들을 정의하고 관리합니다.
UI 업데이트와 진행 상황 추적을 위한 이벤트 클래스들을 제공합니다.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union


class EventType(Enum):
    """이벤트 타입 열거형"""
    FILE_PROCESSED = "file_processed"
    FILE_STARTED = "file_started"
    FILE_ERROR = "file_error"
    METADATA_FOUND = "metadata_found"
    METADATA_NOT_FOUND = "metadata_not_found"
    FILE_MOVED = "file_moved"
    FILE_MOVE_ERROR = "file_move_error"
    PROGRESS_UPDATE = "progress_update"
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_CANCELLED = "pipeline_cancelled"
    PIPELINE_ERROR = "pipeline_error"


class ProcessingStatus(Enum):
    """파일 처리 상태 열거형"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class FileProcessedEvent:
    """
    파일 처리 완료 이벤트
    
    단일 파일의 처리 결과를 나타내는 이벤트입니다.
    """
    # 기본 속성들
    file_path: Path
    target_path: Optional[Path] = None
    metadata: Optional[Dict[str, Any]] = None
    success: bool = False
    error_message: Optional[str] = None
    
    # 처리 정보
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: EventType = EventType.FILE_PROCESSED
    
    # 추가 정보
    file_size: Optional[int] = None
    clean_title: Optional[str] = None
    year: Optional[int] = None
    provider: Optional[str] = None
    
    def __post_init__(self):
        """데이터 검증 및 후처리"""
        if self.file_size is None and self.file_path.exists():
            try:
                self.file_size = self.file_path.stat().st_size
            except (OSError, PermissionError):
                self.file_size = 0
    
    @property
    def is_success(self) -> bool:
        """처리 성공 여부"""
        return self.success and self.error_message is None
    
    @property
    def has_metadata(self) -> bool:
        """메타데이터 존재 여부"""
        return self.metadata is not None and len(self.metadata) > 0
    
    @property
    def was_moved(self) -> bool:
        """파일 이동 여부"""
        return self.target_path is not None and self.success
    
    def to_dict(self) -> Dict[str, Any]:
        """이벤트를 딕셔너리로 변환"""
        return {
            'file_path': str(self.file_path),
            'target_path': str(self.target_path) if self.target_path else None,
            'metadata': self.metadata,
            'success': self.success,
            'error_message': self.error_message,
            'processing_time': self.processing_time,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'file_size': self.file_size,
            'clean_title': self.clean_title,
            'year': self.year,
            'provider': self.provider
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileProcessedEvent':
        """딕셔너리에서 이벤트 생성"""
        return cls(
            file_path=Path(data['file_path']),
            target_path=Path(data['target_path']) if data.get('target_path') else None,
            metadata=data.get('metadata'),
            success=data.get('success', False),
            error_message=data.get('error_message'),
            processing_time=data.get('processing_time', 0.0),
            timestamp=datetime.fromisoformat(data['timestamp']),
            event_type=EventType(data['event_type']),
            file_size=data.get('file_size'),
            clean_title=data.get('clean_title'),
            year=data.get('year'),
            provider=data.get('provider')
        )


@dataclass
class ProgressEvent:
    """
    진행 상황 업데이트 이벤트
    
    전체 처리 과정의 진행 상황을 나타내는 이벤트입니다.
    """
    current_file: Optional[Path] = None
    current_index: int = 0
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    current_time: datetime = field(default_factory=datetime.now)
    message: str = ""
    
    @property
    def progress_percentage(self) -> float:
        """진행률 (0-100)"""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100
    
    @property
    def elapsed_time(self) -> float:
        """경과 시간 (초)"""
        return (self.current_time - self.start_time).total_seconds()
    
    @property
    def estimated_remaining_time(self) -> float:
        """예상 남은 시간 (초)"""
        if self.processed_files == 0:
            return 0.0
        
        avg_time_per_file = self.elapsed_time / self.processed_files
        remaining_files = self.total_files - self.processed_files
        return avg_time_per_file * remaining_files
    
    @property
    def processing_rate(self) -> float:
        """처리 속도 (파일/초)"""
        if self.elapsed_time == 0:
            return 0.0
        return self.processed_files / self.elapsed_time


@dataclass
class PipelineEvent:
    """
    파이프라인 상태 이벤트
    
    전체 파이프라인의 상태 변화를 나타내는 이벤트입니다.
    """
    event_type: EventType
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def pipeline_started(cls, total_files: int) -> 'PipelineEvent':
        """파이프라인 시작 이벤트"""
        return cls(
            event_type=EventType.PIPELINE_STARTED,
            message=f"Pipeline started with {total_files} files",
            data={'total_files': total_files}
        )
    
    @classmethod
    def pipeline_completed(cls, stats: Dict[str, Any]) -> 'PipelineEvent':
        """파이프라인 완료 이벤트"""
        return cls(
            event_type=EventType.PIPELINE_COMPLETED,
            message="Pipeline completed successfully",
            data=stats
        )
    
    @classmethod
    def pipeline_cancelled(cls, reason: str = "User cancelled") -> 'PipelineEvent':
        """파이프라인 취소 이벤트"""
        return cls(
            event_type=EventType.PIPELINE_CANCELLED,
            message=f"Pipeline cancelled: {reason}"
        )
    
    @classmethod
    def pipeline_error(cls, error: str) -> 'PipelineEvent':
        """파이프라인 오류 이벤트"""
        return cls(
            event_type=EventType.PIPELINE_ERROR,
            message=f"Pipeline error: {error}"
        )


@dataclass
class MetadataEvent:
    """
    메타데이터 관련 이벤트
    
    메타데이터 검색 결과를 나타내는 이벤트입니다.
    """
    file_path: Path
    clean_title: str
    year: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    search_time: float = 0.0
    success: bool = False
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def metadata_found(cls, file_path: Path, clean_title: str, metadata: Dict[str, Any], 
                      provider: str, search_time: float, year: Optional[int] = None) -> 'MetadataEvent':
        """메타데이터 발견 이벤트"""
        return cls(
            file_path=file_path,
            clean_title=clean_title,
            year=year,
            metadata=metadata,
            provider=provider,
            search_time=search_time,
            success=True,
            event_type=EventType.METADATA_FOUND
        )
    
    @classmethod
    def metadata_not_found(cls, file_path: Path, clean_title: str, 
                          search_time: float, year: Optional[int] = None) -> 'MetadataEvent':
        """메타데이터 미발견 이벤트"""
        return cls(
            file_path=file_path,
            clean_title=clean_title,
            year=year,
            search_time=search_time,
            success=False,
            event_type=EventType.METADATA_NOT_FOUND
        )


# 이벤트 타입 별칭
Event = Union[FileProcessedEvent, ProgressEvent, PipelineEvent, MetadataEvent] 