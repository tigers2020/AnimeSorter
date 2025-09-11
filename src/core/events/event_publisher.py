"""
이벤트 발행 헬퍼

12개 핵심 이벤트를 쉽게 발행할 수 있는 헬퍼 함수들을 제공합니다.
"""

import logging
from typing import Any

from src.core.events import CoreEvent, CoreEventType
from src.core.events.payload_schemas import (ErrorPayload,
                                             OrganizeCompletedPayload,
                                             OrganizeConflictPayload,
                                             OrganizeSkippedPayload,
                                             OrganizeStartedPayload,
                                             PlanCreatedPayload,
                                             PlanValidatedPayload,
                                             ScanCompletedPayload,
                                             ScanProgressPayload,
                                             ScanStartedPayload,
                                             SettingsChangedPayload,
                                             UserActionRequiredPayload)
from src.core.unified_event_system import get_unified_event_bus

logger = logging.getLogger(__name__)


class EventPublisher:
    """이벤트 발행 헬퍼 클래스"""

    def __init__(self):
        self.event_bus = get_unified_event_bus()

    def publish_scan_started(
        self,
        scan_id: str,
        directory_path: str,
        recursive: bool = True,
        file_extensions: list = None,
    ) -> bool:
        """스캔 시작 이벤트 발행"""
        try:
            payload = ScanStartedPayload(
                scan_id=scan_id,
                directory_path=directory_path,
                recursive=recursive,
                file_extensions=file_extensions or [],
            )
            event = CoreEvent(
                event_type=CoreEventType.SCAN_STARTED,
                payload=payload.model_dump(),
                source="scanner",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"스캔 시작 이벤트 발행 실패: {e}")
            return False

    def publish_scan_progress(
        self,
        scan_id: str,
        processed: int,
        total: int,
        current_file: str = None,
        progress_percent: float = 0.0,
        current_step: str = "scanning",
    ) -> bool:
        """스캔 진행 이벤트 발행"""
        try:
            payload = ScanProgressPayload(
                scan_id=scan_id,
                processed=processed,
                total=total,
                current_file=current_file,
                progress_percent=progress_percent,
                current_step=current_step,
            )
            event = CoreEvent(
                event_type=CoreEventType.SCAN_PROGRESS,
                payload=payload.model_dump(),
                source="scanner",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"스캔 진행 이벤트 발행 실패: {e}")
            return False

    def publish_scan_completed(
        self,
        scan_id: str,
        found_files: list,
        stats: dict[str, Any] = None,
        duration_seconds: float = 0.0,
        status: str = "completed",
        error_message: str = None,
    ) -> bool:
        """스캔 완료 이벤트 발행"""
        try:
            payload = ScanCompletedPayload(
                scan_id=scan_id,
                found_files=found_files,
                stats=stats or {},
                duration_seconds=duration_seconds,
                status=status,
                error_message=error_message,
            )
            event = CoreEvent(
                event_type=CoreEventType.SCAN_COMPLETED,
                payload=payload.model_dump(),
                source="scanner",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"스캔 완료 이벤트 발행 실패: {e}")
            return False

    def publish_plan_created(
        self,
        plan_id: str,
        conflicts: list = None,
        skips: list = None,
        moves: list = None,
        total_operations: int = 0,
    ) -> bool:
        """계획 생성 이벤트 발행"""
        try:
            payload = PlanCreatedPayload(
                plan_id=plan_id,
                conflicts=conflicts or [],
                skips=skips or [],
                moves=moves or [],
                total_operations=total_operations,
            )
            event = CoreEvent(
                event_type=CoreEventType.PLAN_CREATED,
                payload=payload.model_dump(),
                source="planner",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"계획 생성 이벤트 발행 실패: {e}")
            return False

    def publish_plan_validated(
        self,
        plan_id: str,
        warnings: list = None,
        is_valid: bool = True,
        validation_errors: list = None,
    ) -> bool:
        """계획 검증 이벤트 발행"""
        try:
            payload = PlanValidatedPayload(
                plan_id=plan_id,
                warnings=warnings or [],
                is_valid=is_valid,
                validation_errors=validation_errors or [],
            )
            event = CoreEvent(
                event_type=CoreEventType.PLAN_VALIDATED,
                payload=payload.model_dump(),
                source="validator",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"계획 검증 이벤트 발행 실패: {e}")
            return False

    def publish_organize_started(
        self, organization_id: str, total_files: int, estimated_duration: float = None
    ) -> bool:
        """정리 시작 이벤트 발행"""
        try:
            payload = OrganizeStartedPayload(
                organization_id=organization_id,
                total_files=total_files,
                estimated_duration=estimated_duration,
            )
            event = CoreEvent(
                event_type=CoreEventType.ORGANIZE_STARTED,
                payload=payload.model_dump(),
                source="organizer",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"정리 시작 이벤트 발행 실패: {e}")
            return False

    def publish_organize_conflict(
        self,
        organization_id: str,
        path: str,
        reason: str,
        resolution_hint: str = None,
        conflict_type: str = "file_exists",
    ) -> bool:
        """정리 충돌 이벤트 발행"""
        try:
            payload = OrganizeConflictPayload(
                organization_id=organization_id,
                path=path,
                reason=reason,
                resolution_hint=resolution_hint,
                conflict_type=conflict_type,
            )
            event = CoreEvent(
                event_type=CoreEventType.ORGANIZE_CONFLICT,
                payload=payload.model_dump(),
                source="organizer",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"정리 충돌 이벤트 발행 실패: {e}")
            return False

    def publish_organize_skipped(
        self, organization_id: str, path: str, reason: str, skip_count: int = 1
    ) -> bool:
        """정리 스킵 이벤트 발행"""
        try:
            payload = OrganizeSkippedPayload(
                organization_id=organization_id, path=path, reason=reason, skip_count=skip_count
            )
            event = CoreEvent(
                event_type=CoreEventType.ORGANIZE_SKIPPED,
                payload=payload.model_dump(),
                source="organizer",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"정리 스킵 이벤트 발행 실패: {e}")
            return False

    def publish_organize_completed(
        self,
        organization_id: str,
        moved: int,
        backed_up: int,
        duration: float,
        stats: dict[str, Any] = None,
    ) -> bool:
        """정리 완료 이벤트 발행"""
        try:
            payload = OrganizeCompletedPayload(
                organization_id=organization_id,
                moved=moved,
                backed_up=backed_up,
                duration=duration,
                stats=stats or {},
            )
            event = CoreEvent(
                event_type=CoreEventType.ORGANIZE_COMPLETED,
                payload=payload.model_dump(),
                source="organizer",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"정리 완료 이벤트 발행 실패: {e}")
            return False

    def publish_user_action_required(
        self,
        action_id: str,
        message: str,
        action_type: str,
        options: list = None,
        timeout_seconds: int = None,
    ) -> bool:
        """사용자 액션 요청 이벤트 발행"""
        try:
            payload = UserActionRequiredPayload(
                action_id=action_id,
                message=message,
                action_type=action_type,
                options=options or [],
                timeout_seconds=timeout_seconds,
            )
            event = CoreEvent(
                event_type=CoreEventType.USER_ACTION_REQUIRED,
                payload=payload.model_dump(),
                source="ui",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"사용자 액션 요청 이벤트 발행 실패: {e}")
            return False

    def publish_error(
        self,
        error_id: str,
        error_type: str,
        message: str,
        details: str = None,
        where: str = "unknown",
        context: dict[str, Any] = None,
    ) -> bool:
        """오류 이벤트 발행"""
        try:
            payload = ErrorPayload(
                error_id=error_id,
                error_type=error_type,
                message=message,
                details=details,
                where=where,
                context=context or {},
            )
            event = CoreEvent(
                event_type=CoreEventType.ERROR, payload=payload.model_dump(), source="system"
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"오류 이벤트 발행 실패: {e}")
            return False

    def publish_settings_changed(
        self,
        changed_keys: list,
        old_values: dict[str, Any] = None,
        new_values: dict[str, Any] = None,
        source: str = "user",
    ) -> bool:
        """설정 변경 이벤트 발행"""
        try:
            payload = SettingsChangedPayload(
                changed_keys=changed_keys,
                old_values=old_values or {},
                new_values=new_values or {},
                source=source,
            )
            event = CoreEvent(
                event_type=CoreEventType.SETTINGS_CHANGED,
                payload=payload.model_dump(),
                source="settings",
            )
            return self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"설정 변경 이벤트 발행 실패: {e}")
            return False


# 전역 인스턴스
event_publisher = EventPublisher()
