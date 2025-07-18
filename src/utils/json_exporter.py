"""
파일 스캔 결과 JSON 내보내기 유틸리티

파일 스캔 결과를 JSON 형식으로 저장하고 로드하는 기능을 제공합니다.
"""

import json
import gzip
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict, field
from enum import Enum

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger


class ExportFormat(Enum):
    """내보내기 형식"""
    JSON = "json"
    GZIPPED_JSON = "json.gz"
    MINIFIED_JSON = "minified.json"


@dataclass
class ScanMetadata:
    """스캔 메타데이터"""
    scan_timestamp: str
    total_files: int
    total_groups: int
    scan_duration: float
    source_directory: str
    version: str = "1.0.0"
    export_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FileInfo:
    """파일 정보"""
    original_path: str
    file_name: str
    file_size: int
    file_extension: str
    last_modified: str
    is_video: bool
    is_subtitle: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GroupedFileData:
    """그룹화된 파일 데이터"""
    title: str
    year: Optional[int]
    season: int
    episode: Optional[int]
    files: List[FileInfo]
    total_size: int
    file_count: int
    video_count: int
    subtitle_count: int


@dataclass
class ScanResultExport:
    """스캔 결과 내보내기 데이터"""
    metadata: ScanMetadata
    groups: List[GroupedFileData]
    statistics: Dict[str, Any] = field(default_factory=dict)


class JSONExporter:
    """JSON 내보내기 클래스"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    def export_scan_results(self, 
                           grouped_files: Dict, 
                           source_directory: str,
                           scan_duration: float,
                           output_path: Union[str, Path],
                           format: ExportFormat = ExportFormat.JSON,
                           include_metadata: bool = True,
                           compress: bool = False) -> Path:
        """
        스캔 결과를 JSON으로 내보내기
        
        Args:
            grouped_files: 그룹화된 파일 데이터
            source_directory: 소스 디렉토리 경로
            scan_duration: 스캔 소요 시간
            output_path: 출력 파일 경로
            format: 내보내기 형식
            include_metadata: 메타데이터 포함 여부
            compress: 압축 여부
            
        Returns:
            Path: 저장된 파일 경로
        """
        output_path = Path(output_path)
        
        # 스캔 결과 데이터 구조화
        scan_data = self._structure_scan_data(
            grouped_files, source_directory, scan_duration
        )
        
        # JSON 직렬화
        json_data = self._serialize_to_json(scan_data, format)
        
        # 파일 저장
        return self._save_to_file(json_data, output_path, format, compress)
    
    def _structure_scan_data(self, 
                           grouped_files: Dict, 
                           source_directory: str,
                           scan_duration: float) -> ScanResultExport:
        """스캔 데이터를 구조화된 형태로 변환"""
        
        # 메타데이터 생성
        total_files = sum(len(files) for files in grouped_files.values())
        metadata = ScanMetadata(
            scan_timestamp=datetime.now().isoformat(),
            total_files=total_files,
            total_groups=len(grouped_files),
            scan_duration=scan_duration,
            source_directory=str(source_directory)
        )
        
        # 그룹 데이터 변환
        groups = []
        total_size = 0
        total_video_count = 0
        total_subtitle_count = 0
        
        for (title, year, season), files in grouped_files.items():
            group_files = []
            group_size = 0
            video_count = 0
            subtitle_count = 0
            
            # 파일 정보 추출
            for file_data in files:
                if hasattr(file_data, 'original_filename'):
                    file_path = Path(file_data.original_filename)
                elif isinstance(file_data, dict):
                    file_path = Path(file_data.get('original_filename', ''))
                else:
                    continue
                
                # 파일 크기 조회
                try:
                    file_size = file_path.stat().st_size
                except (OSError, FileNotFoundError):
                    file_size = 0
                
                # 파일 타입 판별
                ext = file_path.suffix.lower()
                is_video = ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.flv']
                is_subtitle = ext in ['.srt', '.ass', '.ssa', '.sub', '.idx', '.smi', '.vtt']
                
                if is_video:
                    video_count += 1
                elif is_subtitle:
                    subtitle_count += 1
                
                # 파일 정보 생성
                try:
                    last_modified = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                except (OSError, FileNotFoundError):
                    last_modified = datetime.now().isoformat()
                
                file_info = FileInfo(
                    original_path=str(file_path),
                    file_name=file_path.name,
                    file_size=file_size,
                    file_extension=ext,
                    last_modified=last_modified,
                    is_video=is_video,
                    is_subtitle=is_subtitle,
                    metadata=self._extract_file_metadata(file_data)
                )
                
                group_files.append(file_info)
                group_size += file_size
            
            # 그룹 정보 생성
            group_data = GroupedFileData(
                title=title,
                year=year,
                season=season,
                episode=getattr(files[0], 'episode', None) if files else None,
                files=group_files,
                total_size=group_size,
                file_count=len(group_files),
                video_count=video_count,
                subtitle_count=subtitle_count
            )
            
            groups.append(group_data)
            total_size += group_size
            total_video_count += video_count
            total_subtitle_count += subtitle_count
        
        # 통계 정보
        statistics = {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
            "total_video_files": total_video_count,
            "total_subtitle_files": total_subtitle_count,
            "average_group_size": round(total_size / len(groups), 2) if groups else 0,
            "largest_group": max(len(g.files) for g in groups) if groups else 0,
            "smallest_group": min(len(g.files) for g in groups) if groups else 0
        }
        
        return ScanResultExport(
            metadata=metadata,
            groups=groups,
            statistics=statistics
        )
    
    def _extract_file_metadata(self, file_data: Any) -> Dict[str, Any]:
        """파일 데이터에서 메타데이터 추출"""
        metadata = {}
        
        if hasattr(file_data, '__dict__'):
            # 객체인 경우
            for key, value in file_data.__dict__.items():
                if key not in ['original_filename'] and value is not None:
                    metadata[key] = value
        elif isinstance(file_data, dict):
            # 딕셔너리인 경우
            for key, value in file_data.items():
                if key not in ['original_filename'] and value is not None:
                    metadata[key] = value
        
        return metadata
    
    def _serialize_to_json(self, 
                          scan_data: ScanResultExport, 
                          format: ExportFormat) -> str:
        """데이터를 JSON 문자열로 직렬화"""
        
        # dataclass를 딕셔너리로 변환
        data_dict = asdict(scan_data)
        
        # JSON 직렬화 옵션
        indent = None if format == ExportFormat.MINIFIED_JSON else 2
        separators = (',', ':') if format == ExportFormat.MINIFIED_JSON else None
        
        return json.dumps(
            data_dict,
            indent=indent,
            separators=separators,
            ensure_ascii=False,
            default=str
        )
    
    def _save_to_file(self, 
                     json_data: str, 
                     output_path: Path, 
                     format: ExportFormat,
                     compress: bool) -> Path:
        """JSON 데이터를 파일로 저장"""
        
        # 출력 디렉토리 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장
        if format == ExportFormat.GZIPPED_JSON or compress:
            with gzip.open(output_path.with_suffix('.json.gz'), 'wt', encoding='utf-8') as f:
                f.write(json_data)
            final_path = output_path.with_suffix('.json.gz')
        else:
            with open(output_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
                f.write(json_data)
            final_path = output_path.with_suffix('.json')
        
        self.logger.info(f"스캔 결과가 저장되었습니다: {final_path}")
        return final_path
    
    def load_scan_results(self, 
                         file_path: Union[str, Path]) -> ScanResultExport:
        """
        JSON 파일에서 스캔 결과 로드
        
        Args:
            file_path: JSON 파일 경로
            
        Returns:
            ScanResultExport: 로드된 스캔 결과
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
        # 파일 읽기
        if file_path.suffix == '.gz':
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # 딕셔너리를 dataclass로 변환
        return self._deserialize_from_dict(data)
    
    def _deserialize_from_dict(self, data: Dict[str, Any]) -> ScanResultExport:
        """딕셔너리에서 ScanResultExport 객체 생성"""
        
        # 메타데이터 변환
        metadata = ScanMetadata(**data.get('metadata', {}))
        
        # 그룹 데이터 변환
        groups = []
        for group_data in data.get('groups', []):
            files = [FileInfo(**file_data) for file_data in group_data.get('files', [])]
            
            group = GroupedFileData(
                title=group_data['title'],
                year=group_data.get('year'),
                season=group_data.get('season', 1),
                episode=group_data.get('episode'),
                files=files,
                total_size=group_data.get('total_size', 0),
                file_count=group_data.get('file_count', 0),
                video_count=group_data.get('video_count', 0),
                subtitle_count=group_data.get('subtitle_count', 0)
            )
            groups.append(group)
        
        return ScanResultExport(
            metadata=metadata,
            groups=groups,
            statistics=data.get('statistics', {})
        )
    
    def get_export_summary(self, scan_data: ScanResultExport) -> str:
        """스캔 결과 요약 정보 생성"""
        
        metadata = scan_data.metadata
        stats = scan_data.statistics
        
        summary = f"""
=== 스캔 결과 요약 ===
📁 소스 디렉토리: {metadata.source_directory}
📅 스캔 시간: {metadata.scan_timestamp}
⏱️  스캔 소요 시간: {metadata.scan_duration:.2f}초

📊 파일 통계:
   • 총 파일 수: {metadata.total_files:,}개
   • 그룹 수: {metadata.total_groups:,}개
   • 비디오 파일: {stats.get('total_video_files', 0):,}개
   • 자막 파일: {stats.get('total_subtitle_files', 0):,}개

💾 용량 통계:
   • 총 용량: {stats.get('total_size_gb', 0):.2f}GB
   • 평균 그룹 크기: {stats.get('average_group_size', 0):.2f}MB
   • 최대 그룹: {stats.get('largest_group', 0)}개 파일
   • 최소 그룹: {stats.get('smallest_group', 0)}개 파일
"""
        
        return summary.strip() 