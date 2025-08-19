"""
TMDB 관리자
TMDB API 검색, 메타데이터 가져오기, 포스터 캐싱 등을 관리합니다.
"""

import os
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

# 상대 경로로 수정
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from core.tmdb_client import TMDBClient, TMDBAnimeInfo
from .anime_data_manager import ParsedItem
from plugins.base import PluginManager, MetadataProvider


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
    source: str = "TMDB"  # 메타데이터 소스 추가


class TMDBManager:
    """TMDB API 관리자 (플러그인 시스템 통합)"""
    
    def __init__(self, api_key: str = None):
        """초기화"""
        self.api_key = api_key or os.getenv('TMDB_API_KEY')
        self.tmdb_client = None
        self.poster_cache = {}  # 포스터 이미지 캐시
        self.search_cache = {}  # 검색 결과 캐시
        
        # 플러그인 시스템 초기화
        self.plugin_manager = PluginManager()
        self.metadata_providers = {}
        
        # TMDB 클라이언트 초기화
        if self.api_key:
            try:
                self.tmdb_client = TMDBClient(api_key=self.api_key)
                print("✅ TMDBManager 초기화 성공")
            except Exception as e:
                print(f"❌ TMDBManager 초기화 실패: {e}")
        else:
            print("⚠️ TMDB_API_KEY가 설정되지 않았습니다")
        
        # 플러그인 로드
        self._load_plugins()
    
    def _load_plugins(self):
        """플러그인 로드"""
        try:
            loaded_count = self.plugin_manager.load_all_plugins()
            self.metadata_providers = self.plugin_manager.get_metadata_providers()
            print(f"✅ 플러그인 로드 완료: {loaded_count}개")
            
            # 사용 가능한 메타데이터 제공자 출력
            for name, provider in self.metadata_providers.items():
                print(f"📦 메타데이터 제공자: {name} ({provider.get_plugin_info().description})")
                
        except Exception as e:
            print(f"❌ 플러그인 로드 실패: {e}")
    
    def get_available_providers(self) -> List[str]:
        """사용 가능한 메타데이터 제공자 목록 반환"""
        return list(self.metadata_providers.keys())
    
    def is_available(self) -> bool:
        """TMDB 클라이언트 사용 가능 여부"""
        return self.tmdb_client is not None
    
    def search_anime(self, query: str, language: str = 'ko-KR', use_plugins: bool = True) -> List[TMDBSearchResult]:
        """애니메이션 검색 (플러그인 시스템 포함)"""
        all_results = []
        
        # 1. TMDB 검색 (기본)
        if self.is_available():
            tmdb_results = self._search_tmdb(query, language)
            all_results.extend(tmdb_results)
        
        # 2. 플러그인 검색
        if use_plugins and self.metadata_providers:
            plugin_results = self._search_plugins(query, language)
            all_results.extend(plugin_results)
        
        # 신뢰도 점수로 정렬
        all_results.sort(key=lambda x: x.confidence_score, reverse=True)
        
        print(f"🔍 '{query}' 검색 완료: {len(all_results)}개 결과 (TMDB: {len(tmdb_results) if self.is_available() else 0}, 플러그인: {len(plugin_results) if use_plugins and self.metadata_providers else 0})")
        return all_results
    
    def _search_tmdb(self, query: str, language: str) -> List[TMDBSearchResult]:
        """TMDB에서 검색"""
        if not self.is_available():
            return []
        
        # 캐시 확인
        cache_key = f"tmdb_{query}_{language}"
        if cache_key in self.search_cache:
            print(f"📋 캐시된 TMDB 검색 결과 사용: {query}")
            return self.search_cache[cache_key]
        
        try:
            # TMDB에서 검색
            results = self.tmdb_client.search_anime(query, language=language)
            
            # 결과를 TMDBSearchResult로 변환
            search_results = []
            for result in results:
                # 신뢰도 점수 계산 (제목 유사도 기반)
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
                    source="TMDB"
                )
                search_results.append(search_result)
            
            # 캐시에 저장
            self.search_cache[cache_key] = search_results
            return search_results
            
        except Exception as e:
            print(f"❌ TMDB 검색 실패: {e}")
            return []
    
    def _search_plugins(self, query: str, language: str) -> List[TMDBSearchResult]:
        """플러그인에서 검색"""
        plugin_results = []
        
        for name, provider in self.metadata_providers.items():
            try:
                if not provider.is_available():
                    continue
                
                # 플러그인에서 검색
                results = provider.search_anime(query, language=language)
                
                for result in results:
                    # 신뢰도 점수 계산
                    confidence = self._calculate_title_confidence(query, result.get('title', ''))
                    
                    search_result = TMDBSearchResult(
                        tmdb_id=result.get('id', 0),
                        name=result.get('title', ''),
                        original_name=result.get('original_title', ''),
                        first_air_date=result.get('aired_from', ''),
                        overview=result.get('synopsis', ''),
                        poster_path=result.get('image_url', ''),
                        vote_average=result.get('score', 0.0),
                        vote_count=result.get('scored_by', 0),
                        popularity=result.get('popularity', 0.0),
                        media_type=result.get('type', 'tv'),
                        confidence_score=confidence,
                        source=name
                    )
                    plugin_results.append(search_result)
                
                print(f"📦 {name} 플러그인 검색 완료: {len(results)}개 결과")
                
            except Exception as e:
                print(f"❌ {name} 플러그인 검색 실패: {e}")
        
        return plugin_results
    
    def get_anime_details(self, tmdb_id: int, language: str = 'ko-KR') -> Optional[TMDBAnimeInfo]:
        """애니메이션 상세 정보 가져오기"""
        if not self.is_available():
            return None
        
        try:
            details = self.tmdb_client.get_anime_details(tmdb_id, language=language)
            print(f"📖 TMDB ID {tmdb_id} 상세 정보 로드 완료")
            return details
        except Exception as e:
            print(f"❌ 상세 정보 로드 오류: {e}")
            return None
    
    def get_poster_path(self, poster_path: str, size: str = 'w92') -> Optional[str]:
        """포스터 이미지 경로 가져오기"""
        if not self.is_available() or not poster_path:
            return None
        
        # 캐시 확인
        cache_key = f"{poster_path}_{size}"
        if cache_key in self.poster_cache:
            return self.poster_cache[cache_key]
        
        try:
            poster_file_path = self.tmdb_client.get_poster_path(poster_path, size)
            if poster_file_path and os.path.exists(poster_file_path):
                # 캐시에 저장
                self.poster_cache[cache_key] = poster_file_path
                return poster_file_path
        except Exception as e:
            print(f"❌ 포스터 로드 오류: {e}")
        
        return None
    
    def auto_match_anime(self, parsed_item: ParsedItem) -> Optional[TMDBSearchResult]:
        """파싱된 아이템을 자동으로 TMDB와 매칭"""
        if not self.is_available():
            return None
        
        # 제목으로 검색
        search_query = parsed_item.detectedTitle or parsed_item.title
        if not search_query:
            return None
        
        print(f"🔍 자동 매칭 시도: {search_query}")
        
        # 한국어로 먼저 검색
        results = self.search_anime(search_query, 'ko-KR')
        if results:
            best_match = results[0]
            if best_match.confidence_score >= 0.7:  # 70% 이상 유사도
                print(f"✅ 자동 매칭 성공: {best_match.name} (신뢰도: {best_match.confidence_score:.2f})")
                return best_match
        
        # 영어로도 검색
        results = self.search_anime(search_query, 'en-US')
        if results:
            best_match = results[0]
            if best_match.confidence_score >= 0.7:
                print(f"✅ 자동 매칭 성공 (영어): {best_match.name} (신뢰도: {best_match.confidence_score:.2f})")
                return best_match
        
        print(f"❌ 자동 매칭 실패: {search_query}")
        return None
    
    def batch_search_anime(self, parsed_items: List[ParsedItem]) -> Dict[str, TMDBSearchResult]:
        """여러 애니메이션을 일괄 검색"""
        if not self.is_available():
            return {}
        
        print(f"🚀 일괄 검색 시작: {len(parsed_items)}개 아이템")
        
        results = {}
        for i, item in enumerate(parsed_items):
            print(f"진행률: {i+1}/{len(parsed_items)} - {item.detectedTitle}")
            
            # 이미 TMDB 매칭이 되어 있으면 건너뛰기
            if item.tmdbId:
                continue
            
            # 자동 매칭 시도
            match_result = self.auto_match_anime(item)
            if match_result:
                results[item.id] = match_result
                
                # 아이템 업데이트
                item.tmdbId = match_result.tmdb_id
                item.tmdbMatch = self.get_anime_details(match_result.tmdb_id)
        
        print(f"✅ 일괄 검색 완료: {len(results)}개 매칭 성공")
        return results
    
    def _calculate_title_confidence(self, query: str, title: str) -> float:
        """제목 유사도 계산 (0.0 ~ 1.0)"""
        if not query or not title:
            return 0.0
        
        # 소문자 변환
        query_lower = query.lower()
        title_lower = title.lower()
        
        # 정확한 일치
        if query_lower == title_lower:
            return 1.0
        
        # 포함 관계
        if query_lower in title_lower or title_lower in query_lower:
            return 0.9
        
        # 단어 기반 유사도
        query_words = set(query_lower.split())
        title_words = set(title_lower.split())
        
        if not query_words or not title_words:
            return 0.0
        
        # Jaccard 유사도
        intersection = len(query_words.intersection(title_words))
        union = len(query_words.union(title_words))
        
        if union == 0:
            return 0.0
        
        jaccard_similarity = intersection / union
        
        # 길이 유사도
        length_diff = abs(len(query) - len(title))
        max_length = max(len(query), len(title))
        length_similarity = 1.0 - (length_diff / max_length) if max_length > 0 else 0.0
        
        # 최종 유사도 (Jaccard 70%, 길이 30%)
        final_similarity = (jaccard_similarity * 0.7) + (length_similarity * 0.3)
        
        return final_similarity
    
    def clear_cache(self):
        """캐시 초기화"""
        self.poster_cache.clear()
        self.search_cache.clear()
        print("🗑️ TMDB 캐시 초기화 완료")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """캐시 통계 반환"""
        return {
            'poster_cache_size': len(self.poster_cache),
            'search_cache_size': len(self.search_cache)
        }
    
    def export_cache_info(self, filepath: str):
        """캐시 정보를 파일로 내보내기"""
        try:
            cache_info = {
                'poster_cache': list(self.poster_cache.keys()),
                'search_cache': list(self.search_cache.keys()),
                'stats': self.get_cache_stats()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cache_info, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 캐시 정보 내보내기 완료: {filepath}")
            
        except Exception as e:
            print(f"❌ 캐시 정보 내보내기 실패: {e}")
