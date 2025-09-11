"""
Progress Event Handler

Handles file processing progress events and updates UI components accordingly.
"""

import logging

logger = logging.getLogger(__name__)

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QLabel, QProgressBar


class ProgressEventHandler(QObject):
    """Handles file processing progress events and updates UI components"""

    progress_updated = pyqtSignal(int, str)
    file_processing_started = pyqtSignal(str, int, int)
    file_processing_completed = pyqtSignal(int, int, int, list)
    file_processing_failed = pyqtSignal(str, str)
    speed_updated = pyqtSignal(float, float)
    statistics_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_operation_id = None
        self.current_operation_type = None
        self.total_files = 0
        self.total_size_bytes = 0
        self.start_time = None

    def handle_processing_started(self, event: Any):
        """Handle file processing started event"""
        self.current_operation_id = event.operation_id
        self.current_operation_type = event.operation_type
        self.total_files = event.total_files
        self.total_size_bytes = event.total_size_bytes
        self.start_time = event.timestamp
        self.file_processing_started.emit(
            event.operation_type, event.total_files, event.total_size_bytes
        )
        self.progress_updated.emit(0, f"Starting {event.operation_type}...")

    def handle_processing_progress(self, event: ):
        """Handle file processing progress event"""
        if event.operation_id != self.current_operation_id:
            return
        progress_message = self._create_progress_message(event)
        self.progress_updated.emit(int(event.progress_percentage), progress_message)

    def handle_processing_step(self, event: ):
        """Handle file processing step change event"""
        if event.operation_id != self.current_operation_id:
            return
        step_message = f"Step: {event.current_step} - {event.step_description}"
        self.progress_updated.emit(int(event.step_progress * 100), step_message)

    def handle_processing_completed(self, event: ):
        """Handle file processing completed event"""
        if event.operation_id != self.current_operation_id:
            return
        self.file_processing_completed.emit(
            event.successful_files, event.failed_files, event.skipped_files, event.errors
        )
        completion_message = (
            f"Completed: {event.successful_files} successful, {event.failed_files} failed"
        )
        self.progress_updated.emit(100, completion_message)
        self._reset_state()

    def handle_processing_failed(self, event: ):
        """Handle file processing failed event"""
        if event.operation_id != self.current_operation_id:
            return
        self.file_processing_failed.emit(event.error_message, event.error_type)
        error_message = f"Failed: {event.error_message}"
        self.progress_updated.emit(0, error_message)
        self._reset_state()

    def handle_processing_cancelled(self, event: ):
        """Handle file processing cancelled event"""
        if event.operation_id != self.current_operation_id:
            return
        cancel_message = f"Cancelled: {event.cancellation_reason}"
        self.progress_updated.emit(0, cancel_message)
        self._reset_state()

    def handle_processing_paused(self, event: ):
        """Handle file processing paused event"""
        if event.operation_id != self.current_operation_id:
            return
        pause_message = f"Paused: {event.pause_reason}"
        self.progress_updated.emit(0, pause_message)

    def handle_processing_resumed(self, event: ):
        """Handle file processing resumed event"""
        if event.operation_id != self.current_operation_id:
            return
        resume_message = f"Resumed: {event.resumed_at_step}"
        self.progress_updated.emit(0, resume_message)

    def handle_processing_statistics(self, event: ):
        """Handle file processing statistics event"""
        if event.operation_id != self.current_operation_id:
            return
        stats = {
            "total_files": event.total_files,
            "processed_files": event.processed_files,
            "successful_files": event.successful_files,
            "failed_files": event.failed_files,
            "skipped_files": event.skipped_files,
            "total_size_bytes": event.total_size_bytes,
            "processed_size_bytes": event.processed_size_bytes,
            "average_file_size_bytes": event.average_file_size_bytes,
            "processing_time_seconds": event.processing_time_seconds,
            "average_processing_time_per_file": event.average_processing_time_per_file,
        }
        self.statistics_updated.emit(stats)

    def handle_processing_speed(self, event: ):
        """Handle file processing speed event"""
        if event.operation_id != self.current_operation_id:
            return
        self.speed_updated.emit(event.current_speed_mbps, event.average_speed_mbps)

    def _create_progress_message(self, event: ) -> str:
        """Create detailed progress message from progress event"""
        message_parts = []
        if event.current_file_path:
            filename = event.current_file_path.name
            message_parts.append(f"Processing: {filename}")
        else:
            message_parts.append(
                f"Processing file {event.current_file_index + 1}/{event.total_files}"
            )
        if event.current_operation:
            message_parts.append(f"({event.current_operation.value})")
        if event.current_step:
            message_parts.append(f"- {event.current_step}")
        if event.processing_speed_mbps > 0:
            message_parts.append(f"@ {event.processing_speed_mbps:.1f} MB/s")
        if event.estimated_remaining_seconds:
            remaining_minutes = int(event.estimated_remaining_seconds // 60)
            remaining_seconds = int(event.estimated_remaining_seconds % 60)
            if remaining_minutes > 0:
                message_parts.append(f"ETA: {remaining_minutes}m {remaining_seconds}s")
            else:
                message_parts.append(f"ETA: {remaining_seconds}s")
        if event.success_count > 0 or event.error_count > 0:
            message_parts.append(f"[✓{event.success_count} ✗{event.error_count}]")
        return " ".join(message_parts)

    def _reset_state(self):
        """Reset handler state"""
        self.current_operation_id = None
        self.current_operation_type = None
        self.total_files = 0
        self.total_size_bytes = 0
        self.start_time = None

class ProgressUIUpdater:
    """Updates UI components based on progress events"""

    def __init__(
        self, progress_bar: QProgressBar | None = None, status_label: QLabel | None = None
    ):
        self.progress_bar = progress_bar
        self.status_label = status_label
        self.event_handler = ProgressEventHandler()
        self.event_handler.progress_updated.connect(self._update_progress)
        self.event_handler.file_processing_started.connect(self._on_processing_started)
        self.event_handler.file_processing_completed.connect(self._on_processing_completed)
        self.event_handler.file_processing_failed.connect(self._on_processing_failed)
        self.event_handler.speed_updated.connect(self._on_speed_updated)
        self.event_handler.statistics_updated.connect(self._on_statistics_updated)

    def handle_event(self, event):
        """Handle any progress event"""
        if isinstance(event):
            self.event_handler.handle_processing_started(event)
        elif isinstance(event):
            self.event_handler.handle_processing_progress(event)
        elif isinstance(event):
            self.event_handler.handle_processing_step(event)
        elif isinstance(event):
            self.event_handler.handle_processing_completed(event)
        elif isinstance(event):
            self.event_handler.handle_processing_failed(event)
        elif isinstance(event):
            self.event_handler.handle_processing_cancelled(event)
        elif isinstance(event):
            self.event_handler.handle_processing_paused(event)
        elif isinstance(event):
            self.event_handler.handle_processing_resumed(event)
        elif isinstance(event):
            self.event_handler.handle_processing_statistics(event)
        elif isinstance(event):
            self.event_handler.handle_processing_speed(event)

    def _update_progress(self, percentage: int, message: str):
        """Update progress bar and status label"""
        if self.progress_bar:
            self.progress_bar.setValue(percentage)
        if self.status_label:
            self.status_label.setText(message)

    def _on_processing_started(self, operation_type: str, total_files: int, total_size: int):
        """Handle processing started"""
        if self.progress_bar:
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(100)
        if self.status_label:
            size_mb = total_size / (1024 * 1024) if total_size > 0 else 0
            self.status_label.setText(
                f"Starting {operation_type}: {total_files} files ({size_mb:.1f} MB)"
            )

    def _on_processing_completed(self, success: int, failed: int, skipped: int, errors: list):
        """Handle processing completed"""
        if self.progress_bar:
            self.progress_bar.setValue(100)
        if self.status_label:
            message = f"Completed: {success} successful"
            if failed > 0:
                message += f", {failed} failed"
            if skipped > 0:
                message += f", {skipped} skipped"
            self.status_label.setText(message)

    def _on_processing_failed(self, error_message: str, error_type: str):
        """Handle processing failed"""
        if self.progress_bar:
            self.progress_bar.setValue(0)
        if self.status_label:
            self.status_label.setText(f"Failed: {error_message}")

    def _on_speed_updated(self, current_speed: float, average_speed: float):
        """Handle speed update"""

    def _on_statistics_updated(self, statistics: dict):
        """Handle statistics update"""
