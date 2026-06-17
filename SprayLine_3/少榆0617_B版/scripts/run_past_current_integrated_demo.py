"""Run IntegratedSprayLineService demo.

使用方式
--------
# current：只查 UI time-series，不寫 DB
python scripts/run_past_current_integrated_demo.py --slider 0 --station Station_1

# past：查 60 分鐘前的 past window
python scripts/run_past_current_integrated_demo.py --slider -60 --window 30 --station Station_1

# future：用 current window 產生 future payload，但不寫 DB
python scripts/run_past_current_integrated_demo.py --slider 30 --station Station_1

# 寫回 DB（會觸發 MonitoringWorker 與 future_prediction_result 寫入）
python scripts/run_past_current_integrated_demo.py --slider 30 --station Station_1 --write-back
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from webservices.integration_adapter.database_versionb_adapter import get_connection
from webservices.integrated_service.sprayline_integrated_service import (
    IntegratedSprayLineService,
    build_demo_request,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slider", type=float, default=0, help="negative=past, 0=current, positive=future minutes")
    parser.add_argument("--window", type=int, default=30, help="past/current window minutes")
    parser.add_argument("--station", default="Station_1")
    parser.add_argument("--write-back", action="store_true", help="write alert/status/future result back to DB")
    args = parser.parse_args()

    request = build_demo_request(slider_value=args.slider)
    request["window_minutes"] = args.window
    request["station_scope"] = [args.station]

    conn = get_connection()
    try:
        service = IntegratedSprayLineService(conn=conn)
        result = service.run_integrated_once(conn, request, write_back=args.write_back)
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
