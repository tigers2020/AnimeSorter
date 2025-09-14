"""
파일 조작 Command 구현

안전한 파일 이동, 복사, 삭제, 이름변경 등의 Command들
"""

import logging

logger = logging.getLogger(__name__)
import shutil
from contextlib import suppress
from pathlib import Path

from src.app.commands.base_command import BaseCommand, CompositeCommand, ICommand
from src.core.utils.subtitle_utils import (
    find_subtitle_files,
    get_subtitle_destination_path,
    is_video_file,
)


class MoveFileCommand(BaseCommand):
    """파일 이동 Command"""

    def __init__(
        self,
        source: str | Path,
        destination: str | Path,
        create_dirs: bool = True,
        overwrite: bool = False,
        move_subtitles: bool = True,
    ):
        self.source = Path(source)
        self.destination = Path(destination)
        self.create_dirs = create_dirs
        self.overwrite = overwrite
        self.move_subtitles = move_subtitles
        super().__init__(f"{self.source.name} → {self.destination}")

    def _get_default_description(self) -> str:
        return f"파일 이동: {self.source.name} → {self.destination}"

    def validate(self) -> bool:
        """이동 전 유효성 검사"""
        if not self.source.exists():
            self.logger.error(f"원본 파일이 존재하지 않음: {self.source}")
            return False
        if self.destination.exists():
            if not self.overwrite:
                self.logger.error(f"대상 파일이 이미 존재함: {self.destination}")
                return False
            if self.destination.is_dir():
                self.logger.error(f"대상이 디렉토리임: {self.destination}")
                return False
        if self.create_dirs and not self.destination.parent.exists():
            try:
                self.destination.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                self.logger.error(f"대상 디렉토리 생성 권한 없음: {self.destination.parent}")
                return False
        return True

    def _get_preflight_paths(self) -> tuple[Path, Path | None] | None:
        """프리플라이트 검사할 경로 반환"""
        return self.source, self.destination

    def _execute_impl(self) -> None:
        """파일 이동 실행"""
        self._store_undo_data("original_source", self.source)
        self._store_undo_data("original_destination", self.destination)
        if self.destination.exists():
            backup_path = self.destination.with_suffix(f"{self.destination.suffix}.backup")
            shutil.move(str(self.destination), str(backup_path))
            self._store_undo_data("backup_path", backup_path)
        if self.create_dirs:
            self.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self.source), str(self.destination))
        moved_subtitles = []
        if self.move_subtitles and is_video_file(self.source):
            subtitle_files = find_subtitle_files(self.source)
            for subtitle_file in subtitle_files:
                try:
                    subtitle_dest = get_subtitle_destination_path(
                        self.source, self.destination, subtitle_file
                    )
                    if subtitle_dest.exists():
                        backup_path = subtitle_dest.with_suffix(f"{subtitle_dest.suffix}.backup")
                        shutil.move(str(subtitle_dest), str(backup_path))
                        self._store_undo_data(f"subtitle_backup_{subtitle_file}", backup_path)
                    shutil.move(subtitle_file, subtitle_dest)
                    moved_subtitles.append((subtitle_file, subtitle_dest))
                    self.logger.debug(f"자막 파일 이동: {subtitle_file} -> {subtitle_dest}")
                except Exception as e:
                    self.logger.warning(f"자막 파일 이동 실패: {subtitle_file} - {e}")
        self._store_undo_data("moved_subtitles", moved_subtitles)
        self._add_affected_file(self.source)
        self._add_affected_file(self.destination)
        for subtitle_src, subtitle_dest in moved_subtitles:
            self._add_affected_file(subtitle_src)
            self._add_affected_file(subtitle_dest)
        self._set_metadata("source_size", self.destination.stat().st_size)

    def _undo_impl(self) -> None:
        """파일 이동 취소"""
        original_source = self._get_undo_data("original_source")
        original_destination = self._get_undo_data("original_destination")
        backup_path = self._get_undo_data("backup_path")
        moved_subtitles = self._get_undo_data("moved_subtitles", [])
        if self.destination.exists():
            shutil.move(str(self.destination), str(original_source))
        if backup_path and backup_path.exists():
            shutil.move(str(backup_path), str(original_destination))
        for subtitle_src, subtitle_dest in moved_subtitles:
            try:
                if subtitle_dest.exists():
                    shutil.move(str(subtitle_dest), str(subtitle_src))
                    self.logger.debug(f"자막 파일 복원: {subtitle_dest} -> {subtitle_src}")
            except Exception as e:
                self.logger.warning(f"자막 파일 복원 실패: {subtitle_dest} - {e}")
        for subtitle_src, _ in moved_subtitles:
            backup_key = f"subtitle_backup_{subtitle_src}"
            subtitle_backup = self._get_undo_data(backup_key)
            if subtitle_backup and subtitle_backup.exists():
                try:
                    subtitle_dest = get_subtitle_destination_path(
                        original_source, original_destination, subtitle_src
                    )
                    shutil.move(str(subtitle_backup), str(subtitle_dest))
                    self.logger.debug(f"자막 파일 백업 복원: {subtitle_backup} -> {subtitle_dest}")
                except Exception as e:
                    self.logger.warning(f"자막 파일 백업 복원 실패: {subtitle_backup} - {e}")


class CopyFileCommand(BaseCommand):
    """파일 복사 Command"""

    def __init__(
        self,
        source: str | Path,
        destination: str | Path,
        create_dirs: bool = True,
        overwrite: bool = False,
        copy_subtitles: bool = True,
    ):
        self.source = Path(source)
        self.destination = Path(destination)
        self.create_dirs = create_dirs
        self.overwrite = overwrite
        self.copy_subtitles = copy_subtitles
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
        return self.source, self.destination

    def _execute_impl(self) -> None:
        """파일 복사 실행"""
        if self.destination.exists():
            backup_path = self.destination.with_suffix(f"{self.destination.suffix}.backup")
            shutil.copy2(str(self.destination), str(backup_path))
            self._store_undo_data("backup_path", backup_path)
        if self.create_dirs:
            self.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(self.source), str(self.destination))
        copied_subtitles = []
        if self.copy_subtitles and is_video_file(self.source):
            subtitle_files = find_subtitle_files(self.source)
            for subtitle_file in subtitle_files:
                try:
                    subtitle_dest = get_subtitle_destination_path(
                        self.source, self.destination, subtitle_file
                    )
                    if subtitle_dest.exists():
                        backup_path = subtitle_dest.with_suffix(f"{subtitle_dest.suffix}.backup")
                        shutil.copy2(str(subtitle_dest), str(backup_path))
                        self._store_undo_data(f"subtitle_backup_{subtitle_file}", backup_path)
                    shutil.copy2(subtitle_file, subtitle_dest)
                    copied_subtitles.append((subtitle_file, subtitle_dest))
                    self.logger.debug(f"자막 파일 복사: {subtitle_file} -> {subtitle_dest}")
                except Exception as e:
                    self.logger.warning(f"자막 파일 복사 실패: {subtitle_file} - {e}")
        self._store_undo_data("copied_subtitles", copied_subtitles)
        self._add_created_file(self.destination)
        for _, subtitle_dest in copied_subtitles:
            self._add_created_file(subtitle_dest)
        self._set_metadata("source_size", self.source.stat().st_size)
        self._set_metadata("copied_size", self.destination.stat().st_size)

    def _undo_impl(self) -> None:
        """파일 복사 취소"""
        backup_path = self._get_undo_data("backup_path")
        copied_subtitles = self._get_undo_data("copied_subtitles", [])
        if self.destination.exists():
            self.destination.unlink()
        if backup_path and backup_path.exists():
            shutil.move(str(backup_path), str(self.destination))
        for _, subtitle_dest in copied_subtitles:
            try:
                if subtitle_dest.exists():
                    subtitle_dest.unlink()
                    self.logger.debug(f"복사된 자막 파일 삭제: {subtitle_dest}")
            except Exception as e:
                self.logger.warning(f"복사된 자막 파일 삭제 실패: {subtitle_dest} - {e}")
        for subtitle_src, subtitle_dest in copied_subtitles:
            backup_key = f"subtitle_backup_{subtitle_src}"
            subtitle_backup = self._get_undo_data(backup_key)
            if subtitle_backup and subtitle_backup.exists():
                try:
                    shutil.move(str(subtitle_backup), str(subtitle_dest))
                    self.logger.debug(f"자막 파일 백업 복원: {subtitle_backup} -> {subtitle_dest}")
                except Exception as e:
                    self.logger.warning(f"자막 파일 백업 복원 실패: {subtitle_backup} - {e}")


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
        return self.file_path, None

    def _execute_impl(self) -> None:
        """파일 삭제 실행"""
        if self.use_trash:
            backup_dir = Path.home() / ".animesorter_trash"
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / f"{self.file_path.name}.{self._command_id.hex[:8]}"
            shutil.move(str(self.file_path), str(backup_path))
            self._store_undo_data("backup_path", backup_path)
        else:
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
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(backup_path), str(self.file_path))


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
        return self.directory_path, None

    def _execute_impl(self) -> None:
        """디렉토리 생성 실행"""
        self.directory_path.mkdir(parents=self.parents, exist_ok=False)
        self._add_created_file(self.directory_path)

    def _undo_impl(self) -> None:
        """디렉토리 생성 취소"""
        if self.directory_path.exists() and self.directory_path.is_dir():
            with suppress(OSError):
                self.directory_path.rmdir()


class BatchFileCommand(CompositeCommand):
    """배치 파일 조작 Command"""

    def __init__(self, commands: list[ICommand], description: str = ""):
        if not description:
            description = f"배치 파일 작업 ({len(commands)}개)"
        super().__init__(commands, description)
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
        self._set_metadata("success_count", self._success_count)
        self._set_metadata("failed_count", self._failed_count)
        self._set_metadata("total_count", len(self.commands))
        if self._success_count == 0:
            raise RuntimeError(f"배치 작업 완전 실패: {self._failed_count}개 모두 실패")

    def validate(self) -> bool:
        """배치 Command 유효성 검사 (일부만 유효해도 OK)"""
        valid_count = sum(1 for command in self.commands if command.validate())
        return valid_count > 0
