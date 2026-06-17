"""
SprayLine 資料庫一鍵建立腳本
用途: 建立 sprayline 資料庫、所有資料表、索引，並寫入種子資料
用法: python setup_db.py
      DB_HOST=... DB_PASSWORD=... python setup_db.py
"""

import os
import sys
import pathlib

# ── 安裝確認 ────────────────────────────────────────────────
try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("[錯誤] 缺少 psycopg2，請先執行：")
    print("       pip install psycopg2-binary")
    sys.exit(1)

# ── 連線設定（優先讀取環境變數，其次使用預設值）───────────
CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname":   "postgres",           # 先連 postgres 管理庫
}
TARGET_DB = os.getenv("DB_NAME", "sprayline")
SQL_FILE  = pathlib.Path(__file__).parent / "setup_db.sql"


def connect(dbname: str) -> psycopg2.extensions.connection:
    return psycopg2.connect(**{**CONFIG, "dbname": dbname})


def create_database():
    """若 sprayline 資料庫不存在則建立"""
    conn = connect("postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TARGET_DB,))
    if cur.fetchone():
        print(f"[跳過] 資料庫 '{TARGET_DB}' 已存在")
    else:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TARGET_DB)))
        print(f"[建立] 資料庫 '{TARGET_DB}' 建立成功")
    cur.close()
    conn.close()


def run_sql_file():
    """執行 setup_db.sql（建表 + 種子資料）"""
    if not SQL_FILE.exists():
        print(f"[錯誤] 找不到 SQL 檔案：{SQL_FILE}")
        sys.exit(1)

    ddl = SQL_FILE.read_text(encoding="utf-8")
    conn = connect(TARGET_DB)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("[執行] 正在建立資料表與索引...")
        cur.execute(ddl)
        conn.commit()
        print("[完成] 所有資料表建立成功")
    except Exception as exc:
        conn.rollback()
        print(f"[錯誤] SQL 執行失敗：{exc}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


def verify():
    """列出已建立的資料表與筆數"""
    conn = connect(TARGET_DB)
    cur = conn.cursor()

    tables = [
        "batch_run", "sensor_1min", "sensor_3min", "sensor_threshold",
        "batch_station_status", "alert_event",
        "alert_cause_link", "alert_response_link",
        "future_prediction_result",
        "cause_catalog", "response_catalog",
        "cause_response_map",
        "component_catalog", "issue_catalog",
        "solution_catalog", "component_issue_solution_map",
    ]

    print("\n── 建立結果驗證 ──────────────────────────────────────")
    print(f"{'資料表':<35} {'筆數':>6}")
    print("-" * 43)
    for tbl in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            count = cur.fetchone()[0]
            print(f"  {tbl:<33} {count:>6,}")
        except Exception:
            print(f"  {tbl:<33} {'[錯誤]':>6}")

    cur.close()
    conn.close()
    print("-" * 43)
    print(f"\n資料庫位址: {CONFIG['host']}:{CONFIG['port']}/{TARGET_DB}")
    print("下一步: 請接 DataPreprocess 或少榆 Monitoring/Future 流程。\n")


if __name__ == "__main__":
    print("=" * 50)
    print(" SprayLine 資料庫一鍵建立")
    print("=" * 50)
    print(f"目標: {CONFIG['host']}:{CONFIG['port']}/{TARGET_DB}")
    print(f"SQL : {SQL_FILE}\n")

    create_database()
    run_sql_file()
    verify()
