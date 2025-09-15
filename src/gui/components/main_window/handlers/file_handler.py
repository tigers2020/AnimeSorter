"""
MainWindowFileHandler

MainWindow에서 파일 처리 관련 로직을 담당하는 핸들러 클래스입니다.
"""

import logging

logger = logging.getLogger(__name__)
from pathlib import Path

from PyQt5.QtWidgets import QMessageBox


class MainWindowFileHandler:
    """
    MainWindow의 파일 처리 로직을 담당하는 핸들러

    역할:
    - 파일 스캔 및 처리 로직
    - 기존 FileProcessingManager와 AnimeDataManager 활용
    - MainWindow에서 직접 처리하는 파일 관련 메서드들 위임

    중복 방지:
    - 파일 정리 로직은 UnifiedFileOrganizationService가 담당
    - TMDB 검색 로직은 TMDBSearchHandler가 담당
    - 이벤트 구독은 EventHandlerManager가 담당
    """

    def __init__(self, main_window):
        """
        MainWindowFileHandler 초기화

        Args:
            main_window: MainWindow 인스턴스
        """
        self.main_window = main_window
        self.scanning = False
        self.progress = 0
        self.current_scan_id = None
        self._tmdb_search_started = False

    def process_selected_files(self, file_paths: list[str]) -> None:
        """
        선택된 파일들을 처리하고 Results View에 표시

        Args:
            file_paths: 처리할 파일 경로 리스트
        """
        if not file_paths:
            self.main_window.update_status_bar("처리할 파일이 없습니다.")
            return

        logger.info("🔍 [MainWindowFileHandler] %s개 파일 처리 시작", len(file_paths))

        # 파일 정보를 생성하여 Results View에 표시
        try:
            from pathlib import Path

            # 파일 정보를 담을 리스트
            file_items = []

            from src.core.anitopy_parser import AnitopyFileParser

            file_parser = AnitopyFileParser()

            for file_path in file_paths:
                path_obj = Path(file_path)
                if path_obj.exists():
                    # anitopy로 파일명 파싱
                    parsed_metadata = file_parser.extract_metadata(path_obj.name)
                    title = parsed_metadata.get("title") or self._extract_title_from_filename(
                        path_obj.name
                    )

                    # 기본 파일 정보 생성
                    file_info = {
                        "file_path": str(path_obj),
                        "file_name": path_obj.name,
                        "file_size": path_obj.stat().st_size,
                        "file_extension": path_obj.suffix.lower(),
                        "status": "pending",  # 기본 상태
                        "tmdb_match": None,
                        "group_title": title,  # 파싱된 제목 사용
                        "parsed_metadata": parsed_metadata,  # 파싱된 메타데이터 추가
                    }
                    file_items.append(file_info)

            # 파일들을 제목별로 그룹화
            if file_items:
                self._group_files_by_title(file_items)

                # anime_data_manager에 데이터 설정
                if (
                    hasattr(self.main_window, "anime_data_manager")
                    and self.main_window.anime_data_manager
                ):
                    # ParsedItem 객체들을 생성하여 anime_data_manager에 추가
                    from src.gui.managers.anime_data_manager import ParsedItem

                    # 기존 데이터 클리어
                    self.main_window.anime_data_manager.items.clear()

                    for file_info in file_items:
                        parsed_metadata = file_info.get("parsed_metadata", {})
                        parsed_item = ParsedItem(
                            sourcePath=file_info["file_path"],
                            filename=file_info["file_name"],
                            title=file_info["group_title"],
                            status=file_info["status"],
                            sizeMB=int(file_info["file_size"] / (1024 * 1024))
                            if file_info["file_size"] > 0
                            else 0,
                            # anitopy에서 추출한 메타데이터 추가
                            season=parsed_metadata.get("season"),
                            episode=parsed_metadata.get("episode"),
                            year=parsed_metadata.get("year"),
                            resolution=parsed_metadata.get("resolution"),
                            video_codec=parsed_metadata.get("video_codec"),
                            audio_codec=parsed_metadata.get("audio_codec"),
                            release_group=parsed_metadata.get("release_group"),
                            file_extension=parsed_metadata.get("file_extension"),
                            episode_title=parsed_metadata.get("episode_title"),
                            source=parsed_metadata.get("source"),
                            quality=parsed_metadata.get("quality"),
                            language=parsed_metadata.get("language"),
                            subtitles=parsed_metadata.get("subtitles"),
                            crc32=parsed_metadata.get("crc32"),
                            parsingConfidence=parsed_metadata.get("confidence"),
                        )
                        self.main_window.anime_data_manager.add_item(parsed_item)

                    # 그룹화 실행
                    logger.info("🔧 [MainWindowFileHandler] 파일 그룹화 실행 중...")
                    self.main_window.anime_data_manager.group_similar_titles()

                    # Results View 업데이트
                    if hasattr(self.main_window, "update_results_display"):
                        self.main_window.update_results_display()
                        logger.info("✅ Results View에 %s개 파일 표시 완료", len(file_items))
                    else:
                        logger.warning("⚠️ MainWindow에 update_results_display 메서드가 없습니다")
                else:
                    logger.warning("⚠️ MainWindow에 anime_data_manager가 없습니다")

                self.main_window.update_status_bar(f"파일 처리 완료: {len(file_items)}개 파일")
            else:
                self.main_window.update_status_bar("유효한 파일을 찾을 수 없습니다")

        except Exception as e:
            logger.error("❌ 파일 처리 중 오류 발생: %s", str(e))
            self.main_window.update_status_bar(f"파일 처리 실패: {str(e)}")

    def start_scan(self) -> None:
        """
        스캔 시작 - 간단한 버전
        """
        if not self.main_window.source_files and not self.main_window.source_directory:
            QMessageBox.warning(self.main_window, "경고", "먼저 소스 파일이나 폴더를 선택해주세요.")
            return

        self.scanning = True
        self.progress = 0
        self.main_window.update_status_bar("파일 스캔 중...", 0)

        if self.main_window.source_files:
            self.process_selected_files(self.main_window.source_files)
        elif self.main_window.source_directory:
            self.scan_directory(self.main_window.source_directory)

    def scan_directory(self, directory_path: str) -> None:
        """
        디렉토리 스캔 - 간단한 버전

        Args:
            directory_path: 스캔할 디렉토리 경로
        """
        try:
            logger.info("🚀 [MainWindowFileHandler] 디렉토리 스캔: %s", directory_path)

            # 간단한 파일 스캔
            path = Path(directory_path)
            if not path.exists():
                self.main_window.update_status_bar("디렉토리가 존재하지 않습니다", 0)
                return

            # 비디오 파일 찾기
            video_extensions = {".mkv", ".mp4", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"}
            found_files = []
            for file_path in path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                    found_files.append(str(file_path))

            logger.info("🆔 [MainWindowFileHandler] 스캔 완료: %s개 파일 발견", len(found_files))

            if found_files:
                self.process_selected_files(found_files)
                self.main_window.update_status_bar("파일 스캔 완료", 100)
            else:
                self.main_window.update_status_bar("스캔된 파일이 없습니다", 0)

        except Exception as e:
            logger.error("❌ [MainWindowFileHandler] 디렉토리 스캔 오류: %s", e)
            self.main_window.update_status_bar("파일 스캔에 실패했습니다", 0)

    def stop_scan(self) -> None:
        """
        스캔 중지 - 간단한 버전
        """
        self.scanning = False
        self.main_window.update_status_bar("스캔이 중지되었습니다")

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

    def commit_organization(self) -> None:
        """파일 정리 기능이 제거되었습니다"""
        logger.info("🔧 [MainWindowFileHandler] 파일 정리 기능이 제거됨")
        QMessageBox.information(self.main_window, "기능 제거됨", "파일 정리 기능이 제거되었습니다.")
        self.main_window.update_status_bar("파일 정리 기능이 제거됨")

    def simulate_organization(self) -> None:
        """파일 정리 시뮬레이션 기능이 제거되었습니다"""
        logger.info("🎭 [MainWindowFileHandler] 파일 정리 시뮬레이션 기능이 제거됨")
        QMessageBox.information(
            self.main_window, "기능 제거됨", "파일 정리 시뮬레이션 기능이 제거되었습니다."
        )
        self.main_window.update_status_bar("시뮬레이션 기능이 제거됨")

    def show_preview(self) -> None:
        """파일 정리 미리보기 기능이 제거되었습니다"""
        logger.info("👁️ [MainWindowFileHandler] 파일 정리 미리보기 기능이 제거됨")
        QMessageBox.information(
            self.main_window, "기능 제거됨", "파일 정리 미리보기 기능이 제거되었습니다."
        )
        self.main_window.update_status_bar("미리보기 기능이 제거됨")

    def _extract_title_from_filename(self, filename: str) -> str:
        """
        파일명에서 애니메이션 제목을 추출 (AnitopyFileParser 사용)

        Args:
            filename: 파일명

        Returns:
            추출된 제목 또는 "Unknown"
        """
        try:
            from src.core.anitopy_parser import AnitopyFileParser

            logger.info("🔍 파일명 파싱 시도: %s", filename)

            # AnitopyFileParser 인스턴스 생성 및 파싱
            parser = AnitopyFileParser()
            parsed_metadata = parser.extract_metadata(filename)

            if parsed_metadata and parsed_metadata.get("title"):
                title = parsed_metadata["title"].strip()
                logger.info(
                    "✅ AnitopyFileParser로 추출된 제목: '%s' (신뢰도: %.2f)",
                    title,
                    parsed_metadata.get("confidence", 0.0),
                )

                # 너무 짧은 제목은 제외
                if len(title) > 2:
                    return title

            # AnitopyFileParser로 파싱 실패 시 기본 추출
            import re

            name_without_ext = filename.rsplit(".", 1)[0] if "." in filename else filename
            clean_name = re.sub(r"[._\[\]()\-]", " ", name_without_ext)
            clean_name = re.sub(r"\s+", " ", clean_name).strip()

            words = clean_name.split()
            result = (words[0] if len(words) > 1 else clean_name[:20]) if words else "Unknown"

            logger.info("⚠️ FileParser 실패, 기본 추출: '%s' → '%s'", filename, result)
            return result

        except Exception as e:
            logger.warning("제목 추출 실패: %s - %s", filename, e)
            return "Unknown"

    def _group_files_by_title(self, file_items: list) -> list:
        """
        파일들을 제목별로 그룹화

        Args:
            file_items: 파일 정보 리스트

        Returns:
            그룹화된 데이터 리스트
        """
        try:
            from collections import defaultdict

            # 제목별로 파일들을 그룹화
            title_groups = defaultdict(list)

            for file_info in file_items:
                title = file_info.get("group_title", "Unknown")
                title_groups[title].append(file_info)

            # 그룹화된 데이터 생성
            grouped_items = []
            for title, items in title_groups.items():
                grouped_items.append(
                    {
                        "title": f"{title} ({len(items)}개 파일)",
                        "items": items,
                        "status": "pending",
                        "file_count": len(items),
                    }
                )

            # 파일 수가 많은 그룹부터 정렬
            grouped_items.sort(key=lambda x: x["file_count"], reverse=True)

            logger.info(
                "✅ 파일 그룹화 완료: %s개 파일 → %s개 그룹", len(file_items), len(grouped_items)
            )

            return grouped_items

        except Exception as e:
            logger.error("파일 그룹화 실패: %s", e)
            # 실패 시 모든 파일을 하나의 그룹으로
            return [
                {
                    "title": f"스캔된 파일들 ({len(file_items)}개)",
                    "items": file_items,
                    "status": "pending",
                }
            ]
