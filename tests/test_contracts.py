from __future__ import annotations

import pytest

from self_constrained_control.contracts import (
    BudgetSnapshot,
    InvariantViolation,
    SystemScalars,
    validate_budget_snapshot,
    validate_system_scalars,
)


def test_system_scalars_invariants_ok() -> None:
    validate_system_scalars(SystemScalars(50.0, 50.0, "FULL"))
    validate_system_scalars(SystemScalars(0.0, 0.0, "SAFE"))
    validate_system_scalars(SystemScalars(100.0, 100.0, "MINIMAL"))


@pytest.mark.parametrize("battery", [-1.0, 101.0, float("nan"), float("inf")])
def test_system_scalars_invariants_battery_fail(battery: float) -> None:
    with pytest.raises(InvariantViolation):
        validate_system_scalars(SystemScalars(battery, 50.0, "FULL"))


@pytest.mark.parametrize("energy", [-0.1, 101.0, float("nan"), float("inf")])
def test_system_scalars_invariants_energy_fail(energy: float) -> None:
    with pytest.raises(InvariantViolation):
        validate_system_scalars(SystemScalars(50.0, energy, "FULL"))


def test_budget_snapshot_invariants_ok() -> None:
    snap = BudgetSnapshot(
        budgets={"decoder": 10.0, "planner": 0.0, "actuator": 5.0},
        slas_ms={"decoder": 10.0, "planner": 20.0, "actuator": 30.0},
    )
    validate_budget_snapshot(snap, known_modules=["decoder", "planner", "actuator"])


def test_budget_snapshot_negative_budget_fails() -> None:
    snap = BudgetSnapshot(
        budgets={"decoder": -1.0},
        slas_ms={"decoder": 10.0},
    )
    with pytest.raises(InvariantViolation):
        validate_budget_snapshot(snap)


def test_budget_snapshot_missing_module_fails() -> None:
    snap = BudgetSnapshot(
        budgets={"decoder": 1.0},
        slas_ms={"decoder": 10.0},
    )
    with pytest.raises(InvariantViolation):
        validate_budget_snapshot(snap, known_modules=["decoder", "planner"])
