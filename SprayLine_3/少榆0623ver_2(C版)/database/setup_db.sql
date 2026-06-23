-- ============================================================
-- SprayLine Database Setup — Schema v5
-- 引擎: PostgreSQL 16
-- 執行方式: psql -U postgres -d sprayline -f setup_db.sql
--           或透過 setup_db.py 一鍵建立
-- ============================================================

-- 清除舊表（重新建立時使用）
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS component_issue_solution_map CASCADE;
DROP TABLE IF EXISTS cause_response_map CASCADE;
DROP TABLE IF EXISTS future_prediction_result CASCADE;
DROP TABLE IF EXISTS sensor_threshold CASCADE;
DROP TABLE IF EXISTS solution_catalog  CASCADE;
DROP TABLE IF EXISTS issue_catalog     CASCADE;
DROP TABLE IF EXISTS component_catalog CASCADE;
DROP TABLE IF EXISTS alert_response_link CASCADE;
DROP TABLE IF EXISTS alert_cause_link    CASCADE;
DROP TABLE IF EXISTS alert_event         CASCADE;
DROP TABLE IF EXISTS batch_station_status CASCADE;
DROP TABLE IF EXISTS sensor_3min  CASCADE;
DROP TABLE IF EXISTS sensor_1min  CASCADE;
DROP TABLE IF EXISTS response_catalog CASCADE;
DROP TABLE IF EXISTS cause_catalog    CASCADE;
DROP TABLE IF EXISTS batch_run        CASCADE;

-- ============================================================
-- ZONE 2: 批次生產
-- ============================================================
CREATE TABLE batch_run (
    batch_id    VARCHAR(32)  PRIMARY KEY,
    start_time  TIMESTAMPTZ  NOT NULL,
    ended_time  TIMESTAMPTZ,
    status      VARCHAR(16)  NOT NULL DEFAULT 'running'
                CHECK (status IN ('running','ok','warning','bad'))
);

CREATE INDEX idx_batch_start ON batch_run (start_time DESC);

-- ============================================================
-- CATALOG: 原因 & 解方（Zone 3/4 建立前需先存在）
-- ============================================================
CREATE TABLE cause_catalog (
    cause_id          VARCHAR(32)  PRIMARY KEY,
    category          VARCHAR(16)  NOT NULL
                      CHECK (category IN ('pdm_core','quality_fluid','protection','environment','process')),
    description_zh    TEXT         NOT NULL,
    typical_component VARCHAR(32),
    severity          VARCHAR(8)   NOT NULL CHECK (severity IN ('low','medium','high')),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE response_catalog (
    response_id           VARCHAR(32)  PRIMARY KEY,
    description_zh        TEXT         NOT NULL,
    downtime_estimate_min INT,
    skill_required        VARCHAR(16)  NOT NULL
                          CHECK (skill_required IN ('operator','technician','engineer')),
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE sensor_threshold (
    sensor_name    VARCHAR(64)  NOT NULL,
    threshold_type VARCHAR(16)  NOT NULL
                   CHECK (threshold_type IN ('warning','fault','warning_lo','warning_hi','fault_lo','fault_hi')),
    value          REAL         NOT NULL,
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by     VARCHAR(64),
    note           TEXT,
    PRIMARY KEY (sensor_name, threshold_type)
);

CREATE TABLE cause_response_map (
    cause_id    VARCHAR(32) NOT NULL REFERENCES cause_catalog(cause_id),
    response_id VARCHAR(32) NOT NULL REFERENCES response_catalog(response_id),
    priority    INT         NOT NULL DEFAULT 0,
    note        TEXT,
    PRIMARY KEY (cause_id, response_id)
);

-- ============================================================
-- ZONE 3: 感測資料
-- ============================================================
CREATE TABLE sensor_1min (
    row_id                   UUID         NOT NULL DEFAULT gen_random_uuid(),
    ts                       TIMESTAMPTZ  NOT NULL,
    batch_id                 VARCHAR(32)  NOT NULL REFERENCES batch_run(batch_id),
    station_id               VARCHAR(32)  NOT NULL,
    film_thickness_um        REAL,
    paint_flow_ml_min        REAL,
    nozzle_roll              REAL,
    filter_diff_pressure_bar REAL,
    filter_inflow_ml_min     REAL,
    filter_outflow_ml_min    REAL,
    pump_current_a           REAL,
    air_pressure_bar         REAL,
    spray_width_mm           REAL,
    servo_torque_load_pct    REAL,
    path_error_mm            REAL,
    vibration_g              REAL,
    tcp_x_mm                 REAL,
    tcp_y_mm                 REAL,
    tcp_z_mm                 REAL,
    speed_mm_s               REAL,
    data_quality_flag        VARCHAR(20) NOT NULL DEFAULT 'normal'
                              CHECK (data_quality_flag IN ('normal','interpolated')),
    PRIMARY KEY (row_id, ts)
);

CREATE INDEX idx_s1min_batch   ON sensor_1min (batch_id, ts DESC);
CREATE INDEX idx_s1min_station ON sensor_1min (station_id, ts DESC);
CREATE INDEX idx_s1min_pdm     ON sensor_1min (station_id, ts DESC)
    INCLUDE (filter_diff_pressure_bar, servo_torque_load_pct);

CREATE TABLE sensor_3min (
    row_id                UUID         NOT NULL DEFAULT gen_random_uuid(),
    ts                    TIMESTAMPTZ  NOT NULL,
    batch_id              VARCHAR(32)  REFERENCES batch_run(batch_id),
    station_id            VARCHAR(32)  NOT NULL,
    gearbox_temperature_c REAL,
    temperature_c         REAL,
    humidity_rh           REAL,
    data_quality_flag     VARCHAR(20) NOT NULL DEFAULT 'normal'
                          CHECK (data_quality_flag IN ('normal','interpolated')),
    PRIMARY KEY (row_id, ts)
);

CREATE INDEX idx_s3min_station ON sensor_3min (station_id, ts DESC);

-- ============================================================
-- ZONE 4: 批次站點詳細狀態
-- ============================================================
CREATE TABLE batch_station_status (
    batch_id                  VARCHAR(32)  NOT NULL REFERENCES batch_run(batch_id),
    station_id                VARCHAR(32)  NOT NULL,
    write_time                TIMESTAMPTZ  NOT NULL DEFAULT now(),
    robot_arm_state           VARCHAR(8)   CHECK (robot_arm_state   IN ('ok','warning','fault')),
    nozzle_state              VARCHAR(8)   CHECK (nozzle_state       IN ('ok','warning','fault')),
    filter_state              VARCHAR(8)   CHECK (filter_state       IN ('ok','warning','fault')),
    compressor_state          VARCHAR(8)   CHECK (compressor_state   IN ('ok','warning','fault')),
    spray_width_state         VARCHAR(8)   CHECK (spray_width_state  IN ('ok','warning','fault')),
    quality_state             VARCHAR(8)   CHECK (quality_state      IN ('ok','warning','fault')),
    robot_arm_response_id     VARCHAR(32)  REFERENCES response_catalog(response_id),
    nozzle_response_id        VARCHAR(32)  REFERENCES response_catalog(response_id),
    filter_response_id        VARCHAR(32)  REFERENCES response_catalog(response_id),
    compressor_response_id    VARCHAR(32)  REFERENCES response_catalog(response_id),
    spray_width_response_id   VARCHAR(32)  REFERENCES response_catalog(response_id),
    quality_response_id       VARCHAR(32)  REFERENCES response_catalog(response_id),
    PRIMARY KEY (batch_id, station_id)
);

-- ============================================================
-- ALERT & EVENT
-- ============================================================
CREATE TABLE alert_event (
    event_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id        VARCHAR(32)  NOT NULL REFERENCES batch_run(batch_id),
    station_id      VARCHAR(32)  NOT NULL,
    sensor_name     VARCHAR(64)  NOT NULL,
    measured_value  REAL         NOT NULL,
    state           VARCHAR(8)   NOT NULL CHECK (state IN ('warning','fault')),
    cause           VARCHAR(64),
    ts              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    message         TEXT,
    acknowledged_at TIMESTAMPTZ
);

CREATE INDEX idx_alert_station ON alert_event (station_id, ts DESC);
CREATE INDEX idx_alert_sensor  ON alert_event (sensor_name, ts DESC);
CREATE INDEX idx_alert_unacked ON alert_event (station_id, ts DESC)
    WHERE acknowledged_at IS NULL;

CREATE TABLE alert_cause_link (
    alert_id   UUID         NOT NULL REFERENCES alert_event(event_id),
    cause_id   VARCHAR(32)  NOT NULL REFERENCES cause_catalog(cause_id),
    is_primary BOOLEAN      NOT NULL DEFAULT FALSE,
    PRIMARY KEY (alert_id, cause_id)
);

CREATE TABLE alert_response_link (
    alert_id    UUID         NOT NULL REFERENCES alert_event(event_id),
    response_id VARCHAR(32)  NOT NULL REFERENCES response_catalog(response_id),
    executed_at TIMESTAMPTZ,
    operator_id VARCHAR(64),
    PRIMARY KEY (alert_id, response_id)
);

CREATE TABLE future_prediction_result (
    prediction_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id             VARCHAR(32)  NOT NULL REFERENCES batch_run(batch_id),
    station_id           VARCHAR(32),
    prediction_time      TIMESTAMPTZ  NOT NULL,
    predicted_ok_rate    REAL,
    predicted_ng_count   INT,
    quality_score        REAL,
    risk_level           VARCHAR(8)   CHECK (risk_level IN ('low','medium','high')),
    model_input_source   TEXT,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_future_prediction_time
    ON future_prediction_result (prediction_time DESC);
CREATE INDEX idx_future_prediction_station
    ON future_prediction_result (station_id, prediction_time DESC);

-- ============================================================
-- ZONE 5: 元件問題解方知識庫
-- ============================================================
CREATE TABLE component_catalog (
    component_id VARCHAR(32)  PRIMARY KEY,
    display_name VARCHAR(64)  NOT NULL,
    category     VARCHAR(16)  CHECK (category IN ('hardware','process_metric')),
    description  TEXT
);

CREATE TABLE issue_catalog (
    issue_id     VARCHAR(32)  PRIMARY KEY,
    display_name VARCHAR(128) NOT NULL,
    description  TEXT,
    severity     VARCHAR(8)   CHECK (severity IN ('low','medium','high'))
);

CREATE TABLE solution_catalog (
    solution_id           VARCHAR(32)  PRIMARY KEY,
    description           TEXT         NOT NULL,
    downtime_estimate_min INT,
    skill_required        VARCHAR(16)  CHECK (skill_required IN ('operator','technician','engineer'))
);

CREATE TABLE component_issue_solution_map (
    map_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    component_id      VARCHAR(32)  NOT NULL REFERENCES component_catalog(component_id),
    issue_id          VARCHAR(32)  NOT NULL REFERENCES issue_catalog(issue_id),
    solution_id       VARCHAR(32)  NOT NULL REFERENCES solution_catalog(solution_id),
    relevance_rank    INT,
    effectiveness_pct REAL         CHECK (effectiveness_pct BETWEEN 0 AND 100),
    note              TEXT,
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (component_id, issue_id, solution_id)
);

-- ============================================================
-- SEED DATA: cause_catalog
-- ============================================================
INSERT INTO cause_catalog (cause_id, category, description_zh, typical_component, severity) VALUES
  ('FILTER_CLOG',           'pdm_core',       '漆渣累積導致濾網阻塞，壓差持續上升',           'filter',     'medium'),
  ('SERVO_WEAR',            'pdm_core',       '減速機磨損導致伺服負載升高',                    'servo',      'medium'),
  ('PUMP_DEGRADATION',      'pdm_core',       '幫浦老化導致流量不穩定',                        'pump',       'medium'),
  ('NOZZLE_CLOG',           'quality_fluid',  '塗料殘留堵塞噴嘴孔徑，噴幅變窄',               'nozzle',     'high'),
  ('NOZZLE_WEAR',           'quality_fluid',  '噴嘴孔徑磨損擴大，影響霧化品質',               'nozzle',     'medium'),
  ('FLOW_UNSTABLE',         'quality_fluid',  '流量波動導致膜厚不均勻',                        'pump',       'medium'),
  ('THICKNESS_DRIFT',       'quality_fluid',  '膜厚漂移超出管制範圍',                          'process',    'medium'),
  ('VIBRATION_HIGH',        'protection',     '振動加速度超標，疑似碰撞或軸承鬆動',            'robot',      'high'),
  ('PATH_ERROR_HIGH',       'protection',     '軌跡追蹤誤差過大，需重新校正 TCP',              'robot',      'high'),
  ('GEARBOX_OVERHEAT',      'protection',     '減速機溫度過高，需強制降速',                    'gearbox',    'high'),
  ('AIR_PRESSURE_UNSTABLE', 'quality_fluid',  '空壓機壓力不穩，影響霧化品質',                  'compressor', 'medium'),
  ('AIR_MOISTURE_HIGH',     'quality_fluid',  '壓縮空氣含水量過高，影響附著性',                'compressor', 'medium'),
  ('ENV_TEMP_OUT',          'environment',    '環境溫度超出最佳噴塗範圍（22~26°C）',           'chamber',    'medium'),
  ('ENV_HUMID_OUT',         'environment',    '環境濕度超出最佳範圍（50~60%RH）',              'chamber',    'medium'),
  ('FILTER_DAMAGE',         'pdm_core',       '濾網破損導致洩漏，進出流量異常',                'filter',     'high'),
  ('MANUAL_STOP',           'process',        '操作員手動緊急停機',                            NULL,         'low'),
  ('SCHEDULED_MAINT',       'process',        '計畫性預防保養停機',                            NULL,         'low');

-- ============================================================
-- SEED DATA: response_catalog
-- ============================================================
INSERT INTO response_catalog (response_id, description_zh, downtime_estimate_min, skill_required) VALUES
  ('REPLACE_FILTER',           '更換濾網（壓差超過門檻觸發）',              30,  'operator'),
  ('LUBRICATE_SERVO',          '定期潤滑伺服馬達與減速機',                  20,  'technician'),
  ('REPLACE_SERVO',            '更換伺服馬達或減速機總成',                  120, 'engineer'),
  ('RECALIBRATE_TCP',          '重新校正工具中心點（TCP）',                  45,  'technician'),
  ('TIGHTEN_BASE',             '緊固基座螺栓，檢查並更換防震墊',            15,  'operator'),
  ('CLEAN_NOZZLE',             '拆卸清洗噴嘴，去除漆渣結塊',               20,  'operator'),
  ('REPLACE_NOZZLE',           '更換磨損噴嘴',                              25,  'technician'),
  ('RECALIBRATE_NOZZLE_ANGLE', '重新校正噴嘴翻滾角（roll angle）',          30,  'technician'),
  ('BACKWASH_FILTER',          '反洗濾網管路，臨時恢復流量',               20,  'technician'),
  ('INSTALL_DRYER',            '加裝或更換空氣乾燥機與油水分離器',          180, 'engineer'),
  ('DRAIN_CONDENSATE',         '排放壓縮空氣系統冷凝水',                    5,   'operator'),
  ('CALIBRATE_PRESSURE_VALVE', '校正壓力調節閥，恢復穩定壓力',              30,  'technician'),
  ('ADJUST_TCP_Z',             '校正噴嘴與工件距離（TCP Z 軸偏移）',        20,  'technician'),
  ('ADJUST_FLOW_PRESSURE',     '調整塗料流量與空壓比例至目標值',            10,  'operator'),
  ('CCD_PATH_CORRECTION',      '啟用 CCD 視覺系統進行即時路徑補正',          0,   'engineer'),
  ('ADJUST_SPEED_FLOW',        '調整噴塗移動速度與塗料流量',                10,  'operator'),
  ('CALIBRATE_ENV_CONTROL',    '校正噴塗室溫濕度控制系統',                  60,  'engineer'),
  ('FORCED_COOLDOWN',          '強制降速並加強散熱，等待減速機降溫',        30,  'operator'),
  ('EMERGENCY_STOP',           '緊急停機，排查異常振動源',                  60,  'engineer');

-- ============================================================
-- SEED DATA: component_catalog
-- ============================================================
INSERT INTO component_catalog (component_id, display_name, category, description) VALUES
  ('ROBOT_ARM',      '機器手臂',     'hardware',       '六軸工業機械臂，負責噴塗路徑追蹤，伺服馬達與減速機為主要 PdM 監控點'),
  ('NOZZLE',         '噴嘴',         'hardware',       '塗料霧化噴出元件，易因漆渣堵塞或磨損影響噴幅品質'),
  ('FILTER',         '濾網',         'hardware',       '塗料供給管路濾網，壓差為 PdM 核心 A 指標'),
  ('AIR_COMPRESSOR', '空壓機',       'hardware',       '提供噴塗霧化所需壓縮空氣，壓力穩定性影響霧化品質'),
  ('SPRAY_WIDTH',    '噴幅',         'process_metric', 'CCD 視覺系統量測的實際噴塗寬度，反映噴嘴與機械狀態'),
  ('QUALITY',        '品質（膜厚）', 'process_metric', '最終品質 Y 值（film_thickness_um），是所有元件狀態的綜合反映');

-- ============================================================
-- SEED DATA: issue_catalog
-- ============================================================
INSERT INTO issue_catalog (issue_id, display_name, description, severity) VALUES
  ('SERVO_OVERLOAD',        '伺服馬達負載過高/磨損',          '減速機磨損導致伺服馬達電流與扭矩負載上升，長期超標將導致故障', 'medium'),
  ('PATH_ERROR_HIGH',       '軌跡追蹤誤差過大（TCP 偏移）',   '機械背隙增大或 TCP 校正偏移導致路徑誤差超過 0.5mm',          'high'),
  ('VIBRATION_HIGH',        '異常振動（碰撞/軸承鬆動）',      '振動加速度超過 1.5G，可能為碰撞、螺栓鬆動或軸承磨損',       'high'),
  ('GEARBOX_OVERHEAT',      '減速機過熱',                      '減速機溫度持續超過 55°C，需加強散熱或潤滑',                  'high'),
  ('JOINT_BACKLASH',        '關節背隙增大',                    '長期使用後減速機背隙增大，影響定位精度',                     'medium'),
  ('NOZZLE_CLOG',           '噴嘴堵塞（漆渣累積）',           '塗料殘留在噴嘴孔徑累積，導致噴幅縮小或不均',                'high'),
  ('NOZZLE_WEAR',           '噴嘴孔徑磨損擴大',               '長期使用後噴嘴孔徑磨損，導致噴幅過寬或霧化不良',            'medium'),
  ('NOZZLE_ANGLE_DRIFT',    '噴嘴翻滾角偏移',                  '震動或撞擊導致噴嘴安裝角度偏移',                            'medium'),
  ('FILTER_CLOG',           '濾網堵塞（壓差持續上升）',        '漆渣累積導致濾網阻塞，壓差持續上升超過 0.30 bar',           'medium'),
  ('FILTER_DAMAGE',         '濾網破損洩漏',                    '濾網本體破損導致進出液流量不平衡',                           'high'),
  ('FLOW_IMBALANCE',        '進出液流量不平衡',                '濾網或管路問題導致進出流量差異超過允許範圍',                 'medium'),
  ('AIR_PRESSURE_UNSTABLE', '空氣壓力不穩/不足',               '壓力波動超過 ±10%，影響塗料霧化品質',                      'medium'),
  ('AIR_MOISTURE_HIGH',     '壓縮空氣含水量過高',              '冷凝水未排放或乾燥機失效，油漆附著不良',                    'medium'),
  ('AIR_OIL_CONTAMINATION', '油氣混入污染',                    '壓縮機潤滑油進入氣管，污染塗料',                           'high'),
  ('AIR_LEAKAGE',           '漏氣（管路接頭）',                '管路接頭鬆脫或老化導致氣壓下降',                            'medium'),
  ('SPRAY_WIDTH_DEVIATION', '噴幅偏離基準值',                  '實際噴幅與目標值偏差超過 ±10mm',                           'medium'),
  ('SPRAY_WIDTH_UNSTABLE',  '噴幅不均勻（批次內波動）',        '同批次內噴幅標準差過大，影響覆蓋均勻性',                    'medium'),
  ('FILM_THICKNESS_OOC',    '膜厚超出規格範圍',                '膜厚低於 14.5μm 或高於 15.5μm（warning），超過 14.0/16.0 為 fault', 'high'),
  ('FILM_THICKNESS_VARIATION', '膜厚不均勻（批次標準差過高）', '同批次膜厚標準差超過 0.3μm，表示噴塗不穩定',               'medium'),
  ('SURFACE_DEFECT',        '表面缺陷（橘皮/流掛/氣泡）',     '塗層表面出現橘皮、流掛或氣泡等外觀缺陷',                    'high');

-- ============================================================
-- SEED DATA: solution_catalog
-- ============================================================
INSERT INTO solution_catalog (solution_id, description, downtime_estimate_min, skill_required) VALUES
  ('LUBRICATE_SERVO',          '定期潤滑伺服馬達與減速機',                  20,  'technician'),
  ('REPLACE_SERVO',            '更換伺服馬達或減速機總成',                  120, 'engineer'),
  ('RECALIBRATE_TCP',          '重新校正工具中心點（TCP）',                  45,  'technician'),
  ('TIGHTEN_BASE',             '緊固基座螺栓，檢查並更換防震墊',            15,  'operator'),
  ('FORCED_COOLDOWN',          '強制降速並加強散熱，等待降溫',              30,  'operator'),
  ('CLEAN_NOZZLE',             '拆卸清洗噴嘴，去除漆渣結塊',               20,  'operator'),
  ('REPLACE_NOZZLE',           '更換磨損噴嘴',                              25,  'technician'),
  ('RECALIBRATE_NOZZLE_ANGLE', '重新校正噴嘴翻滾角',                        30,  'technician'),
  ('REPLACE_FILTER',           '更換濾網',                                  30,  'operator'),
  ('BACKWASH_FILTER',          '反洗濾網管路',                              20,  'technician'),
  ('INSTALL_DRYER',            '加裝或更換空氣乾燥機與油水分離器',          180, 'engineer'),
  ('DRAIN_CONDENSATE',         '排放壓縮空氣冷凝水',                         5,  'operator'),
  ('CALIBRATE_PRESSURE_VALVE', '校正壓力調節閥',                            30,  'technician'),
  ('ADJUST_TCP_Z',             '校正噴嘴與工件 TCP Z 軸距離',               20,  'technician'),
  ('ADJUST_FLOW_PRESSURE',     '調整塗料流量與空壓比例',                    10,  'operator'),
  ('CCD_PATH_CORRECTION',      '啟用 CCD 視覺即時路徑補正',                  0,  'engineer'),
  ('ADJUST_SPEED_FLOW',        '調整噴塗速度與流量',                        10,  'operator'),
  ('CALIBRATE_ENV_CONTROL',    '校正環境溫濕度控制系統',                    60,  'engineer');

-- ============================================================
-- SEED DATA: component_issue_solution_map
-- ============================================================
INSERT INTO component_issue_solution_map (component_id, issue_id, solution_id, relevance_rank, effectiveness_pct) VALUES
  ('ROBOT_ARM', 'SERVO_OVERLOAD',        'LUBRICATE_SERVO',          1, 75.0),
  ('ROBOT_ARM', 'SERVO_OVERLOAD',        'REPLACE_SERVO',            2, 95.0),
  ('ROBOT_ARM', 'PATH_ERROR_HIGH',       'RECALIBRATE_TCP',          1, 90.0),
  ('ROBOT_ARM', 'VIBRATION_HIGH',        'TIGHTEN_BASE',             1, 70.0),
  ('ROBOT_ARM', 'GEARBOX_OVERHEAT',      'FORCED_COOLDOWN',          1, 85.0),
  ('ROBOT_ARM', 'GEARBOX_OVERHEAT',      'LUBRICATE_SERVO',          2, 60.0),
  ('ROBOT_ARM', 'JOINT_BACKLASH',        'REPLACE_SERVO',            1, 90.0),
  ('NOZZLE',    'NOZZLE_CLOG',           'CLEAN_NOZZLE',             1, 85.0),
  ('NOZZLE',    'NOZZLE_CLOG',           'REPLACE_NOZZLE',           2, 95.0),
  ('NOZZLE',    'NOZZLE_WEAR',           'REPLACE_NOZZLE',           1, 95.0),
  ('NOZZLE',    'NOZZLE_ANGLE_DRIFT',    'RECALIBRATE_NOZZLE_ANGLE', 1, 90.0),
  ('FILTER',    'FILTER_CLOG',           'REPLACE_FILTER',           1, 95.0),
  ('FILTER',    'FILTER_CLOG',           'BACKWASH_FILTER',          2, 50.0),
  ('FILTER',    'FILTER_DAMAGE',         'REPLACE_FILTER',           1, 99.0),
  ('FILTER',    'FLOW_IMBALANCE',        'REPLACE_FILTER',           1, 80.0),
  ('AIR_COMPRESSOR', 'AIR_PRESSURE_UNSTABLE', 'CALIBRATE_PRESSURE_VALVE', 1, 85.0),
  ('AIR_COMPRESSOR', 'AIR_MOISTURE_HIGH',     'INSTALL_DRYER',       1, 90.0),
  ('AIR_COMPRESSOR', 'AIR_MOISTURE_HIGH',     'DRAIN_CONDENSATE',    2, 60.0),
  ('AIR_COMPRESSOR', 'AIR_LEAKAGE',           'CALIBRATE_PRESSURE_VALVE', 1, 70.0),
  ('SPRAY_WIDTH', 'SPRAY_WIDTH_DEVIATION', 'ADJUST_TCP_Z',           1, 80.0),
  ('SPRAY_WIDTH', 'SPRAY_WIDTH_DEVIATION', 'ADJUST_FLOW_PRESSURE',   2, 65.0),
  ('SPRAY_WIDTH', 'SPRAY_WIDTH_DEVIATION', 'REPLACE_NOZZLE',         3, 75.0),
  ('SPRAY_WIDTH', 'SPRAY_WIDTH_UNSTABLE',  'CCD_PATH_CORRECTION',    1, 70.0),
  ('QUALITY',   'FILM_THICKNESS_OOC',       'ADJUST_SPEED_FLOW',     1, 75.0),
  ('QUALITY',   'FILM_THICKNESS_OOC',       'CALIBRATE_ENV_CONTROL', 2, 60.0),
  ('QUALITY',   'FILM_THICKNESS_VARIATION', 'ADJUST_FLOW_PRESSURE',  1, 70.0),
  ('QUALITY',   'SURFACE_DEFECT',           'ADJUST_FLOW_PRESSURE',  1, 65.0),
  ('QUALITY',   'SURFACE_DEFECT',           'CALIBRATE_ENV_CONTROL', 2, 55.0);

-- ============================================================
-- SEED DATA: sensor_threshold
-- ============================================================
INSERT INTO sensor_threshold (sensor_name, threshold_type, value, updated_by, note) VALUES
  ('filter_diff_pressure_bar', 'warning',    0.30, 'setup_db', 'Filter clog warning threshold'),
  ('filter_diff_pressure_bar', 'fault',      0.50, 'setup_db', 'Filter clog fault threshold'),
  ('servo_torque_load_pct',    'warning',   60.00, 'setup_db', 'Robot arm load warning threshold'),
  ('servo_torque_load_pct',    'fault',     80.00, 'setup_db', 'Robot arm load fault threshold'),
  ('film_thickness_um',        'warning_lo',14.50, 'setup_db', 'Film thickness lower warning'),
  ('film_thickness_um',        'warning_hi',15.50, 'setup_db', 'Film thickness upper warning'),
  ('film_thickness_um',        'fault_lo',  14.00, 'setup_db', 'Film thickness lower fault'),
  ('film_thickness_um',        'fault_hi',  16.00, 'setup_db', 'Film thickness upper fault'),
  ('air_pressure_bar',         'warning_lo', 2.70, 'setup_db', 'Air pressure lower warning aligned with generated data'),
  ('air_pressure_bar',         'warning_hi', 3.80, 'setup_db', 'Air pressure upper warning aligned with generated data'),
  ('spray_width_mm',           'warning_lo',60.00, 'setup_db', 'Spray width lower warning aligned with Station_3'),
  ('spray_width_mm',           'warning_hi',140.0, 'setup_db', 'Spray width upper warning aligned with Station_1');

-- ============================================================
-- SEED DATA: cause_response_map
-- ============================================================
INSERT INTO cause_response_map (cause_id, response_id, priority, note) VALUES
  ('FILTER_CLOG',           'REPLACE_FILTER',            1, 'Primary response for clogged filter'),
  ('FILTER_CLOG',           'BACKWASH_FILTER',           2, 'Fallback response for clogged filter'),
  ('FILTER_DAMAGE',         'REPLACE_FILTER',            1, 'Primary response for damaged filter'),
  ('SERVO_WEAR',            'LUBRICATE_SERVO',           1, 'Primary response for servo wear'),
  ('SERVO_WEAR',            'REPLACE_SERVO',             2, 'Escalation for servo wear'),
  ('NOZZLE_CLOG',           'CLEAN_NOZZLE',              1, 'Primary response for nozzle clog'),
  ('NOZZLE_CLOG',           'REPLACE_NOZZLE',            2, 'Escalation for nozzle clog'),
  ('NOZZLE_WEAR',           'REPLACE_NOZZLE',            1, 'Primary response for nozzle wear'),
  ('FLOW_UNSTABLE',         'ADJUST_FLOW_PRESSURE',      1, 'Primary response for unstable flow'),
  ('THICKNESS_DRIFT',       'ADJUST_SPEED_FLOW',         1, 'Primary response for thickness drift'),
  ('VIBRATION_HIGH',        'TIGHTEN_BASE',              1, 'Primary response for high vibration'),
  ('PATH_ERROR_HIGH',       'RECALIBRATE_TCP',           1, 'Primary response for path error'),
  ('GEARBOX_OVERHEAT',      'FORCED_COOLDOWN',           1, 'Primary response for gearbox overheat'),
  ('AIR_PRESSURE_UNSTABLE', 'CALIBRATE_PRESSURE_VALVE',  1, 'Primary response for unstable pressure'),
  ('AIR_MOISTURE_HIGH',     'DRAIN_CONDENSATE',          1, 'Quick response for air moisture'),
  ('AIR_MOISTURE_HIGH',     'INSTALL_DRYER',             2, 'Engineering response for recurring moisture'),
  ('ENV_TEMP_OUT',          'CALIBRATE_ENV_CONTROL',     1, 'Primary response for environment temperature'),
  ('ENV_HUMID_OUT',         'CALIBRATE_ENV_CONTROL',     1, 'Primary response for environment humidity');

-- ============================================================
-- 0620ver_1 HOTFIX: align runtime mapping/catalog/thresholds
-- Purpose:
--   1) Keep API rule engine stable by preserving JSON-based thresholds.
--   2) Make DB seed complete when others rebuild PostgreSQL from scratch.
--   3) Avoid alert write-back ForeignKeyViolation from sensor_event_mapping.json.
-- ============================================================

INSERT INTO cause_catalog (cause_id, category, description_zh, typical_component, severity) VALUES
  ('FLOW_IMBALANCE',        'quality_fluid', '進出液流量不平衡，可能由濾網或管路阻塞造成',        'filter',      'medium'),
  ('NOZZLE_ANGLE_DRIFT',    'quality_fluid', '噴嘴安裝角度偏移，造成噴幅或膜厚不穩',              'nozzle',      'medium'),
  ('SPRAY_WIDTH_DEVIATION', 'quality_fluid', '噴幅偏離各站基準值，可能影響覆蓋範圍',              'spray_width', 'medium'),
  ('SPRAY_WIDTH_UNSTABLE',  'quality_fluid', '噴幅波動過大，可能造成覆蓋不均',                    'spray_width', 'medium'),
  ('FILM_THICKNESS_OOC',    'quality_fluid', '膜厚超出規格範圍',                                  'quality',     'high'),
  ('FILM_THICKNESS_VARIATION','quality_fluid','膜厚波動過大，疑似噴塗不穩定',                     'quality',     'medium')
ON CONFLICT (cause_id) DO UPDATE SET
  category = EXCLUDED.category,
  description_zh = EXCLUDED.description_zh,
  typical_component = EXCLUDED.typical_component,
  severity = EXCLUDED.severity;

INSERT INTO response_catalog (response_id, description_zh, downtime_estimate_min, skill_required) VALUES
  ('CHECK_FILTER',          '檢查濾網壓差與管路流量，必要時更換濾網',          10, 'operator'),
  ('CHECK_SERVO',           '檢查機械手臂伺服負載、減速機與潤滑狀態',          20, 'technician'),
  ('INSPECT_NOZZLE',        '檢查噴嘴堵塞、磨耗與安裝角度',                    15, 'operator'),
  ('REDUCE_SPEED',          '暫時降低噴塗速度以降低風險',                       5, 'operator'),
  ('ADJUST_FILM_THICKNESS', '調整膜厚參數，包含速度、流量與空壓比例',          10, 'operator')
ON CONFLICT (response_id) DO UPDATE SET
  description_zh = EXCLUDED.description_zh,
  downtime_estimate_min = EXCLUDED.downtime_estimate_min,
  skill_required = EXCLUDED.skill_required;

INSERT INTO cause_response_map (cause_id, response_id, priority, note) VALUES
  ('FLOW_IMBALANCE',        'CHECK_FILTER',          1, 'Check filter and pipe flow first'),
  ('FLOW_IMBALANCE',        'REPLACE_FILTER',        2, 'Replace filter if imbalance persists'),
  ('NOZZLE_ANGLE_DRIFT',    'INSPECT_NOZZLE',        1, 'Inspect nozzle angle and mounting'),
  ('NOZZLE_ANGLE_DRIFT',    'RECALIBRATE_NOZZLE_ANGLE', 2, 'Recalibrate nozzle roll angle'),
  ('SPRAY_WIDTH_DEVIATION', 'ADJUST_TCP_Z',          1, 'Correct nozzle-to-workpiece distance'),
  ('SPRAY_WIDTH_DEVIATION', 'ADJUST_FLOW_PRESSURE',  2, 'Tune flow and atomizing pressure'),
  ('SPRAY_WIDTH_DEVIATION', 'REPLACE_NOZZLE',        3, 'Replace nozzle if deviation is caused by clog/wear'),
  ('SPRAY_WIDTH_UNSTABLE',  'CCD_PATH_CORRECTION',   1, 'Use CCD path correction for unstable width'),
  ('FILM_THICKNESS_OOC',    'ADJUST_FILM_THICKNESS', 1, 'Adjust film thickness process parameters'),
  ('FILM_THICKNESS_OOC',    'ADJUST_SPEED_FLOW',     2, 'Tune speed and flow'),
  ('FILM_THICKNESS_VARIATION','ADJUST_FLOW_PRESSURE',1, 'Tune flow/pressure for thickness variation')
ON CONFLICT (cause_id, response_id) DO UPDATE SET
  priority = EXCLUDED.priority,
  note = EXCLUDED.note;

-- Keep DB sensor_threshold aligned with runtime JSON rule file used by API.
INSERT INTO sensor_threshold (sensor_name, threshold_type, value, updated_by, note) VALUES
  ('air_pressure_bar', 'fault_lo', 2.50, '0620ver_1', 'Hard lower fault for generated air pressure range'),
  ('air_pressure_bar', 'fault_hi', 4.00, '0620ver_1', 'Hard upper fault for generated air pressure range'),
  ('spray_width_mm',   'fault_lo', 60.00, '0620ver_1', 'Hard lower fault compatible with Station_3 baseline'),
  ('spray_width_mm',   'fault_hi', 140.0, '0620ver_1', 'Hard upper fault compatible with Station_1 baseline')
ON CONFLICT (sensor_name, threshold_type) DO UPDATE SET
  value = EXCLUDED.value,
  updated_by = EXCLUDED.updated_by,
  note = EXCLUDED.note,
  updated_at = now();

-- ============================================================
-- 0620ver_1 HOTFIX: generate_data.py requires sensor_1hour
-- ============================================================
CREATE TABLE IF NOT EXISTS sensor_1hour (
    row_id                UUID         NOT NULL DEFAULT gen_random_uuid(),
    ts                    TIMESTAMPTZ  NOT NULL,
    station_id            VARCHAR(32)  NOT NULL,
    gearbox_temperature_c REAL,
    temperature_c         REAL,
    humidity_rh           REAL,
    data_quality_flag     VARCHAR(20) NOT NULL DEFAULT 'normal'
                          CHECK (data_quality_flag IN ('normal','interpolated')),
    PRIMARY KEY (row_id, ts)
);

CREATE INDEX IF NOT EXISTS idx_s1hour_station
ON sensor_1hour (station_id, ts DESC);
