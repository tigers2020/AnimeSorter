"""
Event Handler Manager for MainWindow

MainWindow의 모든 이벤트 핸들러를 관리하는 클래스입니다.
이벤트 처리 로직을 MainWindow에서 분리하여 단일 책임 원칙을 적용합니다.
"""

import logging

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import QWidget

from src.app import (BackupCompletedEvent, BackupFailedEvent,
                     BackupStartedEvent, CommandExecutedEvent,
                     CommandFailedEvent, CommandRedoneEvent,
                     CommandUndoneEvent, ConfirmationRequiredEvent,
                     FilesScannedEvent, MediaDataGroupingCompletedEvent,
                     MediaDataReadyEvent, OrganizationCompletedEvent,
                     OrganizationProgressEvent, OrganizationStartedEvent,
                     PreflightCompletedEvent, PreflightIssueFoundEvent,
                     PreflightStartedEvent, RedoExecutedEvent,
                     SafetyAlertEvent, SafetyStatusUpdateEvent, ScanStatus,
                     TaskCancelledEvent, TaskCompletedEvent, TaskFailedEvent,
                     TaskProgressEvent, TaskStartedEvent, UndoExecutedEvent,
                     UndoRedoStackChangedEvent)


class EventHandlerManager:
    """MainWindow의 모든 이벤트 핸들러를 관리하는 클래스"""

    def __init__(self, main_window: QWidget, event_bus):
        """EventHandlerManager 초기화"""
        self.main_window = main_window
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)

    def _delegate_or_log(
        self, handler_attr: str, handler_method: str, event, fallback_message: str
    ):
        """핸들러가 있으면 위임하고, 없으면 로그를 남기는 헬퍼 메서드"""
        if not hasattr(self.main_window, handler_attr):
            self.logger.info(fallback_message)
            return
        handler = getattr(self.main_window, handler_attr)
        if not hasattr(handler, handler_method):
            self.logger.info(fallback_message)
            return
        getattr(handler, handler_method)(event)

    def setup_event_subscriptions(self):
        """이벤트 구독 설정"""
        try:
            event_bus = self.event_bus
            event_bus.subscribe(FilesScannedEvent, self.on_files_scanned, weak_ref=False)
            self.logger.info("✅ File Scan 이벤트 구독 설정")
            event_bus.subscribe(TaskStartedEvent, self.on_task_started, weak_ref=False)
            event_bus.subscribe(TaskProgressEvent, self.on_task_progress, weak_ref=False)
            event_bus.subscribe(TaskCompletedEvent, self.on_task_completed, weak_ref=False)
            event_bus.subscribe(TaskFailedEvent, self.on_task_failed, weak_ref=False)
            event_bus.subscribe(TaskCancelledEvent, self.on_task_cancelled, weak_ref=False)
            self.logger.info("✅ Task System 이벤트 구독 설정")
            event_bus.subscribe(
                OrganizationStartedEvent, self.on_organization_started, weak_ref=False
            )
            event_bus.subscribe(
                OrganizationProgressEvent, self.on_organization_progress, weak_ref=False
            )
            event_bus.subscribe(
                OrganizationCompletedEvent, self.on_organization_completed, weak_ref=False
            )
            self.logger.info("✅ Organization System 이벤트 구독 설정")
            event_bus.subscribe(MediaDataReadyEvent, self.on_media_data_ready, weak_ref=False)
            event_bus.subscribe(
                MediaDataGroupingCompletedEvent,
                self.on_media_data_grouping_completed,
                weak_ref=False,
            )
            self.logger.info("✅ Media Data System 이벤트 구독 설정")
            self.logger.info("✅ TMDB Search System 이벤트 구독 설정 (제거됨)")
            event_bus.subscribe(
                SafetyStatusUpdateEvent, self.on_safety_status_update, weak_ref=False
            )
            event_bus.subscribe(SafetyAlertEvent, self.on_safety_alert, weak_ref=False)
            event_bus.subscribe(
                ConfirmationRequiredEvent, self.on_confirmation_required, weak_ref=False
            )
            self.logger.info("✅ Safety System 이벤트 구독 설정")
            event_bus.subscribe(BackupStartedEvent, self.on_backup_started, weak_ref=False)
            event_bus.subscribe(BackupCompletedEvent, self.on_backup_completed, weak_ref=False)
            event_bus.subscribe(BackupFailedEvent, self.on_backup_failed, weak_ref=False)
            self.logger.info("✅ Backup System 이벤트 구독 설정")
            event_bus.subscribe(CommandExecutedEvent, self.on_command_executed, weak_ref=False)
            event_bus.subscribe(CommandUndoneEvent, self.on_command_undone, weak_ref=False)
            event_bus.subscribe(CommandRedoneEvent, self.on_command_redone, weak_ref=False)
            event_bus.subscribe(CommandFailedEvent, self.on_command_failed, weak_ref=False)
            self.logger.info("✅ Command System 이벤트 구독 설정")
            event_bus.subscribe(PreflightStartedEvent, self.on_preflight_started, weak_ref=False)
            event_bus.subscribe(
                PreflightCompletedEvent, self.on_preflight_completed, weak_ref=False
            )
            event_bus.subscribe(
                PreflightIssueFoundEvent, self.on_preflight_issue_found, weak_ref=False
            )
            self.logger.info("✅ Preflight System 이벤트 구독 설정")
            # Journal 시스템 제거됨
            event_bus.subscribe(UndoExecutedEvent, self.on_undo_executed, weak_ref=False)
            event_bus.subscribe(RedoExecutedEvent, self.on_redo_executed, weak_ref=False)
            event_bus.subscribe(
                UndoRedoStackChangedEvent, self.on_undo_redo_stack_changed, weak_ref=False
            )
            self.logger.info("✅ Undo/Redo System 이벤트 구독 설정")
        except Exception as e:
            self.logger.error(f"❌ 이벤트 구독 설정 실패: {e}")

    def on_files_scanned(self, event: FilesScannedEvent):
        """파일 스캔 완료 이벤트 핸들러"""
        self.logger.info(
            f"📨 [MainWindow] 파일 스캔 이벤트 수신: {event.status.value} - {len(event.found_files)}개 파일"
        )
        self.logger.debug(f"🔍 [DEBUG] 스캔 ID: {event.scan_id}")
        self.logger.debug(f"🔍 [DEBUG] 디렉토리: {event.directory_path}")
        try:
            if event.status == ScanStatus.STARTED:
                self.main_window.update_status_bar("파일 스캔 시작됨")
                self.main_window.left_panel.update_progress(0)
            elif event.status == ScanStatus.IN_PROGRESS:
                progress = 0
                files_count = len(event.found_files)
                if files_count > 0:
                    progress = min(50, files_count // 10 * 5)
                self.main_window.left_panel.update_progress(progress)
                self.main_window.update_status_bar(f"파일 스캔 중... ({files_count}개 발견)")
            elif event.status == ScanStatus.COMPLETED:
                self.main_window.left_panel.update_progress(100)
                files_count = len(event.found_files)
                self.main_window.update_status_bar(f"스캔 완료: {files_count}개 파일 발견")
                if not event.found_files:
                    self.main_window.update_status_bar("비디오 파일을 찾을 수 없습니다")
                    return
                self.on_scan_completed(event.found_files)
            elif event.status == ScanStatus.FAILED:
                self.main_window.update_status_bar(f"스캔 실패: {event.error_message}")
                self.main_window.left_panel.update_progress(0)
            elif event.status == ScanStatus.CANCELLED:
                self.main_window.update_status_bar("스캔이 취소되었습니다")
                self.main_window.left_panel.update_progress(0)
        except Exception as e:
            self.logger.error(f"❌ 파일 스캔 이벤트 처리 실패: {e}")

    def on_scan_completed(self, found_files: list):
        """스캔 완료 후 파일 처리"""
        try:
            file_paths = [str(file_path) for file_path in found_files]
            self.main_window.process_selected_files(file_paths)
        except Exception as e:
            self.logger.error(f"❌ 스캔 완료 후 처리 실패: {e}")

    def on_task_started(self, event: TaskStartedEvent):
        """백그라운드 작업 시작 이벤트 핸들러"""
        self.logger.info(f"🚀 [MainWindow] 작업 시작: {event.task_name} (ID: {event.task_id})")
        self.main_window.update_status_bar(f"작업 시작: {event.task_name}", 0)

    def on_task_progress(self, event: TaskProgressEvent):
        """백그라운드 작업 진행률 이벤트 핸들러"""
        self.logger.info(
            f"📊 [MainWindow] 작업 진행률: {event.progress_percent}% - {event.current_step}"
        )
        self.main_window.update_status_bar(
            f"{event.current_step} ({event.items_processed}개 처리됨)", event.progress_percent
        )
        if hasattr(self.main_window, "left_panel"):
            self.main_window.left_panel.update_progress(event.progress_percent)

    def on_task_completed(self, event: TaskCompletedEvent):
        """백그라운드 작업 완료 이벤트 핸들러"""
        self.logger.info(
            f"✅ [MainWindow] 작업 완료: {event.task_name} (소요시간: {event.duration:.2f}초)"
        )
        self.main_window.update_status_bar(
            f"작업 완료: {event.task_name} ({event.items_processed}개 처리됨)", 100
        )
        if hasattr(self.main_window, "left_panel"):
            self.main_window.left_panel.update_progress(100)

    def on_task_failed(self, event: TaskFailedEvent):
        """백그라운드 작업 실패 이벤트 핸들러"""
        self.logger.error(f"❌ [MainWindow] 작업 실패: {event.task_name} - {event.error_message}")
        self.main_window.show_error_message(
            f"작업 실패: {event.task_name}", event.error_message, "task_failed"
        )

    def on_task_cancelled(self, event: TaskCancelledEvent):
        """백그라운드 작업 취소 이벤트 핸들러"""
        self.logger.info(f"🚫 [MainWindow] 작업 취소: {event.task_name} - {event.reason}")
        self.main_window.update_status_bar(f"작업 취소됨: {event.task_name}")

    def on_organization_started(self, event: OrganizationStartedEvent):
        """파일 정리 시작 이벤트 핸들러"""
        self._delegate_or_log(
            "file_organization_handler",
            "handle_organization_started",
            event,
            f"🚀 [MainWindow] 파일 정리 시작: {event.organization_id}",
        )
        if not hasattr(self.main_window, "file_organization_handler"):
            self.main_window.update_status_bar("파일 정리 시작됨", 0)

    def on_organization_progress(self, event: OrganizationProgressEvent):
        """파일 정리 진행률 이벤트 핸들러"""
        self._delegate_or_log(
            "file_organization_handler",
            "handle_organization_progress",
            event,
            f"📊 [MainWindow] 파일 정리 진행률: {event.progress_percent}% - {event.current_step}",
        )
        if not hasattr(self.main_window, "file_organization_handler"):
            self.main_window.update_status_bar(
                f"파일 정리 중... {event.current_step}", event.progress_percent
            )

    def on_organization_completed(self, event: OrganizationCompletedEvent):
        """파일 정리 완료 이벤트 핸들러"""
        self._delegate_or_log(
            "file_organization_handler",
            "handle_organization_completed",
            event,
            f"✅ [MainWindow] 파일 정리 완료: {event.organization_id}",
        )
        if not hasattr(self.main_window, "file_organization_handler"):
            self.main_window.update_status_bar("파일 정리 완료됨", 100)

    def on_media_data_ready(self, event: MediaDataReadyEvent):
        """미디어 데이터 준비 완료 이벤트 핸들러"""
        self.logger.info(
            f"📺 [MainWindow] 미디어 데이터 준비 완료: {len(event.media_files)}개 파일"
        )
        self.main_window.update_status_bar("미디어 데이터 분석 완료")

    def on_media_data_grouping_completed(self, event: MediaDataGroupingCompletedEvent):
        """미디어 데이터 그룹화 완료 이벤트 핸들러"""
        self.logger.info(f"📁 [MainWindow] 미디어 데이터 그룹화 완료: {len(event.groups)}개 그룹")
        self.main_window.update_status_bar("미디어 데이터 그룹화 완료")

    def on_safety_status_update(self, event: SafetyStatusUpdateEvent):
        """안전 시스템 상태 업데이트 이벤트 핸들러"""
        self._delegate_or_log(
            "safety_system_manager",
            "handle_safety_status_update",
            event,
            f"🛡️ [MainWindow] 안전 시스템 상태 업데이트: {event.status}",
        )

    def on_safety_alert(self, event: SafetyAlertEvent):
        """안전 시스템 경고 이벤트 핸들러"""
        self._delegate_or_log(
            "safety_system_manager",
            "handle_safety_alert",
            event,
            f"⚠️ [MainWindow] 안전 시스템 경고: {event.message}",
        )

    def on_confirmation_required(self, event: ConfirmationRequiredEvent):
        """확인 요청 이벤트 핸들러"""
        self._delegate_or_log(
            "safety_system_manager",
            "handle_confirmation_required",
            event,
            f"❓ [MainWindow] 확인 요청: {event.message}",
        )

    def on_backup_started(self, event: BackupStartedEvent):
        """백업 시작 이벤트 핸들러"""
        self._delegate_or_log(
            "safety_system_manager",
            "handle_backup_started",
            event,
            f"💾 [MainWindow] 백업 시작: {event.backup_id}",
        )

    def on_backup_completed(self, event: BackupCompletedEvent):
        """백업 완료 이벤트 핸들러"""
        self._delegate_or_log(
            "safety_system_manager",
            "handle_backup_completed",
            event,
            f"✅ [MainWindow] 백업 완료: {event.backup_id}",
        )

    def on_backup_failed(self, event: BackupFailedEvent):
        """백업 실패 이벤트 핸들러"""
        self._delegate_or_log(
            "safety_system_manager",
            "handle_backup_failed",
            event,
            f"❌ [MainWindow] 백업 실패: {event.backup_id} - {event.error_message}",
        )

    def on_command_executed(self, event: CommandExecutedEvent):
        """명령 실행 이벤트 핸들러"""
        self._delegate_or_log(
            "command_system_manager",
            "handle_command_executed",
            event,
            f"▶️ [MainWindow] 명령 실행: {event.command_id}",
        )

    def on_command_undone(self, event: CommandUndoneEvent):
        """명령 실행 취소 이벤트 핸들러"""
        self._delegate_or_log(
            "command_system_manager",
            "handle_command_undone",
            event,
            f"↩️ [MainWindow] 명령 실행 취소: {event.command_id}",
        )

    def on_command_redone(self, event: CommandRedoneEvent):
        """명령 재실행 이벤트 핸들러"""
        self._delegate_or_log(
            "command_system_manager",
            "handle_command_redone",
            event,
            f"↪️ [MainWindow] 명령 재실행: {event.command_id}",
        )

    def on_command_failed(self, event: CommandFailedEvent):
        """명령 실패 이벤트 핸들러"""
        self._delegate_or_log(
            "command_system_manager",
            "handle_command_failed",
            event,
            f"❌ [MainWindow] 명령 실패: {event.command_id} - {event.error_message}",
        )

    def on_preflight_started(self, event: PreflightStartedEvent):
        """프리플라이트 시작 이벤트 핸들러"""
        self.logger.info(f"✈️ [MainWindow] 프리플라이트 시작: {event.preflight_id}")
        self.main_window.update_status_bar("프리플라이트 검사 시작됨")

    def on_preflight_completed(self, event: PreflightCompletedEvent):
        """프리플라이트 완료 이벤트 핸들러"""
        self.logger.info(f"✅ [MainWindow] 프리플라이트 완료: {event.preflight_id}")
        self.main_window.update_status_bar("프리플라이트 검사 완료")

    def on_preflight_issue_found(self, event: PreflightIssueFoundEvent):
        """프리플라이트 이슈 발견 이벤트 핸들러"""
        self.logger.warning(f"⚠️ [MainWindow] 프리플라이트 이슈: {event.issue_description}")
        self.main_window.show_warning_message("프리플라이트 이슈", event.issue_description)

    # Journal 시스템 제거됨

    # Transaction 시스템도 Journal과 함께 제거됨

    def on_undo_executed(self, event: UndoExecutedEvent):
        """실행 취소 이벤트 핸들러"""
        self.logger.info(f"↩️ [MainWindow] 실행 취소: {event.command_id}")
        self.main_window.update_status_bar("실행 취소됨")

    def on_redo_executed(self, event: RedoExecutedEvent):
        """재실행 이벤트 핸들러"""
        self.logger.info(f"↪️ [MainWindow] 재실행: {event.command_id}")
        self.main_window.update_status_bar("재실행됨")

    def on_undo_redo_stack_changed(self, event: UndoRedoStackChangedEvent):
        """실행 취소/재실행 스택 변경 이벤트 핸들러"""
        self.logger.debug(
            f"📚 [MainWindow] Undo/Redo 스택 변경: {event.undo_count}개 취소 가능, {event.redo_count}개 재실행 가능"
        )
