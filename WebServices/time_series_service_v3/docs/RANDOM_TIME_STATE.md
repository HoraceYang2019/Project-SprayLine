# Random Time State Version

本版新增「時間狀態隨機」功能。

## 直接執行

```bash
cd src
python time_series_service.py
```

現在會隨機產生 request：

```text
past    -> slider_value < 0
current -> slider_value = 0
future  -> slider_value > 0
```

所以不會每次都固定 current。

## API Demo

新增：

```text
GET /api/time-series/demo/random
```

使用方式：

```bash
cd src
uvicorn api_server:app --reload
```

瀏覽器開啟：

```text
http://127.0.0.1:8000/api/time-series/demo/random
```

每次重新整理會隨機取得 past/current/future。

## 保留固定 Demo

```text
GET /api/time-series/demo/current
GET /api/time-series/demo/past
GET /api/time-series/demo/future
```

正式 UI 串接仍使用：

```text
POST /api/time-series
```

## 注意

這裡隨機的是 `viewer_state.time_type`，不是 Rule Service 的 `state`。  
`state / risk_text / fault_detail` 仍然留給 Rule Service。
