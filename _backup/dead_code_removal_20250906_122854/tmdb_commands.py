"""
TMDB 관련 명령들

TMDB 검색, 애니메이션 선택, 그룹 건너뛰기 등의 명령을 포함합니다.
"""

from core.tmdb_client import TMDBAnimeInfo

from .base_command import BaseCommand, CommandResult


class StartTMDBSearchCommand(BaseCommand):
    """TMDB 검색 시작 명령"""

    def __init__(self, event_bus, group_keys: list[str] = None):
        super().__init__(event_bus, "TMDB 검색 시작")
        self.group_keys = group_keys or []
        self._previous_matches = {}

    def _execute_impl(self) -> CommandResult:
        """TMDB 검색 시작"""
        try:
            # 이벤트 버스에 TMDB 검색 시작 알림
            if self.event_bus:
                if self.group_keys:
                    self.event_bus.publish("start_tmdb_search_for_groups", self.group_keys)
                else:
                    self.event_bus.publish("start_tmdb_search", None)

            return CommandResult(success=True, message="TMDB 검색을 시작합니다.")

        except Exception as e:
            return CommandResult(success=False, message=f"TMDB 검색 시작 실패: {str(e)}", error=e)

    def can_execute(self) -> bool:
        """명령 실행 가능 여부 확인"""
        return True  # TMDB 검색 시작은 항상 가능

    def _save_state_for_undo(self):
        """실행 취소를 위한 상태 저장"""
        # TMDB 검색 시작은 실행 취소 불가능
        self._can_undo = False
        self._undo_data = None


class SelectTMDBAnimeCommand(BaseCommand):
    """TMDB 애니메이션 선택 명령"""

    def __init__(self, event_bus, group_key: str, anime_info: TMDBAnimeInfo):
        super().__init__(event_bus, "TMDB 애니메이션 선택")
        self.group_key = group_key
        self.anime_info = anime_info
        self._previous_match = None

    def _execute_impl(self) -> CommandResult:
        """TMDB 애니메이션 선택"""
        try:
            # 이벤트 버스에 TMDB 애니메이션 선택 알림
            if self.event_bus:
                self.event_bus.publish(
                    "tmdb_anime_selected",
                    {"group_key": self.group_key, "anime_info": self.anime_info},
                )

            return CommandResult(
                success=True,
                message=f"TMDB 애니메이션 선택됨: {self.anime_info.name}",
                data={"group_key": self.group_key, "anime_info": self.anime_info},
            )

        except Exception as e:
            return CommandResult(
                success=False, message=f"TMDB 애니메이션 선택 실패: {str(e)}", error=e
            )

    def can_execute(self) -> bool:
        """명령 실행 가능 여부 확인"""
        return bool(self.group_key and self.anime_info)  # 그룹 키와 애니메이션 정보가 있어야 함

    def _save_state_for_undo(self):
        """실행 취소를 위한 상태 저장"""
        # 이벤트 버스에서 이전 매치 정보 가져오기
        if self.event_bus:
            tmdb_matches = self.event_bus.publish("get_all_tmdb_matches", [])
            self._previous_match = tmdb_matches.get(self.group_key)
            self._can_undo = True
            self._undo_data = {"group_key": self.group_key, "previous_match": self._previous_match}
        else:
            self._can_undo = False
            self._undo_data = None

    def _undo_impl(self) -> CommandResult:
        """실행 취소 구현"""
        try:
            # 이벤트 버스에 이전 매치로 복원 알림
            if self.event_bus and self._undo_data:
                self.event_bus.publish("tmdb_match_restored", self._undo_data)

            return CommandResult(
                success=True, message=f"TMDB 애니메이션 선택 취소됨: {self.group_key}"
            )

        except Exception as e:
            return CommandResult(
                success=False, message=f"TMDB 애니메이션 선택 취소 실패: {str(e)}", error=e
            )


class SkipTMDBGroupCommand(BaseCommand):
    """TMDB 그룹 건너뛰기 명령"""

    def __init__(self, event_bus, group_key: str):
        super().__init__(event_bus, "TMDB 그룹 건너뛰기")
        self.group_key = group_key
        self._previous_match = None

    def _execute_impl(self) -> CommandResult:
        """TMDB 그룹 건너뛰기"""
        try:
            # 이벤트 버스에 TMDB 그룹 건너뛰기 알림
            if self.event_bus:
                self.event_bus.publish("tmdb_group_skipped", self.group_key)

            return CommandResult(success=True, message=f"TMDB 그룹 건너뛰기: {self.group_key}")

        except Exception as e:
            return CommandResult(
                success=False, message=f"TMDB 그룹 건너뛰기 실패: {str(e)}", error=e
            )

    def _save_state_for_undo(self):
        """실행 취소를 위한 상태 저장"""
        # TMDB 그룹 건너뛰기는 실행 취소 불가능
        self._can_undo = False
        self._undo_data = None
