"""
핵심 이벤트 핸들러 매니저

12개 핵심 이벤트를 처리하는 새로운 이벤트 핸들러 매니저입니다.
기존의 복잡한 이벤트 시스템을 단순화하고 통합합니다.
"""

import logging
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget

from src.core.unified_event_system import get_unified_event_bus
from src.gui.adapters import QtEventAdapter

logger = logging.getLogger(__name__)


class CoreEventHandlerManager(QObject):
    """12개 핵심 이벤트를 처리하는 핸들러 매니저"""

    # Qt 신호들 (MainWindow로 전달)
    scan_started = pyqtSignal(dict)
    scan_progress = pyqtSignal(dict)
    scan_completed = pyqtSignal(dict)
    plan_created = pyqtSignal(dict)
    plan_validated = pyqtSignal(dict)
    organize_started = pyqtSignal(dict)
    organize_conflict = pyqtSignal(dict)
    organize_skipped = pyqtSignal(dict)
    organize_completed = pyqtSignal(dict)
    user_action_required = pyqtSignal(dict)
    error_occurred = pyqtSignal(dict)
    settings_changed = pyqtSignal(dict)

    def __init__(self, main_window: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.main_window = main_window
        self.event_bus = get_unified_event_bus()
        self.qt_adapter = QtEventAdapter(self.event_bus, self)

        # Qt 어댑터 신호를 핸들러 신호로 연결
        self._connect_qt_signals()

        logger.info("✅ CoreEventHandlerManager 초기화 완료")

    def _connect_qt_signals(self):
        """Qt 어댑터 신호를 핸들러 신호로 연결"""
        self.qt_adapter.scan_started.connect(self.scan_started.emit)
        self.qt_adapter.scan_progress.connect(self.scan_progress.emit)
        self.qt_adapter.scan_completed.connect(self.scan_completed.emit)
        self.qt_adapter.plan_created.connect(self.plan_created.emit)
        self.qt_adapter.plan_validated.connect(self.plan_validated.emit)
        self.qt_adapter.organize_started.connect(self.organize_started.emit)
        self.qt_adapter.organize_conflict.connect(self.organize_conflict.emit)
        self.qt_adapter.organize_skipped.connect(self.organize_skipped.emit)
        self.qt_adapter.organize_completed.connect(self.organize_completed.emit)
        self.qt_adapter.user_action_required.connect(self.user_action_required.emit)
        self.qt_adapter.error_occurred.connect(self.error_occurred.emit)
        self.qt_adapter.settings_changed.connect(self.settings_changed.emit)

        logger.info("✅ Qt 신호 연결 완료")

    def setup_main_window_connections(self):
        """MainWindow와 핸들러 신호 연결"""
        try:
            # MainWindow의 핸들러 메서드들에 연결
            if hasattr(self.main_window, "on_scan_started"):
                self.scan_started.connect(self.main_window.on_scan_started)
            if hasattr(self.main_window, "on_scan_progress"):
                self.scan_progress.connect(self.main_window.on_scan_progress)
            if hasattr(self.main_window, "on_scan_completed"):
                self.scan_completed.connect(self.main_window.on_scan_completed)
            if hasattr(self.main_window, "on_plan_created"):
                self.plan_created.connect(self.main_window.on_plan_created)
            if hasattr(self.main_window, "on_plan_validated"):
                self.plan_validated.connect(self.main_window.on_plan_validated)
            if hasattr(self.main_window, "on_organize_started"):
                self.organize_started.connect(self.main_window.on_organize_started)
            if hasattr(self.main_window, "on_organize_conflict"):
                self.organize_conflict.connect(self.main_window.on_organize_conflict)
            if hasattr(self.main_window, "on_organize_skipped"):
                self.organize_skipped.connect(self.main_window.on_organize_skipped)
            if hasattr(self.main_window, "on_organize_completed"):
                self.organize_completed.connect(self.main_window.on_organize_completed)
            if hasattr(self.main_window, "on_user_action_required"):
                self.user_action_required.connect(self.main_window.on_user_action_required)
            if hasattr(self.main_window, "on_error_occurred"):
                self.error_occurred.connect(self.main_window.on_error_occurred)
            if hasattr(self.main_window, "on_settings_changed"):
                self.settings_changed.connect(self.main_window.on_settings_changed)

            logger.info("✅ MainWindow 신호 연결 완료")
        except Exception as e:
            logger.error(f"❌ MainWindow 신호 연결 실패: {e}")

    def cleanup(self):
        """핸들러 정리"""
        try:
            if hasattr(self.qt_adapter, "cleanup"):
                self.qt_adapter.cleanup()
            logger.info("✅ CoreEventHandlerManager 정리 완료")
        except Exception as e:
            logger.warning(f"⚠️ CoreEventHandlerManager 정리 오류: {e}")
