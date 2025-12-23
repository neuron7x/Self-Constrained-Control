from __future__ import annotations

import numpy as np

from self_constrained_control.planner_module import PlannerModule


def test_planner_decision_in_range():
    p = PlannerModule()
    s = np.array([80.0, 80.0], dtype=np.float32)
    a = p.decide_with_stability(s)
    assert a in (0, 1, 2)


def test_planner_rejects_when_unstable(monkeypatch):
    p = PlannerModule(seed=123)
    s = np.array([80.0, 80.0], dtype=np.float32)

    def always_unstable(
        state: np.ndarray, next_state: np.ndarray, target: np.ndarray
    ) -> tuple[bool, float]:
        return False, 0.1

    monkeypatch.setattr(p.lyapunov, "stable", always_unstable)
    a = p.decide_with_stability(s)
    assert a == 2
