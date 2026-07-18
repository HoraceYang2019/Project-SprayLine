@echo off
chcp 65001 >nul
title SprayLine UI Summary Station Aggregation Patch V18

echo ============================================================
echo SprayLine UI Summary/Station Aggregation Patch V18
echo This patch recalculates station status and top summary counts
echo from component metrics returned by Service API.
echo It will NOT delete database volume and will NOT rebuild tables.
echo ============================================================

if not exist "docker-compose.yml" (
  echo [FAIL] Please put this patch inside final_version folder, next to docker-compose.yml
  pause
  exit /b 1
)

if not exist "ui_v18\app\services\dashboard_service.py" (
  echo [FAIL] Missing ui_v18\app\services\dashboard_service.py
  pause
  exit /b 1
)

if not exist "ui\engineer\app\services" (
  echo [FAIL] Cannot find ui\engineer\app\services. Please run inside final_version.
  pause
  exit /b 1
)

echo [1/5] Stop current containers...
docker compose down --remove-orphans

echo [2/5] Backup current dashboard_service.py...
if not exist "ui\engineer\app\services\backup_before_v18" mkdir "ui\engineer\app\services\backup_before_v18"
copy /Y "ui\engineer\app\services\dashboard_service.py" "ui\engineer\app\services\backup_before_v18\dashboard_service_before_v18.py" >nul

echo [3/5] Apply V18 dashboard service...
copy /Y "ui_v18\app\services\dashboard_service.py" "ui\engineer\app\services\dashboard_service.py" >nul

echo [4/5] Rebuild engineer UI image without cache...
docker compose build --no-cache engineer
if errorlevel 1 (
  echo [FAIL] Docker build failed.
  pause
  exit /b 1
)

echo [5/5] Start system...
docker compose up -d
if errorlevel 1 (
  echo [FAIL] Docker start failed.
  pause
  exit /b 1
)

echo.
echo [OK] V18 patch applied.
echo Open http://localhost:8013 and press Ctrl+F5.
echo Expected: station headers and top summary counts follow component status.
echo.
pause
