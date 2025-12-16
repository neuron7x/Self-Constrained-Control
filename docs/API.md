# API

## Core objects

- `N1Simulator`: neural population simulator, returns firing rates
- `IntentionDecoder`: intent label from firing rates
- `PlannerModule`: stability-aware decision engine
- `GameTheoreticBudgetManager`: multi-step budget allocator
- `ResourceAwareSystem`: async orchestrator: decode → plan → act → monitor

## Public surface

```python
from self_constrained_control.system import ResourceAwareSystem

sys = ResourceAwareSystem("data/n1_config.yaml")
await sys.run_loop(actions=["move_arm","stop"], epochs=2)
```

## CLI

```bash
scc run --config data/n1_config.yaml --actions move_arm,plan_route,stop --epochs 2
```
