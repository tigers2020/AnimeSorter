"""
파일 정리 관련 로직을 담당하는 핸들러
리팩토링: 통합된 파일 조직화 서비스를 사용하여 중복 코드 제거
"""

import logging

logger = logging.getLogger(__name__)
import os
from pathlib import Path

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QDialog, QMessageBox

from src.app.file_processing_events import (FileProcessingFailedEvent,
                                            FileProcessingStartedEvent)
from src.core.services.unified_file_organization_service import (
    FileOrganizationConfig, UnifiedFileOrganizationService)
from src.gui.components.dialogs.organize_preflight_dialog import \
    OrganizePreflightDialog


class FileOrganizationHandler(QObject):
    """파일 정리 관련 로직을 담당하는 핸들러 - 리팩토링된 버전"""

    def __init__(self, main_window, event_bus=None):
        super().__init__()
        self.main_window = main_window
        self.event_bus = event_bus
        self.current_operation_id = None
        config = FileOrganizationConfig(
            safe_mode=True, backup_before_operation=True, overwrite_existing=False
        )
        self.unified_service = UnifiedFileOrganizationService(config)

    def init_preflight_system(self):
        """Preflight System 초기화"""
        try:
            from src.app import IPreflightCoordinator, get_service

            self.preflight_coordinator = get_service(IPreflightCoordinator)
            logger.info("✅ PreflightCoordinator 연결됨: %s", id(self.preflight_coordinator))
        except Exception as e:
            logger.info("⚠️ Preflight System 초기화 실패: %s", e)
            self.preflight_coordinator = None

    def start_file_organization(self):
        """파일 정리 실행 시작"""
        try:
            import time

            if hasattr(self, "_is_organizing") and self._is_organizing:
                logger.info("⚠️ 파일 정리 작업이 이미 진행 중입니다")
                self.main_window.update_status_bar("파일 정리 작업이 이미 진행 중입니다")
                return
            if hasattr(self, "_last_organization_time"):
                current_time = time.time()
                time_diff = current_time - self._last_organization_time
                if time_diff < 2.0:
                    logger.info("⚠️ 너무 빠른 연속 요청 감지 (%s초)", time_diff)
                    return
            self._is_organizing = True
            self._last_organization_time = time.time()
            if not hasattr(self.main_window, "anime_data_manager"):
                QMessageBox.warning(
                    self.main_window, "경고", "스캔된 데이터가 없습니다. 먼저 파일을 스캔해주세요."
                )
                return
            grouped_items = self.main_window.anime_data_manager.get_grouped_items()
            if not grouped_items:
                QMessageBox.warning(
                    self.main_window, "경고", "정리할 그룹이 없습니다. 먼저 파일을 스캔해주세요."
                )
                return
            if (
                not self.main_window.destination_directory
                or not Path(self.main_window.destination_directory).exists()
            ):
                QMessageBox.warning(
                    self.main_window, "경고", "대상 폴더가 설정되지 않았거나 존재하지 않습니다."
                )
                return
            reply = QMessageBox.question(
                self.main_window,
                "확인",
                f"{len(grouped_items)}개 그룹의 파일들을 정리하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.on_organize_proceed()
        except Exception as e:
            logger.info("❌ 파일 정리 실행 시작 실패: %s", e)
            QMessageBox.critical(
                self.main_window, "오류", f"파일 정리 실행 중 오류가 발생했습니다:\n{str(e)}"
            )
            self.main_window.update_status_bar(f"파일 정리 실행 실패: {str(e)}")

    def on_organize_proceed(self):
        """프리플라이트 확인 후 실제 정리 실행"""
        try:
            logger.info("🚀 파일 정리 실행 시작")
            self.main_window.update_status_bar("파일 정리 실행 중...")
            grouped_items = self.main_window.anime_data_manager.get_grouped_items()
            result = self._execute_file_organization_with_quality_separation(grouped_items)
            self.on_organization_completed(result)
        except Exception as e:
            logger.info("❌ 파일 정리 실행 실패: %s", e)
            QMessageBox.critical(
                self.main_window, "오류", f"파일 정리 실행 중 오류가 발생했습니다:\n{str(e)}"
            )
            self.main_window.update_status_bar(f"파일 정리 실행 실패: {str(e)}")

    def _execute_file_organization_with_quality_separation(self, grouped_items):
        """해상도별 격리 기능을 사용한 파일 조직화"""
        from uuid import uuid4

        from src.app.organization_events import OrganizationResult

        result = OrganizationResult()
        for name, default in [
            ("success_count", 0),
            ("error_count", 0),
            ("skip_count", 0),
            ("errors", []),
            ("skipped_files", []),
            ("cleaned_directories", 0),
            ("subtitle_count", 0),
        ]:
            if not hasattr(result, name):
                setattr(result, name, default)
        self.current_operation_id = uuid4()
        if self.event_bus:
            started_event = FileProcessingStartedEvent(
                operation_id=self.current_operation_id,
                operation_type="file_organization",
                total_files=sum(
                    len(items) for items in grouped_items.values() if isinstance(items, list)
                ),
                processing_mode="normal",
            )
            self.event_bus.publish(started_event)
        logger.info("%s", "=" * 50)
        logger.debug("🔍 DEBUG: 해상도별 격리 파일 정리 시작!")
        logger.debug("🔍 DEBUG: 총 그룹 수: %s", len(grouped_items))
        logger.info("%s", "=" * 50)
        try:
            # 해상도별 격리 기능을 사용한 파일 정리
            group_qualities = self._prepare_group_qualities(grouped_items)
            source_directories = set()
            self._process_groups_by_quality(group_qualities, result, source_directories)

            # 빈 디렉토리 정리
            logger.info("🧹 빈 디렉토리 정리를 시작합니다...")
            logger.info("🔍 정리할 소스 디렉토리들: %s", list(source_directories))
            cleaned_dirs = self._cleanup_empty_directories_from_source_dirs(source_directories)
            result.cleaned_directories = cleaned_dirs
            logger.info("✅ 빈 디렉토리 정리 완료: %s개 디렉토리 삭제", cleaned_dirs)

            # 추가로 전체 소스 디렉토리에서 빈 폴더 정리
            if hasattr(self.main_window, "source_directory") and self.main_window.source_directory:
                logger.info(
                    "🗂️ 전체 소스 디렉토리에서 빈 폴더 정리 시작: %s",
                    self.main_window.source_directory,
                )
                anime_cleaned = self._cleanup_anime_directories()
                result.cleaned_directories += anime_cleaned
                logger.info("🗑️ 전체 소스 디렉토리 정리 완료: %s개 디렉토리 삭제", anime_cleaned)

            result.total_count = result.success_count + result.error_count + result.skip_count
        except Exception as e:
            logger.info("❌ 파일 조직화 실행 실패: %s", e)
            result.error_count += 1
            result.errors.append(f"조직화 실행 실패: {str(e)}")
            if self.event_bus:
                failed_event = FileProcessingFailedEvent(
                    operation_id=self.current_operation_id,
                    error_message=str(e),
                    error_type="organization_error",
                    failed_at_step="file_organization_execution",
                    processed_files_before_failure=result.success_count,
                    total_files=sum(
                        len(items) for items in grouped_items.values() if isinstance(items, list)
                    ),
                    can_retry=True,
                )
                self.event_bus.publish(failed_event)
        logger.info("%s", "=" * 50)
        logger.debug("🔍 DEBUG: 파일 정리 최종 결과")
        return result

    def _prepare_group_qualities(self, grouped_items):
        """그룹별로 화질 정보를 준비"""
        group_qualities = {}
        for group_key, group_items in grouped_items.items():
            if not isinstance(group_items, list):
                continue
            files = []
            for item in group_items:
                if hasattr(item, "sourcePath") and Path(item.sourcePath).exists():
                    # 해상도 정보 추출
                    resolution = ""
                    if hasattr(item, "resolution") and item.resolution:
                        resolution = item.resolution
                    else:
                        # 파일명에서 해상도 추출 시도
                        filename = Path(item.sourcePath).name
                        import re

                        resolution_match = re.search(r"(\d{3,4}p)", filename, re.IGNORECASE)
                        if resolution_match:
                            resolution = resolution_match.group(1).lower()

                    files.append(
                        {
                            "item": item,
                            "source_path": item.sourcePath,
                            "normalized_path": self._norm(item.sourcePath),
                            "resolution": resolution,
                        }
                    )
            if files:
                group_qualities[group_key] = files
        return group_qualities

    def _cleanup_empty_directories_from_source_dirs(self, source_directories: set) -> int:
        """소스 디렉토리들에서 빈 디렉토리 정리"""
        cleaned_count = 0
        for source_dir in source_directories:
            try:
                if not Path(source_dir).exists():
                    continue
                cleaned_count += self._remove_empty_dirs_recursive(source_dir)
                cleaned_count += self._cleanup_parent_directories(source_dir)
            except Exception as e:
                logger.info("⚠️ 디렉토리 정리 중 오류 (%s): %s", source_dir, e)
        return cleaned_count

    def _cleanup_empty_directories_from_plans(self, organization_plans) -> int:
        """조직화 계획에서 소스 디렉토리들을 정리"""
        cleaned_count = 0
        source_directories = set()
        for plan in organization_plans:
            source_directories.add(str(plan.source_path.parent))
        for source_dir in source_directories:
            try:
                if Path(source_dir).exists():
                    cleaned_count += self._remove_empty_dirs_recursive(source_dir)
                    cleaned_count += self._cleanup_parent_directories(source_dir)
            except Exception as e:
                logger.info("⚠️ 디렉토리 정리 중 오류 (%s): %s", source_dir, e)
        return cleaned_count

    def _process_subtitle_files(self, video_path: str, target_dir: Path, result):
        """비디오 파일과 연관된 자막 파일들을 처리합니다"""
        try:
            if not hasattr(result, "subtitle_count"):
                result.subtitle_count = 0
            subtitle_files = self._find_subtitle_files(video_path)
            for subtitle_path in subtitle_files:
                try:
                    subtitle_filename = Path(subtitle_path).name
                    subtitle_target_path = target_dir / subtitle_filename
                    import shutil

                    # 대상 자막 파일이 이미 존재하면 삭제 (오버라이팅)
                    if subtitle_target_path.exists():
                        logger.info("🔄 기존 자막 파일 덮어쓰기: %s", subtitle_filename)
                        subtitle_target_path.unlink()

                    shutil.move(subtitle_path, subtitle_target_path)
                    result.subtitle_count += 1
                    logger.info("✅ 자막 이동 성공: %s", subtitle_filename)
                except Exception as e:
                    logger.info("❌ 자막 이동 실패: %s - %s", subtitle_path, e)
        except Exception as e:
            logger.info("⚠️ 자막 파일 처리 중 오류: %s", e)

    def _find_subtitle_files(self, video_path: str) -> list[str]:
        """비디오 파일과 연관된 자막 파일들을 찾습니다"""
        subtitle_files = []
        subtitle_extensions = {
            ".srt",
            ".ass",
            ".ssa",
            ".sub",
            ".vtt",
            ".idx",
            ".smi",
            ".sami",
            ".txt",
        }
        try:
            video_dir = str(Path(video_path).parent)
            video_basename = Path(video_path).stem
            for file_path_obj in Path(video_dir).iterdir():
                if not file_path_obj.is_file():
                    continue
                file_ext = file_path_obj.suffix.lower()
                if file_ext not in subtitle_extensions:
                    continue
                subtitle_basename = file_path_obj.stem
                if subtitle_basename == video_basename:
                    subtitle_files.append(str(file_path_obj))
                    continue
                if video_basename in subtitle_basename:
                    subtitle_files.append(str(file_path_obj))
                    continue
        except Exception as e:
            logger.info("⚠️ 자막 파일 검색 중 오류: %s", e)
        return subtitle_files

    def _norm(self, path: str) -> str:
        """경로 정규화: 대소문자/유니코드/중복공백 통일"""
        import re
        import unicodedata
        from pathlib import Path

        s = str(Path(path))
        s = unicodedata.normalize("NFKC", s)
        s = re.sub("[ \\t]+", " ", s)
        return s.lower()

    def _process_groups_by_quality(self, group_qualities: dict, result, source_directories: set):
        """그룹별로 화질을 분석하여 파일들을 분류하고 이동"""
        import shutil
        from pathlib import Path

        for group_key, files in group_qualities.items():
            if not files:
                continue
            logger.info("🎬 그룹 '%s' 화질 분석 시작 (%s개 파일)", group_key, len(files))
            logger.info("🧪 plan: %s items in %s", len(files), group_key)
            quality_priority = {
                "4k": 5,
                "2k": 4,
                "1440p": 3,
                "1080p": 2,
                "720p": 1,
                "480p": 0,
                "": -1,
            }
            file_qualities = []
            for file_info in files:
                resolution = file_info["resolution"]
                priority = quality_priority.get(resolution, -1)
                file_qualities.append({**file_info, "priority": priority})
            if file_qualities:
                highest_priority = max(fq["priority"] for fq in file_qualities)
                logger.info("🎯 그룹 '%s' 최고 화질 우선순위: %s", group_key, highest_priority)
                for file_info in file_qualities:
                    try:
                        item = file_info["item"]
                        source_path = file_info["source_path"]
                        normalized_path = self._norm(source_path)
                        priority = file_info["priority"]
                        resolution = file_info["resolution"]
                        logger.info("➡️ trying: %s", normalized_path)
                        if normalized_path in result._processed_sources:
                            logger.info(
                                "⏭️ [중복처리] skip-duplicate(before-move): %s", normalized_path
                            )
                            result.skip_count += 1
                            result.skipped_files.append(normalized_path)
                            continue
                        if not Path(source_path).exists():
                            logger.info(
                                "⏭️ [이동후소실] skip-missing(post-move-ghost): %s", normalized_path
                            )
                            result.skip_count += 1
                            result.skipped_files.append(normalized_path)
                            continue
                        result._processed_sources.add(normalized_path)
                        source_dir = str(Path(source_path).parent)
                        source_directories.add(source_dir)
                        safe_title = "Unknown"
                        season = 1
                        if hasattr(item, "tmdbMatch") and item.tmdbMatch and item.tmdbMatch.name:
                            raw_title = item.tmdbMatch.name
                        else:
                            raw_title = item.title or item.detectedTitle or "Unknown"
                        import re

                        safe_title = re.sub("[^a-zA-Z0-9가-힣\\s]", "", raw_title)
                        safe_title = re.sub("\\s+", " ", safe_title).strip()
                        if hasattr(item, "season") and item.season:
                            season = item.season
                        if priority == highest_priority:
                            season_folder = f"Season{season:02d}"
                            target_base_dir = (
                                Path(self.main_window.destination_directory)
                                / safe_title
                                / season_folder
                            )
                            quality_type = "고화질"
                        else:
                            season_folder = f"Season{season:02d}"
                            target_base_dir = (
                                Path(self.main_window.destination_directory)
                                / "_low res"
                                / safe_title
                                / season_folder
                            )
                            quality_type = "저화질"
                        target_base_dir.mkdir(parents=True, exist_ok=True)
                        filename = Path(source_path).name
                        target_path = target_base_dir / filename
                        try:
                            logger.info(
                                "🚚 [%s] 파일 이동 시도: %s", quality_type, Path(source_path).name
                            )
                            self._process_subtitle_files(source_path, target_base_dir, result)

                            # 대상 파일이 이미 존재하면 삭제 (오버라이팅)
                            if target_path.exists():
                                logger.info("🔄 기존 파일 덮어쓰기: %s", target_path.name)
                                target_path.unlink()

                            shutil.move(source_path, target_path)
                            logger.info(
                                "✅ [%s] 이동 성공: %s → %s/",
                                quality_type,
                                Path(source_path).name,
                                target_base_dir.name,
                            )
                            result.success_count += 1
                        except Exception as e:
                            result._processed_sources.discard(normalized_path)
                            result.error_count += 1
                            result.errors.append(f"{source_path}: {e}")
                            logger.info(
                                "❌ [%s] 이동 실패: %s - %s",
                                quality_type,
                                Path(source_path).name,
                                e,
                            )
                    except Exception as e:
                        logger.info("❌ 그룹 파일 이동 실패: %s - %s", file_info["source_path"], e)
                        result.error_count += 1
                        result.errors.append(f"{file_info['source_path']}: {e}")
                        result._processed_sources.add(file_info["normalized_path"])

    def _cleanup_empty_directories(self, source_directories: set[str]) -> int:
        """파일 이동 후 빈 디렉토리들을 정리합니다"""
        cleaned_count = 0
        for source_dir in source_directories:
            try:
                if not Path(source_dir).exists():
                    continue
                cleaned_count += self._remove_empty_dirs_recursive(source_dir)
                cleaned_count += self._cleanup_parent_directories(source_dir)
            except Exception as e:
                logger.info("⚠️ 디렉토리 정리 중 오류 (%s): %s", source_dir, e)
        return cleaned_count

    def _remove_empty_dirs_recursive(self, directory: str) -> int:
        """재귀적으로 빈 디렉토리를 삭제합니다 (하위부터 상위로)"""
        cleaned_count = 0
        try:
            directory_path = Path(directory)
            items = list(directory_path.iterdir())
            for item_path in items:
                if item_path.is_dir():
                    cleaned_count += self._remove_empty_dirs_recursive(str(item_path))
            if not list(directory_path.iterdir()):
                try:
                    directory_path.rmdir()
                    cleaned_count += 1
                    logger.info("🗑️ 빈 디렉토리 삭제: %s", directory)
                except OSError as e:
                    logger.info("⚠️ 디렉토리 삭제 실패 (%s): %s", directory, e)
        except Exception as e:
            logger.info("⚠️ 디렉토리 정리 중 오류 (%s): %s", directory, e)
        return cleaned_count

    def _cleanup_parent_directories(self, start_directory: str) -> int:
        """상위 디렉토리까지 올라가면서 빈 디렉토리를 삭제합니다 (안전 경계선 적용)"""
        cleaned_count = 0
        current_dir = Path(start_directory).parent
        import os

        system_root = Path(os.sep).resolve()
        user_home = Path.home()
        while current_dir and current_dir != current_dir.parent:
            if (
                current_dir in [system_root, user_home]
                or system_root in current_dir.parents
                or user_home in current_dir.parents
            ):
                logger.info("🛡️ 안전 경계선 도달, 상위 정리 중단: %s", current_dir)
                break
            try:
                if current_dir.exists() and not list(current_dir.iterdir()):
                    current_dir.rmdir()
                    cleaned_count += 1
                    logger.info("🗑️ 빈 상위 디렉토리 삭제: %s", current_dir)
                    current_dir = current_dir.parent
                else:
                    break
            except OSError as e:
                logger.info("⚠️ 상위 디렉토리 삭제 실패 (%s): %s", current_dir, e)
                break
        return cleaned_count

    def _cleanup_anime_directories(self) -> int:
        """애니 폴더 전체에서 빈 디렉토리들을 정리합니다"""
        cleaned_count = 0
        try:
            source_root = Path(self.main_window.source_directory)
            if not source_root.exists():
                logger.info("⚠️ 소스 디렉토리가 존재하지 않습니다")
                return 0
            logger.info("🗂️ 애니 폴더 스캔 시작: %s", source_root)
            for root, dirs, _files in os.walk(str(source_root), topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            logger.info("🗑️ 빈 폴더 삭제: %s", dir_path)
                            cleaned_count += 1
                    except Exception as e:
                        logger.info("⚠️ 폴더 삭제 실패 (%s): %s", dir_path, e)
            logger.info("🗑️ 애니 폴더 정리 완료: %s개 빈 디렉토리 삭제", cleaned_count)
        except Exception as e:
            logger.info("❌ 애니 폴더 정리 중 오류: %s", e)
        return cleaned_count

    def on_organization_completed(self, result):
        """파일 정리 완료 처리"""
        try:
            message = "파일 정리가 완료되었습니다.\n\n"
            message += "📊 결과 요약:\n"
            message += f"• 성공: {result.success_count}개 파일\n"
            message += f"• 실패: {result.error_count}개 파일\n"
            message += f"• 건너뜀: {result.skip_count}개 파일\n\n"
            if result.errors:
                message += "❌ 오류 목록:\n"
                for i, error in enumerate(result.errors[:5], 1):
                    message += f"{i}. {error}\n"
                if len(result.errors) > 5:
                    message += f"... 및 {len(result.errors) - 5}개 더\n"
                message += "\n"
            if result.skipped_files:
                message += "⏭️ 건너뛴 파일:\n"
                for i, skipped in enumerate(result.skipped_files[:3], 1):
                    message += f"{i}. {skipped}\n"
                if len(result.skipped_files) > 3:
                    message += f"... 및 {len(result.skipped_files) - 3}개 더\n"
                message += "\n"
            msg_box = QMessageBox(self.main_window)
            msg_box.setWindowTitle("파일 정리 완료")
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Information)
            palette = self.main_window.palette()
            bg_color = palette.color(palette.Window).name()
            text_color = palette.color(palette.WindowText).name()
            button_bg = palette.color(palette.Button).name()
            button_text = palette.color(palette.ButtonText).name()
            msg_box.setStyleSheet(
                f"""
                QMessageBox {{
                    background-color: {bg_color};
                    color: {text_color};
                }}
                QMessageBox QPushButton {{
                    background-color: {button_bg};
                    color: {button_text};
                    border: 1px solid {palette.color(palette.Mid).name()};
                    border-radius: 4px;
                    padding: 6px 12px;
                    min-width: 60px;
                }}
                QMessageBox QPushButton:hover {{
                    background-color: {palette.color(palette.Light).name()};
                }}
                QMessageBox QPushButton:pressed {{
                    background-color: {palette.color(palette.Dark).name()};
                }}
            """
            )
            msg_box.exec_()
            if result.success_count > 0:
                self.main_window.update_status_bar(
                    f"파일 정리 완료: {result.success_count}개 파일 이동 성공"
                )
            else:
                self.main_window.update_status_bar("파일 정리 완료 (성공한 파일 없음)")
            logger.info(
                "✅ 파일 정리 완료: 성공 %s, 실패 %s, 건너뜀 %s",
                result.success_count,
                result.error_count,
                result.skip_count,
            )
            self._is_organizing = False
        except Exception as e:
            logger.info("❌ 파일 정리 완료 처리 실패: %s", e)
            self._is_organizing = False
            self.main_window.update_status_bar(f"파일 정리 완료 처리 실패: {str(e)}")

    def commit_organization(self):
        """정리 실행"""
        self.start_file_organization()

    def simulate_organization(self):
        """정리 시뮬레이션"""
        QMessageBox.information(
            self.main_window, "시뮬레이션", "파일 이동을 시뮬레이션합니다. (구현 예정)"
        )

    def show_preview(self):
        """정리 미리보기 표시"""
        try:
            if not hasattr(self.main_window, "anime_data_manager"):
                QMessageBox.warning(
                    self.main_window, "경고", "스캔된 데이터가 없습니다. 먼저 파일을 스캔해주세요."
                )
                return
            grouped_items = self.main_window.anime_data_manager.get_grouped_items()
            if not grouped_items:
                QMessageBox.warning(
                    self.main_window,
                    "경고",
                    "미리보기할 그룹이 없습니다. 먼저 파일을 스캔해주세요.",
                )
                return
            if (
                not self.main_window.destination_directory
                or not Path(self.main_window.destination_directory).exists()
            ):
                QMessageBox.warning(
                    self.main_window, "경고", "대상 폴더가 설정되지 않았거나 존재하지 않습니다."
                )
                return
            dialog = OrganizePreflightDialog(
                grouped_items, self.main_window.destination_directory, self.main_window
            )
            dialog.setWindowTitle("정리 미리보기")
            dialog.set_preview_mode(True)
            result = dialog.exec_()
            if result == QDialog.Accepted:
                logger.info("✅ 미리보기 확인 완료")
                self.main_window.update_status_bar("미리보기 확인 완료")
            else:
                logger.info("❌ 미리보기가 취소되었습니다")
                self.main_window.update_status_bar("미리보기가 취소되었습니다")
        except Exception as e:
            logger.info("❌ 미리보기 표시 실패: %s", e)
            QMessageBox.critical(
                self.main_window, "오류", f"미리보기 표시 중 오류가 발생했습니다:\n{str(e)}"
            )
            self.main_window.update_status_bar(f"미리보기 표시 실패: {str(e)}")

    def handle_organization_started(self, event):
        """파일 정리 시작 이벤트 핸들러"""
        logger.info("🚀 [FileOrganizationHandler] 파일 정리 시작: %s", event.organization_id)
        self.main_window.update_status_bar("파일 정리 시작됨", 0)

    def handle_organization_progress(self, event):
        """파일 정리 진행률 이벤트 핸들러"""
        logger.info(
            "📊 [FileOrganizationHandler] 파일 정리 진행률: %s% - %s",
            event.progress_percent,
            event.current_step,
        )
        self.main_window.update_status_bar(
            f"파일 정리 중... {event.current_step}", event.progress_percent
        )

    def handle_organization_completed(self, event):
        """파일 정리 완료 이벤트 핸들러"""
        logger.info("✅ [FileOrganizationHandler] 파일 정리 완료: %s", event.organization_id)
        self.main_window.update_status_bar("파일 정리 완료됨", 100)
