from __future__ import annotations

import asyncio
from pathlib import Path

from self_constrained_control.system import ResourceAwareSystem
from self_constrained_control.utils import load_config, setup_logging


async def main() -> None:
    setup_logging()
    config_path = "data/n1_config.yaml"
    sys = ResourceAwareSystem(load_config(config_path), config_path=config_path)
    await sys.run_loop(["move_arm", "stop"], epochs=1)
    assert Path("artifacts/metrics/metrics.json").exists()


if __name__ == "__main__":
    asyncio.run(main())
