# Grounded Argumentation and Engineering Validity

This document is a **practical engineering argument** for why the repository’s design is coherent and testable *as a scaffold*, and what is explicitly **out of scope**.

## 1. Scope and non-claims (hard boundaries)

- This repository is **not** an official any neurotech/robotics company/Optimus implementation and makes **no** claims of clinical validity.
- The “N1” reference is used as a *placeholder interface name* for a high‑channel neural acquisition device.
- The goal is an **audit-friendly, resource-aware control loop scaffold** with:
  - explicit state,
  - explicit budgets,
  - explicit safety modes,
  - measurable latencies,
  - reproducible simulation.

## 2. Key design claims (what we assert)

Each claim is paired with a *verification handle* (tests or runtime contracts).

### C1 — Resource variables are bounded and observable
**Claim.** Battery and user energy remain finite and bounded; degradation mode is one of a closed set.

**Mechanism.**
- `validate_system_scalars()` runtime contract (BAT-001, ENE-001, MOD-001).
- Metrics capture `battery_level` and `user_energy_level`.

**Evidence.**
- Unit tests covering invariant checks (`tests/test_contracts.py`).
- Runtime checks in `monitor_resources()`.

### C2 — Budget enforcement is explicit and cannot go negative silently
**Claim.** Module budgets are never negative after any allocation/negotiation phase.

**Mechanism.**
- `validate_budget_snapshot()` contract (BUD-001, SLA-001, BUD-002).
- Budget module refuses requests if insufficient remaining budget.

**Evidence.**
- Contract validation executed in every cycle before action processing.

### C3 — Decisions are stability-aware by construction (not “hand-wavy RL”)
**Claim.** Planner selects an action that decreases a Lyapunov candidate when possible; otherwise it falls back to a deterministic rule.

**Mechanism.**
- `LyapunovStabilityAnalyzer` checks ∆V < 0 for candidate actions.
- Rule-based fallback ensures defined output.

**Evidence.**
- Planner unit tests (`tests/test_planner.py`).

### C4 — Numerical robustness is treated as a first-class requirement
**Claim.** HH rate constant computations avoid division by zero at classical singular points (V≈−40, V≈−55).

**Mechanism.**
- `vtrap` stabilization (`_vtrap_py`, `_vtrap_nb`).

**Evidence.**
- Numerical test ensuring no NaNs/Infs at boundary voltages (`tests/test_numerics.py`).

## 3. Residual risk and why it is acceptable in a scaffold

- The simulator is a **synthetic environment**. Biological realism is not proven here; it is a *controlled source of signals*.
- The system implements **measurable safety controls** (degradation modes, watchdog, circuit breaker), but these are **software safety patterns**, not medical-device assurance.

## 4. What “100% valid” means here

- **No hidden state**: state transitions and budgets are visible.
- **No silent violations**: invariants fail loudly.
- **Traceability**: requirements ↔ tests ↔ code.
- **Reproducibility**: deterministic RNG seed is supported.
