"""
파일 관리 모듈 - AnimeSorter의 파일 정리 기능

이 모듈은 파싱된 메타데이터를 기반으로 애니메이션 파일을
체계적으로 정리하고 구성하는 기능을 제공합니다.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal


@dataclass
class FileOperationResult:
    """파일 작업 결과"""
    success: bool
    source_path: str
    destination_path: str
    message: str
    error: Optional[str] = None


class FileManager(QObject):
    """파일 정리 관리자"""
    
    # PyQt5 시그널
    progress_updated = pyqtSignal(int, str)  # 진행률, 메시지
    operation_started = pyqtSignal(str)      # 작업 시작 메시지
    operation_completed = pyqtSignal(str)    # 작업 완료 메시지
    error_occurred = pyqtSignal(str)        # 에러 메시지
    
    def __init__(self, destination_root: str = "", safe_mode: bool = True):
        """
        FileManager 초기화
        
        Args:
            destination_root: 기본 대상 디렉토리 경로
            safe_mode: 안전 모드 (True: 복사, False: 이동)
        """
        super().__init__()
        self.destination_root = Path(destination_root) if destination_root else None
        self.safe_mode = safe_mode
        self.naming_scheme = "standard"  # 'standard', 'minimal', 'detailed'
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        
        # 작업 통계
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'errors': []
        }
    
    def set_destination_root(self, path: str) -> None:
        """대상 디렉토리 루트 설정"""
        self.destination_root = Path(path)
        self.logger.info(f"대상 디렉토리 설정: {path}")
    
    def set_naming_scheme(self, scheme: str) -> None:
        """파일 이름 지정 방식 설정"""
        valid_schemes = ['standard', 'minimal', 'detailed']
        if scheme in valid_schemes:
            self.naming_scheme = scheme
            self.logger.info(f"이름 지정 방식 설정: {scheme}")
        else:
            self.logger.warning(f"잘못된 이름 지정 방식: {scheme}")
    
    def set_safe_mode(self, enabled: bool) -> None:
        """안전 모드 설정 (True: 복사, False: 이동)"""
        self.safe_mode = enabled
        mode = "복사" if enabled else "이동"
        self.logger.info(f"안전 모드 설정: {mode}")
    
    def organize_file(self, source_path: str, metadata: Dict[str, Any], 
                     destination_dir: Optional[str] = None) -> FileOperationResult:
        """
        파일 정리 실행
        
        Args:
            source_path: 소스 파일 경로
            metadata: 파싱된 메타데이터
            destination_dir: 대상 디렉토리 (None이면 기본값 사용)
        
        Returns:
            FileOperationResult: 작업 결과
        """
        try:
            source_path = Path(source_path)
            if not source_path.exists():
                return FileOperationResult(
                    success=False,
                    source_path=str(source_path),
                    destination_path="",
                    message="소스 파일이 존재하지 않습니다",
                    error="FileNotFoundError"
                )
            
            # 대상 디렉토리 결정
            if destination_dir:
                dest_root = Path(destination_dir)
            elif self.destination_root:
                dest_root = self.destination_root
            else:
                return FileOperationResult(
                    success=False,
                    source_path=str(source_path),
                    destination_path="",
                    message="대상 디렉토리가 설정되지 않았습니다",
                    error="DestinationNotSetError"
                )
            
            # 진행 상황 업데이트
            self.operation_started.emit(f"파일 정리 시작: {source_path.name}")
            
            # 1. 디렉토리 구조 생성
            dest_dir = self._create_directory_structure(dest_root, metadata)
            if not dest_dir:
                return FileOperationResult(
                    success=False,
                    source_path=str(source_path),
                    destination_path="",
                    message="대상 디렉토리 생성에 실패했습니다",
                    error="DirectoryCreationError"
                )
            
            # 2. 새 파일명 생성
            new_filename = self._generate_filename(metadata, source_path.suffix)
            if not new_filename:
                return FileOperationResult(
                    success=False,
                    source_path=str(source_path),
                    destination_path="",
                    message="파일명 생성에 실패했습니다",
                    error="FilenameGenerationError"
                )
            
            # 3. 대상 경로 생성
            dest_path = dest_dir / new_filename
            
            # 4. 파일 이름 충돌 처리
            dest_path = self._handle_filename_conflict(dest_path)
            
            # 5. 파일 이동/복사
            if self.safe_mode:
                result = self._copy_file(source_path, dest_path)
            else:
                result = self._move_file(source_path, dest_path)
            
            if result.success:
                self.stats['successful_operations'] += 1
                self.operation_completed.emit(f"파일 정리 완료: {new_filename}")
            else:
                self.stats['failed_operations'] += 1
                self.error_occurred.emit(f"파일 정리 실패: {result.error}")
            
            self.stats['processed_files'] += 1
            return result
            
        except Exception as e:
            error_msg = f"파일 정리 중 예상치 못한 오류: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.stats['failed_operations'] += 1
            self.stats['errors'].append(str(e))
            self.error_occurred.emit(error_msg)
            
            return FileOperationResult(
                success=False,
                source_path=str(source_path),
                destination_path="",
                message=error_msg,
                error=str(e)
            )
    
    def _create_directory_structure(self, dest_root: Path, metadata: Dict[str, Any]) -> Optional[Path]:
        """대상 디렉토리 구조 생성"""
        try:
            # 기본 구조: 제목/시즌
            title = metadata.get('title', 'Unknown')
            season = metadata.get('season', 1)
            
            # 디렉토리명 정리 (특수문자 제거)
            safe_title = self._sanitize_filename(title)
            season_dir = f"Season {season:02d}"
            
            # 전체 경로 생성
            full_path = dest_root / safe_title / season_dir
            
            # 디렉토리 생성
            full_path.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"디렉토리 생성: {full_path}")
            self.progress_updated.emit(25, f"디렉토리 생성: {season_dir}")
            
            return full_path
            
        except Exception as e:
            error_msg = f"디렉토리 생성 실패: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return None
    
    def _generate_filename(self, metadata: Dict[str, Any], extension: str) -> Optional[str]:
        """새 파일명 생성"""
        try:
            title = metadata.get('title', 'Unknown')
            season = metadata.get('season', 1)
            episode = metadata.get('episode', 1)
            year = metadata.get('year')
            resolution = metadata.get('resolution', '')
            group = metadata.get('group', '')
            
            # 제목 정리
            safe_title = self._sanitize_filename(title)
            
            # 이름 지정 방식에 따른 파일명 생성
            if self.naming_scheme == 'minimal':
                filename = f"{safe_title} - S{season:02d}E{episode:02d}{extension}"
            elif self.naming_scheme == 'detailed':
                parts = [safe_title, f"S{season:02d}E{episode:02d}"]
                if year:
                    parts.append(str(year))
                if resolution:
                    parts.append(resolution)
                if group:
                    parts.append(f"[{group}]")
                filename = " - ".join(parts) + extension
            else:  # standard
                filename = f"{safe_title} - S{season:02d}E{episode:02d} - {resolution}{extension}"
            
            self.logger.info(f"파일명 생성: {filename}")
            self.progress_updated.emit(50, f"파일명 생성: {filename}")
            
            return filename
            
        except Exception as e:
            error_msg = f"파일명 생성 실패: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return None
    
    def _handle_filename_conflict(self, dest_path: Path) -> Path:
        """파일명 충돌 처리"""
        if not dest_path.exists():
            return dest_path
        
        # 충돌 시 번호 추가
        counter = 1
        while dest_path.exists():
            stem = dest_path.stem
            suffix = dest_path.suffix
            new_name = f"{stem} ({counter}){suffix}"
            dest_path = dest_path.parent / new_name
            counter += 1
        
        if counter > 1:
            self.logger.info(f"파일명 충돌 해결: {dest_path.name}")
        
        return dest_path
    
    def _copy_file(self, source: Path, dest: Path) -> FileOperationResult:
        """파일 복사"""
        try:
            shutil.copy2(source, dest)
            
            result = FileOperationResult(
                success=True,
                source_path=str(source),
                destination_path=str(dest),
                message=f"파일 복사 완료: {dest.name}"
            )
            
            self.logger.info(f"파일 복사 완료: {source} -> {dest}")
            self.progress_updated.emit(100, f"파일 복사 완료: {dest.name}")
            
            return result
            
        except Exception as e:
            error_msg = f"파일 복사 실패: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return FileOperationResult(
                success=False,
                source_path=str(source),
                destination_path=str(dest),
                message=error_msg,
                error=str(e)
            )
    
    def _move_file(self, source: Path, dest: Path) -> FileOperationResult:
        """파일 이동"""
        try:
            shutil.move(source, dest)
            
            result = FileOperationResult(
                success=True,
                source_path=str(source),
                destination_path=str(dest),
                message=f"파일 이동 완료: {dest.name}"
            )
            
            self.logger.info(f"파일 이동 완료: {source} -> {dest}")
            self.progress_updated.emit(100, f"파일 이동 완료: {dest.name}")
            
            return result
            
        except Exception as e:
            error_msg = f"파일 이동 실패: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return FileOperationResult(
                success=False,
                source_path=str(source),
                destination_path=str(dest),
                message=error_msg,
                error=str(e)
            )
    
    def _sanitize_filename(self, filename: str) -> str:
        """파일명에서 사용할 수 없는 문자 제거"""
        # Windows에서 사용할 수 없는 문자
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        
        # 연속된 공백을 단일 공백으로 변경
        filename = ' '.join(filename.split())
        
        # 앞뒤 공백 제거
        filename = filename.strip()
        
        return filename
    
    def batch_organize(self, files: List[Dict[str, Any]]) -> List[FileOperationResult]:
        """여러 파일 일괄 정리"""
        results = []
        total_files = len(files)
        
        self.stats['total_files'] = total_files
        self.stats['processed_files'] = 0
        self.stats['successful_operations'] = 0
        self.stats['failed_operations'] = 0
        self.stats['errors'] = []
        
        for i, file_info in enumerate(files):
            source_path = file_info['source_path']
            metadata = file_info['metadata']
            
            # 진행률 업데이트
            progress = int((i / total_files) * 100)
            self.progress_updated.emit(progress, f"처리 중: {i+1}/{total_files}")
            
            # 파일 정리 실행
            result = self.organize_file(source_path, metadata)
            results.append(result)
        
        # 완료 메시지
        self.operation_completed.emit(f"일괄 정리 완료: {self.stats['successful_operations']}/{total_files} 성공")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """작업 통계 반환"""
        return self.stats.copy()
    
    def reset_stats(self) -> None:
        """통계 초기화"""
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'errors': []
        }
    
    def validate_destination(self, path: str) -> bool:
        """대상 디렉토리 유효성 검사"""
        try:
            dest_path = Path(path)
            
            # 경로가 존재하고 디렉토리인지 확인
            if not dest_path.exists():
                return False
            
            if not dest_path.is_dir():
                return False
            
            # 쓰기 권한 확인
            if not os.access(dest_path, os.W_OK):
                return False
            
            return True
            
        except Exception:
            return False
