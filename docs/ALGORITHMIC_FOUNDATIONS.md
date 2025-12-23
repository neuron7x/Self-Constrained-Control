# ALGORITHMIC FOUNDATIONS

## 1) Scope & Non-Goals
- Scope: simulation scaffold for a resource-aware control loop that decodes intents, plans with a stability gate, enforces budgets, and actuates under a safety envelope (see `docs/FORMALIZATION.md`, `src/self_constrained_control/system.py`). Claims apply to software behavior on developer/CI environments only.
- Non-goals: no clinical/medical assertions, no guarantees for real hardware integrations, no networked or safety-critical deployment claims, no performance SLAs beyond documented budgets (see `docs/FORMALIZATION.md` §0.3, `docs/SAFETY_CASE.md`).

## 2) Design Philosophy
- Advisory vs mandatory: planning/RL outputs are advisory; mandatory gates are budgets (`GameTheoreticBudgetManager.request/check_sla`), stability (`LyapunovStabilityAnalyzer`), and safety-mode actuation (`ActuatorModule.perform`). The orchestrator (`ResourceAwareSystem.process_action`) sequences gates before actuation.
- Resource limits as state: battery and user energy are part of state (`SystemScalars`, `ResourceAwareSystem.battery/user_energy`) so downstream logic can reason about feasibility and degrade early.
- Fail-closed and degradation: reject = abort action before actuator; degrade = switch to simplified action (`PlannerModule` action 1) or SAFE mode (`GracefulDegradation.apply_mode`). Any invariant violation raises and stops the current action (see `contracts.py`, `system.py`).

## 3) Algorithmic Overview
- RL/Planning (advisory): `PlannerModule.decide_with_stability` mixes LQR guidance, rule-based fallback, and Lyapunov screening; rewards/costs come from `estimate_params` heuristics.
- Lyapunov stability gate (mandatory): `LyapunovStabilityAnalyzer.stable` checks ΔV<0 against `target_state`; only stable candidates can proceed to actuator.
- Budget allocation (mandatory): `GameTheoreticBudgetManager.allocate_cycle/negotiate_resources/find_nash_equilibrium` enforce per-module token limits and SLA penalties; requests failing `request()` abort work.
- Safety/actuation boundary (mandatory): `ActuatorModule.perform` rejects unknown actions in strict mode before any execution; circuit breaker wraps calls (`CircuitBreaker.call`).
- Monitoring/validation artifacts (mandatory): `MetricsCollector` exports JSON/Parquet; `AnomalyDetector`, `BudgetHealthMonitor`, and `GracefulDegradation` provide health and degradation signals; `StateManager` snapshots enable post-hoc inspection.

## 4) Reinforcement Learning Component
### 4.1 Purpose
Advisory planner proposing `{execute, simplify, reject}` decisions to maximize heuristic reward while preserving stability and budgets.

### 4.2 Contract abstraction
- State: `[battery_pct, user_energy_pct]` (`ResourceAwareSystem.process_action`, `PlannerModule.decide_with_stability`).
- Actions: int in `{0 (execute), 1 (simplify), 2 (reject)}` (interface in `docs/INTERFACE_CONTRACTS.md`, enforced in tests `tests/test_planner.py`).
- Reward proxy: `estimate_params` returns `(reward, cost, stress)`; TD proxy via `compute_bellman_error`. This is implementation-dependent and heuristic (no learned value function shipped).

### 4.3 Mandatory containment
RL outputs cannot actuate directly: budget `request()` gates decoding/planning/actuation; Lyapunov gate vetoes unstable actions; strict actuator validates action names; circuit breaker blocks on repeated faults (`system.py`, `utils.py`).

### 4.4 Failure modes (≥6) + containment + evidence hook
- FM-RL-1: Divergent reward scaling from `estimate_params` noise → containment: Lyapunov gate + rule-based fallback (`decide_with_stability` loop). Evidence: `tests/test_planner.py`.
- FM-RL-2: Unstable proposed action (ΔV≥0) → containment: reject and fall back to rule-based only if Lyapunov gate approves; otherwise hard reject (`decide_with_stability`). Evidence: `planner_module.py`, `tests/test_planner.py::test_planner_rejects_when_unstable`.
- FM-RL-3: Budget exhaustion before planning → containment: early return in `process_action` if `request()` fails. Evidence: `tests/test_budget.py`, `system.py` logic.
- FM-RL-4: Intent mismatch between requested and decoded → containment: `process_action` returns before planning/actuation. Evidence: `tests/test_system.py` intent check.
- FM-RL-5: Latency over SLA → containment: `check_sla` penalizes remaining budget to throttle future work. Evidence: `budget_manager.py`, `tests/test_budget.py`.
- FM-RL-6: Unsupported action index outside {0,1,2} → containment: action set constrained in `decide_with_stability`; actuator strict-mode guard rejects unknown names. Evidence: `actuator_module.py`, `tests/test_integration.py`.
- FM-RL-7: Circuit-breaker opens after repeated planner/simulator failures → containment: `CircuitBreaker.call` raises and stops pipeline. Evidence: `utils.py`, `docs/SAFETY_CASE.md` G4, `tests/test_system.py`.

### 4.5 Fail-closed behavior + fallback
If any gate fails (budget, intent, stability, safety-mode, circuit breaker), the action is aborted and no actuator call occurs. Fallbacks: rule-based planner path, simplified action (1), SAFE degradation mode, or skipping cycle with metrics recorded (`system.py`, `monitoring.py`).

### 4.6 Validation hooks
- Unit tests: `tests/test_planner.py` (action bounds, fail-closed stability), `tests/test_system.py` (budget gating, artifacts), `tests/test_budget.py` (Nash cache TTL), `tests/test_integration.py`.
- Metrics: latency + Bellman error in `MetricsCollector`; anomaly detection on planner latency (`AnomalyDetector`).
- Invariants: `INV-001/002/004` via `validate_system_scalars`; `BUD-001/002` via `validate_budget_snapshot`.

### 4.7 Implementation-dependent notes
- RL backend is stubbed (no policy learning). Any learned policy must still emit `{0,1,2}` and route through Lyapunov + budget + safety gates.
- Reward shaping and cost models are heuristic; claims about optimality or convergence are out-of-scope until backed by training/eval artifacts.

### 4.8 References
[1] R. S. Sutton and A. G. Barto, *Reinforcement Learning: An Introduction*, 2nd ed., MIT Press, 2018.  
[2] J. Achiam et al., “Constrained Policy Optimization,” ICML, 2017.  
[3] Y. Chow et al., “Lyapunov-based Safe Policy Optimization for Continuous Control,” NeurIPS, 2018.

## 5) Lyapunov-Based Stability Gate
### 5.1 Engineering definition
Stability is evaluated on state `[battery, user_energy]` toward `target_state=[75,75]` using quadratic V(x) = (x−x*)ᵀ P (x−x*) with fixed positive-definite P (`LyapunovStabilityAnalyzer.P`). This is a heuristic gate, not a formally proven Lyapunov certificate for the full dynamics. Stable if ΔV<0 between candidate `next_state` and current (`stable` method).

### 5.2 Gate decision policy
- ACCEPT: candidate action with ΔV<0 and within approved action set, budgets available, safety-mode passes.
- DEGRADE: if only simplify (1) passes stability, execute simplified actuation.
- REJECT: if no action yields ΔV<0 or budgets/SLA/intent fail, abort actuation.

### 5.3 Why gate (not controller)
Gate operates as a veto boundary in `ResourceAwareSystem.process_action`; it does not directly control plant dynamics. This matches architecture intent: “smart” parts are advisory and must clear mandatory gates (`docs/ARCHITECTURE.md` §0/§2.2).

### 5.4 Failure modes (≥6) + containment + evidence hook
- FM-LY-1: Non-PD matrix P leading to incorrect V → containment: static PD initialization; change requires tests/ADR. Evidence: `planner_module.py` (constant P).
- FM-LY-2: Target mis-specified (e.g., unrealistic `[75,75]`) → containment: rule-based fallback still bounds actions; degradation to SAFE mode. Evidence: `monitoring.py`, `system.py`.
- FM-LY-3: Numerical overflow in ΔV → containment: bounded state inputs (`validate_system_scalars`), finite checks in simulator; exceptions abort action. Evidence: `contracts.py`, `tests/test_contracts.py`.
- FM-LY-4: Gate bypass due to coding error → containment: action set limited to gate output; actuator still enforces strict-mode whitelist. Evidence: `actuator_module.py`, `tests/test_integration.py`.
- FM-LY-5: State outside [0,100] from sensor bug → containment: invariant checks raise `InvariantViolation` and halt. Evidence: `contracts.py`, `tests/test_contracts.py`.
- FM-LY-6: Concurrency/race on shared state → containment: `resource_lock` in `monitor_resources`; async sequencing around planner call. Evidence: `system.py`.
- FM-LY-7: LQR control proposing unstable action → containment: Lyapunov check rejects, fallback to rule-based. Evidence: `planner_module.py`.

### 5.5 Limits & residual risk
Lyapunov gate uses a handcrafted quadratic form and deterministic target; it does not guarantee global stability for arbitrary dynamics. No robustness margins for model uncertainty are encoded.

### 5.6 Validation hooks
- Tests: `tests/test_planner.py` (action bounds), `tests/test_system.py` (loop invariants), `tests/test_contracts.py` (scalar/budget bounds).
- Metrics: Bellman error and latencies exported; anomalies flagged via `AnomalyDetector`.
- Artifacts: `MetricsCollector` JSON/Parquet, state snapshots from `StateManager`.

### 5.7 Implementation-dependent notes
- Formal Lyapunov certificates are not proven; any change to P/target must add proofs or empirical validation.
- Stability check currently single-step; multi-step safety would require reachability analysis or MPC.

### 5.8 References
[4] H. K. Khalil, *Nonlinear Systems*, 3rd ed., Prentice Hall, 2002.  
[5] A. D. Ames et al., “Control Barrier Function Based Quadratic Programs for Safety Critical Systems,” IEEE TAC, 2017.  
[6] Z. Jiang and Y. Wang, “Input-to-State Stability for Discrete-Time Nonlinear Systems,” Automatica, 2001.

## 6) Auction / Game-Theoretic Budget Allocation
### 6.1 Purpose
Allocate finite resource tokens across decoder/planner/actuator as strategic actors competing for a shared pool, ensuring bounded computation and fairness.

### 6.2 Auction model abstraction
- Actors: module budgets in `GameTheoreticBudgetManager.modules`.
- Bids: implicit via predicted usage (`predict_next_usage`) and urgency/priority functions (`_priority`, `_urgency`).
- Payoff: available budget to execute work; penalties applied on SLA violations (`check_sla`).

### 6.3 Nash equilibrium usage boundaries
`find_nash_equilibrium` iterates heuristic best responses with a 1s cache TTL; it **does not** compute a formal Nash equilibrium and should be read as an approximate allocation heuristic only. Claims of equilibrium convergence are implementation-dependent and currently unsupported.

### 6.4 Bounded computation
- Cache TTL `_cache_ttl_s=1.0` prevents recomputation each cycle.
- Iteration cap: fixed 10 loops per call.
- Negotiation bounded by token amounts and request caps (e.g., 10% top-ups, lending thresholds).
- Verification: `tests/test_budget.py::test_nash_equilibrium_cache_ttl` asserts TTL cache prevents recompute within window.

### 6.5 Failure modes (≥8) + containment + evidence hook
- FM-AU-1: Starvation of lower-priority module → containment: `negotiate_resources` lends from surplus; health monitor triggers degradation. Evidence: `budget_manager.py`, `monitoring.py`.
- FM-AU-2: Oscillation from repeated reallocations → containment: cache TTL and limited iterations dampen churn. Evidence: `budget_manager.py`.
- FM-AU-3: SLA gaming (slow module hoards budget) → containment: `check_sla` penalizes overshoot reducing future budget. Evidence: `budget_manager.py`.
- FM-AU-4: Cache poisoning/staleness → containment: TTL invalidates after 1s; missing cache recomputes strategies. Evidence: `GameTheoreticBudgetManager`.
- FM-AU-5: Predictive overspend from noisy history → containment: cap on top-up (10% of pool) and penalty on negative budgets during `penalize_cycle`. Evidence: `PredictiveBudgetManager`.
- FM-AU-6: Lending loop creates negative budgets → containment: lending uses `min` and only transfers when surplus>usage+margin; budgets clipped by penalize_cycle. Evidence: `negotiate_resources`, `AdaptiveModuleBudget.penalize_cycle`.
- FM-AU-7: Modules absent/misconfigured → containment: `validate_budget_snapshot` enforces known_modules set before equilibrium use. Evidence: `contracts.py`, `system.py`.
- FM-AU-8: Computational blow-up from large module sets → containment: allocation scales linearly with modules; iteration cap 10; cache keyed by hashed budgets. Evidence: `find_nash_equilibrium`.
- FM-AU-9: Token exhaustion in global_pool → containment: `allocate_cycle` divides by module count; `request` hard-fails and aborts work. Evidence: `budget_manager.py`, `system.py`.

### 6.6 Validation hooks
- Tests: `tests/test_budget.py`, `tests/test_contracts.py`, `tests/test_system.py`.
- Metrics: SLA violation history per module; latency metrics in `MetricsCollector`.
- Artifacts: budget snapshots validated each cycle (`BudgetSnapshot`).

### 6.7 Implementation-dependent notes
- Priorities/urgencies are hardcoded heuristics; equilibrium notion is approximate. Formal mechanism-design guarantees require redesign and proofs.
- No explicit collusion/manipulation defenses; treat auction as guardrail, not incentive-compatible mechanism.

### 6.8 References
[7] R. B. Myerson, “Optimal Auction Design,” *Mathematics of Operations Research*, 1981.  
[8] W. Vickrey, “Counterspeculation, Auctions, and Competitive Sealed Tenders,” *Journal of Finance*, 1961.  
[9] N. Nisan, T. Roughgarden, É. Tardos, and V. Vazirani (eds.), *Algorithmic Game Theory*, Cambridge Univ. Press, 2007.

## 7) Cross-Component Interactions
- RL proposals must satisfy stability gate; budgets throttle both planner and actuator, preventing a single point of failure. Strict actuator gate still blocks unknown actions even if stability/budget logic erred.
- Resource updates influence next-cycle planning (battery depletion) and budgeting; degradation mode feeds back into `degradation_mode` invariant for monitoring.
- Circuit breaker and watchdog (timeout) provide orthogonal containment to budgeting/stability; if any layer fails, the pipeline aborts before actuation. No single gate alone authorizes execution.

## 8) Guarantees / Assumptions / Residual Risks
- Guarantees (repo-backed): budget non-negativity and SLA finiteness (`src/self_constrained_control/contracts.py`, tests); strict-mode action whitelist (`src/self_constrained_control/actuator_module.py`); watchdog timeout raising (`src/self_constrained_control/system.py`); metrics/snapshots emitted (`src/self_constrained_control/metrics.py`), state snapshots from `StateManager` (`src/self_constrained_control/utils.py`), fail-closed stability gate (`planner_module.py`).
- Assumptions: deployment is local/CI; users do not bypass gates (`docs/SAFETY_CASE.md` A1); config files are trusted inputs.
- Residual risks: heuristic Lyapunov form may mis-rank actions; auction heuristics may starve under adversarial patterns; simulator realism is limited (R-001/R-003 in `docs/RISK_REGISTER.md`); pickle artifacts are unsafe with untrusted data.

## 9) Engineering Validity Checklist (PR review)
- Semantic drift: any change to gate logic must update `docs/TRACEABILITY.md` and tests covering REQ-PLN/BUD/ACT.
- Auditability: ensure metrics JSON/Parquet and state snapshots remain deterministic enough for replay; include seeds/configs in PR description.
- Safety/fail-closed: verify strict-mode path still rejects unknown actions; ensure circuit breaker/watchdog paths are exercised in tests.
- Reproducibility: pin seeds (`SystemConfig.seed`), document config used, and keep invariants (`validate_system_scalars`, `validate_budget_snapshot`) intact.

## A) Repo Grounding Index
- Planner / Stability: `src/self_constrained_control/planner_module.py` → `PlannerModule`, `LyapunovStabilityAnalyzer`, `LQRController`; invariants REQ-PLN-0001/0002; tests `tests/test_planner.py::test_planner_rejects_when_unstable`, `tests/test_system.py`.
- Budget / Auction: `src/self_constrained_control/budget_manager.py` → `GameTheoreticBudgetManager`, `PredictiveBudgetManager`, `AdaptiveModuleBudget`; invariants BUD-001/002, SLA-001 (`contracts.py`); tests `tests/test_budget.py::test_nash_equilibrium_cache_ttl`, `tests/test_contracts.py`.
- Safety / Actuation: `src/self_constrained_control/actuator_module.py` → `ActuatorModule.perform`; strict whitelist; tests `tests/test_integration.py`.
- Orchestrator: `src/self_constrained_control/system.py` → `ResourceAwareSystem.process_action/run_loop`, `WatchdogTimer`; invariants INV-001/002/005; tests `tests/test_system.py::test_actuator_not_called_when_budget_denied`, `tests/test_system.py::test_metrics_and_state_artifacts`, `tests/test_integration.py`.
- Monitoring: `src/self_constrained_control/monitoring.py` → `AnomalyDetector`, `BudgetHealthMonitor`, `GracefulDegradation`; tests exercised indirectly via system loop.
- Contracts: `src/self_constrained_control/contracts.py` → `validate_system_scalars`, `validate_budget_snapshot`; tests `tests/test_contracts.py`.

## B) Minimal evidence set
- Mandatory artifacts: `artifacts/metrics/metrics.json` (latencies, battery, energy, bellman_error), `artifacts/state/cycle_*.pkl` snapshots + `.sha256` digests (loadable via `StateManager.load_state`), Parquet optional.
- Mandatory tests: planner stability gate fail-closed (`tests/test_planner.py::test_planner_rejects_when_unstable`), TTL cache (`tests/test_budget.py::test_nash_equilibrium_cache_ttl`), budget denial path (`tests/test_system.py::test_actuator_not_called_when_budget_denied`), metrics/state artifacts (`tests/test_system.py::test_metrics_and_state_artifacts`), plus existing integration/contract tests; CI pipeline running ruff+mypy+pytest (REQ-QLT-0001).
- Mandatory invariants: `INV-001/002/004/005`, `BUD-001/002`, `SLA-001` executed each cycle (`system.py` contract calls). Missing evidence must be added as new tests and traceability rows if functionality changes (proposed when extending).

## 10) References
[1] R. S. Sutton and A. G. Barto, *Reinforcement Learning: An Introduction*, 2nd ed., MIT Press, 2018.  
[2] J. Achiam, D. Held, A. Tamar, and P. Abbeel, “Constrained Policy Optimization,” in *Proc. ICML*, 2017.  
[3] Y. Chow, O. Nachum, M. Ghavamzadeh, and D. Schuurmans, “Lyapunov-based Safe Policy Optimization for Continuous Control,” in *Advances in Neural Information Processing Systems*, 2018.  
[4] H. K. Khalil, *Nonlinear Systems*, 3rd ed., Prentice Hall, 2002.  
[5] A. D. Ames, X. Xu, J. W. Grizzle, and P. Tabuada, “Control Barrier Function Based Quadratic Programs for Safety Critical Systems,” *IEEE Trans. Automatic Control*, vol. 62, no. 8, 2017.  
[6] Z.-P. Jiang and Y. Wang, “Input-to-State Stability for Discrete-Time Nonlinear Systems,” *Automatica*, vol. 37, no. 6, 2001.  
[7] R. B. Myerson, “Optimal Auction Design,” *Math. Oper. Res.*, vol. 6, no. 1, 1981.  
[8] W. Vickrey, “Counterspeculation, Auctions, and Competitive Sealed Tenders,” *J. Finance*, vol. 16, no. 1, 1961.  
[9] N. Nisan, T. Roughgarden, É. Tardos, and V. Vazirani (eds.), *Algorithmic Game Theory*, Cambridge Univ. Press, 2007.  
[10] S. García and F. Fernández, “A Comprehensive Survey on Safe Reinforcement Learning,” *J. Machine Learning Research*, vol. 16, 2015.
