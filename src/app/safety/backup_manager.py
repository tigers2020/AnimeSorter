"""
백업 시스템 매니저
"""

import hashlib
import logging
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

from src.app.events import get_event_bus
from src.app.safety_events import (BackupCleanupEvent, BackupCompletedEvent,
                                   BackupFailedEvent, BackupStartedEvent)


class BackupStrategy:
    """백업 전략"""

    COPY = "copy"  # 단순 복사
    ZIP = "zip"  # 압축 백업
    INCREMENTAL = "incremental"  # 증분 백업
    MIRROR = "mirror"  # 미러 백업


class BackupInfo:
    """백업 정보"""

    def __init__(self, backup_id: UUID, source_paths: list[Path], backup_location: Path):
        self.backup_id = backup_id
        self.source_paths = source_paths
        self.backup_location = backup_location
        self.created_at = datetime.now()
        self.backup_size_bytes = 0
        self.files_backed_up = 0
        self.backup_type = BackupStrategy.COPY
        self.metadata: dict[str, Any] = {}


class IBackupManager(Protocol):
    """백업 매니저 인터페이스"""

    def create_backup(
        self, source_paths: list[Path], strategy: str = BackupStrategy.COPY
    ) -> BackupInfo | None:
        """백업 생성"""
        ...

    def restore_backup(self, backup_id: UUID, target_location: Path) -> bool:
        """백업 복원"""
        ...

    def list_backups(self) -> list[BackupInfo]:
        """백업 목록 조회"""
        ...

    def cleanup_old_backups(self, max_age_days: int = 30, max_backups: int = 100) -> int:
        """오래된 백업 정리"""
        ...

    def get_backup_info(self, backup_id: UUID) -> BackupInfo | None:
        """백업 정보 조회"""
        ...


class BackupConfiguration:
    """백업 설정"""

    def __init__(self):
        self.backup_directory = Path.home() / ".animesorter" / "backups"
        self.max_backup_age_days = 30
        self.max_backup_count = 100
        self.default_strategy = BackupStrategy.COPY
        self.auto_backup_enabled = True
        self.backup_before_operations = True
        self.compression_level = 6
        self.verify_backups = True


class BackupManager:
    """백업 매니저"""

    def __init__(self, config: BackupConfiguration | None = None):
        self.config = config or BackupConfiguration()
        self.event_bus = get_event_bus()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 백업 디렉토리 생성
        self.config.backup_directory.mkdir(parents=True, exist_ok=True)

        # 백업 정보 저장소
        self._backups: dict[UUID, BackupInfo] = {}
        self._load_backup_index()

    def create_backup(
        self, source_paths: list[Path], strategy: str = BackupStrategy.COPY
    ) -> BackupInfo | None:
        """백업 생성"""
        if not source_paths:
            self.logger.warning("백업할 소스 경로가 없습니다")
            return None

        backup_id = uuid4()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}_{backup_id.hex[:8]}"
        backup_location = self.config.backup_directory / backup_name

        # 백업 시작 이벤트 발행
        self.event_bus.publish(
            BackupStartedEvent(
                backup_id=backup_id,
                source_paths=source_paths,
                backup_location=backup_location,
                backup_type="auto" if self.config.auto_backup_enabled else "manual",
            )
        )

        try:
            # 백업 전략에 따른 백업 실행
            if strategy == BackupStrategy.ZIP:
                success = self._create_zip_backup(source_paths, backup_location)
            elif strategy == BackupStrategy.INCREMENTAL:
                success = self._create_incremental_backup(source_paths, backup_location)
            elif strategy == BackupStrategy.MIRROR:
                success = self._create_mirror_backup(source_paths, backup_location)
            else:  # COPY
                success = self._create_copy_backup(source_paths, backup_location)

            if not success:
                raise RuntimeError(f"백업 전략 {strategy} 실행 실패")

            # 백업 정보 생성
            backup_info = BackupInfo(backup_id, source_paths, backup_location)
            backup_info.backup_type = strategy
            backup_info.backup_size_bytes = self._calculate_backup_size(backup_location)
            backup_info.files_backed_up = len(source_paths)
            backup_info.metadata = {
                "strategy": strategy,
                "compression_level": (
                    self.config.compression_level if strategy == BackupStrategy.ZIP else None
                ),
                "checksum": self._calculate_checksum(backup_location),
            }

            # 백업 정보 저장
            self._backups[backup_id] = backup_info
            self._save_backup_index()

            # 백업 완료 이벤트 발행
            self.event_bus.publish(
                BackupCompletedEvent(
                    backup_id=backup_id,
                    source_paths=source_paths,
                    backup_location=backup_location,
                    backup_size_bytes=backup_info.backup_size_bytes,
                    files_backed_up=backup_info.files_backed_up,
                    success=True,
                )
            )

            self.logger.info(f"백업 완료: {backup_id} -> {backup_location}")
            return backup_info

        except Exception as e:
            self.logger.error(f"백업 실패: {e}")

            # 백업 실패 이벤트 발행
            self.event_bus.publish(
                BackupFailedEvent(
                    backup_id=backup_id,
                    source_paths=source_paths,
                    backup_location=backup_location,
                    error_message=str(e),
                )
            )

            return None

    def _create_copy_backup(self, source_paths: list[Path], backup_location: Path) -> bool:
        """단순 복사 백업"""
        try:
            backup_location.mkdir(parents=True, exist_ok=True)

            for source_path in source_paths:
                if not source_path.exists():
                    continue

                if source_path.is_file():
                    # 파일 복사
                    dest_path = backup_location / source_path.name
                    shutil.copy2(source_path, dest_path)
                elif source_path.is_dir():
                    # 디렉토리 복사
                    dest_path = backup_location / source_path.name
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)

            return True

        except Exception as e:
            self.logger.error(f"복사 백업 실패: {e}")
            return False

    def _create_zip_backup(self, source_paths: list[Path], backup_location: Path) -> bool:
        """압축 백업"""
        try:
            backup_location = backup_location.with_suffix(".zip")

            with zipfile.ZipFile(
                backup_location,
                "w",
                zipfile.ZIP_DEFLATED,
                compresslevel=self.config.compression_level,
            ) as zipf:
                for source_path in source_paths:
                    if not source_path.exists():
                        continue

                    if source_path.is_file():
                        # 파일 압축
                        zipf.write(source_path, source_path.name)
                    elif source_path.is_dir():
                        # 디렉토리 압축
                        for file_path in source_path.rglob("*"):
                            if file_path.is_file():
                                arcname = file_path.relative_to(source_path)
                                zipf.write(file_path, arcname)

            return True

        except Exception as e:
            self.logger.error(f"압축 백업 실패: {e}")
            return False

    def _create_incremental_backup(self, source_paths: list[Path], backup_location: Path) -> bool:
        """증분 백업 (현재는 단순 복사로 구현)"""
        # TODO: 실제 증분 백업 로직 구현
        return self._create_copy_backup(source_paths, backup_location)

    def _create_mirror_backup(self, source_paths: list[Path], backup_location: Path) -> bool:
        """미러 백업"""
        try:
            # 기존 백업 삭제 후 새로 생성
            if backup_location.exists():
                shutil.rmtree(backup_location)

            return self._create_copy_backup(source_paths, backup_location)

        except Exception as e:
            self.logger.error(f"미러 백업 실패: {e}")
            return False

    def restore_backup(self, backup_id: UUID, target_location: Path) -> bool:
        """백업 복원"""
        backup_info = self.get_backup_info(backup_id)
        if not backup_info:
            self.logger.error(f"백업을 찾을 수 없습니다: {backup_id}")
            return False

        try:
            if backup_info.backup_type == BackupStrategy.ZIP:
                return self._restore_zip_backup(backup_info, target_location)
            return self._restore_copy_backup(backup_info, target_location)

        except Exception as e:
            self.logger.error(f"백업 복원 실패: {e}")
            return False

    def _restore_copy_backup(self, backup_info: BackupInfo, target_location: Path) -> bool:
        """복사 백업 복원"""
        try:
            if backup_info.backup_location.is_file():
                shutil.copy2(backup_info.backup_location, target_location)
            elif backup_info.backup_location.is_dir():
                shutil.copytree(backup_info.backup_location, target_location, dirs_exist_ok=True)

            return True

        except Exception as e:
            self.logger.error(f"복사 백업 복원 실패: {e}")
            return False

    def _restore_zip_backup(self, backup_info: BackupInfo, target_location: Path) -> bool:
        """압축 백업 복원"""
        try:
            with zipfile.ZipFile(backup_info.backup_location, "r") as zipf:
                zipf.extractall(target_location)

            return True

        except Exception as e:
            self.logger.error(f"압축 백업 복원 실패: {e}")
            return False

    def list_backups(self) -> list[BackupInfo]:
        """백업 목록 조회"""
        return list(self._backups.values())

    def cleanup_old_backups(self, max_age_days: int = None, max_backups: int = None) -> int:
        """오래된 백업 정리"""
        max_age_days = max_age_days or self.config.max_backup_age_days
        max_backups = max_backups or self.config.max_backup_count

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        cleaned_count = 0
        freed_space = 0

        # 나이 기반 정리
        for backup_id, backup_info in list(self._backups.items()):
            if backup_info.created_at < cutoff_date and self._remove_backup(backup_id):
                cleaned_count += 1
                freed_space += backup_info.backup_size_bytes

        # 개수 기반 정리
        if len(self._backups) > max_backups:
            # 오래된 순으로 정렬
            sorted_backups = sorted(self._backups.values(), key=lambda x: x.created_at)
            excess_count = len(self._backups) - max_backups

            for backup_info in sorted_backups[:excess_count]:
                if self._remove_backup(backup_info.backup_id):
                    cleaned_count += 1
                    freed_space += backup_info.backup_size_bytes

        if cleaned_count > 0:
            self.event_bus.publish(
                BackupCleanupEvent(
                    backup_ids=[],  # TODO: 실제 삭제된 백업 ID 목록
                    cleanup_type="auto",
                    freed_space_bytes=freed_space,
                )
            )

        return cleaned_count

    def _remove_backup(self, backup_id: UUID) -> bool:
        """백업 제거"""
        try:
            backup_info = self._backups.get(backup_id)
            if not backup_info:
                return False

            # 백업 파일/디렉토리 삭제
            if backup_info.backup_location.exists():
                if backup_info.backup_location.is_file():
                    backup_info.backup_location.unlink()
                else:
                    shutil.rmtree(backup_info.backup_location)

            # 백업 정보 제거
            del self._backups[backup_id]
            self._save_backup_index()

            return True

        except Exception as e:
            self.logger.error(f"백업 제거 실패: {e}")
            return False

    def get_backup_info(self, backup_id: UUID) -> BackupInfo | None:
        """백업 정보 조회"""
        return self._backups.get(backup_id)

    def _calculate_backup_size(self, backup_location: Path) -> int:
        """백업 크기 계산"""
        try:
            if backup_location.is_file():
                return backup_location.stat().st_size
            if backup_location.is_dir():
                total_size = 0
                for file_path in backup_location.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                return total_size
            return 0
        except Exception:
            return 0

    def _calculate_checksum(self, backup_location: Path) -> str:
        """백업 체크섬 계산"""
        try:
            if backup_location.is_file():
                return self._calculate_file_checksum(backup_location)
            if backup_location.is_dir():
                return self._calculate_directory_checksum(backup_location)
            return ""
        except Exception:
            return ""

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """파일 체크섬 계산"""
        hash_md5 = hashlib.md5()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _calculate_directory_checksum(self, dir_path: Path) -> str:
        """디렉토리 체크섬 계산"""
        hash_md5 = hashlib.md5()
        for file_path in sorted(dir_path.rglob("*")):
            if file_path.is_file():
                hash_md5.update(str(file_path.relative_to(dir_path)).encode())
                hash_md5.update(self._calculate_file_checksum(file_path).encode())
        return hash_md5.hexdigest()

    def _load_backup_index(self) -> None:
        """백업 인덱스 로드"""
        # TODO: 백업 인덱스 파일에서 백업 정보 로드

    def _save_backup_index(self) -> None:
        """백업 인덱스 저장"""
        # TODO: 백업 인덱스 파일에 백업 정보 저장
