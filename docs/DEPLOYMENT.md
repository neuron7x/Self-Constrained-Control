# Deployment Notes

## Philosophy
This is a **scaffold**: it provides engineering-grade boundaries (config, logging, safety guards, tests, CI),
while allowing you to swap in real components (decoders, planners, robotics integration).

## Artifacts
The system writes artifacts under `artifacts/`:
- `artifacts/state/` : serialized state snapshots
- `artifacts/metrics/` : json/parquet metrics (depending on installed extras)

## Safety
- Circuit breaker around external calls
- Watchdog to detect hangs
- Degradation modes based on battery/energy and budget health
