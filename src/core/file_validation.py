"""
파일 및 경로 검증 모듈

파일 경로 유효성, 권한, 존재 여부 등을 검증하는 기능을 담당합니다.
"""

import logging
import os
from pathlib import Path
from typing import Any


class FileValidator:
    """파일 및 경로 검증을 담당하는 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # 지원되는 비디오 확장자
        self.video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v", ".flv", ".webm"}

        # 지원되는 자막 확장자
        self.subtitle_extensions = {".srt", ".ass", ".ssa", ".sub", ".idx", ".smi", ".vtt"}

        # 지원되는 오디오 확장자
        self.audio_extensions = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"}

    def validate_destination(self, path: str) -> dict[str, Any]:
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
                "parent_writable": (
                    os.access(dest_path.parent, os.W_OK) if dest_path.parent.exists() else False
                ),
                "valid": writable,  # 전체 유효성
            }

        except Exception as e:
            return {"error": str(e), "valid": False}

    def validate_file_path(self, file_path: str) -> dict[str, Any]:
        """파일 경로 유효성 검사"""
        try:
            path_obj = Path(file_path)

            # 기본 정보
            result = {
                "path": str(path_obj),
                "exists": path_obj.exists(),
                "is_file": False,
                "is_dir": False,
                "readable": False,
                "writable": False,
                "size": 0,
                "extension": "",
                "valid": False,
            }

            if path_obj.exists():
                result.update(
                    {
                        "is_file": path_obj.is_file(),
                        "is_dir": path_obj.is_dir(),
                        "readable": os.access(path_obj, os.R_OK),
                        "writable": os.access(path_obj, os.W_OK),
                        "size": path_obj.stat().st_size if path_obj.is_file() else 0,
                        "extension": path_obj.suffix.lower(),
                    }
                )

                # 파일인 경우 확장자 검증
                if path_obj.is_file():
                    result["valid"] = self._is_supported_file_type(path_obj.suffix.lower())
                else:
                    result["valid"] = True  # 디렉토리는 유효함

            return result

        except Exception as e:
            return {"error": str(e), "valid": False}

    def validate_directory(self, dir_path: str) -> dict[str, Any]:
        """디렉토리 유효성 검사"""
        try:
            dir_obj = Path(dir_path)

            result = {
                "path": str(dir_obj),
                "exists": dir_obj.exists(),
                "is_dir": False,
                "readable": False,
                "writable": False,
                "empty": True,
                "file_count": 0,
                "dir_count": 0,
                "valid": False,
            }

            if dir_obj.exists() and dir_obj.is_dir():
                result.update(
                    {
                        "is_dir": True,
                        "readable": os.access(dir_obj, os.R_OK),
                        "writable": os.access(dir_obj, os.W_OK),
                        "empty": not any(dir_obj.iterdir()),
                    }
                )

                # 파일 및 디렉토리 개수 계산
                try:
                    items = list(dir_obj.iterdir())
                    result["file_count"] = sum(1 for item in items if item.is_file())
                    result["dir_count"] = sum(1 for item in items if item.is_dir())
                except PermissionError:
                    result["file_count"] = -1
                    result["dir_count"] = -1

                result["valid"] = result["readable"] and result["writable"]

            return result

        except Exception as e:
            return {"error": str(e), "valid": False}

    def _is_supported_file_type(self, extension: str) -> bool:
        """지원되는 파일 타입인지 확인"""
        return (
            extension in self.video_extensions
            or extension in self.subtitle_extensions
            or extension in self.audio_extensions
        )

    def get_supported_extensions(self) -> dict[str, set[str]]:
        """지원되는 파일 확장자 반환"""
        return {
            "video": self.video_extensions,
            "subtitle": self.subtitle_extensions,
            "audio": self.audio_extensions,
        }

    def add_supported_extension(self, category: str, extension: str) -> bool:
        """지원되는 확장자 추가"""
        try:
            if not extension.startswith("."):
                extension = "." + extension

            if category == "video":
                self.video_extensions.add(extension)
            elif category == "subtitle":
                self.subtitle_extensions.add(extension)
            elif category == "audio":
                self.audio_extensions.add(extension)
            else:
                self.logger.warning(f"알 수 없는 카테고리: {category}")
                return False

            self.logger.info(f"지원 확장자 추가: {category} - {extension}")
            return True

        except Exception as e:
            self.logger.error(f"지원 확장자 추가 실패: {e}")
            return False

    def remove_supported_extension(self, category: str, extension: str) -> bool:
        """지원되는 확장자 제거"""
        try:
            if not extension.startswith("."):
                extension = "." + extension

            if category == "video":
                self.video_extensions.discard(extension)
            elif category == "subtitle":
                self.subtitle_extensions.discard(extension)
            elif category == "audio":
                self.audio_extensions.discard(extension)
            else:
                self.logger.warning(f"알 수 없는 카테고리: {category}")
                return False

            self.logger.info(f"지원 확장자 제거: {category} - {extension}")
            return True

        except Exception as e:
            self.logger.error(f"지원 확장자 제거 실패: {e}")
            return False

    def validate_file_list(self, file_paths: list[str]) -> dict[str, Any]:
        """파일 목록 일괄 검증"""
        try:
            results: dict[str, Any] = {
                "valid_files": [],
                "invalid_files": [],
                "errors": [],
                "summary": {
                    "total": len(file_paths),
                    "valid": 0,
                    "invalid": 0,
                    "errors": 0,
                },
            }

            for file_path in file_paths:
                validation_result = self.validate_file_path(file_path)

                if "error" in validation_result:
                    results["errors"].append(
                        {"path": file_path, "error": validation_result["error"]}
                    )
                    results["summary"]["errors"] += 1
                elif validation_result["valid"]:
                    results["valid_files"].append(file_path)
                    results["summary"]["valid"] += 1
                else:
                    results["invalid_files"].append(file_path)
                    results["summary"]["invalid"] += 1

            self.logger.info(f"파일 목록 검증 완료: {results['summary']}")
            return results

        except Exception as e:
            self.logger.error(f"파일 목록 검증 실패: {e}")
            return {
                "valid_files": [],
                "invalid_files": [],
                "errors": [{"path": "unknown", "error": str(e)}],
                "summary": {"total": 0, "valid": 0, "invalid": 0, "errors": 1},
            }

    def check_disk_space(self, path: str, required_bytes: int = 0) -> dict[str, Any]:
        """디스크 공간 확인"""
        try:
            path_obj = Path(path)

            # 경로가 존재하지 않으면 부모 디렉토리 사용
            if not path_obj.exists():
                path_obj = path_obj.parent
                if not path_obj.exists():
                    return {"error": "경로를 찾을 수 없습니다", "valid": False}

            # 디스크 공간 확인
            import shutil

            total, used, free = shutil.disk_usage(path_obj)

            return {
                "path": str(path_obj),
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "required_bytes": required_bytes,
                "required_gb": round(required_bytes / (1024**3), 2),
                "sufficient_space": free >= required_bytes,
                "valid": True,
            }

        except Exception as e:
            return {"error": str(e), "valid": False}

    def validate_file_permissions(self, file_path: str) -> dict[str, Any]:
        """파일 권한 검증"""
        try:
            path_obj = Path(file_path)

            if not path_obj.exists():
                return {"error": "파일이 존재하지 않습니다", "valid": False}

            return {
                "path": str(path_obj),
                "readable": os.access(path_obj, os.R_OK),
                "writable": os.access(path_obj, os.W_OK),
                "executable": os.access(path_obj, os.X_OK),
                "owner_readable": os.access(path_obj, os.R_OK),
                "owner_writable": os.access(path_obj, os.W_OK),
                "owner_executable": os.access(path_obj, os.X_OK),
                "valid": True,
            }

        except Exception as e:
            return {"error": str(e), "valid": False}
