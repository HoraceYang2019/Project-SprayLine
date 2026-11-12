from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

MANAGER_TIMEZONE = ZoneInfo("Asia/Taipei")
LINE_TO_STATION = {
    "line_1": "Station_1",
    "line_2": "Station_2",
    "line_3": "Station_3",
}
STATION_TO_LINE = {station_id: line_id for line_id, station_id in LINE_TO_STATION.items()}


class ManagerDateSelectionError(ValueError):
    def __init__(self, message: str, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


def _get_db_fetchers():
    from db_connection import _fetch, _fetchone

    return _fetch, _fetchone


def _hour_as_int(value: Any) -> int:
    if value in (None, ""):
        raise ManagerDateSelectionError("hour is required", status_code=422)

    try:
        hour = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ManagerDateSelectionError(f"invalid hour: {value}", status_code=404) from exc

    if hour < 0 or hour > 23:
        raise ManagerDateSelectionError(f"invalid hour: {value}", status_code=404)

    return hour


def get_manager_available_dates(conn) -> dict[str, Any]:
    fetch, _ = _get_db_fetchers()
    rows = fetch(
        conn,
        """
        SELECT
            DATE(ts AT TIME ZONE 'Asia/Taipei')::text AS data_date,
            EXTRACT(HOUR FROM ts AT TIME ZONE 'Asia/Taipei')::int AS data_hour,
            COUNT(*)::int AS row_count,
            MAX(ts) AS latest_ts
        FROM sensor_1min
        WHERE ts IS NOT NULL
        GROUP BY 1, 2
        ORDER BY data_date DESC, data_hour DESC
        """,
    )

    available_hours_by_date: dict[str, list[int]] = {}
    for row in rows:
        date_key = str(row.get("data_date") or "")
        hour = int(row.get("data_hour") or 0)
        available_hours_by_date.setdefault(date_key, []).append(hour)

    for date_key, hours in available_hours_by_date.items():
        available_hours_by_date[date_key] = sorted({int(hour) for hour in hours})

    available_dates = sorted(available_hours_by_date.keys(), reverse=True)
    latest_date = available_dates[0] if available_dates else None
    latest_hour = (
        max(available_hours_by_date.get(latest_date, []))
        if latest_date and available_hours_by_date.get(latest_date)
        else None
    )

    return {
        "availableDates": available_dates,
        "latestDate": latest_date,
        "availableHoursByDate": available_hours_by_date,
        "latestHour": latest_hour,
        "dateSource": "db_sensor_1min",
    }


def resolve_manager_date_hour(conn, date: str | None = None, hour: Any | None = None) -> dict[str, Any]:
    availability = get_manager_available_dates(conn)
    available_dates = availability["availableDates"]
    if not available_dates:
        raise ManagerDateSelectionError("No sensor_1min data is available for Manager Dashboard.", status_code=404)

    requested_date = str(date).strip() if date not in (None, "") else None
    requested_hour = None if hour in (None, "") else _hour_as_int(hour)

    if requested_date is None:
        selected_date = availability["latestDate"]
        date_source = "db_latest"
    elif requested_date in available_dates:
        selected_date = requested_date
        date_source = "user_selected"
    else:
        raise ManagerDateSelectionError(
            f"No manager dashboard data exists for date {requested_date}.",
            status_code=404,
        )

    available_hours = list(availability["availableHoursByDate"].get(selected_date, []))
    if not available_hours:
        raise ManagerDateSelectionError(
            f"No manager dashboard data exists for date {selected_date}.",
            status_code=404,
        )

    if requested_hour is None:
        selected_hour = max(available_hours)
    elif requested_hour in available_hours:
        selected_hour = requested_hour
        date_source = "user_selected"
    else:
        raise ManagerDateSelectionError(
            f"No manager dashboard data exists for date {selected_date} hour {requested_hour:02d}.",
            status_code=404,
        )

    anchor_row = get_manager_anchor_sensor_row(conn, selected_date, selected_hour)
    if not anchor_row:
        raise ManagerDateSelectionError(
            f"No sensor_1min row exists for date {selected_date} hour {selected_hour:02d}.",
            status_code=404,
        )

    selected_start = datetime.strptime(
        f"{selected_date} {selected_hour:02d}:00:00",
        "%Y-%m-%d %H:%M:%S",
    ).replace(tzinfo=MANAGER_TIMEZONE)
    selected_end = selected_start + timedelta(hours=1)

    anchor_time = anchor_row.get("ts")
    if hasattr(anchor_time, "astimezone"):
        anchor_time = anchor_time.astimezone(MANAGER_TIMEZONE)
    anchor_time_iso = anchor_time.isoformat() if hasattr(anchor_time, "isoformat") else str(anchor_time)

    return {
        **availability,
        "selectedDate": selected_date,
        "selectedHour": selected_hour,
        "availableHours": available_hours,
        "dateSource": date_source,
        "anchorTime": anchor_time_iso,
        "anchorBatchId": anchor_row.get("batch_id"),
        "selectedHourStart": selected_start.isoformat(),
        "selectedHourEnd": selected_end.isoformat(),
    }


def get_manager_anchor_sensor_row(conn, selected_date: str, selected_hour: int) -> dict[str, Any] | None:
    _, fetchone = _get_db_fetchers()
    return fetchone(
        conn,
        """
        SELECT *
        FROM sensor_1min
        WHERE DATE(ts AT TIME ZONE 'Asia/Taipei') = %s::date
          AND EXTRACT(HOUR FROM ts AT TIME ZONE 'Asia/Taipei')::int = %s
        ORDER BY ts DESC
        LIMIT 1
        """,
        (selected_date, selected_hour),
    )


def get_manager_station_rows_for_hour(conn, selected_date: str, selected_hour: int) -> dict[str, dict[str, Any]]:
    fetch, _ = _get_db_fetchers()
    rows = fetch(
        conn,
        """
        SELECT DISTINCT ON (station_id) *
        FROM sensor_1min
        WHERE DATE(ts AT TIME ZONE 'Asia/Taipei') = %s::date
          AND EXTRACT(HOUR FROM ts AT TIME ZONE 'Asia/Taipei')::int = %s
        ORDER BY station_id, ts DESC
        """,
        (selected_date, selected_hour),
    )
    return {str(row.get("station_id")): row for row in rows}


def get_manager_station_hourly_aggregates(conn, selected_date: str) -> dict[str, dict[int, dict[str, Any]]]:
    fetch, _ = _get_db_fetchers()
    rows = fetch(
        conn,
        """
        SELECT
            station_id,
            EXTRACT(HOUR FROM ts AT TIME ZONE 'Asia/Taipei')::int AS data_hour,
            COUNT(*)::int AS row_count,
            COUNT(DISTINCT batch_id) FILTER (WHERE batch_id IS NOT NULL)::int AS distinct_batch_count,
            AVG(paint_flow_ml_min) AS avg_paint_flow_ml_min,
            AVG(air_pressure_bar) AS avg_air_pressure_bar,
            AVG(spray_width_mm) AS avg_spray_width_mm,
            AVG(filter_diff_pressure_bar) AS avg_filter_diff_pressure_bar,
            AVG(servo_torque_load_pct) AS avg_servo_torque_load_pct,
            AVG(path_error_mm) AS avg_path_error_mm,
            MAX(path_error_mm) AS max_path_error_mm,
            MAX(ts) AS latest_ts
        FROM sensor_1min
        WHERE DATE(ts AT TIME ZONE 'Asia/Taipei') = %s::date
        GROUP BY station_id, data_hour
        ORDER BY station_id, data_hour
        """,
        (selected_date,),
    )

    output: dict[str, dict[int, dict[str, Any]]] = {}
    for row in rows:
        station_id = str(row.get("station_id") or "")
        hour = int(row.get("data_hour") or 0)
        output.setdefault(station_id, {})[hour] = row
    return output


def get_manager_sensor_rows_for_date(conn, selected_date: str) -> list[dict[str, Any]]:
    fetch, _ = _get_db_fetchers()
    return fetch(
        conn,
        """
        SELECT
            station_id,
            batch_id,
            ts,
            EXTRACT(HOUR FROM ts AT TIME ZONE 'Asia/Taipei')::int AS data_hour,
            paint_flow_ml_min,
            air_pressure_bar,
            spray_width_mm,
            path_error_mm
        FROM sensor_1min
        WHERE DATE(ts AT TIME ZONE 'Asia/Taipei') = %s::date
        ORDER BY ts ASC
        """,
        (selected_date,),
    )


def get_manager_distinct_batch_count_for_date(conn, selected_date: str) -> int:
    _, fetchone = _get_db_fetchers()
    row = fetchone(
        conn,
        """
        SELECT COUNT(DISTINCT batch_id)::int AS distinct_batch_count
        FROM sensor_1min
        WHERE DATE(ts AT TIME ZONE 'Asia/Taipei') = %s::date
          AND batch_id IS NOT NULL
        """,
        (selected_date,),
    ) or {}
    return int(row.get("distinct_batch_count") or 0)
