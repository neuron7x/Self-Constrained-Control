from __future__ import annotations

from self_constrained_control.budget_manager import GameTheoreticBudgetManager


def test_nash_equilibrium_keys_and_nonnegative():
    bm = GameTheoreticBudgetManager(
        1000.0,
        {"decoder": (200.0, 20.0), "planner": (400.0, 50.0), "actuator": (400.0, 30.0)},
    )
    bm.allocate_cycle()
    eq = bm.find_nash_equilibrium()
    assert set(eq.keys()) == {"decoder", "planner", "actuator"}
    assert all(v >= 0.0 for v in eq.values())
