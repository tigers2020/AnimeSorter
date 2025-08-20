"""
메인 윈도우 뷰모델

메인 윈도우의 UI 상태와 데이터를 관리하는 뷰모델
"""

from dataclasses import dataclass
from typing import Any

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from src.gui.interfaces.i_event_bus import IEventBus
from src.gui.interfaces.i_view_model import IViewModel


@dataclass
class UIState:
    """UI 상태 정보"""

    is_scanning: bool = False
    is_searching: bool = False
    is_organizing: bool = False
    can_start_scan: bool = True
    can_start_search: bool = False
    can_start_organize: bool = False
    has_selected_items: bool = False
    has_parsed_items: bool = False
    has_tmdb_matches: bool = False


class MainWindowViewModel(QObject, IViewModel):
    """메인 윈도우 뷰모델"""

    # 시그널 정의
    ui_state_changed = pyqtSignal()  # UI 상태 변경
    progress_updated = pyqtSignal(int, int)  # 진행률 업데이트 (현재, 전체)
    status_message_changed = pyqtSignal(str)  # 상태 메시지 변경
    error_message_changed = pyqtSignal(str)  # 오류 메시지 변경

    def __init__(self, event_bus: IEventBus = None, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus

        # UI 상태
        self._ui_state = UIState()

        # 진행률 정보
        self._progress_current = 0
        self._progress_total = 0

        # 메시지
        self._status_message = "애니메이션 파일 정리 시스템이 준비되었습니다."
        self._error_message = ""

        # 이벤트 버스 연결
        self._connect_event_bus()

    def initialize(self) -> bool:
        """뷰모델 초기화"""
        try:
            print("✅ MainWindowViewModel 초기화 완료")
            return True
        except Exception as e:
            print(f"❌ MainWindowViewModel 초기화 실패: {e}")
            return False

    def cleanup(self):
        """뷰모델 정리"""
        try:
            # 이벤트 버스 연결 해제
            self._disconnect_event_bus()
            print("🧹 MainWindowViewModel 정리 완료")
        except Exception as e:
            print(f"❌ MainWindowViewModel 정리 실패: {e}")

    def _connect_event_bus(self):
        """이벤트 버스 연결"""
        if self.event_bus:
            # 상태 변경 이벤트
            self.event_bus.subscribe("app_state_changed", self._on_app_state_changed)
            self.event_bus.subscribe("scan_progress", self._on_scan_progress)
            self.event_bus.subscribe("search_progress", self._on_search_progress)
            self.event_bus.subscribe("organize_progress", self._on_organize_progress)

            # 데이터 업데이트 이벤트
            self.event_bus.subscribe("data_updated", self._on_data_updated)

            # 메시지 이벤트
            self.event_bus.subscribe("status_message", self._on_status_message)
            self.event_bus.subscribe("error_message", self._on_error_message)

    def _disconnect_event_bus(self):
        """이벤트 버스 연결 해제"""
        if self.event_bus:
            self.event_bus.unsubscribe("app_state_changed", self._on_app_state_changed)
            self.event_bus.unsubscribe("scan_progress", self._on_scan_progress)
            self.event_bus.unsubscribe("search_progress", self._on_search_progress)
            self.event_bus.unsubscribe("organize_progress", self._on_organize_progress)
            self.event_bus.unsubscribe("data_updated", self._on_data_updated)
            self.event_bus.unsubscribe("status_message", self._on_status_message)
            self.event_bus.unsubscribe("error_message", self._on_error_message)

    # === 이벤트 핸들러 ===

    def _on_app_state_changed(self, state: str):
        """애플리케이션 상태 변경 처리"""
        self._ui_state.is_scanning = state == "scanning"
        self._ui_state.is_searching = state == "searching"
        self._ui_state.is_organizing = state == "organizing"

        # UI 상태 업데이트
        self._update_ui_state()
        self.ui_state_changed.emit()

    def _on_scan_progress(self, current: int, total: int):
        """스캔 진행률 업데이트"""
        self._progress_current = current
        self._progress_total = total
        self.progress_updated.emit(current, total)

        # 상태 메시지 업데이트
        if total > 0:
            percentage = (current / total) * 100
            self._status_message = f"파일 스캔 중... {current}/{total} ({percentage:.1f}%)"
            self.status_message_changed.emit(self._status_message)

    def _on_search_progress(self, current: int, total: int):
        """검색 진행률 업데이트"""
        self._progress_current = current
        self._progress_total = total
        self.progress_updated.emit(current, total)

        # 상태 메시지 업데이트
        if total > 0:
            percentage = (current / total) * 100
            self._status_message = f"TMDB 검색 중... {current}/{total} ({percentage:.1f}%)"
            self.status_message_changed.emit(self._status_message)

    def _on_organize_progress(self, current: int, total: int):
        """정리 진행률 업데이트"""
        self._progress_current = current
        self._progress_total = total
        self.progress_updated.emit(current, total)

        # 상태 메시지 업데이트
        if total > 0:
            percentage = (current / total) * 100
            self._status_message = f"파일 정리 중... {current}/{total} ({percentage:.1f}%)"
            self.status_message_changed.emit(self._status_message)

    def _on_data_updated(self, data_type: str):
        """데이터 업데이트 처리"""
        # UI 상태 업데이트
        self._update_ui_state()
        self.ui_state_changed.emit()

    def _on_status_message(self, message: str):
        """상태 메시지 업데이트"""
        self._status_message = message
        self.status_message_changed.emit(message)

    def _on_error_message(self, message: str):
        """오류 메시지 업데이트"""
        self._error_message = message
        self.error_message_changed.emit(message)

    # === UI 상태 관리 ===

    def _update_ui_state(self):
        """UI 상태 업데이트"""
        # 이벤트 버스를 통해 데이터 상태 확인
        if self.event_bus:
            # 파싱된 아이템이 있는지 확인
            parsed_items = self.event_bus.publish("get_parsed_items", [])
            self._ui_state.has_parsed_items = len(parsed_items) > 0

            # 선택된 아이템이 있는지 확인
            selected_items = self.event_bus.publish("get_selected_items", [])
            self._ui_state.has_selected_items = len(selected_items) > 0

            # TMDB 매치가 있는지 확인
            tmdb_matches = self.event_bus.publish("get_all_tmdb_matches", [])
            self._ui_state.has_tmdb_matches = len(tmdb_matches) > 0

        # 버튼 활성화 상태 업데이트
        self._ui_state.can_start_scan = not (
            self._ui_state.is_scanning
            or self._ui_state.is_searching
            or self._ui_state.is_organizing
        )

        self._ui_state.can_start_search = (
            self._ui_state.has_parsed_items
            and not self._ui_state.is_scanning
            and not self._ui_state.is_searching
            and not self._ui_state.is_organizing
        )

        self._ui_state.can_start_organize = (
            self._ui_state.has_selected_items
            and self._ui_state.has_tmdb_matches
            and not self._ui_state.is_scanning
            and not self._ui_state.is_searching
            and not self._ui_state.is_organizing
        )

    # === 프로퍼티 (PyQt 바인딩용) ===

    @pyqtProperty(bool, notify=ui_state_changed)
    def is_scanning(self) -> bool:
        """스캔 중인지 확인"""
        return self._ui_state.is_scanning

    @pyqtProperty(bool, notify=ui_state_changed)
    def is_searching(self) -> bool:
        """검색 중인지 확인"""
        return self._ui_state.is_searching

    @pyqtProperty(bool, notify=ui_state_changed)
    def is_organizing(self) -> bool:
        """정리 중인지 확인"""
        return self._ui_state.is_organizing

    @pyqtProperty(bool, notify=ui_state_changed)
    def can_start_scan(self) -> bool:
        """스캔 시작 가능한지 확인"""
        return self._ui_state.can_start_scan

    @pyqtProperty(bool, notify=ui_state_changed)
    def can_start_search(self) -> bool:
        """검색 시작 가능한지 확인"""
        return self._ui_state.can_start_search

    @pyqtProperty(bool, notify=ui_state_changed)
    def can_start_organize(self) -> bool:
        """정리 시작 가능한지 확인"""
        return self._ui_state.can_start_organize

    @pyqtProperty(bool, notify=ui_state_changed)
    def has_selected_items(self) -> bool:
        """선택된 아이템이 있는지 확인"""
        return self._ui_state.has_selected_items

    @pyqtProperty(bool, notify=ui_state_changed)
    def has_parsed_items(self) -> bool:
        """파싱된 아이템이 있는지 확인"""
        return self._ui_state.has_parsed_items

    @pyqtProperty(bool, notify=ui_state_changed)
    def has_tmdb_matches(self) -> bool:
        """TMDB 매치가 있는지 확인"""
        return self._ui_state.has_tmdb_matches

    @pyqtProperty(str, notify=status_message_changed)
    def status_message(self) -> str:
        """상태 메시지"""
        return self._status_message

    @pyqtProperty(str, notify=error_message_changed)
    def error_message(self) -> str:
        """오류 메시지"""
        return self._error_message

    @pyqtProperty(int, notify=progress_updated)
    def progress_current(self) -> int:
        """현재 진행률"""
        return self._progress_current

    @pyqtProperty(int, notify=progress_updated)
    def progress_total(self) -> int:
        """전체 진행률"""
        return self._progress_total

    @pyqtProperty(float, notify=progress_updated)
    def progress_percentage(self) -> float:
        """진행률 퍼센트"""
        if self._progress_total > 0:
            return (self._progress_current / self._progress_total) * 100
        return 0.0

    # === IViewModel 인터페이스 구현 ===

    def set_property(self, name: str, value: Any, validate: bool = True) -> bool:
        """프로퍼티 설정"""
        try:
            if hasattr(self, f"_{name}"):
                setattr(self, f"_{name}", value)
                return True
            return False
        except Exception as e:
            print(f"❌ 프로퍼티 설정 실패: {name} = {value} - {e}")
            return False

    def get_property(self, name: str) -> Any:
        """프로퍼티 가져오기"""
        try:
            if hasattr(self, f"_{name}"):
                return getattr(self, f"_{name}")
            return None
        except Exception as e:
            print(f"❌ 프로퍼티 가져오기 실패: {name} - {e}")
            return None

    def get_all_properties(self) -> dict[str, Any]:
        """모든 프로퍼티 가져오기"""
        properties = {}
        for attr_name in dir(self):
            if attr_name.startswith("_") and not attr_name.startswith("__"):
                prop_name = attr_name[1:]  # 언더스코어 제거
                properties[prop_name] = getattr(self, attr_name)
        return properties

    # === 공개 메서드 ===

    def update_status_message(self, message: str):
        """상태 메시지 업데이트"""
        self._status_message = message
        self.status_message_changed.emit(message)

    def update_error_message(self, message: str):
        """오류 메시지 업데이트"""
        self._error_message = message
        self.error_message_changed.emit(message)

    def clear_error_message(self):
        """오류 메시지 지우기"""
        self._error_message = ""
        self.error_message_changed.emit("")

    def get_ui_state(self) -> UIState:
        """UI 상태 반환"""
        return self._ui_state

    def refresh_ui_state(self):
        """UI 상태 새로고침"""
        self._update_ui_state()
        self.ui_state_changed.emit()
