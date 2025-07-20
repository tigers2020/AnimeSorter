"""
플러그인 로더 시스템

플러그인을 동적으로 로드하고 관리하는 시스템을 제공합니다.
"""

import importlib
import inspect
import logging
from typing import Dict, List, Type, Optional, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import asyncio

from .base import MetadataProvider, ProviderConfig, PluginError, PluginInitializationError


logger = logging.getLogger(__name__)


class PluginLoader:
    """플러그인 로더 클래스"""
    
    def __init__(self):
        """PluginLoader 초기화"""
        self.plugins: Dict[str, Type[MetadataProvider]] = {}
        self.instances: Dict[str, MetadataProvider] = {}
        self.configs: Dict[str, ProviderConfig] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        
    async def discover_plugins(self, plugin_dir: Path) -> List[str]:
        """
        플러그인 디렉토리에서 사용 가능한 플러그인들을 발견
        
        Args:
            plugin_dir: 플러그인 디렉토리 경로
            
        Returns:
            List[str]: 발견된 플러그인 이름 목록
        """
        discovered_plugins = []
        
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {plugin_dir}")
            return discovered_plugins
            
        for item in plugin_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                # provider.py 파일이 있는지 확인
                provider_file = item / "provider.py"
                if provider_file.exists():
                    plugin_name = item.name
                    discovered_plugins.append(plugin_name)
                    logger.info(f"Discovered plugin: {plugin_name}")
                    
        return discovered_plugins
    
    async def load_plugin(self, plugin_name: str, plugin_dir: Path) -> bool:
        """
        특정 플러그인 로드
        
        Args:
            plugin_name: 플러그인 이름
            plugin_dir: 플러그인 디렉토리 경로
            
        Returns:
            bool: 로드 성공 여부
        """
        try:
            # 모듈 경로 구성
            module_path = f"src.plugin.{plugin_name}.provider"
            
            # 모듈 동적 로드
            module = importlib.import_module(module_path)
            
            # MetadataProvider를 상속받는 클래스 찾기
            provider_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, MetadataProvider) and 
                    obj != MetadataProvider):
                    provider_class = obj
                    break
                    
            if provider_class is None:
                logger.error(f"No MetadataProvider class found in {plugin_name}")
                return False
                
            # 플러그인 등록
            self.plugins[plugin_name] = provider_class
            logger.info(f"Successfully loaded plugin: {plugin_name}")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import plugin {plugin_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    async def load_all_plugins(self, plugin_dir: Path) -> Dict[str, bool]:
        """
        모든 플러그인 로드
        
        Args:
            plugin_dir: 플러그인 디렉토리 경로
            
        Returns:
            Dict[str, bool]: 플러그인별 로드 결과
        """
        discovered_plugins = await self.discover_plugins(plugin_dir)
        results = {}
        
        for plugin_name in discovered_plugins:
            success = await self.load_plugin(plugin_name, plugin_dir)
            results[plugin_name] = success
            
        return results
    
    def create_provider_config(self, plugin_name: str, **kwargs) -> ProviderConfig:
        """
        플러그인 설정 생성
        
        Args:
            plugin_name: 플러그인 이름
            **kwargs: 설정 파라미터
            
        Returns:
            ProviderConfig: 생성된 설정
        """
        config = ProviderConfig(
            name=plugin_name,
            **kwargs
        )
        self.configs[plugin_name] = config
        return config
    
    async def initialize_provider(self, plugin_name: str, config: ProviderConfig) -> bool:
        """
        플러그인 인스턴스 초기화
        
        Args:
            plugin_name: 플러그인 이름
            config: 플러그인 설정
            
        Returns:
            bool: 초기화 성공 여부
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} not loaded")
            return False
            
        try:
            # 플러그인 인스턴스 생성
            provider_class = self.plugins[plugin_name]
            instance = provider_class(config)
            
            # 초기화
            await instance.initialize()
            
            # 연결 테스트
            if not await instance.test_connection():
                logger.warning(f"Plugin {plugin_name} connection test failed")
                return False
                
            # 인스턴스 등록
            self.instances[plugin_name] = instance
            logger.info(f"Successfully initialized plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
            return False
    
    async def initialize_all_providers(self) -> Dict[str, bool]:
        """
        모든 플러그인 인스턴스 초기화
        
        Returns:
            Dict[str, bool]: 플러그인별 초기화 결과
        """
        results = {}
        
        for plugin_name, config in self.configs.items():
            if config.enabled:
                success = await self.initialize_provider(plugin_name, config)
                results[plugin_name] = success
            else:
                logger.info(f"Plugin {plugin_name} is disabled")
                results[plugin_name] = False
                
        return results
    
    async def search_all_providers(self, title: str, year: Optional[int] = None, season: Optional[int] = None, is_special: bool = False) -> List[Any]:
        """
        모든 활성화된 플러그인에서 검색
        
        Args:
            title: 검색할 제목
            year: 연도 (옵션)
            season: 시즌 번호 (옵션)
            is_special: 특집 여부 (옵션)
            
        Returns:
            List[SearchResult]: 검색 결과 목록
        """
        tasks = []
        
        # 우선순위에 따라 정렬된 플러그인 목록
        sorted_plugins = sorted(
            self.instances.items(),
            key=lambda x: self.configs[x[0]].priority,
            reverse=True
        )
        
        for plugin_name, instance in sorted_plugins:
            if not self.configs[plugin_name].enabled:
                continue
                
            # 비동기 검색 태스크 생성
            task = asyncio.create_task(
                self._search_with_timeout(instance, title, year, season, is_special)
            )
            tasks.append((plugin_name, task))
        
        # 모든 검색 완료 대기
        results = []
        for plugin_name, task in tasks:
            try:
                result = await task
                if result:
                    result.provider = plugin_name
                    results.append(result)
            except Exception as e:
                logger.error(f"Search failed for plugin {plugin_name}: {e}")
                
        return results
    
    async def _search_with_timeout(self, provider: MetadataProvider, title: str, year: Optional[int] = None, season: Optional[int] = None, is_special: bool = False) -> Optional[Any]:
        """
        타임아웃이 적용된 검색
        
        Args:
            provider: 메타데이터 제공자
            title: 검색할 제목
            year: 연도 (옵션)
            season: 시즌 번호 (옵션)
            is_special: 특집 여부 (옵션)
            
        Returns:
            SearchResult or None: 검색 결과
        """
        try:
            timeout = provider.config.timeout
            return await asyncio.wait_for(
                provider.search(title, year, season, is_special),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Search timeout for provider {provider.config.name}")
            return None
        except Exception as e:
            logger.error(f"Search error for provider {provider.config.name}: {e}")
            return None
    
    async def close_all_providers(self):
        """모든 플러그인 인스턴스 정리"""
        for plugin_name, instance in self.instances.items():
            try:
                await instance.close()
                logger.info(f"Closed plugin: {plugin_name}")
            except Exception as e:
                logger.error(f"Error closing plugin {plugin_name}: {e}")
                
        self.instances.clear()
        self._executor.shutdown(wait=True)
    
    def get_available_plugins(self) -> List[str]:
        """사용 가능한 플러그인 목록 반환"""
        return list(self.plugins.keys())
    
    def get_active_plugins(self) -> List[str]:
        """활성화된 플러그인 목록 반환"""
        return [name for name, config in self.configs.items() 
                if config.enabled and name in self.instances]
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """플러그인 정보 반환"""
        if plugin_name not in self.plugins:
            return None
            
        config = self.configs.get(plugin_name)
        instance = self.instances.get(plugin_name)
        
        return {
            "name": plugin_name,
            "loaded": plugin_name in self.plugins,
            "initialized": plugin_name in self.instances,
            "enabled": config.enabled if config else False,
            "priority": config.priority if config else 0,
            "available": instance.is_available() if instance else False
        } 