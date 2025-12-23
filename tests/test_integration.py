from __future__ import annotations

from pathlib import Path

import pytest

from self_constrained_control.system import ResourceAwareSystem


@pytest.mark.asyncio
async def test_artifacts_written(config_data: dict[str, object], tmp_path: Path):
    # run in temp cwd for artifact isolation
    import os

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        sys = ResourceAwareSystem(config_data, config_path="data/n1_config.yaml")
        await sys.run_loop(["move_arm", "stop"], epochs=1)
        assert Path("artifacts/metrics/metrics.json").exists()
        assert any(Path("artifacts/state").glob("cycle_*.pkl"))
    finally:
        os.chdir(cwd)
