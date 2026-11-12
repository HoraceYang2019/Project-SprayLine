# 0718_v2 歷史資料查詢修正

## 修正檔案

`services/integrated_service/sprayline_integrated_service.py`

## 問題

TimeMode 選擇過去時間時，三個站共用同一個 selected time。若某站在固定查詢時間窗內沒有資料，舊程式只允許往前找 12 小時，因此該站即使在 PostgreSQL 有更早的歷史資料，仍可能整站顯示「無資料」。

`sensor_3min` 在時間模式下也沒有歷史 fallback，固定時間窗沒有環境資料時會直接回空。

## 修正內容

1. `sensor_1min` 固定時間窗有資料時，仍回傳該時間窗的真實 DB 資料。
2. 固定時間窗沒有資料時，改為查詢該站在 selected time 以前最近一筆真實 DB 資料。
3. 移除原本 12 小時的 fallback 限制。
4. `sensor_3min` 同樣加入「指定時間以前最近一筆」的 DB fallback。
5. 保留資料原始 `ts`，不把較早資料偽裝成 selected time。
6. 只有該站在 selected time 以前完全沒有資料時，才回傳無資料。

## 查詢邏輯

```sql
SELECT *
FROM sensor_1min
WHERE station_id = :station_id
  AND ts <= :selected_time
ORDER BY ts DESC
LIMIT 1;
```

`sensor_3min` 使用相同原則。

## 未修改

- Future Service 線性預測
- Ontology / threshold
- Manager UI
- Database schema
- API endpoint
- DataProcess 續跑時間問題

DataProcess 重新啟動後可能產生時間斷層的問題仍保留為後續待處理事項。
