# 0623ver_2 Sequence Diagram：UI / API / DB / Ontology Rule 串接

## 1. UI 查詢 Past / Current / Future 與零件狀態

```mermaid
sequenceDiagram
    autonumber

    participant UI as Engineer UI
    participant API as FastAPI API Server
    participant Bridge as UI Bridge
    participant Service as Integrated Service
    participant DB as PostgreSQL Database
    participant Rule as Ontology Rule Engine
    participant TTL as TTL Threshold Knowledge

    UI->>API: GET dashboard data
    API->>Bridge: Normalize station and component names
    Bridge->>Service: Query station summary and component detail
    Service->>DB: SELECT sensor_1min and sensor_3min
    DB-->>Service: Return sensor rows
    Service->>Rule: infer_state metric and value
    Rule->>TTL: Read threshold TTL
    TTL-->>Rule: Return normal warning fault thresholds
    Rule-->>Service: Return state cause_id response_ids
    Service-->>Bridge: Format UI JSON
    Bridge-->>API: Return dashboard and component detail response
    API-->>UI: Render station status component status and trend chart
```

## 2. Service Orchestration：Future / Monitoring / Alert / DB write-back

```mermaid
sequenceDiagram
    autonumber

    participant Client as UI or Swagger
    participant API as FastAPI API Server
    participant Orchestrator as Service Orchestration Adapter
    participant Integrated as Integrated SprayLine Service
    participant Future as Future Service
    participant Monitor as Monitoring Worker
    participant Rule as Ontology Rule Engine
    participant DB as PostgreSQL Database
    participant Catalog as Cause Response Catalog

    Client->>API: POST integrated run once
    API->>Orchestrator: run_integrated_service_query
    Orchestrator->>Integrated: run_integrated_once
    Integrated->>DB: SELECT sensor data
    DB-->>Integrated: Return past and current sensor rows

    Integrated->>Rule: Infer state from TTL rule
    Rule-->>Integrated: Return state cause_id response_ids

    Integrated->>Future: Create future prediction result
    Future->>DB: INSERT future_prediction_result
    DB-->>Future: Return prediction_id

    Integrated->>Monitor: Build monitoring and alert event
    Monitor->>Catalog: Check cause_id and response_id mapping
    Catalog-->>Monitor: Catalog mapping OK
    Monitor->>DB: INSERT alert_event and alert links
    Monitor->>DB: UPDATE batch_station_status

    Integrated-->>Orchestrator: Return integrated result
    Orchestrator-->>API: Return success and write_back result
    API-->>Client: Return API response
```

## 3. Ontology / TTL / Rule 推論流程

```mermaid
sequenceDiagram
    autonumber

    participant CSV as threshold_reference.csv
    participant Parser as threshold_to_ttl.py
    participant TTL as sprayline_threshold.ttl
    participant Rule as rule_inference.py
    participant Result as Inference Result

    CSV->>Parser: Read threshold source table
    Parser->>TTL: Generate TTL knowledge file
    Rule->>TTL: Load SensorThreshold rules
    Rule->>Rule: Compare metric value with thresholds
    Rule->>Result: Output normal warning fault
    Rule->>Result: Output cause_id and response_ids
```

## 4. 報告用說法

這版時序圖主要回應老師逐字稿中「UI 呼叫誰、再呼叫誰、最後誰回傳」的問題。

第一條線是 UI 查詢線。前端透過 dashboard-data、summary、station-detail、component-detail 呼叫 API。API 再透過 UI Bridge 和 Integrated Service 查詢 PostgreSQL 中的 sensor data，並透過 Ontology Rule 讀取 TTL threshold 判斷 normal、warning、fault，最後把整理好的 JSON 回傳給 UI 顯示。

第二條線是 service orchestration 線。透過 integrated run once 呼叫少榆端的 integrated service，執行 future prediction、monitoring、alert event、cause / response mapping，以及 PostgreSQL write-back。

第三條線是 Ontology / TTL / Rule 推論線。threshold_reference.csv 是 threshold 來源檔，threshold_to_ttl.py 會把 CSV 轉成 sprayline_threshold.ttl，rule_inference.py 再讀取 TTL，根據 metric 與 value 判斷 normal、warning、fault，並回傳 cause_id 與 response_ids。
