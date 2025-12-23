from __future__ import annotations

import asyncio
from pathlib import Path

from self_constrained_control.system import ResourceAwareSystem
from self_constrained_control.utils import load_config, setup_logging


async def main() -> None:
    setup_logging()
    sys = ResourceAwareSystem(load_config("data/n1_config.yaml"), config_path="data/n1_config.yaml")
    await sys.run_loop(["move_arm", "stop"], epochs=1)
    assert Path("artifacts/metrics/metrics.json").exists()


if __name__ == "__main__":
    asyncio.run(main())
