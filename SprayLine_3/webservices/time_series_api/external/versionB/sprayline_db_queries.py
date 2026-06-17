"""
SprayLine Database Query & Write Functions
對應 Schema v5.1（setup_db.sql）、PostgreSQL 16

本檔案為統一入口（re-export entry point）。
各功能模組已拆分至獨立 db_*.py 檔案，此檔案全部重新匯出，
確保現有呼叫端無需修改 import 路徑。

使用方式（維持不變）
--------
from sprayline_db_queries import get_connection, get_latest_batches, insert_batch_run, ...

conn = get_connection()          # 預設讀 DB_* 環境變數
rows = get_latest_batches(conn)
conn.close()

模組結構
--------
db_connection.py  → 連線工具（get_connection, _fetch, _fetchone）
db_batch.py       → 批次管理（batch_run）
db_sensor.py      → 感測資料（sensor_1min / sensor_3min）
db_status.py      → 站點狀態快照（batch_station_status）
db_alert.py       → 告警事件（alert_event + M:N 關聯 + UI 串聯函式）
db_knowledge.py   → 門檻值 + 知識庫（cause / response / component / issue / solution）
db_composite.py   → 複合查詢（跨表聚合）

函式命名規則
-----------
get_*        → SELECT，回傳 list[dict] 或 dict | None
insert_*     → INSERT，不自動 commit，回傳 None 或新產生的 PK 字串
update_*     → UPDATE，不自動 commit，回傳 None
upsert_*     → INSERT … ON CONFLICT DO UPDATE，不自動 commit，回傳 None
link_*       → 關聯表 INSERT（M:N junction），不自動 commit，回傳 None
acknowledge_* → UPDATE acknowledged_at，不自動 commit，回傳 None

所有寫入函式均不自動 commit，由呼叫端在適當時機執行 conn.commit()。
"""

# ── 連線工具 ──────────────────────────────────────────────────────────────────
from db_connection import (
    DB_CONFIG,
    get_connection,
    _fetch,
    _fetchone,
)

# ── 批次管理 ──────────────────────────────────────────────────────────────────
from db_batch import (
    get_latest_batches,
    get_batch_by_id,
    get_running_batches,
    get_batches_by_date_range,
    get_latest_completed_batch,
    insert_batch_run,
    update_batch_status,
)

# ── 感測資料 ──────────────────────────────────────────────────────────────────
from db_sensor import (
    get_latest_sensor_1min,
    get_sensor_1min_series,
    get_pdm_trend,
    get_batch_sensor_aggregates,
    get_latest_sensor_3min,
    get_sensor_3min_series,
    insert_sensor_readings_batch,
)

# ── 站點狀態快照 ──────────────────────────────────────────────────────────────
from db_status import (
    get_batch_station_status,
    get_latest_station_status,
    upsert_batch_station_status,
)

# ── 告警事件 ──────────────────────────────────────────────────────────────────
from db_alert import (
    get_unacknowledged_alerts,
    get_alert_history,
    get_alerts_by_filters,
    get_alert_detail,
    get_alert_causes,
    get_alert_responses,
    get_responses_for_cause,
    get_alert_ui_card,
    insert_alert_event,
    link_alert_cause,
    link_alert_response,
    acknowledge_alert,
    acknowledge_alerts_batch,
)

# ── 門檻值 + 知識庫 ───────────────────────────────────────────────────────────
from db_knowledge import (
    get_sensor_thresholds,
    get_single_threshold,
    get_solutions_for_issue,
    get_issues_for_component,
    get_cause_info,
    get_response_info,
    get_all_components,
)

# ── 複合查詢 ──────────────────────────────────────────────────────────────────
from db_composite import (
    get_station_dashboard_snapshot,
    diagnose_component,
)


# ══════════════════════════════════════════════════════════════════════════════
# 快速測試（python sprayline_db_queries.py）
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json

    print("SprayLine DB Query — 連線測試")
    print(f"目標：{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}\n")

    try:
        conn = get_connection()
    except Exception as e:
        print(f"[錯誤] 無法連線：{e}")
        raise SystemExit(1)

    tests = [
        # ── 讀取函式 ──
        ("最近 3 批次",             lambda: get_latest_batches(conn, 3)),
        ("進行中批次",               lambda: get_running_batches(conn)),
        ("最新已完成批次",           lambda: get_latest_completed_batch(conn)),
        ("Station_1 最新感測",       lambda: get_latest_sensor_1min(conn, "Station_1")),
        ("Station_1 環境感測",       lambda: get_latest_sensor_3min(conn, "Station_1")),
        ("Station_1 批次聚合統計",   lambda: get_batch_sensor_aggregates(
                                         conn, "B_20260602_001", "Station_1")),
        ("未確認告警（前5）",        lambda: get_unacknowledged_alerts(conn, limit=5)),
        ("複合條件：fault 告警",     lambda: get_alerts_by_filters(
                                         conn, state="fault", acknowledged=False, days=30)),
        ("濾網 fault 門檻值",        lambda: get_single_threshold(
                                         conn, "filter_diff_pressure_bar", "fault")),
        ("濾網堵塞解方（新函式）",   lambda: get_responses_for_cause(conn, "FILTER_CLOG")),
        ("元件清單",                 lambda: get_all_components(conn)),
    ]

    for label, fn in tests:
        print(f"── {label} ─────────────────────────────")
        result = fn()
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
        print()

    conn.close()
    print("測試完成。")
