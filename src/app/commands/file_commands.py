"""
파일 조작 Command 구현

안전한 파일 이동, 복사, 삭제, 이름변경 등의 Command들
"""

import shutil
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from .base_command import BaseCommand, CompositeCommand, ICommand

if TYPE_CHECKING:
    from ..journal import FileOperationDetails, JournalEntryType


class MoveFileCommand(BaseCommand):
    """파일 이동 Command"""

    def __init__(
        self,
        source: str | Path,
        destination: str | Path,
        create_dirs: bool = True,
        overwrite: bool = False,
    ):
        self.source = Path(source)
        self.destination = Path(destination)
        self.create_dirs = create_dirs
        self.overwrite = overwrite

        super().__init__(f"{self.source.name} → {self.destination}")

    def _get_default_description(self) -> str:
        return f"파일 이동: {self.source.name} → {self.destination}"

    def validate(self) -> bool:
        """이동 전 유효성 검사"""
        # 원본 파일 존재 확인
        if not self.source.exists():
            self.logger.error(f"원본 파일이 존재하지 않음: {self.source}")
            return False

        # 대상이 파일인 경우
        if self.destination.exists():
            if not self.overwrite:
                self.logger.error(f"대상 파일이 이미 존재함: {self.destination}")
                return False

            if self.destination.is_dir():
                self.logger.error(f"대상이 디렉토리임: {self.destination}")
                return False

        # 대상 디렉토리 생성 가능 여부
        if self.create_dirs and not self.destination.parent.exists():
            try:
                self.destination.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                self.logger.error(f"대상 디렉토리 생성 권한 없음: {self.destination.parent}")
                return False

        return True

    def _get_preflight_paths(self) -> tuple[Path, Path | None] | None:
        """프리플라이트 검사할 경로 반환"""
        return (self.source, self.destination)

    def _get_journal_info(self) -> tuple["JournalEntryType", "FileOperationDetails"] | None:
        """저널 정보 반환"""
        from ..journal import FileOperationDetails, JournalEntryType

        return (
            JournalEntryType.FILE_MOVE,
            FileOperationDetails(
                operation_type="file_move",
                source_path=self.source,
                destination_path=self.destination,
                overwrite=self.overwrite,
                create_dirs=self.create_dirs,
                file_size=self.source.stat().st_size if self.source.exists() else None,
                metadata={"create_dirs": self.create_dirs, "overwrite": self.overwrite},
            ),
        )

    def _execute_impl(self) -> None:
        """파일 이동 실행"""
        # 백업용 정보 저장
        self._store_undo_data("original_source", self.source)
        self._store_undo_data("original_destination", self.destination)

        # 기존 파일이 있으면 백업
        if self.destination.exists():
            backup_path = self.destination.with_suffix(f"{self.destination.suffix}.backup")
            shutil.move(str(self.destination), str(backup_path))
            self._store_undo_data("backup_path", backup_path)

        # 대상 디렉토리 생성
        if self.create_dirs:
            self.destination.parent.mkdir(parents=True, exist_ok=True)

        # 파일 이동
        shutil.move(str(self.source), str(self.destination))

        # 결과 기록
        self._add_affected_file(self.source)
        self._add_affected_file(self.destination)
        self._set_metadata("source_size", self.destination.stat().st_size)

    def _undo_impl(self) -> None:
        """파일 이동 취소"""
        original_source = self._get_undo_data("original_source")
        original_destination = self._get_undo_data("original_destination")
        backup_path = self._get_undo_data("backup_path")

        # 이동된 파일을 원래 위치로 복원
        if self.destination.exists():
            shutil.move(str(self.destination), str(original_source))

        # 백업된 파일이 있으면 복원
        if backup_path and backup_path.exists():
            shutil.move(str(backup_path), str(original_destination))


class CopyFileCommand(BaseCommand):
    """파일 복사 Command"""

    def __init__(
        self,
        source: str | Path,
        destination: str | Path,
        create_dirs: bool = True,
        overwrite: bool = False,
    ):
        self.source = Path(source)
        self.destination = Path(destination)
        self.create_dirs = create_dirs
        self.overwrite = overwrite

        super().__init__(f"{self.source.name} 복사 → {self.destination}")

    def _get_default_description(self) -> str:
        return f"파일 복사: {self.source.name} → {self.destination}"

    def validate(self) -> bool:
        """복사 전 유효성 검사"""
        if not self.source.exists():
            return False

        return not (self.destination.exists() and not self.overwrite)

    def _get_preflight_paths(self) -> tuple[Path, Path | None] | None:
        """프리플라이트 검사할 경로 반환"""
        return (self.source, self.destination)

    def _execute_impl(self) -> None:
        """파일 복사 실행"""
        # 기존 파일 백업
        if self.destination.exists():
            backup_path = self.destination.with_suffix(f"{self.destination.suffix}.backup")
            shutil.copy2(str(self.destination), str(backup_path))
            self._store_undo_data("backup_path", backup_path)

        # 대상 디렉토리 생성
        if self.create_dirs:
            self.destination.parent.mkdir(parents=True, exist_ok=True)

        # 파일 복사
        shutil.copy2(str(self.source), str(self.destination))

        # 결과 기록
        self._add_created_file(self.destination)
        self._set_metadata("source_size", self.source.stat().st_size)
        self._set_metadata("copied_size", self.destination.stat().st_size)

    def _undo_impl(self) -> None:
        """파일 복사 취소"""
        backup_path = self._get_undo_data("backup_path")

        # 복사된 파일 삭제
        if self.destination.exists():
            self.destination.unlink()

        # 백업 파일 복원
        if backup_path and backup_path.exists():
            shutil.move(str(backup_path), str(self.destination))


class DeleteFileCommand(BaseCommand):
    """파일 삭제 Command"""

    def __init__(self, file_path: str | Path, use_trash: bool = True):
        self.file_path = Path(file_path)
        self.use_trash = use_trash

        super().__init__(f"{self.file_path.name} 삭제")

    def _get_default_description(self) -> str:
        return f"파일 삭제: {self.file_path.name}"

    def validate(self) -> bool:
        """삭제 전 유효성 검사"""
        return self.file_path.exists()

    def _get_preflight_paths(self) -> tuple[Path, Path | None] | None:
        """프리플라이트 검사할 경로 반환"""
        return (self.file_path, None)

    def _get_journal_info(self) -> tuple["JournalEntryType", "FileOperationDetails"] | None:
        """저널 정보 반환"""
        from ..journal import FileOperationDetails, JournalEntryType

        return (
            JournalEntryType.FILE_DELETE,
            FileOperationDetails(
                operation_type="file_delete",
                source_path=self.file_path,
                use_trash=self.use_trash,
                file_size=self.file_path.stat().st_size if self.file_path.exists() else None,
                metadata={"use_trash": self.use_trash},
            ),
        )

    def _execute_impl(self) -> None:
        """파일 삭제 실행"""
        if self.use_trash:
            # 임시 백업 폴더로 이동 (실제 휴지통 구현은 추후)
            backup_dir = Path.home() / ".animesorter_trash"
            backup_dir.mkdir(exist_ok=True)

            backup_path = backup_dir / f"{self.file_path.name}.{self._command_id.hex[:8]}"
            shutil.move(str(self.file_path), str(backup_path))
            self._store_undo_data("backup_path", backup_path)
        else:
            # 영구 삭제
            self.file_path.unlink()
            self._store_undo_data("permanent_delete", True)

        self._add_deleted_file(self.file_path)

    def _supports_undo(self) -> bool:
        """영구 삭제는 취소 지원하지 않음"""
        return self.use_trash

    def _undo_impl(self) -> None:
        """파일 삭제 취소"""
        backup_path = self._get_undo_data("backup_path")
        permanent_delete = self._get_undo_data("permanent_delete", False)

        if permanent_delete:
            raise RuntimeError("영구 삭제된 파일은 복원할 수 없습니다")

        if backup_path and backup_path.exists():
            # 원래 위치에 파일 복원
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(backup_path), str(self.file_path))


class RenameFileCommand(BaseCommand):
    """파일 이름변경 Command"""

    def __init__(self, file_path: str | Path, new_name: str):
        self.file_path = Path(file_path)
        self.new_name = new_name
        self.new_path = self.file_path.parent / new_name

        super().__init__(f"{self.file_path.name} → {new_name}")

    def _get_default_description(self) -> str:
        return f"파일 이름변경: {self.file_path.name} → {self.new_name}"

    def validate(self) -> bool:
        """이름변경 전 유효성 검사"""
        if not self.file_path.exists():
            return False

        if self.new_path.exists():
            return False

        return not (not self.new_name or self.new_name == self.file_path.name)

    def _get_preflight_paths(self) -> tuple[Path, Path | None] | None:
        """프리플라이트 검사할 경로 반환"""
        return (self.file_path, self.new_path)

    def _execute_impl(self) -> None:
        """파일 이름변경 실행"""
        self._store_undo_data("original_name", self.file_path.name)

        # 파일 이름변경
        self.file_path.rename(self.new_path)

        self._add_affected_file(self.file_path)
        self._add_affected_file(self.new_path)

    def _undo_impl(self) -> None:
        """파일 이름변경 취소"""
        original_name = self._get_undo_data("original_name")

        if self.new_path.exists():
            self.new_path.rename(self.file_path.parent / original_name)


class CreateDirectoryCommand(BaseCommand):
    """디렉토리 생성 Command"""

    def __init__(self, directory_path: str | Path, parents: bool = True):
        self.directory_path = Path(directory_path)
        self.parents = parents

        super().__init__(f"{self.directory_path.name} 디렉토리 생성")

    def _get_default_description(self) -> str:
        return f"디렉토리 생성: {self.directory_path}"

    def validate(self) -> bool:
        """생성 전 유효성 검사"""
        return not self.directory_path.exists()

    def _get_preflight_paths(self) -> tuple[Path, Path | None] | None:
        """프리플라이트 검사할 경로 반환"""
        return (self.directory_path, None)

    def _execute_impl(self) -> None:
        """디렉토리 생성 실행"""
        self.directory_path.mkdir(parents=self.parents, exist_ok=False)
        self._add_created_file(self.directory_path)

    def _undo_impl(self) -> None:
        """디렉토리 생성 취소"""
        if self.directory_path.exists() and self.directory_path.is_dir():
            # 빈 디렉토리만 삭제
            with suppress(OSError):
                self.directory_path.rmdir()


class BatchFileCommand(CompositeCommand):
    """배치 파일 조작 Command"""

    def __init__(self, commands: list[ICommand], description: str = ""):
        if not description:
            description = f"배치 파일 작업 ({len(commands)}개)"

        super().__init__(commands, description)

        # 배치 실행 통계
        self._success_count = 0
        self._failed_count = 0

    def _execute_impl(self) -> None:
        """배치 Command 실행 (일부 실패해도 계속 진행)"""
        for command in self.commands:
            try:
                result = command.execute()
                self._executed_commands.append(command)

                if result.is_success:
                    self._success_count += 1
                    # 결과 통합
                    if self._result:
                        self._result.affected_files.extend(result.affected_files)
                        self._result.created_files.extend(result.created_files)
                        self._result.deleted_files.extend(result.deleted_files)
                        self._result.modified_files.extend(result.modified_files)
                else:
                    self._failed_count += 1
                    self.logger.warning(f"배치 내 Command 실패: {command.description}")

            except Exception as e:
                self._failed_count += 1
                self.logger.error(f"배치 내 Command 예외: {command.description} - {e}")

        # 메타데이터 설정
        self._set_metadata("success_count", self._success_count)
        self._set_metadata("failed_count", self._failed_count)
        self._set_metadata("total_count", len(self.commands))

        # 일부 실패해도 전체가 성공으로 간주 (최소 1개 성공)
        if self._success_count == 0:
            raise RuntimeError(f"배치 작업 완전 실패: {self._failed_count}개 모두 실패")

    def validate(self) -> bool:
        """배치 Command 유효성 검사 (일부만 유효해도 OK)"""
        valid_count = sum(1 for command in self.commands if command.validate())
        return valid_count > 0
