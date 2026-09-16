@echo off
title Batch Video Editor
cd /d "%~dp0video-editor"
echo =================================================================
echo  BATCH VIDEO EDITOR
echo =================================================================
echo  Covers watermark with channel logo and preserves audio stream.
echo =================================================================
echo.
python batch_editor.py
echo.
pause
