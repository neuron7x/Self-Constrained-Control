from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Tuple
from collections import deque

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AdaptiveModuleBudget:
    initial_budget: float
    sla_ms: float

    budget_remaining: float = field(init=False)
    usage: float = 0.0
    penalty_rate: float = 0.2
    violation_history: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.budget_remaining = float(self.initial_budget)

    def request(self, amount: float) -> bool:
        amount = float(amount)
        if self.budget_remaining >= amount:
            self.budget_remaining -= amount
            self.usage += amount
            return True
        return False

    def penalize_cycle(self) -> None:
        # usage already subtracted; violations are tracked via SLA checks and deficits.
        if self.budget_remaining < 0.0:
            overspend = -self.budget_remaining
            ratio = overspend / max(1.0, self.initial_budget)
            self.violation_history.append(ratio)
            rate = self.penalty_rate
            if len(self.violation_history) >= 3 and float(np.mean(self.violation_history[-3:])) > 0.5:
                rate *= 1.5
            self.budget_remaining = max(0.0, self.budget_remaining - rate * overspend)
        self.usage = 0.0

    def top_up(self, amount: float) -> None:
        self.budget_remaining += float(amount)


class BudgetManager:
    def __init__(self, global_pool: float, module_configs: Dict[str, Tuple[float, float]]) -> None:
        self.global_pool = float(global_pool)
        self.modules: Dict[str, AdaptiveModuleBudget] = {
            name: AdaptiveModuleBudget(initial_budget=float(b), sla_ms=float(sla))
            for name, (b, sla) in module_configs.items()
        }

    def allocate_cycle(self) -> None:
        allocation = self.global_pool / max(1, len(self.modules))
        for m in self.modules.values():
            m.top_up(allocation)

    def check_sla(self, module_name: str, actual_latency_ms: float) -> None:
        m = self.modules[module_name]
        if actual_latency_ms > m.sla_ms:
            overshoot = (actual_latency_ms - m.sla_ms) / max(1.0, m.sla_ms)
            m.violation_history.append(float(overshoot))
            # Apply an immediate penalty by reducing remaining budget
            penalty = m.penalty_rate * m.initial_budget * min(1.0, overshoot)
            m.budget_remaining = max(0.0, m.budget_remaining - penalty)

    def end_cycle(self) -> None:
        for m in self.modules.values():
            m.penalize_cycle()


class AuctionBudgetManager(BudgetManager):
    def _priority(self, name: str) -> float:
        return {"decoder": 0.9, "planner": 0.7, "actuator": 1.0}.get(name, 0.5)

    def _urgency(self, name: str) -> float:
        m = self.modules[name]
        return 1.0 - min(1.0, m.budget_remaining / max(1.0, m.initial_budget))

    def allocate_cycle(self) -> None:
        requests: List[Tuple[str, float, float]] = []
        for name, m in self.modules.items():
            amount = 0.10 * m.initial_budget
            score = self._priority(name) * self._urgency(name)
            requests.append((name, float(amount), float(score)))

        requests.sort(key=lambda x: x[2], reverse=True)
        remaining = self.global_pool
        for name, amount, _score in requests:
            give = min(amount, remaining)
            if give <= 0:
                break
            self.modules[name].top_up(give)
            remaining -= give


class PredictiveBudgetManager(AuctionBudgetManager):
    def __init__(self, global_pool: float, module_configs: Dict[str, Tuple[float, float]]) -> None:
        super().__init__(global_pool, module_configs)
        self.usage_history: Dict[str, Deque[float]] = {k: deque(maxlen=10) for k in self.modules}

    def predict_next_usage(self, name: str) -> float:
        hist = self.usage_history[name]
        if len(hist) < 3:
            return self.modules[name].usage
        recent = list(hist)[-5:]
        avg = float(np.mean(recent))
        trend = (recent[-1] - recent[0]) / max(1, len(recent))
        return max(0.0, avg + float(trend))

    def allocate_cycle(self) -> None:
        # predictive top-up (limited)
        for name, m in self.modules.items():
            pred = self.predict_next_usage(name)
            deficit = pred - m.budget_remaining
            if deficit > 0:
                m.top_up(min(deficit, 0.10 * self.global_pool))
        super().allocate_cycle()

    def end_cycle(self) -> None:
        for name, m in self.modules.items():
            self.usage_history[name].append(float(m.usage))
        super().end_cycle()


class GameTheoreticBudgetManager(PredictiveBudgetManager):
    def __init__(self, global_pool: float, module_configs: Dict[str, Tuple[float, float]]) -> None:
        super().__init__(global_pool, module_configs)
        self._cache: Dict[str, Dict[str, float]] = {}
        self._cache_ttl_s = 1.0
        self._cache_t = 0.0

    def find_nash_equilibrium(self) -> Dict[str, float]:
        now = time.time()
        key_payload = "|".join(f"{k}:{m.budget_remaining:.1f}" for k, m in sorted(self.modules.items()))
        key = hashlib.md5(key_payload.encode("utf-8")).hexdigest()
        if key in self._cache and (now - self._cache_t) < self._cache_ttl_s:
            return self._cache[key]

        strategies: Dict[str, float] = {}
        for _ in range(10):
            for name, m in self.modules.items():
                others = sum(mm.budget_remaining for k, mm in self.modules.items() if k != name)
                available = max(0.0, self.global_pool - others)
                predicted = self.predict_next_usage(name)
                risk = 0.1 * len(m.violation_history)
                optimal = min(available, max(0.0, 1.2 * predicted - risk))
                strategies[name] = float(optimal)

            # relaxed convergence
            if all(abs(strategies[n] - self.modules[n].budget_remaining) < 5.0 for n in self.modules):
                break

        self._cache[key] = strategies
        self._cache_t = now
        return strategies

    def negotiate_resources(self) -> None:
        # Simple lending from surplus to deficit based on usage ratio
        surplus: List[Tuple[str, float]] = []
        deficit: List[Tuple[str, float]] = []
        for name, m in self.modules.items():
            if m.budget_remaining > 1.5 * max(1.0, m.usage):
                surplus.append((name, m.budget_remaining - m.usage))
            if m.budget_remaining < 0.2 * m.initial_budget:
                deficit.append((name, 0.2 * m.initial_budget - m.budget_remaining))

        for s_name, s_amt in surplus:
            for d_name, d_amt in deficit:
                give = min(s_amt, d_amt)
                if give > 10.0:
                    self.modules[s_name].budget_remaining -= give
                    self.modules[d_name].budget_remaining += give
                    break
