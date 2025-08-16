"""
파일 관리 모듈 - AnimeSorter

파일 정리, 이동, 복사 등의 작업을 관리하는 기능을 제공합니다.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FileOperationResult:
    """파일 작업 결과"""
    success: bool
    source_path: str
    destination_path: Optional[str] = None
    error_message: Optional[str] = None
    operation_type: str = ""  # copy, move, rename
    file_size: Optional[int] = None
    processing_time: Optional[float] = None


class FileManager:
    """파일 관리자"""
    
    def __init__(self, destination_root: str = "", safe_mode: bool = True):
        """초기화"""
        self.destination_root = Path(destination_root) if destination_root else Path.cwd()
        self.safe_mode = safe_mode
        self.naming_scheme = "standard"  # standard, minimal, detailed
        self.logger = logging.getLogger(__name__)
        
        # 지원되는 비디오 확장자
        self.video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.flv', '.webm'}
        
        # 지원되는 자막 확장자
        self.subtitle_extensions = {'.srt', '.ass', '.ssa', '.sub', '.idx', '.smi', '.vtt'}
    
    def set_destination_root(self, path: str) -> bool:
        """대상 루트 디렉토리 설정"""
        try:
            new_path = Path(path)
            if new_path.exists() and new_path.is_dir():
                self.destination_root = new_path
                return True
            else:
                self.logger.warning(f"대상 디렉토리가 존재하지 않거나 디렉토리가 아닙니다: {path}")
                return False
        except Exception as e:
            self.logger.error(f"대상 디렉토리 설정 실패: {e}")
            return False
    
    def set_safe_mode(self, enabled: bool) -> None:
        """안전 모드 설정"""
        self.safe_mode = enabled
        self.logger.info(f"안전 모드: {'활성화' if enabled else '비활성화'}")
    
    def set_naming_scheme(self, scheme: str) -> None:
        """파일명 지정 방식 설정"""
        if scheme in ["standard", "minimal", "detailed"]:
            self.naming_scheme = scheme
            self.logger.info(f"파일명 지정 방식: {scheme}")
        else:
            self.logger.warning(f"지원되지 않는 파일명 지정 방식: {scheme}")
    
    def organize_file(self, source_path: str, metadata: Dict, operation: str = "copy") -> FileOperationResult:
        """단일 파일 정리"""
        start_time = datetime.now()
        
        try:
            source_file = Path(source_path)
            if not source_file.exists():
                return FileOperationResult(
                    success=False,
                    source_path=source_path,
                    error_message="소스 파일이 존재하지 않습니다",
                    operation_type=operation
                )
            
            # 대상 경로 생성
            destination_path = self._generate_destination_path(source_file, metadata)
            if not destination_path:
                return FileOperationResult(
                    success=False,
                    source_path=source_path,
                    error_message="대상 경로 생성 실패",
                    operation_type=operation
                )
            
            # 대상 디렉토리 생성
            destination_dir = destination_path.parent
            destination_dir.mkdir(parents=True, exist_ok=True)
            
            # 파일 작업 수행
            if operation == "copy":
                result = self._copy_file(source_file, destination_path)
            elif operation == "move":
                result = self._move_file(source_file, destination_path)
            else:
                return FileOperationResult(
                    success=False,
                    source_path=source_path,
                    error_message=f"지원되지 않는 작업: {operation}",
                    operation_type=operation
                )
            
            # 결과 정보 추가
            if result.success:
                result.destination_path = str(destination_path)
                result.file_size = source_file.stat().st_size
                result.processing_time = (datetime.now() - start_time).total_seconds()
            
            return result
            
        except Exception as e:
            self.logger.error(f"파일 정리 실패: {e}")
            return FileOperationResult(
                success=False,
                source_path=source_path,
                error_message=str(e),
                operation_type=operation
            )
    
    def batch_organize(self, file_operations: List[Tuple[str, Dict, str]], 
                       progress_callback: Optional[Callable[[int, int], None]] = None) -> List[FileOperationResult]:
        """여러 파일 일괄 정리"""
        results = []
        total_files = len(file_operations)
        
        for i, (source_path, metadata, operation) in enumerate(file_operations):
            # 진행률 콜백 호출
            if progress_callback:
                progress_callback(i, total_files)
            
            # 파일 정리 수행
            result = self.organize_file(source_path, metadata, operation)
            results.append(result)
            
            # 로그 출력
            if result.success:
                self.logger.info(f"✅ {Path(source_path).name} 정리 완료")
            else:
                self.logger.error(f"❌ {Path(source_path).name} 정리 실패: {result.error_message}")
        
        # 최종 진행률 100% (모든 파일 처리 완료 후)
        if progress_callback:
            progress_callback(total_files, total_files)
        
        return results
    
    def _generate_destination_path(self, source_file: Path, metadata: Dict) -> Optional[Path]:
        """대상 파일 경로 생성"""
        try:
            # 기본 정보 추출
            title = metadata.get('title', 'Unknown')
            season = metadata.get('season', 1)
            episode = metadata.get('episode')
            resolution = metadata.get('resolution', '')
            group = metadata.get('group', '')
            
            # 제목 정리
            title = self._clean_title_for_path(title)
            
            # 시즌 디렉토리명 생성
            if season == 1:
                season_dir = title
            else:
                season_dir = f"{title} Season {season}"
            
            # 에피소드 파일명 생성
            if episode:
                episode_filename = self._generate_episode_filename(
                    title, season, episode, resolution, group
                )
            else:
                episode_filename = f"{title}{source_file.suffix}"
            
            # 전체 경로 구성
            destination_path = self.destination_root / season_dir / episode_filename
            
            return destination_path
            
        except Exception as e:
            self.logger.error(f"대상 경로 생성 실패: {e}")
            return None
    
    def _generate_episode_filename(self, title: str, season: int, episode: int, 
                                  resolution: str, group: str) -> str:
        """에피소드 파일명 생성"""
        if self.naming_scheme == "minimal":
            # 최소한의 정보만 포함
            filename = f"{title} S{season:02d}E{episode:02d}"
            if resolution:
                filename += f" {resolution}"
            filename += ".mkv"  # 기본 확장자
            
        elif self.naming_scheme == "detailed":
            # 상세한 정보 포함
            filename = f"{title} S{season:02d}E{episode:02d}"
            if resolution:
                filename += f" {resolution}"
            if group:
                filename += f" [{group}]"
            filename += ".mkv"
            
        else:  # standard
            # 표준 형식
            filename = f"{title} S{season:02d}E{episode:02d}"
            if resolution and resolution.strip():
                filename += f" - {resolution}"
            filename += ".mkv"
        
        return filename
    
    def _clean_title_for_path(self, title: str) -> str:
        """경로용 제목 정리"""
        if not title:
            return "Unknown"
        
        # 파일 시스템에서 사용할 수 없는 문자 제거/변환
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            title = title.replace(char, '')
        
        # 연속 공백을 단일 공백으로
        title = ' '.join(title.split())
        
        # 앞뒤 공백 제거
        title = title.strip()
        
        return title if title else "Unknown"
    
    def _copy_file(self, source: Path, destination: Path) -> FileOperationResult:
        """파일 복사"""
        try:
            # 안전 모드: 기존 파일 확인
            if self.safe_mode and destination.exists():
                return FileOperationResult(
                    success=False,
                    source_path=str(source),
                    destination_path=str(destination),
                    error_message="대상 파일이 이미 존재합니다 (안전 모드)",
                    operation_type="copy"
                )
            
            # 파일 복사
            shutil.copy2(source, destination)
            
            self.logger.info(f"파일 복사 완료: {source.name} -> {destination}")
            
            return FileOperationResult(
                success=True,
                source_path=str(source),
                destination_path=str(destination),
                operation_type="copy"
            )
            
        except Exception as e:
            self.logger.error(f"파일 복사 실패: {e}")
            return FileOperationResult(
                success=False,
                source_path=str(source),
                destination_path=str(destination),
                error_message=str(e),
                operation_type="copy"
            )
    
    def _move_file(self, source: Path, destination: Path) -> FileOperationResult:
        """파일 이동"""
        try:
            # 안전 모드: 기존 파일 확인
            if self.safe_mode and destination.exists():
                return FileOperationResult(
                    success=False,
                    source_path=str(source),
                    destination_path=str(destination),
                    error_message="대상 파일이 이미 존재합니다 (안전 모드)",
                    operation_type="move"
                )
            
            # 파일 이동
            shutil.move(str(source), str(destination))
            
            self.logger.info(f"파일 이동 완료: {source.name} -> {destination}")
            
            return FileOperationResult(
                success=True,
                source_path=str(source),
                destination_path=str(destination),
                operation_type="move"
            )
            
        except Exception as e:
            self.logger.error(f"파일 이동 실패: {e}")
            return FileOperationResult(
                success=False,
                source_path=str(source),
                destination_path=str(destination),
                error_message=str(e),
                operation_type="move"
            )
    
    def rename_file(self, old_path: str, new_name: str) -> FileOperationResult:
        """파일 이름 변경"""
        try:
            old_file = Path(old_path)
            if not old_file.exists():
                return FileOperationResult(
                    success=False,
                    source_path=old_path,
                    error_message="파일이 존재하지 않습니다",
                    operation_type="rename"
                )
            
            # 새 경로 생성
            new_path = old_file.parent / new_name
            
            # 안전 모드: 기존 파일 확인
            if self.safe_mode and new_path.exists():
                return FileOperationResult(
                    success=False,
                    source_path=old_path,
                    destination_path=str(new_path),
                    error_message="대상 파일명이 이미 존재합니다 (안전 모드)",
                    operation_type="rename"
                )
            
            # 파일 이름 변경
            old_file.rename(new_path)
            
            self.logger.info(f"파일 이름 변경 완료: {old_file.name} -> {new_name}")
            
            return FileOperationResult(
                success=True,
                source_path=old_path,
                destination_path=str(new_path),
                operation_type="rename"
            )
            
        except Exception as e:
            self.logger.error(f"파일 이름 변경 실패: {e}")
            return FileOperationResult(
                success=False,
                source_path=old_path,
                error_message=str(e),
                operation_type="rename"
            )
    
    def delete_file(self, file_path: str) -> FileOperationResult:
        """파일 삭제"""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return FileOperationResult(
                    success=False,
                    source_path=file_path,
                    error_message="파일이 존재하지 않습니다",
                    operation_type="delete"
                )
            
            # 안전 모드: 휴지통으로 이동
            if self.safe_mode:
                # Windows의 경우 휴지통 사용
                try:
                    import send2trash
                    send2trash.send2trash(file_path)
                    operation_type = "trash"
                except ImportError:
                    # send2trash가 없는 경우 일반 삭제
                    file_path_obj.unlink()
                    operation_type = "delete"
            else:
                file_path_obj.unlink()
                operation_type = "delete"
            
            self.logger.info(f"파일 삭제 완료: {file_path}")
            
            return FileOperationResult(
                success=True,
                source_path=file_path,
                operation_type=operation_type
            )
            
        except Exception as e:
            self.logger.error(f"파일 삭제 실패: {e}")
            return FileOperationResult(
                success=False,
                source_path=file_path,
                error_message=str(e),
                operation_type="delete"
            )
    
    def get_file_info(self, file_path: str) -> Dict[str, any]:
        """파일 정보 조회"""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {"error": "파일이 존재하지 않습니다"}
            
            stat = file_path_obj.stat()
            
            return {
                "name": file_path_obj.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "is_file": file_path_obj.is_file(),
                "is_dir": file_path_obj.is_dir(),
                "extension": file_path_obj.suffix,
                "parent": str(file_path_obj.parent)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def validate_destination(self, path: str) -> Dict[str, any]:
        """대상 경로 유효성 검사"""
        try:
            dest_path = Path(path)
            
            # 존재 여부 확인
            exists = dest_path.exists()
            
            # 쓰기 권한 확인
            writable = False
            if exists:
                writable = os.access(dest_path, os.W_OK)
            else:
                # 부모 디렉토리 쓰기 권한 확인
                parent = dest_path.parent
                if parent.exists():
                    writable = os.access(parent, os.W_OK)
            
            return {
                "path": str(dest_path),
                "exists": exists,
                "writable": writable,
                "is_dir": dest_path.is_dir() if exists else False,
                "parent_exists": dest_path.parent.exists(),
                "parent_writable": os.access(dest_path.parent, os.W_OK) if dest_path.parent.exists() else False
            }
            
        except Exception as e:
            return {"error": str(e)}
