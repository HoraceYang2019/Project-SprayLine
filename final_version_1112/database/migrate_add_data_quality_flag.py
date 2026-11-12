"""Migrate sensor data quality flags to the v5.1 contract.

Adds ``data_quality_flag`` to ``sensor_1min`` and ``sensor_3min`` when
missing, normalizes legacy values, and enforces:

- normal
- interpolated
"""

from __future__ import annotations

import os
import sys

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("[error] Missing psycopg2. Install with: pip install psycopg2-binary")
    sys.exit(1)


DB_CONFIG: dict = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname": os.getenv("DB_NAME", "sprayline"),
}


MIGRATION_STEPS: list[dict] = [
    {
        "table": "sensor_1min",
        "sql": """
            ALTER TABLE sensor_1min
            ADD COLUMN IF NOT EXISTS data_quality_flag VARCHAR(20)
                NOT NULL DEFAULT 'normal';

            UPDATE sensor_1min
            SET data_quality_flag = CASE
                WHEN data_quality_flag IN ('normal', 'interpolated')
                    THEN data_quality_flag
                WHEN data_quality_flag = '空值'
                    THEN 'interpolated'
                ELSE 'normal'
            END;

            ALTER TABLE sensor_1min
            DROP CONSTRAINT IF EXISTS sensor_1min_data_quality_flag_check;

            ALTER TABLE sensor_1min
            ADD CONSTRAINT sensor_1min_data_quality_flag_check
                CHECK (data_quality_flag IN ('normal', 'interpolated'));
        """,
    },
    {
        "table": "sensor_3min",
        "sql": """
            ALTER TABLE sensor_3min
            ADD COLUMN IF NOT EXISTS data_quality_flag VARCHAR(20)
                NOT NULL DEFAULT 'normal';

            UPDATE sensor_3min
            SET data_quality_flag = CASE
                WHEN data_quality_flag IN ('normal', 'interpolated')
                    THEN data_quality_flag
                WHEN data_quality_flag = '空值'
                    THEN 'interpolated'
                ELSE 'normal'
            END;

            ALTER TABLE sensor_3min
            DROP CONSTRAINT IF EXISTS sensor_3min_data_quality_flag_check;

            ALTER TABLE sensor_3min
            ADD CONSTRAINT sensor_3min_data_quality_flag_check
                CHECK (data_quality_flag IN ('normal', 'interpolated'));
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


def run_migration() -> None:
    print("=" * 55)
    print("Migration: data_quality_flag v5.1")
    print("=" * 55)
    print(f"Target: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}\n")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as exc:
        print(f"[error] Could not connect to database: {exc}")
        sys.exit(1)

    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            for step in MIGRATION_STEPS:
                table = step["table"]
                print(f"[run] ALTER TABLE {table} ...")
                cur.execute(step["sql"])
                print(f"[ok]  {table}.data_quality_flag migrated")

        conn.commit()
        print("\n[ok] Migration committed\n")

    except Exception as exc:
        conn.rollback()
        conn.close()
        print(f"\n[error] Migration failed and was rolled back: {exc}")
        sys.exit(1)

    print("Verification")
    print("-" * 75)

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(VERIFY_SQL)
        rows = cur.fetchall()

    if not rows:
        print("[warn] No data_quality_flag columns found.")
    else:
        for row in rows:
            print(
                f"{row['table_name']}.{row['column_name']} "
                f"{row['data_type']}({row['character_maximum_length']}) "
                f"nullable={row['is_nullable']} default={row['column_default']}"
            )

    print("\nAllowed values: normal, interpolated")
    conn.close()


if __name__ == "__main__":
    run_migration()
