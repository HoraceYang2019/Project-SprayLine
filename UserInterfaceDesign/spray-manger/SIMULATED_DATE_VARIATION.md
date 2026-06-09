# Simulated date variation fix

This version fixes the simulated API history issue where archived dates looked identical.

## What changed

- Simulation storage keys were bumped to v2 so the UI does not keep reading old duplicated localStorage data.
- Simulated API scenarios now depend on both `date` and `hour`, not only `hour`.
- Daily metric offsets are added so normal days do not render the exact same trend lines.
- Different dates now produce different problem hours and different responsible stations.

## Example behavior

- 2026/06/08: mixed station issues, including station 2, station 3, then station 1.
- 2026/06/09: station 1 morning issue and station 3 evening Cycle Time issue.
- 2026/06/10: station 2 pressure/flow issue and station 1 utilization issue.
- 2026/06/11: station 3 afternoon issue.
- 2026/06/12: station 2 color-layer risk and station 3 night filter/flow risk.
- 2026/06/13: station 1 early short clog risk.

When connected to a real backend, this simulated scenario logic should be replaced by API data from station latest, trend, diagnosis, alert, KPI, and prediction-accuracy endpoints.
