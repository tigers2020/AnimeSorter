"""
파일 백업 관리 모듈

파일 백업 생성, 복원, 정리 등의 기능을 담당합니다.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


class FileBackupManager:
    """파일 백업을 관리하는 클래스"""

    def __init__(self, backup_dir: Path, safe_mode: bool = True):
        self.backup_dir = backup_dir
        self.safe_mode = safe_mode
        self.backup_enabled = True
        self.backup_metadata_file = backup_dir / "backup_metadata.json"
        self.backup_metadata: dict[str, Any] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # 백업 시스템 초기화
        self._init_backup_system()

    def _init_backup_system(self) -> None:
        """백업 시스템 초기화"""
        try:
            if self.backup_enabled:
                self.backup_dir.mkdir(exist_ok=True)
                self._load_backup_metadata()
                self.logger.info(f"백업 시스템 초기화 완료: {self.backup_dir}")
        except Exception as e:
            self.logger.error(f"백업 시스템 초기화 실패: {e}")
            self.backup_enabled = False

    def _load_backup_metadata(self) -> None:
        """백업 메타데이터 로드"""
        try:
            if self.backup_metadata_file.exists():
                with self.backup_metadata_file.open(encoding="utf-8") as f:
                    self.backup_metadata = json.load(f)
                self.logger.info(f"백업 메타데이터 로드 완료: {len(self.backup_metadata)}개 항목")
        except Exception as e:
            self.logger.error(f"백업 메타데이터 로드 실패: {e}")
            self.backup_metadata = {}

    def _save_backup_metadata(self) -> None:
        """백업 메타데이터 저장"""
        try:
            with self.backup_metadata_file.open("w", encoding="utf-8") as f:
                json.dump(self.backup_metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"백업 메타데이터 저장 실패: {e}")

    def create_backup(self, source_path: Path, operation_id: str) -> Path | None:
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

            # 백업 메타데이터 기록
            self.backup_metadata[operation_id] = {
                "original_source_path": str(source_path),
                "backup_path": str(backup_path),
                "timestamp": timestamp,
                "file_size": source_path.stat().st_size,
                "operation_type": "backup",
                "status": "created",
            }
            self._save_backup_metadata()

            self.logger.info(f"백업 생성 완료: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.error(f"백업 생성 실패: {e}")
            return None

    def restore_from_backup(self, operation_id: str) -> bool:
        """백업에서 파일 복원"""
        try:
            if operation_id not in self.backup_metadata:
                self.logger.warning(f"백업 메타데이터를 찾을 수 없음: {operation_id}")
                return False

            backup_info = self.backup_metadata[operation_id]
            backup_path = Path(backup_info["backup_path"])

            if not backup_path.exists():
                self.logger.error(f"백업 파일이 존재하지 않음: {backup_path}")
                return False

            # 백업 파일을 원본 위치로 복원
            original_source_path = Path(backup_info["original_source_path"])

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

            success = self.restore_from_backup(operation_id)
            if success:
                self.logger.info(f"작업 롤백 완료: {operation_id}")
            return success

        except Exception as e:
            self.logger.error(f"작업 롤백 실패: {e}")
            return False

    def get_backup_info(self) -> dict[str, Any]:
        """백업 정보 조회"""
        return {
            "backup_enabled": self.backup_enabled,
            "backup_dir": str(self.backup_dir),
            "backup_count": len(self.backup_metadata),
            "backup_size": self._get_backup_size(),
        }

    def _get_backup_size(self) -> int:
        """백업 디렉토리 크기 계산"""
        try:
            total_size = 0
            for file_path in self.backup_dir.rglob("*"):
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
                backup_path = Path(backup_info["backup_path"])
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

    def update_backup_metadata(self, operation_id: str, **kwargs: Any) -> None:
        """백업 메타데이터 업데이트"""
        try:
            if operation_id in self.backup_metadata:
                self.backup_metadata[operation_id].update(kwargs)
                self._save_backup_metadata()
                self.logger.debug(f"백업 메타데이터 업데이트 완료: {operation_id}")
        except Exception as e:
            self.logger.error(f"백업 메타데이터 업데이트 실패: {e}")

    def set_backup_enabled(self, enabled: bool) -> None:
        """백업 활성화/비활성화 설정"""
        self.backup_enabled = enabled
        self.logger.info(f"백업 시스템: {'활성화' if enabled else '비활성화'}")

    def get_backup_metadata(self) -> dict[str, Any]:
        """백업 메타데이터 반환"""
        return self.backup_metadata.copy()
