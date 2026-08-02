from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re

import MetaTrader5 as mt5
import pandas as pd
from dotenv import load_dotenv


UTC = timezone.utc


@dataclass(slots=True)
class Trade:
    side: str
    pivot_time: str
    confirmation_time: str
    entry_time: str
    entry: float
    exit_time: str
    exit: float
    exit_reason: str
    bars_held: int
    pnl_usd: float
    return_pct: float


def canonical(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def discover_symbol(requested: str) -> str:
    symbols = mt5.symbols_get()
    if not symbols:
        raise RuntimeError(f"MT5 symbol catalogue unavailable: {mt5.last_error()}")
    wanted = canonical(requested)
    matches = [item for item in symbols if canonical(item.name) == wanted]
    if not matches:
        matches = [item for item in symbols if canonical(item.name).startswith(wanted)]
    if not matches:
        raise RuntimeError(f"No broker symbol found for {requested}")
    matches.sort(
        key=lambda item: (
            not bool(item.visible),
            int(item.trade_mode) == int(mt5.SYMBOL_TRADE_MODE_DISABLED),
            len(item.name),
        )
    )
    symbol = matches[0].name
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Could not select {symbol}: {mt5.last_error()}")
    return symbol


def completed_h4_rates(
    symbol: str,
    start: datetime,
    end: datetime,
    distance: int,
    warmup_bars: int = 0,
) -> pd.DataFrame:
    padding = max(distance * 2 + 3, warmup_bars)
    padded_start = start - timedelta(hours=4 * padding)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H4, padded_start, end)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No H4 history for {symbol}: {mt5.last_error()}")
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    current_h4_open = end.replace(
        hour=(end.hour // 4) * 4, minute=0, second=0, microsecond=0
    )
    return frame.loc[frame["time"] < current_h4_open].reset_index(drop=True)


def pivot_signals(frame: pd.DataFrame, distance: int) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    for pivot_idx in range(distance, len(frame) - distance):
        left = pivot_idx - distance
        right = pivot_idx + distance
        low_window = frame.loc[left:right, "low"]
        high_window = frame.loc[left:right, "high"]
        pivot_low = float(frame.at[pivot_idx, "low"])
        pivot_high = float(frame.at[pivot_idx, "high"])
        confirmed_idx = pivot_idx + distance
        execute_idx = confirmed_idx + 1
        if execute_idx >= len(frame):
            continue
        if pivot_low == float(low_window.min()) and int((low_window == pivot_low).sum()) == 1:
            signals.append(
                {
                    "side": "buy",
                    "pivot_idx": pivot_idx,
                    "confirmed_idx": confirmed_idx,
                    "execute_idx": execute_idx,
                }
            )
        if pivot_high == float(high_window.max()) and int((high_window == pivot_high).sum()) == 1:
            signals.append(
                {
                    "side": "sell",
                    "pivot_idx": pivot_idx,
                    "confirmed_idx": confirmed_idx,
                    "execute_idx": execute_idx,
                }
            )
    return sorted(signals, key=lambda item: (int(item["execute_idx"]), str(item["side"])))


def spread_price(frame: pd.DataFrame, index: int, point: float) -> float:
    return max(float(frame.at[index, "spread"]) * point, 0.0)


def order_profit(symbol: str, side: str, lot: float, entry: float, exit_price: float) -> float:
    order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    value = mt5.order_calc_profit(order_type, symbol, lot, entry, exit_price)
    if value is None:
        raise RuntimeError(f"Could not calculate profit for {symbol}: {mt5.last_error()}")
    return float(value)


def executable_price(
    frame: pd.DataFrame,
    index: int,
    side: str,
    action: str,
    point: float,
    field: str = "open",
) -> float:
    mid = float(frame.at[index, field])
    spread = spread_price(frame, index, point)
    if action == "entry":
        return mid + spread if side == "buy" else mid
    return mid if side == "buy" else mid + spread


def run_backtest(
    frame: pd.DataFrame,
    symbol: str,
    start: datetime,
    end: datetime,
    distance: int,
    lot: float,
    initial_balance: float,
    point: float,
    max_same_direction_legs: int = 2,
) -> tuple[list[Trade], pd.DataFrame, dict[str, object]]:
    signals = pivot_signals(frame, distance)
    active: list[dict[str, object]] = []
    trades: list[Trade] = []
    balance = initial_balance
    realized_curve: list[tuple[pd.Timestamp, float]] = []

    def close_leg(
        leg: dict[str, object], idx: int, exit_price: float, reason: str
    ) -> None:
        nonlocal balance
        side = str(leg["side"])
        pnl = order_profit(symbol, side, lot, float(leg["entry"]), exit_price)
        balance += pnl
        entry_idx = int(leg["entry_idx"])
        trades.append(
            Trade(
                side=side,
                pivot_time=frame.at[int(leg["pivot_idx"]), "time"].isoformat(),
                confirmation_time=frame.at[
                    int(leg["confirmed_idx"]), "time"
                ].isoformat(),
                entry_time=frame.at[entry_idx, "time"].isoformat(),
                entry=float(leg["entry"]),
                exit_time=frame.at[idx, "time"].isoformat(),
                exit=exit_price,
                exit_reason=reason,
                bars_held=idx - entry_idx,
                pnl_usd=pnl,
                return_pct=pnl / initial_balance * 100.0,
            )
        )
        realized_curve.append((frame.at[idx, "time"], balance))
        active.remove(leg)

    for signal in signals:
        idx = int(signal["execute_idx"])
        timestamp = frame.at[idx, "time"].to_pydatetime()
        if timestamp < start or timestamp >= end:
            continue
        side = str(signal["side"])
        if active and str(active[0]["side"]) != side:
            exit_price = executable_price(frame, idx, str(active[0]["side"]), "exit", point)
            for leg in list(active):
                close_leg(leg, idx, exit_price, "opposite_signal")
        if len(active) >= max_same_direction_legs:
            continue
        active.append(
            {
                "side": side,
                "pivot_idx": int(signal["pivot_idx"]),
                "confirmed_idx": int(signal["confirmed_idx"]),
                "entry_idx": idx,
                "entry": executable_price(frame, idx, side, "entry", point),
            }
        )

    in_period = frame.loc[(frame["time"] >= start) & (frame["time"] < end)]
    if active and not in_period.empty:
        idx = int(in_period.index[-1])
        exit_price = executable_price(
            frame, idx, str(active[0]["side"]), "exit", point, field="close"
        )
        for leg in list(active):
            close_leg(leg, idx, exit_price, "end_of_test")

    equity_rows: list[dict[str, object]] = []
    for idx in in_period.index:
        timestamp = frame.at[idx, "time"]
        closed = [
            trade for trade in trades if pd.Timestamp(trade.exit_time) <= timestamp
        ]
        running_balance = initial_balance + sum(trade.pnl_usd for trade in closed)
        open_trades = [
            trade
            for trade in trades
            if pd.Timestamp(trade.entry_time) <= timestamp
            and pd.Timestamp(trade.exit_time) > timestamp
        ]
        floating = 0.0
        for open_trade in open_trades:
            mark = executable_price(
                frame, idx, open_trade.side, "exit", point, field="close"
            )
            floating += order_profit(
                symbol, open_trade.side, lot, open_trade.entry, mark
            )
        equity_rows.append(
            {
                "time": timestamp.isoformat(),
                "balance": running_balance,
                "floating_pnl": floating,
                "equity": running_balance + floating,
            }
        )
    equity = pd.DataFrame(equity_rows)
    if not equity.empty:
        equity["peak"] = equity["equity"].cummax()
        equity["drawdown_usd"] = equity["peak"] - equity["equity"]
        equity["drawdown_pct"] = equity["drawdown_usd"] / equity["peak"] * 100.0
        max_equity_dd = float(equity["drawdown_pct"].max())
    else:
        max_equity_dd = 0.0

    pnls = [trade.pnl_usd for trade in trades]
    wins = [value for value in pnls if value > 0]
    losses = [value for value in pnls if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss else math.inf
    realized_values = [initial_balance] + [value for _, value in realized_curve]
    peak = realized_values[0]
    realized_dd = 0.0
    for value in realized_values:
        peak = max(peak, value)
        if peak > 0:
            realized_dd = max(realized_dd, (peak - value) / peak * 100.0)
    summary = {
        "symbol": symbol,
        "timeframe": "H4",
        "start_utc": start.isoformat(),
        "end_utc": end.isoformat(),
        "pivot_distance": distance,
        "max_same_direction_legs": max_same_direction_legs,
        "execution_rule": "next H4 open after 6-right-bar confirmation",
        "lot": lot,
        "initial_balance": initial_balance,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "gross_profit_usd": gross_profit,
        "gross_loss_usd": gross_loss,
        "profit_factor": profit_factor,
        "net_profit_usd": sum(pnls),
        "ending_balance": initial_balance + sum(pnls),
        "return_pct": sum(pnls) / initial_balance * 100.0,
        "max_realized_drawdown_pct": realized_dd,
        "max_equity_drawdown_pct": max_equity_dd,
    }
    return trades, equity, summary


def markdown_summary(summary: dict[str, object]) -> str:
    pf = summary["profit_factor"]
    pf_text = "∞" if isinstance(pf, float) and math.isinf(pf) else f"{pf:.2f}"
    return "\n".join(
        [
            "# EMA3 Pivot Reversal Backtest",
            "",
            f"- Broker symbol: **{summary['symbol']}**",
            f"- Period: **{summary['start_utc']} to {summary['end_utc']}**",
            f"- Timeframe: **{summary['timeframe']}**",
            f"- Pivot distance: **{summary['pivot_distance']} left / {summary['pivot_distance']} right**",
            f"- Same-direction legs: **up to {summary['max_same_direction_legs']}**",
            f"- Execution: **{summary['execution_rule']}**",
            f"- Test size: **{summary['lot']:.2f} lot**, starting balance **${summary['initial_balance']:,.2f}**",
            "",
            "| Metric | Result |",
            "|---|---:|",
            f"| Trades | {summary['trades']} |",
            f"| Wins / losses | {summary['wins']} / {summary['losses']} |",
            f"| Win rate | {summary['win_rate_pct']:.2f}% |",
            f"| Profit factor | {pf_text} |",
            f"| Net profit | ${summary['net_profit_usd']:,.2f} |",
            f"| Ending balance | ${summary['ending_balance']:,.2f} |",
            f"| Return | {summary['return_pct']:.2f}% |",
            f"| Max realized DD | {summary['max_realized_drawdown_pct']:.2f}% |",
            f"| Max equity DD | {summary['max_equity_drawdown_pct']:.2f}% |",
            "",
            "EMA and Bollinger values are plotted by the original indicator but do not",
            "participate in its Buy/Sell label logic. The backtest therefore follows",
            "the confirmed pivot labels exactly and does not add unrequested filters.",
            "",
        ]
    )


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument(
        "--days", type=int, default=int(os.getenv("HISTORY_DAYS", "365"))
    )
    parser.add_argument(
        "--distance", type=int, default=int(os.getenv("PIVOT_DISTANCE", "5"))
    )
    parser.add_argument(
        "--max-legs",
        type=int,
        default=int(os.getenv("MAX_SAME_DIRECTION_LEGS", "1")),
    )
    parser.add_argument(
        "--risk-pct",
        type=float,
        default=float(os.getenv("BACKTEST_RISK_PCT", "1.0")),
    )
    parser.add_argument(
        "--balance", type=float, default=float(os.getenv("STARTING_BALANCE", "1000"))
    )
    parser.add_argument(
        "--exit-mode",
        choices=("fixed", "trail"),
        default=os.getenv("EXIT_MODE", "trail").strip().lower(),
    )
    parser.add_argument(
        "--trailing-enabled",
        action=argparse.BooleanOptionalAction,
        default=os.getenv("TRAILING_ENABLED", "true").strip().lower()
        in {"1", "true", "yes", "on"},
        help="explicitly enable/disable trailing; disabled converts trail mode to fixed",
    )
    parser.add_argument(
        "--target-r", type=float, default=float(os.getenv("TARGET_R", "4.0"))
    )
    parser.add_argument(
        "--max-target-r",
        type=float,
        default=float(os.getenv("MAX_TARGET_R", "1.7")),
        help="hard ceiling for fixed targets and the terminal cap for trailing exits",
    )
    parser.add_argument(
        "--trail-start-r",
        type=float,
        default=float(os.getenv("TRAIL_START_R", "1.0")),
    )
    parser.add_argument(
        "--trail-distance-r",
        type=float,
        default=float(os.getenv("TRAIL_DISTANCE_R", "1.0")),
    )
    parser.add_argument(
        "--risk-progression",
        action=argparse.BooleanOptionalAction,
        default=os.getenv("RISK_PROGRESSION_ENABLED", "false").strip().lower()
        in {"1", "true", "yes", "on"},
    )
    parser.add_argument(
        "--risk-progression-multiplier",
        type=float,
        default=float(os.getenv("RISK_PROGRESSION_MULTIPLIER", "1.6")),
    )
    parser.add_argument(
        "--max-risk-pct",
        type=float,
        default=float(os.getenv("RISK_PROGRESSION_MAX_PCT", "3.2")),
        help="live-style safety cap; ignored with --uncapped-progression",
    )
    parser.add_argument("--uncapped-progression", action="store_true")
    parser.add_argument(
        "--signal-filter",
        choices=("none", "ema200_slope"),
        default=os.getenv("SIGNAL_FILTER", "ema200_slope").strip().lower(),
    )
    parser.add_argument(
        "--ema-slope-bars",
        type=int,
        default=int(os.getenv("EMA_SLOPE_BARS", "6")),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("reports") / "risk_sized_default"
    )
    args = parser.parse_args()

    if not 0 < args.risk_pct < 100:
        raise SystemExit("--risk-pct must be between 0 and 100")
    if args.balance <= 0:
        raise SystemExit("--balance must be positive")
    if args.max_target_r <= 0 or args.max_target_r > 1.7:
        raise SystemExit("--max-target-r must be positive and no greater than 1.7")
    if args.risk_progression_multiplier < 1:
        raise SystemExit("--risk-progression-multiplier must be at least 1")
    if args.max_risk_pct <= 0:
        raise SystemExit("--max-risk-pct must be positive")

    # Import locally to avoid a module-level cycle: optimize imports the shared
    # rate and pivot helpers from this module.
    from .optimize import (
        ExitConfig,
        compounded_journal,
        metrics,
        simulate,
    )

    capped_target_r = min(args.target_r, args.max_target_r)
    effective_exit_mode = (
        "fixed" if args.exit_mode == "trail" and not args.trailing_enabled else args.exit_mode
    )
    exit_config = (
        ExitConfig(mode="fixed", target_r=capped_target_r)
        if effective_exit_mode == "fixed"
        else ExitConfig(
            mode="trail",
            trail_start_r=args.trail_start_r,
            trail_distance_r=args.trail_distance_r,
            target_cap_r=args.max_target_r,
        )
    )

    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        symbol = discover_symbol(args.symbol)
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"No symbol info for {symbol}")
        end = datetime.now(UTC)
        start = end - timedelta(days=args.days)
        warmup_bars = 250 + args.ema_slope_bars if args.signal_filter != "none" else 0
        frame = completed_h4_rates(
            symbol, start, end, args.distance, warmup_bars=warmup_bars
        )
        trades = simulate(
            frame,
            args.symbol,
            float(info.point),
            args.distance,
            start,
            end,
            exit_config,
            max_same_direction_legs=args.max_legs,
            signal_filter=args.signal_filter,
            ema_slope_bars=args.ema_slope_bars,
        )
    finally:
        mt5.shutdown()

    progression_cap = None if args.uncapped_progression else args.max_risk_pct
    stats = metrics(
        trades,
        risk_pct=args.risk_pct,
        starting_balance=args.balance,
        progression_enabled=args.risk_progression,
        progression_multiplier=args.risk_progression_multiplier,
        max_risk_pct=progression_cap,
    )
    journal = compounded_journal(
        trades,
        risk_pct=args.risk_pct,
        starting_balance=args.balance,
        progression_enabled=args.risk_progression,
        progression_multiplier=args.risk_progression_multiplier,
        max_risk_pct=progression_cap,
    )
    equity = pd.DataFrame(
        [
            {"time": start.isoformat(), "balance": args.balance, "drawdown_pct": 0.0},
            *(
                journal[["exit_time", "balance", "drawdown_pct"]]
                .rename(columns={"exit_time": "time"})
                .to_dict("records")
                if not journal.empty
                else []
            ),
        ]
    )
    summary = {
        "strategy": "EMA3 confirmed H4 pivot reversal",
        "requested_symbol": args.symbol,
        "broker_symbol": symbol,
        "timeframe": "H4",
        "period_start_utc": start.isoformat(),
        "period_end_utc": end.isoformat(),
        "history_days": args.days,
        "pivot_distance": args.distance,
        "max_same_direction_legs": args.max_legs,
        "exit_config": exit_config.name,
        "signal_filter": args.signal_filter,
        "ema_slope_bars": args.ema_slope_bars,
        "execution": "next H4 open after right-side pivot confirmation",
        "stop": "confirmed pivot extreme; historical spread included",
        "same_bar_policy": "stop before target (conservative)",
        "starting_balance": args.balance,
        "base_risk_pct": args.risk_pct,
        "risk_progression_enabled": args.risk_progression,
        "risk_progression_multiplier": args.risk_progression_multiplier,
        "risk_progression_max_pct": progression_cap,
        "max_target_r": args.max_target_r,
        "trailing_enabled": args.trailing_enabled,
        **stats,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    journal.to_csv(args.output / "trades.csv", index=False)
    equity.to_csv(args.output / "equity.csv", index=False)
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=True), encoding="utf-8"
    )
    pf = float(summary["profit_factor"])
    pf_text = "inf" if math.isinf(pf) else f"{pf:.2f}"
    report = "\n".join(
        [
            "# EMA3 Risk-Sized Backtest",
            "",
            f"- Period: **{summary['period_start_utc']} to {summary['period_end_utc']}**",
            f"- Broker symbol: **{summary['broker_symbol']}**",
            f"- Setup: **pivot {args.distance} left / {args.distance} right; {exit_config.name}**",
            f"- Filter: **{args.signal_filter}, slope lookback {args.ema_slope_bars} H4 bars**",
            f"- Base risk: **{args.risk_pct:.2f}% of current balance per trade**",
            f"- Loss progression: **{'enabled' if args.risk_progression else 'disabled'}**, multiplier **{args.risk_progression_multiplier:g}x**, cap **{'none' if progression_cap is None else f'{progression_cap:g}%'}**",
            f"- Maximum target: **{args.max_target_r:g}R**",
            f"- Structural stop: **confirmed pivot extreme**",
            "",
            "| Metric | Result |",
            "|---|---:|",
            f"| Trades | {summary['trades']} |",
            f"| Wins / losses | {summary['wins']} / {summary['losses']} |",
            f"| Win rate | {summary['win_rate_pct']:.2f}% |",
            f"| Profit factor | {pf_text} |",
            f"| Net result | {summary['net_r']:+.2f}R |",
            f"| Starting balance | ${args.balance:,.2f} |",
            f"| Ending balance | ${summary['ending_balance']:,.2f} |",
            f"| Return | {(float(summary['ending_balance']) / args.balance - 1) * 100:.2f}% |",
            f"| Max realized drawdown | {summary['max_drawdown_pct']:.2f}% |",
            f"| Account ruined | {'yes' if summary['ruined'] else 'no'} |",
            "",
            "This replaces the legacy fixed-0.10-lot, no-stop calculation. Equity is",
            "never allowed to become negative and later recover, and every trade has",
            "the same percentage risk through its structural stop.",
            "",
        ]
    )
    (args.output / "REPORT.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
