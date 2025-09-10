"""
파일 서비스

파일 시스템 관련 작업을 담당하는 서비스
리팩토링: 통합된 파일 조직화 서비스를 사용하여 중복 코드 제거
"""

import logging

logger = logging.getLogger(__name__)
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.config.file_organization_config import FileOrganizationConfig
from src.core.interfaces.file_organization_interface import FileOperationType

# Legacy interfaces removed - using direct implementations


@dataclass
class FileInfo:
    """파일 정보 데이터 클래스"""

    path: str
    name: str
    size: int
    extension: str
    directory: str
    exists: bool = True
    is_video: bool = False
    is_subtitle: bool = False


@dataclass
class MoveOperation:
    """파일 이동 작업 정보"""

    source_path: str
    destination_path: str
    operation_type: str
    file_type: str
    success: bool = False
    error_message: str | None = None


class FileService:
    """
    파일 서비스 - 리팩토링된 버전

    파일 시스템 작업, 유효성 검사, 경로 처리 등을 담당
    통합된 파일 조직화 서비스를 사용하여 중복 코드 제거
    """

    def __init__(self, event_bus=None):
        self.logger = logging.getLogger(__name__)
        config = FileOrganizationConfig(
            safe_mode=True,
            backup_before_operation=False,
            overwrite_existing=False,
            create_directories=True,
        )
        # 지연 import로 순환 import 문제 해결
        from src.core.services.unified_file_organization_service import \
            UnifiedFileOrganizationService

        self.unified_service = UnifiedFileOrganizationService(config)
        self.video_extensions = config.video_extensions
        self.subtitle_extensions = config.subtitle_extensions
        self.default_config = {
            "min_file_size": config.min_file_size,
            "max_path_length": config.max_path_length,
            "safe_mode": config.safe_mode,
            "backup_before_move": config.backup_before_operation,
            "overwrite_existing": config.overwrite_existing,
            "create_directories": config.create_directories,
        }
        self.configure(self.default_config)
        self.logger.info("FileService 초기화 완료 (리팩토링된 버전)")

    def start(self) -> None:
        """서비스 시작"""
        try:
            self.set_running(True)
            self.event_bus.subscribe("file_operation_requested", self._handle_file_operation)
            self.event_bus.subscribe("directory_scan_requested", self._handle_directory_scan)
            self.event_bus.subscribe("file_validation_requested", self._handle_file_validation)
            self.logger.info("FileService 시작됨")
        except Exception as e:
            self.logger.error(f"FileService 시작 실패: {e}")
            raise

    def stop(self) -> None:
        """서비스 중지"""
        try:
            self.event_bus.unsubscribe("file_operation_requested", self._handle_file_operation)
            self.event_bus.unsubscribe("directory_scan_requested", self._handle_directory_scan)
            self.event_bus.unsubscribe("file_validation_requested", self._handle_file_validation)
            self.set_running(False)
            self.logger.info("FileService 중지됨")
        except Exception as e:
            self.logger.error(f"FileService 중지 실패: {e}")

    def _handle_file_operation(self, event) -> None:
        """파일 작업 이벤트 처리"""
        try:
            data = event.data
            operation_type = data.get("type")
            if operation_type == "move":
                result = self.move_file(data["source"], data["destination"])
                self.event_bus.publish(
                    "file_operation_completed", {"type": "move", "result": result}
                )
            elif operation_type == "copy":
                result = self.copy_file(data["source"], data["destination"])
                self.event_bus.publish(
                    "file_operation_completed", {"type": "copy", "result": result}
                )
        except Exception as e:
            self.logger.error(f"파일 작업 처리 실패: {e}")
            self.event_bus.publish("file_operation_failed", str(e))

    def _handle_directory_scan(self, event) -> None:
        """디렉토리 스캔 이벤트 처리"""
        try:
            directory = event.data.get("directory")
            file_types = event.data.get("file_types", ["video"])
            files = self.scan_directory(directory, file_types)
            self.event_bus.publish(
                "directory_scan_completed", {"directory": directory, "files": files}
            )
        except Exception as e:
            self.logger.error(f"디렉토리 스캔 처리 실패: {e}")
            self.event_bus.publish("directory_scan_failed", str(e))

    def _handle_file_validation(self, event) -> None:
        """파일 유효성 검사 이벤트 처리"""
        try:
            file_paths = event.data.get("file_paths", [])
            validation_results = []
            for file_path in file_paths:
                result = self.validate_file(file_path)
                validation_results.append(result)
            self.event_bus.publish("file_validation_completed", {"results": validation_results})
        except Exception as e:
            self.logger.error(f"파일 유효성 검사 처리 실패: {e}")
            self.event_bus.publish("file_validation_failed", str(e))

    def get_file_info(self, file_path: str) -> FileInfo:
        """파일 정보 반환"""
        try:
            path_obj = Path(file_path)
            file_info = FileInfo(
                path=str(path_obj.absolute()),
                name=path_obj.name,
                size=0,
                extension=path_obj.suffix.lower(),
                directory=str(path_obj.parent.absolute()),
                exists=path_obj.exists(),
            )
            if file_info.exists:
                file_info.size = path_obj.stat().st_size
            file_info.is_video = file_info.extension in self.video_extensions
            file_info.is_subtitle = file_info.extension in self.subtitle_extensions
            return file_info
        except Exception as e:
            self.logger.error(f"파일 정보 가져오기 실패: {file_path} - {e}")
            return FileInfo(
                path=file_path,
                name=Path(file_path).name,
                size=0,
                extension="",
                directory=str(Path(file_path).parent),
                exists=False,
            )

    def validate_file(self, file_path: str) -> dict[str, Any]:
        """파일 유효성 검사"""
        try:
            file_info = self.get_file_info(file_path)
            validation_result = {
                "file_path": file_path,
                "is_valid": True,
                "issues": [],
                "file_info": file_info,
            }
            if not file_info.exists:
                validation_result["is_valid"] = False
                validation_result["issues"].append("파일이 존재하지 않습니다")
                return validation_result
            if file_info.is_video:
                min_size = self.get_config("min_file_size", 1024 * 1024)
                if file_info.size < min_size:
                    validation_result["issues"].append(
                        f"파일 크기가 너무 작습니다 ({file_info.size} bytes)"
                    )
            max_path_length = self.get_config("max_path_length", 260)
            if len(file_info.path) > max_path_length:
                validation_result["issues"].append(
                    f"경로가 너무 깁니다 ({len(file_info.path)} 문자)"
                )
            if not Path(file_path).exists() or not Path(file_path).is_file():
                validation_result["issues"].append("파일 읽기 권한이 없습니다")
            if validation_result["issues"]:
                validation_result["is_valid"] = False
            return validation_result
        except Exception as e:
            self.logger.error(f"파일 유효성 검사 실패: {file_path} - {e}")
            return {
                "file_path": file_path,
                "is_valid": False,
                "issues": [f"검사 중 오류 발생: {str(e)}"],
                "file_info": None,
            }

    def scan_directory(self, directory: str, file_types: list[str] = None) -> list[FileInfo]:
        """디렉토리 스캔 - 리팩토링된 버전"""
        try:
            if not Path(directory).exists():
                self.logger.warning(f"디렉토리가 존재하지 않습니다: {directory}")
                return []
            if file_types is None:
                file_types = ["video"]
            scan_result = self.unified_service.scanner.scan_directory(
                Path(directory), recursive=True
            )
            files = []
            for file_path in scan_result.files_found:
                file_info = self.get_file_info(str(file_path))
                include_file = False
                if (
                    "video" in file_types
                    and file_info.is_video
                    or "subtitle" in file_types
                    and file_info.is_subtitle
                    or "all" in file_types
                ):
                    include_file = True
                if include_file:
                    files.append(file_info)
            self.logger.info(f"디렉토리 스캔 완료: {directory} - {len(files)}개 파일")
            return files
        except Exception as e:
            self.logger.error(f"디렉토리 스캔 실패: {directory} - {e}")
            return []

    def find_subtitle_files(self, video_file_path: str) -> list[str]:
        """비디오 파일과 연관된 자막 파일 찾기"""
        try:
            video_path = Path(video_file_path)
            video_name = video_path.stem
            video_dir = video_path.parent
            subtitle_files = []
            for subtitle_ext in self.subtitle_extensions:
                subtitle_path = video_dir / f"{video_name}{subtitle_ext}"
                if subtitle_path.exists():
                    subtitle_files.append(str(subtitle_path))
            self.logger.debug(f"자막 파일 검색: {video_file_path} -> {len(subtitle_files)}개 발견")
            return subtitle_files
        except Exception as e:
            self.logger.error(f"자막 파일 검색 실패: {video_file_path} - {e}")
            return []

    def move_file(
        self, source_path: str, destination_path: str, move_subtitles: bool = True
    ) -> MoveOperation:
        """파일 이동 - 리팩토링된 버전"""
        try:
            operation = MoveOperation(
                source_path=source_path,
                destination_path=destination_path,
                operation_type="move",
                file_type="video" if self.get_file_info(source_path).is_video else "subtitle",
            )
            from src.core.interfaces.file_organization_interface import \
                FileOperationPlan

            plan = FileOperationPlan(
                source_path=Path(source_path),
                target_path=Path(destination_path),
                operation_type=FileOperationType.MOVE,
            )
            result = self.unified_service.operation_executor.execute_operation(plan)
            if result.success:
                operation.success = True
                if move_subtitles and operation.file_type == "video":
                    subtitle_files = self.find_subtitle_files(source_path)
                    for subtitle_file in subtitle_files:
                        try:
                            subtitle_name = Path(subtitle_file).name
                            subtitle_dest = str(Path(destination_path).parent / subtitle_name)
                            shutil.move(subtitle_file, subtitle_dest)
                            self.logger.debug(f"자막 파일 이동: {subtitle_file} -> {subtitle_dest}")
                        except Exception as e:
                            self.logger.warning(f"자막 파일 이동 실패: {subtitle_file} - {e}")
                self.logger.info(f"파일 이동 성공: {source_path} -> {destination_path}")
            else:
                operation.error_message = result.error_message
                self.logger.error(
                    f"파일 이동 실패: {source_path} -> {destination_path} - {result.error_message}"
                )
            return operation
        except Exception as e:
            operation.error_message = str(e)
            self.logger.error(f"파일 이동 실패: {source_path} -> {destination_path} - {e}")
            return operation

    def copy_file(self, source_path: str, destination_path: str) -> MoveOperation:
        """파일 복사 - 리팩토링된 버전"""
        try:
            operation = MoveOperation(
                source_path=source_path,
                destination_path=destination_path,
                operation_type="copy",
                file_type="video" if self.get_file_info(source_path).is_video else "subtitle",
            )
            from src.core.interfaces.file_organization_interface import \
                FileOperationPlan

            plan = FileOperationPlan(
                source_path=Path(source_path),
                target_path=Path(destination_path),
                operation_type=FileOperationType.COPY,
            )
            result = self.unified_service.operation_executor.execute_operation(plan)
            if result.success:
                operation.success = True
                self.logger.info(f"파일 복사 성공: {source_path} -> {destination_path}")
            else:
                operation.error_message = result.error_message
                self.logger.error(
                    f"파일 복사 실패: {source_path} -> {destination_path} - {result.error_message}"
                )
            return operation
        except Exception as e:
            operation.error_message = str(e)
            self.logger.error(f"파일 복사 실패: {source_path} -> {destination_path} - {e}")
            return operation

    def create_directory(self, directory_path: str) -> bool:
        """디렉토리 생성"""
        try:
            Path(directory_path).mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"디렉토리 생성: {directory_path}")
            return True
        except Exception as e:
            self.logger.error(f"디렉토리 생성 실패: {directory_path} - {e}")
            return False

    def delete_empty_directories(self, root_directory: str) -> int:
        """빈 디렉토리 삭제 (재귀적)"""
        try:
            deleted_count = 0
            for dir_path in sorted(
                Path(root_directory).rglob("*"), key=lambda p: len(p.parts), reverse=True
            ):
                if dir_path.is_dir():
                    try:
                        if not list(dir_path.iterdir()):
                            dir_path.rmdir()
                            deleted_count += 1
                            self.logger.debug(f"빈 디렉토리 삭제: {dir_path}")
                    except OSError:
                        pass
            self.logger.info(f"빈 디렉토리 정리 완료: {deleted_count}개 삭제")
            return deleted_count
        except Exception as e:
            self.logger.error(f"빈 디렉토리 정리 실패: {root_directory} - {e}")
            return 0

    def sanitize_filename(self, filename: str) -> str:
        """파일명 정제"""
        try:
            invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
            sanitized = filename
            for char in invalid_chars:
                sanitized = sanitized.replace(char, "_")
            sanitized = " ".join(sanitized.split())
            sanitized = sanitized.strip()
            if not sanitized:
                sanitized = "unknown"
            return sanitized
        except Exception as e:
            self.logger.error(f"파일명 정제 실패: {filename} - {e}")
            return "unknown"

    def _create_backup(self, file_path: str) -> str | None:
        """파일 백업 생성"""
        try:
            import time

            timestamp = int(time.time())
            backup_path = f"{file_path}.backup_{timestamp}"
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"백업 생성: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"백업 생성 실패: {file_path} - {e}")
            return None

    def get_stats(self) -> dict[str, Any]:
        """서비스 통계 반환"""
        return {
            "is_running": self.is_running,
            "video_extensions_count": len(self.video_extensions),
            "subtitle_extensions_count": len(self.subtitle_extensions),
            "config": dict(self._config),
        }
