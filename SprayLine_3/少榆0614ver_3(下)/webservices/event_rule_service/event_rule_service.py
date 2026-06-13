import json
from pathlib import Path
from typing import Optional
import psycopg2.extras

RULE_FILE = Path(__file__).resolve().parents[2] / "rules" / "sensor_thresholds.json"

def _in_band(value, band):
    if "min" in band and value < band["min"]: return False
    if "min_exclusive" in band and value <= band["min_exclusive"]: return False
    if "max" in band and value > band["max"]: return False
    if "max_exclusive" in band and value >= band["max_exclusive"]: return False
    return True

def classify_value(sensor_name: str, value: float) -> Optional[str]:
    rules=json.loads(RULE_FILE.read_text(encoding="utf-8"))["rules"]
    rule=rules.get(sensor_name)
    if not rule: return None
    if any(_in_band(value,b) for b in rule.get("fault",[])): return "fault"
    if any(_in_band(value,b) for b in rule.get("warning",[])): return "warning"
    if _in_band(value,rule.get("normal",{})): return "normal"
    return "warning"

def insert_alert_event(conn,batch_id,station,sensor_name,value,state,timestamp,message=None):
    # Avoid duplicate alerts for the same batch/station/sensor/timestamp/state.
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT * FROM alert_event
            WHERE batch_id=%s AND station_id=%s AND sensor_name=%s AND ts=%s AND state=%s
            ORDER BY ts DESC LIMIT 1
            """,
            (batch_id, station, sensor_name, timestamp, state),
        )
        existing = cur.fetchone()
        if existing:
            return dict(existing)
        sql="""INSERT INTO alert_event(batch_id,station_id,sensor_name,measured_value,state,ts,message)
                 VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING *"""
        cur.execute(sql,(batch_id,station,sensor_name,value,state,timestamp,message)); row=dict(cur.fetchone()); conn.commit(); return row

def evaluate_event_rules(conn, station: str, batch_id: str, timestamp: str, sensor_payload: dict, data_quality_flag: Optional[str]=None) -> dict:
    if data_quality_flag == "interpolated":
        return {"station":station,"batch_id":batch_id,"timestamp":timestamp,"data_quality_flag":data_quality_flag,"triggered_events":[],"skipped":True,"skip_reason":"interpolated_data"}
    triggered=[]
    for sensor_name,value in sensor_payload.items():
        if value is None: continue
        state=classify_value(sensor_name,float(value))
        if state in {"warning","fault"}:
            triggered.append(insert_alert_event(conn,batch_id,station,sensor_name,float(value),state,timestamp,f"{sensor_name} classified as {state}"))
    return {"station":station,"batch_id":batch_id,"timestamp":timestamp,"data_quality_flag":data_quality_flag,"triggered_events":triggered,"skipped":False,"skip_reason":None}

def list_unacknowledged_alert_events(conn, station: Optional[str]=None, severity: Optional[str]=None):
    sql="""SELECT ae.*, cc.severity cause_severity, cc.description_zh cause_description
             FROM alert_event ae
             LEFT JOIN alert_cause_link acl ON ae.event_id=acl.alert_id
             LEFT JOIN cause_catalog cc ON acl.cause_id=cc.cause_id
             WHERE ae.acknowledged_at IS NULL
               AND (%(station)s IS NULL OR ae.station_id=%(station)s)
               AND (%(severity)s IS NULL OR cc.severity=%(severity)s)
             ORDER BY ae.ts DESC"""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql,{"station":station,"severity":severity}); return [dict(r) for r in cur.fetchall()]

def acknowledge_alert_event(conn,event_id: str,operator_id: str):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("UPDATE alert_event SET acknowledged_at=NOW() WHERE event_id=%s AND acknowledged_at IS NULL RETURNING event_id,acknowledged_at",(event_id,)); row=cur.fetchone(); conn.commit(); return dict(row) if row else {}
