from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re

import MetaTrader5 as mt5
import pandas as pd


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


def completed_h4_rates(symbol: str, start: datetime, end: datetime, distance: int) -> pd.DataFrame:
    padded_start = start - timedelta(hours=4 * (distance * 2 + 3))
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--distance", type=int, default=6)
    parser.add_argument("--max-legs", type=int, default=2)
    parser.add_argument("--lot", type=float, default=0.10)
    parser.add_argument("--balance", type=float, default=1_000.0)
    parser.add_argument("--output", type=Path, default=Path("reports"))
    args = parser.parse_args()

    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        symbol = discover_symbol(args.symbol)
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"No symbol info for {symbol}")
        end = datetime.now(UTC)
        start = end - timedelta(days=args.days)
        frame = completed_h4_rates(symbol, start, end, args.distance)
        trades, equity, summary = run_backtest(
            frame,
            symbol,
            start,
            end,
            args.distance,
            args.lot,
            args.balance,
            float(info.point),
            args.max_legs,
        )
    finally:
        mt5.shutdown()

    args.output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(asdict(trade) for trade in trades).to_csv(
        args.output / "trades.csv", index=False
    )
    equity.to_csv(args.output / "equity.csv", index=False)
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=True), encoding="utf-8"
    )
    report = markdown_summary(summary)
    (args.output / "REPORT.md").write_text(report, encoding="utf-8")
    print(report)
