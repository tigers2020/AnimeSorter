#!/usr/bin/env python3
"""
Analyze file matching between video and subtitle files
"""

import re
from pathlib import Path


def extract_base_name(filename: str) -> str:
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


def analyze_files():
    """Analyze the files in the directory"""
    directory = Path("F:/kiwi/애니")

    video_files = []
    subtitle_files = []

    for file_path in directory.iterdir():
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext in {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}:
                video_files.append(file_path)
            elif ext in {".srt", ".ass", ".ssa", ".vtt", ".sub", ".smi", ".idx", ".sub"}:
                subtitle_files.append(file_path)

    print("=== VIDEO FILES ===")
    for vf in video_files:
        base = extract_base_name(vf.name)
        print(f"Original: {vf.name}")
        print(f"Base:     {base}")
        print()

    print("=== SUBTITLE FILES ===")
    for sf in subtitle_files:
        base = extract_base_name(sf.name)
        print(f"Original: {sf.name}")
        print(f"Base:     {base}")
        print()

    print("=== MATCHING ANALYSIS ===")
    for vf in video_files:
        video_base = extract_base_name(vf.name)
        print(f"\nVideo: {vf.name}")
        print(f"Video base: {video_base}")

        matches = []
        for sf in subtitle_files:
            sub_base = extract_base_name(sf.name)
            if video_base == sub_base:
                matches.append(f"EXACT: {sf.name}")
            elif video_base in sub_base or sub_base in video_base:
                matches.append(f"PARTIAL: {sf.name}")

        if matches:
            for match in matches:
                print(f"  {match}")
        else:
            print("  NO MATCHES FOUND")


if __name__ == "__main__":
    analyze_files()
