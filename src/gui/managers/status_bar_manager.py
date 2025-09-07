"""
상태바 관리자 모듈

MainWindow의 상태바 관련 기능을 담당하는 매니저 클래스입니다.
"""

import sys
from pathlib import Path
from typing import Any, Optional

import psutil

# 이벤트 import 수정
from src.app.ui_events import (ErrorMessageEvent, FileCountUpdateEvent,
                              MemoryUsageUpdateEvent, ProgressUpdateEvent,
                              StatusBarUpdateEvent, SuccessMessageEvent)
from src.core.manager_base import ManagerBase, ManagerConfig, ManagerPriority


class StatusBarManager(ManagerBase):
    """상태바 관리자 클래스"""

    def __init__(self, main_window, parent=None):
        """초기화"""
        # Manager 설정 생성
        config = ManagerConfig(
            name="StatusBarManager", priority=ManagerPriority.LOW, auto_start=True, log_level="INFO"
        )

        super().__init__(config, parent)

        self.main_window = main_window
        self.event_bus = main_window.event_bus if hasattr(main_window, "event_bus") else None

    def update_status_bar(self, message: str, progress: int | None = None):
        """상태바 업데이트 - EventBus 기반으로 전환됨"""
        # Progress bar는 직접 업데이트 (None 체크 추가)
        if (
            progress is not None
            and hasattr(self.main_window, "status_progress")
            and self.main_window.status_progress
        ):
            self.main_window.status_progress.setValue(progress)

        if not self.event_bus:
            # EventBus가 없으면 기존 방식으로 fallback
            self._update_status_bar_direct(message, progress)
            return

        try:
            # StatusBarUpdateEvent 발행
            self.event_bus.publish(StatusBarUpdateEvent(message=message, progress=progress))

            # 파일 수 업데이트 (한 번만 호출)
            if hasattr(self.main_window, "anime_data_manager") and not hasattr(
                self.main_window, "_last_stats_update"
            ):
                stats = self.main_window.anime_data_manager.get_stats()
                self.event_bus.publish(FileCountUpdateEvent(count=stats["total"]))
                self.main_window._last_stats_update = True

            # 메모리 사용량 계산 (간단한 추정) - 주기적으로만 업데이트
            if (
                not hasattr(self.main_window, "_last_memory_update")
                or not self.main_window._last_memory_update
            ):
                try:
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    cpu_percent = process.cpu_percent()

                    self.event_bus.publish(
                        MemoryUsageUpdateEvent(memory_mb=memory_mb, cpu_percent=cpu_percent)
                    )
                    self.main_window._last_memory_update = True
                except Exception as e:
                    print(f"메모리 사용량 계산 실패: {e}")
                    self.event_bus.publish(MemoryUsageUpdateEvent(memory_mb=0.0))
                    self.main_window._last_memory_update = True

        except Exception as e:
            print(f"EventBus를 통한 상태바 업데이트 실패: {e}")
            # Fallback to direct update
        self._update_status_bar_direct(message, progress)

    # ManagerBase 추상 메서드 구현
    def _initialize_impl(self) -> bool:
        """구현체별 초기화 로직"""
        try:
            # 기본 초기화 로직
            self.logger.info("StatusBarManager 초기화 완료")
            return True
        except Exception as e:
            self.logger.error(f"초기화 실패: {e}")
            return False

    def _start_impl(self) -> bool:
        """구현체별 시작 로직"""
        try:
            # 시작 시 필요한 로직
            self.logger.info("StatusBarManager 시작")
            return True
        except Exception as e:
            self.logger.error(f"시작 실패: {e}")
            return False

    def _stop_impl(self) -> bool:
        """구현체별 중지 로직"""
        try:
            # 중지 시 필요한 로직
            self.logger.info("StatusBarManager 중지")
            return True
        except Exception as e:
            self.logger.error(f"중지 실패: {e}")
            return False

    def _pause_impl(self) -> bool:
        """구현체별 일시정지 로직"""
        try:
            # 일시정지 시 필요한 로직
            self.logger.info("StatusBarManager 일시정지")
            return True
        except Exception as e:
            self.logger.error(f"일시정지 실패: {e}")
            return False

    def _resume_impl(self) -> bool:
        """구현체별 재개 로직"""
        try:
            # 재개 시 필요한 로직
            self.logger.info("StatusBarManager 재개")
            return True
        except Exception as e:
            self.logger.error(f"재개 실패: {e}")
            return False

    def _get_custom_health_status(self) -> Optional[dict[str, Any]]:
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

        # 파일 수 업데이트 (한 번만 호출)
        if hasattr(self.main_window, "anime_data_manager") and not hasattr(
            self.main_window, "_last_stats_update"
        ):
            stats = self.main_window.anime_data_manager.get_stats()
            self.main_window.status_file_count.setText(f"파일: {stats['total']}")
            self.main_window._last_stats_update = True

        # 메모리 사용량 계산 (간단한 추정) - 주기적으로만 업데이트
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
                self.event_bus.publish(
                    ErrorMessageEvent(message=message, details=details, error_type=error_type)
                )
            except Exception as e:
                print(f"EventBus를 통한 오류 메시지 발행 실패: {e}")
                # Fallback
                self.update_status_bar(f"❌ {message}")
        else:
            # Fallback
            self.update_status_bar(f"❌ {message}")

    def show_success_message(self, message: str, details: str = "", auto_clear: bool = True):
        """성공 메시지 표시 - EventBus 기반"""
        if self.event_bus:
            try:
                self.event_bus.publish(
                    SuccessMessageEvent(message=message, details=details, auto_clear=auto_clear)
                )
            except Exception as e:
                print(f"EventBus를 통한 성공 메시지 발행 실패: {e}")
                # Fallback
                self.update_status_bar(f"✅ {message}")
        else:
            # Fallback
            self.update_status_bar(f"✅ {message}")

    def update_progress(self, current: int, total: int, message: str = ""):
        """진행률 업데이트 - EventBus 기반"""
        if self.event_bus:
            try:
                self.event_bus.publish(
                    ProgressUpdateEvent(current=current, total=total, message=message)
                )
            except Exception as e:
                print(f"EventBus를 통한 진행률 업데이트 실패: {e}")
                # Fallback
                if total > 0:
                    progress = int((current / total) * 100)
                    self.update_status_bar(f"{message} ({current}/{total})", progress)
                else:
                    self.update_status_bar(message)
        else:
            # Fallback
            if total > 0:
                progress = int((current / total) * 100)
                self.update_status_bar(f"{message} ({current}/{total})", progress)
            else:
                self.update_status_bar(message)
