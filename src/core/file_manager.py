"""
파일 관리 모듈 - AnimeSorter

파일 정리, 이동, 복사 등의 작업을 관리하는 기능을 제공합니다.
"""

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .file_backup import FileBackupManager
from .file_handler import FileHandler
from .file_naming import FileNamingManager
from .file_validation import FileValidator
from .types import FileOperationResult


class FileManager:
    """파일 관리자"""

    def __init__(self, destination_root: str = "", safe_mode: bool = True):
        """초기화"""
        self.destination_root = Path(destination_root) if destination_root else Path.cwd()
        self.safe_mode = safe_mode
        self.logger = logging.getLogger(__name__)

        # 분할된 모듈들 초기화
        self.file_handler = FileHandler(safe_mode)
        self.file_backup_manager = FileBackupManager(self.destination_root / "_backup", safe_mode)
        self.file_naming_manager = FileNamingManager("standard")
        self.file_validator = FileValidator()

        # 세션 내 생성된 대상 경로 추적 (중복 파일명 자동 조정 시 사용)
        self._recent_destinations: set[Path] = set()

        self.logger.info(f"FileManager 초기화 완료: {self.destination_root}")

    def set_destination_root(self, path: str) -> bool:
        """대상 루트 디렉토리 설정"""
        try:
            new_path = Path(path)
            if new_path.exists() and new_path.is_dir():
                self.destination_root = new_path
                # 백업 디렉토리도 업데이트
                self.file_backup_manager.backup_dir = self.destination_root / "_backup"
                return True
            self.logger.warning(f"대상 디렉토리가 존재하지 않거나 디렉토리가 아닙니다: {path}")
            return False
        except Exception as e:
            self.logger.error(f"대상 디렉토리 설정 실패: {e}")
            return False

    def set_safe_mode(self, enabled: bool) -> None:
        """안전 모드 설정"""
        self.safe_mode = enabled
        self.file_handler.set_safe_mode(enabled)
        self.file_backup_manager.safe_mode = enabled
        self.logger.info(f"안전 모드: {'활성화' if enabled else '비활성화'}")

    def set_naming_scheme(self, scheme: str) -> None:
        """파일명 지정 방식 설정"""
        if self.file_naming_manager.set_naming_scheme(scheme):
            self.logger.info(f"파일명 지정 방식: {scheme}")

    def organize_file(
        self,
        source_path: str,
        metadata: dict,
        destination_root: str = None,
        operation: str = "copy",
    ) -> FileOperationResult:
        """단일 파일 정리"""
        start_time = datetime.now()
        operation_id = f"{operation}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # destination_root 복원을 위해 미리 저장
        original_destination_root = self.destination_root

        try:
            source_file = Path(source_path)
            if not source_file.exists():
                return FileOperationResult(
                    success=False,
                    source_path=source_path,
                    error_message="소스 파일이 존재하지 않습니다",
                    operation_type=operation,
                )

            # destination_root가 제공된 경우 임시로 설정
            if destination_root:
                self.destination_root = Path(destination_root)

            # 파일 크기는 이동/이름변경 전 미리 계산해 둔다
            source_file_size = source_file.stat().st_size

            # 백업 생성은 실제 이동 직전에 수행 (충돌로 실패하는 경우 백업이 남지 않도록)
            backup_path = None

            # 대상 경로 생성
            destination_path = self.file_naming_manager.generate_destination_path(
                source_file, metadata, self.destination_root
            )
            if not destination_path:
                return FileOperationResult(
                    success=False,
                    source_path=source_path,
                    error_message="대상 경로 생성 실패",
                    operation_type=operation,
                )

            # 대상 디렉토리 생성
            destination_dir = destination_path.parent
            destination_dir.mkdir(parents=True, exist_ok=True)

            # 충돌 처리 정책
            if destination_path.exists():
                if destination_path in self._recent_destinations:
                    # 이번 세션에서 생성했던 경로와 충돌: 자동으로 비충돌 이름 생성
                    destination_path = self.file_handler.get_non_conflicting_path(destination_path)
                elif self.safe_mode:
                    # 기존 파일과 충돌: 안전 모드에서는 실패로 처리
                    return FileOperationResult(
                        success=False,
                        source_path=source_path,
                        destination_path=str(destination_path),
                        error_message="대상 파일이 이미 존재합니다 (안전 모드)",
                        operation_type=operation,
                    )

            # 파일 작업 수행
            if operation == "copy":
                result = self.file_handler.copy_file(source_file, destination_path)
            elif operation == "move":
                if self.safe_mode:
                    backup_path = self.file_backup_manager.create_backup(source_file, operation_id)
                result = self.file_handler.move_file(source_file, destination_path)
                # 이동 작업 성공 시 백업 메타데이터 업데이트
                if (
                    result.success
                    and backup_path
                    and operation_id in self.file_backup_manager.backup_metadata
                ):
                    self.file_backup_manager.update_backup_metadata(
                        operation_id,
                        final_destination_path=str(destination_path),
                        status="completed",
                    )
            else:
                return FileOperationResult(
                    success=False,
                    source_path=source_path,
                    error_message=f"지원되지 않는 작업: {operation}",
                    operation_type=operation,
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
                    self.file_backup_manager.restore_from_backup(operation_id)
                    self.logger.info(f"작업 실패로 인한 백업 복원 완료: {operation_id}")

            return result

        except Exception as e:
            self.logger.error(f"파일 정리 실패: {e}")
            # 예외 발생 시 백업에서 복원
            if backup_path and operation == "move":
                self.file_backup_manager.restore_from_backup(operation_id)
                self.logger.info(f"예외 발생으로 인한 백업 복원 완료: {operation_id}")

            return FileOperationResult(
                success=False,
                source_path=source_path,
                error_message=str(e),
                operation_type=operation,
            )
        finally:
            # destination_root 복원
            if destination_root:
                self.destination_root = original_destination_root

    def batch_organize(
        self,
        file_operations: list[tuple[str, dict, str]],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[FileOperationResult]:
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

    def rename_file(self, old_path: str, new_name: str) -> FileOperationResult:
        """파일 이름 변경"""
        return self.file_handler.rename_file(Path(old_path), new_name)

    def delete_file(self, file_path: str) -> FileOperationResult:
        """파일 삭제"""
        return self.file_handler.delete_file(Path(file_path))

    def get_file_info(self, file_path: str) -> dict[str, any]:
        """파일 정보 조회"""
        return self.file_handler.get_file_info(Path(file_path))

    def validate_destination(self, path: str) -> dict[str, any]:
        """대상 경로 유효성 검사"""
        return self.file_validator.validate_destination(path)

    def get_stats(self) -> dict[str, any]:
        """통계 정보 조회 (테스트 호환성)"""
        return {
            "recent_destinations_count": len(self._recent_destinations),
            "backup_count": len(self.file_backup_manager.backup_metadata),
            "safe_mode": self.safe_mode,
            "naming_scheme": self.file_naming_manager.naming_scheme,
            "destination_root": str(self.destination_root),
            "backup_enabled": self.file_backup_manager.backup_enabled,
        }

    def get_backup_info(self) -> dict:
        """백업 정보 조회"""
        return self.file_backup_manager.get_backup_info()

    def rollback_operation(self, operation_id: str) -> bool:
        """작업 롤백"""
        return self.file_backup_manager.rollback_operation(operation_id)

    def cleanup_backups(self, max_age_days: int = 7) -> int:
        """오래된 백업 정리"""
        return self.file_backup_manager.cleanup_backups(max_age_days)

    def get_naming_scheme_info(self) -> dict:
        """파일명 지정 방식 정보 조회"""
        return self.file_naming_manager.get_naming_scheme_info()

    def get_supported_extensions(self) -> dict:
        """지원되는 파일 확장자 조회"""
        return self.file_validator.get_supported_extensions()

    def add_supported_extension(self, category: str, extension: str) -> bool:
        """지원되는 확장자 추가"""
        return self.file_validator.add_supported_extension(category, extension)

    def remove_supported_extension(self, category: str, extension: str) -> bool:
        """지원되는 확장자 제거"""
        return self.file_validator.remove_supported_extension(category, extension)

    def check_disk_space(self, path: str, required_bytes: int = 0) -> dict:
        """디스크 공간 확인"""
        return self.file_validator.check_disk_space(path, required_bytes)

    def validate_file_list(self, file_paths: list[str]) -> dict:
        """파일 목록 일괄 검증"""
        return self.file_validator.validate_file_list(file_paths)
