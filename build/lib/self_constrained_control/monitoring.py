from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class AnomalyDetector:
    def __init__(self, z_thresh: float = 3.0, min_std: float = 1e-6, window: int = 50) -> None:
        self.z_thresh = z_thresh
        self.min_std = min_std
        self.window = window
        self.samples: Dict[str, List[float]] = {}

    def add_sample(self, name: str, value: float) -> None:
        buf = self.samples.setdefault(name, [])
        buf.append(float(value))
        if len(buf) > self.window:
            del buf[0 : len(buf) - self.window]

    def detect(self, name: str) -> bool:
        buf = self.samples.get(name, [])
        if len(buf) < 10:
            return False
        arr = np.array(buf, dtype=np.float64)
        mu = float(arr.mean())
        sd = float(arr.std())
        sd = max(sd, self.min_std)
        z = abs((arr[-1] - mu) / sd)
        return z > self.z_thresh


@dataclass
class BudgetHealth:
    healthy: bool
    deficits: Dict[str, float] = field(default_factory=dict)


class BudgetHealthMonitor:
    def __init__(self, thresholds: Dict[str, float]) -> None:
        self.thresholds = thresholds

    def check_health(self, budget_manager: object) -> BudgetHealth:
        deficits: Dict[str, float] = {}
        mods = getattr(budget_manager, "modules", {})
        for name, mod in mods.items():
            remaining = getattr(mod, "budget_remaining", 0.0)
            thresh = self.thresholds.get(name, 0.0)
            if remaining < thresh:
                deficits[name] = float(thresh - remaining)
        return BudgetHealth(healthy=(len(deficits) == 0), deficits=deficits)


class GracefulDegradation:
    def __init__(self) -> None:
        self.mode: str = "FULL"

    def assess_and_degrade(
        self,
        battery: float,
        user_energy: float,
        health: BudgetHealth,
        thresholds: Tuple[float, float] = (10.0, 20.0),
    ) -> str:
        batt_th, energy_th = thresholds
        if battery <= batt_th or user_energy <= energy_th:
            self.mode = "SAFE"
        elif not health.healthy:
            self.mode = "REDUCED"
        else:
            self.mode = "FULL"
        return self.mode

    def apply_mode(self, system: object) -> None:
        # Lightweight hook for future mode-dependent behavior.
        setattr(system, "degradation_mode", self.mode)
