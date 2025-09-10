# Video File Renamer Based on Subtitle Files

This script renames video files in a directory to match their corresponding subtitle files. It's specifically designed for Korean anime directory structures.

## Files Created

- `rename_videos_to_match_subtitles.py` - Main Python script
- `rename_kiwi_anime.bat` - Windows batch file for your specific directory
- `rename_kiwi_anime.ps1` - PowerShell script with better Unicode support

## Usage

### Option 1: Use the provided batch/PowerShell scripts

Simply run one of these files:
- `rename_kiwi_anime.bat` (Windows Command Prompt)
- `rename_kiwi_anime.ps1` (PowerShell - recommended for Korean characters)

### Option 2: Run the Python script directly

```bash
# First, preview what would be changed (dry run)
python scripts/rename_videos_to_match_subtitles.py "F:\kiwi\애니" --dry-run

# If the preview looks correct, execute the actual renaming
python scripts/rename_videos_to_match_subtitles.py "F:\kiwi\애니" --execute
```

## How It Works

1. **Scans the directory** for video files (mp4, mkv, avi, etc.) and subtitle files (srt, ass, ssa, etc.)

2. **Matches files** by:
   - Exact base name match
   - Partial name match (one contains the other)
   - Episode number matching

3. **Extracts clean names** by removing:
   - Quality indicators (1080p, 720p, HD, etc.)
   - Group names in brackets
   - Extra spaces and dots

4. **Creates backups** of original files in `_backup_renamed` folder

5. **Renames video files** to match their subtitle file names

## Safety Features

- **Dry run mode** (default) - shows what would be changed without actually renaming
- **Backup creation** - original files are backed up before renaming
- **Conflict detection** - won't overwrite existing files
- **Detailed logging** - all operations are logged to `video_rename.log`
- **Rename log** - JSON file with all rename operations saved as `rename_log.json`

## Example

If you have:
- Video: `[Group] Anime Name S01E01 [1080p].mkv`
- Subtitle: `Anime Name S01E01.srt`

The script will rename the video to: `Anime Name S01E01.mkv`

## Supported File Types

**Video files:** .mp4, .mkv, .avi, .mov, .wmv, .flv, .webm, .m4v
**Subtitle files:** .srt, .ass, .ssa, .vtt, .sub, .smi, .idx, .sub

## Log Files

- `video_rename.log` - Detailed operation log
- `rename_log.json` - JSON file with all rename operations
- `_backup_renamed/` - Folder containing backups of original files
