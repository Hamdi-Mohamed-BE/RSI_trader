from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys
import time

import pandas as pd

from .backtest import run_backtest
from .config import AppConfig, load_config
from .mt5_adapter import (
    account_summary,
    connection,
    discover_symbol,
    load_or_fetch_m1,
    symbol_info,
    volume_for_risk,
)
from .profiles import build_completed_profile_maps, profiles_for_row
from .reporting import save_backtest, save_validation
from .risk import risk_cash
from .sessions import resample_ohlcv, timeframe_rule
from .strategy import evaluate_signals, watch_snapshot
from .structure import enrich_structure
from .validation import run_validation
from .zones import build_zone_timeline


def _project_dir() -> Path:
    return Path.cwd()


def _format_number(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.2f}"


def _market_data(
    config: AppConfig,
    days: int | None = None,
    refresh: bool = False,
):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days or config.history_days)
    with connection():
        symbol = discover_symbol(config.canonical_symbol)
        account = account_summary()
        metadata = symbol_info(symbol)
        frame = load_or_fetch_m1(
            symbol, start, end, config.cache_dir, refresh=refresh
        )
    return symbol, account, metadata, frame


def command_account(config: AppConfig) -> int:
    with connection():
        account = account_summary()
        symbol = discover_symbol(config.canonical_symbol)
        metadata = symbol_info(symbol)
    print("CONNECTED MT5 ACCOUNT")
    for key, value in account.items():
        print(f"{key:24} {value}")
    print("\nSYMBOL RESOLUTION")
    print(f"{config.canonical_symbol:24} {symbol}")
    print(f"{'volume range':24} {metadata['volume_min']} - {metadata['volume_max']}")
    print(f"{'configured risk':24} {config.risk_pct:.2f}%")
    print(f"{'live submission':24} {'UNLOCKED' if config.live_submission_allowed else 'LOCKED'}")
    return 0


def _latest_context(
    frame: pd.DataFrame,
    symbol: str,
    config: AppConfig,
):
    analysis = enrich_structure(
        resample_ohlcv(frame, timeframe_rule(config.analysis_timeframe))
    )
    h1 = enrich_structure(
        resample_ohlcv(frame, timeframe_rule(config.execution_timeframe))
    )
    htf = analysis[["time", "trend", "structure_break"]].rename(
        columns={
            "trend": "htf_trend",
            "structure_break": "htf_structure_break",
        }
    )
    h1 = pd.merge_asof(
        h1.sort_values("time"),
        htf.sort_values("time"),
        on="time",
        direction="backward",
    )
    h1["ltf_trend"] = h1["trend"]
    h1["trend"] = h1["htf_trend"].fillna(h1["trend"])
    h1["structure_break"] = h1["htf_structure_break"].fillna(
        h1["structure_break"]
    )
    daily, weekly = build_completed_profile_maps(
        frame, config.profile_rows, config.value_area_pct
    )
    # The newest resampled bar is still forming.
    index = len(h1) - 2
    row = h1.iloc[index]
    profiles = profiles_for_row(row, daily, weekly)
    analysis_zone_timeline = build_zone_timeline(
        analysis, config.zone_lookback, config.zone_max_touches
    )
    analysis_index = int(
        analysis["time"].searchsorted(row["time"], side="right") - 1
    )
    zones = (
        analysis_zone_timeline[analysis_index]
        if 0 <= analysis_index < len(analysis_zone_timeline)
        else ()
    )
    signals = evaluate_signals(
        h1, index, symbol, profiles, zones, config, apply_min_grade=True
    )
    return h1, index, profiles, zones, signals


def command_scan(config: AppConfig) -> int:
    symbol, account, metadata, frame = _market_data(
        config, min(config.history_days, 90), refresh=True
    )
    h1, index, profiles, zones, signals = _latest_context(
        frame, symbol, config
    )
    print(
        f"LTA GOLD SCAN | {symbol} | "
        f"risk {config.risk_pct:.2f}% = "
        f"${risk_cash(float(account['balance']), config.risk_pct):.2f}"
    )
    if not signals:
        snapshot = watch_snapshot(h1, index, profiles, zones)
        print("NO A/A+ CONFIRMED SETUP")
        print(json.dumps(snapshot, indent=2, default=str))
        return 0
    signal = signals[0]
    cash = risk_cash(float(account["balance"]), config.risk_pct)
    with connection():
        volume = volume_for_risk(
            symbol, signal.direction, signal.entry, signal.stop, cash
        )
    print("CONFIRMED RESEARCH SIGNAL — ORDER NOT SENT")
    print(f"grade/model       {signal.grade} / {signal.model}")
    print(f"direction         {signal.direction.upper()}")
    print(f"entry             {signal.entry:.3f}")
    print(f"stop              {signal.stop:.3f}")
    print(f"target            {signal.target:.3f}")
    print(f"reward/risk       {signal.rr:.2f}R")
    print(f"risk cash         ${cash:.2f}")
    print(f"calculated volume {volume:.2f}")
    print(f"level             {signal.level_name} @ {signal.level:.3f}")
    print(f"context           {signal.context_quality}")
    print("reasons")
    for reason in signal.reasons:
        print(f"  - {reason}")
    return 0


def command_forward(config: AppConfig, cycles: int = 0) -> int:
    print(
        "FORWARD SCANNER STARTED | "
        f"risk={config.risk_pct:.2f}% | "
        f"order submission={'UNLOCKED' if config.live_submission_allowed else 'LOCKED'}"
    )
    event_path = config.logs_dir / "forward_signals.jsonl"
    seen: set[tuple[str, str, str]] = set()
    completed = 0
    while cycles <= 0 or completed < cycles:
        symbol, account, _, frame = _market_data(
            config, min(config.history_days, 90), refresh=True
        )
        h1, index, profiles, zones, signals = _latest_context(
            frame, symbol, config
        )
        now = datetime.now(timezone.utc).isoformat()
        if signals:
            signal = signals[0]
            key = (signal.time.isoformat(), signal.model, signal.direction)
            if key not in seen:
                seen.add(key)
                payload = {
                    "observed_at": now,
                    "account_balance": account["balance"],
                    "risk_pct": config.risk_pct,
                    "risk_cash": risk_cash(
                        float(account["balance"]), config.risk_pct
                    ),
                    "order_submission": "LOCKED",
                    "signal": signal.to_dict(),
                }
                with event_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, default=str) + "\n")
                print(
                    f"{now} | {signal.grade} {signal.model} "
                    f"{signal.symbol} {signal.direction.upper()} "
                    f"entry={signal.entry:.3f} SL={signal.stop:.3f} "
                    f"TP={signal.target:.3f} RR={signal.rr:.2f}"
                )
        else:
            snapshot = watch_snapshot(h1, index, profiles, zones)
            print(
                f"{now} | no confirmed A setup | "
                f"price={snapshot['price']} trend={snapshot['trend']}"
            )
        completed += 1
        if cycles <= 0 or completed < cycles:
            time.sleep(config.poll_seconds)
    return 0


def _print_stats(stats) -> None:
    print(f"trades                    {stats.trades}")
    print(f"wins / losses / BE        {stats.wins} / {stats.losses} / {stats.breakeven}")
    print(f"win rate                  {stats.win_rate:.2f}%")
    print(f"profit factor             {_format_number(stats.profit_factor)}")
    print(f"expectancy                 {stats.expectancy_r:.3f}R")
    print(f"net result                 {stats.net_r:.2f}R / ${stats.net_profit:.2f}")
    print(f"ending balance            ${stats.ending_balance:.2f}")
    print(f"max realized drawdown      {stats.max_drawdown_pct:.2f}%")
    print(f"max consecutive losses    {stats.max_consecutive_losses}")


def command_backtest(config: AppConfig) -> int:
    symbol, _, _, frame = _market_data(config)
    print(
        f"BACKTESTING {symbol}: {frame['time'].iloc[0]} to "
        f"{frame['time'].iloc[-1]} | risk {config.risk_pct:.2f}%"
    )
    result = run_backtest(frame, symbol, config)
    _print_stats(result.stats)
    trades, summary = save_backtest(
        result, config.reports_dir, f"{symbol}_baseline"
    )
    print(f"trade journal              {trades}")
    print(f"summary                    {summary}")
    return 0


def command_validate(config: AppConfig) -> int:
    symbol, _, _, frame = _market_data(config)
    print(f"VALIDATING {symbol} WITH LOCKED CHRONOLOGICAL SPLITS")
    result = run_validation(frame, symbol, config)
    _print_stats(result.baseline.stats)
    print("\nSPLITS")
    for split in result.splits:
        print(
            f"{split.name:20} trades={split.trades:3d} "
            f"WR={split.win_rate:6.2f}% PF={_format_number(split.profit_factor):>6} "
            f"Exp={split.expectancy_r:+.3f}R"
        )
    print("\nSTRESS")
    for item in result.stress:
        print(
            f"{item['variant']:20} trades={item['trades']:3d} "
            f"PF={_format_number(float(item['profit_factor'])):>6} "
            f"Exp={float(item['expectancy_r']):+.3f}R "
            f"DD={float(item['max_drawdown_pct']):.2f}%"
        )
    print(
        "\nSTATUS: "
        + ("FORWARD APPROVED" if result.approved_for_forward else "NOT APPROVED")
    )
    for reason in result.reasons:
        print(f"  - {reason}")
    path = save_validation(result, config.reports_dir, f"{symbol}_locked")
    print(f"validation report          {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lta")
    parser.add_argument(
        "command",
        choices=("account", "scan", "forward", "backtest", "validate"),
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=0,
        help="Forward scan cycles; 0 runs continuously",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        config = load_config(_project_dir())
        if args.command == "forward":
            return command_forward(config, args.cycles)
        commands = {
            "account": command_account,
            "scan": command_scan,
            "backtest": command_backtest,
            "validate": command_validate,
        }
        return commands[args.command](config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
