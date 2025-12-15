# Self-Constrained Control

## One-sentence summary
Self-Constrained Control is a production-grade control framework design, currently in early development, where an action executes only after passing budget, risk, latency, and stability gates. It enforces deterministic degradation paths when constraints tighten.

## Why this exists
- Controllers often ignore compute/latency budgets and overrun under load.
- Safety gates are bolted on instead of being the execution rule.
- Systems fail open and unpredictably instead of degrading to safe modes.
- Auditability is weak: teams cannot prove why an action was allowed or blocked.

## Core idea
Self-constrained control means every action flows through gates -> planning -> execution -> telemetry.
- Gates set the admissible envelope.
- The planner proposes actions inside it and submits them to gates for approval.
- Execution proceeds only if allowed, and telemetry logs the decision for audit.

## Architecture
- **Budgets**: track compute, latency, energy, and risk allocations per cycle.
- **Gates**: enforce “no action without budget or stability clearance,” including circuit-breaker logic.
- **Planner**: proposes candidate actions ranked by value under current constraints.
- **Degradation**: defines deterministic fallback modes when budgets tighten or gates fail closed.
- **Monitoring**: exports metrics, alerts on anomalies, and records gate decisions.
- **State/Checkpointing**: persists controller state and budget counters for recovery and audits.

## Quickstart
**Current status: early development (README-first scaffold). Commands below reflect the planned production-grade interface and will be implemented once the initial implementation is available.**

```bash
# install (coming next)
python -m venv .venv && source .venv/bin/activate
pip install -e .

# run demo (coming next)
python -m scc.demo --config configs/demo.yaml

# run tests (coming next)
pytest -q

# run benchmarks (coming next)
python -m scc.benchmarks.latency --config configs/demo.yaml
```

## Metrics & Benchmarks
- **Latency p50/p95**: measured per control cycle from plan request to gate decision; benchmark via `python -m scc.benchmarks.latency`.
- **Budget violation rate**: fraction of proposed actions rejected for budget oversubscription; tracked by gates and emitted as a counter.
- **Stability/rollback rate**: proportion of cycles entering degradation or rollback paths; measured in integration tests and benchmarked via replayed traces.
Benchmarks will ship with synthetic traces to make results reproducible.

## Safety model
- **Fail-closed by default**: no action executes without explicit budget and stability approval.
- **Circuit breaker**: sustained violations clamp the planner to minimal-safe policies.
- **Monotonic safety**: Once a budget is exhausted, only degradation or rollback actions are permitted until budgets recover.
- **Deterministic degradation modes**: predefined low-risk behaviors for compute, latency, or stability stress.

## Scope / Non-goals
- Not a hardware-in-the-loop solution; focus is controller logic and telemetry.
- Not a medical or industrial safety certification toolkit.
- Not tied to any vendor model or proprietary runtime.
- Does not promise optimal control; prioritizes constraint compliance and explainability.

## Roadmap
- Implement budget accounting and gate evaluators with replayable configs.
- Add planner stubs with deterministic and learned policy hooks.
- Ship degradation mode library and circuit-breaker policies.
- Provide telemetry sink (Prometheus/OpenTelemetry) and trace export.
- Deliver demo harness (`python -m scc.demo`) with synthetic environment.
- Add benchmark suite for latency, budget violation, and rollback rates.
- Publish LICENSE file and packaging for `pip install self-constrained-control`.

## License + Disclaimer
Planned license: MIT; a LICENSE file will be added with the initial release. This is research software documenting a production-grade control design, with no warranties or fitness claims. There are no medical, industrial, or vendor endorsements. Use at your own risk and validate in your environment.
