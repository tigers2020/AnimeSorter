"""
MediaListModel - 미디어 파일 목록을 위한 QAbstractListModel

Phase 2 MVVM 아키텍처의 일부로, 미디어 파일 목록을 표시하는 Qt 모델입니다.
"""

import logging
from typing import Any

from PyQt5.QtCore import QAbstractListModel, QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from src.app import (FilesScannedEvent, MediaFile,  # 이벤트; 도메인 모델; 인프라
                     MediaFileDeletedEvent, MediaFileUpdatedEvent,
                     MediaQuality, MediaType, ProcessingFlag, TypedEventBus,
                     get_event_bus)


class MediaListModel(QAbstractListModel):
    """미디어 파일 목록을 위한 Qt 모델"""

    # 커스텀 역할 정의
    FilePathRole = Qt.UserRole + 1
    FileNameRole = Qt.UserRole + 2
    FileSizeRole = Qt.UserRole + 3
    FileTypeRole = Qt.UserRole + 4
    MediaTypeRole = Qt.UserRole + 5
    MediaQualityRole = Qt.UserRole + 6
    MediaSourceRole = Qt.UserRole + 7
    ProcessingFlagRole = Qt.UserRole + 8
    HasMetadataRole = Qt.UserRole + 9
    MetadataQualityRole = Qt.UserRole + 10
    TMDBMatchRole = Qt.UserRole + 11
    LastModifiedRole = Qt.UserRole + 12
    CustomDataRole = Qt.UserRole + 13

    # 시그널 정의
    data_changed = pyqtSignal()
    model_reset = pyqtSignal()

    def __init__(self):
        super().__init__()

        # 로깅 설정
        self.logger = logging.getLogger(__name__)

        # 데이터 저장소
        self._media_files: list[MediaFile] = []
        self._filtered_files: list[MediaFile] = []
        self._is_filtered: bool = False

        # 정렬 설정
        self._sort_key: str = "name"
        self._sort_order: Qt.SortOrder = Qt.AscendingOrder

        # 필터 설정
        self._filters: dict[str, Any] = {}

        # 이벤트 버스 연결
        self._event_bus: TypedEventBus | None = None
        self._setup_event_bus()

        self.logger.info("MediaListModel 초기화 완료")

    def _setup_event_bus(self):
        """이벤트 버스 설정"""
        try:
            self._event_bus = get_event_bus()

            # 이벤트 구독
            if self._event_bus:
                self._event_bus.subscribe(FilesScannedEvent, self._on_files_scanned, weak_ref=False)
                self._event_bus.subscribe(
                    MediaFileUpdatedEvent, self._on_media_file_updated, weak_ref=False
                )
                self._event_bus.subscribe(
                    MediaFileDeletedEvent, self._on_media_file_deleted, weak_ref=False
                )

            self.logger.info("MediaListModel 이벤트 버스 연결 완료")
        except Exception as e:
            self.logger.error(f"MediaListModel 이벤트 버스 연결 실패: {e}")

    # QAbstractListModel 필수 메서드들
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """모델의 행 수 반환"""
        if parent.isValid():
            return 0
        return len(self._filtered_files if self._is_filtered else self._media_files)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """지정된 인덱스와 역할에 대한 데이터 반환"""
        if not index.isValid() or index.row() >= self.rowCount():
            return None

        media_file = self._get_media_file_at_index(index.row())
        if not media_file:
            return None

        if role == Qt.DisplayRole:
            return media_file.file_name

        if role == Qt.ToolTipRole:
            return self._create_tooltip(media_file)

        if role == Qt.DecorationRole:
            return self._get_file_icon(media_file)

        if role == Qt.FontRole:
            return self._get_file_font(media_file)

        if role == Qt.BackgroundRole:
            return self._get_file_background(media_file)

        if role == Qt.ForegroundRole:
            return self._get_file_foreground(media_file)

        if role == self.FilePathRole:
            return str(media_file.file_path)

        if role == self.FileNameRole:
            return media_file.file_name

        if role == self.FileSizeRole:
            return media_file.file_size

        if role == self.FileTypeRole:
            return media_file.file_type

        if role == self.MediaTypeRole:
            return media_file.media_type.value if media_file.media_type else ""

        if role == self.MediaQualityRole:
            return media_file.media_quality.value if media_file.media_quality else ""

        if role == self.MediaSourceRole:
            return media_file.media_source.value if media_file.media_source else ""

        if role == self.ProcessingFlagRole:
            return media_file.processing_flag.value if media_file.processing_flag else ""

        if role == self.HasMetadataRole:
            return media_file.metadata is not None

        if role == self.MetadataQualityRole:
            if media_file.metadata:
                return media_file.metadata.quality_score
            return 0.0

        if role == self.TMDBMatchRole:
            return media_file.metadata.tmdb_match_id if media_file.metadata else None

        if role == self.LastModifiedRole:
            return media_file.last_modified

        if role == self.CustomDataRole:
            return media_file

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Any:
        """헤더 데이터 반환"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return "파일명"
            if section == 1:
                return "크기"
            if section == 2:
                return "유형"
            if section == 3:
                return "품질"
            if section == 4:
                return "메타데이터"

        return super().headerData(section, orientation, role)

    def roleNames(self) -> dict[int, bytes]:
        """사용자 정의 역할 이름 반환"""
        return {
            Qt.DisplayRole: b"display",
            Qt.ToolTipRole: b"tooltip",
            Qt.DecorationRole: b"decoration",
            Qt.FontRole: b"font",
            Qt.BackgroundRole: b"background",
            Qt.ForegroundRole: b"foreground",
            self.FilePathRole: b"filePath",
            self.FileNameRole: b"fileName",
            self.FileSizeRole: b"fileSize",
            self.FileTypeRole: b"fileType",
            self.MediaTypeRole: b"mediaType",
            self.MediaQualityRole: b"mediaQuality",
            self.MediaSourceRole: b"mediaSource",
            self.ProcessingFlagRole: b"processingFlag",
            self.HasMetadataRole: b"hasMetadata",
            self.MetadataQualityRole: b"metadataQuality",
            self.TMDBMatchRole: b"tmdbMatch",
            self.LastModifiedRole: b"lastModified",
            self.CustomDataRole: b"customData",
        }

    # 데이터 관리 메서드들
    def set_media_files(self, media_files: list[MediaFile]):
        """미디어 파일 목록 설정"""
        self.beginResetModel()

        self._media_files = media_files.copy()
        self._apply_filters_and_sort()

        self.endResetModel()
        self.model_reset.emit()

        self.logger.info(f"미디어 파일 목록 설정 완료: {len(media_files)}개 파일")

    def add_media_file(self, media_file: MediaFile):
        """미디어 파일 추가"""
        if media_file in self._media_files:
            return

        self.beginInsertRows(QModelIndex(), len(self._media_files), len(self._media_files))

        self._media_files.append(media_file)
        self._apply_filters_and_sort()

        self.endInsertRows()
        self.data_changed.emit()

        self.logger.info(f"미디어 파일 추가: {media_file.file_name}")

    def remove_media_file(self, media_file: MediaFile):
        """미디어 파일 제거"""
        try:
            index = self._media_files.index(media_file)

            self.beginRemoveRows(QModelIndex(), index, index)

            self._media_files.pop(index)
            self._apply_filters_and_sort()

            self.endRemoveRows()
            self.data_changed.emit()

            self.logger.info(f"미디어 파일 제거: {media_file.file_name}")

        except ValueError:
            self.logger.warning(f"제거할 미디어 파일을 찾을 수 없음: {media_file.file_name}")

    def update_media_file(self, media_file: MediaFile):
        """미디어 파일 업데이트"""
        try:
            index = self._media_files.index(media_file)

            # 데이터 변경 알림
            model_index = self.index(index)
            self.dataChanged.emit(model_index, model_index)
            self.data_changed.emit()

            self.logger.info(f"미디어 파일 업데이트: {media_file.file_name}")

        except ValueError:
            self.logger.warning(f"업데이트할 미디어 파일을 찾을 수 없음: {media_file.file_name}")

    def clear(self):
        """모든 데이터 제거"""
        if not self._media_files:
            return

        self.beginResetModel()

        self._media_files.clear()
        self._filtered_files.clear()
        self._is_filtered = False

        self.endResetModel()
        self.model_reset.emit()

        self.logger.info("미디어 파일 목록 초기화 완료")

    # 필터링 메서드들
    def set_filter(self, key: str, value: Any):
        """필터 설정"""
        if value is None or value == "":
            self._filters.pop(key, None)
        else:
            self._filters[key] = value

        self._apply_filters_and_sort()
        self.logger.info(f"필터 설정: {key} = {value}")

    def clear_filters(self):
        """모든 필터 제거"""
        if not self._filters:
            return

        self._filters.clear()
        self._apply_filters_and_sort()

        self.logger.info("모든 필터 제거 완료")

    def get_filtered_count(self) -> int:
        """필터링된 파일 수 반환"""
        return len(self._filtered_files) if self._is_filtered else len(self._media_files)

    def get_total_count(self) -> int:
        """전체 파일 수 반환"""
        return len(self._media_files)

    # 정렬 메서드들
    def set_sort_key(self, key: str):
        """정렬 키 설정"""
        if self._sort_key != key:
            self._sort_key = key
            self._apply_filters_and_sort()
            self.logger.info(f"정렬 키 설정: {key}")

    def set_sort_order(self, order: Qt.SortOrder):
        """정렬 순서 설정"""
        if self._sort_order != order:
            self._sort_order = order
            self._apply_filters_and_sort()
            self.logger.info(f"정렬 순서 설정: {order}")

    def get_sort_key(self) -> str:
        """현재 정렬 키 반환"""
        return self._sort_key

    def get_sort_order(self) -> Qt.SortOrder:
        """현재 정렬 순서 반환"""
        return self._sort_order

    # 검색 메서드들
    def find_files_by_name(self, name_pattern: str) -> list[MediaFile]:
        """파일명으로 파일 검색"""
        import re

        try:
            pattern = re.compile(name_pattern, re.IGNORECASE)
            return [f for f in self._media_files if pattern.search(f.file_name)]
        except re.error:
            self.logger.error(f"잘못된 정규식 패턴: {name_pattern}")
            return []

    def find_files_by_type(self, media_type: MediaType) -> list[MediaFile]:
        """미디어 유형으로 파일 검색"""
        return [f for f in self._media_files if f.media_type == media_type]

    def find_files_by_quality(self, quality: MediaQuality) -> list[MediaFile]:
        """품질로 파일 검색"""
        return [f for f in self._media_files if f.media_quality == quality]

    def find_files_with_metadata(self, has_metadata: bool = True) -> list[MediaFile]:
        """메타데이터 보유 여부로 파일 검색"""
        return [f for f in self._media_files if (f.metadata is not None) == has_metadata]

    # 통계 메서드들
    def get_file_type_distribution(self) -> dict[str, int]:
        """파일 유형별 분포 반환"""
        distribution = {}
        for file in self._media_files:
            file_type = file.file_type.lower()
            distribution[file_type] = distribution.get(file_type, 0) + 1
        return distribution

    def get_media_type_distribution(self) -> dict[str, int]:
        """미디어 유형별 분포 반환"""
        distribution = {}
        for file in self._media_files:
            if file.media_type:
                media_type = file.media_type.value
                distribution[media_type] = distribution.get(media_type, 0) + 1
        return distribution

    def get_total_size(self) -> int:
        """전체 파일 크기 반환"""
        return sum(f.file_size for f in self._media_files)

    def get_average_file_size(self) -> float:
        """평균 파일 크기 반환"""
        if not self._media_files:
            return 0.0
        return self.get_total_size() / len(self._media_files)

    # 내부 헬퍼 메서드들
    def _get_media_file_at_index(self, row: int) -> MediaFile | None:
        """지정된 행의 미디어 파일 반환"""
        files = self._filtered_files if self._is_filtered else self._media_files
        if 0 <= row < len(files):
            return files[row]
        return None

    def _apply_filters_and_sort(self):
        """필터와 정렬 적용"""
        # 필터 적용
        if self._filters:
            self._filtered_files = self._apply_filters(self._media_files)
            self._is_filtered = True
        else:
            self._filtered_files = self._media_files.copy()
            self._is_filtered = False

        # 정렬 적용
        self._sort_files(self._filtered_files)

    def _apply_filters(self, files: list[MediaFile]) -> list[MediaFile]:
        """필터 적용"""
        filtered_files = files.copy()

        for key, value in self._filters.items():
            if key == "name":
                filtered_files = [f for f in filtered_files if value.lower() in f.file_name.lower()]
            elif key == "type":
                filtered_files = [f for f in filtered_files if f.file_type.lower() == value.lower()]
            elif key == "media_type":
                filtered_files = [
                    f for f in filtered_files if f.media_type and f.media_type.value == value
                ]
            elif key == "quality":
                filtered_files = [
                    f for f in filtered_files if f.media_quality and f.media_quality.value == value
                ]
            elif key == "has_metadata":
                filtered_files = [f for f in filtered_files if (f.metadata is not None) == value]
            elif key == "min_size":
                filtered_files = [f for f in filtered_files if f.file_size >= value]
            elif key == "max_size":
                filtered_files = [f for f in filtered_files if f.file_size <= value]

        return filtered_files

    def _sort_files(self, files: list[MediaFile]):
        """파일 정렬"""
        reverse = self._sort_order == Qt.DescendingOrder

        if self._sort_key == "name":
            files.sort(key=lambda f: f.file_name.lower(), reverse=reverse)
        elif self._sort_key == "size":
            files.sort(key=lambda f: f.file_size, reverse=reverse)
        elif self._sort_key == "type":
            files.sort(key=lambda f: f.file_type.lower(), reverse=reverse)
        elif self._sort_key == "modified":
            files.sort(key=lambda f: f.last_modified or 0, reverse=reverse)
        elif self._sort_key == "metadata_quality":
            files.sort(
                key=lambda f: f.metadata.quality_score if f.metadata else 0.0, reverse=reverse
            )
        else:
            # 기본값: 이름으로 정렬
            files.sort(key=lambda f: f.file_name.lower(), reverse=reverse)

    def _create_tooltip(self, media_file: MediaFile) -> str:
        """파일 툴팁 생성"""
        tooltip_parts = [
            f"파일명: {media_file.file_name}",
            f"경로: {media_file.file_path}",
            f"크기: {self._format_file_size(media_file.file_size)}",
            f"유형: {media_file.file_type}",
        ]

        if media_file.media_type:
            tooltip_parts.append(f"미디어 유형: {media_file.media_type.value}")

        if media_file.media_quality:
            tooltip_parts.append(f"품질: {media_file.media_quality.value}")

        if media_file.metadata:
            tooltip_parts.append(f"메타데이터 품질: {media_file.metadata.quality_score:.1f}%")

        if media_file.last_modified:
            tooltip_parts.append(f"수정일: {media_file.last_modified}")

        return "\n".join(tooltip_parts)

    def _format_file_size(self, size_bytes: int) -> str:
        """파일 크기 포맷팅"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        if size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _get_file_icon(self, media_file: MediaFile):
        """파일 아이콘 반환"""
        # TODO: 실제 아이콘 구현
        return

    def _get_file_font(self, media_file: MediaFile) -> QFont:
        """파일 폰트 반환"""
        font = QFont()

        # 메타데이터가 있는 파일은 굵게 표시
        if media_file.metadata:
            font.setBold(True)

        # 처리 중인 파일은 기울임체로 표시
        if media_file.processing_flag == ProcessingFlag.PROCESSING:
            font.setItalic(True)

        return font

    def _get_file_background(self, media_file: MediaFile) -> QColor:
        """파일 배경색 반환"""
        # 처리 중인 파일은 노란색 배경
        if media_file.processing_flag == ProcessingFlag.PROCESSING:
            return QColor(255, 255, 200)

        # 오류가 있는 파일은 빨간색 배경
        if media_file.processing_flag == ProcessingFlag.ERROR:
            return QColor(255, 200, 200)

        # 메타데이터 품질이 낮은 파일은 주황색 배경
        if media_file.metadata and media_file.metadata.quality_score < 50:
            return QColor(255, 220, 200)

        return QColor()

    def _get_file_foreground(self, media_file: MediaFile) -> QColor:
        """파일 전경색 반환"""
        # 기본 검은색
        return QColor()

    # 이벤트 핸들러들
    def _on_files_scanned(self, event):
        """파일 스캔 이벤트 처리"""
        try:
            # 스캔된 파일들로 모델 업데이트
            if event.status == "completed":
                self.set_media_files(event.found_files)

        except Exception as e:
            self.logger.error(f"파일 스캔 이벤트 처리 중 오류 발생: {e}")

    def _on_media_file_updated(self, event):
        """미디어 파일 업데이트 이벤트 처리"""
        try:
            # 해당 파일 업데이트
            self.update_media_file(event.media_file)

        except Exception as e:
            self.logger.error(f"미디어 파일 업데이트 이벤트 처리 중 오류 발생: {e}")

    def _on_media_file_deleted(self, event):
        """미디어 파일 삭제 이벤트 처리"""
        try:
            # 해당 파일 제거
            self.remove_media_file(event.media_file)

        except Exception as e:
            self.logger.error(f"미디어 파일 삭제 이벤트 처리 중 오류 발생: {e}")
