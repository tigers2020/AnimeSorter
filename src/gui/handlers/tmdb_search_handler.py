#!/usr/bin/env python3
"""
TMDB Search Handler for MainWindow

MainWindow의 TMDB 검색 관련 메서드들을 관리하는 클래스입니다.
TMDB 검색, 다이얼로그 관리, 순차적 검색을 담당합니다.
"""

import logging

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMainWindow

from ..components.tmdb_search_dialog import TMDBSearchDialog


class TMDBSearchHandler:
    """TMDB 검색 관련 메서드들을 관리하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        """TMDBSearchHandler 초기화"""
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # TMDB 검색 관련 상태
        self.tmdb_search_dialogs: dict[str, TMDBSearchDialog] = {}
        self.pending_tmdb_groups: list[tuple[str, str]] = []

    def on_tmdb_search_requested(self, group_id: str):
        """TMDB 검색 요청 처리"""
        print(f"🔍 on_tmdb_search_requested 호출됨: {group_id}")
        self.logger.info(f"🔍 on_tmdb_search_requested 호출됨: {group_id}")
        self._perform_tmdb_search(group_id)

    def _perform_tmdb_search(self, group_id: str):
        """TMDB 검색 직접 수행"""
        try:
            # 그룹 정보 가져오기
            grouped_items = self.main_window.anime_data_manager.get_grouped_items()
            if group_id not in grouped_items:
                self.logger.error(f"❌ 그룹 {group_id}를 찾을 수 없습니다")
                return

            group_items = grouped_items[group_id]
            if not group_items:
                self.logger.error(f"❌ 그룹 {group_id}에 아이템이 없습니다")
                return

            # 그룹 제목 가져오기
            group_title = group_items[0].title or group_items[0].detectedTitle or "Unknown"
            self.logger.info(f"🔍 TMDB 검색 시작: {group_title} (그룹 {group_id})")

            # TMDB 검색 실행
            if not self.main_window.tmdb_client:
                self.logger.error("❌ TMDB 클라이언트가 초기화되지 않았습니다")
                return

            self.logger.info(f"🔍 TMDB API 호출 시작: {group_title}")
            search_results = self.main_window.tmdb_client.search_anime(group_title)
            self.logger.info(f"🔍 TMDB API 호출 완료: {len(search_results)}개 결과")

            if len(search_results) == 1:
                # 결과가 1개면 자동 선택
                selected_anime = search_results[0]
                self.logger.info(f"✅ 검색 결과 1개 - 자동 선택: {selected_anime.name}")
                try:
                    self.on_tmdb_anime_selected(group_id, selected_anime)
                    return
                except Exception as e:
                    self.logger.error(f"❌ 자동 선택 실패: {e}")

            # 다이얼로그 표시
            self._show_search_dialog(group_id, group_title, search_results)

        except Exception as e:
            self.logger.error(f"❌ TMDB 검색 실패: {e}")

    def _show_search_dialog(self, group_id: str, group_title: str, search_results: list = None):
        """검색 다이얼로그 표시"""
        try:
            # 이미 열린 다이얼로그가 있으면 포커스
            if group_id in self.tmdb_search_dialogs:
                dialog = self.tmdb_search_dialogs[group_id]
                if dialog.isVisible():
                    dialog.raise_()
                    dialog.activateWindow()
                    return

            # 새 다이얼로그 생성
            dialog = TMDBSearchDialog(group_title, self.main_window.tmdb_client, self.main_window)
            dialog.anime_selected.connect(
                lambda anime: self.on_tmdb_anime_selected(group_id, anime)
            )

            # 다이얼로그 저장
            self.tmdb_search_dialogs[group_id] = dialog

            # 검색 결과가 있으면 미리 설정
            if search_results:
                dialog.set_search_results(search_results)

            # 다이얼로그 표시
            dialog.show()
            dialog.raise_()  # 다이얼로그를 맨 앞으로 가져오기
            dialog.activateWindow()  # 다이얼로그 활성화

            self.logger.info(f"✅ TMDB 검색 다이얼로그 표시됨: {group_title}")

        except Exception as e:
            self.logger.error(f"❌ TMDB 검색 다이얼로그 생성 실패: {e}")
            self.main_window.update_status_bar(f"TMDB 검색 다이얼로그 생성 실패: {str(e)}")

    def on_tmdb_anime_selected(self, group_id: str, tmdb_anime):
        """TMDB 애니메이션 선택 처리"""
        try:
            # 데이터 관리자에 TMDB 매치 결과 설정
            self.main_window.anime_data_manager.set_tmdb_match_for_group(group_id, tmdb_anime)

            # 그룹 모델 업데이트
            self.update_group_model()

            # 상태바 업데이트 (name 속성 사용)
            self.main_window.update_status_bar(f"✅ {tmdb_anime.name} 매치 완료")

            # 다이얼로그 닫기
            if group_id in self.tmdb_search_dialogs:
                dialog = self.tmdb_search_dialogs[group_id]
                dialog.close()
                del self.tmdb_search_dialogs[group_id]

            # 순차적 처리를 위해 다음 그룹 처리 (잠시 대기 후)
            QTimer.singleShot(500, self.process_next_tmdb_group)

        except Exception as e:
            self.logger.error(f"❌ TMDB 애니메이션 선택 처리 실패: {e}")
            # 에러가 발생해도 다음 그룹 처리
            QTimer.singleShot(500, self.process_next_tmdb_group)

    def update_group_model(self):
        """그룹 모델 업데이트"""
        try:
            if hasattr(self.main_window, "grouped_model"):
                grouped_items = self.main_window.anime_data_manager.get_grouped_items()
                self.main_window.grouped_model.set_grouped_items(grouped_items)
        except Exception as e:
            self.logger.error(f"❌ 그룹 모델 업데이트 실패: {e}")

    def reset_for_new_scan(self):
        """새로운 스캔을 위한 TMDB 검색 상태 초기화"""
        try:
            # 진행 중인 검색 중단
            self.pending_tmdb_groups = []

            # 모든 다이얼로그 닫기
            self.close_all_dialogs()

            # AnimeDataManager의 TMDB 매치 정보 초기화
            if hasattr(self.main_window, "anime_data_manager"):
                self.main_window.anime_data_manager.clear_tmdb_matches()

            self.logger.info("🔄 새로운 스캔을 위해 TMDB 검색 상태가 초기화되었습니다")

        except Exception as e:
            self.logger.error(f"❌ TMDB 검색 상태 초기화 실패: {e}")

    def start_tmdb_search_for_groups(self):
        """그룹화 후 TMDB 검색 시작 (순차적 처리)"""
        try:
            if not self.main_window.tmdb_client:
                self.logger.warning("⚠️ TMDB 클라이언트가 초기화되지 않아 검색을 건너뜁니다")
                self.main_window.update_status_bar("TMDB API 키가 설정되지 않아 검색을 건너뜁니다")
                return

            grouped_items = self.main_window.anime_data_manager.get_grouped_items()
            self.pending_tmdb_groups = []

            # 검색할 그룹들을 수집
            for group_id, group_items in grouped_items.items():
                if group_id == "ungrouped":
                    continue

                # 이미 TMDB 매치가 있는 그룹은 건너뛰기
                if self.main_window.anime_data_manager.get_tmdb_match_for_group(group_id):
                    continue

                # 그룹 제목으로 TMDB 검색 대기열에 추가
                group_title = group_items[0].title or group_items[0].detectedTitle or "Unknown"
                self.pending_tmdb_groups.append((group_id, group_title))

            if self.pending_tmdb_groups:
                self.logger.info(
                    f"🔍 {len(self.pending_tmdb_groups)}개 그룹에 대해 순차적 TMDB 검색을 시작합니다"
                )
                self.main_window.update_status_bar(
                    f"TMDB 검색 시작: {len(self.pending_tmdb_groups)}개 그룹 (순차적 처리)"
                )
                # TMDB 검색 중 파일 정리 버튼 및 메뉴 비활성화
                if hasattr(self.main_window, "main_toolbar"):
                    self.main_window.main_toolbar.set_organize_enabled(False)
                # 메뉴 항목도 비활성화
                if hasattr(self.main_window, "window_manager") and hasattr(
                    self.main_window.window_manager, "menu_actions"
                ):
                    if "organize" in self.main_window.window_manager.menu_actions:
                        self.main_window.window_manager.menu_actions["organize"].setEnabled(False)
                # 첫 번째 그룹부터 시작
                self.process_next_tmdb_group()
            else:
                self.logger.info("✅ 모든 그룹이 이미 TMDB 매치가 완료되었습니다")
                self.main_window.update_status_bar("모든 그룹의 TMDB 매치가 완료되었습니다")

        except Exception as e:
            self.logger.error(f"❌ TMDB 검색 시작 실패: {e}")
            self.main_window.update_status_bar(f"TMDB 검색 시작 실패: {str(e)}")
            # TMDB 검색 실패 시 파일 정리 버튼 및 메뉴 다시 활성화
            if hasattr(self.main_window, "main_toolbar"):
                self.main_window.main_toolbar.set_organize_enabled(True)
            # 메뉴 항목도 다시 활성화
            if hasattr(self.main_window, "window_manager") and hasattr(
                self.main_window.window_manager, "menu_actions"
            ):
                if "organize" in self.main_window.window_manager.menu_actions:
                    self.main_window.window_manager.menu_actions["organize"].setEnabled(True)

    def process_next_tmdb_group(self):
        """다음 TMDB 그룹 처리"""
        if not self.pending_tmdb_groups:
            self.logger.info("✅ 모든 TMDB 검색이 완료되었습니다")
            self.main_window.update_status_bar("모든 TMDB 검색이 완료되었습니다")
            # TMDB 검색 완료 후 파일 정리 버튼 및 메뉴 다시 활성화
            if hasattr(self.main_window, "main_toolbar"):
                self.main_window.main_toolbar.set_organize_enabled(True)
            # 메뉴 항목도 다시 활성화
            if hasattr(self.main_window, "window_manager") and hasattr(
                self.main_window.window_manager, "menu_actions"
            ):
                if "organize" in self.main_window.window_manager.menu_actions:
                    self.main_window.window_manager.menu_actions["organize"].setEnabled(True)
            return

        group_id, group_title = self.pending_tmdb_groups.pop(0)
        self.logger.info(
            f"🔍 TMDB 검색 시작: '{group_title}' (그룹 {group_id}) - {len(self.pending_tmdb_groups)}개 남음"
        )
        self.main_window.update_status_bar(
            f"TMDB 검색 중: {group_title} ({len(self.pending_tmdb_groups)}개 남음)"
        )

        # 현재 그룹에 대해 TMDB 검색 시작 (직접 다이얼로그 표시)
        self.main_window.show_tmdb_dialog_for_group(group_id)

    def close_all_dialogs(self):
        """모든 TMDB 검색 다이얼로그 닫기"""
        try:
            for dialog in self.tmdb_search_dialogs.values():
                if dialog.isVisible():
                    dialog.close()
            self.tmdb_search_dialogs.clear()
            self.logger.info("✅ 모든 TMDB 검색 다이얼로그가 닫혔습니다")
        except Exception as e:
            self.logger.error(f"❌ 다이얼로그 닫기 실패: {e}")

    def get_pending_groups_count(self) -> int:
        """대기 중인 그룹 수 반환"""
        return len(self.pending_tmdb_groups)

    def is_search_in_progress(self) -> bool:
        """검색이 진행 중인지 확인"""
        return len(self.pending_tmdb_groups) > 0 or len(self.tmdb_search_dialogs) > 0

    # === 이벤트 핸들러 메서드들 ===

    def handle_search_started(self, event):
        """TMDB 검색 시작 이벤트 처리"""
        try:
            self.logger.info(f"🔍 [TMDBSearchHandler] TMDB 검색 시작: {event.search_id}")
            self.main_window.update_status_bar("TMDB 검색 시작됨")
        except Exception as e:
            self.logger.error(f"❌ TMDB 검색 시작 이벤트 처리 중 오류: {e}")

    def handle_search_completed(self, event):
        """TMDB 검색 완료 이벤트 처리"""
        try:
            self.logger.info(
                f"✅ [TMDBSearchHandler] TMDB 검색 완료: {event.search_id} - {len(event.results)}개 결과"
            )
            self.main_window.update_status_bar("TMDB 검색 완료")
        except Exception as e:
            self.logger.error(f"❌ TMDB 검색 완료 이벤트 처리 중 오류: {e}")

    def handle_match_found(self, event):
        """TMDB 매치 발견 이벤트 처리"""
        try:
            self.logger.info(
                f"🎯 [TMDBSearchHandler] TMDB 매치 발견: {event.anime_title} (ID: {event.tmdb_id})"
            )
            self.main_window.update_status_bar(f"TMDB 매치 발견: {event.anime_title}")
        except Exception as e:
            self.logger.error(f"❌ TMDB 매치 발견 이벤트 처리 중 오류: {e}")
