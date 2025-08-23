"""
스테이징 매니저

파일 작업을 안전하게 수행하기 위한 스테이징 디렉토리 시스템
Phase 3 요구사항: 모든 파일 조작 전 스테이징 디렉토리에서 준비
"""

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


@dataclass
class StagingConfiguration:
    """스테이징 시스템 설정"""

    # 기본 설정
    staging_directory: Path = field(default_factory=lambda: Path(".animesorter_staging"))
    temp_directory: Path = field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "animesorter_temp"
    )

    # 정리 설정
    auto_cleanup: bool = True
    cleanup_interval_hours: int = 24
    max_staging_age_hours: int = 72
    max_staging_size_mb: int = 1000

    # 보안 설정
    preserve_original_permissions: bool = True
    validate_file_integrity: bool = True
    create_backup_before_staging: bool = True

    # 성능 설정
    use_hard_links: bool = False  # Windows에서는 권장하지 않음
    batch_operations: bool = True
    max_concurrent_operations: int = 4


@dataclass
class StagedFile:
    """스테이징된 파일 정보"""

    staging_id: UUID
    original_path: Path
    staging_path: Path
    operation_type: str
    staged_at: datetime
    file_size: int
    checksum: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "staged"  # staged, processing, completed, failed, cleaned


class IStagingManager:
    """스테이징 매니저 인터페이스"""

    def stage_file(self, source_path: Path, operation_type: str) -> StagedFile:
        """파일을 스테이징 디렉토리에 준비"""
        raise NotImplementedError

    def stage_directory(self, source_path: Path, operation_type: str) -> StagedFile:
        """디렉토리를 스테이징 디렉토리에 준비"""
        raise NotImplementedError

    def get_staged_file(self, staging_id: UUID) -> StagedFile | None:
        """스테이징된 파일 정보 조회"""
        raise NotImplementedError

    def commit_staged_file(self, staging_id: UUID) -> bool:
        """스테이징된 파일 작업 완료"""
        raise NotImplementedError

    def rollback_staged_file(self, staging_id: UUID) -> bool:
        """스테이징된 파일 롤백"""
        raise NotImplementedError

    def cleanup_old_staging(self) -> int:
        """오래된 스테이징 파일 정리"""
        raise NotImplementedError

    def get_staging_summary(self) -> dict[str, Any]:
        """스테이징 상태 요약"""
        raise NotImplementedError

    def get_staging_directory(self) -> Path:
        """스테이징 디렉토리 경로 반환"""
        raise NotImplementedError


class StagingManager:
    """스테이징 매니저 구현"""

    def __init__(self, config: StagingConfiguration | None = None):
        self.config = config or StagingConfiguration()
        self.logger = logging.getLogger(self.__class__.__name__)

        # 스테이징된 파일들 관리
        self._staged_files: dict[UUID, StagedFile] = {}
        self._path_to_staging_id: dict[Path, UUID] = {}

        # 상태 관리
        self._is_initialized = False
        self._last_cleanup_time: datetime | None = None

        # 초기화
        self._initialize_directories()
        self._is_initialized = True

        self.logger.info("StagingManager 초기화 완료")

    def _initialize_directories(self) -> None:
        """필요한 디렉토리들 초기화"""
        try:
            # 스테이징 디렉토리 생성
            self.config.staging_directory.mkdir(parents=True, exist_ok=True)

            # 임시 디렉토리 생성
            self.config.temp_directory.mkdir(parents=True, exist_ok=True)

            # 하위 디렉토리들 생성
            for subdir in ["files", "directories", "backups", "processing"]:
                (self.config.staging_directory / subdir).mkdir(parents=True, exist_ok=True)

            self.logger.info(f"스테이징 디렉토리 초기화 완료: {self.config.staging_directory}")

        except Exception as e:
            self.logger.error(f"스테이징 디렉토리 초기화 실패: {e}")
            raise

    def stage_file(self, source_path: Path, operation_type: str) -> StagedFile:
        """파일을 스테이징 디렉토리에 준비"""
        try:
            if not source_path.exists():
                raise FileNotFoundError(f"소스 파일을 찾을 수 없습니다: {source_path}")

            if not source_path.is_file():
                raise ValueError(f"소스 경로가 파일이 아닙니다: {source_path}")

            # 스테이징 ID 생성
            staging_id = uuid4()

            # 스테이징 경로 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(staging_id)[:8]
            staging_name = f"{timestamp}_{unique_id}_{source_path.name}"
            staging_path = self.config.staging_directory / "files" / staging_name

            # 백업 생성 (설정에 따라)
            backup_path = None
            if self.config.create_backup_before_staging:
                backup_name = f"backup_{staging_name}"
                backup_path = self.config.staging_directory / "backups" / backup_name
                shutil.copy2(source_path, backup_path)
                self.logger.debug(f"백업 생성: {backup_path}")

            # 파일 스테이징
            if self.config.use_hard_links and hasattr(os, "link"):
                # 하드 링크 사용 (Unix/Linux)
                os.link(source_path, staging_path)
            else:
                # 파일 복사
                shutil.copy2(source_path, staging_path)

            # 파일 크기 및 체크섬 계산
            file_size = staging_path.stat().st_size
            checksum = (
                self._calculate_checksum(staging_path)
                if self.config.validate_file_integrity
                else None
            )

            # StagedFile 객체 생성
            staged_file = StagedFile(
                staging_id=staging_id,
                original_path=source_path,
                staging_path=staging_path,
                operation_type=operation_type,
                staged_at=datetime.now(),
                file_size=file_size,
                checksum=checksum,
                metadata={
                    "backup_path": str(backup_path) if backup_path else None,
                    "original_permissions": self._get_file_permissions(source_path),
                    "staging_method": "hard_link" if self.config.use_hard_links else "copy",
                },
            )

            # 관리 목록에 추가
            self._staged_files[staging_id] = staged_file
            self._path_to_staging_id[source_path] = staging_id

            self.logger.info(f"파일 스테이징 완료: {source_path} -> {staging_path}")
            return staged_file

        except Exception as e:
            self.logger.error(f"파일 스테이징 실패: {e}")
            raise

    def stage_directory(self, source_path: Path, operation_type: str) -> StagedFile:
        """디렉토리를 스테이징 디렉토리에 준비"""
        try:
            if not source_path.exists():
                raise FileNotFoundError(f"소스 디렉토리를 찾을 수 없습니다: {source_path}")

            if not source_path.is_dir():
                raise ValueError(f"소스 경로가 디렉토리가 아닙니다: {source_path}")

            # 스테이징 ID 생성
            staging_id = uuid4()

            # 스테이징 경로 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(staging_id)[:8]
            staging_name = f"{timestamp}_{unique_id}_{source_path.name}"
            staging_path = self.config.staging_directory / "directories" / staging_name

            # 백업 생성 (설정에 따라)
            backup_path = None
            if self.config.create_backup_before_staging:
                backup_name = f"backup_{staging_name}"
                backup_path = self.config.staging_directory / "backups" / backup_name
                shutil.copytree(source_path, backup_path)
                self.logger.debug(f"백업 생성: {backup_path}")

            # 디렉토리 스테이징 (복사)
            shutil.copytree(source_path, staging_path)

            # 디렉토리 크기 계산
            total_size = sum(f.stat().st_size for f in staging_path.rglob("*") if f.is_file())

            # StagedFile 객체 생성
            staged_file = StagedFile(
                staging_id=staging_id,
                original_path=source_path,
                staging_path=staging_path,
                operation_type=operation_type,
                staged_at=datetime.now(),
                file_size=total_size,
                checksum=None,  # 디렉토리 체크섬은 계산하지 않음
                metadata={
                    "backup_path": str(backup_path) if backup_path else None,
                    "file_count": len(list(staging_path.rglob("*"))),
                    "staging_method": "copy",
                },
            )

            # 관리 목록에 추가
            self._staged_files[staging_id] = staged_file
            self._path_to_staging_id[source_path] = staging_id

            self.logger.info(f"디렉토리 스테이징 완료: {source_path} -> {staging_path}")
            return staged_file

        except Exception as e:
            self.logger.error(f"디렉토리 스테이징 실패: {e}")
            raise

    def get_staged_file(self, staging_id: UUID) -> StagedFile | None:
        """스테이징된 파일 정보 조회"""
        return self._staged_files.get(staging_id)

    def get_staged_file_by_path(self, original_path: Path) -> StagedFile | None:
        """원본 경로로 스테이징된 파일 정보 조회"""
        staging_id = self._path_to_staging_id.get(original_path)
        if staging_id:
            return self._staged_files.get(staging_id)
        return None

    def commit_staged_file(self, staging_id: UUID) -> bool:
        """스테이징된 파일 작업 완료"""
        try:
            staged_file = self._staged_files.get(staging_id)
            if not staged_file:
                raise ValueError(f"스테이징 ID를 찾을 수 없습니다: {staging_id}")

            # 상태 업데이트
            staged_file.status = "completed"

            # 백업 파일 정리 (선택적)
            if staged_file.metadata.get("backup_path"):
                backup_path = Path(staged_file.metadata["backup_path"])
                if backup_path.exists():
                    backup_path.unlink()
                    self.logger.debug(f"백업 파일 정리: {backup_path}")

            self.logger.info(f"스테이징 파일 작업 완료: {staging_id}")
            return True

        except Exception as e:
            self.logger.error(f"스테이징 파일 작업 완료 실패: {e}")
            return False

    def rollback_staged_file(self, staging_id: UUID) -> bool:
        """스테이징된 파일 롤백"""
        try:
            staged_file = self._staged_files.get(staging_id)
            if not staged_file:
                raise ValueError(f"스테이징 ID를 찾을 수 없습니다: {staging_id}")

            # 백업에서 복원
            backup_path = staged_file.metadata.get("backup_path")
            if backup_path and Path(backup_path).exists():
                if staged_file.original_path.is_file():
                    shutil.copy2(Path(backup_path), staged_file.original_path)
                elif staged_file.original_path.is_dir():
                    if staged_file.original_path.exists():
                        shutil.rmtree(staged_file.original_path)
                    shutil.copytree(Path(backup_path), staged_file.original_path)

                self.logger.info(f"스테이징 파일 롤백 완료: {staging_id}")
                return True
            self.logger.warning(f"백업 파일을 찾을 수 없어 롤백할 수 없습니다: {staging_id}")
            return False

        except Exception as e:
            self.logger.error(f"스테이징 파일 롤백 실패: {e}")
            return False

    def cleanup_old_staging(self) -> int:
        """오래된 스테이징 파일 정리"""
        if not self.config.auto_cleanup:
            return 0

        try:
            cleaned_count = 0
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=self.config.max_staging_age_hours)

            staging_ids_to_remove = []

            for staging_id, staged_file in self._staged_files.items():
                # 완료된 파일들 중 오래된 것들 정리
                if staged_file.status == "completed" and staged_file.staged_at < cutoff_time:
                    # 스테이징 파일 삭제
                    if staged_file.staging_path.exists():
                        if staged_file.staging_path.is_file():
                            staged_file.staging_path.unlink()
                        elif staged_file.staging_path.is_dir():
                            shutil.rmtree(staged_file.staging_path)

                    # 백업 파일도 정리
                    backup_path = staged_file.metadata.get("backup_path")
                    if backup_path and Path(backup_path).exists():
                        Path(backup_path).unlink()

                    staging_ids_to_remove.append(staging_id)
                    cleaned_count += 1

            # 관리 목록에서 제거
            for staging_id in staging_ids_to_remove:
                staged_file = self._staged_files.pop(staging_id)
                self._path_to_staging_id.pop(staged_file.original_path, None)

            self._last_cleanup_time = current_time
            self.logger.info(f"오래된 스테이징 파일 {cleaned_count}개 정리 완료")

            return cleaned_count

        except Exception as e:
            self.logger.error(f"스테이징 파일 정리 실패: {e}")
            return 0

    def get_staging_summary(self) -> dict[str, Any]:
        """스테이징 상태 요약"""
        try:
            total_files = len(self._staged_files)
            status_counts: dict[str, int] = {}
            total_size = 0

            for staged_file in self._staged_files.values():
                status = staged_file.status
                status_counts[status] = status_counts.get(status, 0) + 1
                total_size += staged_file.file_size

            return {
                "total_staged_files": total_files,
                "status_distribution": status_counts,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "staging_directory": str(self.config.staging_directory),
                "last_cleanup": (
                    self._last_cleanup_time.isoformat() if self._last_cleanup_time else None
                ),
                "auto_cleanup_enabled": self.config.auto_cleanup,
            }

        except Exception as e:
            self.logger.error(f"스테이징 요약 생성 실패: {e}")
            return {}

    def _calculate_checksum(self, file_path: Path) -> str | None:
        """파일 체크섬 계산"""
        try:
            import hashlib

            hash_md5 = hashlib.md5()

            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)

            return hash_md5.hexdigest()

        except Exception as e:
            self.logger.warning(f"체크섬 계산 실패: {e}")
            return None

    def _get_file_permissions(self, file_path: Path) -> dict[str, Any]:
        """파일 권한 정보 조회"""
        try:
            stat_info = file_path.stat()
            return {
                "mode": stat_info.st_mode,
                "uid": stat_info.st_uid,
                "gid": stat_info.st_gid,
                "atime": stat_info.st_atime,
                "mtime": stat_info.st_mtime,
                "ctime": stat_info.st_ctime,
            }
        except Exception as e:
            self.logger.warning(f"파일 권한 정보 조회 실패: {e}")
            return {}

    def get_staging_directory(self) -> Path:
        """스테이징 디렉토리 반환"""
        return self.config.staging_directory

    def get_temp_directory(self) -> Path:
        """임시 디렉토리 반환"""
        return self.config.temp_directory

    def is_file_staged(self, file_path: Path) -> bool:
        """파일이 스테이징되었는지 확인"""
        return file_path in self._path_to_staging_id

    def get_staging_info(self, file_path: Path) -> StagedFile | None:
        """파일의 스테이징 정보 반환"""
        return self.get_staged_file_by_path(file_path)
