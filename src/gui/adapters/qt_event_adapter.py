"""
Qt 이벤트 어댑터

CoreBus의 이벤트를 Qt Signal/Slot으로 변환하는 어댑터입니다.
메인 스레드 안전성을 보장하고 중복 신호를 방지합니다.
"""

import logging
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

from src.core.events import CoreEvent, CoreEventType
from src.core.unified_event_system import UnifiedEventBus

logger = logging.getLogger(__name__)


class QtEventAdapter(QObject):
    """CoreBus → Qt Signal 어댑터"""

    # 12개 핵심 이벤트에 대한 Qt 신호
    scan_started = pyqtSignal(dict)  # payload
    scan_progress = pyqtSignal(dict)  # payload
    scan_completed = pyqtSignal(dict)  # payload
    plan_created = pyqtSignal(dict)  # payload
    plan_validated = pyqtSignal(dict)  # payload
    organize_started = pyqtSignal(dict)  # payload
    organize_conflict = pyqtSignal(dict)  # payload
    organize_skipped = pyqtSignal(dict)  # payload
    organize_completed = pyqtSignal(dict)  # payload
    user_action_required = pyqtSignal(dict)  # payload
    error_occurred = pyqtSignal(dict)  # payload
    settings_changed = pyqtSignal(dict)  # payload

    def __init__(self, core_bus: UnifiedEventBus, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.core_bus = core_bus
        self._last_events: dict[CoreEventType, str] = {}  # 중복 방지용
        self._setup_subscriptions()
        logger.info("✅ QtEventAdapter 초기화 완료")

    def _setup_subscriptions(self):
        """CoreBus 구독 설정"""
        try:
            for event_type in CoreEventType:
                self.core_bus.subscribe(
                    event_type=event_type, handler=self._handle_core_event, filter=None, priority=0
                )
            logger.info("✅ CoreBus 구독 설정 완료")
        except Exception as e:
            logger.error(f"❌ CoreBus 구독 설정 실패: {e}")

    def _handle_core_event(self, event: CoreEvent):
        """Core 이벤트를 Qt 신호로 변환"""
        try:
            # 중복 방지 체크
            event_key = f"{event.job_id}_{event.timestamp.isoformat()}"
            if self._last_events.get(event.event_type) == event_key:
                logger.debug(f"중복 이벤트 무시: {event.event_type.value}")
                return

            self._last_events[event.event_type] = event_key

            # Qt 신호 발송 (메인 스레드에서)
            signal_map = {
                CoreEventType.SCAN_STARTED: self.scan_started,
                CoreEventType.SCAN_PROGRESS: self.scan_progress,
                CoreEventType.SCAN_COMPLETED: self.scan_completed,
                CoreEventType.PLAN_CREATED: self.plan_created,
                CoreEventType.PLAN_VALIDATED: self.plan_validated,
                CoreEventType.ORGANIZE_STARTED: self.organize_started,
                CoreEventType.ORGANIZE_CONFLICT: self.organize_conflict,
                CoreEventType.ORGANIZE_SKIPPED: self.organize_skipped,
                CoreEventType.ORGANIZE_COMPLETED: self.organize_completed,
                CoreEventType.USER_ACTION_REQUIRED: self.user_action_required,
                CoreEventType.ERROR: self.error_occurred,
                CoreEventType.SETTINGS_CHANGED: self.settings_changed,
            }

            signal = signal_map.get(event.event_type)
            if signal:
                signal.emit(event.payload)
                logger.debug(f"Qt 신호 발송: {event.event_type.value}")
            else:
                logger.warning(f"알 수 없는 이벤트 타입: {event.event_type}")

        except Exception as e:
            logger.error(f"Core 이벤트 처리 실패: {e}")

    def cleanup(self):
        """어댑터 정리"""
        try:
            # 구독 해제는 UnifiedEventBus에서 자동으로 처리됨
            logger.info("✅ QtEventAdapter 정리 완료")
        except Exception as e:
            logger.warning(f"⚠️ QtEventAdapter 정리 오류: {e}")
