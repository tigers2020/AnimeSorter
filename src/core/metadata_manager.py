"""
통합 메타데이터 관리자

새로운 플러그인 시스템을 사용하여 여러 메타데이터 제공자로부터
정보를 수집하고 관리하는 통합 시스템입니다.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from src.plugin.loader import PluginLoader
from src.plugin.base import SearchResult, ProviderConfig
from src.config.plugin_config import PluginConfigManager
from src.cache.cache_db import CacheDB


logger = logging.getLogger(__name__)


class MetadataManager:
    """통합 메타데이터 관리자"""
    
    # 성능 최적화 상수
    SEARCH_TIMEOUT = 10.0  # 검색 타임아웃 (초)
    CACHE_TIMEOUT = 5.0    # 캐시 작업 타임아웃 (초)
    MAX_CONCURRENT_SEARCHES = 3  # 최대 동시 검색 수
    
    def __init__(self, plugin_dir: Path = Path("src/plugin")):
        """
        MetadataManager 초기화
        
        Args:
            plugin_dir: 플러그인 디렉토리 경로
        """
        self.plugin_dir = plugin_dir
        self.plugin_loader = PluginLoader()
        self.config_manager = PluginConfigManager()
        self.cache_db = CacheDB()
        self._executor = ThreadPoolExecutor(max_workers=2)  # 워커 수 제한
        self._initialized = False
        self._search_semaphore = asyncio.Semaphore(3)  # 동시 검색 제한
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)  # 디버그 레벨 설정
    
    async def initialize(self) -> None:
        """메타데이터 관리자 초기화"""
        try:
            self.logger.info("🚀 [METADATA] Starting Metadata Manager initialization...")
            start_time = time.time()
            
            # 캐시 데이터베이스 초기화 (타임아웃 적용)
            self.logger.debug("💾 [METADATA] Initializing cache database...")
            try:
                await asyncio.wait_for(
                    self.cache_db.initialize(),
                    timeout=self.CACHE_TIMEOUT
                )
                self.logger.debug("✅ [METADATA] Cache database initialized successfully")
            except asyncio.TimeoutError:
                self.logger.warning("⚠️ [METADATA] Cache initialization timeout, continuing without cache")
            except Exception as e:
                self.logger.warning(f"⚠️ [METADATA] Cache initialization failed: {e}, continuing without cache")
            
            # 플러그인 로드
            self.logger.debug("📦 [METADATA] Loading plugins...")
            load_start = time.time()
            load_results = await self.plugin_loader.load_all_plugins(self.plugin_dir)
            load_elapsed = time.time() - load_start
            self.logger.info(f"📦 [METADATA] Plugin load results: {load_results} (took {load_elapsed:.3f}s)")
            
            # 활성화된 플러그인들 초기화
            self.logger.debug("🔧 [METADATA] Initializing active plugins...")
            init_start = time.time()
            
            for plugin_name in self.plugin_loader.get_available_plugins():
                if plugin_name in load_results and load_results[plugin_name]:
                    self.logger.debug(f"🔧 [METADATA] Initializing plugin: {plugin_name}")
                    
                    # 설정 가져오기
                    settings = self.config_manager.get_plugin_settings(plugin_name)
                    
                    if settings.enabled:
                        self.logger.debug(f"✅ [METADATA] Plugin {plugin_name} is enabled, proceeding with initialization")
                        
                        # API 키 가져오기 (실제로는 보안 저장소에서)
                        api_key = settings.custom_settings.get('api_key')
                        
                        # ProviderConfig 생성
                        provider_config = self.config_manager.get_provider_config(
                            plugin_name, api_key
                        )
                        
                        # 플러그인 초기화 (타임아웃 적용)
                        try:
                            plugin_start = time.time()
                            success = await asyncio.wait_for(
                                self.plugin_loader.initialize_provider(plugin_name, provider_config),
                                timeout=5.0
                            )
                            plugin_elapsed = time.time() - plugin_start
                            
                            if success:
                                self.logger.info(f"✅ [METADATA] Successfully initialized plugin: {plugin_name} (took {plugin_elapsed:.3f}s)")
                            else:
                                self.logger.warning(f"⚠️ [METADATA] Failed to initialize plugin: {plugin_name} (took {plugin_elapsed:.3f}s)")
                        except asyncio.TimeoutError:
                            self.logger.warning(f"⚠️ [METADATA] Plugin initialization timeout: {plugin_name}")
                        except Exception as e:
                            self.logger.error(f"❌ [METADATA] Plugin initialization error: {plugin_name} - {e}")
                    else:
                        self.logger.debug(f"❌ [METADATA] Plugin {plugin_name} is disabled, skipping initialization")
                else:
                    self.logger.warning(f"⚠️ [METADATA] Plugin {plugin_name} failed to load, skipping initialization")
            
            init_elapsed = time.time() - init_start
            self.logger.debug(f"🔧 [METADATA] Plugin initialization completed in {init_elapsed:.3f}s")
            
            self._initialized = True
            total_elapsed = time.time() - start_time
            self.logger.info(f"🎉 [METADATA] Metadata Manager initialization completed in {total_elapsed:.3f}s")
            
        except Exception as e:
            self.logger.error(f"❌ [METADATA] Failed to initialize Metadata Manager: {e}")
            raise
    
    async def close(self) -> None:
        """메타데이터 관리자 정리"""
        try:
            self.logger.info("🧹 [METADATA] Starting Metadata Manager cleanup...")
            start_time = time.time()
            
            # 플러그인들 정리
            self.logger.debug("🔧 [METADATA] Closing plugins...")
            await self.plugin_loader.close_all_providers()
            
            # 캐시 데이터베이스 정리
            self.logger.debug("💾 [METADATA] Closing cache database...")
            try:
                await asyncio.wait_for(
                    self.cache_db.close(),
                    timeout=self.CACHE_TIMEOUT
                )
                self.logger.debug("✅ [METADATA] Cache database closed successfully")
            except asyncio.TimeoutError:
                self.logger.warning("⚠️ [METADATA] Cache close timeout")
            except Exception as e:
                self.logger.warning(f"⚠️ [METADATA] Cache close error: {e}")
            
            # 스레드 풀 정리
            self.logger.debug("🧵 [METADATA] Shutting down thread pool...")
            self._executor.shutdown(wait=False)  # 비동기 정리
            
            self._initialized = False
            elapsed = time.time() - start_time
            self.logger.info(f"✅ [METADATA] Metadata Manager cleanup completed in {elapsed:.3f}s")
            
        except Exception as e:
            self.logger.error(f"❌ [METADATA] Error during Metadata Manager cleanup: {e}")
    
    async def search(self, title: str, year: Optional[int] = None, season: Optional[int] = None, is_special: bool = False) -> Optional[SearchResult]:
        """
        모든 활성화된 플러그인에서 메타데이터 검색 (타임아웃 및 에러 처리 강화)
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            season: 시즌 번호 (옵션)
            is_special: 특집 여부 (옵션)
            
        Returns:
            SearchResult or None: 검색 결과 또는 None
        """
        if not self._initialized:
            raise RuntimeError("Metadata Manager is not initialized")
        
        search_start = time.time()
        self.logger.info(f"🔍 [METADATA] Starting search for: '{title}' (year: {year})")
        
        async with self._search_semaphore:  # 동시 검색 제한
            self.logger.debug(f"🔒 [METADATA] Acquired search semaphore for: '{title}'")
            
            try:
                # 캐시 확인 (타임아웃 적용)
                cache_key = self._generate_cache_key(title, year)
                self.logger.debug(f"💾 [METADATA] Checking cache with key: {cache_key}")
                
                cached_result = None
                cache_start = time.time()
                
                try:
                    cached_result = await asyncio.wait_for(
                        self.cache_db.get_cache(cache_key),
                        timeout=self.CACHE_TIMEOUT
                    )
                    cache_elapsed = time.time() - cache_start
                    self.logger.debug(f"💾 [METADATA] Cache lookup completed in {cache_elapsed:.3f}s")
                except asyncio.TimeoutError:
                    self.logger.warning(f"⚠️ [METADATA] Cache lookup timeout for: {title}")
                except Exception as e:
                    self.logger.warning(f"⚠️ [METADATA] Cache lookup failed for {title}: {e}")
                
                if cached_result:
                    self.logger.info(f"✅ [METADATA] Cache hit for: {title}")
                    return SearchResult(**cached_result)
                
                # 모든 플러그인에서 검색 (타임아웃 적용)
                self.logger.debug(f"🔍 [METADATA] No cache hit, searching all providers for: '{title}'")
                search_providers_start = time.time()
                
                try:
                    results = await asyncio.wait_for(
                        self.plugin_loader.search_all_providers(title, year, season, is_special),
                        timeout=self.SEARCH_TIMEOUT
                    )
                    search_providers_elapsed = time.time() - search_providers_start
                    self.logger.debug(f"🔍 [METADATA] Provider search completed in {search_providers_elapsed:.3f}s")
                    self.logger.debug(f"📊 [METADATA] Found {len(results)} results from providers")
                except asyncio.TimeoutError:
                    self.logger.warning(f"⚠️ [METADATA] Search timeout for: {title}")
                    return None
                except Exception as e:
                    self.logger.error(f"❌ [METADATA] Search failed for {title}: {e}")
                    return None
                
                if not results:
                    self.logger.warning(f"⚠️ [METADATA] No results found for: {title}")
                    return None
                
                # 가장 우선순위가 높은 결과 선택
                self.logger.debug(f"🎯 [METADATA] Selecting best result from {len(results)} candidates")
                selection_start = time.time()
                best_result = self._select_best_result(results, title, year)
                selection_elapsed = time.time() - selection_start
                self.logger.debug(f"🎯 [METADATA] Result selection completed in {selection_elapsed:.3f}s")
                
                if best_result:
                    # 캐시에 저장 (비동기, 에러 무시)
                    self.logger.debug(f"💾 [METADATA] Caching result for: {title}")
                    try:
                        asyncio.create_task(
                            self._cache_result_async(cache_key, best_result, year)
                        )
                    except Exception as e:
                        self.logger.warning(f"⚠️ [METADATA] Failed to cache result: {e}")
                
                total_elapsed = time.time() - search_start
                self.logger.info(f"✅ [METADATA] Search completed for '{title}' in {total_elapsed:.3f}s")
                return best_result
                
            except Exception as e:
                total_elapsed = time.time() - search_start
                self.logger.error(f"❌ [METADATA] Search error for {title} after {total_elapsed:.3f}s: {e}")
                return None
            finally:
                self.logger.debug(f"🔓 [METADATA] Released search semaphore for: '{title}'")
    
    async def _cache_result_async(self, cache_key: str, result: SearchResult, year: Optional[int] = None) -> None:
        """비동기 캐시 저장 (에러 무시)"""
        try:
            cache_start = time.time()
            await asyncio.wait_for(
                self.cache_db.set_cache(cache_key, result.__dict__, year),
                timeout=self.CACHE_TIMEOUT
            )
            cache_elapsed = time.time() - cache_start
            self.logger.debug(f"💾 [METADATA] Async cache save completed in {cache_elapsed:.3f}s")
        except Exception as e:
            self.logger.debug(f"⚠️ [METADATA] Async cache save failed: {e}")
    
    async def search_with_fallback(self, title: str, year: Optional[int] = None) -> Optional[SearchResult]:
        """
        폴백 전략을 사용한 메타데이터 검색 (타임아웃 적용)
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            
        Returns:
            SearchResult or None: 검색 결과 또는 None
        """
        fallback_start = time.time()
        self.logger.info(f"🔄 [METADATA] Starting fallback search for: '{title}' (year: {year})")
        
        try:
            # 1차 검색: 정확한 제목으로 검색
            self.logger.debug(f"🔍 [METADATA] Fallback step 1: Exact title search for '{title}'")
            result = await self.search(title, year)
            if result:
                self.logger.info(f"✅ [METADATA] Fallback step 1 successful for '{title}'")
                return result
            
            # 2차 검색: 제목 정제 후 검색
            self.logger.debug(f"🔧 [METADATA] Fallback step 2: Cleaned title search")
            from src.utils.file_cleaner import FileCleaner
            clean_title = FileCleaner.clean_title(title)
            
            if clean_title != title:
                self.logger.info(f"🔄 [METADATA] Trying with cleaned title: '{clean_title}' (original: '{title}')")
                result = await self.search(clean_title, year)
                if result:
                    self.logger.info(f"✅ [METADATA] Fallback step 2 successful with cleaned title")
                    return result
            
            # 3차 검색: 연도 없이 검색
            if year:
                self.logger.debug(f"🔄 [METADATA] Fallback step 3: Search without year")
                self.logger.info(f"🔄 [METADATA] Trying without year: '{title}'")
                result = await self.search(title, None)
                if result:
                    self.logger.info(f"✅ [METADATA] Fallback step 3 successful without year")
                    return result
            
            total_elapsed = time.time() - fallback_start
            self.logger.warning(f"⚠️ [METADATA] All fallback steps failed for '{title}' after {total_elapsed:.3f}s")
            return None
            
        except Exception as e:
            total_elapsed = time.time() - fallback_start
            self.logger.error(f"❌ [METADATA] Fallback search error for {title} after {total_elapsed:.3f}s: {e}")
            return None
    
    async def batch_search(self, titles: List[str], years: Optional[List[Optional[int]]] = None) -> List[Optional[SearchResult]]:
        """
        배치 메타데이터 검색 (성능 최적화)
        
        Args:
            titles: 검색할 제목 목록
            years: 연도 목록 (옵션)
            
        Returns:
            List[Optional[SearchResult]]: 검색 결과 목록
        """
        if years is None:
            years = [None] * len(titles)
        
        if len(titles) != len(years):
            raise ValueError("Titles and years lists must have the same length")
        
        batch_start = time.time()
        self.logger.info(f"🚀 [METADATA] Starting batch search for {len(titles)} titles")
        
        # 동시성 제한을 위한 세마포어
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_SEARCHES)
        
        async def search_with_semaphore(title: str, year: Optional[int]) -> Optional[SearchResult]:
            async with semaphore:
                self.logger.debug(f"🔒 [METADATA] Acquired batch semaphore for: '{title}'")
                try:
                    result = await self.search_with_fallback(title, year)
                    self.logger.debug(f"🔓 [METADATA] Released batch semaphore for: '{title}'")
                    return result
                except Exception as e:
                    self.logger.error(f"❌ [METADATA] Batch search failed for {title}: {e}")
                    self.logger.debug(f"🔓 [METADATA] Released batch semaphore for: '{title}' (error)")
                    return None
        
        # 모든 검색 태스크 생성
        self.logger.debug("📋 [METADATA] Creating batch search tasks...")
        tasks = [search_with_semaphore(title, year) for title, year in zip(titles, years)]
        
        # 결과 수집 (타임아웃 적용)
        self.logger.debug("🚀 [METADATA] Starting parallel batch processing...")
        process_start = time.time()
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=len(titles) * 2.0  # 파일당 2초씩 허용
            )
            
            process_elapsed = time.time() - process_start
            
            # 예외 처리
            self.logger.debug("🔍 [METADATA] Processing batch results and handling exceptions...")
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"❌ [METADATA] Batch task {i} failed with exception: {result}")
                    processed_results.append(None)
                else:
                    processed_results.append(result)
            
            total_elapsed = time.time() - batch_start
            successful = sum(1 for r in processed_results if r is not None)
            
            self.logger.info(f"🎉 [METADATA] Batch search completed!")
            self.logger.info(f"📊 [METADATA] Batch Statistics:")
            self.logger.info(f"   - Total titles: {len(titles)}")
            self.logger.info(f"   - Successful: {successful}")
            self.logger.info(f"   - Failed: {len(titles) - successful}")
            self.logger.info(f"   - Processing time: {process_elapsed:.3f}s")
            self.logger.info(f"   - Total time: {total_elapsed:.3f}s")
            self.logger.info(f"   - Average time per title: {process_elapsed/len(titles):.3f}s")
            
            return processed_results
            
        except asyncio.TimeoutError:
            total_elapsed = time.time() - batch_start
            self.logger.warning(f"⚠️ [METADATA] Batch search timeout after {total_elapsed:.3f}s")
            return [None] * len(titles)
        except Exception as e:
            total_elapsed = time.time() - batch_start
            self.logger.error(f"❌ [METADATA] Batch search error after {total_elapsed:.3f}s: {e}")
            return [None] * len(titles)
    
    def _select_best_result(self, results: List[SearchResult], title: str, year: Optional[int] = None) -> Optional[SearchResult]:
        """
        여러 결과 중 최적의 결과 선택 (에러 처리 강화)
        
        Args:
            results: 검색 결과 목록
            title: 원본 검색 제목
            year: 연도 (옵션)
            
        Returns:
            SearchResult or None: 최적의 결과
        """
        if not results:
            return None
        
        self.logger.debug(f"🎯 [METADATA] Selecting best result from {len(results)} candidates")
        
        try:
            # 점수 계산 함수
            def calculate_score(result: SearchResult) -> float:
                try:
                    score = 0.0
                    
                    # 제목 유사도 (0-100)
                    from rapidfuzz import fuzz
                    title_similarity = fuzz.ratio(title.lower(), result.title.lower())
                    score += title_similarity
                    
                    # 연도 매칭 보너스
                    if year and result.year:
                        if result.year == year:
                            score += 50
                        elif abs(result.year - year) <= 1:
                            score += 25
                    
                    # 평점 보너스 (0-20)
                    if result.rating:
                        score += min(20, result.rating * 2)
                    
                    # 플러그인 우선순위 보너스
                    try:
                        plugin_config = self.config_manager.get_plugin_settings(result.provider)
                        score += plugin_config.priority * 10
                    except Exception:
                        pass  # 플러그인 설정 에러 무시
                    
                    return score
                except Exception:
                    return 0.0  # 점수 계산 실패 시 0점
            
            # 점수로 정렬
            scored_results = [(result, calculate_score(result)) for result in results]
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # 최고 점수 결과 반환
            best_result, best_score = scored_results[0]
            
            self.logger.info(f"🎯 [METADATA] Selected result: {best_result.title} (score: {best_score:.1f}) from {best_result.provider}")
            
            return best_result
            
        except Exception as e:
            self.logger.error(f"❌ [METADATA] Result selection error: {e}")
            # 에러 시 첫 번째 결과 반환
            return results[0] if results else None
    
    def _generate_cache_key(self, title: str, year: Optional[int] = None) -> str:
        """캐시 키 생성 (에러 처리 강화)"""
        try:
            from slugify import slugify
        from src.utils.safe_slugify import safe_slugify
            normalized_title = safe_slugify(title, separator='_')
            year_part = f"_{year}" if year else "_any"
            return f"{normalized_title}{year_part}"
        except Exception:
            # slugify 실패 시 간단한 키 생성
            safe_title = "".join(c for c in title.lower() if c.isalnum() or c.isspace())
            safe_title = safe_title.replace(" ", "_")
            year_part = f"_{year}" if year else "_any"
            return f"{safe_title}{year_part}"
    
    def get_available_providers(self) -> List[str]:
        """사용 가능한 제공자 목록 반환"""
        providers = self.plugin_loader.get_available_plugins()
        self.logger.debug(f"📋 [METADATA] Available providers: {providers}")
        return providers
    
    def get_active_providers(self) -> List[str]:
        """활성화된 제공자 목록 반환"""
        providers = self.plugin_loader.get_active_plugins()
        self.logger.debug(f"✅ [METADATA] Active providers: {providers}")
        return providers
    
    def get_provider_info(self, provider_name: str) -> Dict[str, Any]:
        """제공자 정보 반환"""
        info = self.plugin_loader.get_plugin_info(provider_name)
        self.logger.debug(f"📋 [METADATA] Provider info for {provider_name}: {info}")
        return info
    
    def enable_provider(self, provider_name: str) -> None:
        """제공자 활성화"""
        self.logger.info(f"✅ [METADATA] Enabling provider: {provider_name}")
        self.config_manager.enable_plugin(provider_name)
    
    def disable_provider(self, provider_name: str) -> None:
        """제공자 비활성화"""
        self.logger.info(f"❌ [METADATA] Disabling provider: {provider_name}")
        self.config_manager.disable_plugin(provider_name)
    
    def set_provider_priority(self, provider_name: str, priority: int) -> None:
        """제공자 우선순위 설정"""
        self.logger.info(f"⚡ [METADATA] Setting provider priority: {provider_name} = {priority}")
        self.config_manager.set_plugin_priority(provider_name, priority)
    
    async def test_provider_connection(self, provider_name: str) -> bool:
        """제공자 연결 테스트 (타임아웃 적용)"""
        self.logger.debug(f"🔍 [METADATA] Testing connection for provider: {provider_name}")
        try:
            if provider_name not in self.plugin_loader.instances:
                self.logger.warning(f"⚠️ [METADATA] Provider {provider_name} not found in instances")
                return False
            
            provider = self.plugin_loader.instances[provider_name]
            result = await asyncio.wait_for(
                provider.test_connection(),
                timeout=5.0
            )
            self.logger.info(f"{'✅' if result else '❌'} [METADATA] Connection test for {provider_name}: {'SUCCESS' if result else 'FAILED'}")
            return result
        except Exception as e:
            self.logger.error(f"❌ [METADATA] Provider connection test failed for {provider_name}: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        self.logger.debug("📊 [METADATA] Getting cache statistics...")
        try:
            stats = {
                "cache_enabled": self.cache_db is not None,
                "cache_file": str(self.cache_db.db_path) if self.cache_db else None
            }
            self.logger.debug(f"📊 [METADATA] Cache stats: {stats}")
            return stats
        except Exception as e:
            self.logger.error(f"❌ [METADATA] Cache stats error: {e}")
            return {"cache_enabled": False, "error": str(e)}
    
    async def clear_cache(self) -> None:
        """캐시 정리 (타임아웃 적용)"""
        self.logger.info("🧹 [METADATA] Clearing cache...")
        try:
            if self.cache_db:
                await asyncio.wait_for(
                    self.cache_db.cleanup_cache(),
                    timeout=self.CACHE_TIMEOUT
                )
                self.logger.info("✅ [METADATA] Cache cleared")
        except Exception as e:
            self.logger.error(f"❌ [METADATA] Cache clear error: {e}")
    
    def export_config(self, export_path: Path) -> None:
        """설정 내보내기"""
        self.logger.info(f"📤 [METADATA] Exporting config to: {export_path}")
        try:
            self.config_manager.export_config(export_path)
            self.logger.info("✅ [METADATA] Config exported")
        except Exception as e:
            self.logger.error(f"❌ [METADATA] Config export error: {e}")
    
    def import_config(self, import_path: Path) -> None:
        """설정 가져오기"""
        self.logger.info(f"📥 [METADATA] Importing config from: {import_path}")
        try:
            self.config_manager.import_config(import_path)
            self.logger.info("✅ [METADATA] Config imported")
        except Exception as e:
            self.logger.error(f"❌ [METADATA] Config import error: {e}") 