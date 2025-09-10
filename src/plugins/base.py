"""
플러그인 시스템 기본 모듈 - AnimeSorter

플러그인 인터페이스와 플러그인 매니저를 정의합니다.
"""

import importlib
import importlib.util
import logging

logger = logging.getLogger(__name__)
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PluginInfo:
    """플러그인 정보"""

    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    enabled: bool = True


class BasePlugin(ABC):
    """플러그인 기본 클래스"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.info = self.get_plugin_info()

    @abstractmethod
    def get_plugin_info(self) -> PluginInfo:
        """플러그인 정보 반환"""

    def initialize(self) -> bool:
        """플러그인 초기화"""
        try:
            self.logger.info(f"플러그인 초기화: {self.info.name}")
            return True
        except Exception as e:
            self.logger.error(f"플러그인 초기화 실패: {e}")
            return False

    def cleanup(self) -> None:
        """플러그인 정리"""
        try:
            self.logger.info(f"플러그인 정리: {self.info.name}")
        except Exception as e:
            self.logger.error(f"플러그인 정리 실패: {e}")


class MetadataProvider(BasePlugin):
    """메타데이터 제공자 플러그인 기본 클래스"""

    @abstractmethod
    def get_metadata(self, title: str, **kwargs) -> dict[str, Any] | None:
        """
        제목을 기반으로 메타데이터를 검색합니다.

        Args:
            title: 검색할 애니메이션 제목
            **kwargs: 추가 검색 매개변수 (시즌, 에피소드 등)

        Returns:
            메타데이터 딕셔너리 또는 None (찾지 못한 경우)
        """

    @abstractmethod
    def search_anime(self, query: str, **kwargs) -> list[dict[str, Any]]:
        """
        애니메이션을 검색합니다.

        Args:
            query: 검색 쿼리
            **kwargs: 추가 검색 매개변수

        Returns:
            검색 결과 리스트
        """

    def is_available(self) -> bool:
        """플러그인이 사용 가능한지 확인"""
        return True


class FileProcessor(BasePlugin):
    """파일 처리기 플러그인 기본 클래스"""

    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """파일을 처리할 수 있는지 확인"""

    @abstractmethod
    def process_file(self, file_path: str, **kwargs) -> dict[str, Any]:
        """파일을 처리합니다"""


class PluginManager:
    """플러그인 매니저"""

    def __init__(self, plugin_dirs: list[str] | None = None):
        self.logger = logging.getLogger(__name__)
        self.plugins: dict[str, BasePlugin] = {}
        self.plugin_dirs = plugin_dirs or [str(Path(__file__).parent / "providers")]
        self.metadata_providers: dict[str, MetadataProvider] = {}
        self.file_processors: dict[str, FileProcessor] = {}
        for plugin_dir in self.plugin_dirs:
            Path(plugin_dir).mkdir(parents=True, exist_ok=True)

    def discover_plugins(self) -> list[str]:
        """사용 가능한 플러그인을 발견합니다"""
        discovered_plugins = []
        for plugin_dir in self.plugin_dirs:
            plugin_path = Path(plugin_dir)
            if not plugin_path.exists():
                continue
            for file_path in plugin_path.glob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
                    if spec and spec.loader:
                        discovered_plugins.append(str(file_path))
                        self.logger.info(f"플러그인 발견: {file_path.name}")
                except Exception as e:
                    self.logger.warning(f"플러그인 로드 실패 {file_path.name}: {e}")
        return discovered_plugins

    def load_plugin(self, plugin_path: str) -> BasePlugin | None:
        """플러그인을 로드합니다"""
        try:
            plugin_path_obj = Path(plugin_path)
            if not plugin_path_obj.exists():
                self.logger.error(f"플러그인 파일이 존재하지 않음: {plugin_path}")
                return None
            src_dir = plugin_path_obj.parent.parent.parent
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))
            plugin_dir = plugin_path_obj.parent
            if str(plugin_dir) not in sys.path:
                sys.path.insert(0, str(plugin_dir))
            spec = importlib.util.spec_from_file_location(plugin_path_obj.stem, plugin_path)
            if not spec or not spec.loader:
                self.logger.error(f"플러그인 모듈 로드 실패: {plugin_path}")
                return None
            module = importlib.util.module_from_spec(spec)
            module.__package__ = "src.plugins.providers"
            spec.loader.exec_module(module)
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BasePlugin)
                    and attr != BasePlugin
                    and attr != MetadataProvider
                    and attr != FileProcessor
                    and not attr.__abstractmethods__
                ):
                    plugin_class = attr
                    break
            if not plugin_class:
                self.logger.error(f"플러그인 클래스를 찾을 수 없음: {plugin_path}")
                return None
            plugin = plugin_class()
            if not plugin.initialize():
                self.logger.error(f"플러그인 초기화 실패: {plugin_path}")
                return None
            plugin_info = plugin.get_plugin_info()
            plugin_name = plugin_info.name
            if isinstance(plugin, MetadataProvider):
                self.metadata_providers[plugin_name] = plugin
                self.logger.info(f"메타데이터 제공자 로드: {plugin_name}")
            elif isinstance(plugin, FileProcessor):
                self.file_processors[plugin_name] = plugin
                self.logger.info(f"파일 처리기 로드: {plugin_name}")
            self.plugins[plugin_name] = plugin
            return plugin
        except Exception as e:
            self.logger.error(f"플러그인 로드 실패 {plugin_path}: {e}")
            return None

    def load_all_plugins(self) -> int:
        """모든 플러그인을 로드합니다"""
        discovered_plugins = self.discover_plugins()
        loaded_count = 0
        for plugin_path in discovered_plugins:
            if self.load_plugin(plugin_path):
                loaded_count += 1
        self.logger.info(f"플러그인 로드 완료: {loaded_count}/{len(discovered_plugins)}")
        return loaded_count

    def unload_plugin(self, plugin_name: str) -> bool:
        """플러그인을 언로드합니다"""
        try:
            if plugin_name not in self.plugins:
                self.logger.warning(f"플러그인을 찾을 수 없음: {plugin_name}")
                return False
            plugin = self.plugins[plugin_name]
            plugin.cleanup()
            if isinstance(plugin, MetadataProvider):
                self.metadata_providers.pop(plugin_name, None)
            elif isinstance(plugin, FileProcessor):
                self.file_processors.pop(plugin_name, None)
            del self.plugins[plugin_name]
            self.logger.info(f"플러그인 언로드: {plugin_name}")
            return True
        except Exception as e:
            self.logger.error(f"플러그인 언로드 실패 {plugin_name}: {e}")
            return False

    def get_metadata_providers(self) -> dict[str, MetadataProvider]:
        """메타데이터 제공자 목록 반환"""
        return self.metadata_providers.copy()

    def get_file_processors(self) -> dict[str, FileProcessor]:
        """파일 처리기 목록 반환"""
        return self.file_processors.copy()

    def get_plugin_info(self, plugin_name: str) -> PluginInfo | None:
        """플러그인 정보 반환"""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name].get_plugin_info()
        return None

    def list_plugins(self) -> list[PluginInfo]:
        """모든 플러그인 정보 반환"""
        return [plugin.get_plugin_info() for plugin in self.plugins.values()]

    def cleanup(self) -> None:
        """모든 플러그인 정리"""
        for plugin_name in list(self.plugins.keys()):
            self.unload_plugin(plugin_name)
