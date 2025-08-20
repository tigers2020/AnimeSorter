"""
파일 관련 명령들

파일 선택, 폴더 선택, 스캔 시작/중지 등의 명령을 포함합니다.
"""

from typing import List, Optional
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from .base_command import BaseCommand, CommandResult


class ChooseFilesCommand(BaseCommand):
    """파일 선택 명령"""
    
    def __init__(self, event_bus, parent_widget=None):
        super().__init__(event_bus, "파일 선택")
        self.parent_widget = parent_widget
        self._selected_files: List[str] = []
    
    def _execute_impl(self) -> CommandResult:
        """파일 선택 다이얼로그 실행"""
        try:
            # 파일 선택 다이얼로그
            files, _ = QFileDialog.getOpenFileNames(
                self.parent_widget,
                "애니메이션 파일 선택",
                "",
                "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm);;All Files (*)"
            )
            
            if not files:
                return CommandResult(
                    success=False,
                    message="파일이 선택되지 않았습니다."
                )
            
            self._selected_files = files
            
            # 이벤트 버스에 파일 선택 알림
            if self.event_bus:
                self.event_bus.publish("files_selected", files)
            
            return CommandResult(
                success=True,
                message=f"{len(files)}개 파일이 선택되었습니다.",
                data=files
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"파일 선택 실패: {str(e)}",
                error=e
            )
    
    def can_execute(self) -> bool:
        """명령 실행 가능 여부 확인"""
        return True  # 파일 선택은 항상 가능
    
    def _save_state_for_undo(self):
        """실행 취소를 위한 상태 저장"""
        # 파일 선택은 실행 취소 불가능
        self._can_undo = False
        self._undo_data = None


class ChooseFolderCommand(BaseCommand):
    """폴더 선택 명령"""
    
    def __init__(self, event_bus, parent_widget=None):
        super().__init__(event_bus, "폴더 선택")
        self.parent_widget = parent_widget
        self._selected_folder: Optional[str] = None
    
    def _execute_impl(self) -> CommandResult:
        """폴더 선택 다이얼로그 실행"""
        try:
            # 폴더 선택 다이얼로그
            folder = QFileDialog.getExistingDirectory(
                self.parent_widget,
                "애니메이션 폴더 선택",
                ""
            )
            
            if not folder:
                return CommandResult(
                    success=False,
                    message="폴더가 선택되지 않았습니다."
                )
            
            self._selected_folder = folder
            
            # 이벤트 버스에 폴더 선택 알림
            if self.event_bus:
                self.event_bus.publish("folder_selected", folder)
            
            return CommandResult(
                success=True,
                message=f"폴더가 선택되었습니다: {folder}",
                data=folder
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"폴더 선택 실패: {str(e)}",
                error=e
            )
    
    def can_execute(self) -> bool:
        """명령 실행 가능 여부 확인"""
        return True  # 폴더 선택은 항상 가능
    
    def _save_state_for_undo(self):
        """실행 취소를 위한 상태 저장"""
        # 폴더 선택은 실행 취소 불가능
        self._can_undo = False
        self._undo_data = None


class StartScanCommand(BaseCommand):
    """스캔 시작 명령"""
    
    def __init__(self, event_bus, file_paths: List[str] = None, folder_path: str = None):
        super().__init__(event_bus, "스캔 시작")
        self.file_paths = file_paths or []
        self.folder_path = folder_path
        self._previous_state = None
    
    def _execute_impl(self) -> CommandResult:
        """스캔 시작"""
        try:
            # 이벤트 버스에 스캔 시작 알림
            if self.event_bus:
                if self.file_paths:
                    self.event_bus.publish("start_file_scan", self.file_paths)
                elif self.folder_path:
                    self.event_bus.publish("start_folder_scan", self.folder_path)
                else:
                    return CommandResult(
                        success=False,
                        message="스캔할 파일이나 폴더가 지정되지 않았습니다."
                    )
            
            return CommandResult(
                success=True,
                message="파일 스캔을 시작합니다."
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"스캔 시작 실패: {str(e)}",
                error=e
            )
    
    def can_execute(self) -> bool:
        """명령 실행 가능 여부 확인"""
        return bool(self.file_paths or self.folder_path)  # 파일이나 폴더가 지정되어야 함
    
    def _save_state_for_undo(self):
        """실행 취소를 위한 상태 저장"""
        # 스캔 시작은 실행 취소 불가능
        self._can_undo = False
        self._undo_data = None


class StopScanCommand(BaseCommand):
    """스캔 중지 명령"""
    
    def __init__(self, event_bus):
        super().__init__(event_bus, "스캔 중지")
    
    def _execute_impl(self) -> CommandResult:
        """스캔 중지"""
        try:
            # 이벤트 버스에 스캔 중지 알림
            if self.event_bus:
                self.event_bus.publish("stop_scan", None)
            
            return CommandResult(
                success=True,
                message="파일 스캔을 중지합니다."
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"스캔 중지 실패: {str(e)}",
                error=e
            )
    
    def can_execute(self) -> bool:
        """명령 실행 가능 여부 확인"""
        return True  # 스캔 중지는 항상 가능
    
    def _save_state_for_undo(self):
        """실행 취소를 위한 상태 저장"""
        # 스캔 중지는 실행 취소 불가능
        self._can_undo = False
        self._undo_data = None
