"""
Migration：新增 data_quality_flag 欄位
目標資料表：sensor_1min、sensor_3min
Schema 版本：v5 → v5.1

使用方式
--------
python migrate_add_data_quality_flag.py

支援環境變數覆蓋連線設定：
    DB_HOST=... DB_PORT=... DB_USER=... DB_PASSWORD=... DB_NAME=... \
    python migrate_add_data_quality_flag.py

說明
----
data_quality_flag 欄位記錄每筆感測資料經 DataPreprocess 處理後的品質狀態：
    '正常'  —— 原始值通過所有品質檢查
    '空值'  —— 原始值為 NULL，已進行線性插值補值
    '突波'  —— IQR 離群值偵測命中，已套用 5 秒滑動平均平滑

使用 ADD COLUMN IF NOT EXISTS，若欄位已存在則跳過，可安全重複執行（冪等）。
"""

from __future__ import annotations

import os
import sys

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("[錯誤] 缺少 psycopg2，請先執行：")
    print("       pip install psycopg2-binary")
    sys.exit(1)

# ── 連線設定 ──────────────────────────────────────────────────────────────────

DB_CONFIG: dict = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname":   os.getenv("DB_NAME",     "sprayline"),
}

# ── Migration SQL ─────────────────────────────────────────────────────────────

MIGRATION_STEPS: list[dict] = [
    {
        "table": "sensor_1min",
        "sql": """
            ALTER TABLE sensor_1min
            ADD COLUMN IF NOT EXISTS data_quality_flag VARCHAR(20)
                NOT NULL DEFAULT '正常'
                CHECK (data_quality_flag IN ('正常', '空值', '突波'));
        """,
    },
    {
        "table": "sensor_3min",
        "sql": """
            ALTER TABLE sensor_3min
            ADD COLUMN IF NOT EXISTS data_quality_flag VARCHAR(20)
                NOT NULL DEFAULT '正常'
                CHECK (data_quality_flag IN ('正常', '空值', '突波'));
        """,
    },
]

VERIFY_SQL = """
    SELECT table_name,
           column_name,
           data_type,
           character_maximum_length,
           column_default,
           is_nullable
    FROM   information_schema.columns
    WHERE  table_schema = 'public'
      AND  table_name   IN ('sensor_1min', 'sensor_3min')
      AND  column_name  = 'data_quality_flag'
    ORDER  BY table_name;
"""

# ── 執行邏輯 ──────────────────────────────────────────────────────────────────

def run_migration() -> None:
    print("=" * 55)
    print(" Migration：新增 data_quality_flag")
    print("=" * 55)
    print(f"目標：{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}\n")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as e:
        print(f"[錯誤] 無法連線至資料庫：{e}")
        sys.exit(1)

    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            for step in MIGRATION_STEPS:
                table = step["table"]
                print(f"[執行] ALTER TABLE {table} ...")
                cur.execute(step["sql"])
                print(f"[OK]   {table}.data_quality_flag 已處理（ADD COLUMN IF NOT EXISTS）")

        conn.commit()
        print("\n[完成] 所有 migration 已成功提交。\n")

    except Exception as exc:
        conn.rollback()
        print(f"\n[錯誤] Migration 失敗，已回滾：{exc}")
        conn.close()
        sys.exit(1)

    # ── 驗證結果 ──────────────────────────────────────────────────────────────
    print("── 驗證結果 ───────────────────────────────────────────")
    print(f"{'資料表':<16} {'欄位':<22} {'型別':<14} {'NOT NULL':<10} {'預設值'}")
    print("-" * 75)

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(VERIFY_SQL)
        rows = cur.fetchall()

    if not rows:
        print("[警告] 查不到欄位，請手動確認資料庫狀態。")
    else:
        for r in rows:
            not_null = "YES" if r["is_nullable"] == "NO" else "NO"
            default  = (r["column_default"] or "")[:30]
            print(
                f"  {r['table_name']:<14} "
                f"{r['column_name']:<22} "
                f"VARCHAR({r['character_maximum_length']}){'':<4} "
                f"{not_null:<10} "
                f"{default}"
            )

    print("-" * 75)
    print("\n欄位說明：")
    print("  '正常' — 原始值通過品質檢查（DEFAULT）")
    print("  '空值' — 原始 NULL，已線性插值補值")
    print("  '突波' — IQR 離群值偵測命中，已滑動平均平滑")
    print("\n寫入範例（DataPreprocess 服務呼叫）：")
    print("  INSERT INTO sensor_1min (..., data_quality_flag)")
    print("  VALUES (..., '突波');")
    print()

    conn.close()


if __name__ == "__main__":
    run_migration()
