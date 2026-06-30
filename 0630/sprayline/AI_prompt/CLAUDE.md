# Project-SprayLine — CLAUDE.md

## 協作規則（最高優先）

1. **語言**：所有回應一律使用**繁體中文**。
2. **Git 操作**：不自動執行 `git push`；每完成一個階段後，僅提醒使用者確認是否上傳，不主動執行。
3. **工作範圍**：僅負責整合專案內容，以及修改 `Database/` 與 `Omiverse/` 資料夾內的檔案；其他區域（`SprayLine_*/`、`WebServices/`、`UserInterfaceDesign/` 等）只讀參考，不主動修改。
4. **階段提醒**：每完成一個明確階段，主動提示目前進度，並詢問是否繼續下一步。
5. **開發前同步**：每次開始開發或修改功能前，先確認並執行 `git pull` 拉取所有遠端最新資料，確保本地與遠端同步後再進行任何修改。

---

## 專案概覽

本專案是一套工業 IoT **數位孿生系統**，用於噴塗生產線的即時監控與預測性維護（PdM）。目標客戶為輝創（Huichuang），涵蓋三個噴塗工站（底漆、面漆、金漆）。

系統實作五階段數位孿生流程：

| 階段 | 名稱 | 說明 |
|------|------|------|
| 1 | 感測（Sensing） | 機器人位置、流量、壓力、噴幅（原始感測資料） |
| 2 | 辨識（Identification） | 狀態分類（normal / warning / fault）—製程、機器人、濾網、噴嘴 |
| 3 | 推理（Inference） | 故障原因與品質預測（RDF/SPARQL 推理） |
| 4 | 評估（Evaluation） | 零件 RUL、噴幅、品質指標計算 |
| 5 | 適應（Adaptation） | 零件與製程管理建議 |

---

## 專案結構

```
Project-SprayLine/
├── SprayLine_1/          推理引擎 v1：Python + rdflib，門檻值型 SPARQL 推理
├── SprayLine_2/          SPARQL/MQTT 管線 v2：rdflib + paho-mqtt，規則檔於 rules/*.rq
├── SprayLine_3/          完整管線 v3：JSON→TTL、SHACL 驗證，單一入口 pipeline.py
├── WebServices/          時間序列服務層：time_series_service.py，KPI 計算
├── Database/             資料庫綱要設計：PostgreSQL + TimescaleDB，ER 模型與參考文件 ★可修改
├── DataPreprocess/       邊緣預處理筆記本：IQR 離群值偵測、5 秒滑動平均
├── UserInterfaceDesign/  Streamlit 儀表板（UI_v2.py）與 HTML5 儀表板
├── Omiverse/             NVIDIA Omniverse 整合介面（早期設計階段） ★可修改
├── Data/                 原始及探索性感測器資料筆記本
└── CLAUDE.md             本檔案
```

> `★可修改`：Claude 在此專案中僅主動修改這兩個資料夾內的檔案。

---

## 技術堆疊

| 層次 | 技術 | 版本 |
|------|------|------|
| RDF 圖形 / SPARQL | rdflib | >= 7.0.0 |
| SHACL 驗證與推理 | pyshacl | >= 0.26.0 |
| MQTT 串流 | paho-mqtt | >= 2.0.0 |
| JSON 綱要驗證 | jsonschema | >= 4.0.0 |
| 時間序列資料庫 | PostgreSQL 16 + TimescaleDB 2.x | — |
| 儀表板 UI | Streamlit | — |
| 資料處理 | pandas、Jupyter Notebook | — |

---

## 執行方式

```bash
# SprayLine_1 — 基礎推理
python SprayLine_1/sprayline_runtime_inference.py

# SprayLine_2 — SPARQL 推理
python SprayLine_2/rdf_native_infer_sparql.py
# SprayLine_2 — SHACL 推理
python SprayLine_2/rdf_native_infer_shacl.py
# MQTT Broker（SprayLine_2）
mosquitto -v -p 1883

# SprayLine_3 — 完整管線（單一入口）
python SprayLine_3/pipeline.py

# Streamlit 儀表板
python UserInterfaceDesign/UI_v2.py
```

---

## 資料庫綱要摘要

- **工站**：Station_1（底漆 Primer）、Station_2（面漆 Topcoat）、Station_3（金漆 Gold Paint）
- **核心資料表**：7 張（`station_config`、`sensor_threshold`、`batch_run`、`sensor_1hz`、`batch_summary`、`pdm_degradation_log`、`alert_event`）
- **超級資料表**（TimescaleDB hypertable）：`sensor_1hz`（1Hz 感測資料）、`alert_event`（告警事件）
- **核心 PdM 指標**：
  - `filter_diff_pressure_bar`：濾網壓差（0.15 bar 正常 → > 0.50 bar 嚴重）
  - `servo_torque_load_pct`：伺服馬達負載（< 60% 正常 → > 80% 異常）
- **檢視**：`v_latest_pdm_status`、`v_latest_batch_per_station`、`v_unacknowledged_alerts`

---

## 程式碼慣例

- **本體論命名空間**：URI 使用 `MIS:` 與 `STH:` 前綴
- **SPARQL 規則命名**：各模組的 `rules/` 資料夾內依 `01_*.rq`、`02_*.rq`… 順序命名
- **JSON→TTL 轉換**：執行期 JSON 資料透過 `json_to_sprayline_ttl.py` 轉為 RDF Turtle（SprayLine_3 模式）
- **服務模式**：服務類別採用請求/回應字典模式，核心入口為 `HandleTimeSeriesQuery()`

---

## CI/CD 說明

目前**無自動化測試或 GitHub Actions**，所有模組均以手動方式執行。GitHub 遠端倉庫：`HoraceYang2019/Project-SprayLine`。
