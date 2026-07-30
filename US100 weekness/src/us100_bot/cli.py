from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path

import pandas as pd

from .analytics import metrics, trades_frame
from .config import load_config
from .live import run_loop
from .mt5_data import connection, discover, load_or_fetch
from .normalization import PriceNormalizer
from .optimizer import robustness, walk_forward
from .reporting import write_report
from .strategies import Backtest


def configure_logging(log_dir: Path, level: str = "INFO") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "us100.log", encoding="utf-8"),
    ]
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)sZ | %(levelname)-7s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )


def _date(value: str, end: bool = False) -> datetime:
    dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return dt + timedelta(days=1) if end else dt


def main() -> None:
    parser = argparse.ArgumentParser(description="US100 New York strategy bot")
    parser.add_argument("--env", default=".env")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover")
    back = sub.add_parser("backtest")
    back.add_argument("--start", default="")
    back.add_argument("--end", default="")
    back.add_argument("--refresh", action="store_true")
    back.add_argument("--skip-optimization", action="store_true")
    live = sub.add_parser("live")
    live.add_argument("--once", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.env)
    configure_logging(cfg.log_dir)

    with connection(cfg) as (account, terminal):
        spec, ranked = discover(cfg)
        norm = PriceNormalizer(spec, cfg.pip_size)
        if args.command == "discover":
            print(json.dumps({
                "selected": spec.name,
                "description": spec.description,
                "conversion": norm.describe(),
                "top_candidates": [
                    {"symbol": c.symbol, "score": c.score, "reasons": c.reasons}
                    for c in ranked[:10]
                ],
                "account": {
                    "login": account.login, "server": account.server,
                    "balance": account.balance, "equity": account.equity,
                },
            }, indent=2, default=str))
            return
        if args.command == "live":
            run_loop(cfg, spec, norm, once=args.once)
            return

        # Latest complete broker-data year by default.
        end = _date(args.end, end=True) if args.end else datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start = _date(args.start) if args.start else end - timedelta(days=365)
        bars, data_path = load_or_fetch(cfg, spec.name, start, end, args.refresh)
        baseline, baseline_skips = Backtest(cfg, norm).run(bars)
        if args.skip_optimization:
            oos, oos_skips, wf = [], [], pd.DataFrame()
        else:
            oos, oos_skips, wf = walk_forward(bars, cfg, norm)
        robust = robustness(bars, cfg, norm)
        paths = write_report(
            cfg, spec, norm, baseline, baseline_skips, oos, oos_skips,
            wf, robust, str(start.date()), str((end - timedelta(days=1)).date()),
            data_path, len(bars),
        )
        base_metrics = metrics(trades_frame(baseline), cfg.starting_balance)
        oos_metrics = metrics(trades_frame(oos), cfg.starting_balance)
        print(json.dumps({
            "symbol": spec.name,
            "period": [str(start.date()), str((end - timedelta(days=1)).date())],
            "bars": len(bars),
            "conversion": norm.describe(),
            "baseline": base_metrics,
            "walk_forward_oos": oos_metrics,
            "files": {k: str(v) for k, v in paths.items()},
        }, indent=2, default=str))

