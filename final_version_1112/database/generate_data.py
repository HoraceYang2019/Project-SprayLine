"""
SprayLine 一週假資料生成腳本
用途: 依照 Schema v5 生成七天的模擬感測資料並寫入 PostgreSQL
用法: python generate_data.py
      DB_HOST=... DB_PASSWORD=... python generate_data.py

模擬情境:
  - 日期: 2026-06-02 (週一) ~ 2026-06-08 (週日)
  - 每天 08:00~17:00 運作，每 35 分鐘啟動一批次 → 每天 13 批次
  - 每批次依序通過 Station_1 → Station_2 → Station_3，各站 30 分鐘
  - 濾網壓差每批次+0.008 bar，超過 0.50 觸發故障並自動更換（重設 0.15）
  - 伺服負載每批次+0.12%，模擬一週緩慢磨耗趨勢
"""

import os, sys, random, uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("[錯誤] 缺少 psycopg2，請先執行：pip install psycopg2-binary")
    sys.exit(1)

# ── 連線設定 ─────────────────────────────────────────────────
CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname":   os.getenv("DB_NAME",     "sprayline"),
}

# ── 模擬參數 ─────────────────────────────────────────────────
RANDOM_SEED         = 42
START_DT = datetime(2026, 6, 2, 8, 0, 0, tzinfo=timezone.utc)
DAYS                = 7
BATCH_INTERVAL_MIN  = 35
STATION_DURATION_MIN= 30
CHANGEOVER_MIN      = 5
DAY_START_HOUR      = 8
LAST_BATCH_HOUR     = 15   # 最後一個批次於 15:30 前啟動，Station_3 在 17:40 前結束

STATIONS = ["Station_1", "Station_2", "Station_3"]
STATION_CFG = {
    "Station_1": {"pressure": 3.5, "spray_width": 120.0,
                  "tcp_base": (300.0, 0.0,   220.0)},
    "Station_2": {"pressure": 3.2, "spray_width": 100.0,
                  "tcp_base": (280.0, 0.0,   210.0)},
    "Station_3": {"pressure": 3.0, "spray_width":  82.0,
                  "tcp_base": (260.0, 0.0,   200.0)},
}

# 感測器閾值
FILTER_WARN  = 0.30;  FILTER_FAULT = 0.50
SERVO_WARN   = 60.0;  SERVO_FAULT  = 80.0
FILM_OK      = (14.5, 15.5)
FILM_WARN    = (14.0, 16.0)
SPRAY_OK_D   = 10.0;  SPRAY_WARN_D = 20.0

# 衰退模型
FILTER_INIT       = 0.15
FILTER_INC        = 0.008   # bar / batch
SERVO_INIT        = 40.0
SERVO_INC         = 0.12    # % / batch


# ── 亂數工具 ─────────────────────────────────────────────────
rng = random.Random(RANDOM_SEED)

def gauss(mu: float, sigma: float, lo: float = None, hi: float = None) -> float:
    v = rng.gauss(mu, sigma)
    if lo is not None: v = max(v, lo)
    if hi is not None: v = min(v, hi)
    return round(v, 4)

def clamp(v, lo, hi): return max(lo, min(hi, v))


# ── 狀態判斷輔助 ─────────────────────────────────────────────
def filter_state(val: float) -> str:
    if val > FILTER_FAULT: return "fault"
    if val > FILTER_WARN:  return "warning"
    return "ok"

def servo_state(val: float) -> str:
    if val > SERVO_FAULT: return "fault"
    if val > SERVO_WARN:  return "warning"
    return "ok"

def film_state(val: float) -> str:
    if val < FILM_WARN[0] or val > FILM_WARN[1]: return "fault"
    if val < FILM_OK[0]  or val > FILM_OK[1]:    return "warning"
    return "ok"

def spray_state(val: float, nominal: float) -> str:
    delta = abs(val - nominal)
    if delta > SPRAY_WARN_D: return "fault"
    if delta > SPRAY_OK_D:   return "warning"
    return "ok"

def worst(states) -> str:
    if "fault"   in states: return "fault"
    if "warning" in states: return "warning"
    return "ok"

STATE_TO_RESPONSE = {
    "filter":     {"warning": "BACKWASH_FILTER",  "fault": "REPLACE_FILTER"},
    "servo":      {"warning": "LUBRICATE_SERVO",  "fault": "REPLACE_SERVO"},
    "nozzle":     {"warning": "CLEAN_NOZZLE",     "fault": "REPLACE_NOZZLE"},
    "compressor": {"warning": "CALIBRATE_PRESSURE_VALVE", "fault": "CALIBRATE_PRESSURE_VALVE"},
    "spray_width":{"warning": "ADJUST_FLOW_PRESSURE", "fault": "ADJUST_TCP_Z"},
    "quality":    {"warning": "ADJUST_SPEED_FLOW",    "fault": "ADJUST_SPEED_FLOW"},
}

CAUSE_MAP = {
    "filter":     {"warning": "FILTER_CLOG",           "fault": "FILTER_CLOG"},
    "servo":      {"warning": "SERVO_WEAR",             "fault": "SERVO_WEAR"},
    "nozzle":     {"warning": "NOZZLE_CLOG",            "fault": "NOZZLE_CLOG"},
    "compressor": {"warning": "AIR_PRESSURE_UNSTABLE",  "fault": "AIR_PRESSURE_UNSTABLE"},
    "spray_width":{"warning": "SPRAY_WIDTH_DEVIATION",  "fault": "NOZZLE_CLOG"},
    "quality":    {"warning": "THICKNESS_DRIFT",        "fault": "THICKNESS_DRIFT"},
}


# ── 批次生成邏輯 ─────────────────────────────────────────────
def gen_batch_schedule() -> list:
    """回傳 [(batch_id, station_id, station_start, station_end, day_batch_idx), ...]"""
    schedule = []
    batch_counter = 0

    for day in range(DAYS):
        day_base = START_DT + timedelta(days=day)
        # 重置到當天 08:00
        t = day_base.replace(hour=DAY_START_HOUR, minute=0, second=0, microsecond=0)
        cutoff = day_base.replace(hour=LAST_BATCH_HOUR, minute=30, second=0)

        while t <= cutoff:
            batch_counter += 1
            bid = f"B_{t.strftime('%Y%m%d')}_{batch_counter:04d}"
            station_t = t
            for si, stn in enumerate(STATIONS):
                s_start = station_t
                s_end   = s_start + timedelta(minutes=STATION_DURATION_MIN)
                schedule.append((bid, stn, s_start, s_end))
                station_t = s_end + timedelta(minutes=CHANGEOVER_MIN)
            t += timedelta(minutes=BATCH_INTERVAL_MIN)

    return schedule


def gen_sensor_reading(
    stn: str, ts: datetime, minute_idx: int,
    filter_p: float, servo_base: float,
    nozzle_wear: float = 0.0,
    add_noise_event: bool = False,
) -> dict:
    """產生一筆 sensor_1min 資料"""
    cfg = STATION_CFG[stn]
    nom_pressure = cfg["pressure"]
    nom_spray    = cfg["spray_width"]
    tx, ty, tz   = cfg["tcp_base"]

    # 機器手臂：TCP 沿 Y 軸移動模擬噴塗行程
    tcp_y = ty + minute_idx * 45.0 + gauss(0, 1.5)
    tcp_x = tx + gauss(0, 2.0)
    tcp_z = tz + gauss(0, 1.0)

    # 伺服負載（含衰退基底）
    servo = gauss(servo_base, 2.5, 20.0, 95.0)
    if add_noise_event and rng.random() < 0.05:
        servo = gauss(65.0, 5.0, 60.0, 85.0)

    # 路徑誤差
    path_error = gauss(0.25, 0.08, 0.05, 2.0)
    if servo > 65.0:
        path_error = gauss(0.8, 0.2, 0.3, 2.0)

    # 振動（正常微震，偶爾突波）
    vibration = gauss(0.8, 0.15, 0.3, 4.0)
    if add_noise_event and rng.random() < 0.02:
        vibration = gauss(2.5, 0.5, 1.5, 4.0)

    # 濾網壓差（衰退）
    fdp = gauss(filter_p, 0.004, 0.10, 1.0)

    # 濾網流量（壓差越高，出口流量越低）
    blockage = clamp((filter_p - 0.15) / 0.40, 0, 1)
    f_in  = gauss(250.0, 2.0, 200.0, 290.0)
    f_out = gauss(f_in * (1 - blockage * 0.3), 1.5, 150.0, 290.0)
    pump_a = round(3.5 + filter_p * 1.8 + gauss(0, 0.1), 4)

    # 空壓機
    air_p = gauss(nom_pressure, 0.05, nom_pressure - 0.3, nom_pressure + 0.3)
    if add_noise_event and rng.random() < 0.02:
        air_p = gauss(nom_pressure * 0.88, 0.05)

    # 噴幅（含噴嘴磨耗）
    spray_width = gauss(nom_spray + nozzle_wear * 8, 2.5, nom_spray - 30, nom_spray + 30)

    # 塗料流量
    paint_flow = gauss(250.0, 2.0, 230.0, 270.0)

    # 噴嘴翻滾角
    nozzle_roll = gauss(0.0, 0.4, -5.0, 5.0)

    # 膜厚（與流量、壓力正相關）
    film = gauss(15.0, 0.2, 13.0, 17.0)
    if paint_flow < 240:
        film = gauss(14.2, 0.2)
    if add_noise_event and rng.random() < 0.03:
        film = gauss(14.1, 0.15, 13.5, 14.4)

    return {
        "ts": ts,
        "film_thickness_um":        round(film, 3),
        "paint_flow_ml_min":        round(paint_flow, 3),
        "nozzle_roll":              round(nozzle_roll, 3),
        "filter_diff_pressure_bar": round(fdp, 4),
        "filter_inflow_ml_min":     round(f_in, 3),
        "filter_outflow_ml_min":    round(f_out, 3),
        "pump_current_a":           pump_a,
        "air_pressure_bar":         round(air_p, 4),
        "spray_width_mm":           round(spray_width, 3),
        "servo_torque_load_pct":    round(servo, 3),
        "path_error_mm":            round(path_error, 4),
        "vibration_g":              round(vibration, 4),
        "tcp_x_mm":                 round(tcp_x, 2),
        "tcp_y_mm":                 round(tcp_y, 2),
        "tcp_z_mm":                 round(tcp_z, 2),
        "speed_mm_s":               round(gauss(300.0, 5.0, 260.0, 340.0), 2),
    }


# ── 主程式 ───────────────────────────────────────────────────
def main():
    print("=" * 55)
    print(" SprayLine 一週假資料生成")
    print("=" * 55)

    conn = psycopg2.connect(**CONFIG)
    cur  = conn.cursor()

    # 清除舊資料（保留 catalog）
    print("[清除] 刪除舊生產資料...")
    for tbl in ["alert_response_link","alert_cause_link","alert_event",
                "batch_station_status","sensor_1hour","sensor_1min","batch_run"]:
        cur.execute(f"DELETE FROM {tbl}")
    conn.commit()

    # 建立批次時間表
    schedule = gen_batch_schedule()
    batch_ids = list(dict.fromkeys(s[0] for s in schedule))  # 保序去重

    print(f"[計畫] 共 {len(batch_ids)} 個批次 × 3 站點 = {len(schedule)} 個站次")
    print(f"       日期範圍: 2026-06-02 ~ 2026-06-08\n")

    # ── 衰退狀態（每站獨立）──────────────────────────────────
    filter_p    = {s: FILTER_INIT for s in STATIONS}
    servo_base  = {s: SERVO_INIT  for s in STATIONS}
    nozzle_wear = {s: 0.0         for s in STATIONS}

    # ── 寫入 batch_run ────────────────────────────────────────
    print("[寫入] batch_run...")
    batch_info = {}  # batch_id → (start_time, station3_end)
    for bid, stn, s_start, s_end in schedule:
        if bid not in batch_info:
            batch_info[bid] = [s_start, s_end]
        else:
            if s_end > batch_info[bid][1]:
                batch_info[bid][1] = s_end

    batch_rows = [
        (bid, times[0], times[1], "ok")
        for bid, times in batch_info.items()
    ]
    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO batch_run (batch_id, start_time, ended_time, status) VALUES %s",
        batch_rows
    )
    conn.commit()

    # ── 主迴圈：逐站次模擬 ───────────────────────────────────
    print("[寫入] sensor_1min + batch_station_status + alerts...")
    s1min_buf   = []
    bss_buf     = []
    alert_buf   = []
    cause_buf   = []
    resp_buf    = []

    FLUSH_SIZE = 2000  # 每 2000 筆感測資料批次寫入

    prev_bid = None
    for idx, (bid, stn, s_start, s_end) in enumerate(schedule):
        cfg    = STATION_CFG[stn]
        fp     = filter_p[stn]
        sb     = servo_base[stn]
        nw     = nozzle_wear[stn]
        nom_sw = cfg["spray_width"]

        batch_readings = []
        for m in range(STATION_DURATION_MIN):
            ts   = s_start + timedelta(minutes=m)
            row  = gen_sensor_reading(stn, ts, m, fp, sb, nw, add_noise_event=True)
            row["batch_id"]   = bid
            row["station_id"] = stn
            batch_readings.append(row)
            s1min_buf.append(row)

        # 批次統計（用平均值判斷狀態）
        def mean_col(col): return sum(r[col] for r in batch_readings) / len(batch_readings)

        avg_fdp    = mean_col("filter_diff_pressure_bar")
        avg_servo  = mean_col("servo_torque_load_pct")
        avg_film   = mean_col("film_thickness_um")
        avg_spray  = mean_col("spray_width_mm")
        avg_vibr   = mean_col("vibration_g")
        avg_air    = mean_col("air_pressure_bar")

        fst = filter_state(avg_fdp)
        sst = servo_state(avg_servo)
        qst = film_state(avg_film)
        swst= spray_state(avg_spray, nom_sw)
        nst = "warning" if avg_vibr > 1.5 else "ok"    # 振動異常 → 噴嘴/機械
        cst = "warning" if abs(avg_air - cfg["pressure"]) > 0.12 else "ok"

        def pick_resp(component: str, state: str) -> Optional[str]:
            return STATE_TO_RESPONSE[component].get(state) if state != "ok" else None

        bss_buf.append((
            bid, stn,
            fst,  sst,  nst,  cst,  swst, qst,
            pick_resp("filter", fst),
            pick_resp("servo",  sst),
            pick_resp("nozzle", nst),
            pick_resp("compressor", cst),
            pick_resp("spray_width", swst),
            pick_resp("quality", qst),
        ))

        # ── 告警生成 ───────────────────────────────────────
        def make_alert(sensor_name, measured, state_val, component):
            eid = str(uuid.uuid4())
            cause_id = CAUSE_MAP[component].get(state_val)
            resp_id  = STATE_TO_RESPONSE[component].get(state_val)
            alert_buf.append((eid, bid, stn, sensor_name, measured, state_val,
                               cause_id, s_end))
            if cause_id:
                cause_buf.append((eid, cause_id, True))
            if resp_id:
                resp_buf.append((eid, resp_id,
                                 s_end + timedelta(minutes=rng.randint(5, 60)),
                                 f"OP_{rng.choice(['A','B','C'])}"))

        if fst != "ok":
            make_alert("filter_diff_pressure_bar", round(avg_fdp, 4), fst, "filter")
        if sst != "ok":
            make_alert("servo_torque_load_pct", round(avg_servo, 3), sst, "servo")
        if qst != "ok":
            make_alert("film_thickness_um", round(avg_film, 3), qst, "quality")
        if swst != "ok":
            make_alert("spray_width_mm", round(avg_spray, 3), swst, "spray_width")

        # ── 衰退更新 ───────────────────────────────────────
        filter_p[stn]   += FILTER_INC
        servo_base[stn] += SERVO_INC
        nozzle_wear[stn] = clamp(nozzle_wear[stn] + 0.003, 0, 1.0)

        # 濾網故障後更換 → 重設
        if filter_p[stn] > FILTER_FAULT:
            filter_p[stn]    = FILTER_INIT
            nozzle_wear[stn] = 0.0  # 順便清洗噴嘴

        # 定期批次寫入
        if len(s1min_buf) >= FLUSH_SIZE:
            _flush_s1min(cur, s1min_buf);  s1min_buf.clear()
            conn.commit()
            print(f"  sensor_1min: {idx+1}/{len(schedule)} 站次已處理...")

    # 寫入剩餘
    _flush_s1min(cur, s1min_buf)
    conn.commit()

    # batch_station_status
    print("[寫入] batch_station_status...")
    psycopg2.extras.execute_values(cur, """
        INSERT INTO batch_station_status
          (batch_id, station_id,
           filter_state, robot_arm_state, nozzle_state, compressor_state,
           spray_width_state, quality_state,
           filter_response_id, robot_arm_response_id, nozzle_response_id,
           compressor_response_id, spray_width_response_id, quality_response_id)
        VALUES %s
    """, bss_buf)
    conn.commit()

    # alerts
    print("[寫入] alert_event + cause/response links...")
    if alert_buf:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO alert_event
              (event_id, batch_id, station_id, sensor_name,
               measured_value, state, cause, ts)
            VALUES %s
        """, alert_buf)
    if cause_buf:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO alert_cause_link (alert_id, cause_id, is_primary)
            VALUES %s
        """, cause_buf)
    if resp_buf:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO alert_response_link
              (alert_id, response_id, executed_at, operator_id)
            VALUES %s
        """, resp_buf)
    conn.commit()

    # ── sensor_1hour ─────────────────────────────────────────
    print("[寫入] sensor_1hour...")
    s1hour_buf = []
    gbox_base  = {s: 45.0 for s in STATIONS}
    for day in range(DAYS):
        day_dt = START_DT + timedelta(days=day)
        for hr in range(8, 19):  # 08:00 ~ 18:00
            ts = day_dt.replace(hour=hr, minute=0, second=0, microsecond=0)
            for stn in STATIONS:
                gtemp = gauss(gbox_base[stn] + servo_base[stn] * 0.08, 1.5, 35.0, 80.0)
                s1hour_buf.append((
                    str(uuid.uuid4()), ts, stn,
                    round(gtemp, 2),
                    round(gauss(23.5, 0.8, 20.0, 30.0), 2),
                    round(gauss(55.0, 2.5, 40.0, 75.0), 2),
                ))
    psycopg2.extras.execute_values(cur, """
        INSERT INTO sensor_1hour
          (row_id, ts, station_id, gearbox_temperature_c, temperature_c, humidity_rh)
        VALUES %s
    """, s1hour_buf)
    conn.commit()

    # ── 最終統計 ─────────────────────────────────────────────
    print_stats(cur)
    cur.close()
    conn.close()


def _flush_s1min(cur, buf):
    if not buf: return
    psycopg2.extras.execute_values(cur, """
        INSERT INTO sensor_1min
          (row_id, ts, batch_id, station_id,
           film_thickness_um, paint_flow_ml_min, nozzle_roll,
           filter_diff_pressure_bar, filter_inflow_ml_min, filter_outflow_ml_min,
           pump_current_a, air_pressure_bar, spray_width_mm,
           servo_torque_load_pct, path_error_mm, vibration_g,
           tcp_x_mm, tcp_y_mm, tcp_z_mm, speed_mm_s)
        VALUES %s
    """, [
        (str(uuid.uuid4()), r["ts"], r["batch_id"], r["station_id"],
         r["film_thickness_um"], r["paint_flow_ml_min"], r["nozzle_roll"],
         r["filter_diff_pressure_bar"], r["filter_inflow_ml_min"],
         r["filter_outflow_ml_min"], r["pump_current_a"],
         r["air_pressure_bar"], r["spray_width_mm"],
         r["servo_torque_load_pct"], r["path_error_mm"], r["vibration_g"],
         r["tcp_x_mm"], r["tcp_y_mm"], r["tcp_z_mm"], r["speed_mm_s"])
        for r in buf
    ])


def print_stats(cur):
    print("\n── 寫入結果 ──────────────────────────────────────────")
    checks = [
        ("batch_run",           "SELECT COUNT(*) FROM batch_run"),
        ("sensor_1min",         "SELECT COUNT(*) FROM sensor_1min"),
        ("sensor_1hour",        "SELECT COUNT(*) FROM sensor_1hour"),
        ("batch_station_status","SELECT COUNT(*) FROM batch_station_status"),
        ("alert_event",         "SELECT COUNT(*) FROM alert_event"),
        ("  ├ warning",         "SELECT COUNT(*) FROM alert_event WHERE state='warning'"),
        ("  └ fault",           "SELECT COUNT(*) FROM alert_event WHERE state='fault'"),
        ("alert_cause_link",    "SELECT COUNT(*) FROM alert_cause_link"),
        ("alert_response_link", "SELECT COUNT(*) FROM alert_response_link"),
    ]
    print(f"  {'項目':<25} {'筆數':>8}")
    print("  " + "-" * 35)
    for label, sql in checks:
        cur.execute(sql)
        n = cur.fetchone()[0]
        print(f"  {label:<25} {n:>8,}")

    cur.execute("""
        SELECT station_id, state, COUNT(*)
        FROM alert_event GROUP BY station_id, state ORDER BY station_id, state
    """)
    rows = cur.fetchall()
    if rows:
        print("\n  各站告警分布:")
        for stn, state, cnt in rows:
            print(f"    {stn} / {state:<8}: {cnt} 筆")

    cur.execute("""
        SELECT station_id,
               ROUND(AVG(filter_diff_pressure_bar)::numeric, 3) AS avg_filter,
               ROUND(AVG(servo_torque_load_pct)::numeric, 2)    AS avg_servo
        FROM sensor_1min GROUP BY station_id ORDER BY station_id
    """)
    print("\n  各站一週感測平均:")
    print(f"  {'站點':<12} {'濾網壓差(bar)':>14} {'伺服負載(%)':>12}")
    for stn, af, sv in cur.fetchall():
        print(f"  {stn:<12} {float(af):>14.3f} {float(sv):>12.2f}")

    print("-" * 45)
    print("\n完成！執行 setup_db.py 可重新建立資料庫。\n")


if __name__ == "__main__":
    main()
