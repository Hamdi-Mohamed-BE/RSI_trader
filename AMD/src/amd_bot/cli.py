from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path

import pandas as pd

from .config import load_config
from .engine import backtest_symbol, metrics
from .live import run_live
from .mt5_data import connection, discover_symbols, load_m1, symbol_metadata


UTC = timezone.utc


def _fmt(value: object, digits: int = 2) -> str:
    if isinstance(value, float) and math.isinf(value):
        return "INF"
    if isinstance(value, (float, int)):
        return f"{float(value):.{digits}f}"
    return str(value)


def write_report(
    path: Path,
    rows: list[dict[str, object]],
    start: datetime,
    end: datetime,
    account: object,
    config: object,
) -> None:
    mode = str(getattr(config, "ny_entry_mode", "unknown"))
    risk_pct = float(getattr(config, "risk_pct", 0.0))
    max_risk = risk_pct * 2.0 if mode == "dual" else risk_pct
    mode_explanation = {
        "limit_only": (
            "Rest one opposite-London liquidity limit from the New York open "
            "until the signal cutoff."
        ),
        "stop_only": (
            "After the configured New York observation window, place only an "
            "opposite-London breakout stop beyond that range."
        ),
        "single_fallback": (
            "Rest the liquidity limit during the observation window; if it "
            "does not fill, cancel it and replace it with the breakout stop."
        ),
        "dual": (
            "Keep the liquidity limit active and add the breakout stop after "
            "the observation window; both legs can fill."
        ),
    }.get(mode, "Unknown entry mode.")
    lines = [
        "# AMD Session Strategy Backtest",
        "",
        f"- Period: **{start.isoformat()} to {end.isoformat()}**",
        f"- Data source: **MT5 / {getattr(account, 'server', 'unknown')}**",
        "- Starting balance per symbol: **$1,000**",
        (
            f"- Risk: **{_fmt(risk_pct)}% of current balance per leg; "
            f"maximum planned exposure {_fmt(max_risk)}%**"
        ),
        "- Asia range: **00:00-08:00 UTC**",
        "- London reference: **08:00-09:00 UTC H1 close; no London trade is placed**",
        "- A close beyond the Asia range establishes direction; New York trades only the opposite side",
        f"- Entry mode: **{mode}** — {mode_explanation}",
        (
            f"- New York observation window: **"
            f"{getattr(config, 'ny_fallback_minutes', 0)} minutes from 13:30 UTC**"
        ),
        (
            f"- Breakout target: **"
            f"{_fmt(getattr(config, 'ny_fallback_rr', 0.0))}R**; stop buffer: **"
            f"{_fmt(getattr(config, 'ny_stop_buffer_fraction', 0.0) * 100)}% "
            "of the Asia range**"
        ),
        (
            f"- Management: **at +"
            f"{_fmt(getattr(config, 'lock_trigger_r', 0.0))}R, stop advances "
            f"to +{_fmt(getattr(config, 'lock_profit_r', 0.0))}R**"
        ),
        "- Pending orders expire at 16:00 UTC.",
        "- Any open trade is closed at **21:00 UTC**",
        "- Conservative rule: when SL and TP are both touched in one M1 bar, SL is assumed first.",
        "",
        "- Max DD is realized balance drawdown; intrabar floating drawdown is not included.",
        "",
        "| Symbol | Trades | NY limit | NY stop | Both-filled days | Win rate | PF | Net R | Max exposure | Realized max DD | Ending balance |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['canonical_symbol']} ({row['symbol']}) "
            f"| {row['trades']} | {row['new_york_limit_trades']} "
            f"| {row['new_york_stop_trades']} "
            f"| {row['both_filled_days']} "
            f"| {_fmt(row['win_rate_pct'])}% | {_fmt(row['profit_factor'])} "
            f"| {_fmt(row['net_r'])}R "
            f"| {_fmt(row['max_planned_exposure_pct'])}% "
            f"| {_fmt(row['max_drawdown_pct'])}% "
            f"| ${_fmt(row['ending_balance'])} |"
        )
    lines.extend(
        [
            "",
            "## Entry-leg breakdown",
            "",
            "| Symbol | Leg | Trades | Win rate | PF (R-based) | Net R |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        lines.extend(
            [
                (
                    f"| {row['canonical_symbol']} | NY liquidity limit "
                    f"| {row['new_york_limit_trades']} "
                    f"| {_fmt(row['new_york_limit_win_rate_pct'])}% "
                    f"| {_fmt(row['new_york_limit_profit_factor_r'])} "
                    f"| {_fmt(row['new_york_limit_net_r'])}R |"
                ),
                (
                    f"| {row['canonical_symbol']} | NY breakout stop "
                    f"| {row['new_york_stop_trades']} "
                    f"| {_fmt(row['new_york_stop_win_rate_pct'])}% "
                    f"| {_fmt(row['new_york_stop_profit_factor_r'])} "
                    f"| {_fmt(row['new_york_stop_net_r'])}R |"
                ),
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def command_backtest(args: argparse.Namespace) -> None:
    config = load_config(args.env)
    end = (
        datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=UTC)
        if args.end
        else datetime.now(UTC).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    )
    start = (
        datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=UTC)
        if args.start
        else end - timedelta(days=args.days)
    )
    instruments = (
        tuple(item.strip().upper() for item in args.symbols.split(","))
        if args.symbols
        else config.symbols
    )
    reports = config.root / "reports"
    trade_dir = reports / "trades"
    reports.mkdir(parents=True, exist_ok=True)
    trade_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, object]] = []
    with connection() as account:
        print(
            f"MT5 account {account.login} | {account.server} | "
            f"balance ${account.balance:,.2f}"
        )
        symbol_map = discover_symbols(instruments)
        for canonical, symbol in symbol_map.items():
            print(f"Testing {canonical} -> {symbol}...")
            metadata = symbol_metadata(symbol)
            frame = load_m1(
                symbol,
                start,
                end,
                config.root / "data",
                args.refresh,
            )
            trades = backtest_symbol(
                frame,
                symbol,
                float(metadata["point"]),
                config,
                start,
                end,
            )
            row = metrics(
                symbol,
                trades,
                config.starting_balance,
                config.risk_pct,
            )
            row["canonical_symbol"] = canonical
            row["bars"] = len(frame)
            summaries.append(row)
            pd.DataFrame([trade.to_dict() for trade in trades]).to_csv(
                trade_dir / f"{canonical}.csv",
                index=False,
            )
            print(
                f"  {len(trades)} trades | WR {_fmt(row['win_rate_pct'])}% | "
                f"PF {_fmt(row['profit_factor'])} | "
                f"DD {_fmt(row['max_drawdown_pct'])}% | "
                f"end ${_fmt(row['ending_balance'])}"
            )
    pd.DataFrame(summaries).to_csv(reports / "summary.csv", index=False)
    (reports / "summary.json").write_text(
        json.dumps(summaries, indent=2, default=str),
        encoding="utf-8",
    )
    write_report(
        reports / "REPORT.md",
        summaries,
        start,
        end,
        account,
        config,
    )
    print(f"\nReport: {reports / 'REPORT.md'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AMD MT5 session bot")
    sub = parser.add_subparsers(dest="command", required=True)
    backtest = sub.add_parser("backtest", help="Run historical M1 simulation")
    backtest.add_argument("--env")
    backtest.add_argument("--days", type=int, default=60)
    backtest.add_argument("--start")
    backtest.add_argument("--end")
    backtest.add_argument("--symbols")
    backtest.add_argument("--refresh", action="store_true")
    backtest.set_defaults(func=command_backtest)
    live = sub.add_parser("live", help="Run the protected live scanner")
    live.add_argument("--env")
    live.add_argument("--once", action="store_true")
    live.set_defaults(func=lambda args: run_live(load_config(args.env), args.once))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)
