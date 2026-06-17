"""
SprayLine DB — 連線工具與內部查詢輔助函式
對應 Schema v5.1、PostgreSQL 16

此模組供其他 db_*.py 模組 import，不應由應用程式直接使用。
"""

from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# ── 連線設定 ──────────────────────────────────────────────────────────────────

DB_CONFIG: dict[str, Any] = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname":   os.getenv("DB_NAME",     "sprayline"),
}


def get_connection(**overrides) -> psycopg2.extensions.connection:
    """建立資料庫連線並回傳 connection 物件。

    使用方式
    --------
    conn = get_connection()
    conn = get_connection(host="192.168.1.10", password="secret")
    """
    cfg = {**DB_CONFIG, **overrides}
    conn = psycopg2.connect(**cfg)
    conn.autocommit = False
    return conn


def _fetch(conn, sql: str, params=()) -> list[dict]:
    """內部工具：執行 SELECT 並回傳 list[dict]。"""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def _fetchone(conn, sql: str, params=()) -> dict | None:
    """內部工具：執行 SELECT 並回傳第一筆 dict 或 None。"""
    rows = _fetch(conn, sql, params)
    return rows[0] if rows else None
