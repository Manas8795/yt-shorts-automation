@echo off
title Cleanup Original Videos
cd /d "%~dp0"
echo =================================================================
echo  ORIGINAL VIDEOS CLEANUP UTILITY
echo =================================================================
echo  Safely deletes original raw videos from youtube-automation
echo  ONLY after verifying that the final edited video exists.
echo =================================================================
echo.
python cleanup_original_videos.py
echo.
pause
