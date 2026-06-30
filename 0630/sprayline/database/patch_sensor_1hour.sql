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
