from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from self_constrained_control.planner_module import PlannerModule
from self_constrained_control.rl.reward import compute_reward
from self_constrained_control.system import ResourceAwareSystem


@pytest.mark.asyncio
async def test_training_updates_qtable_deterministically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    planner = PlannerModule(seed=123)
    initial = planner.rl_policy.export_weights().copy()
    await planner.train(epochs=2)
    updated = planner.rl_policy.export_weights().copy()
    assert not np.allclose(initial, updated)

    artifact = Path("artifacts/models/rl_policy.npz")
    artifact.unlink(missing_ok=True)
    artifact.with_suffix(".npz.sha256").unlink(missing_ok=True)

    planner2 = PlannerModule(seed=123)
    await planner2.train(epochs=2)
    assert np.allclose(planner2.rl_policy.export_weights(), updated)


def test_reward_penalizes_positive_delta_v() -> None:
    r_negative = compute_reward(
        delta_v=-0.5,
        spent=10.0,
        available=100.0,
        latency_ms=10.0,
        sla_ms=50.0,
        intent="a",
        action_name="a",
        approved=True,
    )
    r_positive = compute_reward(
        delta_v=0.5,
        spent=10.0,
        available=100.0,
        latency_ms=10.0,
        sla_ms=50.0,
        intent="a",
        action_name="a",
        approved=True,
    )
    assert r_negative > r_positive


def test_rl_respects_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    planner = PlannerModule(seed=42)
    state = np.array([20.0, 20.0], dtype=np.float32)

    monkeypatch.setattr(
        planner.rl_policy,
        "propose_action_distribution",
        lambda _state, k=1: [(0, 1.0, 1.0)],
    )
    monkeypatch.setattr(
        planner.lyapunov,
        "stable",
        lambda *_args, **_kwargs: (False, 0.1),
    )
    action = planner.decide_with_stability(state)
    assert action == 2
    assert planner.rl_fallbacks >= 1


def test_fail_closed_on_corrupt_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    artifact = Path("artifacts/models/rl_policy.npz")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"corrupt")
    artifact.with_suffix(".npz.sha256").write_text("bad", encoding="utf-8")

    planner = PlannerModule()
    assert not planner.rl_enabled
    state = np.array([50.0, 50.0], dtype=np.float32)
    action = planner.decide_with_stability(state)
    assert action in (0, 1, 2)


@pytest.mark.asyncio
async def test_end_to_end_loop_emits_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    data_path = Path(__file__).resolve().parent.parent / "data" / "n1_config.yaml"
    assert data_path.exists()
    system = ResourceAwareSystem(config_path=str(data_path))

    async def fixed_spikes() -> np.ndarray:
        return np.full(system.config.n_channels, 100.0, dtype=np.float32)

    async def fixed_intent(_rates: np.ndarray) -> str:
        return "move_arm"

    async def noop_perform(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(system.n1, "get_neural_spikes", fixed_spikes)
    monkeypatch.setattr(system.decoder, "decode_intent", fixed_intent)
    monkeypatch.setattr(system.actuator, "perform", noop_perform)

    await system.run_loop(actions=["move_arm"], epochs=1)

    model_path = Path("artifacts/models/rl_policy.npz")
    metrics_path = Path("artifacts/metrics/metrics.json")
    assert model_path.exists()
    assert metrics_path.exists()
    metrics = metrics_path.read_text(encoding="utf-8")
    for key in ("rl/epsilon", "rl/td_error_mean", "rl/policy_version"):
        assert key in metrics
