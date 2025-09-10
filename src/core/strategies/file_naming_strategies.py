"""
File Naming Strategies

This module provides various file naming strategies for different use cases
and preferences in file organization.
"""

import logging

logger = logging.getLogger(__name__)
import re
import time
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.interfaces.file_organization_interface import (
    FileConflictResolution, IFileNamingStrategy)


@dataclass
class NamingConfig:
    """Configuration for file naming strategies"""

    use_season_episode: bool = True
    use_resolution: bool = True
    use_year: bool = True
    use_group: bool = False
    use_quality_indicators: bool = True
    sanitize_special_chars: bool = True
    max_title_length: int = 100
    season_format: str = "S{season:02d}"
    episode_format: str = "E{episode:02d}"
    resolution_format: str = "[{resolution}]"
    year_format: str = "({year})"
    group_format: str = "[{group}]"
    max_unique_attempts: int = 1000
    enable_timestamp_fallback: bool = True


class BaseNamingStrategy(IFileNamingStrategy):
    """Base class for file naming strategies"""

    def __init__(self, config: NamingConfig, logger=None):
        self.config = config
        self.logger = logger

    def generate_target_path(
        self, source_path: Path, metadata: dict[str, Any], destination_root: Path
    ) -> Path:
        """Generate target path - always preserve original filename"""
        # 항상 원본 파일명을 유지하고 디렉토리만 변경
        return destination_root / source_path.name

    def resolve_conflict(self, target_path: Path, resolution: FileConflictResolution) -> Path:
        """Resolve file naming conflicts"""
        if not target_path.exists():
            return target_path
        if (
            resolution == FileConflictResolution.SKIP
            or resolution == FileConflictResolution.OVERWRITE
        ):
            return target_path
        if resolution == FileConflictResolution.RENAME:
            return self._generate_unique_name(target_path)
        if resolution == FileConflictResolution.BACKUP_AND_OVERWRITE:
            backup_path = target_path.with_suffix(f"{target_path.suffix}.backup_{int(time.time())}")
            try:
                import shutil

                shutil.copy2(target_path, backup_path)
                if self.logger:
                    self.logger.info(f"Backup created: {backup_path}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Backup creation failed: {e}")
            return target_path
        return target_path

    def _sanitize_title(self, title: str) -> str:
        """Sanitize title for filesystem compatibility"""
        if not self.config.sanitize_special_chars:
            return title
        invalid_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
        sanitized = title
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")
        sanitized = re.sub("\\s+", " ", sanitized).strip()
        if len(sanitized) > self.config.max_title_length:
            sanitized = sanitized[: self.config.max_title_length].rstrip()
        if not sanitized:
            sanitized = "Unknown"
        return sanitized

    def _create_directory_structure(
        self, destination_root: Path, title: str, season: int, year: int | None
    ) -> Path:
        """Create directory structure for the file"""
        base_dir = destination_root / title
        if self.config.use_year and year:
            base_dir = base_dir / str(year)
        if self.config.use_season_episode:
            season_folder = self.config.season_format.format(season=season)
            base_dir = base_dir / season_folder
        return base_dir

    def _generate_filename(
        self, title: str, season: int, episode: int, resolution: str, year: int | None, group: str
    ) -> str:
        """Generate filename based on strategy"""
        parts = []
        parts.append(title)
        if self.config.use_season_episode:
            season_part = self.config.season_format.format(season=season)
            episode_part = self.config.episode_format.format(episode=episode)
            parts.append(f"{season_part}{episode_part}")
        if self.config.use_resolution and resolution and resolution != "Unknown":
            parts.append(self.config.resolution_format.format(resolution=resolution))
        if self.config.use_year and year:
            parts.append(self.config.year_format.format(year=year))
        if self.config.use_group and group and group != "Unknown":
            parts.append(self.config.group_format.format(group=group))
        return " - ".join(parts)

    def _generate_unique_name(self, target_path: Path) -> Path:
        """Generate a unique name for the target path with safety limits"""
        if not target_path.exists():
            return target_path
        stem = target_path.stem
        suffix = target_path.suffix
        max_attempts = self.config.max_unique_attempts
        for counter in range(1, max_attempts + 1):
            new_name = f"{stem}_{counter}{suffix}"
            new_path = target_path.parent / new_name
            if not new_path.exists():
                return new_path
        if self.config.enable_timestamp_fallback:
            timestamp = int(time.time())
            new_name = f"{stem}_{timestamp}{suffix}"
            new_path = target_path.parent / new_name
            if not new_path.exists():
                return new_path
        from uuid import uuid4

        uuid_suffix = str(uuid4())[:8]
        new_name = f"{stem}_{uuid_suffix}{suffix}"
        return target_path.parent / new_name

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this naming strategy"""


class StandardNamingStrategy(BaseNamingStrategy):
    """Standard naming strategy: Title - S01E01 [1080p] (2023)"""

    def __init__(self, config: NamingConfig = None, logger=None):
        if config is None:
            config = NamingConfig()
        super().__init__(config, logger)

    def get_strategy_name(self) -> str:
        return "Standard"


class MinimalNamingStrategy(BaseNamingStrategy):
    """Minimal naming strategy: Title S01E01"""

    def __init__(self, config: NamingConfig = None, logger=None):
        if config is None:
            config = NamingConfig(
                use_resolution=False,
                use_year=False,
                use_group=False,
                season_format="S{season:02d}",
                episode_format="E{episode:02d}",
            )
        super().__init__(config, logger)

    def get_strategy_name(self) -> str:
        return "Minimal"


class DetailedNamingStrategy(BaseNamingStrategy):
    """Detailed naming strategy: Title - S01E01 [1080p] (2023) [Group]"""

    def __init__(self, config: NamingConfig = None, logger=None):
        if config is None:
            config = NamingConfig(
                use_season_episode=True,
                use_resolution=True,
                use_year=True,
                use_group=True,
                use_quality_indicators=True,
            )
        super().__init__(config, logger)

    def get_strategy_name(self) -> str:
        return "Detailed"


class AnimeNamingStrategy(BaseNamingStrategy):
    """Anime-specific naming strategy with special handling for anime conventions"""

    def __init__(self, config: NamingConfig = None, logger=None):
        if config is None:
            config = NamingConfig(
                use_season_episode=True,
                use_resolution=True,
                use_year=True,
                use_group=True,
                season_format="Season {season}",
                episode_format="Episode {episode:02d}",
                resolution_format="[{resolution}]",
            )
        super().__init__(config, logger)

    def _create_directory_structure(
        self, destination_root: Path, title: str, season: int, year: int | None
    ) -> Path:
        """Create anime-specific directory structure"""
        base_dir = destination_root / title
        if self.config.use_year and year:
            base_dir = base_dir / str(year)
        if self.config.use_season_episode:
            season_folder = self.config.season_format.format(season=season)
            base_dir = base_dir / season_folder
        return base_dir

    def get_strategy_name(self) -> str:
        return "Anime"


class MovieNamingStrategy(BaseNamingStrategy):
    """Movie-specific naming strategy"""

    def __init__(self, config: NamingConfig = None, logger=None):
        if config is None:
            config = NamingConfig(
                use_season_episode=False, use_resolution=True, use_year=True, use_group=False
            )
        super().__init__(config, logger)

    def _create_directory_structure(
        self, destination_root: Path, title: str, season: int, year: int | None
    ) -> Path:
        """Create movie-specific directory structure"""
        base_dir = destination_root / title
        if self.config.use_year and year:
            base_dir = base_dir / str(year)
        return base_dir

    def get_strategy_name(self) -> str:
        return "Movie"


class NamingStrategyFactory:
    """Factory for creating naming strategies"""

    @staticmethod
    def create_strategy(
        strategy_name: str, config: NamingConfig = None, logger=None
    ) -> IFileNamingStrategy:
        """Create a naming strategy by name"""
        strategies = {
            "standard": StandardNamingStrategy,
            "minimal": MinimalNamingStrategy,
            "detailed": DetailedNamingStrategy,
            "anime": AnimeNamingStrategy,
            "movie": MovieNamingStrategy,
        }
        strategy_class = strategies.get(strategy_name.lower())
        if not strategy_class:
            raise ValueError(f"Unknown naming strategy: {strategy_name}")
        return strategy_class(config, logger)

    @staticmethod
    def get_available_strategies() -> list[str]:
        """Get list of available strategy names"""
        return ["standard", "minimal", "detailed", "anime", "movie"]

    @staticmethod
    def get_strategy_description(strategy_name: str) -> str:
        """Get description of a naming strategy"""
        descriptions = {
            "standard": "Title - S01E01 [1080p] (2023)",
            "minimal": "Title S01E01",
            "detailed": "Title - S01E01 [1080p] (2023) [Group]",
            "anime": "Title/Season 1/Episode 01 [1080p]",
            "movie": "Title (2023) [1080p]",
        }
        return descriptions.get(strategy_name.lower(), "Unknown strategy")
