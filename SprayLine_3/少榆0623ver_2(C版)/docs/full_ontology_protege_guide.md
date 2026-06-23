# SprayLine Full Ontology for Protégé

請用 Protégé 開啟：

```text
ontology/sprayline_full_ontology.ttl
```

建議在 Protégé 的 Classes 與 Individuals 檢查：

```text
Classes:
SprayLineSystem, Station, Component, SensorMetric, SensorThreshold, ThresholdSet, State, Cause, ResponseAction, InferenceRule

Individuals:
SprayLine_A, Station_1, AirCompressor, Metric_air_pressure_bar, Threshold_air_pressure_bar, Cause_AIR_PRESSURE_UNSTABLE, Action_CALIBRATE_PRESSURE_VALVE
```

OntoGraf 建議點選 `SprayLine_A` 或 `AirCompressor`，可以看到：

```text
SprayLine_A → Station → Component → SensorMetric → SensorThreshold → State / Cause / ResponseAction
```
