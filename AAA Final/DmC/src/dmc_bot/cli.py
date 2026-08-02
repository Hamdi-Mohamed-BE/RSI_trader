from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import logging
import math
import re

import MetaTrader5 as mt5
import pandas as pd

from .config import load_config
from .live import run_live
from .mt5_data import account_summary, connection, discover_symbol, load_or_fetch_m1
from .strategy import run_backtest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dumb Money Concepts pullback bot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("account")
    backtest = sub.add_parser("backtest")
    backtest.add_argument("--days", type=int, default=60)
    backtest.add_argument("--balance", type=float, default=1000.0)
    backtest.add_argument(
        "--symbol",
        help="Test one configured instrument instead of the complete basket",
    )
    live = sub.add_parser("live")
    live.add_argument("--once", action="store_true")
    return parser


def _configure_logging(root) -> None:
    (root / "logs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)sZ | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(root / "logs" / "dmc.log", encoding="utf-8")],
    )


def _print_account(account: dict[str, object]) -> None:
    print(
        f"Account {account['login']} | {account['server']} | "
        f"balance {account['balance']:.2f} {account['currency']} | "
        f"equity {account['equity']:.2f} | free margin {account['free_margin']:.2f} | "
        f"leverage 1:{account['leverage']}"
    )


def _write_backtest_report(
    config,
    symbol: str,
    effective_start: datetime,
    effective_end: datetime,
    trades,
    metrics,
) -> None:
    report_dir = config.root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    safe_symbol = re.sub(r"[^A-Za-z0-9_.-]", "_", symbol)
    stem = f"dmc_{safe_symbol}_{effective_start.date()}_{effective_end.date()}"
    pd.DataFrame([trade.row() for trade in trades]).to_csv(
        report_dir / f"{stem}_trades.csv", index=False
    )
    payload = {
        "symbol": symbol,
        "config": {key: str(value) for key, value in asdict(config).items()},
        "metrics": asdict(metrics),
    }
    (report_dir / f"{stem}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    pf = "inf" if math.isinf(metrics.profit_factor) else f"{metrics.profit_factor:.2f}"
    print(
        f"\nDmC backtest | {symbol} | "
        f"{effective_start.isoformat()} -> {effective_end.isoformat()}"
    )
    print(
        f"Trades {metrics.trades} | W/L {metrics.wins}/{metrics.losses} | "
        f"Win rate {metrics.win_rate_pct:.2f}%"
    )
    print(
        f"PF {pf} | Net {metrics.net_r:+.2f}R | "
        f"Return {metrics.return_pct:+.2f}% | Ending {metrics.ending_balance:.2f}"
    )
    print(
        f"Realized max DD {metrics.max_realized_dd_pct:.2f}% | "
        f"Intratrade max DD {metrics.max_intratrade_dd_pct:.2f}%"
    )
    print(f"Report: {report_dir / f'{stem}.json'}")


def main() -> None:
    args = _parser().parse_args()
    config = load_config()
    _configure_logging(config.root)
    with connection():
        account = account_summary()
        _print_account(account)
        if args.command == "account":
            hints = (
                [item.canonical_symbol for item in config.instruments]
                if config.instruments
                else [config.canonical_symbol]
            )
            for hint in hints:
                instrument_config = config.for_instrument(hint)
                symbol = discover_symbol(hint)
                print(
                    f"  {hint} -> {symbol} | stop {instrument_config.stop_points:g} | "
                    f"trail {instrument_config.trail_start_r:g}R/"
                    f"{instrument_config.trail_distance_r:g}R | "
                    f"max spread {instrument_config.max_spread_points:g} points"
                )
            print(
                f"Risk {config.risk_pct:.2f}% per idea | "
                f"DmC basket cap {config.max_total_risk_pct:.2f}%"
            )
            return
        if args.command == "live":
            run_live(config, once=args.once)
            return
        end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        start = end - timedelta(days=args.days)
        hints = (
            [args.symbol]
            if args.symbol
            else [item.canonical_symbol for item in config.instruments]
            if config.instruments
            else [config.canonical_symbol]
        )
        for hint in hints:
            instrument_config = config.for_instrument(hint)
            warmup_days = (
                120
                if instrument_config.h1_confirmation_mode == "body_level"
                or instrument_config.target_mode == "next_body"
                else 10
            )
            warmup = start - timedelta(days=warmup_days)
            symbol = discover_symbol(hint)
            info = mt5.symbol_info(symbol)
            if info is None:
                raise RuntimeError(f"Cannot read {symbol} metadata")
            frame = load_or_fetch_m1(
                symbol,
                warmup,
                end,
                config.root / "data",
                refresh=True,
            )
            effective_start = max(start, frame.time.min().to_pydatetime())
            effective_end = min(end, frame.time.max().to_pydatetime())
            trades, metrics = run_backtest(
                frame,
                instrument_config,
                point=float(info.point),
                start=effective_start,
                end=effective_end,
                starting_balance=args.balance,
            )
            _write_backtest_report(
                instrument_config,
                symbol,
                effective_start,
                effective_end,
                trades,
                metrics,
            )


if __name__ == "__main__":
    main()
