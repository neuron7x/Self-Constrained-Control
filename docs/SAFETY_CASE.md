# Safety / Assurance Case (GSN-lite)

This document is an **engineering assurance case** for the safety boundaries of the repository **as shipped**.

> **Important**: this is a *simulation scaffold*; the safety case is about preventing uncontrolled execution inside this codebase, not about clinical or real-world safety.

## 0. Top-level goal

- **G0**: The system prevents **uncontrolled actuation** and **unbounded computation** within the scope of this repository.

### Context
- **C0**: Actuation is represented by `ActuatorModule` stub; any hardware integration must keep the same gates.
- **C1**: Budgets are abstract tokens; they bound work and provide a measurable control mechanism.
- **C2**: Stochastic simulation is allowed; safety is enforced by deterministic gates.

### Assumptions
- **A0**: The deployment environment is a developer workstation/CI runner; there are no external network-triggered commands.
- **A1**: Users do not patch out safety gates in production. (If they do, safety claims do not apply.)

## 1. Strategy: “Gates at the edges”

- **S1**: Put mandatory safety constraints at **module boundaries** that are executed regardless of internal planner complexity.

### Subgoals

- **G1**: The actuator rejects unknown/unsafe actions in strict mode.
  - **Evidence**: `tests/test_system.py`, `tests/test_integration.py` (strict gating).

- **G2**: The system aborts the action pipeline if intent mismatches.
  - **Evidence**: `tests/test_system.py` (intent mismatch abort).

- **G3**: The system does not execute module work without budget approval.
  - **Evidence**: `tests/test_budget.py` and system tests verifying early returns.

- **G4**: Repeated failures do not lead to tight loops or uncontrolled retries.
  - **Strategy**: Circuit breaker opens after N failures and enforces reset timeout.
  - **Evidence**: `tests/test_system.py` (circuit breaker behavior).

- **G5**: If the loop stalls, the system terminates.
  - **Strategy**: Watchdog monitors progress.
  - **Evidence**: watchdog tests.

- **G6**: Abnormal latency is detectable and observable.
  - **Strategy**: anomaly detector flags outliers; metrics record latencies.
  - **Evidence**: `tests/test_system.py` + `tests/test_integration.py`.

## 2. Residual risks and limitations

- **R1 (Model realism)**: simulator outputs are not guaranteed to correspond to real neural signals.
  - Mitigation: explicit scope boundary; validate only software properties.

- **R2 (Misuse)**: replacing the actuator with hardware control can create real-world hazards.
  - Mitigation: require explicit integration ADR + hazard analysis before enabling hardware backends.

- **R3 (Budget policy correctness)**: game-theoretic allocation may be incorrect for some workloads.
  - Mitigation: treat budgets as guardrails; validate with tests and runtime metrics.

## 3. Required evidence for future expansions

If you integrate real sensors/robotics, you MUST add:
- hazard analysis (HARA/FMEA),
- safety requirements and traceability,
- hardware-in-the-loop tests,
- security threat model for external interfaces.

This repo intentionally stops short of those claims.
