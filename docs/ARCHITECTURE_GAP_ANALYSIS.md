# Architecture Gap Analysis (maturity, maintainability, scalability)

Scope: library entrypoint `ResourceAwareSystem`, modules under `src/self_constrained_control/`, and supporting docs/tests as of the current main branch.

## Current boundary map (textual)
- **Orchestrator (`system.py`)** wires config → simulator → decoder → planner → actuator, owns resource locks, metrics export, and persistence.
- **Budgeting (`budget_manager.py`)** tracks per-module budgets and SLA penalties; called synchronously from the orchestrator.
- **Neural I/O (`neural_interface.py`)** sim/decoder utilities; no external deps beyond NumPy.
- **Monitoring (`monitoring.py`, `metrics.py`, `utils.StateManager`)** latency/anomaly signals and artifact writing; invoked from the orchestrator.
- **Safety gates (`actuator_module.py`, `contracts.py`, `utils.CircuitBreaker`)** enforce safety mode and invariant checks.

## Gap analysis (prioritized)
- **P0 (architectural defect)**: Import-time side effect (`setup_logging()` in `system.py`) configures global logging on library import, violating layering and surprising embedding contexts.
- **P1 (growth blocker)**: Configuration is loaded from disk inside `ResourceAwareSystem.__init__`, coupling runtime config with filesystem paths and preventing dependency injection for tests/hosting.
- **P1 (growth blocker)**: Orchestrator is a god-object (metrics export, persistence, degradation, budget negotiation) without explicit seams for swapping subsystems, reducing evolvability.
- **P2 (readability)**: Observability responsibilities are split across `metrics`, `monitoring`, and `system` with no single contract describing what must be emitted per cycle.

## Proposed PR stack (small, controlled)
1) **Boundary hardening (goal: library-safe import and clearer public API surface).**
   - Boundary sketch: CLI configures logging; package exports remain side-effect free; `contracts.py` stays the only cross-cutting invariant layer.
   - Files: `system.py`, `cli.py`, `docs/INTERFACE_CONTRACTS.md`.
   - Acceptance: ruff+mypy+pytest pass; importing `self_constrained_control` does not mutate root logger; public API unchanged.
   - Rollback: revert touched files; remove new logging bootstrap.

2) **Config injection (goal: separate runtime config from environment, unblock scaling).**
   - Boundary sketch: `SystemConfig` accepts dict/typed object; file I/O handled by caller; orchestrator accepts ready config instance.
   - Files: `system.py`, `utils.py`, `docs/REQUIREMENTS.md`.
   - Acceptance: existing tests updated; orchestrator can be constructed from in-memory config; CI passes.
   - Rollback: revert constructor signature and helper; restore file-loading path.

3) **Observability contract (goal: stable artifacts for multi-team use).**
   - Boundary sketch: per-cycle emitted metrics/errors documented as contract; `MetricsCollector` gains minimal interface docstring and optional sink hook.
   - Files: `metrics.py`, `docs/INTERFACE_CONTRACTS.md`.
   - Acceptance: documented fields match emitted JSON; tests asserting export shape; CI passes.
   - Rollback: remove interface doc and hook; keep prior behavior.

All PRs run existing CI (`make lint type test build`) and include a short rollback note as above.
