# Past / Current Service 噴漆補強版 README

本資料夾是額外補強版本，保留原本 全一致命名的架構，但加入更符合噴漆製程實務的三大類欄位。

## 為什麼要做補強版？

目前未補強版已經能支援基本資料流：

```text
Past / Current Service
 ↓
Statistics Service
 ↓
UI(E)
 ↓
Ontology / Runtime TTL
```

但它比較像一般機台監測資料，包含：

```text
line_id
state
metrics
process_parameters
```

如果要更像實際噴漆機台，還需要補上製程背景、噴漆設備、噴塗品質與環境資訊。

因為目前尚未取得更前面的實際資料來源，所以本補強版先作為「可討論的擴充版本」，不取代未補強版本。

---

## 補強第一類：製程背景 `process_context`

新增欄位：

```json
"process_context": {
 "batch_id": "<string|null>",
 "product_id": "<string|null>",
 "part_id": "<string|null>",
 "recipe_name": "<string|null>",
 "paint_type": "<primer|topcoat|gold_paint>",
 "paint_batch_id": "<string|null>"
}
```

### 為什麼需要？

噴漆不是只看機台狀態，也需要知道正在處理哪一批、哪個產品、哪個零件、哪種配方與漆料。

不同漆料或配方會影響：

- 壓力標準
- 流量標準
- 膜厚標準
- 品質判斷規則
- future / statistics / ontology 的推論依據

### Ontology 可對應

```text
ProductionBatch
ProductPart
PaintRecipe
PaintMaterial
PaintBatch
```

---

## 補強第二類：噴漆設備 `paint_equipment`

新增欄位：

```json
"paint_equipment": {
 "nozzle_id": "<string|null>",
 "spray_gun_id": "<string|null>",
 "nozzle_status": "<string|null>",
 "spray_gun_status": "<string|null>"
}
```

並在 `metrics` 中補充：

```json
"paint_pressure_bar": "<number|null>",
"paint_flow_rate_ml_min": "<number|null>",
"atomizing_pressure_bar": "<number|null>",
"air_flow_rate_value": "<number|null>",
"air_flow_rate_unit": "<string|null>"
```

### 為什麼需要？

噴嘴、噴槍、漆料壓力、漆料流量、霧化空氣壓力，都是噴漆製程的核心。 
如果未來要推論堵塞、噴霧不均、流量異常或膜厚不穩，不能只有一般的 `pressure_bar` 和 `flow_rate_ml_min`。

### Ontology 可對應

```text
Nozzle
SprayGun
PaintPressureMetric
PaintFlowRateMetric
AtomizingAirPressureMetric
```

---

## 補強第三類：噴塗品質與環境 `quality_and_environment`

新增欄位：

```json
"quality_and_environment": {
 "chamber_temperature_c": "<number|null>",
 "chamber_humidity_pct": "<number|null>",
 "film_thickness_um": "<number|null>",
 "color_difference_delta_e": "<number|null>",
 "defect_count": "<number|null>",
 "defect_type": "<string|null>"
}
```

### 為什麼需要？

噴漆品質不應只用 `quality_score_pct` 表示。 
實務上常見品質重點可能包含：

- 膜厚
- 色差
- 缺陷數
- 缺陷種類
- 腔體溫度
- 腔體濕度

其中環境因素也會影響噴塗品質，例如濕度、溫度或排風狀態。

### Ontology 可對應

```text
ChamberEnvironment
CoatingQuality
FilmThicknessMetric
ColorDifferenceMetric
Defect
```

---

## 注意

本補強版中的新增欄位多數使用 `<string|null>`、`<number|null>`，代表它們是可討論的欄位位置，不代表目前已經有真實資料。

如果上游資料來源無法提供這些欄位，仍可先使用未補強版。
