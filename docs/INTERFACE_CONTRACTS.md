# Interface Contracts

This file defines the **stable interfaces** between modules. The intent is to keep the public contract small and testable.

## Orchestrator

### `ResourceAwareSystem(config: SystemConfig | dict[str, Any], *, config_path: str | None = None)`
- Caller provides an in-memory configuration (dict or `SystemConfig`); no file I/O occurs inside the constructor. `config_path` is optional metadata and is not read.
- Logging bootstrap is owned by the CLI entrypoint (`src/self_constrained_control/cli.py`); importing `self_constrained_control` must not mutate global logging handlers or levels.

## Neural Interface

### `N1Simulator.get_neural_spikes() -> np.ndarray`
- Returns firing rates as `float32` array with shape `(n_channels,)`.
- Invariants:
  - all finite
  - `0 <= rate <= max_firing_hz`
- Failure: raises `ValueError` if validation fails.

### `IntentionDecoder.decode_intent(firing_rates) -> str`
- Pure mapping from rates → action label.
- Must be deterministic for a given `firing_rates`.

## Planner

### `PlannerModule.decide_with_stability(state) -> int`
- Input: `state = [battery_pct, user_energy_pct]`.
- Output: action index in `{0,1,2}`.
- Guarantees:
  - always returns a valid action
  - prefers stability (∆V < 0) when a candidate exists.

### RL proposal interfaces (advisory only)
- `self_constrained_control.rl.policy.Policy`
  - `propose_action_distribution(state, k)` returns ranked candidate actions with probabilities.
  - `propose_action(state)` returns a single action proposal (epsilon-greedy).
- `self_constrained_control.rl.trainer.Trainer`
  - `train_step(transition)` performs one update; returns TD error.
  - `train_epochs(buffer, epochs)` runs bounded epochs over deterministic buffer.
- `self_constrained_control.rl.buffer.TrajectoryBuffer`
  - Append-only, deterministic iteration for reproducible training.
- `self_constrained_control.rl.reward.compute_reward(...)`
  - Pure function combining ∆V penalty, budget efficiency, SLA penalty, and task success.

### Persistence and metrics contracts
- `self_constrained_control.rl.persistence.save_policy_artifact` / `load_policy_artifact`
  - Persist/restore tabular policy weights with `schema_version`, `hyperparams`, `action_mapping`, `seed`, `policy_version`; `.sha256` must match or RL is disabled (fail-closed).
  - Artifact path: `artifacts/models/rl_policy.npz` + `.sha256`.
- Metrics (`MetricsCollector.snapshot()`):
  - RL metrics exported under keys `rl/epsilon`, `rl/td_error_mean`, `rl/updates`, `rl/policy_version`, `rl/fallback_rate`, `rl/gate_rejection_rate` alongside latency/battery/user_energy/bellman_error.

## Budget Manager

### `BudgetManager.allocate_cycle()`
- Allocates resources for a cycle.
- Postcondition:
  - every module’s `budget` is finite and ≥ 0.

### `BudgetManager.check_sla(name, actual_latency_ms)`
- Triggers penalty logic when SLA violated.

## Degradation

### `GracefulDegradation.assess_and_degrade(...)`
- Computes degradation mode based on thresholds and health.
- Output is one of `FULL|REDUCED|MINIMAL|SAFE`.

## Runtime Contracts
See `src/self_constrained_control/contracts.py` for the canonical invariant IDs.
