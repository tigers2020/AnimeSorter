"""
파일 서비스

파일 시스템 관련 작업을 담당하는 서비스
"""

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..interfaces.i_event_bus import IEventBus
from ..interfaces.i_service import IService


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
    operation_type: str  # 'move', 'copy', 'simulate'
    file_type: str  # 'video', 'subtitle'
    success: bool = False
    error_message: str | None = None


class FileService(IService):
    """
    파일 서비스

    파일 시스템 작업, 유효성 검사, 경로 처리 등을 담당
    """

    def __init__(self, event_bus: IEventBus):
        super().__init__(event_bus)
        self.logger = logging.getLogger(__name__)

        # 파일 확장자 정의
        self.video_extensions = {
            ".mkv",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".mpg",
            ".mpeg",
            ".ts",
            ".m2ts",
        }

        self.subtitle_extensions = {
            ".srt",
            ".ass",
            ".ssa",
            ".sub",
            ".vtt",
            ".idx",
            ".smi",
            ".sami",
            ".txt",
        }

        # 기본 설정
        self.default_config = {
            "min_file_size": 1024 * 1024,  # 1MB
            "max_path_length": 260,  # Windows 경로 길이 제한
            "safe_mode": True,
            "backup_before_move": False,
            "overwrite_existing": False,
            "create_directories": True,
        }

        self.configure(self.default_config)

        self.logger.info("FileService 초기화 완료")

    def start(self) -> None:
        """서비스 시작"""
        try:
            self.set_running(True)

            # 이벤트 구독
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
            # 이벤트 구독 해제
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

            # 기본 정보
            file_info = FileInfo(
                path=str(path_obj.absolute()),
                name=path_obj.name,
                size=0,
                extension=path_obj.suffix.lower(),
                directory=str(path_obj.parent.absolute()),
                exists=path_obj.exists(),
            )

            # 파일이 존재하는 경우 추가 정보
            if file_info.exists:
                file_info.size = path_obj.stat().st_size

            # 파일 타입 분류
            file_info.is_video = file_info.extension in self.video_extensions
            file_info.is_subtitle = file_info.extension in self.subtitle_extensions

            return file_info

        except Exception as e:
            self.logger.error(f"파일 정보 가져오기 실패: {file_path} - {e}")
            # 오류 시 기본 정보 반환
            return FileInfo(
                path=file_path,
                name=os.path.basename(file_path),
                size=0,
                extension="",
                directory=os.path.dirname(file_path),
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

            # 파일 존재 확인
            if not file_info.exists:
                validation_result["is_valid"] = False
                validation_result["issues"].append("파일이 존재하지 않습니다")
                return validation_result

            # 파일 크기 확인 (비디오 파일만)
            if file_info.is_video:
                min_size = self.get_config("min_file_size", 1024 * 1024)
                if file_info.size < min_size:
                    validation_result["issues"].append(
                        f"파일 크기가 너무 작습니다 ({file_info.size} bytes)"
                    )

            # 경로 길이 확인
            max_path_length = self.get_config("max_path_length", 260)
            if len(file_info.path) > max_path_length:
                validation_result["issues"].append(
                    f"경로가 너무 깁니다 ({len(file_info.path)} 문자)"
                )

            # 권한 확인
            if not os.access(file_path, os.R_OK):
                validation_result["issues"].append("파일 읽기 권한이 없습니다")

            # 문제가 있으면 유효하지 않음으로 표시
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
        """디렉토리 스캔"""
        try:
            if not os.path.exists(directory):
                self.logger.warning(f"디렉토리가 존재하지 않습니다: {directory}")
                return []

            if file_types is None:
                file_types = ["video"]

            files = []

            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    file_info = self.get_file_info(file_path)

                    # 파일 타입 필터링
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
            video_name = video_path.stem  # 확장자 제외한 파일명
            video_dir = video_path.parent

            subtitle_files = []

            # 같은 디렉토리에서 같은 이름의 자막 파일 검색
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
        """파일 이동"""
        try:
            operation = MoveOperation(
                source_path=source_path,
                destination_path=destination_path,
                operation_type="move",
                file_type="video" if self.get_file_info(source_path).is_video else "subtitle",
            )

            # 대상 디렉토리 생성
            if self.get_config("create_directories", True):
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            # 기존 파일 확인
            if os.path.exists(destination_path):
                if not self.get_config("overwrite_existing", False):
                    operation.error_message = "대상 파일이 이미 존재합니다"
                    return operation

            # 백업 생성
            if self.get_config("backup_before_move", False):
                self._create_backup(source_path)

            # 파일 이동
            shutil.move(source_path, destination_path)
            operation.success = True

            # 자막 파일도 함께 이동
            if move_subtitles and operation.file_type == "video":
                subtitle_files = self.find_subtitle_files(source_path)
                for subtitle_file in subtitle_files:
                    try:
                        subtitle_name = os.path.basename(subtitle_file)
                        subtitle_dest = os.path.join(
                            os.path.dirname(destination_path), subtitle_name
                        )
                        shutil.move(subtitle_file, subtitle_dest)
                        self.logger.debug(f"자막 파일 이동: {subtitle_file} -> {subtitle_dest}")
                    except Exception as e:
                        self.logger.warning(f"자막 파일 이동 실패: {subtitle_file} - {e}")

            self.logger.info(f"파일 이동 성공: {source_path} -> {destination_path}")
            return operation

        except Exception as e:
            operation.error_message = str(e)
            self.logger.error(f"파일 이동 실패: {source_path} -> {destination_path} - {e}")
            return operation

    def copy_file(self, source_path: str, destination_path: str) -> MoveOperation:
        """파일 복사"""
        try:
            operation = MoveOperation(
                source_path=source_path,
                destination_path=destination_path,
                operation_type="copy",
                file_type="video" if self.get_file_info(source_path).is_video else "subtitle",
            )

            # 대상 디렉토리 생성
            if self.get_config("create_directories", True):
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            # 파일 복사
            shutil.copy2(source_path, destination_path)
            operation.success = True

            self.logger.info(f"파일 복사 성공: {source_path} -> {destination_path}")
            return operation

        except Exception as e:
            operation.error_message = str(e)
            self.logger.error(f"파일 복사 실패: {source_path} -> {destination_path} - {e}")
            return operation

    def create_directory(self, directory_path: str) -> bool:
        """디렉토리 생성"""
        try:
            os.makedirs(directory_path, exist_ok=True)
            self.logger.debug(f"디렉토리 생성: {directory_path}")
            return True
        except Exception as e:
            self.logger.error(f"디렉토리 생성 실패: {directory_path} - {e}")
            return False

    def delete_empty_directories(self, root_directory: str) -> int:
        """빈 디렉토리 삭제 (재귀적)"""
        try:
            deleted_count = 0

            for root, dirs, files in os.walk(root_directory, topdown=False):
                for directory in dirs:
                    dir_path = os.path.join(root, directory)
                    try:
                        if not os.listdir(dir_path):  # 빈 디렉토리인지 확인
                            os.rmdir(dir_path)
                            deleted_count += 1
                            self.logger.debug(f"빈 디렉토리 삭제: {dir_path}")
                    except OSError:
                        # 디렉토리가 비어있지 않거나 삭제할 수 없는 경우
                        pass

            self.logger.info(f"빈 디렉토리 정리 완료: {deleted_count}개 삭제")
            return deleted_count

        except Exception as e:
            self.logger.error(f"빈 디렉토리 정리 실패: {root_directory} - {e}")
            return 0

    def sanitize_filename(self, filename: str) -> str:
        """파일명 정제"""
        try:
            # Windows에서 사용할 수 없는 문자 제거
            invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
            sanitized = filename

            for char in invalid_chars:
                sanitized = sanitized.replace(char, "_")

            # 연속된 공백을 하나로 줄이기
            sanitized = " ".join(sanitized.split())

            # 앞뒤 공백 제거
            sanitized = sanitized.strip()

            # 빈 문자열 방지
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
