# Formalization: Engineering-Grade Specification & Argumentation (v0.1.x)

> **Purpose**: convert a concept-heavy prototype into a **standardized, logically consistent, engineering-practical** artifact that can evolve **without information loss**.
>
> **Key rule**: every non-trivial statement must be traceable to at least one of:
> 1) a requirement (REQ-*), 2) an architecture decision (ADR-*), 3) a verification activity (VER-*), 4) a measured artifact (ART-*), or 5) an explicit assumption/limit (ASSUMP-*).

---

## 0. Status, scope, and non-goals

### 0.1 Status
- **This repository is a simulation + orchestration scaffold.**
- **Not affiliated** with any neurotech/robotics company/OpenAI.
- **No medical/clinical/human-use claims.**

### 0.2 Scope (what this repo *is*)
A modular control loop that:
1) simulates a neural signal stream (population rates),
2) decodes discrete intents,
3) makes a stability-gated plan decision,
4) budgets resources via game-theoretic allocation,
5) executes an actuator stub under a safety envelope,
6) exports metrics and persists state.

### 0.3 Non-goals (what this repo *is not*)
- Not a medical device.
- Not a N1 (placeholder) reverse-engineering effort.
- Not a full biophysical brain simulator.
- Not a ROS2/hardware control stack (only a stub interface).

**ADR link**: see `docs/adr/ADR-0001-project-scope-and-safety-boundaries.md`.

---

## 1. Terminology and invariants

### 1.1 Glossary
See `docs/GLOSSARY.md`.

### 1.2 System invariants (MUST always hold)
- **INV-001 (Budgets non-negative)**: module budget remaining is never allowed to drift below 0 without being detected and recorded.
- **INV-002 (Action gating in strict mode)**: actuator must reject unknown actions in `strict` mode.
- **INV-003 (Finite outputs)**: simulator outputs must be finite numbers (no NaN/Inf).
- **INV-004 (Bounded rates)**: population rates are clipped to a defined physiological range in the simulator.
- **INV-005 (Watchdog progress)**: control loop must reset watchdog every cycle; watchdog must terminate the loop if progress stalls.

These invariants map to tests and monitoring. See Traceability.

---

## 2. System model: inputs → outputs

### 2.1 Interfaces (public surface)
- `N1Simulator.get_neural_spikes() -> np.ndarray` (rates)
- `IntentionDecoder.decode_intent(rates) -> str`
- `PlannerModule.decide_with_stability(state) -> int` (execute/simplify/reject)
- `GameTheoreticBudgetManager.allocate_cycle()` / `find_nash_equilibrium()`
- `ActuatorModule.perform(action_name, simplified)`
- `ResourceAwareSystem.run_loop(actions, epochs)`

### 2.2 Dataflow (control plane)
1) **Sense**: sample/produce rates from simulator
2) **Decode**: map rates to intent
3) **Plan**: compute candidate actions + stability gate
4) **Budget**: allocate/penalize budgets, enforce SLA
5) **Act**: execute only if allowed + budgeted
6) **Observe**: update resources, log metrics, persist state

### 2.3 State variables (minimal)
- `battery ∈ [0,100]`
- `user_energy ∈ [0,100]`
- `budgets[module] ∈ [0,∞)`
- `latency[module] ∈ (0,∞)`

---

## 3. Requirements (SRS-lite)

> Requirements are written as **verifiable statements**.

### 3.1 Functional requirements
- **REQ-SYS-0001**: The system SHALL execute the loop: decode → plan → act → monitor for each requested action.
- **REQ-SYS-0002**: The system SHALL refuse execution when the decoded intent mismatches the requested action.
- **REQ-SYS-0003**: The system SHALL enforce per-module budgets before performing module work.
- **REQ-SYS-0004**: The system SHALL record per-phase latency metrics.
- **REQ-SYS-0005**: The system SHALL persist a recoverable state snapshot per cycle.

### 3.2 Safety and robustness requirements
- **REQ-SAF-0001**: In `strict` safety mode, the actuator SHALL reject unknown actions.
- **REQ-SAF-0002**: A watchdog SHALL terminate the process if the loop fails to progress within timeout.
- **REQ-SAF-0003**: The circuit breaker SHALL open after a bounded number of failures and enforce reset timeout.
- **REQ-SAF-0004**: The anomaly detector SHALL flag abnormal latency outliers beyond a z-threshold.

### 3.3 Quality requirements
- **REQ-QLT-0001**: The project SHALL pass ruff + mypy + pytest in CI.
- **REQ-QLT-0002**: Public APIs SHALL be documented in `docs/API.md`.
- **REQ-QLT-0003**: Breaking changes SHALL be tracked via ADR + SemVer.

Full list + mapping: `docs/REQUIREMENTS.md` and `docs/TRACEABILITY.md`.

---

## 4. Architecture (SAD-lite)

### 4.1 Components
- **Neural Interface**: produces a bounded, validated rate vector; may include fatigue/metabolic coupling.
- **Decoder**: deterministic mapping from rates → discrete intent.
- **Planner**: combines heuristics + RL backend + stability gate (Lyapunov) + optional LQR guidance.
- **Budgeting**: auction + predictive allocation + best-response equilibrium cache.
- **Actuation**: safety envelope + execution stub.
- **Monitoring**: anomaly detection, degradation modes, metrics export.

### 4.2 Separation of concerns
- All safety boundaries sit **at the edges**: actuator gating, circuit breaker, watchdog.
- All “smart” decisions are treated as **advisory** unless they pass stability + budget + safety checks.

See `docs/ARCHITECTURE.md`.

---

## 5. Argumentation (why this is logically valid)

> Format: **Claim → Justification → Evidence → Residual risk**.

### 5.1 Core claims
- **CLM-001 (Bounded behavior)**: actions are bounded by budgets + safety mode gating.
  - Justification: budgets prevent unlimited computation; safety mode prevents unknown actions.
  - Evidence: unit tests for actuator gating; budget manager tests; CI pass.
  - Residual risk: budget policy correctness is model-dependent; mitigated by traceable tests.

- **CLM-002 (Fail-safe on stalls)**: watchdog terminates on control-loop stalls.
  - Evidence: watchdog unit test; integration test coverage.

- **CLM-003 (Detect abnormal latency)**: anomaly detector flags outliers.
  - Evidence: deterministic z-score implementation + tests.

- **CLM-004 (Reproducible evolution)**: every design change is captured via ADR + changelog.
  - Evidence: ADR directory + SemVer policy.

Full safety/assurance structure: `docs/SAFETY_CASE.md`.

---

## 6. Verification & validation plan

### 6.1 Verification (correctness of implementation)
- **Static**: ruff, mypy
- **Dynamic**: pytest (unit/integration)
- **Performance**: benchmarks are *informational*; they must not gate correctness.

### 6.2 Validation (does it meet its stated purpose)
- Demonstrate: stable loop execution, deterministic gating, metric export, state persistence.

Acceptance criteria and test matrix: `docs/VALIDATION_PLAN.md`.

---

## 7. Risk register and limits

This project explicitly tracks:
- modeling limits (biology realism),
- safety limits (no human/hardware use),
- security limits (no secrets, no PHI),
- reliability limits (stochastic simulations).

See `docs/RISK_REGISTER.md`.

---

## 8. Change control: “no information degradation” rule

### 8.1 What “no degradation” means here
- No implicit changes to semantics.
- Any change that affects behavior requires:
  - a requirement update (REQ), or
  - an ADR (design decision), and
  - an explicit verification update (VER/test).

### 8.2 Versioning policy
- SemVer:
  - PATCH: docs/tests/internal refactors
  - MINOR: new backward-compatible modules/features
  - MAJOR: breaking API/behavior changes

See `docs/adr/ADR-0002-versioning-and-api-stability.md` and `CHANGELOG.md`.

## 11. Argumentation checklist (practical, non-negotiable)

When you claim something is “production-grade”, “stable”, “safe”, or “validated”, you must provide:

1) **Claim**: a single sentence that can be proven false.
2) **Scope**: what world the claim applies to (simulation only? CI? local machine?).
3) **Definitions**: what “stable/safe/validated” means numerically or behaviorally.
4) **Evidence**: code pointer + test pointer + artifact pointer.
5) **Counterexamples**: known failure cases and how they are handled.
6) **Residual risk**: what remains risky even after mitigation.

### Review gate: “If I delete a file, can I still justify the claim?”

If the claim depends on a file, **the file must be referenced** in traceability.

## 12. Example: converting a narrative sentence into engineering truth

Narrative (not acceptable):
- “Planner is mathematically rigorous and stable.”

Engineering form (acceptable):
- **REQ-PLN-0002**: Planner decisions MUST pass a Lyapunov stability gate; if the gate fails, the system MUST fall back to rule-based.
- **Impl**: `planner_module.py` (`decide_with_stability`).
- **Tests**: `tests/test_planner.py` checks action is within {0,1,2} and that gate is invoked.
- **Artifact**: CI run + logs show gate decisions.

## 13. “No degradation” evolution rules

These rules prevent “information degradation” over time:

- **Do not delete rationale**: move old rationale to an ADR or a “Superseded” section.
- **Do not change semantics silently**: if a constant changes meaning, bump version and update requirements.
- **Do not broaden scope casually**: new scope requires new risks, new requirements, and new evidence.
- **Prefer additive interfaces**: add new methods/config keys instead of redefining old ones.
- **Keep deterministic tests deterministic**: isolate randomness behind fixed seeds.

## 14. Release discipline

- **Release checklist** (minimum):
  - [ ] CI green
  - [ ] Version bumped
  - [ ] Changelog updated
  - [ ] Requirements updated (if behavior changed)
  - [ ] Traceability updated
  - [ ] ADR added (if architectural decision changed)



---

## Invariant IDs (runtime-enforced)

- **BAT-001** battery_pct is finite and in [0,100]
- **ENE-001** user_energy_pct is finite and in [0,100]
- **MOD-001** degradation_mode ∈ {FULL,REDUCED,MINIMAL,SAFE}
- **BUD-001** all module budgets finite and ≥ 0
- **SLA-001** all SLA values finite and > 0

These are enforced in `contracts.py` and executed during runtime (see `system.py`).
