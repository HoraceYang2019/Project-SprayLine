"""AlertHistoryService：依時間範圍與問題類型查詢告警歷程。

只讀取 alert_event、alert_response_link、cause_catalog、response_catalog，不寫入資料庫。

時間基準
--------
alert_event.ts 是感測資料列的時間（MonitoringWorker 以資料列的 ts 寫入告警），
不是寫入資料庫的時間。因此未指定時間範圍時，預設以資料庫中最新一筆告警時間
（anchor = latest_data）往回計算，避免歷史或模擬資料以系統時鐘查詢時落空。

三種查詢
--------
list_alerts      ：逐筆列出告警，附原因說明與建議處置，可分頁。
summarize_alerts ：依原因、站點、指標、嚴重度或日期分組計數。
list_episodes    ：把同站點、同指標、同原因且間隔不超過 gap_minutes 的告警
                   合併成一段異常，回報開始、最後一次告警、持續時間與確認情況。
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RULE_TTL_PATH = PROJECT_ROOT / "ontology" / "sprayline_threshold.ttl"

DEFAULT_TZ = "Asia/Taipei"
DEFAULT_DAYS = 7
MAX_DAYS = 366
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000
DEFAULT_GAP_MINUTES = 15
MAX_GAP_MINUTES = 1440
MAX_EPISODE_ROWS = 20000
ANCHORS = ("latest_data", "now")
GROUP_BY_OPTIONS = ("cause", "station", "sensor", "state", "day")
UNKNOWN_CAUSE = "UNKNOWN"

_STATE_ALIASES = {"warning": "warning", "warn": "warning", "警告": "warning",
                  "fault": "fault", "故障": "fault"}
_STATE_ZH = {"warning": "警告", "fault": "故障"}
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_STATION_NUMBER = re.compile(r"^(?:station)?[\s_-]*(\d+)$", re.IGNORECASE)

EPISODE_NOTES = [
    "end_ts 是該段最後一次告警的時間，不代表已確認恢復正常。",
    "MonitoringWorker 對尚未確認的同一異常，5 分鐘內不重複寫入告警，因此同一段異常的告警間隔可能大於 1 分鐘。",
]


class AlertQueryError(ValueError):
    """查詢參數不正確；API 層轉為 HTTP 422。"""


@dataclass
class AlertQuery:
    """API 傳入的原始查詢條件（字串或清單），由 resolve_query() 驗證與正規化。"""

    start: str | None = None
    end: str | None = None
    days: int | None = None
    anchor: str = "latest_data"
    tz: str = DEFAULT_TZ
    station_id: str | Iterable[str] | None = None
    cause_id: str | Iterable[str] | None = None
    sensor_name: str | Iterable[str] | None = None
    component: str | Iterable[str] | None = None
    state: str | Iterable[str] | None = None
    acknowledged: bool | None = None


@dataclass
class ResolvedQuery:
    start: datetime
    end: datetime
    tz_name: str
    tzinfo: ZoneInfo
    time_basis: dict[str, Any]
    stations: list[str] = field(default_factory=list)
    causes: list[str] = field(default_factory=list)
    sensors: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    component_sensors: list[str] | None = None
    states: list[str] = field(default_factory=list)
    acknowledged: bool | None = None

    def echo(self) -> dict[str, Any]:
        return {
            "station_id": self.stations or None,
            "cause_id": self.causes or None,
            "sensor_name": self.sensors or None,
            "component": self.components or None,
            "component_sensors": self.component_sensors,
            "state": self.states or None,
            "acknowledged": self.acknowledged,
        }


# ── 資料庫讀取（只讀） ─────────────────────────────────────────────────────────

def _fetch(conn, sql: str, params: Iterable[Any] = ()) -> list[dict]:
    import psycopg2.extras

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]


def _fetchone(conn, sql: str, params: Iterable[Any] = ()) -> dict | None:
    rows = _fetch(conn, sql, params)
    return rows[0] if rows else None


# ── 規則對應：指標 → 元件 ──────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def metric_components() -> dict[str, dict[str, Any]]:
    """由 Runtime 門檻 TTL 取得每個指標的元件、中文名稱與單位；讀取失敗時回傳空 dict。"""
    try:
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from ontology.rule_inference import load_rules

        rules = load_rules(RULE_TTL_PATH)
    except Exception:
        return {}
    return {
        metric: {"component": rule.component, "component_zh": rule.component_zh, "unit": rule.unit}
        for metric, rule in rules.items()
    }


def sensors_for_components(components: list[str]) -> list[str]:
    """元件鍵（如 filter_mesh）或任一中文名稱（如 濾網、品質）→ 該元件下的所有指標。"""
    mapping = metric_components()
    wanted = {c.lower() for c in components}
    keys = {
        (info.get("component") or "").lower()
        for info in mapping.values()
        if (info.get("component") or "").lower() in wanted or (info.get("component_zh") or "") in components
    } - {""}
    sensors = sorted(metric for metric, info in mapping.items() if (info.get("component") or "").lower() in keys)
    if not sensors:
        labels: dict[str, list[str]] = {}
        for info in mapping.values():
            if info.get("component"):
                zh = labels.setdefault(info["component"], [])
                if info.get("component_zh") and info["component_zh"] not in zh:
                    zh.append(info["component_zh"])
        valid = [f"{key}（{'、'.join(zh)}）" for key, zh in sorted(labels.items())]
        raise AlertQueryError(f"找不到元件 {components}；可用的元件為：{'；'.join(valid) or '規則檔未載入'}")
    return sensors


# ── 參數正規化 ──────────────────────────────────────────────────────────────────

def split_values(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    items = value.split(",") if isinstance(value, str) else list(value)
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def normalize_station(value: str) -> str:
    match = _STATION_NUMBER.match(value.strip())
    return f"Station_{int(match.group(1))}" if match else value.strip()


def normalize_states(values: list[str]) -> list[str]:
    states: list[str] = []
    for value in values:
        state = _STATE_ALIASES.get(value.lower(), _STATE_ALIASES.get(value))
        if state is None:
            raise AlertQueryError(f"state 只接受 warning、fault（或警告、故障），收到：{value}")
        if state not in states:
            states.append(state)
    return states


def get_tz(name: str | None) -> tuple[str, ZoneInfo]:
    tz_name = (name or DEFAULT_TZ).strip()
    try:
        return tz_name, ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise AlertQueryError(f"無法辨識的時區：{tz_name}；例如 Asia/Taipei 或 UTC") from exc


def parse_time(value: str | datetime | None, tzinfo: ZoneInfo, *, end_of_day: bool) -> datetime | None:
    """解析 YYYY-MM-DD 或 ISO 8601；沒有時區時視為 tzinfo。只有日期的 end 代表當天結束。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=tzinfo)
    text = str(value).strip()
    if not text:
        return None
    if _DATE_ONLY.match(text):
        try:
            day = date.fromisoformat(text)
        except ValueError as exc:
            raise AlertQueryError(f"日期不存在：{text}") from exc
        return datetime.combine(day, time.max if end_of_day else time.min, tzinfo=tzinfo)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AlertQueryError(
            f"時間格式無法解析：{text}；請用 YYYY-MM-DD 或 ISO 8601，例如 2026-10-01T08:00:00+08:00"
        ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=tzinfo)


def resolve_query(conn, query: AlertQuery, *, now: datetime | None = None) -> ResolvedQuery:
    """驗證參數並決定實際查詢時間範圍。

    - start、end 都有：直接使用。
    - 只有 start：查到現在（系統時間）。
    - 只有 end：往前 days 天（預設 7）。
    - 都沒有：以 anchor 為終點往前 days 天；anchor = latest_data 時取資料庫最新告警時間，
      資料庫沒有告警時改用系統時間；anchor = now 時用系統時間。
    """
    tz_name, tzinfo = get_tz(query.tz)
    if query.anchor not in ANCHORS:
        raise AlertQueryError(f"anchor 只接受 {', '.join(ANCHORS)}，收到：{query.anchor}")
    if query.days is not None and not (1 <= int(query.days) <= MAX_DAYS):
        raise AlertQueryError(f"days 必須介於 1 到 {MAX_DAYS}")
    days = int(query.days) if query.days is not None else DEFAULT_DAYS
    current = now or datetime.now(timezone.utc)

    start = parse_time(query.start, tzinfo, end_of_day=False)
    end = parse_time(query.end, tzinfo, end_of_day=True)
    basis: dict[str, Any] = {"mode": None, "anchor": None, "anchor_time": None, "days": None}

    if start is not None and end is not None:
        basis["mode"] = "explicit_range"
    elif start is not None:
        end = current
        basis.update(mode="start_to_now", anchor_time=current)
    elif end is not None:
        start = end - timedelta(days=days)
        basis.update(mode="days_before_end", days=days)
    else:
        if query.anchor == "now":
            end, source = current, "system_clock"
        else:
            row = _fetchone(conn, "SELECT MAX(ts) AS latest_ts FROM alert_event")
            latest = row.get("latest_ts") if row else None
            end, source = (latest, "latest_alert_ts") if latest is not None else (current, "system_clock_no_alert_data")
        start = end - timedelta(days=days)
        basis.update(mode="days_before_anchor", anchor=query.anchor, anchor_source=source, anchor_time=end, days=days)

    if start > end:
        raise AlertQueryError("start 必須早於或等於 end")
    if end - start > timedelta(days=MAX_DAYS, seconds=1):
        raise AlertQueryError(f"時間範圍最多 {MAX_DAYS} 天")

    components = split_values(query.component)
    return ResolvedQuery(
        start=start,
        end=end,
        tz_name=tz_name,
        tzinfo=tzinfo,
        time_basis=basis,
        stations=[normalize_station(s) for s in split_values(query.station_id)],
        causes=[c.upper() for c in split_values(query.cause_id)],
        sensors=split_values(query.sensor_name),
        components=components,
        component_sensors=sensors_for_components(components) if components else None,
        states=normalize_states(split_values(query.state)),
        acknowledged=query.acknowledged,
    )


def build_where(resolved: ResolvedQuery) -> tuple[str, list[Any]]:
    conditions = ["ae.ts >= %s", "ae.ts <= %s"]
    params: list[Any] = [resolved.start, resolved.end]
    if resolved.stations:
        conditions.append("ae.station_id = ANY(%s)")
        params.append(resolved.stations)
    if resolved.causes:
        conditions.append(f"COALESCE(ae.cause, '{UNKNOWN_CAUSE}') = ANY(%s)")
        params.append(resolved.causes)
    if resolved.sensors:
        conditions.append("ae.sensor_name = ANY(%s)")
        params.append(resolved.sensors)
    if resolved.component_sensors is not None:
        conditions.append("ae.sensor_name = ANY(%s)")
        params.append(resolved.component_sensors)
    if resolved.states:
        conditions.append("ae.state = ANY(%s)")
        params.append(resolved.states)
    if resolved.acknowledged is True:
        conditions.append("ae.acknowledged_at IS NOT NULL")
    elif resolved.acknowledged is False:
        conditions.append("ae.acknowledged_at IS NULL")
    return " AND ".join(conditions), params


# ── 輸出整理 ────────────────────────────────────────────────────────────────────

def _iso(value: Any, tzinfo: ZoneInfo) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return aware.astimezone(tzinfo).isoformat()
    return str(value)


def _time_range(resolved: ResolvedQuery) -> dict[str, Any]:
    basis = dict(resolved.time_basis)
    basis["anchor_time"] = _iso(basis.get("anchor_time"), resolved.tzinfo)
    return {
        "start": _iso(resolved.start, resolved.tzinfo),
        "end": _iso(resolved.end, resolved.tzinfo),
        "timezone": resolved.tz_name,
        "basis": basis,
        "time_field": "alert_event.ts（感測資料時間）",
    }


def _component_fields(sensor_name: str | None) -> dict[str, Any]:
    info = metric_components().get(sensor_name or "", {})
    return {"component": info.get("component"), "component_zh": info.get("component_zh"), "unit": info.get("unit")}


def _cause_labels(conn, cause_ids: Iterable[str]) -> dict[str, dict[str, Any]]:
    ids = sorted({c for c in cause_ids if c and c != UNKNOWN_CAUSE})
    if not ids:
        return {}
    rows = _fetch(conn, "SELECT cause_id, description_zh, severity FROM cause_catalog WHERE cause_id = ANY(%s)", [ids])
    return {row["cause_id"]: row for row in rows}


def _responses_for(conn, event_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not event_ids:
        return {}
    rows = _fetch(
        conn,
        """
        SELECT arl.alert_id::text AS alert_id, arl.response_id, arl.executed_at, arl.operator_id,
               rc.description_zh
        FROM   alert_response_link arl
        LEFT   JOIN response_catalog rc ON rc.response_id = arl.response_id
        WHERE  arl.alert_id = ANY(%s::uuid[])
        ORDER  BY arl.alert_id, arl.response_id
        """,
        [event_ids],
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["alert_id"], []).append(row)
    return grouped


def _float(value: Any) -> float | None:
    return None if value is None else float(value)


# ── 查詢 1：逐筆告警 ────────────────────────────────────────────────────────────

def list_alerts(conn, query: AlertQuery, *, limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict[str, Any]:
    if not (1 <= limit <= MAX_LIMIT):
        raise AlertQueryError(f"limit 必須介於 1 到 {MAX_LIMIT}")
    if offset < 0:
        raise AlertQueryError("offset 不可小於 0")
    resolved = resolve_query(conn, query)
    where, params = build_where(resolved)

    total = int((_fetchone(conn, f"SELECT COUNT(*) AS n FROM alert_event ae WHERE {where}", params) or {}).get("n") or 0)
    rows = _fetch(
        conn,
        f"""
        SELECT ae.event_id::text AS event_id, ae.ts, ae.station_id, ae.batch_id, ae.sensor_name,
               ae.measured_value, ae.state, ae.cause, ae.message, ae.acknowledged_at,
               cc.description_zh AS cause_description_zh, cc.severity AS cause_severity
        FROM   alert_event ae
        LEFT   JOIN cause_catalog cc ON cc.cause_id = ae.cause
        WHERE  {where}
        ORDER  BY ae.ts DESC, ae.event_id
        LIMIT  %s OFFSET %s
        """,
        params + [limit, offset],
    )
    responses = _responses_for(conn, [row["event_id"] for row in rows])
    tz = resolved.tzinfo
    items = []
    for row in rows:
        linked = responses.get(row["event_id"], [])
        items.append({
            "event_id": row["event_id"],
            "ts": _iso(row["ts"], tz),
            "station_id": row["station_id"],
            "batch_id": row["batch_id"],
            "sensor_name": row["sensor_name"],
            **_component_fields(row["sensor_name"]),
            "measured_value": _float(row["measured_value"]),
            "state": row["state"],
            "state_zh": _STATE_ZH.get(row["state"]),
            "cause_id": row["cause"] or UNKNOWN_CAUSE,
            "cause_description_zh": row.get("cause_description_zh"),
            "cause_severity": row.get("cause_severity"),
            "message": row["message"],
            "acknowledged": row["acknowledged_at"] is not None,
            "acknowledged_at": _iso(row["acknowledged_at"], tz),
            "responses": [
                {"response_id": r["response_id"], "description_zh": r.get("description_zh"),
                 "executed_at": _iso(r.get("executed_at"), tz), "operator_id": r.get("operator_id")}
                for r in linked
            ],
            "response_executed": any(r.get("executed_at") is not None for r in linked),
        })
    return {
        "time_range": _time_range(resolved),
        "filters": resolved.echo(),
        "total": total,
        "count": len(items),
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
        "items": items,
    }


# ── 查詢 2：分組統計 ────────────────────────────────────────────────────────────

def summarize_alerts(conn, query: AlertQuery, *, group_by: str = "cause") -> dict[str, Any]:
    if group_by not in GROUP_BY_OPTIONS:
        raise AlertQueryError(f"group_by 只接受 {', '.join(GROUP_BY_OPTIONS)}，收到：{group_by}")
    resolved = resolve_query(conn, query)
    where, params = build_where(resolved)
    key_params: list[Any] = []
    key_sql = {
        "cause": f"COALESCE(ae.cause, '{UNKNOWN_CAUSE}')",
        "station": "ae.station_id",
        "sensor": "ae.sensor_name",
        "state": "ae.state",
    }.get(group_by)
    if group_by == "day":
        key_sql = "to_char(ae.ts AT TIME ZONE %s, 'YYYY-MM-DD')"
        key_params = [resolved.tz_name]
    rows = _fetch(
        conn,
        f"""
        SELECT {key_sql} AS group_key,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE ae.state = 'warning') AS warning_count,
               COUNT(*) FILTER (WHERE ae.state = 'fault')   AS fault_count,
               COUNT(*) FILTER (WHERE ae.acknowledged_at IS NULL) AS unacknowledged_count,
               MIN(ae.ts) AS first_ts,
               MAX(ae.ts) AS last_ts,
               array_agg(DISTINCT ae.station_id)  AS stations,
               array_agg(DISTINCT ae.sensor_name) AS sensors,
               array_agg(DISTINCT COALESCE(ae.cause, '{UNKNOWN_CAUSE}')) AS causes
        FROM   alert_event ae
        WHERE  {where}
        GROUP  BY 1
        ORDER  BY total DESC, group_key
        """,
        key_params + params,
    )
    causes = _cause_labels(conn, [r["group_key"] for r in rows] if group_by == "cause" else [])
    tz = resolved.tzinfo
    groups = []
    for row in rows:
        key = row["group_key"]
        if group_by == "cause":
            label = (causes.get(key) or {}).get("description_zh") or ("未對應原因" if key == UNKNOWN_CAUSE else None)
        elif group_by == "sensor":
            label = _component_fields(key).get("component_zh")
        elif group_by == "state":
            label = _STATE_ZH.get(key)
        else:
            label = None
        groups.append({
            "key": key,
            "label_zh": label,
            "total": int(row["total"]),
            "warning_count": int(row["warning_count"]),
            "fault_count": int(row["fault_count"]),
            "unacknowledged_count": int(row["unacknowledged_count"]),
            "first_ts": _iso(row["first_ts"], tz),
            "last_ts": _iso(row["last_ts"], tz),
            "stations": sorted(row.get("stations") or []),
            "sensors": sorted(row.get("sensors") or []),
            "causes": sorted(row.get("causes") or []),
        })
    return {
        "time_range": _time_range(resolved),
        "filters": resolved.echo(),
        "group_by": group_by,
        "total": sum(g["total"] for g in groups),
        "group_count": len(groups),
        "groups": groups,
    }


# ── 查詢 3：連續異常段 ──────────────────────────────────────────────────────────

def group_episodes(rows: list[dict[str, Any]], gap: timedelta) -> list[dict[str, Any]]:
    """rows 需依 ts 由舊到新排序；同 (站點, 指標, 原因) 相鄰告警間隔 <= gap 視為同一段。"""
    episodes: list[dict[str, Any]] = []
    open_by_key: dict[tuple, dict[str, Any]] = {}
    for row in rows:
        key = (row["station_id"], row["sensor_name"], row["cause"] or UNKNOWN_CAUSE)
        ts = row["ts"]
        episode = open_by_key.get(key)
        if episode is None or ts - episode["end_ts"] > gap:
            episode = {
                "station_id": key[0], "sensor_name": key[1], "cause_id": key[2],
                "start_ts": ts, "end_ts": ts, "alert_count": 0, "warning_count": 0, "fault_count": 0,
                "acknowledged_count": 0, "first_acknowledged_at": None,
                "min_value": None, "max_value": None, "latest_value": None,
                "first_event_id": row["event_id"], "last_event_id": row["event_id"],
            }
            episodes.append(episode)
            open_by_key[key] = episode
        value = _float(row.get("measured_value"))
        episode["end_ts"] = ts
        episode["last_event_id"] = row["event_id"]
        episode["alert_count"] += 1
        episode["warning_count" if row["state"] == "warning" else "fault_count"] += 1
        if value is not None:
            episode["min_value"] = value if episode["min_value"] is None else min(episode["min_value"], value)
            episode["max_value"] = value if episode["max_value"] is None else max(episode["max_value"], value)
            episode["latest_value"] = value
        ack = row.get("acknowledged_at")
        if ack is not None:
            episode["acknowledged_count"] += 1
            if episode["first_acknowledged_at"] is None or ack < episode["first_acknowledged_at"]:
                episode["first_acknowledged_at"] = ack
    return episodes


def list_episodes(conn, query: AlertQuery, *, gap_minutes: int = DEFAULT_GAP_MINUTES,
                  limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    if not (1 <= gap_minutes <= MAX_GAP_MINUTES):
        raise AlertQueryError(f"gap_minutes 必須介於 1 到 {MAX_GAP_MINUTES}")
    if not (1 <= limit <= MAX_LIMIT):
        raise AlertQueryError(f"limit 必須介於 1 到 {MAX_LIMIT}")
    resolved = resolve_query(conn, query)
    where, params = build_where(resolved)
    rows = _fetch(
        conn,
        f"""
        SELECT ae.event_id::text AS event_id, ae.ts, ae.station_id, ae.sensor_name, ae.cause,
               ae.state, ae.measured_value, ae.acknowledged_at
        FROM   alert_event ae
        WHERE  {where}
        ORDER  BY ae.ts DESC, ae.event_id
        LIMIT  %s
        """,
        params + [MAX_EPISODE_ROWS + 1],
    )
    truncated = len(rows) > MAX_EPISODE_ROWS
    rows = list(reversed(rows[:MAX_EPISODE_ROWS]))
    episodes = group_episodes(rows, timedelta(minutes=gap_minutes))
    episodes.sort(key=lambda e: (e["start_ts"], e["station_id"], e["sensor_name"]), reverse=True)
    causes = _cause_labels(conn, [e["cause_id"] for e in episodes])
    tz = resolved.tzinfo
    items = []
    for e in episodes[:limit]:
        unack = e["alert_count"] - e["acknowledged_count"]
        items.append({
            "station_id": e["station_id"],
            "sensor_name": e["sensor_name"],
            **_component_fields(e["sensor_name"]),
            "cause_id": e["cause_id"],
            "cause_description_zh": (causes.get(e["cause_id"]) or {}).get("description_zh"),
            "start_ts": _iso(e["start_ts"], tz),
            "end_ts": _iso(e["end_ts"], tz),
            "duration_minutes": round((e["end_ts"] - e["start_ts"]).total_seconds() / 60, 1),
            "alert_count": e["alert_count"],
            "warning_count": e["warning_count"],
            "fault_count": e["fault_count"],
            "worst_state": "fault" if e["fault_count"] else "warning",
            "min_value": e["min_value"],
            "max_value": e["max_value"],
            "latest_value": e["latest_value"],
            "acknowledged_count": e["acknowledged_count"],
            "unacknowledged_count": unack,
            "handling_status": "unacknowledged" if e["acknowledged_count"] == 0
                               else ("partially_acknowledged" if unack else "acknowledged"),
            "first_acknowledged_at": _iso(e["first_acknowledged_at"], tz),
            "first_event_id": e["first_event_id"],
            "last_event_id": e["last_event_id"],
        })
    return {
        "time_range": _time_range(resolved),
        "filters": resolved.echo(),
        "gap_minutes": gap_minutes,
        "alerts_scanned": len(rows),
        "truncated": truncated,
        "truncated_note": f"告警超過 {MAX_EPISODE_ROWS} 筆，只合併最新的 {MAX_EPISODE_ROWS} 筆；請縮小時間範圍。" if truncated else None,
        "episode_total": len(episodes),
        "count": len(items),
        "items": items,
        "notes": EPISODE_NOTES,
    }
