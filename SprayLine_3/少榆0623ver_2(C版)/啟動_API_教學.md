# 0623ver_2 啟動 API / UI 教學

## 一、正常啟動

請先打開 Docker Desktop，等 Docker Engine 正常啟動。

PowerShell 進入本資料夾：

```powershell
cd "C:\Users\jed92\Desktop\Project-SprayLine\0623ver_2"
```

啟動：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1 -Mode start -WithData
```

或直接雙擊：

```text
啟動_API_一鍵.bat
```

## 二、檢查狀態

```powershell
docker compose ps
```

應該看到 API / DB / UI / dataprocess 都是 Up。

## 三、網址

```text
API Swagger: http://localhost:8011/docs
Engineer UI: http://localhost:8013
Manager UI: http://localhost:8012
```

## 四、DB

```text
Host: localhost
Port: 5433
Database: sprayline
Username: postgres
Password: postgres
```

## 五、關閉

```powershell
docker compose down
```
