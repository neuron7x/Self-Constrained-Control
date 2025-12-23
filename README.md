# Self-Constrained-Control

[![CI](https://github.com/neuron7x/Self-Constrained-Control/actions/workflows/ci.yml/badge.svg)](https://github.com/neuron7x/Self-Constrained-Control/actions/workflows/ci.yml)

**OpenAI-level engineering scaffold** for a **resource-aware control loop** integrating:
- **Neural interface simulation** (population-rate generation with optional HH-style hooks)
- **Intention decoding** (rate vector → discrete intent)
- **Stability-aware planning** (Lyapunov gate + LQR guidance + optional RL backend)
- **Game-theoretic budgeting** (auction + prediction + best-response equilibrium)
- **Safety & robustness primitives** (circuit breaker, watchdog, anomaly detection, graceful degradation)
- **Observability** (latency metrics, artifacts, snapshots)

## Disclaimer / scope boundary

- This repository is **not affiliated with a neurotech company, a humanoid platform vendor, or OpenAI**.
- This is a **simulation + orchestration scaffold** for research and engineering iteration.
- It makes **no clinical, medical, or real-world safety claims**.
- The default actuator is a stub. **Replacing it with real hardware control requires a new safety review**.

## Documentation (formal, traceable, “no information degradation”)

If you want the system to evolve without semantic drift, start here:

- `docs/FORMALIZATION.md` — how we preserve meaning while changing code
- `docs/REQUIREMENTS.md` — testable requirements (SRS-lite)
- `docs/ARCHITECTURE.md` — component/dataflow model (SAD-lite)
- `docs/ALGORITHMIC_FOUNDATIONS.md` — gating, budgeting, and advisory logic with evidence hooks
- `docs/SAFETY_CASE.md` — assurance case (GSN-lite)
- `docs/VALIDATION_PLAN.md` — acceptance criteria and scenarios
- `docs/TRACEABILITY.md` — requirements → implementation → tests
- `docs/RISK_REGISTER.md` — risk scoring and mitigations
- `docs/GLOSSARY.md` — fixed terminology
- `docs/adr/` — architecture decision records (ADRs)

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,sim]"
python -m self_constrained_control.cli run --config data/n1_config.yaml --actions move_arm,plan_route,stop --epochs 2
```

## Project layout

- `src/self_constrained_control/` — library
- `scripts/` — runnable scripts
- `tests/` — unit/integration tests
- `docs/` — architecture, requirements, API, deployment notes
- `data/n1_config.yaml` — config

## Developer Quickstart

```bash
# Setup (one-time)
pip install -e ".[dev]"
pre-commit install

# Daily workflow (using make)
make fmt          # Format code
make lint         # Lint with auto-fix
make type         # Type check
make test         # Run tests with coverage
make all          # Run all checks

# Or run pre-commit on all files
make pre-commit
```

## License

Apache-2.0


## Non-claims (hard boundaries)

- This repository is **not** affiliated with any neurotech/robotics company and does **not** represent an actual medical device.
- The “N1” naming is used as a **placeholder interface** for a high-channel neural acquisition device.
- The simulator is synthetic; “validity” here means **engineering validity** (explicit state, contracts, tests, traceability).

## Documentation map

- `docs/FORMALIZATION.md` — formal model, invariants, and runtime contract IDs
- `docs/ARGUMENTATION.md` — claim → mechanism → evidence argument (grounded engineering)
- `docs/INTERFACE_CONTRACTS.md` — stable module interfaces and guarantees
- `docs/ARCHITECTURE_GAP_ANALYSIS.md` — prioritized gaps and PR stack for architectural maturity
- `docs/SAFETY_CASE.md` — safety argument + evidence pointers
- `docs/TRACEABILITY.md` — requirements ↔ tests ↔ implementation
- `docs/ALGORITHMIC_FOUNDATIONS.md` — algorithmic basis, gates, and containment
- `docs/DOCUMENTATION_PROMPT_RESPONSE.md` — coverage of documentation/testing/CI/security items from the UA prompt
