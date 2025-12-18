from __future__ import annotations

import numpy as np

from self_constrained_control.planner_module import PlannerModule


def test_planner_decision_in_range():
    p = PlannerModule()
    s = np.array([80.0, 80.0], dtype=np.float32)
    a = p.decide_with_stability(s)
    assert a in (0, 1, 2)
