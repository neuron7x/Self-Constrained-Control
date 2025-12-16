from __future__ import annotations

import asyncio
from pathlib import Path

from self_constrained_control.system import ResourceAwareSystem


async def main() -> None:
    sys = ResourceAwareSystem("data/n1_config.yaml")
    await sys.run_loop(["move_arm", "stop"], epochs=1)
    assert Path("artifacts/metrics/metrics.json").exists()


if __name__ == "__main__":
    asyncio.run(main())
