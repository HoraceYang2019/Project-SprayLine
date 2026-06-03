<!--
檔案備註：
欄位目錄閱讀版：與 field_catalog.csv 內容一致，但用 Markdown 表格方便人工閱讀。

資料夾流程定位：流程 Step 2：把 UI 需要的資料整理成正式欄位目錄。
-->

# Field Catalog

此表整理統計 service contract 的核心欄位。所有數值欄位皆為動態產生，不代表固定假資料。

| section | field_key | label_zh | label_en | unit | source_service | ui_position | required | value_policy | ontology_class | ontology_property |
|:--------------|:--------------------|:-------------|:---------------------|:-------|:------------------------------|:-------------------|:-----------|:------------------|:----------------------|:--------------------|
| summary | total_station_count | 總站數 | Total Stations | count | statistics_service | summary_card | true | dynamic | LineSummary | totalStationCount |
| summary | normal_count | 正常站數 | Normal | count | statistics_service | summary_card | true | dynamic | LineSummary | normalCount |
| summary | warning_count | 注意站數 | Warning | count | statistics_service | summary_card | true | dynamic | LineSummary | warningCount |
| summary | predict_risk_count | 預測風險站數 | Predict Risk | count | statistics_service_with_threshold_config | summary_card | true | dynamic | LineSummary | predictRiskCount |

| station | line_id | 產線編號 | Line ID | | configuration_or_upstream | station_card | true | identifier | StationSnapshot | lineId |
| station | station_name_zh | 站別中文名稱 | Station zh label | | configuration | station_card | true | label | StationSnapshot | stationNameZh |
| station | station_name_en | 站別英文名稱 | Station en label | | configuration | station_card | true | label | StationSnapshot | stationNameEn |
| station | chamber_id | 腔體編號 | Chamber ID | | configuration_or_upstream | station_card | false | identifier | Chamber | chamberId |
| station | overall_state | 站別狀態 | Station State | | statistics_service_with_threshold_config | status_badge | true | dynamic | StationSnapshot | overallState |
| station | status_badge_text | 狀態顯示文字 | Status Badge Text | | statistics_service_with_threshold_config | status_badge | true | dynamic_label | StationSnapshot | statusBadgeText |

| component | component_key | 零件代碼 | Component Key | | service_contract | component_overview | true | identifier | ComponentOverviewItem | componentKey |
| component | component_name_zh | 零件中文名稱 | Component zh label | | service_contract | component_overview | true | label | ComponentOverviewItem | componentNameZh |
| component | component_name_en | 零件英文名稱 | Component en label | | service_contract | component_overview | true | label | ComponentOverviewItem | componentNameEn |
| component | level | 零件狀態等級 | Component Level | | statistics_service_with_threshold_config | component_overview | true | dynamic | ComponentOverviewItem | componentLevel |
| component | level_text | 零件狀態文字 | Component Level Text | | statistics_service_with_threshold_config | component_overview | true | dynamic_label | ComponentOverviewItem | componentLevelText |

| part_status | arm_status | 機械手臂狀態 | Robot Arm Status | | current_or_future_service | part_status | true | dynamic | PartStatus | armStatus |
| part_status | availability_pct | 可用度 | Availability | % | statistics_service | part_status | true | dynamic_metric | AvailabilityMetric | metricValue |
| part_status | nozzle_status | 噴嘴狀態 | Nozzle Status | | current_or_future_service | part_status | true | dynamic | PartStatus | nozzleStatus |
| part_status | clog_rate_pct | 堵塞率 | Clog Rate | % | statistics_service | part_status | true | dynamic_metric | ClogRateMetric | metricValue |
| part_status | air_compressor_status | 空壓機狀態 | Air Compressor Status | | current_or_future_service | part_status | true | dynamic | PartStatus | airCompressorStatus |
| part_status | pressure_bar | 壓力 | Pressure | bar | statistics_or_current_service | part_status | true | dynamic_metric | PressureMetric | metricValue |
| part_status | air_valve_status | 氣閥狀態 | Air Valve Status | | current_or_future_service | part_status | true | dynamic | PartStatus | airValveStatus |
| part_status | flow_rate_ml_min | 流量 | Flow Rate | ml/min | statistics_or_current_service | part_status | true | dynamic_metric | FlowRateMetric | metricValue |
| part_status | filter_mesh_status | 濾網狀態 | Filter Mesh Status | | current_or_future_service | part_status | true | dynamic | PartStatus | filterMeshStatus |
| part_status | maintainability_pct | 維護性 | Maintainability | % | statistics_service | part_status | true | dynamic_metric | MaintainabilityMetric | metricValue |
| part_status | quality_score_pct | 品質分數 | Quality Score | % | statistics_service | part_status | true | dynamic_metric | QualityMetric | metricValue |
| part_status | quality_subtext | 品質小字說明 | Quality Subtext | | ui_label_or_service | part_status | true | display_label | PartStatus | qualitySubtext |
| part_status | risk_text | 風險文字 | Risk Text | | statistics_service_with_threshold_config | part_status | true | dynamic_label | RiskAssessment | riskText |

| process | recipe_name | 配方 | Recipe | | current_service_or_config | process_parameters | true | dynamic_or_config | ProcessParameters | recipeName |
| process | temperature_c | 溫度 | Temperature | °C | current_or_statistics_service | process_parameters | true | dynamic_metric | TemperatureMetric | metricValue |
| process | utilization_pct | 利用率 | Utilization | % | statistics_service | process_parameters | true | dynamic_metric | UtilizationMetric | metricValue |
| process | cycle_time_sec | 週期時間 | Cycle Time | sec | statistics_service | process_parameters | true | dynamic_metric | CycleTimeMetric | metricValue |

| viewer_query | mode | 模式 | Mode | | ui | time_series_viewer | true | query | TimeSeriesViewerQuery | mode |
| viewer_query | window_type | 視窗類型 | Window Type | | ui_or_service_config | time_series_viewer | true | query | StatisticsWindow | windowType |
| viewer_query | slider_value | 時間軸位置 | Slider Value | | ui | time_series_viewer | true | query | TimeSeriesViewerQuery | sliderValue |
| viewer_output | display_label | 顯示標籤 | Display Label | | statistics_service | time_series_viewer | true | dynamic_label | ViewerState | displayLabel |
| viewer_output | summary_text | 摘要文字 | Summary Text | | statistics_service | time_series_viewer | true | dynamic_label | Narrative | summaryText |
| viewer_output | series | 趨勢序列 | Trend Series | | statistics_service | time_series_viewer | false | dynamic_series | MetricSeries | hasSeries |
