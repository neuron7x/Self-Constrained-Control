from __future__ import annotations

import pytest

from self_constrained_control.system import ResourceAwareSystem

@pytest.mark.asyncio
async def test_system_run_loop_smoke(config_path: str):
    sys = ResourceAwareSystem(config_path)
    await sys.run_loop(["move_arm", "stop"], epochs=1)
    assert 0.0 <= sys.battery <= 100.0
    assert 0.0 <= sys.user_energy <= 100.0
