"""
파일명 생성 및 관리 모듈

파일명 생성, 경로 생성, 제목 정리 등의 기능을 담당합니다.
"""

import logging
from pathlib import Path
from typing import Optional


class FileNamingManager:
    """파일명 생성 및 관리를 담당하는 클래스"""

    def __init__(self, naming_scheme: str = "standard"):
        self.naming_scheme = naming_scheme
        self.logger = logging.getLogger(self.__class__.__name__)

        # 지원되는 파일명 지정 방식
        self.supported_schemes = ["standard", "minimal", "detailed"]

    def set_naming_scheme(self, scheme: str) -> bool:
        """파일명 지정 방식 설정"""
        if scheme in self.supported_schemes:
            self.naming_scheme = scheme
            self.logger.info(f"파일명 지정 방식: {scheme}")
            return True
        else:
            self.logger.warning(f"지원되지 않는 파일명 지정 방식: {scheme}")
            return False

    def generate_destination_path(
        self, source_file: Path, metadata: dict, destination_root: Path
    ) -> Optional[Path]:
        """대상 파일 경로 생성"""
        try:
            # 기본 정보 추출
            title = metadata.get("title", "Unknown")
            season = metadata.get("season", 1)
            episode = metadata.get("episode")
            resolution = metadata.get("resolution", "")
            group = metadata.get("group", "")

            # 제목 정리
            title = self._clean_title_for_path(title)

            # 시즌 디렉토리명 생성
            season_dir = title if season == 1 else f"{title} Season {season}"

            # 에피소드 파일명 생성
            if episode:
                episode_filename = self._generate_episode_filename(
                    title, season, episode, resolution, group
                )
            else:
                episode_filename = f"{title}{source_file.suffix}"

            # 전체 경로 구성
            return destination_root / season_dir / episode_filename

        except Exception as e:
            self.logger.error(f"대상 경로 생성 실패: {e}")
            return None

    def _generate_episode_filename(
        self, title: str, season: int, episode: int, resolution: str, group: str
    ) -> str:
        """에피소드 파일명 생성"""
        if self.naming_scheme == "minimal":
            # 최소한의 정보만 포함
            filename = f"{title} S{season:02d}E{episode:02d}"
            if resolution:
                filename += f" {resolution}"
            filename += ".mkv"  # 기본 확장자

        elif self.naming_scheme == "detailed":
            # 상세한 정보 포함
            filename = f"{title} S{season:02d}E{episode:02d}"
            if resolution:
                filename += f" {resolution}"
            if group:
                filename += f" [{group}]"
            filename += ".mkv"

        else:  # standard
            # 표준 형식
            filename = f"{title} S{season:02d}E{episode:02d}"
            if resolution and resolution.strip():
                filename += f" - {resolution}"
            filename += ".mkv"

        return filename

    def _clean_title_for_path(self, title: str) -> str:
        """경로용 제목 정리"""
        if not title:
            return "Unknown"

        # 파일 시스템에서 사용할 수 없는 문자 제거/변환
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            title = title.replace(char, "")

        # 연속 공백을 단일 공백으로
        title = " ".join(title.split())

        # 앞뒤 공백 제거
        title = title.strip()

        return title if title else "Unknown"

    def generate_series_filename(
        self, title: str, season: int, episode: int, extension: str = ".mkv"
    ) -> str:
        """시리즈 파일명 생성"""
        try:
            # 기본 시리즈 파일명 형식
            filename = f"{title} S{season:02d}E{episode:02d}{extension}"

            # 제목 정리
            clean_title = self._clean_title_for_path(title)
            filename = filename.replace(title, clean_title)

            return filename

        except Exception as e:
            self.logger.error(f"시리즈 파일명 생성 실패: {e}")
            return f"Unknown S{season:02d}E{episode:02d}{extension}"

    def generate_movie_filename(
        self, title: str, year: Optional[int] = None, extension: str = ".mkv"
    ) -> str:
        """영화 파일명 생성"""
        try:
            # 기본 영화 파일명 형식
            if year:
                filename = f"{title} ({year}){extension}"
            else:
                filename = f"{title}{extension}"

            # 제목 정리
            clean_title = self._clean_title_for_path(title)
            filename = filename.replace(title, clean_title)

            return filename

        except Exception as e:
            self.logger.error(f"영화 파일명 생성 실패: {e}")
            return f"Unknown{extension}"

    def generate_episode_filename_with_quality(
        self, title: str, season: int, episode: int, quality: str, extension: str = ".mkv"
    ) -> str:
        """품질 정보가 포함된 에피소드 파일명 생성"""
        try:
            # 품질 정보 정리
            clean_quality = quality.strip() if quality else ""

            # 파일명 생성
            if clean_quality:
                filename = f"{title} S{season:02d}E{episode:02d} - {clean_quality}{extension}"
            else:
                filename = f"{title} S{season:02d}E{episode:02d}{extension}"

            # 제목 정리
            clean_title = self._clean_title_for_path(title)
            filename = filename.replace(title, clean_title)

            return filename

        except Exception as e:
            self.logger.error(f"품질 정보 포함 파일명 생성 실패: {e}")
            return f"Unknown S{season:02d}E{episode:02d}{extension}"

    def get_naming_scheme_info(self) -> dict:
        """파일명 지정 방식 정보 반환"""
        return {
            "current_scheme": self.naming_scheme,
            "supported_schemes": self.supported_schemes,
            "description": {
                "standard": "표준 형식: 제목 S01E01 - 품질.mkv",
                "minimal": "최소 형식: 제목 S01E01 품질.mkv",
                "detailed": "상세 형식: 제목 S01E01 품질 [그룹].mkv",
            },
        }

    def validate_filename(self, filename: str) -> bool:
        """파일명 유효성 검사"""
        try:
            # 파일 시스템에서 사용할 수 없는 문자 확인
            invalid_chars = '<>:"|?*'
            for char in invalid_chars:
                if char in filename:
                    return False

            # 파일명 길이 확인 (Windows 제한: 255자)
            if len(filename) > 255:
                return False

            # 빈 파일명 확인
            if not filename.strip():
                return False

            return True

        except Exception as e:
            self.logger.error(f"파일명 유효성 검사 실패: {e}")
            return False

    def sanitize_filename(self, filename: str) -> str:
        """파일명 정리 (안전한 문자로 변환)"""
        try:
            # 파일 시스템에서 사용할 수 없는 문자를 안전한 문자로 변환
            replacements = {
                "<": "(",
                ">": ")",
                ":": "-",
                '"': "'",
                "|": "-",
                "?": "",
                "*": "",
            }

            sanitized = filename
            for old_char, new_char in replacements.items():
                sanitized = sanitized.replace(old_char, new_char)

            # 연속 공백을 단일 공백으로
            sanitized = " ".join(sanitized.split())

            # 앞뒤 공백 제거
            sanitized = sanitized.strip()

            return sanitized if sanitized else "unnamed"

        except Exception as e:
            self.logger.error(f"파일명 정리 실패: {e}")
            return "unnamed"
