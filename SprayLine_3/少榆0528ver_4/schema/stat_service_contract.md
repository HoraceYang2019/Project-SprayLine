<!--
檔案備註：
API contract 文字說明：先說明 service contract 包含與不包含的範圍，特別強調不含 UI demo 數值、固定假資料或模擬公式。

資料夾流程定位：流程 Step 3：建立 API contract 與 JSON Schema，只驗證結構與型別，不綁定數值。
-->

# Statistics Service API Contract

## 目的

此 contract 定義統計 service 與 UI / 上游 service 之間的資料交換格式。

## 不包含的內容

- 不包含 UI demo 數值
- 不包含固定假資料
- 不包含由前端模擬值反推的計算公式
- 不包含固定 threshold 數字

## 包含的內容

- output structure
- field names
- data types
- required fields
- field descriptions
- source notes
