@echo off
title Pipeline Status Manager
cd /d "%~dp0"
python manage_status.py
pause
