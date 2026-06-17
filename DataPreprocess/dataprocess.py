import time
import math
from datetime import datetime, timedelta
import numpy as np
import sprayline_db_queries as db

STATION_CONFIG = {
    "Station_1": {"spray_width_base": 120.0},
    "Station_2": {"spray_width_base": 100.0},
    "Station_3": {"spray_width_base": 82.0}
}

# --- 資料清洗函式 ---
def clean_data(station, reading, last_valid):
    if reading['data_quality_flag'] == 'outlier':
        if last_valid[station] is not None:
            reading['servo_torque_load_pct'] = last_valid[station]['servo_torque_load_pct']
            reading['filter_diff_pressure_bar'] = last_valid[station]['filter_diff_pressure_bar']
            reading['paint_flow_ml_min'] = last_valid[station]['paint_flow_ml_min']
            reading['spray_width_mm'] = last_valid[station]['spray_width_mm']
            reading['path_error_mm'] = last_valid[station]['path_error_mm']
            reading['data_quality_flag'] = 'interpolated'
        return reading
    else:
        last_valid[station] = reading.copy()
        return reading

def run_physical_twin_pipeline():
    print("啟動邊緣運算【1分鐘快照拋轉、跨分鐘陡坡惡化、雙軌維修重置】...\n")
    
    try:
        conn = db.get_connection()
        print("成功連線至 PostgreSQL 資料庫\n")
    except Exception as e:
        print(f"資料庫連線失敗: {e}")
        return

    SPEED_MULTIPLIER = 0.01  
    
    print("正在與資料庫同步狀態，尋找上次斷點與機台耗損度...")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(start_time) FROM batch_run;")
            last_db_time = cur.fetchone()[0]
            if last_db_time:
                virtual_time = last_db_time + timedelta(minutes=1)
                virtual_time = virtual_time.replace(second=0, microsecond=0)
                print(f"時間同步成功！從 {virtual_time.strftime('%Y-%m-%d %H:%M:%S')} 繼續模擬。")
            else:
                virtual_time = datetime(2026, 6, 9, 8, 0, 0)
                print(f"資料庫為空，從初始時間 {virtual_time.strftime('%Y-%m-%d %H:%M:%S')} 開始全新模擬。")
            
            cur.execute("SELECT COUNT(*) FROM batch_run WHERE status = 'ok';")
            total_batches = cur.fetchone()[0]
            daily_batches = 0
            print(f"耗損同步成功！目前累積總生產 {total_batches} 批。\n")
    except Exception as e:
        print(f"同步狀態失敗 ({e})，使用預設初始值。")
        virtual_time = datetime(2026, 6, 9, 8, 0, 0)
        total_batches = 0
        daily_batches = 0

    last_valid_readings = {"Station_1": None, "Station_2": None, "Station_3": None} 
    
    factory_state = {
        "Station_1": None, "Conv_1_to_2": [None, None],
        "Station_2": None, "Conv_2_to_3": [None, None],
        "Station_3": None
    }
    
    # 🌟 狀態機：老化磨損度、維修計時器、陡坡惡化計時器
    station_wear = {"Station_1": 0, "Station_2": 0, "Station_3": 0}
    maintenance_timers = {"Station_1": 0, "Station_2": 0, "Station_3": 0}
    steep_slope_timers = {"Station_1": 0, "Station_2": 0, "Station_3": 0}

    while True:
        current_hour = virtual_time.hour
        minute = virtual_time.minute
        sec = virtual_time.second
        
        if current_hour == 8 and minute == 0 and sec == 0:
            daily_batches = 0
            print(f"[{virtual_time.strftime('%H:%M:%S')}] 🔧 廠房每日開線巡檢完成！")

        accept_new_batch = (8 <= current_hour < 12) or (13 <= current_hour < 15)
        has_wip = not (factory_state["Station_1"] is None and all(b is None for b in factory_state["Conv_1_to_2"]) and factory_state["Station_2"] is None and all(b is None for b in factory_state["Conv_2_to_3"]) and factory_state["Station_3"] is None)

        if not accept_new_batch and not has_wip:
            if 12 <= current_hour < 13: next_start = virtual_time.replace(hour=13, minute=0, second=0)
            else: next_start = (virtual_time + timedelta(days=1)).replace(hour=8, minute=0, second=0)
            print(f"\n[{virtual_time.strftime('%H:%M:%S')}] 產線淨空，系統休眠。快轉至 {next_start.strftime('%m-%d %H:%M:%S')}...\n")
            virtual_time = next_start
            time.sleep(1.0)
            continue

        if sec == 0 and minute % 3 == 0:
            env_readings = []
            for station in STATION_CONFIG.keys():
                env_readings.append({
                    "ts": virtual_time, "batch_id": factory_state[station], "station_id": station,
                    "temperature_c": round(np.random.normal(25.0, 0.3), 2),
                    "humidity_rh": round(np.random.normal(50.0, 1.0), 2),
                    "data_quality_flag": "normal"
                })
            try:
                db.insert_sensor_3min_readings_batch(conn, env_readings)
                conn.commit()
            except: pass

        # =================================================
        # 狀態更新與排程判斷 (每分鐘第 0 秒)
        # =================================================
        if sec == 0:
            for st in STATION_CONFIG.keys():
                # 1. 維修中倒數
                if maintenance_timers[st] > 0:
                    maintenance_timers[st] -= 1
                    if maintenance_timers[st] == 0:
                        station_wear[st] = 0 # 完修後老化清零
                        print(f"[{virtual_time.strftime('%H:%M:%S')}] 🟢 {st} 維修完成！狀態恢復如新。")
                
                # 2. 陡坡惡化中倒數
                elif steep_slope_timers[st] > 0:
                    steep_slope_timers[st] += 1
                    # 惡化滿 3 分鐘後，徹底崩潰，進入維修停機
                    if steep_slope_timers[st] > 3:
                        steep_slope_timers[st] = 0
                        maintenance_timers[st] = 3
                        print(f"[{virtual_time.strftime('%H:%M:%S')}] 💥 {st} 惡化衝破臨界點！設備停機，維修人員介入。")
                
                # 3. 正常運作中的異常判定
                else:
                    if accept_new_batch:
                        is_sudden = np.random.rand() < (1.0 / 900.0)
                        is_aging_broken = station_wear[st] >= 1000

                        if is_sudden:
                            steep_slope_timers[st] = 1 # 啟動陡坡惡化 (第 1 分鐘)
                            print(f"[{virtual_time.strftime('%H:%M:%S')}] ⚠️ 警告！{st} 發生異常磨損，數值開始高斜率飆升...")
                        elif is_aging_broken:
                            maintenance_timers[st] = 3
                            print(f"[{virtual_time.strftime('%H:%M:%S')}] 🚨 警告！{st} 壽命極限，直接停機大修。")

            # 輸送帶工單推移
            factory_state["Station_3"] = factory_state["Conv_2_to_3"].pop(-1)
            factory_state["Conv_2_to_3"].insert(0, factory_state["Station_2"])
            factory_state["Station_2"] = factory_state["Conv_1_to_2"].pop(-1)
            factory_state["Conv_1_to_2"].insert(0, factory_state["Station_1"])
            
            if accept_new_batch:
                new_batch_id = f"B_{virtual_time.strftime('%Y%m%d_%H%M%S')}"
                factory_state["Station_1"] = new_batch_id
                try:
                    db.insert_batch_run(conn, batch_id=new_batch_id, start_time=virtual_time, status="running")
                    conn.commit()
                except: pass
            else: factory_state["Station_1"] = None

        # =================================================
        # 1 分鐘特徵快照生成與寫入 (每分鐘第 50 秒)
        # =================================================
        if sec == 50:
            minute_readings = []
            
            for station, config in STATION_CONFIG.items():
                current_batch = factory_state[station]
                if current_batch is None: continue
                
                wear = station_wear[station]
                
                # A 狀態：維修中（極端故障值，會被打上 outlier 並被清洗成平線）
                if maintenance_timers[station] > 0:
                    filter_pressure = 0.85
                    torque_reading = 85.0
                    paint_flow = 50.0
                    spray_width = 0.0
                    path_error = 0.0
                    flag = "outlier"
                    
                # B 狀態：🌟 陡坡惡化期 🌟（連續 3 分鐘，數值每一分鐘都比上一分鐘更糟）
                elif steep_slope_timers[station] > 0:
                    progress = steep_slope_timers[station] # 值為 1, 2, 或 3
                    
                    # 隨著 progress 增加，斜率越來越陡
                    torque_reading = round(np.random.normal(45.0 + (wear * 0.015) + (progress * 12.0), 1.0), 2)
                    filter_pressure = round(np.random.normal(0.10 + (wear * 0.0005) + (progress * 0.15), 0.005), 3)
                    paint_flow = round(np.random.normal(115.0 - (wear * 0.01) - (progress * 15.0), 0.5), 2)
                    
                    spray_width = max(0.0, round(np.random.normal(config["spray_width_base"] - (wear * 0.005) - (progress * 8.0), 0.5), 2))
                    path_error = round(np.random.normal(0.02 + (wear * 0.0001) + (progress * 0.03), 0.001), 3)
                    
                    # 保持 normal，讓資料庫如實記錄下這 3 分鐘的上升斜坡！
                    flag = "normal" 
                    
                # C 狀態：正常健康 / 漸進老化
                else:
                    filter_pressure = 0.10 + (wear * 0.0005)
                    base_torque = 45.0 + (wear * 0.015) 
                    base_flow = 115.0 - (wear * 0.01)
                    spray_width = config["spray_width_base"] - (wear * 0.005)
                    path_error = 0.02 + (wear * 0.0001)

                    flag = "normal"
                    torque_reading = round(np.random.normal(base_torque, 1.5), 2)
                    paint_flow = round(np.random.normal(base_flow, 0.5), 2)
                    filter_pressure = round(np.random.normal(filter_pressure, 0.01), 3)
                    
                    # 1% 機率的瞬間雜訊
                    if np.random.rand() > 0.99:
                        torque_reading = 85.0
                        flag = "outlier"
                        
                reading = {
                    "ts": virtual_time, "batch_id": current_batch, "station_id": station,
                    "paint_flow_ml_min": paint_flow,
                    "filter_diff_pressure_bar": filter_pressure,
                    "servo_torque_load_pct": torque_reading,
                    "air_pressure_bar": round(np.random.normal(3.2, 0.05), 2), 
                    "spray_width_mm": round(np.random.normal(spray_width, 0.5), 2),
                    "path_error_mm": round(np.random.normal(path_error, 0.005), 3),
                    "data_quality_flag": flag
                }
                
                reading = clean_data(station, reading, last_valid_readings)
                minute_readings.append(reading)
                
                # 只有在正常狀態下加工，磨損度才 +1 (惡化期不加)
                if maintenance_timers[station] == 0 and steep_slope_timers[station] == 0 and flag == "normal":
                    station_wear[station] += 1

            try:
                # 只寫入該分鐘的 3 筆快照
                if minute_readings: db.insert_sensor_readings_batch(conn, minute_readings)
                
                completed_batch = factory_state["Station_3"]
                if completed_batch:
                    db.update_batch_status(conn, batch_id=completed_batch, status="ok", ended_time=virtual_time)
                    total_batches += 1
                    daily_batches += 1
                conn.commit()
            except Exception as e: conn.rollback()

        # 時間推進
        virtual_time += timedelta(seconds=1)
        time.sleep(SPEED_MULTIPLIER)

if __name__ == "__main__":
    run_physical_twin_pipeline()