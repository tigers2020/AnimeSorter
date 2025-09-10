#!/usr/bin/env python3
"""
Video File Renamer Based on Subtitle Files

This script renames video files in a directory to match their corresponding subtitle files.
It's designed specifically for the Korean anime directory structure.
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("video_rename.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class VideoSubtitleMatcher:
    """Matches video files with their corresponding subtitle files and renames them"""

    # Common video extensions
    VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}

    # Common subtitle extensions
    SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub", ".smi", ".idx", ".sub"}

    def __init__(self, directory_path: str):
        self.directory = Path(directory_path)
        self.backup_dir = self.directory / "_backup_renamed"
        self.rename_log = []

    def scan_files(self) -> tuple[list[Path], list[Path]]:
        """Scan directory for video and subtitle files"""
        video_files = []
        subtitle_files = []

        logger.info(f"Scanning directory: {self.directory}")

        for file_path in self.directory.iterdir():
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in self.VIDEO_EXTENSIONS:
                    video_files.append(file_path)
                elif ext in self.SUBTITLE_EXTENSIONS:
                    subtitle_files.append(file_path)

        logger.info(
            f"Found {len(video_files)} video files and {len(subtitle_files)} subtitle files"
        )
        return video_files, subtitle_files

    def extract_base_name(self, filename: str) -> str:
        """Extract base name from filename, removing common patterns"""
        # Remove extension
        base = Path(filename).stem

        # Remove group names in brackets at the beginning
        base = re.sub(r"^\[.*?\]\s*", "", base)

        # Remove quality indicators in brackets and parentheses
        quality_patterns = [
            r"\s*\[.*?1080p.*?\]",
            r"\s*\[.*?720p.*?\]",
            r"\s*\[.*?480p.*?\]",
            r"\s*\[.*?HD.*?\]",
            r"\s*\[.*?SD.*?\]",
            r"\s*\[.*?BluRay.*?\]",
            r"\s*\[.*?WEB.*?\]",
            r"\s*\[.*?BDRip.*?\]",
            r"\s*\[.*?DVDRip.*?\]",
            r"\s*\(.*?1080p.*?\)",
            r"\s*\(.*?720p.*?\)",
            r"\s*\(.*?480p.*?\)",
            r"\s*\(.*?HD.*?\)",
            r"\s*\(.*?SD.*?\)",
            r"\s*\(.*?BluRay.*?\)",
            r"\s*\(.*?WEB.*?\)",
            r"\s*\(.*?BDRip.*?\)",
            r"\s*\(.*?DVDRip.*?\)",
        ]

        for pattern in quality_patterns:
            base = re.sub(pattern, "", base, flags=re.IGNORECASE)

        # Remove hash codes in brackets at the end
        base = re.sub(r"\s*\[[A-F0-9]{8,}\]$", "", base)

        # Clean up extra spaces and dots
        base = re.sub(r"\s+", " ", base).strip()
        base = re.sub(r"\.+", ".", base).strip(".")

        return base

    def find_matching_subtitle(
        self, video_file: Path, subtitle_files: list[Path]
    ) -> Optional[Path]:
        """Find matching subtitle file for a video file"""
        video_base = self.extract_base_name(video_file.name)

        # Try exact match first
        for sub_file in subtitle_files:
            sub_base = self.extract_base_name(sub_file.name)
            if video_base == sub_base:
                return sub_file

        # Try matching by episode numbers, show name, and resolution
        video_episode = self.extract_episode_number(video_file.name)
        video_show = self.extract_show_name(video_file.name)
        video_resolution = self.extract_resolution(video_file.name)

        if video_episode and video_show:
            # First try exact resolution match
            for sub_file in subtitle_files:
                sub_episode = self.extract_episode_number(sub_file.name)
                sub_show = self.extract_show_name(sub_file.name)
                sub_resolution = self.extract_resolution(sub_file.name)

                # Match if episode numbers match, show names are similar, and resolutions match
                if (
                    sub_episode == video_episode
                    and self._names_similar(video_show, sub_show)
                    and sub_resolution == video_resolution
                ):
                    return sub_file

            # If no exact resolution match, try any resolution match
            for sub_file in subtitle_files:
                sub_episode = self.extract_episode_number(sub_file.name)
                sub_show = self.extract_show_name(sub_file.name)

                # Match if episode numbers match and show names are similar
                if sub_episode == video_episode and self._names_similar(video_show, sub_show):
                    return sub_file

        # Try partial match (subtitle name contains video name or vice versa)
        for sub_file in subtitle_files:
            sub_base = self.extract_base_name(sub_file.name)
            if video_base in sub_base or sub_base in video_base:
                return sub_file

        return None

    def extract_show_name(self, filename: str) -> str:
        """Extract show name from filename"""
        base = Path(filename).stem

        # Remove group name at beginning
        base = re.sub(r"^\[.*?\]\s*", "", base)

        # Remove episode information - be more specific
        base = re.sub(r"\s*S\d+E\d+.*$", "", base)  # S01E10
        base = re.sub(r"\s*S\d+\s*-\s*\d+.*$", "", base)  # S4 - 10
        base = re.sub(r"\s*-\s*\d+.*$", "", base)  # - 10
        base = re.sub(r"\s*\d+화.*$", "", base)  # 10화
        base = re.sub(r"\s*第\d+話.*$", "", base)  # 第10話

        # Clean up
        base = re.sub(r"\s+", " ", base).strip()
        return base

    def _names_similar(self, name1: str, name2: str) -> bool:
        """Check if two show names are similar enough to be the same show"""
        # Normalize names
        name1 = re.sub(r"[^\w\s]", "", name1.lower())
        name2 = re.sub(r"[^\w\s]", "", name2.lower())

        # Check if one contains the other
        if name1 in name2 or name2 in name1:
            return True

        # Check if they share significant words
        words1 = set(name1.split())
        words2 = set(name2.split())

        # Remove common words that don't help with matching
        common_words_to_ignore = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        words1 = words1 - common_words_to_ignore
        words2 = words2 - common_words_to_ignore

        # If they share more than 30% of words, consider them similar
        if words1 and words2:
            common_words = words1.intersection(words2)
            similarity = len(common_words) / min(len(words1), len(words2))
            return similarity > 0.3

        return False

    def extract_episode_number(self, filename: str) -> Optional[str]:
        """Extract episode number from filename"""
        patterns = [
            r"[Ee](\d+)",  # E01, e01
            r"(\d+)화",  # 1화, 2화
            r"第(\d+)話",  # 第1話
            r"[Ee]p(\d+)",  # Ep01
            r"(\d+)",  # Just numbers
        ]

        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)

        return None

    def extract_resolution(self, filename: str) -> Optional[str]:
        """Extract resolution from filename"""
        patterns = [
            r"(\d+p)",  # 1080p, 720p, 480p
            r"(HD)",  # HD
            r"(SD)",  # SD
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1).lower()

        return None

    def create_backup(self, file_path: Path) -> Path:
        """Create backup of original file"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)

        backup_path = self.backup_dir / file_path.name
        shutil.copy2(file_path, backup_path)
        logger.info(f"Backup created: {backup_path}")
        return backup_path

    def rename_video_file(
        self, video_file: Path, subtitle_file: Path, dry_run: bool = True
    ) -> bool:
        """Rename video file to match subtitle file name"""
        # Get subtitle name without extension
        subtitle_stem = subtitle_file.stem
        video_extension = video_file.suffix

        # Create new video filename
        new_video_name = f"{subtitle_stem}{video_extension}"
        new_video_path = video_file.parent / new_video_name

        # Check if target already exists
        if new_video_path.exists() and new_video_path != video_file:
            logger.warning(f"Target file already exists: {new_video_path}")
            return False

        if dry_run:
            logger.info(f"[DRY RUN] Would rename: {video_file.name} -> {new_video_name}")
            self.rename_log.append(
                {
                    "original": str(video_file),
                    "new": str(new_video_path),
                    "subtitle": str(subtitle_file),
                    "action": "rename",
                }
            )
            return True

        try:
            # Create backup
            self.create_backup(video_file)

            # Rename the file
            video_file.rename(new_video_path)
            logger.info(f"Renamed: {video_file.name} -> {new_video_name}")

            self.rename_log.append(
                {
                    "original": str(video_file),
                    "new": str(new_video_path),
                    "subtitle": str(subtitle_file),
                    "action": "renamed",
                }
            )
            return True

        except Exception as e:
            logger.error(f"Failed to rename {video_file.name}: {e}")
            return False

    def process_directory(self, dry_run: bool = True) -> dict[str, int]:
        """Process all files in directory"""
        video_files, subtitle_files = self.scan_files()

        if not video_files:
            logger.warning("No video files found in directory")
            return {"processed": 0, "renamed": 0, "skipped": 0}

        if not subtitle_files:
            logger.warning("No subtitle files found in directory")
            return {"processed": 0, "renamed": 0, "skipped": 0}

        stats = {"processed": 0, "renamed": 0, "skipped": 0}

        logger.info(f"Processing {len(video_files)} video files...")

        for video_file in video_files:
            stats["processed"] += 1

            # Find matching subtitle
            matching_subtitle = self.find_matching_subtitle(video_file, subtitle_files)

            if not matching_subtitle:
                logger.warning(f"No matching subtitle found for: {video_file.name}")
                stats["skipped"] += 1
                continue

            # Check if already matches
            video_base = self.extract_base_name(video_file.name)
            sub_base = self.extract_base_name(matching_subtitle.name)

            if video_base == sub_base:
                logger.info(f"Already matches: {video_file.name}")
                stats["skipped"] += 1
                continue

            # Rename the file
            if self.rename_video_file(video_file, matching_subtitle, dry_run):
                stats["renamed"] += 1

        return stats

    def save_rename_log(self):
        """Save rename log to file"""
        log_file = self.directory / "rename_log.json"
        import json

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(self.rename_log, f, ensure_ascii=False, indent=2)
        logger.info(f"Rename log saved to: {log_file}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Rename video files to match subtitle files")
    parser.add_argument("directory", help="Directory containing video and subtitle files")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be renamed without actually renaming (default: True)",
    )
    parser.add_argument(
        "--execute", action="store_true", help="Actually perform the renaming (overrides --dry-run)"
    )

    args = parser.parse_args()

    # Handle Unicode paths properly
    try:
        directory_path = Path(args.directory)
    except UnicodeDecodeError:
        # Try with different encoding
        directory_path = Path(args.directory.encode("utf-8").decode("utf-8"))

    if not directory_path.exists():
        logger.error(f"Directory does not exist: {directory_path}")
        return

    if not directory_path.is_dir():
        logger.error(f"Path is not a directory: {directory_path}")
        return

    # Determine if this is a dry run
    dry_run = not args.execute

    if dry_run:
        logger.info("Running in DRY RUN mode - no files will be modified")
    else:
        logger.info("Running in EXECUTE mode - files will be renamed")

    # Create matcher and process
    matcher = VideoSubtitleMatcher(directory_path)
    stats = matcher.process_directory(dry_run=dry_run)

    # Print summary
    logger.info("=" * 50)
    logger.info("SUMMARY:")
    logger.info(f"Files processed: {stats['processed']}")
    logger.info(f"Files renamed: {stats['renamed']}")
    logger.info(f"Files skipped: {stats['skipped']}")

    if dry_run and stats["renamed"] > 0:
        logger.info("\nTo actually perform the renaming, run with --execute flag")

    # Save log
    matcher.save_rename_log()


if __name__ == "__main__":
    main()
