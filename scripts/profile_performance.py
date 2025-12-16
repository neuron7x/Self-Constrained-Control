from __future__ import annotations

import asyncio
import cProfile
import pstats
from pathlib import Path

from self_constrained_control.system import ResourceAwareSystem


async def _run() -> None:
    sys = ResourceAwareSystem("data/n1_config.yaml")
    await sys.run_loop(["move_arm", "plan_route", "stop"], epochs=1)


def main() -> None:
    prof = cProfile.Profile()
    prof.enable()
    asyncio.run(_run())
    prof.disable()
    out = Path("artifacts/profile")
    out.parent.mkdir(parents=True, exist_ok=True)
    stats = pstats.Stats(prof).sort_stats("tottime")
    stats.dump_stats(str(out) + ".pstats")


if __name__ == "__main__":
    main()
