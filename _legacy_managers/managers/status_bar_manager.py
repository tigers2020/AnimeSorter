"""
상태바 관리자 모듈

MainWindow의 상태바 관련 기능을 담당하는 매니저 클래스입니다.
"""

import logging

logger = logging.getLogger(__name__)
from typing import Any

import psutil

# 기존 이벤트들은 새로운 12개 핵심 이벤트 시스템으로 대체됨
# from src.core.events import (ErrorMessageEvent, FileCountUpdateEvent,
#                                MemoryUsageUpdateEvent, ProgressUpdateEvent,
#                                StatusBarUpdateEvent, SuccessMessageEvent)
from src.core.manager_base import ManagerBase, ManagerConfig, ManagerPriority


class StatusBarManager(ManagerBase):
    """상태바 관리자 클래스"""

    def __init__(self, main_window, parent=None):
        """초기화"""
        config = ManagerConfig(
            name="StatusBarManager", priority=ManagerPriority.LOW, auto_start=True, log_level="INFO"
        )
        super().__init__(config, parent)
        self.main_window = main_window
        self.event_bus = main_window.event_bus if hasattr(main_window, "event_bus") else None

    def update_status_bar(self, message: str, progress: int | None = None):
        """상태바 업데이트 - EventBus 기반으로 전환됨"""
        if (
            progress is not None
            and hasattr(self.main_window, "status_progress")
            and self.main_window.status_progress
        ):
            self.main_window.status_progress.setValue(progress)
        if not self.event_bus:
            self._update_status_bar_direct(message, progress)
            return
        try:
            # 새로운 이벤트 시스템으로 변경 - 로그만 남김
            logger.info(f"Status bar update: {message} (progress: {progress})")
            if hasattr(self.main_window, "anime_data_manager") and not hasattr(
                self.main_window, "_last_stats_update"
            ):
                stats = self.main_window.anime_data_manager.get_stats()
                # 새로운 이벤트 시스템으로 변경 - 로그만 남김
                logger.info(f"File count update: {stats['total']}")
                self.main_window._last_stats_update = True
            if (
                not hasattr(self.main_window, "_last_memory_update")
                or not self.main_window._last_memory_update
            ):
                try:
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    cpu_percent = process.cpu_percent()
                    # 새로운 이벤트 시스템으로 변경 - 로그만 남김
                    logger.info(f"Memory usage update: {memory_mb:.2f}MB, CPU: {cpu_percent}%")
                    self.main_window._last_memory_update = True
                except Exception as e:
                    logger.info("메모리 사용량 계산 실패: %s", e)
                    # 새로운 이벤트 시스템으로 변경 - 로그만 남김
                    logger.info("Memory usage update: 0.0MB (error fallback)")
                    self.main_window._last_memory_update = True
        except Exception as e:
            logger.info("EventBus를 통한 상태바 업데이트 실패: %s", e)
        self._update_status_bar_direct(message, progress)

    def _initialize_impl(self) -> bool:
        """구현체별 초기화 로직"""
        try:
            self.logger.info("StatusBarManager 초기화 완료")
            return True
        except Exception as e:
            self.logger.error(f"초기화 실패: {e}")
            return False

    def _start_impl(self) -> bool:
        """구현체별 시작 로직"""
        try:
            self.logger.info("StatusBarManager 시작")
            return True
        except Exception as e:
            self.logger.error(f"시작 실패: {e}")
            return False

    def _stop_impl(self) -> bool:
        """구현체별 중지 로직"""
        try:
            self.logger.info("StatusBarManager 중지")
            return True
        except Exception as e:
            self.logger.error(f"중지 실패: {e}")
            return False

    def _pause_impl(self) -> bool:
        """구현체별 일시정지 로직"""
        try:
            self.logger.info("StatusBarManager 일시정지")
            return True
        except Exception as e:
            self.logger.error(f"일시정지 실패: {e}")
            return False

    def _resume_impl(self) -> bool:
        """구현체별 재개 로직"""
        try:
            self.logger.info("StatusBarManager 재개")
            return True
        except Exception as e:
            self.logger.error(f"재개 실패: {e}")
            return False

    def _get_custom_health_status(self) -> dict[str, Any] | None:
        """구현체별 건강 상태 반환"""
        return {
            "main_window_available": self.main_window is not None,
            "event_bus_available": self.event_bus is not None,
            "status_label_available": (
                hasattr(self.main_window, "status_label") if self.main_window else False
            ),
            "status_progress_available": (
                hasattr(self.main_window, "status_progress") if self.main_window else False
            ),
        }

    def _update_status_bar_direct(self, message: str, progress: int | None = None):
        """직접 상태바 업데이트 (Fallback 용도)"""
        if hasattr(self.main_window, "status_label") and self.main_window.status_label:
            self.main_window.status_label.setText(message)
        if (
            progress is not None
            and hasattr(self.main_window, "status_progress")
            and self.main_window.status_progress
        ):
            self.main_window.status_progress.setValue(progress)
        if hasattr(self.main_window, "anime_data_manager") and not hasattr(
            self.main_window, "_last_stats_update"
        ):
            stats = self.main_window.anime_data_manager.get_stats()
            self.main_window.status_file_count.setText(f"파일: {stats['total']}")
            self.main_window._last_stats_update = True
        if (
            not hasattr(self.main_window, "_last_memory_update")
            or not self.main_window._last_memory_update
        ):
            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.main_window.status_memory.setText(f"메모리: {memory_mb:.1f}MB")
                self.main_window._last_memory_update = True
            except Exception:
                self.main_window.status_memory.setText("메모리: N/A")
                self.main_window._last_memory_update = True

    def show_error_message(self, message: str, details: str = "", error_type: str = "error"):
        """오류 메시지 표시 - EventBus 기반"""
        if self.event_bus:
            try:
                # 새로운 이벤트 시스템으로 변경 - 로그만 남김
                logger.error(f"Error message: {message} (type: {error_type}, details: {details})")
            except Exception as e:
                logger.info("EventBus를 통한 오류 메시지 발행 실패: %s", e)
                self.update_status_bar(f"❌ {message}")
        else:
            self.update_status_bar(f"❌ {message}")

    def show_success_message(self, message: str, details: str = "", auto_clear: bool = True):
        """성공 메시지 표시 - EventBus 기반"""
        if self.event_bus:
            try:
                # 새로운 이벤트 시스템으로 변경 - 로그만 남김
                logger.info(
                    f"Success message: {message} (details: {details}, auto_clear: {auto_clear})"
                )
            except Exception as e:
                logger.info("EventBus를 통한 성공 메시지 발행 실패: %s", e)
                self.update_status_bar(f"✅ {message}")
        else:
            self.update_status_bar(f"✅ {message}")

    def update_progress(self, current: int, total: int, message: str = ""):
        """진행률 업데이트 - EventBus 기반"""
        if self.event_bus:
            try:
                # 새로운 이벤트 시스템으로 변경 - 로그만 남김
                logger.info(f"Progress update: {current}/{total} - {message}")
            except Exception as e:
                logger.info("EventBus를 통한 진행률 업데이트 실패: %s", e)
                if total > 0:
                    progress = int(current / total * 100)
                    self.update_status_bar(f"{message} ({current}/{total})", progress)
                else:
                    self.update_status_bar(message)
        elif total > 0:
            progress = int(current / total * 100)
            self.update_status_bar(f"{message} ({current}/{total})", progress)
        else:
            self.update_status_bar(message)
