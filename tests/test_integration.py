from __future__ import annotations

import pytest
from pathlib import Path

from self_constrained_control.system import ResourceAwareSystem

@pytest.mark.asyncio
async def test_artifacts_written(config_path: str, tmp_path: Path):
    # run in temp cwd for artifact isolation
    import os
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # Need config file in temp working dir
        Path("data").mkdir(parents=True, exist_ok=True)
        Path(config_path).write_text(Path(config_path).read_text(encoding="utf-8"), encoding="utf-8")
        Path("data/n1_config.yaml").write_text(Path(config_path).read_text(encoding="utf-8"), encoding="utf-8")
        sys = ResourceAwareSystem("data/n1_config.yaml")
        await sys.run_loop(["move_arm", "stop"], epochs=1)
        assert Path("artifacts/metrics/metrics.json").exists()
        assert any(Path("artifacts/state").glob("cycle_*.pkl"))
    finally:
        os.chdir(cwd)
