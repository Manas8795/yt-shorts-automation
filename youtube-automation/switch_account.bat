@echo off
echo =======================================================
echo     Google Flow - Switch / Change Google Account
echo =======================================================
echo.
echo 1. Cleaning old account session in browser_profile...
taskkill /F /IM chrome.exe /FI "WINDOWTITLE eq Google Flow*" >nul 2>&1
timeout /t 2 /nobreak >nul

if exist "browser_profile" (
    rmdir /S /Q "browser_profile" >nul 2>&1
)
mkdir "browser_profile"

echo 2. Opening Google Chrome with fresh profile...
echo.
echo >> PLEASE SIGN IN WITH YOUR NEW GOOGLE ACCOUNT ON FLOW <<
echo.
echo Once you see the Google Flow project workspace, simply close the browser.
echo.
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%~dp0browser_profile" "https://flow.google.com/"
