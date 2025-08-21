"""
상태바 관리자 모듈

MainWindow의 상태바 관련 기능을 담당하는 매니저 클래스입니다.
"""

import sys
from pathlib import Path

import psutil

# 상대 경로로 수정
sys.path.append(str(Path(__file__).parent.parent.parent))
from app import (
    ErrorMessageEvent,
    FileCountUpdateEvent,
    MemoryUsageUpdateEvent,
    ProgressUpdateEvent,
    StatusBarUpdateEvent,
    SuccessMessageEvent,
)


class StatusBarManager:
    """상태바 관리자 클래스"""

    def __init__(self, main_window):
        """초기화"""
        self.main_window = main_window
        self.event_bus = main_window.event_bus if hasattr(main_window, "event_bus") else None

    def update_status_bar(self, message: str, progress: int | None = None):
        """상태바 업데이트 - EventBus 기반으로 전환됨"""
        # Progress bar는 직접 업데이트
        if progress is not None and hasattr(self.main_window, "status_progress"):
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

    def _update_status_bar_direct(self, message: str, progress: int | None = None):
        """직접 상태바 업데이트 (Fallback 용도)"""
        self.main_window.status_label.setText(message)
        if progress is not None:
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
