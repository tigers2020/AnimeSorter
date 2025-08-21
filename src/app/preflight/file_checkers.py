"""
구체적인 파일 검사기들

각각의 안전성 검사를 담당하는 구체적인 검사기 구현
"""

import os
import shutil
from pathlib import Path

from .base_checker import BasePreflightChecker, PreflightResult


class FileConflictChecker(BasePreflightChecker):
    """파일 충돌 검사기"""

    def _get_default_name(self) -> str:
        return "FileConflict"

    def _get_default_description(self) -> str:
        return "대상 위치에 동일한 이름의 파일/디렉토리가 존재하는지 검사"

    def is_applicable(self, source_path: Path, destination_path: Path | None = None) -> bool:
        """이동/복사 작업에만 적용"""
        return destination_path is not None

    def _check_impl(
        self, source_path: Path, destination_path: Path | None, result: PreflightResult
    ) -> None:
        if not destination_path:
            return

        # 대상 파일이 이미 존재하는지 확인
        if destination_path.exists():
            # 동일한 파일인지 확인 (같은 경로)
            try:
                if source_path.resolve() == destination_path.resolve():
                    self._add_warning(
                        result,
                        "같은 파일로 이동/복사",
                        f"원본과 대상이 같은 파일입니다: {destination_path}",
                        [source_path, destination_path],
                        ["다른 이름이나 위치를 선택해주세요."],
                    )
                    return
            except (OSError, ValueError):
                # 경로 해석 실패 시 무시하고 계속
                pass

            # 파일 타입 확인
            source_is_file = source_path.is_file()
            dest_is_file = destination_path.is_file()

            if source_is_file and dest_is_file:
                # 파일 → 파일 충돌
                source_size = source_path.stat().st_size
                dest_size = destination_path.stat().st_size

                self._add_error(
                    result,
                    "파일 덮어쓰기",
                    f"대상 파일이 이미 존재합니다: {destination_path} "
                    f"(기존: {dest_size:,} bytes, 새로운: {source_size:,} bytes)",
                    [destination_path],
                    [
                        "다른 이름으로 저장하거나",
                        "기존 파일을 백업한 후 진행하거나",
                        "덮어쓰기를 확인해주세요.",
                    ],
                )

            elif source_path.is_dir() and destination_path.is_dir():
                # 디렉토리 → 디렉토리 충돌
                dest_contents = list(destination_path.iterdir())
                if dest_contents:
                    self._add_warning(
                        result,
                        "디렉토리 병합",
                        f"대상 디렉토리가 이미 존재하며 {len(dest_contents)}개의 파일을 포함합니다: {destination_path}",
                        [destination_path],
                        ["내용이 병합됩니다.", "같은 이름의 파일이 있으면 덮어쓰여집니다."],
                    )
                else:
                    self._add_info(
                        result,
                        "빈 디렉토리 덮어쓰기",
                        f"빈 대상 디렉토리를 덮어씁니다: {destination_path}",
                        [destination_path],
                    )

            else:
                # 파일 ↔ 디렉토리 충돌 (타입 불일치)
                self._add_critical(
                    result,
                    "파일 타입 충돌",
                    f"원본({'파일' if source_is_file else '디렉토리'})과 "
                    f"대상({'파일' if dest_is_file else '디렉토리'})의 타입이 다릅니다: {destination_path}",
                    [source_path, destination_path],
                    [
                        "다른 이름이나 위치를 선택하거나",
                        "기존 파일/디렉토리를 삭제한 후 진행해주세요.",
                    ],
                )


class PermissionChecker(BasePreflightChecker):
    """권한 검사기"""

    def _get_default_name(self) -> str:
        return "Permission"

    def _get_default_description(self) -> str:
        return "파일/디렉토리에 대한 읽기/쓰기 권한을 검사"

    def _check_impl(
        self, source_path: Path, destination_path: Path | None, result: PreflightResult
    ) -> None:
        # 원본 읽기 권한 확인
        if not os.access(source_path, os.R_OK):
            self._add_critical(
                result,
                "원본 읽기 권한 없음",
                f"원본 파일/디렉토리를 읽을 권한이 없습니다: {source_path}",
                [source_path],
                ["파일 권한을 확인하고 읽기 권한을 부여하거나", "관리자 권한으로 실행해주세요."],
            )

        # 이동 작업인 경우 원본 쓰기 권한도 확인
        if destination_path and not os.access(source_path.parent, os.W_OK):
            self._add_critical(
                result,
                "원본 디렉토리 쓰기 권한 없음",
                f"원본을 삭제할 권한이 없습니다: {source_path.parent}",
                [source_path.parent],
                [
                    "디렉토리 권한을 확인하고 쓰기 권한을 부여하거나",
                    "관리자 권한으로 실행해주세요.",
                ],
            )

        # 대상 권한 확인
        if destination_path:
            dest_parent = destination_path.parent

            # 대상 디렉토리가 존재하지 않으면 생성 가능한지 확인
            if not dest_parent.exists():
                # 상위 디렉토리들 중 존재하는 가장 가까운 것 찾기
                existing_parent = dest_parent
                while not existing_parent.exists() and existing_parent != existing_parent.parent:
                    existing_parent = existing_parent.parent

                if not os.access(existing_parent, os.W_OK):
                    self._add_critical(
                        result,
                        "대상 디렉토리 생성 권한 없음",
                        f"대상 디렉토리를 생성할 권한이 없습니다: {dest_parent}",
                        [dest_parent],
                        [
                            "상위 디렉토리의 권한을 확인하고 쓰기 권한을 부여하거나",
                            "관리자 권한으로 실행해주세요.",
                        ],
                    )
            else:
                # 대상 디렉토리가 존재하면 쓰기 권한 확인
                if not os.access(dest_parent, os.W_OK):
                    self._add_critical(
                        result,
                        "대상 디렉토리 쓰기 권한 없음",
                        f"대상 디렉토리에 쓸 권한이 없습니다: {dest_parent}",
                        [dest_parent],
                        [
                            "디렉토리 권한을 확인하고 쓰기 권한을 부여하거나",
                            "관리자 권한으로 실행해주세요.",
                        ],
                    )

            # 대상 파일이 이미 존재하는 경우 덮어쓰기 권한 확인
            if destination_path.exists() and not os.access(destination_path, os.W_OK):
                self._add_critical(
                    result,
                    "대상 파일 덮어쓰기 권한 없음",
                    f"기존 파일을 덮어쓸 권한이 없습니다: {destination_path}",
                    [destination_path],
                    [
                        "파일 권한을 확인하고 쓰기 권한을 부여하거나",
                        "읽기 전용 속성을 해제하거나",
                        "관리자 권한으로 실행해주세요.",
                    ],
                )


class DiskSpaceChecker(BasePreflightChecker):
    """디스크 용량 검사기"""

    def _get_default_name(self) -> str:
        return "DiskSpace"

    def _get_default_description(self) -> str:
        return "복사/이동 작업에 필요한 디스크 용량을 검사"

    def is_applicable(self, source_path: Path, destination_path: Path | None = None) -> bool:
        """복사 작업이나 다른 드라이브로의 이동에만 적용"""
        if not destination_path:
            return False

        try:
            # 같은 드라이브 내 이동은 용량 검사 불필요
            source_drive = source_path.resolve().parts[0]
            dest_drive = destination_path.resolve().parts[0]
            return source_drive != dest_drive
        except (IndexError, OSError):
            # 드라이브 확인 실패 시 안전하게 검사 수행
            return True

    def _check_impl(
        self, source_path: Path, destination_path: Path | None, result: PreflightResult
    ) -> None:
        if not destination_path:
            return

        try:
            # 원본 크기 계산
            if source_path.is_file():
                source_size = source_path.stat().st_size
            elif source_path.is_dir():
                source_size = self._get_directory_size(source_path)
            else:
                self._add_warning(
                    result,
                    "알 수 없는 파일 타입",
                    f"파일 타입을 확인할 수 없습니다: {source_path}",
                    [source_path],
                )
                return

            # 대상 드라이브의 사용 가능 용량 확인
            dest_parent = destination_path.parent
            dest_parent.mkdir(parents=True, exist_ok=True)  # 디렉토리가 없으면 생성

            free_space = shutil.disk_usage(dest_parent).free

            # 용량 비교
            if source_size > free_space:
                self._add_critical(
                    result,
                    "디스크 용량 부족",
                    f"사용 가능한 디스크 용량이 부족합니다. "
                    f"필요: {self._format_size(source_size)}, "
                    f"사용 가능: {self._format_size(free_space)}",
                    [source_path, destination_path],
                    ["다른 위치를 선택하거나", "불필요한 파일을 삭제하여 공간을 확보해주세요."],
                )
            elif source_size > free_space * 0.9:  # 90% 이상 사용 시 경고
                self._add_warning(
                    result,
                    "디스크 용량 부족 경고",
                    f"디스크 용량이 부족해질 수 있습니다. "
                    f"필요: {self._format_size(source_size)}, "
                    f"사용 가능: {self._format_size(free_space)}",
                    [destination_path],
                    ["작업 후 디스크 공간이 10% 미만으로 줄어듭니다."],
                )
            else:
                self._add_info(
                    result,
                    "디스크 용량 충분",
                    f"필요: {self._format_size(source_size)}, "
                    f"사용 가능: {self._format_size(free_space)}",
                )

        except (OSError, PermissionError) as e:
            self._add_warning(
                result,
                "디스크 용량 확인 실패",
                f"디스크 용량을 확인할 수 없습니다: {e}",
                [destination_path],
                ["수동으로 디스크 용량을 확인해주세요."],
            )

    def _get_directory_size(self, directory: Path) -> int:
        """디렉토리의 총 크기 계산"""
        total_size = 0
        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                    except (OSError, PermissionError):
                        # 접근할 수 없는 파일은 건너뛰기
                        continue
        except (OSError, PermissionError):
            # 디렉토리 순회 실패
            pass
        return total_size

    def _format_size(self, size_bytes: int) -> str:
        """바이트를 읽기 쉬운 형태로 변환"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"


class PathValidityChecker(BasePreflightChecker):
    """경로 유효성 검사기"""

    def _get_default_name(self) -> str:
        return "PathValidity"

    def _get_default_description(self) -> str:
        return "파일/디렉토리 경로의 유효성을 검사"

    def _check_impl(
        self, source_path: Path, destination_path: Path | None, result: PreflightResult
    ) -> None:
        # 원본 경로 검사
        self._check_path_validity(source_path, "원본", result)

        # 대상 경로 검사
        if destination_path:
            self._check_path_validity(destination_path, "대상", result)

    def _check_path_validity(self, path: Path, path_type: str, result: PreflightResult) -> None:
        """개별 경로의 유효성 검사"""
        path_str = str(path)

        # 경로 길이 검사 (Windows 제한)
        if len(path_str) > 260:
            self._add_error(
                result,
                f"{path_type} 경로가 너무 김",
                f"{path_type} 경로가 Windows 제한(260자)을 초과합니다: {len(path_str)}자",
                [path],
                ["더 짧은 경로를 사용하거나", "긴 경로 지원을 활성화해주세요."],
            )

        # 예약된 이름 검사 (Windows)
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }

        path_name = path.name.upper()
        if "." in path_name:
            path_name = path_name.split(".")[0]

        if path_name in reserved_names:
            self._add_critical(
                result,
                f"{path_type} 예약된 파일명",
                f"{path_type} 파일명이 시스템 예약어입니다: {path.name}",
                [path],
                ["다른 파일명을 사용해주세요."],
            )

        # 금지된 문자 검사 (Windows)
        forbidden_chars = '<>"|?*'  # ':' 제외 (드라이브 문자에 사용됨)

        # 파일명 부분만 검사 (전체 경로가 아닌)
        filename_parts = [path.name] + list(path.parts[1:])  # 드라이브 문자 제외

        for part in filename_parts:
            for char in forbidden_chars:
                if char in part:
                    self._add_error(
                        result,
                        f"{path_type} 금지된 문자",
                        f"{path_type} 파일/디렉토리명에 금지된 문자가 포함되어 있습니다: '{char}'",
                        [path],
                        ["금지된 문자를 제거하거나 대체해주세요."],
                    )
                    return  # 첫 번째 금지된 문자만 보고

            # ':' 문자는 파일명 내부에서만 금지 (드라이브 문자 제외)
            if ":" in part and len(part) > 2:  # "C:" 같은 드라이브 문자가 아닌 경우
                self._add_error(
                    result,
                    f"{path_type} 금지된 문자",
                    f"{path_type} 파일/디렉토리명에 금지된 문자가 포함되어 있습니다: ':'",
                    [path],
                    ["금지된 문자를 제거하거나 대체해주세요."],
                )
                return

        # 경로 끝의 공백이나 점 검사
        if path.name.endswith((" ", ".")):
            self._add_warning(
                result,
                f"{path_type} 경로 끝 문자",
                f"{path_type} 파일명이 공백이나 점으로 끝납니다: '{path.name}'",
                [path],
                ["파일명 끝의 공백이나 점을 제거해주세요."],
            )


class CircularReferenceChecker(BasePreflightChecker):
    """순환 참조 검사기"""

    def _get_default_name(self) -> str:
        return "CircularReference"

    def _get_default_description(self) -> str:
        return "디렉토리를 자기 하위로 이동하는 등의 순환 참조를 검사"

    def is_applicable(self, source_path: Path, destination_path: Path | None = None) -> bool:
        """디렉토리 이동/복사에만 적용"""
        return destination_path is not None and source_path.is_dir()

    def _check_impl(
        self, source_path: Path, destination_path: Path | None, result: PreflightResult
    ) -> None:
        if not destination_path or not source_path.is_dir():
            return

        try:
            source_resolved = source_path.resolve()
            dest_resolved = destination_path.resolve()

            # 대상이 원본의 하위 디렉토리인지 확인
            try:
                dest_resolved.relative_to(source_resolved)
                # 예외가 발생하지 않으면 하위 디렉토리임
                self._add_critical(
                    result,
                    "순환 참조 감지",
                    f"디렉토리를 자기 자신의 하위로 이동할 수 없습니다: "
                    f"{source_path} → {destination_path}",
                    [source_path, destination_path],
                    ["다른 위치를 선택하거나", "먼저 내용을 다른 곳으로 이동한 후 작업해주세요."],
                )
            except ValueError:
                # 하위 디렉토리가 아님 - 정상
                pass

        except (OSError, ValueError) as e:
            self._add_warning(
                result,
                "순환 참조 확인 실패",
                f"순환 참조를 확인할 수 없습니다: {e}",
                [source_path, destination_path],
                ["수동으로 경로를 확인해주세요."],
            )


class FileLockChecker(BasePreflightChecker):
    """파일 잠금 검사기"""

    def _get_default_name(self) -> str:
        return "FileLock"

    def _get_default_description(self) -> str:
        return "다른 프로세스가 파일을 사용 중인지 검사"

    def _check_impl(
        self, source_path: Path, destination_path: Path | None, result: PreflightResult
    ) -> None:
        # 원본 파일 잠금 확인
        self._check_file_lock(source_path, "원본", result)

        # 대상 파일 잠금 확인 (덮어쓰기 하는 경우)
        if destination_path and destination_path.exists():
            self._check_file_lock(destination_path, "대상", result)

    def _check_file_lock(self, file_path: Path, file_type: str, result: PreflightResult) -> None:
        """개별 파일의 잠금 상태 확인"""
        if not file_path.is_file():
            return

        try:
            # 파일을 독점 모드로 열어서 잠금 여부 확인
            with file_path.open("r+b"):
                # 파일을 열 수 있으면 잠금되지 않음
                pass
        except PermissionError:
            self._add_error(
                result,
                f"{file_type} 파일 사용 중",
                f"{file_type} 파일이 다른 프로세스에서 사용 중입니다: {file_path}",
                [file_path],
                ["파일을 사용 중인 프로그램을 종료하거나", "나중에 다시 시도해주세요."],
            )
        except OSError as e:
            self._add_warning(
                result,
                f"{file_type} 파일 접근 확인 실패",
                f"{file_type} 파일의 사용 상태를 확인할 수 없습니다: {e}",
                [file_path],
                ["파일이 사용 중일 수 있으니 주의해주세요."],
            )
