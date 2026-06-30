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
docker ps -a --filter "name=sprayline" --format "{{.Names}}" | ForEach-Object { docker rm -f $_ }

docker compose build api
docker compose build frontend
docker compose build engineer

docker compose up -d db
docker compose --profile setup run --rm db-setup

docker compose up -d api
docker compose up -d frontend
docker compose up -d engineer
docker compose up -d dataprocess
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


## Step3c hotfix
- 修正 TimeMode 未來 Future 顯示：UI selected_time 現在使用後端 viewer_state.future_time，而不是 anchor_time。
- 過去 Past 仍顯示 anchor_time；現在 Now 顯示 anchor_time；批次 BatchMode 不受影響。
