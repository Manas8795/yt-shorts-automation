@echo off
title YouTube Shorts Uploader
cd /d "%~dp0"
echo ========================================================
echo Launching YouTube Shorts Uploader (PUBLIC Mode)
echo Account: manasagrawal8791@gmail.com
echo ========================================================
python uploader.py --visibility PUBLIC
pause
