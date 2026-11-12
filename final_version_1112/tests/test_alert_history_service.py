"""AlertHistoryService 與 /api/alerts/history、summary、episodes 的測試。

前兩組測試不需要資料庫。最後一組在設定環境變數 SPRAYLINE_TEST_PG_DSN 時才執行：
它在暫時 schema 內建立與 setup_db.sql 相同欄位的告警表，測完即刪除，不碰正式資料表。
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
for rel in ("api", "services", "database"):
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("VERSIONB_PATH", str(ROOT / "database"))

import alert_history_adapter  # noqa: E402
from alert_history_service import alert_history_service as svc  # noqa: E402
from api_server import app  # noqa: E402

TPE = ZoneInfo("Asia/Taipei")
UTC = timezone.utc


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        self.conn.executed.append((sql, params))
        self._rows = self.conn.responder(sql, params)

    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self, responder=lambda sql, params: []):
        self.responder = responder
        self.executed = []
        self.readonly = None
        self.closed = False

    def cursor(self, cursor_factory=None):
        return FakeCursor(self)

    def set_session(self, readonly=None, **_):
        self.readonly = readonly

    def rollback(self):
        pass

    def close(self):
        self.closed = True


# ── 1. 參數與時間範圍 ─────────────────────────────────────────────────────────

def test_parse_time_date_only_and_naive_use_requested_timezone():
    start = svc.parse_time("2026-10-01", TPE, end_of_day=False)
    end = svc.parse_time("2026-10-01", TPE, end_of_day=True)
    assert start == datetime(2026, 10, 1, 0, 0, tzinfo=TPE)
    assert end.date() == start.date() and end.hour == 23 and end.minute == 59
    naive = svc.parse_time("2026-10-01T08:30:00", TPE, end_of_day=False)
    assert naive.utcoffset() == timedelta(hours=8)
    zulu = svc.parse_time("2026-10-01T00:30:00Z", TPE, end_of_day=False)
    assert zulu == datetime(2026, 10, 1, 0, 30, tzinfo=UTC)
    with pytest.raises(svc.AlertQueryError):
        svc.parse_time("yesterday", TPE, end_of_day=False)
    with pytest.raises(svc.AlertQueryError):
        svc.parse_time("2026-02-30", TPE, end_of_day=False)


def test_station_state_and_list_normalization():
    assert [svc.normalize_station(v) for v in ["1", "Station 2", "station_3", "Station_1"]] == [
        "Station_1", "Station_2", "Station_3", "Station_1"]
    assert svc.split_values(" a, b ,a,,") == ["a", "b"]
    assert svc.normalize_states(["Warning", "故障"]) == ["warning", "fault"]
    with pytest.raises(svc.AlertQueryError):
        svc.normalize_states(["normal"])


def test_default_range_uses_latest_alert_time_not_system_clock():
    latest = datetime(2026, 6, 30, 18, 0, tzinfo=UTC)
    conn = FakeConn(lambda sql, params: [{"latest_ts": latest}] if "MAX(ts)" in sql else [])
    resolved = svc.resolve_query(conn, svc.AlertQuery(days=3))
    assert resolved.end == latest
    assert resolved.start == latest - timedelta(days=3)
    assert resolved.time_basis["anchor_source"] == "latest_alert_ts"


def test_default_range_without_alert_data_falls_back_to_system_clock():
    now = datetime(2026, 11, 12, 4, 0, tzinfo=UTC)
    conn = FakeConn(lambda sql, params: [{"latest_ts": None}])
    resolved = svc.resolve_query(conn, svc.AlertQuery(), now=now)
    assert resolved.end == now and resolved.start == now - timedelta(days=7)
    assert resolved.time_basis["anchor_source"] == "system_clock_no_alert_data"


def test_range_modes_and_validation():
    now = datetime(2026, 11, 12, 4, 0, tzinfo=UTC)
    conn = FakeConn()
    only_start = svc.resolve_query(conn, svc.AlertQuery(start="2026-11-01"), now=now)
    assert only_start.end == now and only_start.time_basis["mode"] == "start_to_now"
    only_end = svc.resolve_query(conn, svc.AlertQuery(end="2026-10-31", days=10), now=now)
    assert only_end.end - only_end.start == timedelta(days=10)
    assert conn.executed == []  # 有給時間就不查最新告警
    with pytest.raises(svc.AlertQueryError):
        svc.resolve_query(conn, svc.AlertQuery(start="2026-11-02", end="2026-11-01"))
    with pytest.raises(svc.AlertQueryError):
        svc.resolve_query(conn, svc.AlertQuery(start="2025-01-01", end="2026-11-01"))
    with pytest.raises(svc.AlertQueryError):
        svc.resolve_query(conn, svc.AlertQuery(tz="Mars/Base"))


def test_component_filter_maps_to_rule_metrics():
    assert svc.sensors_for_components(["filter_mesh"]) == ["filter_diff_pressure_bar"]
    assert svc.sensors_for_components(["濾網"]) == ["filter_diff_pressure_bar"]
    quality = svc.sensors_for_components(["品質"])  # 中文名稱對到元件後，帶入該元件全部指標
    assert len(quality) == 5 and "quality_score_pct" in quality and "film_thickness_um" in quality
    with pytest.raises(svc.AlertQueryError) as err:
        svc.sensors_for_components(["pump"])
    assert "filter_mesh" in str(err.value)


def test_where_clause_uses_parameters_for_every_filter():
    resolved = svc.resolve_query(FakeConn(), svc.AlertQuery(
        start="2026-10-01", end="2026-10-31", station_id="1,2", cause_id="filter_clog",
        sensor_name="filter_diff_pressure_bar", state="fault", acknowledged=False))
    where, params = svc.build_where(resolved)
    assert where.count("%s") == len(params) == 6
    assert params[2] == ["Station_1", "Station_2"] and params[3] == ["FILTER_CLOG"]
    assert "acknowledged_at IS NULL" in where


# ── 2. 連續異常段 ───────────────────────────────────────────────────────────────

def _row(minute, station="Station_1", sensor="filter_diff_pressure_bar", cause="FILTER_CLOG",
         state="warning", value=0.6, ack=None):
    return {"event_id": str(uuid.uuid4()), "ts": datetime(2026, 10, 14, 6, 0, tzinfo=UTC) + timedelta(minutes=minute),
            "station_id": station, "sensor_name": sensor, "cause": cause, "state": state,
            "measured_value": value, "acknowledged_at": ack}


def test_group_episodes_splits_on_gap_and_key():
    rows = [_row(0), _row(5, value=0.65), _row(10, state="fault", value=0.75),
            _row(40, value=0.62),                       # 間隔 30 分鐘 → 新的一段
            _row(12, station="Station_2", value=0.55)]  # 不同站點 → 另一段
    rows.sort(key=lambda r: r["ts"])
    episodes = svc.group_episodes(rows, timedelta(minutes=15))
    assert len(episodes) == 3
    first = next(e for e in episodes if e["station_id"] == "Station_1" and e["alert_count"] == 3)
    assert first["fault_count"] == 1 and first["max_value"] == 0.75 and first["latest_value"] == 0.75
    assert first["end_ts"] - first["start_ts"] == timedelta(minutes=10)


def test_list_episodes_reports_handling_status():
    ack = datetime(2026, 10, 14, 6, 20, tzinfo=UTC)
    rows = [_row(0, ack=ack), _row(5), _row(100, ack=ack)]

    def responder(sql, params):
        if "FROM   alert_event ae" in sql:
            return list(reversed(rows))  # SQL 依時間由新到舊
        if "cause_catalog" in sql:
            return [{"cause_id": "FILTER_CLOG", "description_zh": "濾網阻塞", "severity": "medium"}]
        return []

    result = svc.list_episodes(FakeConn(responder), svc.AlertQuery(start="2026-10-14", end="2026-10-14"))
    assert result["episode_total"] == 2
    newest, older = result["items"]
    assert newest["handling_status"] == "acknowledged" and newest["alert_count"] == 1
    assert older["handling_status"] == "partially_acknowledged" and older["duration_minutes"] == 5.0
    assert older["component"] == "filter_mesh" and older["cause_description_zh"] == "濾網阻塞"
    assert older["start_ts"].endswith("+08:00")


# ── 3. API 路由 ─────────────────────────────────────────────────────────────────

client = TestClient(app)


def test_history_routes_are_not_captured_by_event_id_route():
    calls = {}

    def fake(filters, **kwargs):
        calls["filters"], calls["kwargs"] = filters, kwargs
        return 200, {"output_type": "alert_history", "items": []}

    with patch("api_server.AlertHistoryList", fake):
        response = client.get("/api/alerts/history", params={"station_id": "1", "state": "fault", "limit": 5})
    assert response.status_code == 200 and response.json()["output_type"] == "alert_history"
    assert calls["filters"]["station_id"] == "1" and calls["kwargs"] == {"limit": 5, "offset": 0}
    routes = {r.path for r in app.routes}
    assert {"/api/alerts/history", "/api/alerts/summary", "/api/alerts/episodes"} <= routes


@pytest.mark.parametrize("path,params", [
    ("/api/alerts/history", {"limit": 0}),
    ("/api/alerts/history", {"days": 0}),
    ("/api/alerts/summary", {"group_by": "weather"}),
    ("/api/alerts/episodes", {"gap_minutes": 0}),
    ("/api/alerts/history", {"anchor": "yesterday"}),
])
def test_invalid_query_parameters_return_422(path, params):
    assert client.get(path, params=params).status_code == 422


def test_service_validation_error_returns_422_and_uses_read_only_connection():
    conn = FakeConn()
    with patch.object(alert_history_adapter, "_open_connection", return_value=(conn, {"db_alert": object()}, {})):
        response = client.get("/api/alerts/history", params={"component": "pump"})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_query"
    assert conn.readonly is True and conn.closed is True


def test_database_unavailable_returns_503():
    with patch.object(alert_history_adapter, "_open_connection", return_value=(None, None, {"error": "no db"})):
        response = client.get("/api/alerts/summary")
    assert response.status_code == 503
    body = response.json()
    assert body["db_available"] is False and body["service_name"] == "AlertHistoryService"


# ── 4. 真實 PostgreSQL（選用） ───────────────────────────────────────────────────

PG_DSN = os.getenv("SPRAYLINE_TEST_PG_DSN")

DDL = """
CREATE TABLE cause_catalog (cause_id VARCHAR(32) PRIMARY KEY, category VARCHAR(32), description_zh TEXT,
                            typical_component VARCHAR(32), severity VARCHAR(8));
CREATE TABLE response_catalog (response_id VARCHAR(32) PRIMARY KEY, description_zh TEXT,
                               downtime_estimate_min INT, skill_required VARCHAR(16));
CREATE TABLE alert_event (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), batch_id VARCHAR(32) NOT NULL,
    station_id VARCHAR(32) NOT NULL, sensor_name VARCHAR(64) NOT NULL, measured_value REAL NOT NULL,
    state VARCHAR(8) NOT NULL CHECK (state IN ('warning','fault')), cause VARCHAR(64),
    ts TIMESTAMPTZ NOT NULL DEFAULT now(), message TEXT, acknowledged_at TIMESTAMPTZ);
CREATE TABLE alert_response_link (
    alert_id UUID NOT NULL REFERENCES alert_event(event_id),
    response_id VARCHAR(32) NOT NULL REFERENCES response_catalog(response_id),
    executed_at TIMESTAMPTZ, operator_id VARCHAR(64), PRIMARY KEY (alert_id, response_id));
"""


@pytest.fixture()
def pg_conn():
    if not PG_DSN:
        pytest.skip("未設定 SPRAYLINE_TEST_PG_DSN")
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(PG_DSN)
    schema = f"alert_history_test_{uuid.uuid4().hex[:8]}"
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA {schema}")
        cur.execute(f"SET search_path TO {schema}")
        cur.execute(DDL)
        cur.execute("INSERT INTO cause_catalog VALUES ('FILTER_CLOG','pdm_core','濾網阻塞','filter','medium'),"
                    "('NOZZLE_CLOG','quality_fluid','噴嘴堵塞','nozzle','high')")
        cur.execute("INSERT INTO response_catalog VALUES ('REPLACE_FILTER','更換濾網',30,'operator'),"
                    "('BACKWASH_FILTER','反洗濾網管路',20,'technician')")
        base = datetime(2026, 10, 14, 6, 0, tzinfo=UTC)
        alerts = [  # (分鐘, 站點, 指標, 原因, 狀態, 數值, 是否確認)
            (0, "Station_1", "filter_diff_pressure_bar", "FILTER_CLOG", "warning", 0.62, False),
            (6, "Station_1", "filter_diff_pressure_bar", "FILTER_CLOG", "fault", 0.74, True),
            (12, "Station_1", "filter_diff_pressure_bar", "FILTER_CLOG", "fault", 0.78, False),
            (60 * 24, "Station_2", "paint_flow_ml_min", "NOZZLE_CLOG", "warning", 41.0, False),
            (60 * 24 * 40, "Station_3", "temperature_c", None, "warning", 29.0, False),
        ]
        for minute, station, sensor, cause, state, value, acked in alerts:
            ts = base + timedelta(minutes=minute)
            cur.execute(
                "INSERT INTO alert_event (batch_id, station_id, sensor_name, measured_value, state, cause, ts, "
                "acknowledged_at) VALUES ('B1', %s, %s, %s, %s, %s, %s, %s) RETURNING event_id",
                (station, sensor, value, state, cause, ts, ts + timedelta(minutes=2) if acked else None))
            event_id = cur.fetchone()[0]
            if cause == "FILTER_CLOG":
                cur.execute("INSERT INTO alert_response_link (alert_id, response_id, executed_at) VALUES "
                            "(%s, 'REPLACE_FILTER', %s), (%s, 'BACKWASH_FILTER', NULL)",
                            (event_id, ts + timedelta(minutes=30) if acked else None, event_id))
    conn.commit()
    conn.set_session(readonly=True)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}")
    try:
        yield conn
    finally:
        conn.rollback()
        conn.set_session(readonly=False)
        with conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {schema} CASCADE")
        conn.commit()
        conn.close()


def test_postgres_history_summary_and_episodes(pg_conn):
    october = svc.AlertQuery(start="2026-10-01", end="2026-10-31")
    history = svc.list_alerts(pg_conn, october, limit=2)
    assert history["total"] == 4 and history["count"] == 2 and history["has_more"] is True
    newest = history["items"][0]
    assert newest["station_id"] == "Station_2" and newest["cause_description_zh"] == "噴嘴堵塞"
    filter_alert = svc.list_alerts(pg_conn, svc.AlertQuery(start="2026-10-14", end="2026-10-14", state="fault",
                                                           component="濾網", acknowledged=True))
    assert filter_alert["total"] == 1
    item = filter_alert["items"][0]
    assert item["acknowledged"] is True and item["response_executed"] is True
    assert {r["response_id"] for r in item["responses"]} == {"REPLACE_FILTER", "BACKWASH_FILTER"}

    by_cause = svc.summarize_alerts(pg_conn, october, group_by="cause")
    assert [(g["key"], g["total"]) for g in by_cause["groups"]] == [("FILTER_CLOG", 3), ("NOZZLE_CLOG", 1)]
    assert by_cause["groups"][0]["fault_count"] == 2 and by_cause["groups"][0]["label_zh"] == "濾網阻塞"
    by_day = svc.summarize_alerts(pg_conn, october, group_by="day")
    assert [g["key"] for g in by_day["groups"]] == ["2026-10-14", "2026-10-15"]

    default_window = svc.summarize_alerts(pg_conn, svc.AlertQuery(days=1), group_by="cause")
    assert default_window["time_range"]["basis"]["anchor_source"] == "latest_alert_ts"
    assert [g["key"] for g in default_window["groups"]] == ["UNKNOWN"]  # 只剩 11/23 那筆未對應原因

    episodes = svc.list_episodes(pg_conn, october, gap_minutes=15)
    assert episodes["episode_total"] == 2
    filter_episode = next(e for e in episodes["items"] if e["cause_id"] == "FILTER_CLOG")
    assert filter_episode["alert_count"] == 3 and filter_episode["duration_minutes"] == 12.0
    assert filter_episode["worst_state"] == "fault" and filter_episode["handling_status"] == "partially_acknowledged"
