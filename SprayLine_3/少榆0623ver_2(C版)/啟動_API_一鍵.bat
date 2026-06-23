@echo off
setlocal
cd /d "%~dp0"
echo [SprayLine] Starting 0623ver_2 API / UI / DB...
powershell -ExecutionPolicy Bypass -File ".\start.ps1" -Mode start -WithData
echo.
echo API Swagger: http://localhost:8011/docs
echo Engineer UI: http://localhost:8013
echo Manager UI: http://localhost:8012
pause
