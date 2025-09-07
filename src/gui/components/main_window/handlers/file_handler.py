"""
MainWindowFileHandler

MainWindow에서 파일 처리 관련 로직을 담당하는 핸들러 클래스입니다.
기존 컴포넌트들과의 중복을 방지하고, ViewModel과 Service를 활용하여 파일 처리를 수행합니다.
"""

from pathlib import Path

from PyQt5.QtWidgets import QMessageBox

from src.gui.managers.anime_data_manager import AnimeDataManager, ParsedItem
from src.gui.managers.file_processing_manager import FileProcessingManager


class MainWindowFileHandler:
    """
    MainWindow의 파일 처리 로직을 담당하는 핸들러

    역할:
    - 파일 스캔 및 처리 로직
    - 기존 FileProcessingManager와 AnimeDataManager 활용
    - MainWindow에서 직접 처리하는 파일 관련 메서드들 위임

    중복 방지:
    - 파일 정리 로직은 FileOrganizationHandler가 담당
    - TMDB 검색 로직은 TMDBSearchHandler가 담당
    - 이벤트 구독은 EventHandlerManager가 담당
    """

    def __init__(
        self,
        main_window,
        file_processing_manager: FileProcessingManager,
        anime_data_manager: AnimeDataManager,
        file_parser=None,
        file_scan_service=None,
    ):
        """
        MainWindowFileHandler 초기화

        Args:
            main_window: MainWindow 인스턴스
            file_processing_manager: 파일 처리 매니저
            anime_data_manager: 애니메이션 데이터 매니저
            file_parser: 파일 파서 (기존 MainWindow에서 사용)
            file_scan_service: 파일 스캔 서비스 (기존 MainWindow에서 사용)
        """
        self.main_window = main_window
        self.file_processing_manager = file_processing_manager
        self.anime_data_manager = anime_data_manager
        self.file_parser = file_parser
        self.file_scan_service = file_scan_service

        # 스캔 상태 관리
        self.scanning = False
        self.progress = 0
        self.current_scan_id = None

        # TMDB 검색 상태
        self._tmdb_search_started = False

    def process_selected_files(self, file_paths: list[str]) -> None:
        """
        선택된 파일들을 처리

        Args:
            file_paths: 처리할 파일 경로 리스트
        """
        if not file_paths:
            self.main_window.update_status_bar("처리할 파일이 없습니다.")
            return

        print(f"🔍 [MainWindowFileHandler] {len(file_paths)}개 파일 처리 시작")

        parsed_items = []

        for file_path in file_paths:
            try:
                # 파일 존재 확인
                if not Path(file_path).exists():
                    print(f"⚠️ 파일이 존재하지 않음: {file_path}")
                    continue

                # 비디오 파일 크기 확인 (1MB 미만 제외 - 더미 파일 방지)
                try:
                    file_size = Path(file_path).stat().st_size
                    if file_size < 1024 * 1024:  # 1MB 미만
                        print(
                            f"⚠️ 비디오 파일 크기가 너무 작음 (제외): {Path(file_path).name} ({file_size} bytes)"
                        )
                        print(f"⚠️ 제외됨: {Path(file_path).name} (크기: {file_size} bytes)")
                        continue
                except OSError:
                    print(f"⚠️ 파일 크기 확인 실패 (제외): {Path(file_path).name}")
                    print(f"⚠️ 제외됨: {Path(file_path).name} (파일 접근 불가)")
                    continue

                # 파일 파싱
                print(f"🔍 파싱 시작: {Path(file_path).name}")
                parsed_metadata = self.file_parser.parse_filename(file_path)

                if parsed_metadata and parsed_metadata.title:
                    # 파싱된 항목 생성
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
                    parsed_items.append(parsed_item)

                    # 활동 로그 업데이트
                    log_message = f"✅ {Path(file_path).name} - {parsed_metadata.title} S{parsed_item.season:02d}E{parsed_item.episode:02d}"
                    print(log_message)

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
                    self.main_window.update_status_bar(f"파일명 파싱 실패: {Path(file_path).name}")

            except Exception as e:
                print(f"❌ 파일 처리 오류: {file_path} - {e}")
                # 에러 발생 시
                parsed_item = ParsedItem(
                    sourcePath=file_path,
                    detectedTitle="Error",
                    title="Error",
                    status="error",
                    parsingConfidence=0.0,
                )
                parsed_items.append(parsed_item)
                self.main_window.update_status_bar(
                    f"파일 처리 오류: {Path(file_path).name} - {str(e)}"
                )

        # 파싱된 항목들을 데이터 관리자에 추가
        if parsed_items:
            self.anime_data_manager.add_items(parsed_items)

            # 그룹화 수행
            self.anime_data_manager.group_similar_titles()
            self.anime_data_manager.display_grouped_results()

            # 통계 업데이트
            stats = self.anime_data_manager.get_stats()
            if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                self.main_window.left_panel.update_stats(
                    stats["total"], stats["parsed"], stats["pending"], stats["groups"]
                )

            # 테이블에 결과 표시
            if hasattr(self.main_window, "update_results_display"):
                self.main_window.update_results_display()

            # 상태바 업데이트
            self.main_window.update_status_bar(f"파일 처리 완료: {len(parsed_items)}개 파일 파싱됨")
        else:
            self.main_window.update_status_bar("파일 처리 완료: 파싱된 파일 없음")

    def start_scan(self) -> None:
        """
        스캔 시작

        MainWindow의 source_files와 source_directory를 확인하여
        적절한 스캔 방법을 선택합니다.
        """
        if not self.main_window.source_files and not self.main_window.source_directory:
            QMessageBox.warning(self.main_window, "경고", "먼저 소스 파일이나 폴더를 선택해주세요.")
            return

        self.scanning = True
        self.progress = 0

        # UI 상태 업데이트
        if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
            self.main_window.left_panel.btnStart.setEnabled(False)
            self.main_window.left_panel.btnPause.setEnabled(True)

        self.main_window.update_status_bar("파일 스캔 중...", 0)

        # TMDB 검색 플래그 초기화
        self._tmdb_search_started = False

        # 실제 스캔 로직 구현
        if self.main_window.source_files:
            self.process_selected_files(self.main_window.source_files)
        elif self.main_window.source_directory:
            # 폴더 내 파일들을 찾아서 처리
            self.scan_directory(self.main_window.source_directory)

    def scan_directory(self, directory_path: str) -> None:
        """
        디렉토리 스캔

        Args:
            directory_path: 스캔할 디렉토리 경로
        """
        try:
            # 백그라운드 서비스를 통한 파일 스캔
            if self.file_scan_service:
                # 폴백: 직접 서비스 호출
                print(
                    f"🚀 [MainWindowFileHandler] 백그라운드 서비스로 디렉토리 스캔: {directory_path}"
                )
                self.current_scan_id = self.file_scan_service.scan_directory(
                    directory_path=Path(directory_path),
                    recursive=True,
                    extensions={".mkv", ".mp4", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"},
                    min_file_size=1024 * 1024,  # 1MB
                    max_file_size=50 * 1024 * 1024 * 1024,  # 50GB
                )
                print(f"🆔 [MainWindowFileHandler] 백그라운드 작업 ID: {self.current_scan_id}")

                # UI 상태 업데이트
                self.main_window.update_status_bar("백그라운드에서 파일 스캔 중...", 0)
            else:
                # FileScanService를 사용할 수 없는 경우
                print("❌ [MainWindowFileHandler] FileScanService를 사용할 수 없습니다")
                self.main_window.show_error_message("파일 스캔 서비스를 사용할 수 없습니다")
                self.main_window.update_status_bar("파일 스캔 서비스를 사용할 수 없습니다", 0)

        except Exception as e:
            self.main_window.show_error_message(f"디렉토리 스캔 오류: {str(e)}")
            print(f"❌ [MainWindowFileHandler] 디렉토리 스캔 오류: {e}")
            # Service 실패 시 사용자에게 알림
            self.main_window.update_status_bar("파일 스캔에 실패했습니다", 0)

    def _scan_directory_legacy_deprecated(self, directory_path: str) -> None:
        """
        기존 방식 디렉토리 스캔 (더 이상 사용되지 않음)

        DEPRECATED: FileScanService를 사용하세요.
        이 메서드는 향후 제거될 예정입니다.

        Args:
            directory_path: 스캔할 디렉토리 경로
        """
        try:
            video_extensions = (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm")
            video_files = []

            for file_path in Path(directory_path).rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                    # 비디오 파일 크기 확인 (1MB 미만 제외 - 더미 파일 방지)
                    try:
                        file_size = file_path.stat().st_size
                        if file_size < 1024 * 1024:  # 1MB 미만
                            print(
                                f"⚠️ 비디오 파일 크기가 너무 작음 (제외): {file_path.name} ({file_size} bytes)"
                            )
                            print(f"⚠️ 제외됨: {file_path.name} (크기: {file_size} bytes)")
                            continue
                    except OSError:
                        print(f"⚠️ 파일 크기 확인 실패 (제외): {file_path.name}")
                        print(f"⚠️ 제외됨: {file_path.name} (파일 접근 불가)")
                        continue

                    video_files.append(str(file_path))

            if video_files:
                self.main_window.update_status_bar(
                    f"디렉토리에서 {len(video_files)}개 비디오 파일 발견"
                )
                self.process_selected_files(video_files)
            else:
                self.main_window.update_status_bar("디렉토리에서 비디오 파일을 찾을 수 없습니다")

        except Exception as e:
            self.main_window.update_status_bar(f"디렉토리 스캔 오류: {str(e)}")
            print(f"디렉토리 스캔 오류: {e}")

    def stop_scan(self) -> None:
        """
        스캔 중지

        ViewModel이나 Service를 통해 스캔을 중지합니다.
        """
        try:
            # 비즈니스 로직은 ViewModel에서 처리
            if hasattr(self.main_window, "view_model") and self.main_window.view_model:
                print("📋 [MainWindowFileHandler] ViewModel을 통한 스캔 중지")
                self.main_window.view_model.stop_current_scan()
            else:
                # 폴백: 직접 서비스 호출
                self.scanning = False

                # 새로운 FileScanService의 스캔 취소 시도
                if (
                    self.file_scan_service
                    and hasattr(self, "current_scan_id")
                    and self.current_scan_id
                ):
                    try:
                        success = self.file_scan_service.cancel_scan(self.current_scan_id)
                        if success:
                            print(
                                f"✅ [MainWindowFileHandler] 스캔 취소 요청 성공: {self.current_scan_id}"
                            )
                        else:
                            print(
                                f"⚠️ [MainWindowFileHandler] 스캔 취소 실패: {self.current_scan_id}"
                            )
                    except Exception as e:
                        print(f"❌ [MainWindowFileHandler] 스캔 취소 중 오류: {e}")

                # UI 상태 업데이트
                if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                    self.main_window.left_panel.btnStart.setEnabled(True)
                    self.main_window.left_panel.btnPause.setEnabled(False)
                self.main_window.update_status_bar("스캔이 중지되었습니다")

        except Exception as e:
            print(f"❌ [MainWindowFileHandler] 스캔 중지 처리 실패: {e}")
            # 직접 UI 업데이트
            if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                self.main_window.left_panel.btnStart.setEnabled(True)
                self.main_window.left_panel.btnPause.setEnabled(False)
            self.main_window.show_error_message("스캔 중지 중 오류가 발생했습니다")

    def get_scan_status(self) -> dict:
        """
        현재 스캔 상태 반환

        Returns:
            스캔 상태 정보를 담은 딕셔너리
        """
        return {
            "scanning": self.scanning,
            "progress": self.progress,
            "current_scan_id": self.current_scan_id,
            "tmdb_search_started": self._tmdb_search_started,
        }

    def set_scan_status(self, scanning: bool, progress: int = 0) -> None:
        """
        스캔 상태 설정

        Args:
            scanning: 스캔 중 여부
            progress: 진행률 (0-100)
        """
        self.scanning = scanning
        self.progress = progress
