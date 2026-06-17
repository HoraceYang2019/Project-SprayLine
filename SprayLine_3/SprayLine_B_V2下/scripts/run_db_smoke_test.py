"""End-to-end DB smoke test for 少榆0616ver_4.

Read-only mode:
    python scripts/run_db_smoke_test.py

Write test data and run 少榆 Monitoring/Future once:
    python scripts/run_db_smoke_test.py --write-test-data

The write mode creates a new test batch_id starting with B_SHAOYU_E2E_.
It does not delete production data. Do not run setup_db.py here unless the DB owner agrees,
because setup_db.py rebuilds tables.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from webservices.integration_adapter.database_versionb_adapter import (  # noqa: E402
    get_adapter_status,
    get_connection,
    import_database_module,
)
from webservices.monitoring_worker.monitoring_worker import run_monitoring_once  # noqa: E402
from webservices.future_service.future_service import (  # noqa: E402
    build_future_prediction_payload,
    save_future_prediction_result,
)


def insert_minimal_fault_sensor_data(conn, station_id: str, batch_id: str) -> None:
    db_batch = import_database_module("db_batch")
    db_sensor = import_database_module("db_sensor")

    now = datetime.now(timezone.utc)
    db_batch.insert_batch_run(conn, batch_id=batch_id, start_time=now, status="running")
    db_sensor.insert_sensor_readings_batch(conn, [
        {
            "ts": now,
            "batch_id": batch_id,
            "station_id": station_id,
            "film_thickness_um": 15.0,
            "paint_flow_ml_min": 108.0,
            "nozzle_roll": 0.0,
            "filter_diff_pressure_bar": 0.95,  # fault: > 0.7 in rules/sensor_thresholds.json
            "filter_inflow_ml_min": 110.0,
            "filter_outflow_ml_min": 109.0,
            "pump_current_a": 2.1,
            "air_pressure_bar": 2.5,
            "spray_width_mm": 105.0,
            "servo_torque_load_pct": 45.0,
            "path_error_mm": 0.02,
            "vibration_g": 0.12,
            "tcp_x_mm": 100.0,
            "tcp_y_mm": 50.0,
            "tcp_z_mm": 200.0,
            "speed_mm_s": 300.0,
            "data_quality_flag": "normal",
        }
    ])
    conn.commit()


def run_future_write_test(conn, batch_id: str, station_id: str) -> str:
    payload = build_future_prediction_payload(
        batch_id=batch_id,
        station_id=station_id,
        prediction_time=datetime.now(timezone.utc).isoformat(),
        predicted_ok_rate=88.5,
        predicted_ng_count=22,
        quality_score=87.0,
        model_input_source="shaoyu_0616ver_4_db_smoke_test;sensor_1min;sensor_3min;batch_run",
    )
    return save_future_prediction_result(conn, payload, commit=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--station", default="Station_1")
    parser.add_argument("--lookback-minutes", type=int, default=5)
    parser.add_argument("--write-test-data", action="store_true", help="insert one test batch and one fault sensor row before running MonitoringWorker")
    args = parser.parse_args()

    print("=== 少榆0616ver_4 DB smoke test ===")
    print("Adapter:", get_adapter_status())

    conn = get_connection()
    try:
        batch_id = f"B_SHAOYU_E2E_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        if args.write_test_data:
            print(f"[WRITE] inserting test batch/sensor data: batch_id={batch_id}, station={args.station}")
            insert_minimal_fault_sensor_data(conn, args.station, batch_id)
        else:
            print("[READ-ONLY] no test data inserted. Use --write-test-data for full E2E write test.")

        print("[RUN] MonitoringWorker.run_monitoring_once")
        monitoring_result = run_monitoring_once(station=args.station, lookback_minutes=args.lookback_minutes)
        print(monitoring_result)

        if args.write_test_data:
            print("[WRITE] FutureService.save_future_prediction_result")
            prediction_id = run_future_write_test(conn, batch_id, args.station)
            print({"prediction_id": prediction_id, "batch_id": batch_id})

        print("[DONE] smoke test completed")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] smoke test failed and rolled back current transaction: {type(exc).__name__}: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
