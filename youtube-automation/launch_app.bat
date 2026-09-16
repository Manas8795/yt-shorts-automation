@echo off
title Google Flow - One-Time Sign In
echo =================================================================
echo Opening Chrome for Google Flow One-Time Sign-In...
echo Profile path: %~dp0browser_profile
echo =================================================================
echo.

python -m app.main
pause
