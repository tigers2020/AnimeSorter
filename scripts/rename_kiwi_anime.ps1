# PowerShell script to rename video files in F:\kiwi\애니 to match subtitle files
# This script provides better Unicode support for Korean characters

Write-Host "Renaming video files in F:\kiwi\애니 to match subtitle files..." -ForegroundColor Green
Write-Host ""

# First, run in dry-run mode to see what would be changed
Write-Host "Running dry-run to preview changes..." -ForegroundColor Yellow
python scripts/rename_videos_to_match_subtitles.py "F:\kiwi\애니" --dry-run

Write-Host ""
Write-Host "If the preview looks correct, press any key to execute the actual renaming..." -ForegroundColor Cyan
Write-Host "Or close this window to cancel." -ForegroundColor Red
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Now execute the actual renaming
Write-Host ""
Write-Host "Executing actual renaming..." -ForegroundColor Yellow
python scripts/rename_videos_to_match_subtitles.py "F:\kiwi\애니" --execute

Write-Host ""
Write-Host "Renaming complete! Check the log files for details." -ForegroundColor Green
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
