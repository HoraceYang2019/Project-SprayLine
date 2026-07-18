"""Apply non-destructive SprayLine backend migrations exactly once.

This runner is executed by docker-compose before the API starts. It never runs
setup_db.sql because that setup file intentionally drops and recreates tables.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import psycopg2


DATABASE_DIR = Path(__file__).resolve().parent
MIGRATIONS = (
    DATABASE_DIR / "patch_service_metrics_writeback.sql",
    DATABASE_DIR / "migrate_0718_v3_backend.sql",
)
LOCK_NAME = "sprayline_backend_schema_migrations"


def _connection_config() -> dict[str, object]:
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
        "dbname": os.getenv("DB_NAME", "sprayline"),
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_migrations() -> list[dict[str, str]]:
    """Apply pending migrations and return one status record per file."""
    missing = [str(path) for path in MIGRATIONS if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing migration file(s): {', '.join(missing)}")

    results: list[dict[str, str]] = []
    conn = psycopg2.connect(**_connection_config())
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (LOCK_NAME,))
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migration (
                    migration_name TEXT PRIMARY KEY,
                    sha256_hex CHAR(64) NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            for path in MIGRATIONS:
                checksum = _sha256(path)
                cur.execute(
                    "SELECT sha256_hex FROM schema_migration WHERE migration_name = %s",
                    (path.name,),
                )
                row = cur.fetchone()
                if row:
                    recorded_checksum = str(row[0]).strip()
                    if recorded_checksum != checksum:
                        raise RuntimeError(
                            f"Migration checksum changed after apply: {path.name}"
                        )
                    results.append({"migration": path.name, "status": "already_applied"})
                    continue

                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    """
                    INSERT INTO schema_migration (migration_name, sha256_hex)
                    VALUES (%s, %s)
                    """,
                    (path.name, checksum),
                )
                results.append({"migration": path.name, "status": "applied"})

        conn.commit()
        return results
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    print("[migration] target:", _connection_config()["dbname"])
    for result in apply_migrations():
        print(f"[migration] {result['status']}: {result['migration']}")


if __name__ == "__main__":
    main()
