"""Check Database/versionB connection for 少榆0616ver_4.

Usage:
    python scripts/check_db_connection.py

This script is read-only. It verifies:
- adapter can locate Database/versionB
- DB_* environment variables are visible
- PostgreSQL connection can be opened
- important tables/functions are available
"""

from __future__ import annotations

from pathlib import Path
import os
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from webservices.integration_adapter.database_versionb_adapter import (  # noqa: E402
    get_adapter_status,
    get_connection,
    import_database_module,
)


def _masked_env() -> dict[str, str]:
    keys = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME", "SPRAYLINE_PROJECT_ROOT", "SPRAYLINE_DB_FUNCTION_PATH"]
    out = {}
    for key in keys:
        value = os.getenv(key, "")
        out[key] = "***" if key == "DB_PASSWORD" and value else value
    return out


def main() -> int:
    print("=== 少榆0616ver_4 DB connection check ===")
    print("Env:", _masked_env())
    print("Adapter:", get_adapter_status())

    conn = None
    try:
        conn = get_connection()
        print("[OK] PostgreSQL connection opened")

        db_batch = import_database_module("db_batch")
        db_alert = import_database_module("db_alert")
        db_future = import_database_module("db_future")
        db_status = import_database_module("db_status")

        checks = {
            "latest_batches": lambda: db_batch.get_latest_batches(conn, limit=3),
            "unack_alerts": lambda: db_alert.get_unacknowledged_alerts(conn, limit=3),
            "future_summary": lambda: db_future.get_future_prediction_summary(conn),
            "station_status_Station_1_demo": lambda: db_status.get_latest_station_status(conn, "Station_1"),
        }
        for name, fn in checks.items():
            try:
                result = fn()
                print(f"[OK] {name}: {result}")
            except Exception as exc:
                print(f"[WARN] {name}: {type(exc).__name__}: {exc}")
        return 0
    except Exception as exc:
        print(f"[ERROR] DB check failed: {type(exc).__name__}: {exc}")
        return 1
    finally:
        if conn is not None:
            conn.close()
            print("[OK] connection closed")


if __name__ == "__main__":
    raise SystemExit(main())
