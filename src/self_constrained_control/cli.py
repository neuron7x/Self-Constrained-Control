from __future__ import annotations

import argparse
import asyncio

from .system import ResourceAwareSystem
from .utils import load_config, setup_logging


def _parse_actions(s: str) -> list[str]:
    return [a.strip() for a in s.split(",") if a.strip()]


def main() -> None:
    p = argparse.ArgumentParser(prog="scc")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run")
    run.add_argument("--config", default="data/n1_config.yaml")
    run.add_argument("--actions", default="move_arm,plan_route,stop")
    run.add_argument("--epochs", type=int, default=1)

    args = p.parse_args()
    if args.cmd == "run":
        setup_logging()
        cfg = load_config(args.config)
        sys = ResourceAwareSystem(cfg, config_path=args.config)
        asyncio.run(sys.run_loop(_parse_actions(args.actions), epochs=args.epochs))
