"""
비디오 메타데이터 추출 모듈

비디오 파일에서 해상도, 코덱 등의 메타데이터를 추출하는 기능을 제공합니다.
"""

import json
import logging
import subprocess
from typing import Any, Optional


class VideoMetadataExtractor:
    """비디오 파일 메타데이터 추출기"""

    def __init__(self):
        """초기화"""
        self.logger = logging.getLogger(__name__)
        self._ffprobe_available = self._check_ffprobe_availability()

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
