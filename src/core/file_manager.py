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
import json


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
    backup_path: Optional[str] = None  # 백업 파일 경로


class FileManager:
    """파일 관리자"""
    
    def __init__(self, destination_root: str = "", safe_mode: bool = True):
        """초기화"""
        self.destination_root = Path(destination_root) if destination_root else Path.cwd()
        self.safe_mode = safe_mode
        self.naming_scheme = "standard"  # standard, minimal, detailed
        self.logger = logging.getLogger(__name__)
        
        # 백업 시스템 설정
        self.backup_enabled = True
        self.backup_dir = self.destination_root / "_backup"
        self.backup_metadata_file = self.backup_dir / "backup_metadata.json"
        self.backup_metadata = {}

        # 세션 내 생성된 대상 경로 추적 (중복 파일명 자동 조정 시 사용)
        self._recent_destinations: set[Path] = set()
        
        # 지원되는 비디오 확장자
        self.video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.flv', '.webm'}
        
        # 지원되는 자막 확장자
        self.subtitle_extensions = {'.srt', '.ass', '.ssa', '.sub', '.idx', '.smi', '.vtt'}
        
        # 백업 디렉토리 초기화
        self._init_backup_system()

    def _get_non_conflicting_path(self, target_path: Path) -> Path:
        """기존 파일이 있을 경우 중복되지 않는 경로를 생성"""
        try:
            if not target_path.exists():
                return target_path
            base_stem = target_path.stem
            suffix = target_path.suffix
            index = 1
            while True:
                candidate = target_path.with_name(f"{base_stem} ({index}){suffix}")
                if not candidate.exists():
                    return candidate
                index += 1
        except Exception as e:
            self.logger.error(f"고유 경로 생성 실패: {e}")
            return target_path
    
    def _init_backup_system(self):
        """백업 시스템 초기화"""
        try:
            if self.backup_enabled:
                self.backup_dir.mkdir(exist_ok=True)
                self._load_backup_metadata()
                self.logger.info(f"백업 시스템 초기화 완료: {self.backup_dir}")
        except Exception as e:
            self.logger.error(f"백업 시스템 초기화 실패: {e}")
            self.backup_enabled = False
    
    def _load_backup_metadata(self):
        """백업 메타데이터 로드"""
        try:
            if self.backup_metadata_file.exists():
                with open(self.backup_metadata_file, 'r', encoding='utf-8') as f:
                    self.backup_metadata = json.load(f)
                self.logger.info(f"백업 메타데이터 로드 완료: {len(self.backup_metadata)}개 항목")
        except Exception as e:
            self.logger.error(f"백업 메타데이터 로드 실패: {e}")
            self.backup_metadata = {}
    
    def _save_backup_metadata(self):
        """백업 메타데이터 저장"""
        try:
            with open(self.backup_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.backup_metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"백업 메타데이터 저장 실패: {e}")
    
    def _create_backup(self, source_path: Path, operation_id: str) -> Optional[Path]:
        """파일 백업 생성"""
        if not self.backup_enabled or not self.safe_mode:
            return None
        
        try:
            # 백업 파일명 생성 (타임스탬프 포함)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{operation_id}_{timestamp}_{source_path.name}"
            backup_path = self.backup_dir / backup_filename
            
            # 파일 복사 (메타데이터 포함)
            shutil.copy2(source_path, backup_path)
            
            # 백업 메타데이터 기록 (원본 경로는 백업 시점의 경로로 저장)
            self.backup_metadata[operation_id] = {
                'original_source_path': str(source_path),
                'backup_path': str(backup_path),
                'timestamp': timestamp,
                'file_size': source_path.stat().st_size,
                'operation_type': 'backup',
                'status': 'created'  # 백업 상태 추가
            }
            self._save_backup_metadata()
            
            self.logger.info(f"백업 생성 완료: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"백업 생성 실패: {e}")
            return None
    
    def _restore_from_backup(self, operation_id: str) -> bool:
        """백업에서 파일 복원"""
        try:
            if operation_id not in self.backup_metadata:
                self.logger.warning(f"백업 메타데이터를 찾을 수 없음: {operation_id}")
                return False
            
            backup_info = self.backup_metadata[operation_id]
            backup_path = Path(backup_info['backup_path'])
            
            if not backup_path.exists():
                self.logger.error(f"백업 파일이 존재하지 않음: {backup_path}")
                return False
            
            # 백업 파일을 원본 위치로 복원
            original_source_path = Path(backup_info['original_source_path'])
            
            # 원본 디렉토리가 존재하지 않으면 생성
            original_source_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 백업에서 원본 위치로 복원
            shutil.copy2(backup_path, original_source_path)
            
            # 백업 메타데이터에서 제거
            del self.backup_metadata[operation_id]
            self._save_backup_metadata()
            
            self.logger.info(f"백업에서 복원 완료: {original_source_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"백업 복원 실패: {e}")
            return False
    
    def rollback_operation(self, operation_id: str) -> bool:
        """작업 롤백"""
        try:
            if operation_id not in self.backup_metadata:
                self.logger.warning(f"롤백할 작업을 찾을 수 없음: {operation_id}")
                return False
            
            success = self._restore_from_backup(operation_id)
            if success:
                self.logger.info(f"작업 롤백 완료: {operation_id}")
            return success
            
        except Exception as e:
            self.logger.error(f"작업 롤백 실패: {e}")
            return False
    
    def get_backup_info(self) -> Dict:
        """백업 정보 조회"""
        return {
            'backup_enabled': self.backup_enabled,
            'backup_dir': str(self.backup_dir),
            'backup_count': len(self.backup_metadata),
            'backup_size': self._get_backup_size()
        }
    
    def _get_backup_size(self) -> int:
        """백업 디렉토리 크기 계산"""
        try:
            total_size = 0
            for file_path in self.backup_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception as e:
            self.logger.error(f"백업 크기 계산 실패: {e}")
            return 0
    
    def cleanup_backups(self, max_age_days: int = 7) -> int:
        """오래된 백업 정리"""
        try:
            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
            cleaned_count = 0
            
            for operation_id, backup_info in list(self.backup_metadata.items()):
                backup_path = Path(backup_info['backup_path'])
                if backup_path.exists():
                    file_time = backup_path.stat().st_mtime
                    if file_time < cutoff_time:
                        backup_path.unlink()
                        del self.backup_metadata[operation_id]
                        cleaned_count += 1
            
            self._save_backup_metadata()
            self.logger.info(f"백업 정리 완료: {cleaned_count}개 파일 삭제")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"백업 정리 실패: {e}")
            return 0
    
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
        operation_id = f"{operation}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        try:
            source_file = Path(source_path)
            if not source_file.exists():
                return FileOperationResult(
                    success=False,
                    source_path=source_path,
                    error_message="소스 파일이 존재하지 않습니다",
                    operation_type=operation
                )
            
            # 파일 크기는 이동/이름변경 전 미리 계산해 둔다
            source_file_size = source_file.stat().st_size
            
            # 백업 생성은 실제 이동 직전에 수행 (충돌로 실패하는 경우 백업이 남지 않도록)
            backup_path = None
            
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
            
            # 충돌 처리 정책
            if destination_path.exists():
                if destination_path in self._recent_destinations:
                    # 이번 세션에서 생성했던 경로와 충돌: 자동으로 비충돌 이름 생성
                    destination_path = self._get_non_conflicting_path(destination_path)
                elif self.safe_mode:
                    # 기존 파일과 충돌: 안전 모드에서는 실패로 처리
                    return FileOperationResult(
                        success=False,
                        source_path=source_path,
                        destination_path=str(destination_path),
                        error_message="대상 파일이 이미 존재합니다 (안전 모드)",
                        operation_type=operation
                    )
            
            # 파일 작업 수행
            if operation == "copy":
                result = self._copy_file(source_file, destination_path)
            elif operation == "move":
                if self.safe_mode:
                    backup_path = self._create_backup(source_file, operation_id)
                result = self._move_file(source_file, destination_path)
                # 이동 작업 성공 시 백업 메타데이터 업데이트
                if result.success and backup_path and operation_id in self.backup_metadata:
                    self.backup_metadata[operation_id]['final_destination_path'] = str(destination_path)
                    self.backup_metadata[operation_id]['status'] = 'completed'
                    self._save_backup_metadata()
            else:
                return FileOperationResult(
                    success=False,
                    source_path=source_path,
                    error_message=f"지원되지 않는 작업: {operation}",
                    operation_type=operation
                )

            # 작업 성공 시 이번 세션의 대상 경로로 기록
            if result.success:
                self._recent_destinations.add(destination_path)

            # 결과 정보 추가
            if result.success:
                result.destination_path = str(destination_path)
                result.file_size = source_file_size
                result.processing_time = (datetime.now() - start_time).total_seconds()
                result.backup_path = str(backup_path) if backup_path else None
            else:
                # 작업 실패 시 백업에서 복원
                if backup_path and operation == "move":
                    self._restore_from_backup(operation_id)
                    self.logger.info(f"작업 실패로 인한 백업 복원 완료: {operation_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"파일 정리 실패: {e}")
            # 예외 발생 시 백업에서 복원
            if backup_path and operation == "move":
                self._restore_from_backup(operation_id)
                self.logger.info(f"예외 발생으로 인한 백업 복원 완료: {operation_id}")
            
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
            
            # 파일 이동 (백업은 이미 organize_file에서 생성됨)
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
