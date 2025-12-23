from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MetricsCollector:
    latencies_s: dict[str, list[float]] = field(default_factory=dict)
    battery_level: float = 0.0
    user_energy_level: float = 0.0
    bellman_error: float = 0.0
    rl_metrics: dict[str, float | str] = field(default_factory=dict)

    def record_latency(self, name: str, duration_s: float) -> None:
        self.latencies_s.setdefault(name, []).append(float(duration_s))

    def set_rl_metrics(self, metrics: dict[str, float | str]) -> None:
        self.rl_metrics = {k: v for k, v in metrics.items()}

    def snapshot(self) -> dict[str, Any]:
        return {
            "ts": time.time(),
            "battery": self.battery_level,
            "user_energy": self.user_energy_level,
            "bellman_error": self.bellman_error,
            "rl": dict(self.rl_metrics),
            "latencies_s": {k: list(v) for k, v in self.latencies_s.items()},
        }

    def export_json(self, path: str = "artifacts/metrics/metrics.json") -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.snapshot(), indent=2, sort_keys=True), encoding="utf-8")
        return p

    def export_parquet(self, path: str = "artifacts/metrics/metrics.parquet") -> Path:
        # Optional dependency path: pandas + pyarrow/fastparquet.
        try:
            import pandas as pd  # type: ignore
        except Exception as e:
            logger.warning("Parquet export skipped (pandas missing): %s", e)
            return self.export_json(path.replace(".parquet", ".json"))

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        rows: list[dict[str, float]] = []
        for name, vals in self.latencies_s.items():
            for v in vals:
                rows.append({"metric": f"latency.{name}", "value": float(v)})

        rows.extend(
            [
                {"metric": "battery", "value": float(self.battery_level)},
                {"metric": "user_energy", "value": float(self.user_energy_level)},
                {"metric": "bellman_error", "value": float(self.bellman_error)},
            ]
        )

        df = pd.DataFrame(rows)
        try:
            df.to_parquet(p, index=False)
            return p
        except Exception as e:
            logger.warning("Parquet export failed, falling back to json: %s", e)
            return self.export_json(path.replace(".parquet", ".json"))
