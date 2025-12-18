from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass


class InvariantViolation(RuntimeError):
    """Raised when a runtime invariant is violated."""


def _is_finite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


@dataclass(frozen=True)
class SystemScalars:
    """Minimal scalar state required to reason about safety and resource behavior."""

    battery_pct: float
    user_energy_pct: float
    degradation_mode: str


@dataclass(frozen=True)
class BudgetSnapshot:
    """Budget invariants are checked on observable quantities only."""

    budgets: dict[str, float]  # remaining per module
    slas_ms: dict[str, float]  # configured SLA per module


DEFAULT_DEGRADATION_MODES = {"FULL", "REDUCED", "MINIMAL", "SAFE"}


def validate_system_scalars(state: SystemScalars, *, allow_negative_energy: bool = False) -> None:
    """
    Runtime contract for system resource scalars.

    Invariants:
      - BAT-001: battery_pct is finite and in [0, 100]
      - ENE-001: user_energy_pct is finite and in [0, 100] (unless allow_negative_energy)
      - MOD-001: degradation_mode ∈ DEFAULT_DEGRADATION_MODES
    """
    if not _is_finite(state.battery_pct):
        raise InvariantViolation("BAT-001 battery_pct must be finite")
    if state.battery_pct < 0.0 or state.battery_pct > 100.0:
        raise InvariantViolation(f"BAT-001 battery_pct out of range: {state.battery_pct}")

    if not _is_finite(state.user_energy_pct):
        raise InvariantViolation("ENE-001 user_energy_pct must be finite")

    if not allow_negative_energy and (state.user_energy_pct < 0.0 or state.user_energy_pct > 100.0):
        raise InvariantViolation(f"ENE-001 user_energy_pct out of range: {state.user_energy_pct}")
    if allow_negative_energy and state.user_energy_pct > 100.0:
        raise InvariantViolation(f"ENE-001 user_energy_pct > 100: {state.user_energy_pct}")

    if state.degradation_mode not in DEFAULT_DEGRADATION_MODES:
        raise InvariantViolation(f"MOD-001 unknown degradation_mode: {state.degradation_mode}")


def validate_budget_snapshot(
    snapshot: BudgetSnapshot, *, known_modules: Iterable[str] | None = None
) -> None:
    """
    Budget contract.

    Invariants:
      - BUD-001: all budgets are finite and >= 0
      - SLA-001: SLA values are finite and > 0
      - BUD-002: if known_modules given, keys are a superset of known modules
    """
    for k, v in snapshot.budgets.items():
        if not _is_finite(v):
            raise InvariantViolation(f"BUD-001 budget for {k} must be finite")
        if v < 0.0:
            raise InvariantViolation(f"BUD-001 budget for {k} must be >= 0, got {v}")

    for k, v in snapshot.slas_ms.items():
        if not _is_finite(v) or float(v) <= 0.0:
            raise InvariantViolation(f"SLA-001 SLA for {k} must be finite and > 0, got {v}")

    if known_modules is not None:
        missing = set(known_modules) - set(snapshot.budgets.keys())
        if missing:
            raise InvariantViolation(f"BUD-002 missing module budgets: {sorted(missing)}")
