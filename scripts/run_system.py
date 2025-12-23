from __future__ import annotations

import argparse
import asyncio

from self_constrained_control.system import ResourceAwareSystem
from self_constrained_control.utils import load_config, setup_logging


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="data/n1_config.yaml")
    ap.add_argument("--actions", default="move_arm,plan_route,stop")
    ap.add_argument("--epochs", type=int, default=1)
    args = ap.parse_args()

    setup_logging()
    sys = ResourceAwareSystem(load_config(args.config), config_path=args.config)
    actions = [a.strip() for a in args.actions.split(",") if a.strip()]
    asyncio.run(sys.run_loop(actions, epochs=args.epochs))


if __name__ == "__main__":
    main()
