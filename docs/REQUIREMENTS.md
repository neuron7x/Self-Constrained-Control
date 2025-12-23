# Requirements (SRS-lite)

This document is the **single source of truth** for what the system claims to do.
Every requirement is:
- **unambiguous**,
- **testable** (or at least inspectable),
- linked to a verification method (VER-*),
- mapped to an implementation surface (code/tests) via `docs/TRACEABILITY.md`.

## 0. Conventions

- IDs are stable. Never reuse an ID for a different requirement.
- Keywords follow **MUST/SHALL/SHOULD/MAY** semantics (see `docs/GLOSSARY.md`).

## 1. Assumptions and constraints

### 1.1 Explicit assumptions

- **ASSUMP-0001**: The repository is a **simulation and orchestration scaffold**; all biological and hardware elements are abstracted.
- **ASSUMP-0002**: All actions are non-safety-critical placeholders unless replaced by a domain-reviewed actuator backend.
- **ASSUMP-0003**: Stochastic simulation is permitted; determinism is not guaranteed unless a random seed is fixed.

### 1.2 Hard constraints

- **CONST-0001**: The project SHALL NOT claim medical safety or fitness for clinical use.
- **CONST-0002**: The project SHALL NOT include PHI/biometric personal data.

## 2. Functional requirements

### 2.1 Core loop

- **REQ-SYS-0001**: The system SHALL execute, per requested action, the phases: **decode → plan → act → monitor**.
  - Verification: VER-TEST (integration test).

- **REQ-SYS-0002**: The system SHALL stop processing an action if decoded intent != requested action.
  - Verification: VER-TEST.

- **REQ-SYS-0003**: The system SHALL expose a programmatic entry point `ResourceAwareSystem.run_loop(actions, epochs)`.
  - Verification: VER-INSPECT (API presence) + VER-TEST (smoke test).

- **REQ-SYS-0004**: The system SHALL expose a CLI entry point to run the loop with a config and action list.
  - Verification: VER-TEST (CLI smoke).

### 2.2 Neural interface simulation

- **REQ-NIF-0001**: The simulator SHALL return a rate vector of length `channels`.
  - Verification: VER-TEST.

- **REQ-NIF-0002**: The simulator SHALL return finite values (no NaN/Inf).
  - Verification: VER-TEST.

- **REQ-NIF-0003**: The simulator SHALL bound the rate vector to a configured physiological range.
  - Verification: VER-TEST.

- **REQ-NIF-0004**: The simulator SHOULD provide hooks for fatigue/metabolic coupling and neuromodulation.
  - Verification: VER-INSPECT.

### 2.3 Decoding

- **REQ-DEC-0001**: The decoder SHALL map a rate vector to one intent label.
  - Verification: VER-TEST.

- **REQ-DEC-0002**: The decoder SHOULD be deterministic given the same input.
  - Verification: VER-TEST.

### 2.4 Planning

- **REQ-PLN-0001**: The planner SHALL output an action index in `{0,1,2}` representing `{execute, simplify, reject}`.
  - Verification: VER-TEST.

- **REQ-PLN-0002**: The planner SHALL apply a stability gate (Lyapunov-style) before approving an action when enabled.
  - Verification: VER-INSPECT + VER-TEST.

- **REQ-PLN-0003**: The planner MAY use RL components; if present, it SHALL fail closed (fallback) if the RL backend is unavailable.
  - Verification: VER-TEST.

### 2.5 Budgeting and allocation

- **REQ-BUD-0001**: Each module (decoder/planner/actuator) SHALL have a budget state.
  - Verification: VER-TEST.

- **REQ-BUD-0002**: A module SHALL NOT perform work requiring budget if the request is denied.
  - Verification: VER-TEST.

- **REQ-BUD-0003**: The allocator SHOULD support a multi-step policy: base allocation + predictive adjustment + best-response equilibrium.
  - Verification: VER-INSPECT + VER-TEST.

- **REQ-BUD-0004**: The Nash-equilibrium computation SHOULD be cached with a TTL.
  - Verification: VER-TEST.

### 2.6 Actuation

- **REQ-ACT-0001**: In `strict` mode, the actuator SHALL reject unknown actions.
  - Verification: VER-TEST.

- **REQ-ACT-0002**: The actuator SHALL support a `simplified` flag to represent degraded execution.
  - Verification: VER-TEST.

### 2.7 Monitoring and persistence

- **REQ-MON-0001**: The system SHALL export latency metrics for monitor/decoder/planner/actuator.
  - Verification: VER-TEST.

- **REQ-MON-0002**: The anomaly detector SHALL flag latency outliers beyond a threshold.
  - Verification: VER-TEST.

- **REQ-PER-0001**: The system SHALL persist a per-cycle snapshot that is recoverable by a compatible reader.
  - Verification: VER-TEST.

## 3. Safety & robustness requirements

- **REQ-SAF-0001**: A watchdog SHALL terminate execution if loop progress stalls beyond timeout.
  - Verification: VER-TEST.

- **REQ-SAF-0002**: The circuit breaker SHALL open after `N` failures and enforce a reset timeout.
  - Verification: VER-TEST.

- **REQ-SAF-0003**: Failures in simulation/decoding/planning SHALL be surfaced as logged errors and SHALL prevent actuation.
  - Verification: VER-TEST.

## 4. Quality requirements (OpenAI-style engineering hygiene)

- **REQ-QLT-0001**: CI SHALL run on Python 3.10/3.11/3.12 and SHALL include lint + format check + mypy + pytest.
  - Verification: VER-INSPECT (workflow file).

- **REQ-QLT-0002**: The repository SHALL use pinned dev tooling or minimum versions and a pre-commit configuration.
  - Verification: VER-INSPECT.

- **REQ-QLT-0003**: Public APIs SHALL be documented and kept stable within a minor version.
  - Verification: VER-INSPECT + VER-POLICY.

## 5. Verification methods

- **VER-TEST**: automated tests (`pytest`).
- **VER-INSPECT**: direct inspection of code/docs for presence and structure.
- **VER-POLICY**: process compliance (SemVer/ADR/Changelog).

Next: `docs/TRACEABILITY.md`.
