from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys
import time

import pandas as pd

from .backtest import run_backtest
from .config import Config, load_config
from .live import run_live
from .mt5_adapter import (
    account_summary,
    connection,
    discover_symbol,
    load_or_fetch_m1,
    symbol_metadata,
)
from .optimize import optimize
from .reporting import save_backtest, save_optimization
from .strategy import NY, build_day_plan


def _market_data(config: Config, refresh: bool = True):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=config.history_days)
    with connection():
        symbol = discover_symbol(config.canonical_symbol)
        account = account_summary()
        metadata = symbol_metadata(symbol)
        frame = load_or_fetch_m1(
            symbol, start, now, config.cache_dir, refresh=refresh
        )
    return symbol, account, metadata, frame


def _format_pf(value: float) -> str:
    return "inf" if math.isinf(value) else f"{value:.2f}"


def _print_stats(label: str, stats) -> None:
    print(f"\n{label}")
    print(f"ideas                     {stats.trades}")
    print(f"wins / losses / BE        {stats.wins} / {stats.losses} / {stats.breakeven}")
    print(f"win rate                  {stats.win_rate:.2f}%")
    print(f"profit factor             {_format_pf(stats.profit_factor)}")
    print(f"expectancy                {stats.expectancy_r:+.3f}R")
    print(f"net result                {stats.net_r:+.2f}R / ${stats.net_profit:+.2f}")
    print(f"ending balance            ${stats.ending_balance:.2f}")
    print(f"maximum drawdown          {stats.max_drawdown_pct:.2f}%")
    print(f"max consecutive losses    {stats.max_consecutive_losses}")


def command_account(config: Config) -> int:
    with connection():
        account = account_summary()
        symbol = discover_symbol(config.canonical_symbol)
        metadata = symbol_metadata(symbol)
    print("CONNECTED MT5 ACCOUNT")
    for key, value in account.items():
        print(f"{key:24} {value}")
    print("\nAUTO SYMBOL DISCOVERY")
    print(f"{'canonical':24} {config.canonical_symbol}")
    print(f"{'resolved broker symbol':24} {symbol}")
    print(f"{'digits / point':24} {metadata['digits']} / {metadata['point']}")
    print(f"{'configured idea risk':24} {config.risk_pct:.2f}%")
    print(f"{'live submission':24} {'UNLOCKED' if config.live_allowed else 'LOCKED'}")
    return 0


def command_scan(config: Config) -> int:
    symbol, account, metadata, frame = _market_data(config)
    now = datetime.now(timezone.utc)
    plan = build_day_plan(
        frame, symbol, now.astimezone(NY).date(), config, as_of=now
    )
    payload = plan.to_dict()
    payload["observed_at"] = now.isoformat()
    payload["risk_pct"] = config.risk_pct
    payload["risk_cash"] = (
        float(account["balance"]) * config.risk_pct / 100
    )
    payload["broker_point"] = metadata["point"]
    payload["live_submission"] = (
        "UNLOCKED" if config.live_allowed else "LOCKED"
    )
    print(json.dumps(payload, indent=2, default=str))
    return 0


def command_forward(config: Config, cycles: int) -> int:
    path = config.logs_dir / "forward_signals.jsonl"
    seen: set[str] = set()
    done = 0
    while cycles <= 0 or done < cycles:
        symbol, account, metadata, frame = _market_data(config)
        now = datetime.now(timezone.utc)
        plan = build_day_plan(
            frame, symbol, now.astimezone(NY).date(), config, as_of=now
        )
        key = f"{plan.ny_date}:{plan.setup}:{plan.status}"
        if key not in seen:
            seen.add(key)
            payload = {
                "observed_at": now.isoformat(),
                "account": account,
                "broker_point": metadata["point"],
                "risk_pct": config.risk_pct,
                "plan": plan.to_dict(),
            }
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, default=str) + "\n")
            print(
                f"{now.isoformat()} | {symbol} | {plan.setup} | "
                f"{plan.status} | orders={len(plan.orders)}"
            )
        done += 1
        if cycles <= 0 or done < cycles:
            time.sleep(config.poll_seconds)
    return 0


def command_backtest(config: Config) -> int:
    symbol, _, metadata, frame = _market_data(config)
    print(
        f"BACKTEST {symbol} | available data {frame['time'].iloc[0]} -> "
        f"{frame['time'].iloc[-1]} | risk {config.risk_pct:.2f}%"
    )
    result = run_backtest(
        frame, symbol, config, point=float(metadata["point"])
    )
    _print_stats("FULL SAMPLE", result.stats)
    journal, summary = save_backtest(
        result, config.reports_dir, f"{symbol}_baseline"
    )
    print(f"\ntrade journal              {journal}")
    print(f"summary                    {summary}")
    return 0


def command_optimize(config: Config) -> int:
    symbol, _, metadata, frame = _market_data(config)
    print(
        f"TRAIN-ONLY OPTIMIZATION {symbol} | {frame['time'].iloc[0]} -> "
        f"{frame['time'].iloc[-1]} | risk {config.risk_pct:.2f}%"
    )
    payload = optimize(
        frame, symbol, config, point=float(metadata["point"])
    )
    print("\nBEST PARAMETERS (selected on training only)")
    for key, value in payload["best_parameters"].items():
        print(f"{key:24} {value}")
    for key, label in (
        ("training", "TRAINING"),
        ("validation", "VALIDATION"),
        ("untouched_holdout", "UNTOUCHED HOLDOUT"),
        ("full_sample", "FULL SAMPLE — descriptive only"),
    ):
        stats = type("StatsView", (), payload[key])()
        _print_stats(label, stats)
    print(
        "\nSTATUS: "
        + (
            "FORWARD APPROVED"
            if payload["approved_for_forward"]
            else "NOT APPROVED"
        )
    )
    for reason in payload["reasons"]:
        print(f"  - {reason}")
    path = save_optimization(payload, config.reports_dir)
    print(f"optimization report        {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nasdaq-weakness")
    parser.add_argument(
        "command",
        choices=(
            "account",
            "scan",
            "forward",
            "backtest",
            "optimize",
            "live",
        ),
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=0,
        help="Number of scanner/live cycles; 0 runs continuously",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = load_config(Path.cwd())
        commands = {
            "account": command_account,
            "scan": command_scan,
            "forward": lambda value: command_forward(value, args.cycles),
            "backtest": command_backtest,
            "optimize": command_optimize,
            "live": lambda value: (run_live(value, args.cycles) or 0),
        }
        return commands[args.command](config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
