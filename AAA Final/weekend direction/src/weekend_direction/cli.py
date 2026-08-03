from __future__ import annotations

import argparse
from dataclasses import replace
import json

from .backtest import run as backtest_run
from .config import Config
from .live import configure_logging, run_live, run_once


def main() -> None:
    parser = argparse.ArgumentParser(prog="weekend-direction")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("paper")
    sub.add_parser("live")
    backtest = sub.add_parser("backtest")
    backtest.add_argument("--no-refresh", action="store_true")
    args = parser.parse_args()
    configure_logging()
    config = Config.load()
    if args.command == "backtest":
        print(json.dumps(backtest_run(refresh=not args.no_refresh), indent=2))
    elif args.command == "paper":
        paper = replace(config, live_trading=False, place_orders=False, dry_run=True)
        print(run_once(paper))
    else:
        run_live(config)
