"""
애니메이션 데이터 관리자
파싱된 애니메이션 파일들의 데이터를 관리하고 그룹화하는 기능을 제공합니다.
"""

import re
# 상대 경로로 수정
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal

sys.path.append(str(Path(__file__).parent.parent.parent))
from core.unified_event_system import (EventCategory, EventPriority,
                                       get_unified_event_bus)

sys.path.append(str(Path(__file__).parent.parent.parent))
from core.tmdb_client import TMDBAnimeInfo


@dataclass
class ParsedItem:
    """파싱된 애니메이션 파일 정보"""

    id: str = None
    status: str = "pending"  # 'parsed' | 'needs_review' | 'error' | 'skipped'
    sourcePath: str = ""
    detectedTitle: str = ""
    filename: str = ""  # 파일명만
    path: str = ""  # 전체 경로
    title: str = ""  # 파싱된 제목
    season: int | None = None
    episode: int | None = None
    year: int | None = None
    tmdbId: int | None = None
    resolution: str | None = None
    group: str | None = None
    codec: str | None = None
    container: str | None = None
    sizeMB: int | None = None
    message: str | None = None
    tmdbMatch: TMDBAnimeInfo | None = None  # TMDB 매치 결과
    parsingConfidence: float | None = None  # 파싱 신뢰도
    groupId: str | None = None  # 그룹 ID (동일 제목 파일들을 묶음)
    normalizedTitle: str | None = None  # 정규화된 제목 (그룹화용)

    def __post_init__(self):
        """초기화 후 처리"""
        if not self.id:
            import uuid

            self.id = str(uuid.uuid4())[:8]
        if not self.filename and self.sourcePath:
            from pathlib import Path

            self.filename = Path(self.sourcePath).name
        if not self.path and self.sourcePath:
            self.path = self.sourcePath
        if not self.title and self.detectedTitle:
            self.title = self.detectedTitle


class AnimeDataManager(QObject):
    """애니메이션 데이터 관리자"""

    # 시그널 정의
    tmdb_search_requested = pyqtSignal(str)  # TMDB 검색 요청
    tmdb_anime_selected = pyqtSignal(
        str, object
    )  # TMDB 애니메이션 선택됨 (group_id, TMDBAnimeInfo)

    def __init__(self, tmdb_client=None):
        super().__init__()
        self.items: list[ParsedItem] = []
        self.tmdb_client = tmdb_client
        self.group_tmdb_matches = {}  # 그룹별 TMDB 매치 결과 저장

        # 통합 이벤트 시스템 초기화
        self.unified_event_bus = get_unified_event_bus()

    def add_item(self, item: ParsedItem):
        """아이템 추가"""
        self.items.append(item)

        # 통합 이벤트 시스템을 통해 이벤트 발행
        if self.unified_event_bus:
            from core.unified_event_system import BaseEvent

            event = BaseEvent(
                source="AnimeDataManager",
                category=EventCategory.MEDIA,
                priority=EventPriority.NORMAL,
                metadata={"item_id": item.id, "title": item.title},
            )
            self.unified_event_bus.publish(event)

    def add_items(self, items: list[ParsedItem]):
        """여러 아이템 추가"""
        self.items.extend(items)

    def get_items(self) -> list[ParsedItem]:
        """모든 아이템 반환"""
        return self.items

    def get_item_by_id(self, item_id: str) -> ParsedItem | None:
        """ID로 아이템 찾기"""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def update_item_status(self, item_id: str, status: str):
        """아이템 상태 업데이트"""
        item = self.get_item_by_id(item_id)
        if item:
            item.status = status

    def clear_completed_items(self):
        """완료된 아이템들 제거"""
        self.items = [item for item in self.items if item.status != "parsed"]

    def get_stats(self) -> dict:
        """통계 정보 반환"""
        total = len(self.items)
        parsed = len([item for item in self.items if item.status == "parsed"])
        pending = len([item for item in self.items if item.status == "pending"])
        needs_review = len([item for item in self.items if item.status == "needs_review"])
        error = len([item for item in self.items if item.status == "error"])
        skipped = len([item for item in self.items if item.status == "skipped"])

        # 그룹 수 계산
        groups = self.get_grouped_items()
        group_count = len(groups)

        return {
            "total": total,
            "parsed": parsed,
            "pending": pending,
            "needs_review": needs_review,
            "error": error,
            "skipped": skipped,
            "groups": group_count,
        }

    def normalize_title_for_grouping(self, title: str) -> str:
        """제목을 그룹화용으로 정규화"""
        if not title:
            return ""

        # 소문자로 변환
        normalized = title.lower()

        # 특수문자 및 공백 제거
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)

        # 일반적인 애니메이션 제목 패턴 정리
        patterns_to_remove = [
            r"\bthe\b",
            r"\banimation\b",
            r"\banime\b",
            r"\btv\b",
            r"\bseries\b",
            r"\bseason\b",
            r"\bepisode\b",
            r"\bep\b",
            r"\bova\b",
            r"\bmovie\b",
        ]

        for pattern in patterns_to_remove:
            normalized = re.sub(pattern, "", normalized)

        # 앞뒤 공백 제거
        return normalized.strip()

    def group_similar_titles(self) -> list[ParsedItem]:
        """유사한 제목을 가진 파일들을 그룹화"""
        if not self.items:
            return self.items

        # 제목 정규화 및 그룹 ID 할당
        title_groups = {}  # 정규화된 제목 -> 그룹 ID 매핑
        group_counter = 1

        for item in self.items:
            if not item.title:
                continue

            # 제목 정규화
            normalized_title = self.normalize_title_for_grouping(item.title)
            item.normalizedTitle = normalized_title

            # 유사한 제목이 있는지 확인 (Levenshtein 거리 기반)
            best_match = None
            best_similarity = 0.8  # 최소 유사도 임계값

            for existing_title, _group_id in title_groups.items():
                similarity = self.calculate_title_similarity(normalized_title, existing_title)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = existing_title

            if best_match:
                # 기존 그룹에 추가
                item.groupId = title_groups[best_match]
                print(
                    f"🔗 그룹화: '{item.title}' → 그룹 {item.groupId} (유사도: {best_similarity:.2f})"
                )
            else:
                # 새 그룹 생성
                new_group_id = f"group_{group_counter:03d}"
                item.groupId = new_group_id
                title_groups[normalized_title] = new_group_id
                group_counter += 1
                print(f"🆕 새 그룹 생성: '{item.title}' → 그룹 {new_group_id}")

        # 그룹화 완료 후 결과 출력
        print(f"✅ 그룹화 완료: {len(self.items)}개 파일 → {len(title_groups)}개 그룹")

        return self.items

    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """두 제목 간의 유사도 계산 (0.0 ~ 1.0)"""
        if not title1 or not title2:
            return 0.0

        # 간단한 유사도 계산 (공통 단어 기반)
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        if not words1 or not words2:
            return 0.0

        # Jaccard 유사도
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        if union == 0:
            return 0.0

        jaccard_similarity = intersection / union

        # 추가 가중치: 제목 길이 유사성
        length_diff = abs(len(title1) - len(title2))
        max_length = max(len(title1), len(title2))
        length_similarity = 1.0 - (length_diff / max_length) if max_length > 0 else 0.0

        # 최종 유사도 (Jaccard 70%, 길이 30%)
        return (jaccard_similarity * 0.7) + (length_similarity * 0.3)

    def get_grouped_items(self) -> dict:
        """그룹별로 정리된 아이템들 반환"""
        groups = {}
        for item in self.items:
            group_id = item.groupId or "ungrouped"
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(item)

        # ungrouped 그룹이 비어있으면 제거
        if "ungrouped" in groups and not groups["ungrouped"]:
            del groups["ungrouped"]

        # 로그 출력 제거 - 반복 호출 시 중복 로그 방지
        # print(f"📊 그룹별 아이템 반환: {len(groups)}개 그룹")
        return groups

    def search_tmdb_for_group(self, group_id: str, group_title: str):
        """그룹에 대한 TMDB 검색 실행"""
        if not self.tmdb_client:
            print("❌ TMDB 클라이언트가 초기화되지 않았습니다")
            return

        print(f"🔍 TMDB 검색 시작: '{group_title}' (그룹 {group_id})")
        print(f"🔍 시그널 발행: tmdb_search_requested.emit({group_id})")
        self.tmdb_search_requested.emit(group_id)
        print(f"🔍 시그널 발행 완료: {group_id}")

    def set_tmdb_match_for_group(self, group_id: str, tmdb_anime: TMDBAnimeInfo):
        """그룹에 TMDB 매치 결과 설정"""
        self.group_tmdb_matches[group_id] = tmdb_anime

        # 해당 그룹의 모든 아이템에 TMDB 정보 업데이트
        for item in self.items:
            if item.groupId == group_id:
                item.tmdbMatch = tmdb_anime
                item.tmdbId = tmdb_anime.id
                item.status = "tmdb_matched"

        print(f"✅ TMDB 매치 완료: 그룹 {group_id} → {tmdb_anime.name}")

    def get_tmdb_match_for_group(self, group_id: str) -> TMDBAnimeInfo | None:
        """그룹의 TMDB 매치 결과 반환"""
        return self.group_tmdb_matches.get(group_id)

    def clear_tmdb_matches(self):
        """모든 TMDB 매치 정보 초기화"""
        self.group_tmdb_matches.clear()

        # 모든 아이템의 TMDB 정보 초기화
        for item in self.items:
            item.tmdbMatch = None
            item.tmdbId = None
            if item.status == "tmdb_matched":
                item.status = "pending"

        print("🔄 모든 TMDB 매치 정보가 초기화되었습니다")

    def get_group_destination_path(self, group_id: str, base_destination: str) -> str:
        """그룹의 최종 이동 경로 생성"""
        tmdb_anime = self.get_tmdb_match_for_group(group_id)
        if not tmdb_anime:
            return str(Path(base_destination) / "Unknown")

        # TMDB 제목으로 폴더명 생성 (특수문자 제거)
        safe_title = re.sub(r'[<>:"/\\|?*]', "", tmdb_anime.name)

        # 그룹의 첫 번째 아이템에서 시즌 정보 가져오기
        group_items = [item for item in self.items if item.groupId == group_id]
        if group_items and group_items[0].season:
            season_folder = f"Season{group_items[0].season:02d}"
            return str(Path(base_destination) / safe_title / season_folder)
        return str(Path(base_destination) / safe_title)

    def get_group_display_info(self, group_id: str) -> dict:
        """그룹의 표시 정보 반환"""
        group_items = [item for item in self.items if item.groupId == group_id]
        if not group_items:
            return {}

        tmdb_anime = self.get_tmdb_match_for_group(group_id)

        # 에피소드 범위
        episodes = [item.episode for item in group_items if item.episode is not None]
        if episodes:
            min_ep = min(episodes)
            max_ep = max(episodes)
            episode_info = f"E{min_ep:02d}" if min_ep == max_ep else f"E{min_ep:02d}-E{max_ep:02d}"
        else:
            episode_info = "Unknown"

        # 해상도별 분포
        resolutions = {}
        for item in group_items:
            res = item.resolution or "Unknown"
            resolutions[res] = resolutions.get(res, 0) + 1

        return {
            "title": tmdb_anime.name if tmdb_anime else group_items[0].title,
            "original_title": tmdb_anime.original_name if tmdb_anime else None,
            "episode_info": episode_info,
            "file_count": len(group_items),
            "resolutions": resolutions,
            "tmdb_id": tmdb_anime.id if tmdb_anime else None,
            "poster_path": tmdb_anime.poster_path if tmdb_anime else None,
            "status": "tmdb_matched" if tmdb_anime else "pending",
        }

    def display_grouped_results(self):
        """그룹화된 결과를 출력"""
        if not self.items:
            return None

        # 그룹별로 정리
        groups = self.get_grouped_items()

        # 최종 결과만 깔끔하게 표시
        print(f"\n📊 스캔 결과: {len(self.items)}개 파일 → {len(groups)}개 그룹")

        for group_id, items in groups.items():
            if group_id == "ungrouped":
                continue

            # 그룹의 대표 제목
            title = items[0].title if items else "Unknown"

            # 에피소드 범위
            episodes = [item.episode for item in items if item.episode is not None]
            if episodes:
                min_ep = min(episodes)
                max_ep = max(episodes)
                if min_ep == max_ep:
                    episode_info = f"E{min_ep:02d}"
                else:
                    episode_info = f"E{min_ep:02d}-E{max_ep:02d}"
            else:
                episode_info = "Unknown"

            # 해상도별 분포
            resolutions = {}
            for item in items:
                res = item.resolution or "Unknown"
                resolutions[res] = resolutions.get(res, 0) + 1

            resolution_info = ", ".join([f"{res}: {count}" for res, count in resolutions.items()])

            print(f"🔗 {title} ({episode_info}) - {len(items)}개 파일 [{resolution_info}]")

        return groups
