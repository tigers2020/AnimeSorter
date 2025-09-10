@echo off
chcp 65001 >nul
echo Renaming video files in F:\kiwi\애니 to match subtitle files...
echo.

REM First, run in dry-run mode to see what would be changed
echo Running dry-run to preview changes...
python scripts\rename_videos_to_match_subtitles.py "F:\kiwi\애니" --dry-run

echo.
echo If the preview looks correct, press any key to execute the actual renaming...
echo Or close this window to cancel.
pause

REM Now execute the actual renaming
echo.
echo Executing actual renaming...
python scripts\rename_videos_to_match_subtitles.py "F:\kiwi\애니" --execute

echo.
echo Renaming complete! Check the log files for details.
pause
