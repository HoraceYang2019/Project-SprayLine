@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo SprayLine UI Time + Shaoyu Rule Mapping Patch V19
echo This patch updates engineer UI only.
echo - keeps UI slider display unchanged
echo - sends correct minute offsets to Shaoyu Service API
echo - uses Shaoyu 0620 corrected sensor_thresholds.json for judgement
echo - keeps V18 component-to-station summary aggregation
echo It will NOT delete database and will NOT rebuild tables.
echo ============================================================

if not exist docker-compose.yml (
  echo [FAIL] Please put this patch inside final_version folder, next to docker-compose.yml
  pause
  exit /b 1
)
if not exist ui_v19\app\services\dashboard_service.py (
  echo [FAIL] Missing ui_v19\app\services\dashboard_service.py
  pause
  exit /b 1
)
if not exist ui_v19\app\services\webservices_client.py (
  echo [FAIL] Missing ui_v19\app\services\webservices_client.py
  pause
  exit /b 1
)
if not exist ui_v19\config\sensor_thresholds.json (
  echo [FAIL] Missing ui_v19\config\sensor_thresholds.json
  pause
  exit /b 1
)
if not exist ui\engineer\app\services (
  echo [FAIL] Cannot find ui\engineer\app\services. Are you in final_version?
  pause
  exit /b 1
)
if not exist ui\engineer\config (
  echo [FAIL] Cannot find ui\engineer\config. Are you in final_version?
  pause
  exit /b 1
)

echo [1/6] Stop current docker services...
docker compose down --remove-orphans

echo [2/6] Backup old UI files...
if not exist ui\engineer\backup_before_v19 mkdir ui\engineer\backup_before_v19
copy /Y ui\engineer\app\services\dashboard_service.py ui\engineer\backup_before_v19\dashboard_service.py.bak >nul
copy /Y ui\engineer\app\services\webservices_client.py ui\engineer\backup_before_v19\webservices_client.py.bak >nul
copy /Y ui\engineer\config\sensor_thresholds.json ui\engineer\backup_before_v19\sensor_thresholds.json.bak >nul

echo [3/6] Apply V19 files...
copy /Y ui_v19\app\services\dashboard_service.py ui\engineer\app\services\dashboard_service.py >nul
copy /Y ui_v19\app\services\webservices_client.py ui\engineer\app\services\webservices_client.py >nul
copy /Y ui_v19\config\sensor_thresholds.json ui\engineer\config\sensor_thresholds.json >nul

echo UI_V16 Database Integrated + V17 Mapping + V18 Aggregation + V19 TimeRuleFix> ui\engineer\VERSION.txt

echo [4/6] Rebuild engineer UI without cache...
docker compose build --no-cache engineer
if errorlevel 1 (
  echo [FAIL] docker compose build engineer failed.
  pause
  exit /b 1
)

echo [5/6] Start full system...
powershell -ExecutionPolicy Bypass -File .\start.ps1 -Mode start -WithData
if errorlevel 1 (
  echo [WARN] start.ps1 returned non-zero. Trying docker compose up -d...
  docker compose up -d
)

echo [6/6] Done.
echo Open http://localhost:8013 and press Ctrl+F5.
echo If it still looks old, run:
echo   docker exec sprayline_engineer sh -c "cat VERSION.txt"
pause
