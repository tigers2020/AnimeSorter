"""
이벤트 시스템 마이그레이션 가이드

기존 이벤트 시스템에서 12개 핵심 이벤트 시스템으로의 마이그레이션 가이드입니다.
"""

import logging
from typing import Any

from src.core.events.event_publisher import event_publisher

logger = logging.getLogger(__name__)


class EventMigrationHelper:
    """이벤트 마이그레이션 헬퍼"""

    @staticmethod
    def migrate_scan_events(old_events: list[dict[str, Any]]) -> None:
        """스캔 관련 이벤트 마이그레이션"""
        for event in old_events:
            event_type = event.get("type", "")

            if event_type == "FileScanStartedEvent":
                event_publisher.publish_scan_started(
                    scan_id=event.get("scan_id", ""),
                    directory_path=event.get("directory_path", ""),
                    recursive=event.get("recursive", True),
                    file_extensions=event.get("file_extensions", []),
                )

            elif event_type == "FileScanProgressEvent":
                event_publisher.publish_scan_progress(
                    scan_id=event.get("scan_id", ""),
                    processed=event.get("processed_count", 0),
                    total=event.get("total_estimated", 0),
                    current_file=event.get("current_file", ""),
                    progress_percent=event.get("progress_percentage", 0.0),
                    current_step="scanning",
                )

            elif event_type == "FilesScannedEvent":
                event_publisher.publish_scan_completed(
                    scan_id=event.get("scan_id", ""),
                    found_files=[str(f) for f in event.get("found_files", [])],
                    stats=event.get("stats", {}),
                    duration_seconds=event.get("scan_duration_seconds", 0.0),
                    status=event.get("status", "completed"),
                    error_message=event.get("error_message"),
                )

    @staticmethod
    def migrate_organization_events(old_events: list[dict[str, Any]]) -> None:
        """파일 정리 관련 이벤트 마이그레이션"""
        for event in old_events:
            event_type = event.get("type", "")

            if event_type == "OrganizationStartedEvent":
                event_publisher.publish_organize_started(
                    organization_id=event.get("organization_id", ""),
                    total_files=event.get("total_files", 0),
                    estimated_duration=event.get("estimated_duration"),
                )

            elif event_type == "OrganizationProgressEvent":
                # 진행률은 별도 이벤트로 처리하지 않고 로그로만 처리
                logger.debug(f"정리 진행률: {event.get('progress_percent', 0)}%")

            elif event_type == "OrganizationCompletedEvent":
                event_publisher.publish_organize_completed(
                    organization_id=event.get("organization_id", ""),
                    moved=event.get("success_count", 0),
                    backed_up=event.get("backed_up_count", 0),
                    duration=event.get("operation_duration_seconds", 0.0),
                    stats=event.get("stats", {}),
                )

            elif event_type == "OrganizationFailedEvent":
                event_publisher.publish_error(
                    error_id=event.get("organization_id", ""),
                    error_type="file_operation_error",
                    message=event.get("error_message", "파일 정리 실패"),
                    where="organize",
                    context={"organization_id": event.get("organization_id", "")},
                )

    @staticmethod
    def migrate_background_events(old_events: list[dict[str, Any]]) -> None:
        """백그라운드 작업 관련 이벤트 마이그레이션"""
        # 백그라운드 작업 이벤트는 대부분 함수 반환값으로 처리
        # 필요한 경우에만 핵심 이벤트로 변환
        for event in old_events:
            event_type = event.get("type", "")

            if event_type in ["TaskFailedEvent", "CommandFailedEvent"]:
                event_publisher.publish_error(
                    error_id=event.get("task_id", event.get("command_id", "")),
                    error_type="unknown_error",
                    message=event.get("error_message", "작업 실패"),
                    where="background",
                    context={"task_type": event.get("task_type", "unknown")},
                )

    @staticmethod
    def migrate_safety_events(old_events: list[dict[str, Any]]) -> None:
        """안전 시스템 관련 이벤트 마이그레이션"""
        for event in old_events:
            event_type = event.get("type", "")

            if event_type == "ConfirmationRequiredEvent":
                event_publisher.publish_user_action_required(
                    action_id=event.get("confirmation_id", ""),
                    message=event.get("message", "확인이 필요합니다"),
                    action_type="confirm",
                    timeout_seconds=event.get("timeout_seconds"),
                )

            elif event_type == "SafetyAlertEvent":
                event_publisher.publish_user_action_required(
                    action_id=event.get("alert_id", ""),
                    message=event.get("message", "안전 경고"),
                    action_type="resolve",
                    options=event.get("options", []),
                )

            elif event_type == "SafetyStatusUpdateEvent":
                event_publisher.publish_settings_changed(
                    changed_keys=["safety_status"],
                    new_values={"status": event.get("status", "unknown")},
                    source="safety_system",
                )


# 마이그레이션 예제
def migrate_legacy_events():
    """기존 이벤트를 새로운 시스템으로 마이그레이션하는 예제"""
    logger.info("🔄 이벤트 시스템 마이그레이션 시작")

    # 예제: 기존 이벤트 데이터
    legacy_events = [
        {
            "type": "FileScanStartedEvent",
            "scan_id": "scan_001",
            "directory_path": "/path/to/anime",
            "recursive": True,
            "file_extensions": [".mp4", ".mkv"],
        },
        {
            "type": "FilesScannedEvent",
            "scan_id": "scan_001",
            "found_files": ["/path/to/anime/episode1.mp4"],
            "scan_duration_seconds": 5.2,
            "status": "completed",
        },
    ]

    # 마이그레이션 실행
    EventMigrationHelper.migrate_scan_events(legacy_events)

    logger.info("✅ 이벤트 시스템 마이그레이션 완료")


if __name__ == "__main__":
    migrate_legacy_events()
