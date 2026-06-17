from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

for url in [
    "/api/health",
    "/api/dashboard-data?mode=time&slider_value=0",
    "/api/component-detail?station_id=M2&component_key=width&mode=time&slider_value=0",
    "/api/station-detail?station_id=M3&mode=time&slider_value=0",
    "/api/trend-data?station_id=M1&component_key=arm",
]:
    response = client.get(url)
    assert response.status_code == 200, (url, response.status_code, response.text)
    print(url, "OK")
