"""
애니메이션 데이터 관리자
파싱된 애니메이션 파일들의 데이터를 관리하고 그룹화하는 기능을 제공합니다.
"""

import logging

logger = logging.getLogger(__name__)
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PyQt5.QtCore import pyqtSignal

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.core.manager_base import ManagerBase, ManagerConfig, ManagerPriority
from src.core.tmdb_client import TMDBAnimeInfo
from src.core.unified_event_system import EventCategory, EventPriority, get_unified_event_bus


@dataclass
class ParsedItem:
    """파싱된 애니메이션 파일 정보"""

    id: str = None
    status: str = "pending"
    sourcePath: str = ""
    detectedTitle: str = ""
    filename: str = ""
    path: str = ""
    title: str = ""
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
    tmdbMatch: TMDBAnimeInfo | None = None
    parsingConfidence: float | None = None
    groupId: str | None = None
    normalizedTitle: str | None = None

    # anitopy에서 추출할 수 있는 추가 정보들
    video_codec: str | None = None
    audio_codec: str | None = None
    release_group: str | None = None
    file_extension: str | None = None
    episode_title: str | None = None
    source: str | None = None  # TV, Web, Blu-ray 등
    quality: str | None = None  # HD, SD 등
    language: str | None = None
    subtitles: str | None = None
    crc32: str | None = None

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


class AnimeDataManager(ManagerBase):
    """애니메이션 데이터 관리자"""

    tmdb_search_requested = pyqtSignal(str)
    tmdb_anime_selected = pyqtSignal(str, object)

    def __init__(self, tmdb_client=None, parent=None):
        config = ManagerConfig(
            name="AnimeDataManager",
            priority=ManagerPriority.NORMAL,
            auto_start=True,
            log_level="INFO",
        )
        super().__init__(config, parent)
        self.items: list[ParsedItem] = []
        self.tmdb_client = tmdb_client
        self.group_tmdb_matches = {}
        self.unified_event_bus = get_unified_event_bus()
        self.logger.info(
            f"AnimeDataManager 초기화 완료 (TMDB 클라이언트: {'있음' if tmdb_client else '없음'})"
        )

    def set_tmdb_client(self, tmdb_client):
        """TMDB 클라이언트 설정"""
        self.tmdb_client = tmdb_client
        self.logger.info(f"TMDB 클라이언트 업데이트: {'있음' if tmdb_client else '없음'}")

    def add_item(self, item: ParsedItem):
        """아이템 추가"""
        self.items.append(item)
        if self.unified_event_bus:
            from src.core.unified_event_system import BaseEvent

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
        """제목을 그룹화용으로 정규화 (개선된 버전)"""
        if not title:
            return ""

        # 기본 정리
        normalized = title.strip()

        # 불필요한 접미사 제거 (괄호, 대괄호, 특수문자)
        suffixes_to_remove = [
            r"\s*\([^)]*\)\s*$",  # 괄호 안의 내용 제거
            r"\s*\[[^\]]*\]\s*$",  # 대괄호 안의 내용 제거
            r"\s*-\s*$",  # 끝의 대시 제거
            r"\s*\.\s*$",  # 끝의 점 제거
            r"\s*:\s*$",  # 끝의 콜론 제거
        ]

        for pattern in suffixes_to_remove:
            normalized = re.sub(pattern, "", normalized)

        # 소문자 변환
        normalized = normalized.lower()

        # 특수문자 제거 (한글, 영문, 숫자, 공백만 유지)
        normalized = re.sub(r"[^\w\s가-힣]", "", normalized)

        # 공백 정규화
        normalized = re.sub(r"\s+", " ", normalized)

        # 불필요한 단어 제거
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
            r"\bfilm\b",
            r"\bspecial\b",
        ]

        for pattern in patterns_to_remove:
            normalized = re.sub(pattern, "", normalized)

        # 최종 공백 정리
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized.strip()

    def group_similar_titles(self) -> list[ParsedItem]:
        """유사한 제목을 가진 파일들을 그룹화"""
        if not self.items:
            return self.items
        title_groups = {}
        group_counter = 1
        for item in self.items:
            if not item.title:
                continue
            normalized_title = self.normalize_title_for_grouping(item.title)
            item.normalizedTitle = normalized_title
            best_match = None
            best_similarity = 0.6  # 더 낮은 임계값으로 더 많은 유사 제목 그룹화
            for existing_title, _group_id in title_groups.items():
                similarity = self.calculate_title_similarity(normalized_title, existing_title)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = existing_title
            if best_match:
                item.groupId = title_groups[best_match]
                logger.info(
                    "🔗 그룹화: '%s' → 그룹 %s (유사도: %s)",
                    item.title,
                    item.groupId,
                    best_similarity,
                )
            else:
                new_group_id = f"group_{group_counter:03d}"
                item.groupId = new_group_id
                title_groups[normalized_title] = new_group_id
                group_counter += 1
                logger.info("🆕 새 그룹 생성: '%s' → 그룹 %s", item.title, new_group_id)
        logger.info("✅ 그룹화 완료: %s개 파일 → %s개 그룹", len(self.items), len(title_groups))
        return self.items

    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """두 제목 간의 유사도 계산 (0.0 ~ 1.0) - 개선된 버전"""
        if not title1 or not title2:
            return 0.0

        # 정확히 같은 경우
        if title1 == title2:
            return 1.0

        # 한쪽이 다른 쪽에 포함되는 경우
        if title1 in title2 or title2 in title1:
            return 0.9

        # 단어 기반 유사도 (Jaccard)
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        jaccard_similarity = intersection / union if union > 0 else 0.0

        # 문자열 유사도 (Levenshtein 기반)
        def levenshtein_ratio(s1: str, s2: str) -> float:
            if len(s1) < len(s2):
                return levenshtein_ratio(s2, s1)
            if len(s2) == 0:
                return 0.0

            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row

            max_len = max(len(s1), len(s2))
            return 1.0 - (previous_row[-1] / max_len) if max_len > 0 else 0.0

        string_similarity = levenshtein_ratio(title1.lower(), title2.lower())

        # 길이 유사도
        length_diff = abs(len(title1) - len(title2))
        max_length = max(len(title1), len(title2))
        length_similarity = 1.0 - (length_diff / max_length) if max_length > 0 else 0.0

        # 가중 평균 (단어 유사도 40%, 문자열 유사도 40%, 길이 유사도 20%)
        return jaccard_similarity * 0.4 + string_similarity * 0.4 + length_similarity * 0.2

    def get_grouped_items(self) -> dict:
        """그룹별로 정리된 아이템들 반환"""
        groups = {}
        for item in self.items:
            group_id = item.groupId or "ungrouped"
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(item)
        if "ungrouped" in groups and not groups["ungrouped"]:
            del groups["ungrouped"]
        return groups

    def _initialize_impl(self) -> bool:
        """구현체별 초기화 로직"""
        try:
            self.logger.info("AnimeDataManager 초기화 완료")
            return True
        except Exception as e:
            self.logger.error(f"초기화 실패: {e}")
            return False

    def _start_impl(self) -> bool:
        """구현체별 시작 로직"""
        try:
            self.logger.info("AnimeDataManager 시작")
            return True
        except Exception as e:
            self.logger.error(f"시작 실패: {e}")
            return False

    def _stop_impl(self) -> bool:
        """구현체별 중지 로직"""
        try:
            self.logger.info("AnimeDataManager 중지")
            return True
        except Exception as e:
            self.logger.error(f"중지 실패: {e}")
            return False

    def _pause_impl(self) -> bool:
        """구현체별 일시정지 로직"""
        try:
            self.logger.info("AnimeDataManager 일시정지")
            return True
        except Exception as e:
            self.logger.error(f"일시정지 실패: {e}")
            return False

    def _resume_impl(self) -> bool:
        """구현체별 재개 로직"""
        try:
            self.logger.info("AnimeDataManager 재개")
            return True
        except Exception as e:
            self.logger.error(f"재개 실패: {e}")
            return False

    def _get_custom_health_status(self) -> dict[str, Any] | None:
        """구현체별 건강 상태 반환"""
        return {
            "item_count": len(self.items),
            "group_count": len(self.get_grouped_items()),
            "tmdb_matches": len(self.group_tmdb_matches),
            "tmdb_client_available": self.tmdb_client is not None,
        }

    def search_tmdb_for_group(self, group_id: str, group_title: str):
        """그룹에 대한 TMDB 검색 실행"""
        if not self.tmdb_client:
            logger.info("❌ TMDB 클라이언트가 초기화되지 않았습니다")
            return
        logger.info("🔍 TMDB 검색 시작: '%s' (그룹 %s)", group_title, group_id)
        logger.info("🔍 시그널 발행: tmdb_search_requested.emit(%s)", group_id)
        self.tmdb_search_requested.emit(group_id)
        logger.info("🔍 시그널 발행 완료: %s", group_id)

    def set_tmdb_match_for_group(self, group_id: str, tmdb_anime: TMDBAnimeInfo):
        """그룹에 TMDB 매치 결과 설정"""
        self.group_tmdb_matches[group_id] = tmdb_anime
        for item in self.items:
            if item.groupId == group_id:
                item.tmdbMatch = tmdb_anime
                item.tmdbId = tmdb_anime.id
                item.status = "tmdb_matched"
        logger.info("✅ TMDB 매치 완료: 그룹 %s → %s", group_id, tmdb_anime.name)

    def get_tmdb_match_for_group(self, group_id: str) -> TMDBAnimeInfo | None:
        """그룹의 TMDB 매치 결과 반환"""
        return self.group_tmdb_matches.get(group_id)

    def clear_tmdb_matches(self):
        """모든 TMDB 매치 정보 초기화"""
        self.group_tmdb_matches.clear()
        for item in self.items:
            item.tmdbMatch = None
            item.tmdbId = None
            if item.status == "tmdb_matched":
                item.status = "pending"
        logger.info("🔄 모든 TMDB 매치 정보가 초기화되었습니다")

    def get_group_destination_path(self, group_id: str, base_destination: str) -> str:
        """그룹의 최종 이동 경로 생성"""
        tmdb_anime = self.get_tmdb_match_for_group(group_id)
        if not tmdb_anime:
            return str(Path(base_destination) / "Unknown")
        safe_title = re.sub('[<>:"/\\\\|?*]', "", tmdb_anime.name)
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
        episodes = [item.episode for item in group_items if item.episode is not None]
        if episodes:
            min_ep = min(episodes)
            max_ep = max(episodes)
            episode_info = f"E{min_ep:02d}" if min_ep == max_ep else f"E{min_ep:02d}-E{max_ep:02d}"
        else:
            episode_info = "Unknown"
        resolutions = {}
        for item in group_items:
            from src.core.resolution_normalizer import normalize_resolution

            res = normalize_resolution(item.resolution or "Unknown")
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
        groups = self.get_grouped_items()
        logger.info("\n📊 스캔 결과: %s개 파일 → %s개 그룹", len(self.items), len(groups))
        for group_id, items in groups.items():
            if group_id == "ungrouped":
                continue
            title = items[0].title if items else "Unknown"
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
            resolutions = {}
            for item in items:
                from src.core.resolution_normalizer import normalize_resolution

                res = normalize_resolution(item.resolution or "Unknown")
                resolutions[res] = resolutions.get(res, 0) + 1
            resolution_info = ", ".join([f"{res}: {count}" for res, count in resolutions.items()])
            logger.info(
                "🔗 %s (%s) - %s개 파일 [%s]", title, episode_info, len(items), resolution_info
            )
        return groups
