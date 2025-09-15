"""
Unified File Parser - AnimeSorter

This module provides a unified interface for file parsing that wraps AnitopyFileParser
for backward compatibility with existing code that expects a FileParser class.
"""

import logging
from typing import Any

from .anitopy_parser import AnitopyFileParser

logger = logging.getLogger(__name__)


class FileParser:
    """
    Unified file parser that wraps AnitopyFileParser for backward compatibility.

    This class provides the same interface as the old FileParser but uses anitopy
    internally for all file parsing operations.
    """

    def __init__(self):
        """Initialize the file parser with anitopy backend."""
        self.anitopy_parser = AnitopyFileParser()
        logger.info("FileParser initialized with anitopy backend")

    def parse_filename(self, filename: str) -> dict[str, Any] | None:
        """
        Parse filename and extract metadata using anitopy.

        Args:
            filename: The filename to parse

        Returns:
            Parsed metadata dictionary or None if parsing fails
        """
        return self.anitopy_parser.parse_filename(filename)

    def extract_metadata(self, filename: str) -> dict[str, Any]:
        """
        Extract metadata from filename using anitopy.

        Args:
            filename: The filename to extract metadata from

        Returns:
            Standardized metadata dictionary
        """
        return self.anitopy_parser.extract_metadata(filename)

    def get_title(self, filename: str) -> str:
        """
        Extract title from filename.

        Args:
            filename: The filename to extract title from

        Returns:
            Extracted title or "Unknown" if extraction fails
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("title", "Unknown")

    def get_episode_info(self, filename: str) -> tuple[int | None, int | None]:
        """
        Extract season and episode information from filename.

        Args:
            filename: The filename to extract episode info from

        Returns:
            Tuple of (season, episode) or (None, None) if not found
        """
        metadata = self.extract_metadata(filename)
        season = metadata.get("season")
        episode = metadata.get("episode")
        return season, episode

    def get_resolution(self, filename: str) -> str | None:
        """
        Extract resolution from filename.

        Args:
            filename: The filename to extract resolution from

        Returns:
            Resolution string or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("resolution")

    def get_release_group(self, filename: str) -> str | None:
        """
        Extract release group from filename.

        Args:
            filename: The filename to extract release group from

        Returns:
            Release group string or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("release_group")

    def get_file_extension(self, filename: str) -> str | None:
        """
        Extract file extension from filename.

        Args:
            filename: The filename to extract extension from

        Returns:
            File extension without dot or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("file_extension")

    def get_video_codec(self, filename: str) -> str | None:
        """
        Extract video codec from filename.

        Args:
            filename: The filename to extract video codec from

        Returns:
            Video codec string or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("video_codec")

    def get_audio_codec(self, filename: str) -> str | None:
        """
        Extract audio codec from filename.

        Args:
            filename: The filename to extract audio codec from

        Returns:
            Audio codec string or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("audio_codec")

    def get_episode_title(self, filename: str) -> str | None:
        """
        Extract episode title from filename.

        Args:
            filename: The filename to extract episode title from

        Returns:
            Episode title string or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("episode_title")

    def get_source(self, filename: str) -> str | None:
        """
        Extract source information from filename.

        Args:
            filename: The filename to extract source from

        Returns:
            Source string (TV, Web, Blu-ray, etc.) or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("source")

    def get_quality(self, filename: str) -> str | None:
        """
        Extract quality information from filename.

        Args:
            filename: The filename to extract quality from

        Returns:
            Quality string (HD, SD, etc.) or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("quality")

    def get_language(self, filename: str) -> str | None:
        """
        Extract language information from filename.

        Args:
            filename: The filename to extract language from

        Returns:
            Language string or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("language")

    def get_subtitles(self, filename: str) -> str | None:
        """
        Extract subtitle information from filename.

        Args:
            filename: The filename to extract subtitle info from

        Returns:
            Subtitle string or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("subtitles")

    def get_crc32(self, filename: str) -> str | None:
        """
        Extract CRC32 checksum from filename.

        Args:
            filename: The filename to extract CRC32 from

        Returns:
            CRC32 string or None if not found
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("crc32")

    def get_confidence(self, filename: str) -> float:
        """
        Get parsing confidence score for filename.

        Args:
            filename: The filename to get confidence for

        Returns:
            Confidence score between 0.0 and 1.0
        """
        metadata = self.extract_metadata(filename)
        return metadata.get("confidence", 0.0)

    def is_valid_anime_file(self, filename: str) -> bool:
        """
        Check if the file is a valid anime file based on parsing results.

        Args:
            filename: The filename to check

        Returns:
            True if the file appears to be a valid anime file
        """
        metadata = self.extract_metadata(filename)

        # Check if we have at least a title and some basic info
        has_title = bool(metadata.get("title")) and metadata.get("title") != "Unknown"
        has_episode = metadata.get("episode") is not None
        has_season = metadata.get("season") is not None

        # Consider it valid if we have a title and either episode or season info
        return has_title and (has_episode or has_season)

    def get_all_metadata(self, filename: str) -> dict[str, Any]:
        """
        Get all available metadata for a filename.

        Args:
            filename: The filename to get metadata for

        Returns:
            Complete metadata dictionary
        """
        return self.extract_metadata(filename)
