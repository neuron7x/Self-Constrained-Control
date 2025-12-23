from __future__ import annotations

from pathlib import Path

import pytest

from self_constrained_control.system import ResourceAwareSystem


@pytest.mark.asyncio
async def test_system_run_loop_smoke(config_path: str):
    sys = ResourceAwareSystem(config_path)
    await sys.run_loop(["move_arm", "stop"], epochs=1)
    assert 0.0 <= sys.battery <= 100.0
    assert 0.0 <= sys.user_energy <= 100.0


@pytest.mark.asyncio
async def test_actuator_not_called_when_budget_denied(tmp_path, monkeypatch):
    cfg_text = Path("data/n1_config.yaml").read_text(encoding="utf-8")
    cfg_text = cfg_text.replace("global_resource_pool: 1000.0", "global_resource_pool: 1.0")
    cfg_text = cfg_text.replace("planner_budget: 400.0", "planner_budget: 250.0")
    cfg_text = cfg_text.replace("actuator_budget: 400.0", "actuator_budget: 50.0")
    cfg_text = cfg_text.replace("n_channels: 128", "n_channels: 16")
    cfg_path = tmp_path / "n1_config.yaml"
    cfg_path.write_text(cfg_text, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    sys = ResourceAwareSystem(str(cfg_path))

    async def _intent_always_matches(_firing):
        return "move_arm"

    monkeypatch.setattr(sys.decoder, "decode_intent", _intent_always_matches)

    called = {"act": False}

    async def _guarded_perform(action_name: str, simplified: bool = False) -> None:
        called["act"] = True

    monkeypatch.setattr(sys.actuator, "perform", _guarded_perform)
    await sys.run_loop(["move_arm"], epochs=1)
    assert called["act"] is False


@pytest.mark.asyncio
async def test_metrics_and_state_artifacts(tmp_path, monkeypatch, config_path: str):
    import json

    monkeypatch.chdir(tmp_path)
    sys = ResourceAwareSystem(config_path)

    async def _intent_always_matches(_firing):
        return "move_arm"

    monkeypatch.setattr(sys.decoder, "decode_intent", _intent_always_matches)
    await sys.run_loop(["move_arm"], epochs=1)

    metrics_path = Path("artifacts/metrics/metrics.json")
    assert metrics_path.exists()
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    for key in ("ts", "battery", "user_energy", "bellman_error", "latencies_s"):
        assert key in data

    state_dir = Path("artifacts/state")
    pkls = sorted(state_dir.glob("*.pkl"))
    assert pkls, "state snapshots not found"
    for pkl in pkls:
        digest = pkl.with_suffix(".sha256")
        assert digest.exists()
        sys.state.load_state(pkl.stem)
