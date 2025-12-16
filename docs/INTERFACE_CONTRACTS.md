# Interface Contracts

This file defines the **stable interfaces** between modules. The intent is to keep the public contract small and testable.

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
