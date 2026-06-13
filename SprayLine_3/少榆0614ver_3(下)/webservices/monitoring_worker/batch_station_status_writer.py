from typing import Dict, Any
import psycopg2.extras

SENSOR_TO_STATE_FIELD = {
    "servo_torque_load_pct": "robot_arm_state",
    "path_error_mm": "robot_arm_state",
    "vibration_g": "robot_arm_state",
    "gearbox_temperature_c": "robot_arm_state",
    "paint_flow_ml_min": "nozzle_state",
    "nozzle_roll": "nozzle_state",
    "filter_diff_pressure_bar": "filter_state",
    "air_pressure_bar": "compressor_state",
    "spray_width_mm": "spray_width_state",
    "film_thickness_um": "quality_state",
    "temperature_c": "quality_state",
    "humidity_rh": "quality_state",
}


def merge_state(old_state, new_state):
    order = {None: 0, "ok": 1, "warning": 2, "fault": 3}
    return new_state if order.get(new_state, 0) >= order.get(old_state, 0) else old_state


def upsert_batch_station_status(conn, batch_id: str, station_id: str, detected: Dict[str, Any]) -> Dict[str, Any]:
    state_field = SENSOR_TO_STATE_FIELD.get(detected["sensor_name"])
    if not state_field:
        return {"skipped": True, "reason": "no_state_field_mapping", "sensor_name": detected["sensor_name"]}
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM batch_station_status WHERE batch_id=%s AND station_id=%s",
            (batch_id, station_id),
        )
        existing = dict(cur.fetchone() or {})
        next_state = merge_state(existing.get(state_field), detected["state"])
        cur.execute(
            f"""
            INSERT INTO batch_station_status(batch_id, station_id, {state_field})
            VALUES(%s, %s, %s)
            ON CONFLICT (batch_id, station_id)
            DO UPDATE SET {state_field}=EXCLUDED.{state_field}, write_time=NOW()
            RETURNING *
            """,
            (batch_id, station_id, next_state),
        )
        row = dict(cur.fetchone())
        conn.commit()
        return row
