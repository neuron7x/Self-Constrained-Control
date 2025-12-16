# System Architecture (SAD-lite)

## 0. Architectural intent

This architecture is designed for a specific engineering goal:

> **Make the “smart” parts advisory, and make the “safe/bounded” parts mandatory.**

In practice this means:
- Planning/RL can propose actions, but cannot bypass budgets, safety gating, watchdog, or circuit breaker.
- The actuator is the **last line of defense** and must fail closed in strict mode.
- Monitoring produces artifacts that enable objective evaluation (latency, budget depletion, anomalies).

## 1. Component model

### 1.1 Modules and responsibilities

- **Neural interface (`neural_interface.py`)**
  - Produces a rate vector; may apply optional correlations and fatigue hooks.
  - Guarantees: bounded length, bounded range, finite outputs.

- **Decoder (`neural_interface.py` / `IntentionDecoder`)**
  - Maps rate vector → intent label.
  - Policy: deterministic thresholds by default.

- **Planner (`planner_module.py`)**
  - Produces a discrete decision `{execute, simplify, reject}`.
  - Uses: rule baseline + optional RL + stability gate.

- **Budgeting (`budget_manager.py`)**
  - Allocates abstract resource tokens.
  - Enforces module budgets and SLA penalties.
  - Optional equilibrium caching.

- **Actuator (`actuator_module.py`)**
  - Applies safety mode gating.
  - Executes a stub action with simulated latency.

- **Monitoring (`monitoring.py`, `metrics.py`, `utils.py`)**
  - Anomaly detection (latency), graceful degradation signals, persistence snapshots.

- **Orchestrator (`system.py`)**
  - Owns control loop ordering and boundary checks.
  - Ensures all gates are applied before actuation.

## 2. Dataflow and controlflow

### 2.1 Per-cycle pipeline

```
+----------+     +----------+     +----------+     +----------+
| Simulator| --> | Decoder  | --> | Planner  | --> | Actuator |
+----------+     +----------+     +----------+     +----------+
      |               |               |                |
      v               v               v                v
  Metrics/Logs    Budget Gate     Stability Gate   Safety Mode Gate
      |               |               |                |
      +------------------- Orchestrator (system.py) ---+
```

### 2.2 Mandatory gates (cannot be bypassed)

1) **Circuit breaker** around simulator and actuator calls.
2) **Budget checks** prior to decoder/planner/actuator work.
3) **Intent match** prior to planning and actuation.
4) **Stability gate** prior to approving execution.
5) **Safety mode gate** inside actuator.
6) **Watchdog** for progress.

## 3. State model

### 3.1 System state

- `battery`: proxy resource ∈ [0,100]
- `user_energy`: proxy ∈ [0,100]
- `budgets`: per module budgets (remaining + usage)
- `metrics`: latency series, errors, snapshots

### 3.2 Persistence

State persistence is implemented as a **snapshot artifact** suitable for debugging and regression. It is not a secure storage layer.

Constraints:
- Snapshots must not contain secrets or personal data.
- Snapshot schema stability is tracked by SemVer and ADR.

## 4. Concurrency model

- The orchestrator uses asyncio and locks (`resource_lock`, `decision_lock`) to prevent race conditions between resource monitoring and decision work.
- All expensive or failure-prone calls are wrapped by `CircuitBreaker.call()`.

## 5. Error handling policy

- **Fail closed** for actuation:
  - Any exception in simulator/decoder/planner causes the current action to abort before actuator call.
  - Unknown actions in strict mode raise immediately.

- **Observable failures**:
  - All errors must be logged with enough context to reproduce.

## 6. Extensibility boundaries

### 6.1 Replaceable backends

- **Simulator backend**: replace `N1Simulator` with real acquisition adapter, keeping the contract `-> np.ndarray`.
- **Planner backend**: replace RL or add constrained optimization; must still output `{0,1,2}` and obey the gate.
- **Actuator backend**: integrate ROS2/hardware behind an interface; strict gating remains mandatory.

### 6.2 Compatibility rule

If a replacement changes behavior, it MUST:
- update requirements (REQ),
- add or update tests (VER),
- and record an ADR.

## 7. Performance posture

Performance goals are secondary to correctness and boundedness.
The architecture supports:
- caching at decision boundaries,
- optional vectorization/JIT in simulation,
- optional GPU in planning.

Benchmarks are informational until the project adds stable performance requirements.

## 8. Security posture (minimal)

- No network services by default.
- No secret storage.
- Artifacts are written to local disk.

See `SECURITY.md` and `docs/RISK_REGISTER.md`.
