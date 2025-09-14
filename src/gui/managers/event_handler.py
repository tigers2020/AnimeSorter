"""
이벤트 핸들러
GUI 이벤트와 비즈니스 로직을 연결하는 이벤트 핸들러 클래스입니다.
"""

import logging
import sys

logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, QThreadPool, QTimer, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

sys.path.append(str(Path(__file__).parent.parent))
from managers.anime_data_manager import AnimeDataManager, ParsedItem
from managers.tmdb_manager import TMDBManager


class EventHandler(QObject):
    """GUI 이벤트 핸들러"""

    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    stats_updated = pyqtSignal(dict)
    items_updated = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        anime_data_manager: AnimeDataManager,
        tmdb_manager: TMDBManager,
        file_organization_service=None,
    ):
        """초기화"""
        super().__init__()
        self.anime_data_manager = anime_data_manager
        self.tmdb_manager = tmdb_manager
        self.file_organization_service = file_organization_service
        self.is_processing = False
        self.current_operation = None
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
        logger.info("✅ EventHandler 초기화 완료")

    def handle_source_folder_selected(self, folder_path: str) -> bool:
        """소스 폴더 선택 이벤트 처리"""
        try:
            if not Path(folder_path).exists():
                self.error_occurred.emit(f"폴더가 존재하지 않습니다: {folder_path}")
                return False
            if not self.file_organization_service:
                self.error_occurred.emit("파일 조직화 서비스가 초기화되지 않았습니다")
                return False
            scan_result = self.file_organization_service.scanner.scan_directory(Path(folder_path))
            video_files = [str(f) for f in scan_result.files_found]
            if not video_files:
                self.error_occurred.emit("선택된 폴더에서 비디오 파일을 찾을 수 없습니다")
                return False
            from src.core.file_parser import FileParser

            file_parser = FileParser()
            parsed_items = []
            for file_path in video_files:
                try:
                    parsed_metadata = file_parser.parse_filename(Path(file_path).name)
                    from src.gui.managers.anime_data_manager import ParsedItem

                    parsed_items.append(
                        ParsedItem(
                            sourcePath=file_path,
                            title=parsed_metadata.title or "Unknown",
                            season=parsed_metadata.season,
                            episode=parsed_metadata.episode,
                            year=parsed_metadata.year,
                            status="parsed",
                        )
                    )
                except Exception as e:
                    logger.error("파일 파싱 오류: %s - %s", file_path, e)
                    continue
            self.anime_data_manager.add_items(parsed_items)
            stats = self.anime_data_manager.get_stats()
            self.stats_updated.emit(stats)
            self.status_updated.emit(f"소스 폴더 스캔 완료: {len(video_files)}개 파일")
            return True
        except Exception as e:
            self.error_occurred.emit(f"소스 폴더 처리 오류: {str(e)}")
            return False

    def handle_source_files_selected(self, file_paths: list[str]) -> bool:
        """소스 파일 선택 이벤트 처리"""
        try:
            if not file_paths:
                self.error_occurred.emit("선택된 파일이 없습니다")
                return False
            from src.core.file_parser import FileParser

            file_parser = FileParser()
            parsed_items = []
            for file_path in file_paths:
                try:
                    parsed_metadata = file_parser.parse_filename(Path(file_path).name)
                    from src.gui.managers.anime_data_manager import ParsedItem

                    parsed_items.append(
                        ParsedItem(
                            sourcePath=file_path,
                            title=parsed_metadata.title or "Unknown",
                            season=parsed_metadata.season,
                            episode=parsed_metadata.episode,
                            year=parsed_metadata.year,
                            status="parsed",
                        )
                    )
                except Exception as e:
                    logger.error("파일 파싱 오류: %s - %s", file_path, e)
                    continue
            self.anime_data_manager.add_items(parsed_items)
            stats = self.anime_data_manager.get_stats()
            self.stats_updated.emit(stats)
            self.status_updated.emit(f"파일 파싱 완료: {len(parsed_items)}개 파일")
            return True
        except Exception as e:
            self.error_occurred.emit(f"소스 파일 처리 오류: {str(e)}")
            return False

    def handle_destination_folder_selected(self, folder_path: str) -> bool:
        """대상 폴더 선택 이벤트 처리"""
        try:
            if not Path(folder_path).exists():
                try:
                    Path(folder_path).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.error_occurred.emit(f"대상 폴더 생성 실패: {str(e)}")
                    return False
            self.status_updated.emit(f"대상 폴더 설정 완료: {folder_path}")
            return True
        except Exception as e:
            self.error_occurred.emit(f"대상 폴더 처리 오류: {str(e)}")
            return False

    def handle_scan_started(self) -> bool:
        """스캔 시작 이벤트 처리"""
        if self.is_processing:
            self.error_occurred.emit("이미 처리 중입니다")
            return False
        try:
            self.is_processing = True
            self.current_operation = "scan"
            self.progress_timer.start(100)
            self.status_updated.emit("파일 스캔 시작...")
            self._start_tmdb_matching()
            return True
        except Exception as e:
            self.is_processing = False
            self.current_operation = None
            self.error_occurred.emit(f"스캔 시작 오류: {str(e)}")
            return False

    def handle_scan_paused(self) -> bool:
        """스캔 일시정지 이벤트 처리"""
        try:
            self.is_processing = False
            self.current_operation = None
            self.progress_timer.stop()
            self.status_updated.emit("스캔이 일시정지되었습니다")
            return True
        except Exception as e:
            self.error_occurred.emit(f"스캔 일시정지 오류: {str(e)}")
            return False

    def _start_tmdb_matching(self):
        """TMDB 자동 매칭 시작"""
        try:
            items = self.anime_data_manager.get_items()
            pending_items = [item for item in items if item.status == "pending"]
            if not pending_items:
                self.status_updated.emit("매칭할 아이템이 없습니다")
                return
            self.status_updated.emit(f"TMDB 자동 매칭 시작: {len(pending_items)}개 아이템")
            self._perform_tmdb_matching(pending_items)
        except Exception as e:
            self.error_occurred.emit(f"TMDB 매칭 시작 오류: {str(e)}")

    def _perform_tmdb_matching(self, items: list[ParsedItem]):
        """TMDB 매칭 수행"""
        try:
            if self.tmdb_manager.is_available():
                match_results = self.tmdb_manager.batch_search_anime(items)
                for item in items:
                    if item.id in match_results:
                        item.status = "parsed"
                        item.tmdbMatch = match_results[item.id]
                    else:
                        item.status = "needs_review"
                stats = self.anime_data_manager.get_stats()
                self.stats_updated.emit(stats)
                self.status_updated.emit(f"TMDB 매칭 완료: {len(match_results)}개 성공")
            else:
                for item in items:
                    item.status = "needs_review"
                self.status_updated.emit("TMDB가 사용 불가능하여 수동 검토가 필요합니다")
            self._complete_scan()
        except Exception as e:
            self.error_occurred.emit(f"TMDB 매칭 오류: {str(e)}")
            self._complete_scan()

    def _complete_scan(self):
        """스캔 완료 처리"""
        self.is_processing = False
        self.current_operation = None
        self.progress_timer.stop()
        self.status_updated.emit("스캔 완료")
        self.progress_updated.emit(100)

    def handle_commit_requested(self) -> bool:
        """정리 실행 요청 이벤트 처리"""
        if self.is_processing:
            self.error_occurred.emit("이미 처리 중입니다")
            return False
        try:
            reply = QMessageBox.question(
                None,
                "정리 실행 확인",
                "파일 정리를 실행하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                return self._execute_file_organization()
            self.status_updated.emit("파일 정리가 취소되었습니다")
            return False
        except Exception as e:
            self.error_occurred.emit(f"정리 실행 요청 오류: {str(e)}")
            return False

    def handle_simulate_requested(self) -> bool:
        """시뮬레이션 요청 이벤트 처리"""
        try:
            self.status_updated.emit("파일 정리 시뮬레이션 시작...")
            items = self.anime_data_manager.get_items()
            valid_items = [item for item in items if item.status == "parsed"]
            if not valid_items:
                self.error_occurred.emit("정리할 아이템이 없습니다")
                return False
            plans = []
            if not plans:
                self.error_occurred.emit("처리 계획을 생성할 수 없습니다")
                return False
            simulation_results = {}
            self._show_simulation_results(simulation_results)
            return True
        except Exception as e:
            self.error_occurred.emit(f"시뮬레이션 요청 오류: {str(e)}")
            return False

    def _execute_file_organization(self) -> bool:
        """파일 정리 실행"""
        try:
            self.is_processing = True
            self.current_operation = "organize"
            self.progress_timer.start(100)
            items = self.anime_data_manager.get_items()
            valid_items = [item for item in items if item.status == "parsed"]
            if not valid_items:
                self.error_occurred.emit("정리할 아이템이 없습니다")
                return False
            plans = []
            if not plans:
                self.error_occurred.emit("처리 계획을 생성할 수 없습니다")
                return False
            self.status_updated.emit("파일 정리 실행 중...")
            self._perform_file_processing(plans)
            return True
        except Exception as e:
            self.is_processing = False
            self.current_operation = None
            self.error_occurred.emit(f"파일 정리 실행 오류: {str(e)}")
            return False

    def _perform_file_processing(self, plans):
        """파일 처리 수행"""
        try:
            if not hasattr(self, "_thread_pool"):
                self._thread_pool = QThreadPool.globalInstance()

            def on_progress(value: int):
                self.progress_updated.emit(value)

            def on_done(results: dict[str, Any]):
                if "error" in results:
                    self.error_occurred.emit(results["error"])
                else:
                    for plan in results["processed"]:
                        for item in self.anime_data_manager.get_items():
                            if item.sourcePath == plan.source_path:
                                item.status = "parsed"
                                break
                    stats = self.anime_data_manager.get_stats()
                    self.stats_updated.emit(stats)
                    self.status_updated.emit(f"파일 정리 완료: {results['total_processed']}개 성공")
                self._complete_organization()

        except Exception as e:
            self.error_occurred.emit(f"파일 처리 오류: {str(e)}")
            self._complete_organization()

    def _complete_organization(self):
        """정리 완료 처리"""
        self.is_processing = False
        self.current_operation = None
        self.progress_timer.stop()
        self.status_updated.emit("파일 정리 완료")
        self.progress_updated.emit(100)

    def handle_completed_cleared(self) -> bool:
        """완료된 항목 정리 이벤트 처리"""
        try:
            self.anime_data_manager.clear_completed_items()
            stats = self.anime_data_manager.get_stats()
            self.stats_updated.emit(stats)
            self.status_updated.emit("완료된 항목이 정리되었습니다")
            return True
        except Exception as e:
            self.error_occurred.emit(f"완료된 항목 정리 오류: {str(e)}")
            return False

    def handle_filters_reset(self) -> bool:
        """필터 초기화 이벤트 처리"""
        try:
            self.status_updated.emit("필터가 초기화되었습니다")
            return True
        except Exception as e:
            self.error_occurred.emit(f"필터 초기화 오류: {str(e)}")
            return False

    def _update_progress(self):
        """진행률 업데이트"""
        if not self.is_processing:
            return
        if self.current_operation == "scan":
            current_progress = getattr(self, "_current_progress", 0)
            current_progress = min(95, current_progress + 5)
            self._current_progress = current_progress
            self.progress_updated.emit(current_progress)
        elif self.current_operation == "organize":
            current_progress = getattr(self, "_current_progress", 0)
            current_progress = min(95, current_progress + 10)
            self._current_progress = current_progress
            self.progress_updated.emit(current_progress)

    def _show_simulation_results(self, results: dict[str, any]):
        """시뮬레이션 결과 표시"""
        try:
            message = f"""시뮬레이션 결과:

총 파일 수: {results.get("total_files", 0)}개
총 크기: {results.get("total_size_mb", 0)}MB
예상 소요 시간: {results.get("estimated_time", 0)}초
성공: {results.get("success_count", 0)}개
충돌: {results.get("error_count", 0)}개"""
            if results.get("conflicts"):
                message += "\n\n충돌 발생 파일:"
                for conflict in results["conflicts"][:5]:
                    message += f"\n- {Path(conflict['source']).name}"
                if len(results["conflicts"]) > 5:
                    message += f"\n... 외 {len(results['conflicts']) - 5}개"
            QMessageBox.information(None, "시뮬레이션 결과", message)
        except Exception as e:
            self.error_occurred.emit(f"시뮬레이션 결과 표시 오류: {str(e)}")

    def get_current_status(self) -> dict[str, any]:
        """현재 상태 정보 반환"""
        return {
            "is_processing": self.is_processing,
            "current_operation": self.current_operation,
            "stats": self.anime_data_manager.get_stats(),
        }

    def cleanup(self):
        """정리 작업"""
        try:
            self.progress_timer.stop()
            self.is_processing = False
            self.current_operation = None
            logger.info("✅ EventHandler 정리 완료")
        except Exception as e:
            logger.warning("⚠️ EventHandler 정리 오류: %s", e)
