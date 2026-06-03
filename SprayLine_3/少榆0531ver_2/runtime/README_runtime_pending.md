# Runtime layer 說明

此資料夾目前只放可解析的 runtime TTL template。

目前沒有放正式：

- `SprayLine_runtime_observation.ttl`
- `SprayLine_runtime_inferred_sparql.ttl`

原因是尚未取得正式 sample JSON、Database runtime output 與完整 rules。  
未來流程應為：

```text
sample JSON / database query result / service output
→ runtime observation TTL
→ rules inference
→ inferred output TTL
```
