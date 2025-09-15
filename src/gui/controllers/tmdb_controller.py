"""
TMDB 컨트롤러

TMDB 검색, 매칭, 다이얼로그 관리 등을 담당하는 컨트롤러
"""

import logging

logger = logging.getLogger(__name__)
from typing import Any

from PyQt5.QtCore import QObject, QTimer

from src.app.interfaces.i_controller import IController
from src.app.interfaces.i_event_bus import Event, IEventBus
from src.core.tmdb_client import TMDBAnimeInfo, TMDBClient
from src.gui.components.tmdb_search_dialog import TMDBSearchDialog


class TMDBController(IController):
    """
    TMDB 컨트롤러

    TMDB API를 통한 애니메이션 검색, 매칭, 사용자 인터페이스 관리
    """

    def __init__(self, event_bus: IEventBus, parent_widget: QObject = None):
        super().__init__(event_bus)
        self.parent_widget = parent_widget
        self.logger = logging.getLogger(__name__)
        self.tmdb_client: TMDBClient | None = None
        self.search_dialogs: dict[str, TMDBSearchDialog] = {}
        self.pending_search_groups: list[tuple[str, str]] = []
        self.is_batch_searching = False
        self.tmdb_matches: dict[str, TMDBAnimeInfo] = {}
        self.config = {
            "auto_select_single_result": True,
            "show_dialog_for_multiple_results": True,
            "show_dialog_for_no_results": True,
            "search_delay_ms": 500,
            "max_concurrent_dialogs": 3,
        }
        self.logger.info("TMDBController 초기화 완료")

    def initialize(self) -> None:
        """컨트롤러 초기화"""
        try:
            self._setup_event_subscriptions()
            self.logger.info("TMDBController 초기화 완료")
        except Exception as e:
            self.logger.error(f"TMDBController 초기화 실패: {e}")
            raise

    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            self._close_all_dialogs()
            self._stop_batch_search()
            self._cleanup_event_subscriptions()
            self.logger.info("TMDBController 정리 완료")
        except Exception as e:
            self.logger.error(f"TMDBController 정리 실패: {e}")

    def handle_event(self, event: Event) -> None:
        """이벤트 처리"""
        try:
            if event.type == "tmdb_client_ready":
                self._set_tmdb_client(event.data)
            elif event.type == "tmdb_search_requested":
                self._handle_search_request(event.data)
            elif event.type == "tmdb_batch_search_requested":
                self._start_batch_search(event.data)
            elif event.type == "tmdb_anime_selected":
                self._handle_anime_selection(event.data)
            elif event.type == "tmdb_search_cancelled":
                self._handle_search_cancellation(event.data)
            elif event.type == "grouped_items_ready":
                self._auto_start_search_for_groups(event.data)
        except Exception as e:
            self.logger.error(f"이벤트 처리 실패: {event.type} - {e}")

    def _setup_event_subscriptions(self) -> None:
        """이벤트 구독 설정"""
        self.event_bus.subscribe("tmdb_client_ready", self.handle_event)
        self.event_bus.subscribe("tmdb_search_requested", self.handle_event)
        self.event_bus.subscribe("tmdb_batch_search_requested", self.handle_event)
        self.event_bus.subscribe("tmdb_anime_selected", self.handle_event)
        self.event_bus.subscribe("tmdb_search_cancelled", self.handle_event)
        self.event_bus.subscribe("grouped_items_ready", self.handle_event)

    def _cleanup_event_subscriptions(self) -> None:
        """이벤트 구독 해제"""
        self.event_bus.unsubscribe("tmdb_client_ready", self.handle_event)
        self.event_bus.unsubscribe("tmdb_search_requested", self.handle_event)
        self.event_bus.unsubscribe("tmdb_batch_search_requested", self.handle_event)
        self.event_bus.unsubscribe("tmdb_anime_selected", self.handle_event)
        self.event_bus.unsubscribe("tmdb_search_cancelled", self.handle_event)
        self.event_bus.unsubscribe("grouped_items_ready", self.handle_event)

    def _set_tmdb_client(self, tmdb_client: TMDBClient) -> None:
        """TMDB 클라이언트 설정"""
        self.tmdb_client = tmdb_client
        self.logger.info("TMDB 클라이언트 설정 완료")

    def _handle_search_request(self, data: dict[str, Any]) -> None:
        """개별 검색 요청 처리"""
        try:
            group_id = data.get("group_id")
            title = data.get("title")
            if not group_id or not title:
                self.logger.warning("검색 요청에 필수 정보가 없습니다")
                return
            if not self.tmdb_client:
                self.logger.warning("TMDB 클라이언트가 초기화되지 않았습니다")
                self.event_bus.publish("error_occurred", "TMDB API 키가 설정되지 않았습니다")
                return
            self.logger.info(f"TMDB 검색 시작: '{title}' (그룹 {group_id})")
            search_results = self.tmdb_client.search_anime(title, use_fallback=True)
            if len(search_results) == 1 and self.config["auto_select_single_result"]:
                selected_anime = search_results[0]
                self.logger.info(f"검색 결과 1개 - 자동 선택: {selected_anime.name}")
                self._handle_anime_selection({"group_id": group_id, "anime": selected_anime})
            elif len(search_results) == 0 and self.config["show_dialog_for_no_results"]:
                self.logger.info("검색 결과 없음 - 다이얼로그 표시")
                self._show_search_dialog(group_id, title, [])
            elif len(search_results) > 1 and self.config["show_dialog_for_multiple_results"]:
                self.logger.info(f"검색 결과 {len(search_results)}개 - 다이얼로그 표시")
                self._show_search_dialog(group_id, title, search_results)
            else:
                self.logger.info(f"검색 결과 {len(search_results)}개 - 다이얼로그 건너뜀")
                self._process_next_search()
        except Exception as e:
            self.logger.error(f"TMDB 검색 실패: {e}")
            self.event_bus.publish("error_occurred", f"TMDB 검색 실패: {str(e)}")
            self._process_next_search()

    def _show_search_dialog(
        self, group_id: str, title: str, search_results: list[TMDBAnimeInfo]
    ) -> None:
        """검색 다이얼로그 표시"""
        try:
            if group_id in self.search_dialogs:
                dialog = self.search_dialogs[group_id]
                if dialog.isVisible():
                    dialog.raise_()
                    dialog.activateWindow()
                    return
            if len(self.search_dialogs) >= self.config["max_concurrent_dialogs"]:
                self.logger.warning(
                    f"최대 다이얼로그 수 제한 ({self.config['max_concurrent_dialogs']})"
                )
                return
            dialog = TMDBSearchDialog(
                title, self.tmdb_client, self.parent_widget, "", title, search_results
            )
            dialog.anime_selected.connect(
                lambda anime: self._handle_anime_selection({"group_id": group_id, "anime": anime})
            )
            dialog.search_cancelled.connect(
                lambda: self._handle_search_cancellation({"group_id": group_id})
            )
            self.search_dialogs[group_id] = dialog
            dialog.show()
            self.logger.info(f"TMDB 검색 다이얼로그 표시: {title} (그룹 {group_id})")
        except Exception as e:
            self.logger.error(f"검색 다이얼로그 표시 실패: {e}")
            self._process_next_search()

    def _handle_anime_selection(self, data: dict[str, Any]) -> None:
        """애니메이션 선택 처리"""
        try:
            group_id = data.get("group_id")
            anime = data.get("anime")
            if not group_id or not anime:
                self.logger.warning("애니메이션 선택 데이터가 유효하지 않습니다")
                return
            self.tmdb_matches[group_id] = anime
            if group_id in self.search_dialogs:
                dialog = self.search_dialogs[group_id]
                dialog.close()
                del self.search_dialogs[group_id]
            self.event_bus.publish("tmdb_match_completed", {"group_id": group_id, "anime": anime})
            self.logger.info(f"TMDB 매칭 완료: {anime.name} (그룹 {group_id})")
            self._process_next_search()
        except Exception as e:
            self.logger.error(f"애니메이션 선택 처리 실패: {e}")
            self._process_next_search()

    def _handle_search_cancellation(self, data: dict[str, Any]) -> None:
        """검색 취소 처리"""
        try:
            group_id = data.get("group_id")
            if not group_id:
                return
            if group_id in self.search_dialogs:
                dialog = self.search_dialogs[group_id]
                dialog.close()
                del self.search_dialogs[group_id]
            self.logger.info(f"TMDB 검색 취소: 그룹 {group_id}")
            self._process_next_search()
        except Exception as e:
            self.logger.error(f"검색 취소 처리 실패: {e}")
            self._process_next_search()

    def _auto_start_search_for_groups(self, grouped_items: dict[str, list]) -> None:
        """그룹화 완료 후 자동 검색 시작"""
        try:
            if not self.tmdb_client:
                self.logger.warning("TMDB 클라이언트가 없어 자동 검색을 건너뜁니다")
                return
            search_groups = []
            for group_id, group_items in grouped_items.items():
                if group_id == "ungrouped":
                    continue
                if group_id in self.tmdb_matches:
                    continue
                if group_items and len(group_items) > 0:
                    group_title = group_items[0].title or group_items[0].detectedTitle or "Unknown"
                    search_groups.append((group_id, group_title))
            if search_groups:
                self.logger.info(f"자동 TMDB 검색 시작: {len(search_groups)}개 그룹")
                self._start_batch_search(search_groups)
            else:
                self.logger.info("검색할 그룹이 없습니다")
        except Exception as e:
            self.logger.error(f"자동 검색 시작 실패: {e}")

    def _start_batch_search(self, search_groups: list[tuple[str, str]]) -> None:
        """배치 검색 시작"""
        try:
            if self.is_batch_searching:
                self.logger.warning("이미 배치 검색이 진행 중입니다")
                return
            self.pending_search_groups = search_groups.copy()
            self.is_batch_searching = True
            self.event_bus.publish(
                "status_update",
                {"message": f"TMDB 검색 시작: {len(search_groups)}개 그룹 (순차적 처리)"},
            )
            self._process_next_search()
        except Exception as e:
            self.logger.error(f"배치 검색 시작 실패: {e}")
            self.is_batch_searching = False

    def _process_next_search(self) -> None:
        """다음 검색 처리"""
        try:
            if not self.is_batch_searching or not self.pending_search_groups:
                if self.is_batch_searching:
                    self.is_batch_searching = False
                    self.event_bus.publish(
                        "tmdb_batch_search_completed", {"matches_count": len(self.tmdb_matches)}
                    )
                    self.logger.info("모든 TMDB 검색이 완료되었습니다")
                return
            group_id, group_title = self.pending_search_groups.pop(0)
            remaining_count = len(self.pending_search_groups)
            self.event_bus.publish(
                "status_update",
                {"message": f"TMDB 검색 중: {group_title} ({remaining_count}개 남음)"},
            )
            QTimer.singleShot(
                self.config["search_delay_ms"],
                lambda: self._handle_search_request({"group_id": group_id, "title": group_title}),
            )
        except Exception as e:
            self.logger.error(f"다음 검색 처리 실패: {e}")
            self.is_batch_searching = False

    def _stop_batch_search(self) -> None:
        """배치 검색 중단"""
        if self.is_batch_searching:
            self.is_batch_searching = False
            self.pending_search_groups.clear()
            self.logger.info("배치 검색이 중단되었습니다")

    def _close_all_dialogs(self) -> None:
        """모든 검색 다이얼로그 닫기"""
        for group_id, dialog in list(self.search_dialogs.items()):
            try:
                dialog.close()
            except Exception as e:
                self.logger.error(f"다이얼로그 닫기 실패 ({group_id}): {e}")
        self.search_dialogs.clear()
        self.logger.info("모든 TMDB 검색 다이얼로그가 닫혔습니다")

    def get_match_for_group(self, group_id: str) -> TMDBAnimeInfo | None:
        """그룹의 TMDB 매칭 결과 반환"""
        return self.tmdb_matches.get(group_id)

    def set_match_for_group(self, group_id: str, anime: TMDBAnimeInfo) -> None:
        """그룹의 TMDB 매칭 결과 설정"""
        self.tmdb_matches[group_id] = anime
        self.event_bus.publish("tmdb_match_updated", {"group_id": group_id, "anime": anime})

    def clear_match_for_group(self, group_id: str) -> None:
        """그룹의 TMDB 매칭 결과 제거"""
        if group_id in self.tmdb_matches:
            del self.tmdb_matches[group_id]
            self.event_bus.publish("tmdb_match_cleared", {"group_id": group_id})

    def get_search_stats(self) -> dict[str, Any]:
        """검색 통계 반환"""
        return {
            "is_batch_searching": self.is_batch_searching,
            "pending_searches": len(self.pending_search_groups),
            "active_dialogs": len(self.search_dialogs),
            "total_matches": len(self.tmdb_matches),
            "has_tmdb_client": self.tmdb_client is not None,
        }

    def configure(self, config: dict[str, Any]) -> None:
        """설정 업데이트"""
        self.config.update(config)
        self.logger.debug(f"TMDBController 설정 업데이트: {config}")
