"""
정리 컨트롤러

파일 정리 및 조직화 작업을 담당하는 컨트롤러
"""

import logging

logger = logging.getLogger(__name__)
import os
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QDialog, QMessageBox

from src.components.organize_preflight_dialog import OrganizePreflightDialog
from src.gui.components.dialogs.organize_progress_dialog import (
    OrganizeProgressDialog,
    OrganizeResult,
)
from src.interfaces.i_controller import IController
from src.interfaces.i_event_bus import Event, IEventBus


class OrganizeController(IController):
    """
    파일 정리 컨트롤러

    파일 정리 계획 검토, 실행, 결과 처리를 담당
    """

    def __init__(self, event_bus: IEventBus, parent_widget: QObject = None):
        super().__init__(event_bus)
        self.parent_widget = parent_widget
        self.logger = logging.getLogger(__name__)
        self.is_organizing = False
        self.current_operation: str | None = None
        self.destination_directory: str | None = None
        self.grouped_items: dict[str, list] = {}
        self.last_organize_result: OrganizeResult | None = None
        self.config = {
            "safe_mode": True,
            "backup_before_organize": False,
            "dry_run_first": False,
            "confirm_before_execute": True,
            "auto_cleanup_empty_dirs": True,
            "skip_existing_files": True,
        }
        self.logger.info("OrganizeController 초기화 완료")

    def initialize(self) -> None:
        """컨트롤러 초기화"""
        try:
            self._setup_event_subscriptions()
            self.logger.info("OrganizeController 초기화 완료")
        except Exception as e:
            self.logger.error(f"OrganizeController 초기화 실패: {e}")
            raise

    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            if self.is_organizing:
                self._cancel_current_operation()
            self._cleanup_event_subscriptions()
            self.logger.info("OrganizeController 정리 완료")
        except Exception as e:
            self.logger.error(f"OrganizeController 정리 실패: {e}")

    def handle_event(self, event: Event) -> None:
        """이벤트 처리"""
        try:
            if event.type == "organize_requested":
                self._handle_organize_request(event.data)
            elif event.type == "simulate_requested":
                self._handle_simulate_request(event.data)
            elif event.type == "destination_folder_selected":
                self._set_destination_directory(event.data)
            elif event.type == "grouped_items_ready":
                self._set_grouped_items(event.data)
            elif event.type == "menu_organize_triggered":
                self._start_organize_flow()
            elif event.type == "menu_simulate_triggered":
                self._start_simulate_flow()
            elif event.type == "organize_cancelled":
                self._cancel_current_operation()
        except Exception as e:
            self.logger.error(f"이벤트 처리 실패: {event.type} - {e}")

    def _setup_event_subscriptions(self) -> None:
        """이벤트 구독 설정"""
        self.event_bus.subscribe("organize_requested", self.handle_event)
        self.event_bus.subscribe("simulate_requested", self.handle_event)
        self.event_bus.subscribe("destination_folder_selected", self.handle_event)
        self.event_bus.subscribe("grouped_items_ready", self.handle_event)
        self.event_bus.subscribe("menu_organize_triggered", self.handle_event)
        self.event_bus.subscribe("menu_simulate_triggered", self.handle_event)
        self.event_bus.subscribe("organize_cancelled", self.handle_event)

    def _cleanup_event_subscriptions(self) -> None:
        """이벤트 구독 해제"""
        self.event_bus.unsubscribe("organize_requested", self.handle_event)
        self.event_bus.unsubscribe("simulate_requested", self.handle_event)
        self.event_bus.unsubscribe("destination_folder_selected", self.handle_event)
        self.event_bus.unsubscribe("grouped_items_ready", self.handle_event)
        self.event_bus.unsubscribe("menu_organize_triggered", self.handle_event)
        self.event_bus.unsubscribe("menu_simulate_triggered", self.handle_event)
        self.event_bus.unsubscribe("organize_cancelled", self.handle_event)

    def _handle_organize_request(self, data: dict[str, Any]) -> None:
        """정리 요청 처리"""
        mode = data.get("mode", "execute")
        if mode == "execute":
            self._start_organize_flow()
        elif mode == "simulate":
            self._start_simulate_flow()
        else:
            self.logger.warning(f"알 수 없는 정리 모드: {mode}")

    def _handle_simulate_request(self, data: dict[str, Any]) -> None:
        """시뮬레이션 요청 처리"""
        self._start_simulate_flow()

    def _set_destination_directory(self, directory: str) -> None:
        """대상 디렉토리 설정"""
        if Path(directory).exists():
            self.destination_directory = directory
            self.logger.info(f"대상 디렉토리 설정: {directory}")
        else:
            self.logger.warning(f"존재하지 않는 대상 디렉토리: {directory}")

    def _set_grouped_items(self, grouped_items: dict[str, list]) -> None:
        """그룹화된 아이템 설정"""
        self.grouped_items = grouped_items
        self.logger.info(f"그룹화된 아이템 설정: {len(grouped_items)}개 그룹")

    def _start_organize_flow(self) -> None:
        """파일 정리 플로우 시작"""
        try:
            if self.is_organizing:
                self.logger.warning("이미 정리 작업이 진행 중입니다")
                return
            if not self._validate_organize_prerequisites():
                return
            self.logger.info("파일 정리 플로우 시작")
            self.current_operation = "organize"
            self._show_preflight_dialog(execute_mode=True)
        except Exception as e:
            self.logger.error(f"파일 정리 플로우 시작 실패: {e}")
            self.event_bus.publish("error_occurred", f"파일 정리 시작 실패: {str(e)}")

    def _start_simulate_flow(self) -> None:
        """시뮬레이션 플로우 시작"""
        try:
            if self.is_organizing:
                self.logger.warning("이미 정리 작업이 진행 중입니다")
                return
            if not self._validate_organize_prerequisites():
                return
            self.logger.info("시뮬레이션 플로우 시작")
            self.current_operation = "simulate"
            self._show_preflight_dialog(execute_mode=False)
        except Exception as e:
            self.logger.error(f"시뮬레이션 플로우 시작 실패: {e}")
            self.event_bus.publish("error_occurred", f"시뮬레이션 시작 실패: {str(e)}")

    def _validate_organize_prerequisites(self) -> bool:
        """정리 작업 전제 조건 검증"""
        try:
            if not self.grouped_items:
                self.event_bus.publish("error_occurred", "정리할 그룹이 없습니다. 먼저 파일을 스캔해주세요.")
                return False
            valid_groups = {k: v for k, v in self.grouped_items.items() if k != "ungrouped" and v}
            if not valid_groups:
                self.event_bus.publish("error_occurred", "정리할 유효한 그룹이 없습니다.")
                return False
            if not self.destination_directory or not Path(self.destination_directory).exists():
                self.event_bus.publish("error_occurred", "대상 폴더가 설정되지 않았거나 존재하지 않습니다.")
                return False
            if not os.access(self.destination_directory, os.W_OK):
                self.event_bus.publish("error_occurred", "대상 폴더에 쓰기 권한이 없습니다.")
                return False
            return True
        except Exception as e:
            self.logger.error(f"전제 조건 검증 실패: {e}")
            self.event_bus.publish("error_occurred", f"검증 실패: {str(e)}")
            return False

    def _show_preflight_dialog(self, execute_mode: bool = True) -> None:
        """프리플라이트 다이얼로그 표시"""
        try:
            if not self.parent_widget:
                self.logger.warning("부모 위젯이 설정되지 않아 다이얼로그를 표시할 수 없습니다")
                return
            dialog = OrganizePreflightDialog(
                self.grouped_items, self.destination_directory, self.parent_widget
            )
            if not execute_mode:
                dialog.set_simulation_mode(True)
            dialog.proceed_requested.connect(lambda: self._on_preflight_proceed(execute_mode))
            dialog.cancelled.connect(self._on_preflight_cancelled)
            result = dialog.exec_()
            if result == QDialog.Accepted:
                self.logger.info("프리플라이트 확인 완료")
            else:
                self.logger.info("프리플라이트 취소됨")
                self._reset_operation_state()
        except Exception as e:
            self.logger.error(f"프리플라이트 다이얼로그 표시 실패: {e}")
            self._reset_operation_state()

    def _on_preflight_proceed(self, execute_mode: bool = True) -> None:
        """프리플라이트 확인 후 진행"""
        try:
            self.logger.info(f"{'파일 정리' if execute_mode else '시뮬레이션'} 실행 시작")
            self.is_organizing = True
            operation_name = "파일 정리" if execute_mode else "시뮬레이션"
            self.event_bus.publish("status_update", {"message": f"{operation_name} 실행 중..."})
            progress_dialog = OrganizeProgressDialog(
                self.grouped_items, self.destination_directory, self.parent_widget
            )
            if not execute_mode:
                progress_dialog.set_simulation_mode(True)
            progress_dialog.start_organization()
            result = progress_dialog.exec_()
            if result == QDialog.Accepted:
                organize_result = progress_dialog.get_result()
                if organize_result:
                    self._on_organize_completed(organize_result, execute_mode)
                else:
                    self.logger.warning("정리 결과를 가져올 수 없습니다")
                    self._on_organize_failed("결과 확인 불가")
            else:
                self.logger.info(f"{operation_name}이 취소되었습니다")
                self._on_organize_cancelled()
        except Exception as e:
            self.logger.error(f"정리 실행 실패: {e}")
            self._on_organize_failed(str(e))

    def _on_preflight_cancelled(self) -> None:
        """프리플라이트 취소 처리"""
        self.logger.info("프리플라이트가 취소되었습니다")
        self._reset_operation_state()

    def _on_organize_completed(self, result: OrganizeResult, execute_mode: bool = True) -> None:
        """정리 완료 처리"""
        try:
            self.last_organize_result = result
            operation_name = "파일 정리" if execute_mode else "시뮬레이션"
            summary = self._generate_result_summary(result, execute_mode)
            QMessageBox.information(self.parent_widget, f"{operation_name} 완료", summary)
            self.event_bus.publish(
                "organize_completed",
                {"result": result, "execute_mode": execute_mode, "summary": summary},
            )
            if result.success_count > 0:
                status_msg = f"{operation_name} 완료: {result.success_count}개 파일 처리 성공"
            else:
                status_msg = f"{operation_name} 완료 (성공한 파일 없음)"
            self.event_bus.publish("status_update", {"message": status_msg})
            self.logger.info(
                f"{operation_name} 완료: 성공 {result.success_count}, 실패 {result.error_count}"
            )
            self._reset_operation_state()
        except Exception as e:
            self.logger.error(f"정리 완료 처리 실패: {e}")
            self._on_organize_failed(str(e))

    def _on_organize_failed(self, error_message: str) -> None:
        """정리 실패 처리"""
        operation_name = "파일 정리" if self.current_operation == "organize" else "시뮬레이션"
        QMessageBox.critical(
            self.parent_widget,
            f"{operation_name} 실패",
            f"""{operation_name} 중 오류가 발생했습니다:
{error_message}""",
        )
        self.event_bus.publish(
            "organize_failed", {"error_message": error_message, "operation": self.current_operation}
        )
        self.event_bus.publish(
            "status_update", {"message": f"{operation_name} 실패: {error_message}"}
        )
        self._reset_operation_state()

    def _on_organize_cancelled(self) -> None:
        """정리 취소 처리"""
        operation_name = "파일 정리" if self.current_operation == "organize" else "시뮬레이션"
        self.event_bus.publish("organize_cancelled", {"operation": self.current_operation})
        self.event_bus.publish("status_update", {"message": f"{operation_name}이 취소되었습니다"})
        self._reset_operation_state()

    def _cancel_current_operation(self) -> None:
        """현재 작업 취소"""
        if self.is_organizing:
            self.logger.info("정리 작업 취소 요청")
            self._on_organize_cancelled()

    def _reset_operation_state(self) -> None:
        """작업 상태 초기화"""
        self.is_organizing = False
        self.current_operation = None

    def reset_state(self):
        """Reset the controller state to its initial values.

        This method resets all controller state variables and clears
        any accumulated data from previous operations.
        """
        try:
            logger.info("🔄 Resetting OrganizeController state...")

            # Reset operation state
            self._reset_operation_state()

            # Reset any other state variables if they exist
            if hasattr(self, "current_scan_id"):
                self.current_scan_id = None
            if hasattr(self, "current_organization_id"):
                self.current_organization_id = None

            logger.info("✅ OrganizeController state reset completed")

        except Exception as e:
            logger.error(f"❌ Error resetting OrganizeController state: {e}")
            import traceback

            traceback.print_exc()

    def _generate_result_summary(self, result: OrganizeResult, execute_mode: bool = True) -> str:
        """결과 요약 생성"""
        operation_name = "파일 정리" if execute_mode else "시뮬레이션"
        summary = f"{operation_name}이 완료되었습니다.\n\n"
        summary += "📊 결과 요약:\n"
        summary += f"• 성공: {result.success_count}개 파일\n"
        summary += f"• 실패: {result.error_count}개 파일\n"
        summary += f"• 건너뜀: {result.skip_count}개 파일\n"
        if hasattr(result, "cleaned_directories") and result.cleaned_directories > 0:
            summary += f"• 정리된 빈 디렉토리: {result.cleaned_directories}개\n"
        summary += "\n"
        if result.errors:
            summary += "❌ 오류 목록:\n"
            for i, error in enumerate(result.errors[:5], 1):
                summary += f"{i}. {error}\n"
            if len(result.errors) > 5:
                summary += f"... 및 {len(result.errors) - 5}개 더\n"
            summary += "\n"
        if result.skipped_files:
            summary += "⏭️ 건너뛴 파일:\n"
            for i, skipped in enumerate(result.skipped_files[:3], 1):
                summary += f"{i}. {skipped}\n"
            if len(result.skipped_files) > 3:
                summary += f"... 및 {len(result.skipped_files) - 3}개 더\n"
        return summary

    def get_organize_stats(self) -> dict[str, Any]:
        """정리 통계 반환"""
        return {
            "is_organizing": self.is_organizing,
            "current_operation": self.current_operation,
            "has_destination": self.destination_directory is not None,
            "has_grouped_items": len(self.grouped_items) > 0,
            "last_result": (
                self.last_organize_result.__dict__ if self.last_organize_result else None
            ),
        }

    def configure(self, config: dict[str, Any]) -> None:
        """설정 업데이트"""
        self.config.update(config)
        self.logger.debug(f"OrganizeController 설정 업데이트: {config}")
