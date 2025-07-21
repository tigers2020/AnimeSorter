"""
파일 정렬 및 메타데이터 검색 시스템

새로운 플러그인 시스템을 사용하여 파일을 정렬하고 메타데이터를 검색합니다.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from .metadata_manager import MetadataManager
from ..utils.file_cleaner import FileCleaner



logger = logging.getLogger(__name__)


class AnimeSorter:
    """애니메이션 파일 정렬기 (새로운 플러그인 시스템 기반)"""
    
    def __init__(self, plugin_dir: Path = Path("src/plugin")):
        """
        AnimeSorter 초기화
        
        Args:
            plugin_dir: 플러그인 디렉토리 경로
        """
        self.metadata_manager = MetadataManager(plugin_dir)
        self.file_cleaner = FileCleaner()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._initialized = False
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)  # 디버그 레벨 설정
    
    async def initialize(self) -> None:
        """정렬기 초기화"""
        try:
            self.logger.info("🚀 [SORTER] Starting AnimeSorter initialization...")
            start_time = time.time()
            
            # 메타데이터 관리자 초기화
            self.logger.debug("📋 [SORTER] Initializing metadata manager...")
            await self.metadata_manager.initialize()
            self.logger.debug("✅ [SORTER] Metadata manager initialized successfully")
            
            self._initialized = True
            elapsed = time.time() - start_time
            self.logger.info(f"🎉 [SORTER] AnimeSorter initialization completed in {elapsed:.2f}s")
            
        except Exception as e:
            self.logger.error(f"❌ [SORTER] Failed to initialize AnimeSorter: {e}")
            raise
    
    async def close(self) -> None:
        """정렬기 정리"""
        try:
            self.logger.info("🧹 [SORTER] Starting AnimeSorter cleanup...")
            start_time = time.time()
            
            await self.metadata_manager.close()
            self._executor.shutdown(wait=True)
            self._initialized = False
            
            elapsed = time.time() - start_time
            self.logger.info(f"✅ [SORTER] AnimeSorter cleanup completed in {elapsed:.2f}s")
            
        except Exception as e:
            self.logger.error(f"❌ [SORTER] Error during AnimeSorter cleanup: {e}")
    
    async def process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        단일 파일 처리 (상세한 디버그 로그 포함)
        
        Args:
            file_path: 처리할 파일 경로
            
        Returns:
            Dict or None: 처리 결과 또는 None
        """
        if not self._initialized:
            raise RuntimeError("AnimeSorter is not initialized")
        
        file_start_time = time.time()
        self.logger.info(f"📁 [SORTER] Processing file: {file_path}")
        
        try:
            # 1단계: 파일명 정제
            self.logger.debug(f"🔧 [SORTER] Step 1: Cleaning filename for {file_path.name}")
            clean_start = time.time()
            
            clean_result = self.file_cleaner.clean_filename_static(file_path)
            
            clean_elapsed = time.time() - clean_start
            self.logger.debug(f"✅ [SORTER] Filename cleaning completed in {clean_elapsed:.3f}s")
            self.logger.debug(f"📝 [SORTER] Cleaned title: '{clean_result.title}' (original: '{file_path.stem}')")
            
            # 2단계: 메타데이터 검색
            self.logger.debug(f"🔍 [SORTER] Step 2: Searching metadata for '{clean_result.title}'")
            search_start = time.time()
            
            metadata = await self.metadata_manager.search_with_fallback(
                clean_result.title, clean_result.year
            )
            
            search_elapsed = time.time() - search_start
            self.logger.debug(f"✅ [SORTER] Metadata search completed in {search_elapsed:.3f}s")
            
            if metadata:
                self.logger.debug(f"🎯 [SORTER] Found metadata: {metadata.title} from {metadata.provider}")
                result = {
                    'file_path': str(file_path),
                    'clean_title': clean_result.title,
                    'year': clean_result.year,
                    'metadata': metadata.__dict__,
                    'success': True
                }
                self.logger.info(f"✅ [SORTER] Successfully processed: {file_path.name}")
            else:
                self.logger.debug(f"⚠️ [SORTER] No metadata found for '{clean_result.title}'")
                result = {
                    'file_path': str(file_path),
                    'clean_title': clean_result.title,
                    'year': clean_result.year,
                    'metadata': None,
                    'success': False,
                    'error': 'No metadata found'
                }
                self.logger.warning(f"⚠️ [SORTER] No metadata found for: {file_path.name}")
            
            file_elapsed = time.time() - file_start_time
            self.logger.debug(f"⏱️ [SORTER] Total file processing time: {file_elapsed:.3f}s")
            return result
                
        except Exception as e:
            file_elapsed = time.time() - file_start_time
            self.logger.error(f"❌ [SORTER] Error processing file {file_path} after {file_elapsed:.3f}s: {e}")
            return {
                'file_path': str(file_path),
                'metadata': None,
                'success': False,
                'error': str(e)
            }
    
    async def process_directory(self, directory: Path, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        디렉토리 내 모든 파일 처리 (상세한 디버그 로그 포함)
        
        Args:
            directory: 처리할 디렉토리 경로
            recursive: 하위 디렉토리 포함 여부
            
        Returns:
            List[Dict]: 처리 결과 목록
        """
        if not self._initialized:
            raise RuntimeError("AnimeSorter is not initialized")
        
        dir_start_time = time.time()
        self.logger.info(f"📂 [SORTER] Processing directory: {directory}")
        self.logger.debug(f"🔍 [SORTER] Recursive mode: {recursive}")
        
        # 지원하는 비디오 파일 확장자
        VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.flv'}
        
        # 파일 목록 수집
        self.logger.debug("📋 [SORTER] Collecting file list...")
        collect_start = time.time()
        
        files = []
        if recursive:
            for ext in VIDEO_EXTENSIONS:
                files.extend(directory.rglob(f"*{ext}"))
        else:
            for ext in VIDEO_EXTENSIONS:
                files.extend(directory.glob(f"*{ext}"))
        
        collect_elapsed = time.time() - collect_start
        self.logger.info(f"📊 [SORTER] Found {len(files)} video files in {directory} (collection took {collect_elapsed:.3f}s)")
        
        if not files:
            self.logger.warning("⚠️ [SORTER] No video files found in directory")
            return []
        
        # 파일 처리
        self.logger.debug("🚀 [SORTER] Starting file processing...")
        process_start = time.time()
        
        results = []
        for i, file_path in enumerate(files, 1):
            self.logger.debug(f"📁 [SORTER] Processing file {i}/{len(files)}: {file_path.name}")
            
            result = await self.process_file(file_path)
            results.append(result)
            
            # 진행률 로그
            if i % 10 == 0 or i == len(files):
                progress = (i / len(files)) * 100
                elapsed = time.time() - process_start
                avg_time = elapsed / i
                remaining = (len(files) - i) * avg_time
                self.logger.info(f"📈 [SORTER] Progress: {progress:.1f}% ({i}/{len(files)}) - Avg: {avg_time:.3f}s/file - ETA: {remaining:.1f}s")
        
        process_elapsed = time.time() - process_start
        total_elapsed = time.time() - dir_start_time
        
        # 결과 통계
        successful = sum(1 for r in results if r and r.get('success', False))
        failed = len(results) - successful
        
        self.logger.info(f"🎉 [SORTER] Directory processing completed!")
        self.logger.info(f"📊 [SORTER] Statistics:")
        self.logger.info(f"   - Total files: {len(files)}")
        self.logger.info(f"   - Successful: {successful}")
        self.logger.info(f"   - Failed: {failed}")
        self.logger.info(f"   - Processing time: {process_elapsed:.3f}s")
        self.logger.info(f"   - Total time: {total_elapsed:.3f}s")
        self.logger.info(f"   - Average time per file: {process_elapsed/len(files):.3f}s")
        
        return results
    
    async def batch_process_files(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        여러 파일 배치 처리 (상세한 디버그 로그 포함)
        
        Args:
            file_paths: 처리할 파일 경로 목록
            
        Returns:
            List[Dict]: 처리 결과 목록
        """
        if not self._initialized:
            raise RuntimeError("AnimeSorter is not initialized")
        
        batch_start_time = time.time()
        self.logger.info(f"🚀 [SORTER] Starting batch processing of {len(file_paths)} files")
        
        # 병렬 처리 (동시성 제한)
        semaphore = asyncio.Semaphore(4)  # 최대 4개 동시 처리
        
        async def process_with_semaphore(file_path: Path) -> Dict[str, Any]:
            async with semaphore:
                self.logger.debug(f"🔒 [SORTER] Acquired semaphore for {file_path.name}")
                try:
                    result = await self.process_file(file_path)
                    self.logger.debug(f"🔓 [SORTER] Released semaphore for {file_path.name}")
                    return result
                except Exception as e:
                    self.logger.error(f"❌ [SORTER] Semaphore processing error for {file_path.name}: {e}")
                    self.logger.debug(f"🔓 [SORTER] Released semaphore for {file_path.name} (error)")
                    return {
                        'file_path': str(file_path),
                        'metadata': None,
                        'success': False,
                        'error': str(e)
                    }
        
        # 모든 파일 처리
        self.logger.debug("📋 [SORTER] Creating processing tasks...")
        tasks = [process_with_semaphore(file_path) for file_path in file_paths]
        
        self.logger.debug("🚀 [SORTER] Starting parallel processing...")
        process_start = time.time()
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        process_elapsed = time.time() - process_start
        
        # 예외 처리
        self.logger.debug("🔍 [SORTER] Processing results and handling exceptions...")
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"❌ [SORTER] Task {i} failed with exception: {result}")
                processed_results.append({
                    'file_path': str(file_paths[i]),
                    'metadata': None,
                    'success': False,
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        batch_elapsed = time.time() - batch_start_time
        
        # 결과 통계
        successful = sum(1 for r in processed_results if r and r.get('success', False))
        failed = len(processed_results) - successful
        
        self.logger.info(f"🎉 [SORTER] Batch processing completed!")
        self.logger.info(f"📊 [SORTER] Batch Statistics:")
        self.logger.info(f"   - Total files: {len(file_paths)}")
        self.logger.info(f"   - Successful: {successful}")
        self.logger.info(f"   - Failed: {failed}")
        self.logger.info(f"   - Processing time: {process_elapsed:.3f}s")
        self.logger.info(f"   - Total time: {batch_elapsed:.3f}s")
        self.logger.info(f"   - Average time per file: {process_elapsed/len(file_paths):.3f}s")
        
        return processed_results
    
    def get_available_providers(self) -> List[str]:
        """사용 가능한 메타데이터 제공자 목록 반환"""
        providers = self.metadata_manager.get_available_providers()
        self.logger.debug(f"📋 [SORTER] Available providers: {providers}")
        return providers
    
    def get_active_providers(self) -> List[str]:
        """활성화된 메타데이터 제공자 목록 반환"""
        providers = self.metadata_manager.get_active_providers()
        self.logger.debug(f"✅ [SORTER] Active providers: {providers}")
        return providers
    
    def enable_provider(self, provider_name: str) -> None:
        """제공자 활성화"""
        self.logger.info(f"✅ [SORTER] Enabling provider: {provider_name}")
        self.metadata_manager.enable_provider(provider_name)
    
    def disable_provider(self, provider_name: str) -> None:
        """제공자 비활성화"""
        self.logger.info(f"❌ [SORTER] Disabling provider: {provider_name}")
        self.metadata_manager.disable_provider(provider_name)
    
    def set_provider_priority(self, provider_name: str, priority: int) -> None:
        """제공자 우선순위 설정"""
        self.logger.info(f"⚡ [SORTER] Setting provider priority: {provider_name} = {priority}")
        self.metadata_manager.set_provider_priority(provider_name, priority)
    
    async def test_provider_connection(self, provider_name: str) -> bool:
        """제공자 연결 테스트"""
        self.logger.debug(f"🔍 [SORTER] Testing connection for provider: {provider_name}")
        result = await self.metadata_manager.test_provider_connection(provider_name)
        self.logger.info(f"{'✅' if result else '❌'} [SORTER] Connection test for {provider_name}: {'SUCCESS' if result else 'FAILED'}")
        return result
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        self.logger.debug("📊 [SORTER] Getting cache statistics...")
        stats = await self.metadata_manager.get_cache_stats()
        self.logger.debug(f"📊 [SORTER] Cache stats: {stats}")
        return stats
    
    async def clear_cache(self) -> None:
        """캐시 정리"""
        self.logger.info("🧹 [SORTER] Clearing cache...")
        await self.metadata_manager.clear_cache()
        self.logger.info("✅ [SORTER] Cache cleared")
    
    def export_config(self, export_path: Path) -> None:
        """설정 내보내기"""
        self.logger.info(f"📤 [SORTER] Exporting config to: {export_path}")
        self.metadata_manager.export_config(export_path)
        self.logger.info("✅ [SORTER] Config exported")
    
    def import_config(self, import_path: Path) -> None:
        """설정 가져오기"""
        self.logger.info(f"📥 [SORTER] Importing config from: {import_path}")
        self.metadata_manager.import_config(import_path)
        self.logger.info("✅ [SORTER] Config imported") 