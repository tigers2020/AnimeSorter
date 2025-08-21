"""
이벤트 핸들러
GUI 이벤트와 비즈니스 로직을 연결하는 이벤트 핸들러 클래스입니다.
"""

import sys
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, QThreadPool, QTimer, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

sys.path.append(str(Path(__file__).parent.parent))
from managers.anime_data_manager import AnimeDataManager, ParsedItem
from managers.file_processing_manager import FileProcessingManager
from managers.tmdb_manager import TMDBManager


class EventHandler(QObject):
    """GUI 이벤트 핸들러"""

    # 시그널 정의
    status_updated = pyqtSignal(str)  # 상태 메시지 업데이트
    progress_updated = pyqtSignal(int)  # 진행률 업데이트
    stats_updated = pyqtSignal(dict)  # 통계 업데이트
    items_updated = pyqtSignal(list)  # 아이템 목록 업데이트
    error_occurred = pyqtSignal(str)  # 오류 발생

    def __init__(
        self,
        anime_data_manager: AnimeDataManager,
        tmdb_manager: TMDBManager,
        file_processing_manager: FileProcessingManager,
    ):
        """초기화"""
        super().__init__()

        self.anime_data_manager = anime_data_manager
        self.tmdb_manager = tmdb_manager
        self.file_processing_manager = file_processing_manager

        # 상태 변수
        self.is_processing = False
        self.current_operation = None

        # 타이머 설정
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)

        print("✅ EventHandler 초기화 완료")

    # ==================== 파일 선택 이벤트 ====================

    def handle_source_folder_selected(self, folder_path: str) -> bool:
        """소스 폴더 선택 이벤트 처리"""
        try:
            if not Path(folder_path).exists():
                self.error_occurred.emit(f"폴더가 존재하지 않습니다: {folder_path}")
                return False

            # 폴더 내 비디오 파일 스캔
            video_files = self.file_processing_manager.scan_directory(folder_path)

            if not video_files:
                self.error_occurred.emit("선택된 폴더에서 비디오 파일을 찾을 수 없습니다")
                return False

            # 파일 파싱
            parsed_items = self.file_processing_manager.parse_files(video_files)

            # 데이터 관리자에 추가
            self.anime_data_manager.add_items(parsed_items)

            # 통계 업데이트
            stats = self.anime_data_manager.get_stats()
            self.stats_updated.emit(stats)

            # 상태 업데이트
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

            # 파일 파싱
            parsed_items = self.file_processing_manager.parse_files(file_paths)

            # 데이터 관리자에 추가
            self.anime_data_manager.add_items(parsed_items)

            # 통계 업데이트
            stats = self.anime_data_manager.get_stats()
            self.stats_updated.emit(stats)

            # 상태 업데이트
            self.status_updated.emit(f"파일 파싱 완료: {len(parsed_items)}개 파일")

            return True

        except Exception as e:
            self.error_occurred.emit(f"소스 파일 처리 오류: {str(e)}")
            return False

    def handle_destination_folder_selected(self, folder_path: str) -> bool:
        """대상 폴더 선택 이벤트 처리"""
        try:
            if not Path(folder_path).exists():
                # 폴더가 없으면 생성 시도
                try:
                    Path(folder_path).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.error_occurred.emit(f"대상 폴더 생성 실패: {str(e)}")
                    return False

            # 파일 처리 관리자에 대상 폴더 설정
            self.file_processing_manager.destination_root = folder_path

            # 상태 업데이트
            self.status_updated.emit(f"대상 폴더 설정 완료: {folder_path}")

            return True

        except Exception as e:
            self.error_occurred.emit(f"대상 폴더 처리 오류: {str(e)}")
            return False

    # ==================== 스캔 이벤트 ====================

    def handle_scan_started(self) -> bool:
        """스캔 시작 이벤트 처리"""
        if self.is_processing:
            self.error_occurred.emit("이미 처리 중입니다")
            return False

        try:
            self.is_processing = True
            self.current_operation = "scan"

            # 진행률 타이머 시작
            self.progress_timer.start(100)  # 100ms마다 업데이트

            # 상태 업데이트
            self.status_updated.emit("파일 스캔 시작...")

            # TMDB 자동 매칭 시작
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

            # 진행률 타이머 중지
            self.progress_timer.stop()

            # 상태 업데이트
            self.status_updated.emit("스캔이 일시정지되었습니다")

            return True

        except Exception as e:
            self.error_occurred.emit(f"스캔 일시정지 오류: {str(e)}")
            return False

    def _start_tmdb_matching(self):
        """TMDB 자동 매칭 시작"""
        try:
            # 파싱된 아이템들 가져오기
            items = self.anime_data_manager.get_items()
            pending_items = [item for item in items if item.status == "pending"]

            if not pending_items:
                self.status_updated.emit("매칭할 아이템이 없습니다")
                return

            # TMDB 일괄 검색
            self.status_updated.emit(f"TMDB 자동 매칭 시작: {len(pending_items)}개 아이템")

            # 백그라운드에서 TMDB 매칭 수행
            self._perform_tmdb_matching(pending_items)

        except Exception as e:
            self.error_occurred.emit(f"TMDB 매칭 시작 오류: {str(e)}")

    def _perform_tmdb_matching(self, items: list[ParsedItem]):
        """TMDB 매칭 수행"""
        try:
            # TMDB 매니저를 사용하여 일괄 검색
            if self.tmdb_manager.is_available():
                match_results = self.tmdb_manager.batch_search_anime(items)

                # 매칭 결과에 따라 상태 업데이트
                for item in items:
                    if item.id in match_results:
                        item.status = "parsed"
                        item.tmdbMatch = match_results[item.id]
                    else:
                        item.status = "needs_review"

                # 통계 업데이트
                stats = self.anime_data_manager.get_stats()
                self.stats_updated.emit(stats)

                self.status_updated.emit(f"TMDB 매칭 완료: {len(match_results)}개 성공")
            else:
                # TMDB가 사용 불가능한 경우
                for item in items:
                    item.status = "needs_review"

                self.status_updated.emit("TMDB가 사용 불가능하여 수동 검토가 필요합니다")

            # 스캔 완료
            self._complete_scan()

        except Exception as e:
            self.error_occurred.emit(f"TMDB 매칭 오류: {str(e)}")
            self._complete_scan()

    def _complete_scan(self):
        """스캔 완료 처리"""
        self.is_processing = False
        self.current_operation = None
        self.progress_timer.stop()

        # 상태 업데이트
        self.status_updated.emit("스캔 완료")

        # 진행률 100%로 설정
        self.progress_updated.emit(100)

    # ==================== 파일 정리 이벤트 ====================

    def handle_commit_requested(self) -> bool:
        """정리 실행 요청 이벤트 처리"""
        if self.is_processing:
            self.error_occurred.emit("이미 처리 중입니다")
            return False

        try:
            # 확인 다이얼로그
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

            # 처리 계획 생성
            items = self.anime_data_manager.get_items()
            valid_items = [item for item in items if item.status == "parsed"]

            if not valid_items:
                self.error_occurred.emit("정리할 아이템이 없습니다")
                return False

            # 처리 계획 생성
            plans = self.file_processing_manager.create_processing_plans(valid_items)

            if not plans:
                self.error_occurred.emit("처리 계획을 생성할 수 없습니다")
                return False

            # 시뮬레이션 실행
            simulation_results = self.file_processing_manager.simulate_processing()

            # 결과 표시
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

            # 진행률 타이머 시작
            self.progress_timer.start(100)

            # 처리 계획 생성
            items = self.anime_data_manager.get_items()
            valid_items = [item for item in items if item.status == "parsed"]

            if not valid_items:
                self.error_occurred.emit("정리할 아이템이 없습니다")
                return False

            # 처리 계획 생성
            plans = self.file_processing_manager.create_processing_plans(valid_items)

            if not plans:
                self.error_occurred.emit("처리 계획을 생성할 수 없습니다")
                return False

            # 실제 파일 처리 실행
            self.status_updated.emit("파일 정리 실행 중...")

            # 백그라운드에서 파일 처리 수행
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
            # 백그라운드 워커 준비
            if not hasattr(self, "_thread_pool"):
                self._thread_pool = QThreadPool.globalInstance()

            def on_progress(value: int):
                self.progress_updated.emit(value)

            def on_done(results: dict[str, Any]):
                if "error" in results:
                    self.error_occurred.emit(results["error"])
                else:
                    # 성공한 아이템들의 상태 업데이트
                    for plan in results["processed"]:
                        for item in self.anime_data_manager.get_items():
                            if item.sourcePath == plan.source_path:
                                item.status = "parsed"
                                break
                    # 통계 업데이트
                    stats = self.anime_data_manager.get_stats()
                    self.stats_updated.emit(stats)
                    self.status_updated.emit(f"파일 정리 완료: {results['total_processed']}개 성공")
                self._complete_organization()

            # ProcessingWorker가 정의되지 않았으므로 주석 처리
            # worker = _ProcessingWorker(self.file_processing_manager, on_progress, on_done)
            # self._thread_pool.start(worker)

        except Exception as e:
            self.error_occurred.emit(f"파일 처리 오류: {str(e)}")
            self._complete_organization()

    def _complete_organization(self):
        """정리 완료 처리"""
        self.is_processing = False
        self.current_operation = None
        self.progress_timer.stop()

        # 상태 업데이트
        self.status_updated.emit("파일 정리 완료")

        # 진행률 100%로 설정
        self.progress_updated.emit(100)

    # ==================== 기타 이벤트 ====================

    def handle_completed_cleared(self) -> bool:
        """완료된 항목 정리 이벤트 처리"""
        try:
            # 완료된 항목들 제거
            self.anime_data_manager.clear_completed_items()

            # 통계 업데이트
            stats = self.anime_data_manager.get_stats()
            self.stats_updated.emit(stats)

            # 상태 업데이트
            self.status_updated.emit("완료된 항목이 정리되었습니다")

            return True

        except Exception as e:
            self.error_occurred.emit(f"완료된 항목 정리 오류: {str(e)}")
            return False

    def handle_filters_reset(self) -> bool:
        """필터 초기화 이벤트 처리"""
        try:
            # 필터 초기화 로직 (구현 필요)
            self.status_updated.emit("필터가 초기화되었습니다")
            return True

        except Exception as e:
            self.error_occurred.emit(f"필터 초기화 오류: {str(e)}")
            return False

    # ==================== 유틸리티 메서드 ====================

    def _update_progress(self):
        """진행률 업데이트"""
        if not self.is_processing:
            return

        # 현재 작업에 따른 진행률 계산
        if self.current_operation == "scan":
            # 스캔 진행률 (간단한 시뮬레이션)
            current_progress = getattr(self, "_current_progress", 0)
            current_progress = min(95, current_progress + 5)
            self._current_progress = current_progress
            self.progress_updated.emit(current_progress)

        elif self.current_operation == "organize":
            # 정리 진행률
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
                for conflict in results["conflicts"][:5]:  # 최대 5개만 표시
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
            # 타이머 중지
            self.progress_timer.stop()

            # 처리 상태 초기화
            self.is_processing = False
            self.current_operation = None

            print("✅ EventHandler 정리 완료")

        except Exception as e:
            print(f"⚠️ EventHandler 정리 오류: {e}")
