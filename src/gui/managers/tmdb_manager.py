"""
TMDB 관리자
TMDB API 검색, 메타데이터 가져오기, 포스터 캐싱 등을 관리합니다.
"""

import logging

logger = logging.getLogger(__name__)
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.core.tmdb_client import TMDBAnimeInfo, TMDBClient
from src.core.unified_config import unified_config_manager
from src.gui.managers.anime_data_manager import ParsedItem
from src.plugins.base import PluginManager


@dataclass
class TMDBSearchResult:
    """TMDB 검색 결과"""

    tmdb_id: int
    name: str
    original_name: str
    first_air_date: str
    overview: str
    poster_path: str
    vote_average: float
    vote_count: int
    popularity: float
    media_type: str
    confidence_score: float = 0.0
    source: str = "TMDB"


class TMDBManager:
    """TMDB API 관리자 (플러그인 시스템 통합)"""

    def __init__(self, api_key: str = None):
        """초기화"""
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = unified_config_manager.get("services", "tmdb_api", {}).get("api_key", "")
        self.tmdb_client = None
        self.poster_cache = {}
        self.search_cache = {}
        self.plugin_manager = PluginManager()
        self.metadata_providers = {}
        if self.api_key:
            try:
                self.tmdb_client = TMDBClient(api_key=self.api_key)
                logger.info("✅ TMDBManager 초기화 성공")
            except Exception as e:
                logger.info("❌ TMDBManager 초기화 실패: %s", e)
        else:
            logger.info("⚠️ TMDB_API_KEY가 설정되지 않았습니다")
        self._load_plugins()

    def _load_plugins(self):
        """플러그인 로드"""
        try:
            loaded_count = self.plugin_manager.load_all_plugins()
            self.metadata_providers = self.plugin_manager.get_metadata_providers()
            logger.info("✅ 플러그인 로드 완료: %s개", loaded_count)
            for name, provider in self.metadata_providers.items():
                logger.info(
                    "📦 메타데이터 제공자: %s (%s)", name, provider.get_plugin_info().description
                )
        except Exception as e:
            logger.info("❌ 플러그인 로드 실패: %s", e)

    def get_available_providers(self) -> list[str]:
        """사용 가능한 메타데이터 제공자 목록 반환"""
        return list(self.metadata_providers.keys())

    def is_available(self) -> bool:
        """TMDB 클라이언트 사용 가능 여부"""
        return self.tmdb_client is not None

    def search_anime(
        self, query: str, language: str = "ko-KR", use_plugins: bool = True
    ) -> list[TMDBSearchResult]:
        """애니메이션 검색 (플러그인 시스템 포함)"""
        all_results = []
        if self.is_available():
            tmdb_results = self._search_tmdb(query, language)
            all_results.extend(tmdb_results)
        if use_plugins and self.metadata_providers:
            plugin_results = self._search_plugins(query, language)
            all_results.extend(plugin_results)
        all_results.sort(key=lambda x: x.confidence_score, reverse=True)
        logger.info(
            "🔍 '%s' 검색 완료: %s개 결과 (TMDB: %s, 플러그인: %s)",
            query,
            len(all_results),
            len(tmdb_results) if self.is_available() else 0,
            len(plugin_results) if use_plugins and self.metadata_providers else 0,
        )
        return all_results

    def _search_tmdb(self, query: str, language: str) -> list[TMDBSearchResult]:
        """TMDB에서 검색"""
        if not self.is_available():
            return []
        cache_key = f"tmdb_{query}_{language}"
        if cache_key in self.search_cache:
            logger.info("📋 캐시된 TMDB 검색 결과 사용: %s", query)
            return self.search_cache[cache_key]
        try:
            results = self.tmdb_client.search_anime(query, language=language)
            search_results = []
            for result in results:
                confidence = self._calculate_title_confidence(query, result.name)
                search_result = TMDBSearchResult(
                    tmdb_id=result.id,
                    name=result.name,
                    original_name=result.original_name,
                    first_air_date=result.first_air_date or "",
                    overview=result.overview or "",
                    poster_path=result.poster_path or "",
                    vote_average=result.vote_average or 0.0,
                    vote_count=result.vote_count or 0,
                    popularity=result.popularity or 0.0,
                    media_type=result.media_type or "tv",
                    confidence_score=confidence,
                    source="TMDB",
                )
                search_results.append(search_result)
            self.search_cache[cache_key] = search_results
            return search_results
        except Exception as e:
            logger.info("❌ TMDB 검색 실패: %s", e)
            return []

    def _search_plugins(self, query: str, language: str) -> list[TMDBSearchResult]:
        """플러그인에서 검색"""
        plugin_results = []
        for name, provider in self.metadata_providers.items():
            try:
                if not provider.is_available():
                    continue
                results = provider.search_anime(query, language=language)
                for result in results:
                    confidence = self._calculate_title_confidence(query, result.get("title", ""))
                    search_result = TMDBSearchResult(
                        tmdb_id=result.get("id", 0),
                        name=result.get("title", ""),
                        original_name=result.get("original_title", ""),
                        first_air_date=result.get("aired_from", ""),
                        overview=result.get("synopsis", ""),
                        poster_path=result.get("image_url", ""),
                        vote_average=result.get("score", 0.0),
                        vote_count=result.get("scored_by", 0),
                        popularity=result.get("popularity", 0.0),
                        media_type=result.get("type", "tv"),
                        confidence_score=confidence,
                        source=name,
                    )
                    plugin_results.append(search_result)
                logger.info("📦 %s 플러그인 검색 완료: %s개 결과", name, len(results))
            except Exception as e:
                logger.info("❌ %s 플러그인 검색 실패: %s", name, e)
        return plugin_results

    def get_anime_details(self, tmdb_id: int, language: str = "ko-KR") -> TMDBAnimeInfo | None:
        """애니메이션 상세 정보 가져오기"""
        if not self.is_available():
            return None
        try:
            details = self.tmdb_client.get_anime_details(tmdb_id, language=language)
            logger.info("📖 TMDB ID %s 상세 정보 로드 완료", tmdb_id)
            return details
        except Exception as e:
            logger.info("❌ 상세 정보 로드 오류: %s", e)
            return None

    def get_poster_path(self, poster_path: str, size: str = "w92") -> str | None:
        """포스터 이미지 경로 가져오기"""
        if not self.is_available() or not poster_path:
            return None
        cache_key = f"{poster_path}_{size}"
        if cache_key in self.poster_cache:
            return self.poster_cache[cache_key]
        try:
            poster_file_path = self.tmdb_client.get_poster_path(poster_path, size)
            if poster_file_path and Path(poster_file_path).exists():
                self.poster_cache[cache_key] = poster_file_path
                return poster_file_path
        except Exception as e:
            logger.info("❌ 포스터 로드 오류: %s", e)
        return None

    def auto_match_anime(self, parsed_item: ParsedItem) -> TMDBSearchResult | None:
        """파싱된 아이템을 자동으로 TMDB와 매칭"""
        if not self.is_available():
            return None
        search_query = parsed_item.detectedTitle or parsed_item.title
        if not search_query:
            return None
        logger.info("🔍 자동 매칭 시도: %s", search_query)
        results = self.search_anime(search_query, "ko-KR")
        if results:
            best_match = results[0]
            if best_match.confidence_score >= 0.7:
                logger.info(
                    "✅ 자동 매칭 성공: %s (신뢰도: %s)",
                    best_match.name,
                    best_match.confidence_score,
                )
                return best_match
        results = self.search_anime(search_query, "en-US")
        if results:
            best_match = results[0]
            if best_match.confidence_score >= 0.7:
                logger.info(
                    "✅ 자동 매칭 성공 (영어): %s (신뢰도: %s)",
                    best_match.name,
                    best_match.confidence_score,
                )
                return best_match
        logger.info("❌ 자동 매칭 실패: %s", search_query)
        return None

    def batch_search_anime(self, parsed_items: list[ParsedItem]) -> dict[str, TMDBSearchResult]:
        """여러 애니메이션을 일괄 검색"""
        if not self.is_available():
            return {}
        logger.info("🚀 일괄 검색 시작: %s개 아이템", len(parsed_items))
        results = {}
        for i, item in enumerate(parsed_items):
            logger.info("진행률: %s/%s - %s", i + 1, len(parsed_items), item.detectedTitle)
            if item.tmdbId:
                continue
            match_result = self.auto_match_anime(item)
            if match_result:
                results[item.id] = match_result
                item.tmdbId = match_result.tmdb_id
                item.tmdbMatch = self.get_anime_details(match_result.tmdb_id)
        logger.info("✅ 일괄 검색 완료: %s개 매칭 성공", len(results))
        return results

    def _calculate_title_confidence(self, query: str, title: str) -> float:
        """제목 유사도 계산 (0.0 ~ 1.0)"""
        if not query or not title:
            return 0.0
        query_lower = query.lower()
        title_lower = title.lower()
        if query_lower == title_lower:
            return 1.0
        if query_lower in title_lower or title_lower in query_lower:
            return 0.9
        query_words = set(query_lower.split())
        title_words = set(title_lower.split())
        if not query_words or not title_words:
            return 0.0
        intersection = len(query_words.intersection(title_words))
        union = len(query_words.union(title_words))
        if union == 0:
            return 0.0
        jaccard_similarity = intersection / union
        length_diff = abs(len(query) - len(title))
        max_length = max(len(query), len(title))
        length_similarity = 1.0 - length_diff / max_length if max_length > 0 else 0.0
        return jaccard_similarity * 0.7 + length_similarity * 0.3

    def clear_cache(self):
        """캐시 초기화"""
        self.poster_cache.clear()
        self.search_cache.clear()
        logger.info("🗑️ TMDB 캐시 초기화 완료")

    def get_cache_stats(self) -> dict[str, int]:
        """캐시 통계 반환"""
        return {
            "poster_cache_size": len(self.poster_cache),
            "search_cache_size": len(self.search_cache),
        }

    def export_cache_info(self, filepath: str):
        """캐시 정보를 파일로 내보내기"""
        try:
            cache_info = {
                "poster_cache": list(self.poster_cache.keys()),
                "search_cache": list(self.search_cache.keys()),
                "stats": self.get_cache_stats(),
            }
            with Path(filepath).open("w", encoding="utf-8") as f:
                json.dump(cache_info, f, ensure_ascii=False, indent=2)
            logger.info("✅ 캐시 정보 내보내기 완료: %s", filepath)
        except Exception as e:
            logger.info("❌ 캐시 정보 내보내기 실패: %s", e)
