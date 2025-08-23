"""
파일 처리 모듈

파일 복사, 이동, 이름 변경, 삭제 등의 기본 작업을 담당합니다.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from .types import FileOperationResult


class FileHandler:
    """파일 처리 작업을 담당하는 클래스"""

    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode
        self.logger = logging.getLogger(self.__class__.__name__)

    def copy_file(self, source: Path, destination: Path) -> FileOperationResult:
        """파일 복사"""
        try:
            # 안전 모드: 기존 파일 확인
            if self.safe_mode and destination.exists():
                return FileOperationResult(
                    success=False,
                    source_path=str(source),
                    destination_path=str(destination),
                    error_message="대상 파일이 이미 존재합니다 (안전 모드)",
                    operation_type="copy",
                )

            # 대상 디렉토리 생성
            destination.parent.mkdir(parents=True, exist_ok=True)

            # 파일 복사
            shutil.copy2(source, destination)

            self.logger.info(f"파일 복사 완료: {source.name} -> {destination}")

            return FileOperationResult(
                success=True,
                source_path=str(source),
                destination_path=str(destination),
                operation_type="copy",
            )

        except Exception as e:
            self.logger.error(f"파일 복사 실패: {e}")
            return FileOperationResult(
                success=False,
                source_path=str(source),
                destination_path=str(destination),
                error_message=str(e),
                operation_type="copy",
            )

    def move_file(self, source: Path, destination: Path) -> FileOperationResult:
        """파일 이동"""
        try:
            # 안전 모드: 기존 파일 확인
            if self.safe_mode and destination.exists():
                return FileOperationResult(
                    success=False,
                    source_path=str(source),
                    destination_path=str(destination),
                    error_message="대상 파일이 이미 존재합니다 (안전 모드)",
                    operation_type="move",
                )

            # 대상 디렉토리 생성
            destination.parent.mkdir(parents=True, exist_ok=True)

            # 파일 이동
            shutil.move(str(source), str(destination))

            self.logger.info(f"파일 이동 완료: {source.name} -> {destination}")

            return FileOperationResult(
                success=True,
                source_path=str(source),
                destination_path=str(destination),
                operation_type="move",
            )

        except Exception as e:
            self.logger.error(f"파일 이동 실패: {e}")
            return FileOperationResult(
                success=False,
                source_path=str(source),
                destination_path=str(destination),
                error_message=str(e),
                operation_type="move",
            )

    def rename_file(self, old_path: Path, new_name: str) -> FileOperationResult:
        """파일 이름 변경"""
        try:
            if not old_path.exists():
                return FileOperationResult(
                    success=False,
                    source_path=str(old_path),
                    error_message="파일이 존재하지 않습니다",
                    operation_type="rename",
                )

            # 새 경로 생성
            new_path = old_path.parent / new_name

            # 안전 모드: 기존 파일 확인
            if self.safe_mode and new_path.exists():
                return FileOperationResult(
                    success=False,
                    source_path=str(old_path),
                    destination_path=str(new_path),
                    error_message="대상 파일명이 이미 존재합니다 (안전 모드)",
                    operation_type="rename",
                )

            # 파일 이름 변경
            old_path.rename(new_path)

            self.logger.info(f"파일 이름 변경 완료: {old_path.name} -> {new_name}")

            return FileOperationResult(
                success=True,
                source_path=str(old_path),
                destination_path=str(new_path),
                operation_type="rename",
            )

        except Exception as e:
            self.logger.error(f"파일 이름 변경 실패: {e}")
            return FileOperationResult(
                success=False,
                source_path=str(old_path),
                error_message=str(e),
                operation_type="rename",
            )

    def delete_file(self, file_path: Path) -> FileOperationResult:
        """파일 삭제"""
        try:
            if not file_path.exists():
                return FileOperationResult(
                    success=False,
                    source_path=str(file_path),
                    error_message="파일이 존재하지 않습니다",
                    operation_type="delete",
                )

            # 안전 모드: 휴지통으로 이동
            if self.safe_mode:
                # Windows의 경우 휴지통 사용
                try:
                    import send2trash

                    send2trash.send2trash(str(file_path))
                    operation_type = "trash"
                except ImportError:
                    # send2trash가 없는 경우 일반 삭제
                    file_path.unlink()
                    operation_type = "delete"
            else:
                file_path.unlink()
                operation_type = "delete"

            self.logger.info(f"파일 삭제 완료: {file_path}")

            return FileOperationResult(
                success=True, source_path=str(file_path), operation_type=operation_type
            )

        except Exception as e:
            self.logger.error(f"파일 삭제 실패: {e}")
            return FileOperationResult(
                success=False,
                source_path=str(file_path),
                error_message=str(e),
                operation_type="delete",
            )

    def get_non_conflicting_path(self, target_path: Path) -> Path:
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

    def get_file_info(self, file_path: Path) -> dict:
        """파일 정보 조회"""
        try:
            if not file_path.exists():
                return {"error": "파일이 존재하지 않습니다"}

            stat = file_path.stat()

            return {
                "name": file_path.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "is_file": file_path.is_file(),
                "is_dir": file_path.is_dir(),
                "extension": file_path.suffix,
                "parent": str(file_path.parent),
            }

        except Exception as e:
            return {"error": str(e)}

    def set_safe_mode(self, enabled: bool) -> None:
        """안전 모드 설정"""
        self.safe_mode = enabled
        self.logger.info(f"안전 모드: {'활성화' if enabled else '비활성화'}")
