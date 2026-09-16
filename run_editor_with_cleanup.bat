@echo off
title Batch Video Editor with Folder Cleanup
cd /d "%~dp0video-editor"
echo =================================================================
echo  BATCH VIDEO EDITOR (WITH VEHICLE FOLDER CLEANUP)
echo =================================================================
echo  1. Covers watermark with channel logo and preserves audio.
echo  2. Organizes output into: video-editor/output/
echo  3. DELETES the entire original vehicle folder from youtube-automation
echo     ONLY AFTER verifying the edited video is intact (>500KB).
echo =================================================================
echo.
python batch_editor.py --delete-original
echo.
pause
