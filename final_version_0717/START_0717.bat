@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting final_version_0717 with the existing 0627 database...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\start.ps1" -Mode start
if errorlevel 1 (
  echo.
  echo Startup failed. Please keep this window and take a screenshot.
  pause
  exit /b 1
)
start "" "http://localhost:8013"
echo.
echo Engineer UI: http://localhost:8013
pause
