"""
파일 처리 컨트롤러

파일 선택, 스캔, 파싱 등 파일 처리 관련 로직을 담당하는 컨트롤러
"""

import logging
from pathlib import Path
from typing import Any

from managers.anime_data_manager import ParsedItem
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog

from core.file_parser import FileParser

from ..interfaces.i_controller import IController
from ..interfaces.i_event_bus import Event, IEventBus


class FileProcessingWorker(QThread):
    """파일 처리 워커 스레드"""

    progress_updated = pyqtSignal(int, str)  # (progress, message)
    file_processed = pyqtSignal(object)  # ParsedItem
    processing_completed = pyqtSignal(list)  # List[ParsedItem]
    error_occurred = pyqtSignal(str)  # error_message

    def __init__(self, file_parser: FileParser, file_paths: list[str]):
        super().__init__()
        self.file_parser = file_parser
        self.file_paths = file_paths
        self._should_stop = False
        self.logger = logging.getLogger(__name__)

    def run(self):
        """파일 처리 실행"""
        try:
            parsed_items = []
            total_files = len(self.file_paths)

            for i, file_path in enumerate(self.file_paths):
                if self._should_stop:
                    self.logger.info("파일 처리가 중단되었습니다")
                    break

                try:
                    # 진행률 업데이트
                    progress = int((i / total_files) * 100)
                    filename = Path(file_path).name
                    self.progress_updated.emit(progress, f"처리 중: {filename}")

                    # 파일 크기 확인 (1MB 미만 제외)
                    if not self._validate_file_size(file_path):
                        self.logger.warning(f"파일 크기가 너무 작음: {filename}")
                        continue

                    # 파일 파싱
                    parsed_metadata = self.file_parser.parse_filename(file_path)

                    if parsed_metadata and parsed_metadata.title:
                        # 성공적으로 파싱된 경우
                        parsed_item = ParsedItem(
                            sourcePath=file_path,
                            detectedTitle=parsed_metadata.title,
                            title=parsed_metadata.title,
                            season=parsed_metadata.season or 1,
                            episode=parsed_metadata.episode or 1,
                            resolution=parsed_metadata.resolution or "Unknown",
                            container=parsed_metadata.container or "Unknown",
                            codec=parsed_metadata.codec or "Unknown",
                            year=parsed_metadata.year,
                            group=parsed_metadata.group or "Unknown",
                            status="pending",
                            parsingConfidence=parsed_metadata.confidence or 0.0,
                        )

                        # 파일 크기 정보 추가
                        try:
                            file_size = Path(file_path).stat().st_size
                            parsed_item.sizeMB = file_size / (1024 * 1024)
                        except OSError:
                            parsed_item.sizeMB = 0

                        parsed_items.append(parsed_item)
                        self.file_processed.emit(parsed_item)

                        self.logger.debug(f"파싱 성공: {filename} -> {parsed_metadata.title}")

                    else:
                        # 파싱 실패
                        parsed_item = ParsedItem(
                            sourcePath=file_path,
                            detectedTitle="Unknown",
                            title="Unknown",
                            status="error",
                            parsingConfidence=0.0,
                        )
                        parsed_items.append(parsed_item)
                        self.logger.warning(f"파싱 실패: {filename}")

                except Exception as e:
                    self.logger.error(f"파일 처리 오류: {file_path} - {e}")
                    self.error_occurred.emit(f"파일 처리 오류: {Path(file_path).name} - {str(e)}")

            # 완료 신호 발송
            if not self._should_stop:
                self.progress_updated.emit(100, "처리 완료")
                self.processing_completed.emit(parsed_items)
                self.logger.info(f"파일 처리 완료: {len(parsed_items)}개 파일")

        except Exception as e:
            self.logger.error(f"파일 처리 스레드 오류: {e}")
            self.error_occurred.emit(f"파일 처리 중 오류 발생: {str(e)}")

    def stop(self):
        """처리 중단"""
        self._should_stop = True

    def _validate_file_size(self, file_path: str) -> bool:
        """파일 크기 유효성 검사"""
        try:
            file_size = Path(file_path).stat().st_size
            return file_size >= 1024 * 1024  # 1MB 이상
        except OSError:
            return False


class FileProcessingController(IController):
    """
    파일 처리 컨트롤러

    파일 선택, 스캔, 파싱 등의 파일 처리 작업 관리
    """

    def __init__(self, event_bus: IEventBus, parent_widget: QObject = None):
        super().__init__(event_bus)
        self.parent_widget = parent_widget
        self.logger = logging.getLogger(__name__)

        # 핵심 컴포넌트
        self.file_parser = None

        # 파일 처리 상태
        self.source_directory: str | None = None
        self.source_files: list[str] = []
        self.is_processing = False

        # 워커 스레드
        self.processing_worker: FileProcessingWorker | None = None

        # 처리 결과
        self.parsed_items: list[ParsedItem] = []

        # 설정
        self.config = {
            "video_extensions": (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"),
            "min_file_size": 1024 * 1024,  # 1MB
            "max_concurrent_files": 100,
        }

        self.logger.info("FileProcessingController 초기화 완료")

    def initialize(self) -> None:
        """컨트롤러 초기화"""
        try:
            # FileParser 초기화
            self.file_parser = FileParser()

            # 이벤트 구독
            self._setup_event_subscriptions()

            self.logger.info("FileProcessingController 초기화 완료")

        except Exception as e:
            self.logger.error(f"FileProcessingController 초기화 실패: {e}")
            raise

    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            # 진행 중인 작업 중단
            self.stop_processing()

            # 이벤트 구독 해제
            self.event_bus.unsubscribe("menu_open_files_triggered", self.handle_event)
            self.event_bus.unsubscribe("menu_open_folder_triggered", self.handle_event)
            self.event_bus.unsubscribe("start_scan_requested", self.handle_event)
            self.event_bus.unsubscribe("stop_scan_requested", self.handle_event)

            self.logger.info("FileProcessingController 정리 완료")

        except Exception as e:
            self.logger.error(f"FileProcessingController 정리 실패: {e}")

    def handle_event(self, event: Event) -> None:
        """이벤트 처리"""
        try:
            if event.type == "menu_open_files_triggered":
                self.choose_files()
            elif event.type == "menu_open_folder_triggered":
                self.choose_folder()
            elif event.type == "start_scan_requested":
                self.start_processing()
            elif event.type == "stop_scan_requested":
                self.stop_processing()
            elif event.type == "source_folder_selected":
                self.set_source_directory(event.data)
            elif event.type == "source_files_selected":
                self.set_source_files(event.data)

        except Exception as e:
            self.logger.error(f"이벤트 처리 실패: {event.type} - {e}")

    def _setup_event_subscriptions(self) -> None:
        """이벤트 구독 설정"""
        self.event_bus.subscribe("menu_open_files_triggered", self.handle_event)
        self.event_bus.subscribe("menu_open_folder_triggered", self.handle_event)
        self.event_bus.subscribe("start_scan_requested", self.handle_event)
        self.event_bus.subscribe("stop_scan_requested", self.handle_event)
        self.event_bus.subscribe("source_folder_selected", self.handle_event)
        self.event_bus.subscribe("source_files_selected", self.handle_event)

    def choose_files(self) -> None:
        """파일 선택 다이얼로그"""
        try:
            if not self.parent_widget:
                self.logger.warning("부모 위젯이 설정되지 않아 파일 선택을 진행할 수 없습니다")
                return

            files, _ = QFileDialog.getOpenFileNames(
                self.parent_widget,
                "파일 선택",
                "",
                "Video Files (*.mkv *.mp4 *.avi *.mov);;All Files (*)",
            )

            if files:
                self.set_source_files(files)
                self.event_bus.publish("source_files_selected", files)
                self.logger.info(f"{len(files)}개 파일 선택됨")

        except Exception as e:
            self.logger.error(f"파일 선택 실패: {e}")
            self.event_bus.publish("error_occurred", f"파일 선택 실패: {str(e)}")

    def choose_folder(self) -> None:
        """폴더 선택 다이얼로그"""
        try:
            if not self.parent_widget:
                self.logger.warning("부모 위젯이 설정되지 않아 폴더 선택을 진행할 수 없습니다")
                return

            folder = QFileDialog.getExistingDirectory(self.parent_widget, "폴더 선택")

            if folder:
                self.set_source_directory(folder)
                self.event_bus.publish("source_folder_selected", folder)
                self.logger.info(f"폴더 선택됨: {folder}")

        except Exception as e:
            self.logger.error(f"폴더 선택 실패: {e}")
            self.event_bus.publish("error_occurred", f"폴더 선택 실패: {str(e)}")

    def set_source_directory(self, directory: str) -> None:
        """소스 디렉토리 설정"""
        if Path(directory).exists():
            self.source_directory = directory
            self.source_files = []  # 디렉토리 설정 시 개별 파일 목록 초기화
            self.event_bus.publish("status_update", {"message": f"소스 폴더 설정: {directory}"})
        else:
            self.logger.warning(f"존재하지 않는 디렉토리: {directory}")

    def set_source_files(self, file_paths: list[str]) -> None:
        """소스 파일 목록 설정"""
        valid_files = [f for f in file_paths if Path(f).exists()]
        self.source_files = valid_files
        self.source_directory = None  # 개별 파일 설정 시 디렉토리 초기화

        self.event_bus.publish("status_update", {"message": f"{len(valid_files)}개 파일 선택됨"})

    def start_processing(self) -> None:
        """파일 처리 시작"""
        try:
            if self.is_processing:
                self.logger.warning("이미 파일 처리가 진행 중입니다")
                return

            # 처리할 파일 목록 준비
            files_to_process = self._prepare_file_list()

            if not files_to_process:
                self.event_bus.publish(
                    "error_occurred", "처리할 파일이 없습니다. 먼저 파일이나 폴더를 선택해주세요."
                )
                return

            if not self.file_parser:
                self.event_bus.publish("error_occurred", "FileParser가 초기화되지 않았습니다.")
                return

            self.logger.info(f"파일 처리 시작: {len(files_to_process)}개 파일")

            # 상태 업데이트
            self.is_processing = True
            self.event_bus.publish("processing_started", {"file_count": len(files_to_process)})

            # 워커 스레드 생성 및 시작
            self.processing_worker = FileProcessingWorker(self.file_parser, files_to_process)
            self.processing_worker.progress_updated.connect(self._on_progress_updated)
            self.processing_worker.file_processed.connect(self._on_file_processed)
            self.processing_worker.processing_completed.connect(self._on_processing_completed)
            self.processing_worker.error_occurred.connect(self._on_error_occurred)

            self.processing_worker.start()

        except Exception as e:
            self.logger.error(f"파일 처리 시작 실패: {e}")
            self.is_processing = False
            self.event_bus.publish("error_occurred", f"파일 처리 시작 실패: {str(e)}")

    def stop_processing(self) -> None:
        """파일 처리 중단"""
        try:
            if not self.is_processing:
                return

            if self.processing_worker and self.processing_worker.isRunning():
                self.processing_worker.stop()
                self.processing_worker.wait(3000)  # 3초 대기

                if self.processing_worker.isRunning():
                    self.processing_worker.terminate()
                    self.processing_worker.wait(1000)  # 1초 대기

            self.is_processing = False
            self.event_bus.publish("processing_stopped")
            self.logger.info("파일 처리가 중단되었습니다")

        except Exception as e:
            self.logger.error(f"파일 처리 중단 실패: {e}")

    def _prepare_file_list(self) -> list[str]:
        """처리할 파일 목록 준비"""
        if self.source_files:
            # 개별 파일 목록 사용
            return [f for f in self.source_files if self._is_video_file(f)]

        if self.source_directory:
            # 디렉토리에서 비디오 파일 검색
            video_files = []
            for file_path in Path(self.source_directory).rglob("*"):
                if file_path.is_file() and self._is_video_file(str(file_path)):
                    video_files.append(str(file_path))
            return video_files

        return []

    def _is_video_file(self, file_path: str) -> bool:
        """비디오 파일 여부 확인"""
        return file_path.lower().endswith(self.config["video_extensions"])

    def _on_progress_updated(self, progress: int, message: str) -> None:
        """진행률 업데이트 처리"""
        self.event_bus.publish("progress_update", {"value": progress})
        self.event_bus.publish("status_update", {"message": message})

    def _on_file_processed(self, parsed_item: ParsedItem) -> None:
        """개별 파일 처리 완료"""
        filename = Path(parsed_item.sourcePath).name
        if parsed_item.status != "error":
            log_message = f"✅ {filename} - {parsed_item.detectedTitle} S{parsed_item.season:02d}E{parsed_item.episode:02d}"
        else:
            log_message = f"❌ {filename} - 파싱 실패"

        self.event_bus.publish("activity_log", log_message)

    def _on_processing_completed(self, parsed_items: list[ParsedItem]) -> None:
        """전체 처리 완료"""
        self.is_processing = False
        self.parsed_items = parsed_items

        # 결과 이벤트 발행
        self.event_bus.publish(
            "processing_completed",
            {
                "parsed_items": parsed_items,
                "total_count": len(parsed_items),
                "success_count": len([item for item in parsed_items if item.status != "error"]),
                "error_count": len([item for item in parsed_items if item.status == "error"]),
            },
        )

        self.logger.info(f"파일 처리 완료: 총 {len(parsed_items)}개 파일")

    def _on_error_occurred(self, error_message: str) -> None:
        """오류 발생 처리"""
        self.event_bus.publish("error_log", error_message)
        self.logger.error(f"처리 오류: {error_message}")

    def get_processing_stats(self) -> dict[str, Any]:
        """처리 통계 반환"""
        return {
            "is_processing": self.is_processing,
            "total_files": len(self.parsed_items),
            "success_count": len([item for item in self.parsed_items if item.status != "error"]),
            "error_count": len([item for item in self.parsed_items if item.status == "error"]),
            "source_directory": self.source_directory,
            "source_files_count": len(self.source_files),
        }

    def configure(self, config: dict[str, Any]) -> None:
        """설정 업데이트"""
        self.config.update(config)
        self.logger.debug(f"FileProcessingController 설정 업데이트: {config}")
