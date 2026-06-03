# Dashboard v15 Service Contract

本資料夾取代舊的 舊中央時序服務 中央服務方向，改採 Dashboard v15 / DB Schema v2 的多 service function 工作流。

`dashboard_v15_service_contract.py` 只定義 service contract，不回傳假資料。  
正式實作需由 FastAPI + PostgreSQL/TimescaleDB + Redis Cache 串接。
