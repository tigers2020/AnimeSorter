"""
비디오 메타데이터 추출 모듈

비디오 파일에서 해상도, 코덱 등의 메타데이터를 추출하는 기능을 제공합니다.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from src.app.domain import MediaQuality


class VideoMetadataExtractor:
    """비디오 파일 메타데이터 추출기"""

    def __init__(self):
        """초기화"""
        self.logger = logging.getLogger(__name__)
        self._ffprobe_available = self._check_ffprobe_availability()

        # MediaQuality 우선순위 정의 (높은 값이 더 높은 우선순위)
        self._quality_priority = {
            MediaQuality.UHD_8K: 8,
            MediaQuality.UHD_4K: 7,
            MediaQuality.QHD_1440P: 6,
            MediaQuality.FHD_1080P: 5,
            MediaQuality.HD_720P: 4,
            MediaQuality.SD_480P: 3,
            MediaQuality.UNKNOWN: 1,
        }

    def _check_ffprobe_availability(self) -> bool:
        """ffprobe 사용 가능 여부 확인"""
        try:
            result = subprocess.run(
                ["ffprobe", "-version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            self.logger.warning("ffprobe를 찾을 수 없습니다. 비디오 메타데이터 추출이 제한됩니다.")
            return False

    def extract_resolution(self, file_path: str) -> str | None:
        """
        비디오 파일에서 해상도 정보 추출

        Args:
            file_path: 비디오 파일 경로

        Returns:
            해상도 문자열 (예: "1920x1080", "1280x720") 또는 None
        """
        if not self._ffprobe_available:
            self.logger.warning("ffprobe가 사용 불가능하여 해상도 추출을 건너뜁니다.")
            return None

        try:
            # ffprobe 명령어 구성
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                "-select_streams",
                "v:0",  # 첫 번째 비디오 스트림만
                str(file_path),
            ]

            # ffprobe 실행
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )  # 30초 타임아웃

            if result.returncode != 0:
                self.logger.warning(f"ffprobe 실행 실패: {result.stderr}")
                return None

            # JSON 파싱
            data = json.loads(result.stdout)

            if not data.get("streams"):
                self.logger.warning("비디오 스트림을 찾을 수 없습니다.")
                return None

            # 첫 번째 비디오 스트림에서 해상도 추출
            video_stream = data["streams"][0]
            width = video_stream.get("width")
            height = video_stream.get("height")

            if width and height:
                resolution = f"{width}x{height}"
                self.logger.debug(f"해상도 추출 성공: {resolution}")
                return resolution

            self.logger.warning("해상도 정보를 찾을 수 없습니다.")
            return None

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 실패: {e}")
            return None
        except subprocess.TimeoutExpired:
            self.logger.error("ffprobe 실행 시간 초과")
            return None
        except Exception as e:
            self.logger.error(f"해상도 추출 중 오류 발생: {e}")
            return None

    def extract_video_metadata(self, file_path: str) -> dict[str, Any] | None:
        """
        비디오 파일에서 전체 메타데이터 추출

        Args:
            file_path: 비디오 파일 경로

        Returns:
            메타데이터 딕셔너리 또는 None
        """
        if not self._ffprobe_available:
            return None

        try:
            # ffprobe 명령어 구성
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                str(file_path),
            ]

            # ffprobe 실행
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return None

            # JSON 파싱
            data = json.loads(result.stdout)

            metadata = {}

            # 비디오 스트림 정보
            video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
            if video_streams:
                video = video_streams[0]
                metadata.update(
                    {
                        "width": video.get("width"),
                        "height": video.get("height"),
                        "codec_name": video.get("codec_name"),
                        "bit_rate": video.get("bit_rate"),
                        "duration": video.get("duration"),
                        "frame_rate": video.get("r_frame_rate"),
                    }
                )

            # 오디오 스트림 정보
            audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
            if audio_streams:
                audio = audio_streams[0]
                metadata.update(
                    {
                        "audio_codec": audio.get("codec_name"),
                        "audio_bit_rate": audio.get("bit_rate"),
                        "sample_rate": audio.get("sample_rate"),
                    }
                )

            # 포맷 정보
            format_info = data.get("format", {})
            metadata.update(
                {
                    "file_size": format_info.get("size"),
                    "duration": format_info.get("duration"),
                    "bit_rate": format_info.get("bit_rate"),
                }
            )

            return metadata

        except Exception as e:
            self.logger.error(f"메타데이터 추출 중 오류 발생: {e}")
            return None

    def normalize_resolution(self, resolution: str) -> str:
        """
        해상도 문자열을 표준 형식으로 정규화

        Args:
            resolution: 원본 해상도 문자열

        Returns:
            정규화된 해상도 문자열
        """
        if not resolution:
            return "Unknown"

        # 1920x1080 형태를 1080p로 변환
        if "1920x1080" in resolution or "1080x1920" in resolution:
            return "1080p"
        if "1280x720" in resolution or "720x1280" in resolution:
            return "720p"
        if "854x480" in resolution or "480x854" in resolution:
            return "480p"
        if "3840x2160" in resolution or "2160x3840" in resolution:
            return "4K"
        if "2560x1440" in resolution or "1440x2560" in resolution:
            return "2K"

        # 이미 정규화된 형태인 경우 그대로 반환
        if resolution.upper() in ["1080P", "720P", "480P", "4K", "2K"]:
            return resolution.upper()

        return resolution

    def get_media_quality_from_resolution(self, resolution: str) -> MediaQuality:
        """
        해상도 문자열로부터 MediaQuality enum 값 반환

        Args:
            resolution: 해상도 문자열

        Returns:
            MediaQuality enum 값
        """
        if not resolution:
            return MediaQuality.UNKNOWN

        normalized = self.normalize_resolution(resolution).upper()

        if "4K" in normalized or "2160" in normalized:
            return MediaQuality.UHD_4K
        if "2K" in normalized or "1440" in normalized:
            return MediaQuality.QHD_1440P
        if "1080" in normalized:
            return MediaQuality.FHD_1080P
        if "720" in normalized:
            return MediaQuality.HD_720P
        if "480" in normalized:
            return MediaQuality.SD_480P

        return MediaQuality.UNKNOWN

    def compare_quality(self, quality1: MediaQuality, quality2: MediaQuality) -> int:
        """
        두 MediaQuality 값을 비교하여 우선순위 반환

        Args:
            quality1: 첫 번째 품질
            quality2: 두 번째 품질

        Returns:
            -1: quality1이 더 낮음, 0: 동일, 1: quality1이 더 높음
        """
        priority1 = self._quality_priority.get(quality1, 0)
        priority2 = self._quality_priority.get(quality2, 0)

        if priority1 < priority2:
            return -1
        if priority1 > priority2:
            return 1

        return 0

    def get_highest_quality(self, qualities: list[MediaQuality]) -> MediaQuality:
        """
        여러 MediaQuality 값 중 가장 높은 품질 반환

        Args:
            qualities: MediaQuality 리스트

        Returns:
            가장 높은 품질의 MediaQuality
        """
        if not qualities:
            return MediaQuality.UNKNOWN

        return max(qualities, key=lambda q: self._quality_priority.get(q, 0))

    def classify_files_by_quality(self, file_paths: list[str]) -> tuple[list[str], list[str]]:
        """
        파일들을 화질에 따라 분류하여 고화질과 저화질 그룹으로 나눔

        Args:
            file_paths: 파일 경로 리스트

        Returns:
            (고화질 파일 리스트, 저화질 파일 리스트) 튜플
        """
        if not file_paths:
            return [], []

        # 각 파일의 화질 정보 추출
        file_qualities = []
        for file_path in file_paths:
            try:
                resolution = self.extract_resolution(file_path)
                quality = self.get_media_quality_from_resolution(resolution)
                file_qualities.append((file_path, quality))
                self.logger.debug(f"파일 {Path(file_path).name}: {quality.value}")
            except Exception as e:
                self.logger.warning(f"파일 {file_path}의 화질 추출 실패: {e}")
                file_qualities.append((file_path, MediaQuality.UNKNOWN))

        if not file_qualities:
            return [], []

        # 가장 높은 화질 찾기
        highest_quality = self.get_highest_quality([q for _, q in file_qualities])
        self.logger.info(f"그룹 내 최고 화질: {highest_quality.value}")

        # 고화질과 저화질로 분류
        high_quality_files = []
        low_quality_files = []

        for file_path, quality in file_qualities:
            if quality == highest_quality:
                high_quality_files.append(file_path)
            else:
                low_quality_files.append(file_path)

        self.logger.info(
            f"화질별 분류 완료: 고화질 {len(high_quality_files)}개, 저화질 {len(low_quality_files)}개"
        )

        return high_quality_files, low_quality_files

    def get_quality_summary(self, file_paths: list[str]) -> dict[str, Any]:
        """
        파일 그룹의 화질 요약 정보 반환

        Args:
            file_paths: 파일 경로 리스트

        Returns:
            화질 요약 정보 딕셔너리
        """
        if not file_paths:
            return {
                "total_files": 0,
                "quality_distribution": {},
                "highest_quality": MediaQuality.UNKNOWN.value,
            }

        quality_counts = {}
        file_qualities = []

        for file_path in file_paths:
            try:
                resolution = self.extract_resolution(file_path)
                quality = self.get_media_quality_from_resolution(resolution)
                quality_counts[quality.value] = quality_counts.get(quality.value, 0) + 1
                file_qualities.append(quality)
            except Exception as e:
                self.logger.warning(f"파일 {file_path}의 화질 추출 실패: {e}")
                quality_counts[MediaQuality.UNKNOWN.value] = (
                    quality_counts.get(MediaQuality.UNKNOWN.value, 0) + 1
                )

        highest_quality = self.get_highest_quality(file_qualities)

        return {
            "total_files": len(file_paths),
            "quality_distribution": quality_counts,
            "highest_quality": highest_quality.value,
            "highest_quality_enum": highest_quality,
        }
