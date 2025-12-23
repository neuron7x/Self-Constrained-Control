# Traceability Matrix

This matrix links **Requirements → Implementation → Verification**.

> Rule: a requirement is not “done” until there is a **verification row** that points to a test or inspection.

## Legend

- Impl: primary implementation files
- Test: primary verification tests
- Method: VER-TEST / VER-INSPECT / VER-POLICY

## Core requirements

| Requirement ID | Description | Impl | Test | Method |
|---|---|---|---|---|
| REQ-SYS-0001 | Execute decode→plan→act→monitor per action | `system.py` | `tests/test_integration.py` | VER-TEST |
| REQ-SYS-0002 | Abort on intent mismatch | `system.py` | `tests/test_system.py` | VER-TEST |
| REQ-SYS-0003 | Provide `ResourceAwareSystem.run_loop` | `system.py` | `tests/test_system.py` | VER-TEST |
| REQ-SYS-0004 | Provide CLI runner | `cli.py` | `tests/test_integration.py` | VER-TEST |
| REQ-NIF-0001 | Rate vector length = channels | `neural_interface.py` | `tests/test_neural_interface.py` | VER-TEST |
| REQ-NIF-0002 | Rates are finite | `neural_interface.py` | `tests/test_neural_interface.py` | VER-TEST |
| REQ-NIF-0003 | Rates bounded to range | `neural_interface.py` | `tests/test_neural_interface.py` | VER-TEST |
| REQ-DEC-0001 | Decode returns single label | `neural_interface.py` | `tests/test_system.py` | VER-TEST |
| REQ-PLN-0001 | Planner returns {0,1,2} | `planner_module.py` | `tests/test_planner.py` | VER-TEST |
| REQ-PLN-0002 | Stability gate applied | `planner_module.py` | `tests/test_planner.py::test_planner_rejects_when_unstable` | VER-TEST |
| REQ-BUD-0001 | Budgets exist per module | `budget_manager.py` | `tests/test_budget.py` | VER-TEST |
| REQ-BUD-0002 | Work denied without budget | `budget_manager.py`, `system.py` | `tests/test_system.py::test_actuator_not_called_when_budget_denied` | VER-TEST |
| REQ-BUD-0004 | Nash-equilibrium computation cached with TTL | `budget_manager.py` | `tests/test_budget.py::test_nash_equilibrium_cache_ttl` | VER-TEST |
| REQ-ACT-0001 | Strict mode rejects unknown actions | `actuator_module.py` | `tests/test_integration.py` | VER-TEST |
| REQ-MON-0001 | Latency metrics exported | `metrics.py` | `tests/test_system.py::test_metrics_and_state_artifacts` | VER-TEST |
| REQ-PER-0001 | Per-cycle snapshot recoverable | `utils.py`, `system.py` | `tests/test_system.py::test_metrics_and_state_artifacts` | VER-TEST |
| REQ-SAF-0001 | Watchdog terminates on stall | `system.py` | `tests/test_system.py` | VER-TEST |
| REQ-SAF-0002 | Circuit breaker opens after failures | `utils.py` | `tests/test_system.py` | VER-TEST |
| REQ-QLT-0001 | CI runs ruff/mypy/pytest | `.github/workflows/ci.yml` | (inspection) | VER-INSPECT |
| REQ-QLT-0002 | Diff coverage ≥95% with artifacts | `.github/workflows/ci.yml`, `scripts/diff_coverage.py` | `tests/test_diff_coverage.py` | VER-TEST |

## Evidence artifact pointers

- **ART-001**: CI green (GitHub Actions)
- **ART-002**: Coverage report (pytest-cov)
- **ART-003**: Metrics JSON/Parquet outputs (`artifacts/metrics/`)

## Maintaining traceability

When you add a feature:
1) add/modify requirements in `docs/REQUIREMENTS.md`,
2) add/modify tests,
3) update this matrix,
4) record an ADR if behavior or interfaces changed.


## Additional evidence

- `docs/ARGUMENTATION.md` (claim → mechanism → evidence)
- `docs/INTERFACE_CONTRACTS.md` (module boundaries)
- `tests/test_contracts.py` (runtime invariant coverage)
- `tests/test_numerics.py` (HH singularity protection)
