"""
미디어 데이터 내보내기

미디어 데이터를 다양한 형식으로 내보내는 기능을 담당하는 모듈입니다.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

from ...domain import MediaFile, MediaGroup


class MediaExporter:
    """미디어 데이터를 다양한 형식으로 내보내는 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def export_data(
        self,
        media_files: list[MediaFile],
        groups: dict[str, MediaGroup],
        export_path: Path,
        format: str = "json",
        include_statistics: bool = True,
    ) -> dict[str, Any]:
        """미디어 데이터를 지정된 형식으로 내보냅니다."""
        try:
            self.logger.info(f"데이터 내보내기 시작: {format} 형식, {export_path}")

            start_time = time.time()

            # 내보낼 데이터 준비
            export_data = self._prepare_export_data(media_files, groups, include_statistics)

            # 형식에 따라 내보내기
            if format.lower() == "json":
                self._export_to_json(export_data, export_path)
            else:
                raise ValueError(f"지원하지 않는 내보내기 형식: {format}")

            export_duration = time.time() - start_time
            export_size = export_path.stat().st_size if export_path.exists() else 0

            # 내보내기 결과 정보
            result = {
                "export_path": export_path,
                "export_size_bytes": export_size,
                "exported_files_count": len(media_files),
                "exported_groups_count": len(groups),
                "export_duration_seconds": export_duration,
                "format": format,
                "success": True,
            }

            self.logger.info(f"데이터 내보내기 완료: {export_path}")
            return result

        except Exception as e:
            self.logger.error(f"데이터 내보내기 실패: {e}")

            result = {
                "export_path": export_path,
                "error": str(e),
                "success": False,
            }

            return result

    def _prepare_export_data(
        self,
        media_files: list[MediaFile],
        groups: dict[str, MediaGroup],
        include_statistics: bool,
    ) -> dict[str, Any]:
        """내보낼 데이터를 준비합니다."""
        export_data = {
            "files": [self._media_file_to_dict(file) for file in media_files],
            "groups": {gid: self._media_group_to_dict(group) for gid, group in groups.items()},
            "metadata": {
                "export_timestamp": time.time(),
                "total_files": len(media_files),
                "total_groups": len(groups),
                "export_format": "json",
            },
        }

        if include_statistics:
            export_data["statistics"] = self._calculate_statistics(media_files, groups)

        return export_data

    def _export_to_json(self, data: dict[str, Any], export_path: Path) -> None:
        """JSON 형식으로 데이터를 내보냅니다."""
        # 디렉토리 생성
        export_path.parent.mkdir(parents=True, exist_ok=True)

        # JSON 파일로 저장
        with export_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _media_file_to_dict(self, media_file: MediaFile) -> dict[str, Any]:
        """MediaFile을 딕셔너리로 변환합니다."""
        return {
            "file_id": str(media_file.file_id),
            "original_filename": media_file.original_filename,
            "file_path": str(media_file.file_path),
            "file_size_bytes": media_file.file_size_bytes,
            "media_type": media_file.media_type.value,
            "quality": media_file.quality.value,
            "source": media_file.source.value,
            "title": media_file.title,
            "series": media_file.series,
            "season": media_file.season,
            "episode": media_file.episode,
        }

    def _media_group_to_dict(self, media_group: MediaGroup) -> dict[str, Any]:
        """MediaGroup을 딕셔너리로 변환합니다."""
        return {
            "group_id": media_group.group_id,
            "title": media_group.title,
            "total_episodes": media_group.total_episodes,
            "media_type": media_group.media_type.value,
            "files": [self._media_file_to_dict(f) for f in media_group.files],
        }

    def _calculate_statistics(
        self, media_files: list[MediaFile], groups: dict[str, MediaGroup]
    ) -> dict[str, Any]:
        """통계 정보를 계산합니다."""
        if not media_files:
            return {
                "total_files": 0,
                "total_groups": 0,
                "files_by_type": {},
                "files_by_quality": {},
                "files_by_source": {},
                "total_size_bytes": 0,
                "average_file_size_mb": 0.0,
                "largest_file_size_mb": 0.0,
                "smallest_file_size_mb": 0.0,
            }

        # 타입별, 품질별, 소스별 통계
        files_by_type = {}
        files_by_quality = {}
        files_by_source = {}

        total_size = 0
        file_sizes = []

        for file in media_files:
            # 타입별 통계
            type_key = file.media_type.value
            files_by_type[type_key] = files_by_type.get(type_key, 0) + 1

            # 품질별 통계
            quality_key = file.quality.value
            files_by_quality[quality_key] = files_by_quality.get(quality_key, 0) + 1

            # 소스별 통계
            source_key = file.source.value
            files_by_source[source_key] = files_by_source.get(source_key, 0) + 1

            # 파일 크기 통계
            if file.file_size_bytes > 0:
                total_size += file.file_size_bytes
                file_sizes.append(file.file_size_bytes / (1024 * 1024))  # MB로 변환

        # 파일 크기 통계 계산
        average_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0.0
        largest_size = max(file_sizes) if file_sizes else 0.0
        smallest_size = min(file_sizes) if file_sizes else 0.0

        return {
            "total_files": len(media_files),
            "total_groups": len(groups),
            "files_by_type": files_by_type,
            "files_by_quality": files_by_quality,
            "files_by_source": files_by_source,
            "total_size_bytes": total_size,
            "average_file_size_mb": round(average_size, 2),
            "largest_file_size_mb": round(largest_size, 2),
            "smallest_file_size_mb": round(smallest_size, 2),
        }

    def export_to_csv(self, media_files: list[MediaFile], export_path: Path) -> bool:
        """CSV 형식으로 데이터를 내보냅니다."""
        try:
            import csv

            # 디렉토리 생성
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with export_path.open("w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "file_id",
                    "original_filename",
                    "file_path",
                    "file_size_bytes",
                    "media_type",
                    "quality",
                    "source",
                    "title",
                    "series",
                    "season",
                    "episode",
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for file in media_files:
                    writer.writerow(self._media_file_to_dict(file))

            self.logger.info(f"CSV 내보내기 완료: {export_path}")
            return True

        except ImportError:
            self.logger.error("CSV 모듈을 가져올 수 없습니다")
            return False
        except Exception as e:
            self.logger.error(f"CSV 내보내기 실패: {e}")
            return False

    def get_supported_formats(self) -> list[str]:
        """지원하는 내보내기 형식을 반환합니다."""
        return ["json", "csv"]

    def validate_export_path(self, export_path: Path) -> bool:
        """내보내기 경로가 유효한지 확인합니다."""
        try:
            # 디렉토리가 존재하거나 생성 가능한지 확인
            if export_path.exists():
                # 파일이 이미 존재하는 경우 덮어쓸 수 있는지 확인
                return export_path.is_file() and export_path.parent.is_dir()
            else:
                # 부모 디렉토리가 존재하거나 생성 가능한지 확인
                return export_path.parent.exists() or export_path.parent.is_dir()
        except Exception:
            return False
