# CHANGELOG 0718_v2

## Base
- Copied from the latest inner project in `final_version_0715(3).zip`.
- The original 0715 upload is not overwritten.
- The runnable folder is flattened to one level: `final_version_0718_v2`.

## Integration fixes
- Fixed UI hour index → Service API minute conversion.
- Unified UI display time with Service API / PostgreSQL data time.
- Removed the UI-side 18-minute batch-time assumption.
- Kept the external `final_version_0627_sprayline_pgdata` volume.
- Disabled automatic `db-setup`, `dataprocess`, and reset in normal 0718_v2 use.

## Batch performance
- Limited recent station sensor rows before joining `batch_run`.
- Reduced the batch lookup buffer from 500 to 64 batches.
- Increased PostgreSQL shared memory to 512 MB.
- Dashboard refresh now uses Summary + three Station Detail calls.
- Component Detail is called only when a component or trend is opened.
- The slider sends requests only after release.

## Data integrity / display
- Trend points use raw Service API values only.
- Removed UI moving average, vertical shift, neighbor clamp, and current-value fill.
- Missing component fields show no-data instead of returning HTTP 502.
- Batch temperature/humidity use the nearest real `sensor_3min` within ±3 minutes.
- Empty process values display `--`, not `0`.
- Clicking component detail no longer overwrites the station card with a newer snapshot.

## Safety
- Normal startup does not initialize or generate data.
- `-Mode reset` is disabled.
- Modified files include `.before_0718_v2` backups.
