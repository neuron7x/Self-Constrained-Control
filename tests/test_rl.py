from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from self_constrained_control.planner_module import PlannerModule
from self_constrained_control.rl import (
    Policy,
    PolicyArtifact,
    Trainer,
    TrajectoryBuffer,
    Transition,
    budget_efficiency,
    compute_reward,
    load_policy_artifact,
    save_policy_artifact,
    sla_penalty,
)
from self_constrained_control.system import ResourceAwareSystem
from self_constrained_control.utils import load_config


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
    system = ResourceAwareSystem(load_config(str(data_path)), config_path=str(data_path))

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


def test_trajectory_buffer_capacity_and_iteration() -> None:
    buf = TrajectoryBuffer(capacity=2)
    t1 = Transition(np.zeros(2, dtype=np.float32), 0, 0.0, np.zeros(2, dtype=np.float32), False)
    t2 = Transition(np.ones(2, dtype=np.float32), 1, 1.0, np.ones(2, dtype=np.float32), False)
    t3 = Transition(
        np.full(2, 2.0, dtype=np.float32), 2, 2.0, np.full(2, 2.0, dtype=np.float32), True
    )
    buf.add(t1)
    buf.add(t2)
    buf.add(t3)
    assert len(buf) == 2
    all_items = buf.all()
    assert all_items[0] == t2 and all_items[1] == t3
    assert tuple(buf.iter_deterministic()) == (t2, t3)


def test_policy_and_trainer_notimplemented() -> None:
    policy = Policy()
    trainer = Trainer()
    with pytest.raises(NotImplementedError):
        policy.propose_action_distribution(np.zeros(2, dtype=np.float32))
    with pytest.raises(NotImplementedError):
        policy.propose_action(np.zeros(2, dtype=np.float32))
    with pytest.raises(NotImplementedError):
        trainer.train_step(
            Transition(np.zeros(2, dtype=np.float32), 0, 0.0, np.zeros(2, dtype=np.float32), False)
        )
    with pytest.raises(NotImplementedError):
        trainer.train_epochs(TrajectoryBuffer(), 1)


def test_reward_edge_cases() -> None:
    assert budget_efficiency(1.0, 0.0) == -1.0
    assert sla_penalty(10.0, 0.0) == -1.0


def test_persistence_missing_and_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_policy_artifact("artifacts/models/rl_policy.npz")

    weights = np.ones((2, 2, 3), dtype=np.float32)
    artifact = PolicyArtifact(
        schema_version="1.0",
        algo="tabular_q_learning",
        hyperparams={"gamma": 0.9},
        weights=weights,
        feature_spec={"state_bins": (2, 2)},
        action_mapping=[0, 1, 2],
        seed=123,
        timestamp=0.0,
        policy_version="v5",
    )
    save_policy_artifact(artifact)
    loaded = load_policy_artifact()
    assert loaded.policy_version == "v5"
    assert loaded.weights.shape == weights.shape


def test_planner_budget_gate_rejection_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    planner = PlannerModule(seed=7)
    state = np.array([1.0, 1.0], dtype=np.float32)
    monkeypatch.setattr(
        planner.rl_policy, "propose_action_distribution", lambda _s, k=1: [(0, 1.0, 0.0)]
    )
    action = planner.decide_with_stability(state)
    assert action == 2
    assert planner.rl_gate_rejections >= 1


@pytest.mark.asyncio
async def test_planner_train_disabled_returns_early(monkeypatch: pytest.MonkeyPatch) -> None:
    planner = PlannerModule(seed=5)
    planner.rl_enabled = False
    await planner.train(epochs=1)
    assert planner.rl_updates == 0


def test_planner_load_model_success_sets_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    weights = np.full((11, 11, 3), 0.5, dtype=np.float32)
    artifact = PolicyArtifact(
        schema_version="1.0",
        algo="tabular_q_learning",
        hyperparams={"gamma": 0.9},
        weights=weights,
        feature_spec={"state_bins": (11, 11)},
        action_mapping=[0, 1, 2],
        seed=1,
        timestamp=0.0,
        policy_version="v3",
    )
    save_policy_artifact(artifact)
    planner = PlannerModule(seed=1)
    assert planner.rl_policy_version == "v3"
    assert planner.rl_version_counter >= 3


def test_planner_load_model_bad_version_counter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    weights = np.full((11, 11, 3), 0.2, dtype=np.float32)
    artifact = PolicyArtifact(
        schema_version="1.0",
        algo="tabular_q_learning",
        hyperparams={"gamma": 0.9},
        weights=weights,
        feature_spec={"state_bins": (11, 11)},
        action_mapping=[0, 1, 2],
        seed=1,
        timestamp=0.0,
        policy_version="abc",
    )
    save_policy_artifact(artifact)
    planner = PlannerModule(seed=2)
    assert planner.rl_policy_version == "abc"
    assert planner.rl_version_counter >= 0


@pytest.mark.asyncio
async def test_system_sets_rl_metrics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    data_path = Path(__file__).resolve().parent.parent / "data" / "n1_config.yaml"
    system = ResourceAwareSystem(load_config(str(data_path)), config_path=str(data_path))

    async def fixed_spikes() -> np.ndarray:
        return np.full(system.config.n_channels, 120.0, dtype=np.float32)

    async def fixed_intent(_rates: np.ndarray) -> str:
        return "move_arm"

    async def noop_perform(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(system.n1, "get_neural_spikes", fixed_spikes)
    monkeypatch.setattr(system.decoder, "decode_intent", fixed_intent)
    monkeypatch.setattr(system.actuator, "perform", noop_perform)

    await system.process_action("move_arm")
    snapshot = system.metrics.snapshot()
    assert snapshot.get("rl")


def test_lqr_control_initializes_gain() -> None:
    controller = PlannerModule().lqr
    state = np.array([50.0, 50.0], dtype=np.float32)
    target = np.array([75.0, 75.0], dtype=np.float32)
    out = controller.control(state, target)
    assert out.shape == (controller.B.shape[1],)


def test_decide_rule_based_force_simplify() -> None:
    planner = PlannerModule()
    planner.force_simplify = True
    assert planner.decide_rule_based(np.array([10.0, 10.0], dtype=np.float32)) == 1
