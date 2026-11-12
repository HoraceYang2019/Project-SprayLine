# final_version_0715 integration

This package preserves the latest Engineer UI from `final_version_0627 (2).zip`
and merges the complete backend from Desktop `SprayLine_0627`.

## Included runtime chain

```text
ontology/runtime_threshold_reference.csv
  -> ontology/threshold_to_ttl.py
  -> ontology/sprayline_threshold.ttl
  -> ontology/rule_inference.py
  -> services/event_rule_service/runtime_rule_classifier.py
  -> Integrated Service / Event Rule / Monitoring / API
```

Ontology TTL is the preferred runtime rule source. JSON rules remain available
as fallback.

## Engineer UI compatibility

Engineer UI V29 calls:

```text
GET  /api/health
GET  /api/database/status
POST /api/time-series/ui/summary
POST /api/time-series/ui/station-detail
POST /api/time-series/ui/component-detail
```

The `/api/database/status` compatibility endpoint was added during this merge.

## Write-back behavior

UI query endpoints are read-only by default. Database write-back is explicit:

```text
POST /api/service-orchestration/integrated/run-once
POST /api/service-orchestration/future/save
POST /api/service-orchestration/monitoring/run
```

## LAN endpoints

Replace `<server-ipv4>` with the IPv4 address of the computer running Docker.

```text
API:         http://<server-ipv4>:8011
Manager UI:  http://<server-ipv4>:8012
Engineer UI: http://<server-ipv4>:8013
```
