# Validation Plan (V&V)

This plan defines how to validate the repository **against its stated scope**.

> **Verification**: “did we build it right?” (tests, typing, lint)
> **Validation**: “did we build the right thing?” (does the delivered behavior match the scope)

## 0. Validation scope

We validate only:
- correctness of the control-loop sequencing,
- mandatory gates (budget, intent match, safety mode),
- observability artifacts (metrics, logs, snapshots),
- stability-gated planner behavior as defined by this repo.

We do NOT validate clinical safety, real neural data correctness, or real robotics safety.

## 1. Acceptance criteria

### 1.1 Functional acceptance

- **AC-001**: Running the CLI with default config executes the loop for N actions without uncaught exceptions.
- **AC-002**: Intent mismatch prevents actuation.
- **AC-003**: If a module budget is insufficient, the action is skipped and logged.
- **AC-004**: In strict mode, unknown actions raise or are refused.
- **AC-005**: Metrics are exported as JSON and (optionally) Parquet.

### 1.2 Robustness acceptance

- **AC-101**: Circuit breaker opens after repeated simulator failures and prevents further calls until reset timeout.
- **AC-102**: Watchdog terminates on forced stall.
- **AC-103**: Anomaly detector flags synthetic outliers.

### 1.3 Quality acceptance

- **AC-201**: CI passes on Python 3.10/3.11/3.12.
- **AC-202**: `ruff check`, `ruff format --check`, `mypy`, and `pytest` pass locally.

## 2. Validation scenarios

### Scenario V1: Happy path loop
- Actions: `move_arm, plan_route, stop`
- Expect: loop completes; metrics exported; snapshots created.

### Scenario V2: Intent mismatch
- Modify decoder thresholds so it returns `stop` regardless of input.
- Expect: system aborts action; actuator not called.

### Scenario V3: Budget exhaustion
- Set budgets low (decoder/planner/actuator) in config.
- Expect: early returns; no actuation; health monitor reports deficits.

### Scenario V4: Circuit breaker
- Monkeypatch simulator to raise exception.
- Expect: breaker opens after N failures.

### Scenario V5: Watchdog stall
- Inject a sleep longer than watchdog timeout.
- Expect: watchdog triggers shutdown.

## 3. Test mapping (where this is implemented)

- Unit tests: `tests/test_*.py`
- Integration tests: `tests/test_integration.py`
- Benchmarks: `tests/benchmark.py` (informational)

## 4. Execution commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,sim]"
pytest
python -m self_constrained_control.cli run --config data/n1_config.yaml --actions move_arm,plan_route,stop --epochs 2
```

## 5. Reporting

On each CI run, the following artifacts are expected:
- junit/pytest output in logs,
- coverage summary in logs,
- optional exported metrics in `artifacts/metrics/` when running locally.

## 6. Validation audit — 2025-12-16

- **Tools run (local):**
  - `ruff check .` — **fails** (ambiguous current `I` in `neural_interface.py`; unused unpacked var `r` in `planner_module.py`; pyproject enables `fix=true`, so fixes were reverted to preserve state).
  - `mypy src` — **fails** (unused `type: ignore` markers, untyped `njit` decorators/returns in `neural_interface.py`, `no-any-return` in planner and monitoring, `attr-defined` for `degradation_mode` assignment).
  - `pytest` — **passes** (21 tests, ~2s).
- **Validity level:** *Partial*. Functional/integration coverage passes, but AC-202 (ruff/mypy) is unmet until the above lint/type issues are addressed.
