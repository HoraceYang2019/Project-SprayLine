# Ontology Dashboard v15 Hierarchy Check

本檔案說明 `0602ver_3` 對 `0602ver_2` 的 ontology 修正。

## 問題來源

`0602ver_2` 的 ontology 有宣告 classes，但沒有建立 `rdfs:subClassOf` class hierarchy。  
因此在 Protégé 的 Class Hierarchy 中，`Nozzle`、`FilterMesh`、`AirCompressor`、`RobotArm` 等 class 會全部直接顯示在 `owl:Thing` 底下。

## 修正方式

本版新增一個總根類別：

```text
SprayLineProjectConcept
```

並將 class hierarchy 重整為：

```text
SprayLineProjectConcept
├─ SprayLine
│  └─ ProductionLine
├─ PhysicalAsset
│  ├─ RobotArm
│  ├─ Nozzle
│  ├─ AirCompressor
│  ├─ FilterMesh
│  ├─ QualityModule
│  └─ Oven
├─ UIComponent
│  ├─ DashboardV15Interface
│  ├─ EngineerMonitoringTab
│  ├─ ProductionManagementTab
│  └─ Drawer
├─ ServiceFunction
│  ├─ DashboardService
│  ├─ RuntimeService
│  ├─ DiagnosisService
│  ├─ TrendService
│  ├─ KPIService
│  ├─ ChartService
│  ├─ BatchService
│  ├─ AlertService
│  ├─ PredictionAccuracyService
│  ├─ RiskService
│  ├─ FeatureService
│  ├─ PredictionService
│  ├─ OmniverseService
│  ├─ DataImportService
│  ├─ ThresholdImportService
│  ├─ TTLImportService
│  ├─ ProductionHistoryService
│  └─ QCService
├─ DatabaseConcept
│  ├─ DatabaseZone
│  └─ DatabaseTable
│     ├─ ThresholdTable
│     └─ Hypertable
├─ DataResource
│  ├─ Metric
│  │  ├─ RuntimeMetric
│  │  └─ SprayWidth
│  ├─ RuntimeSignal
│  ├─ RuntimeReference
│  ├─ DiagnosisResult
│  ├─ AlertLog
│  ├─ MLPredictionResult
│  └─ ResponseSchema
└─ Infrastructure
   ├─ APIGateway
   ├─ RESTEndpoint
   └─ RedisCache
```

## 檢查結果

```text
SprayLine_service_extension.ttl: classes=53, classes_without_parent_except_root=0
  Nozzle subClassOf PhysicalAsset: OK
  FilterMesh subClassOf PhysicalAsset: OK
  AirCompressor subClassOf PhysicalAsset: OK
  RobotArm subClassOf PhysicalAsset: OK
  Oven subClassOf PhysicalAsset: OK
  SprayWidth subClassOf Metric: OK
  DashboardService subClassOf ServiceFunction: OK
  RuntimeService subClassOf ServiceFunction: OK
  RiskService subClassOf ServiceFunction: OK
  RESTEndpoint subClassOf Infrastructure: OK
  DatabaseTable subClassOf DatabaseConcept: OK
  ThresholdTable subClassOf DatabaseTable: OK
  ResponseSchema subClassOf DataResource: OK
SprayLine_service_extension_chinese.ttl: classes=53, classes_without_parent_except_root=0
  Nozzle subClassOf PhysicalAsset: OK
  FilterMesh subClassOf PhysicalAsset: OK
  AirCompressor subClassOf PhysicalAsset: OK
  RobotArm subClassOf PhysicalAsset: OK
  Oven subClassOf PhysicalAsset: OK
  SprayWidth subClassOf Metric: OK
  DashboardService subClassOf ServiceFunction: OK
  RuntimeService subClassOf ServiceFunction: OK
  RiskService subClassOf ServiceFunction: OK
  RESTEndpoint subClassOf Infrastructure: OK
  DatabaseTable subClassOf DatabaseConcept: OK
  ThresholdTable subClassOf DatabaseTable: OK
  ResponseSchema subClassOf DataResource: OK
SprayLine_service_extension_english.ttl: classes=53, classes_without_parent_except_root=0
  Nozzle subClassOf PhysicalAsset: OK
  FilterMesh subClassOf PhysicalAsset: OK
  AirCompressor subClassOf PhysicalAsset: OK
  RobotArm subClassOf PhysicalAsset: OK
  Oven subClassOf PhysicalAsset: OK
  SprayWidth subClassOf Metric: OK
  DashboardService subClassOf ServiceFunction: OK
  RuntimeService subClassOf ServiceFunction: OK
  RiskService subClassOf ServiceFunction: OK
  RESTEndpoint subClassOf Infrastructure: OK
  DatabaseTable subClassOf DatabaseConcept: OK
  ThresholdTable subClassOf DatabaseTable: OK
  ResponseSchema subClassOf DataResource: OK
```
