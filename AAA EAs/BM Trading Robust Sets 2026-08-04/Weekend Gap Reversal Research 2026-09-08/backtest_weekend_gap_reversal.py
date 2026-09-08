from __future__ import annotations

import json
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5


ROOT = Path(__file__).resolve().parent
SYMBOLS = ("EURUSD", "GBPUSD", "NZDUSD", "GBPJPY")
ROLLING_WEEKS = 260
TAIL_QUANTILE = 0.05
ROUND_TRIP_COST = 0.0008
REQUESTED_BARS = 700
COMMON_TEST_START = datetime(2019, 1, 13, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Trade:
    week: str
    symbol: str
    side: str
    gap_pct: float
    gross_return_pct: float
    net_return_pct: float


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def resolve_symbol(canonical: str) -> str:
    candidates = [symbol.name for symbol in (mt5.symbols_get() or ())]
    exact = next((name for name in candidates if name.upper() == canonical), None)
    if exact:
        return exact
    prefixed = [name for name in candidates if name.upper().startswith(canonical)]
    if not prefixed:
        raise RuntimeError(f"No broker symbol found for {canonical}")
    return min(prefixed, key=len)


def closed_weekly_bars(symbol: str) -> list[dict[str, float | int]]:
    raw = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_W1, 0, REQUESTED_BARS)
    if raw is None or not len(raw):
        raise RuntimeError(f"No W1 history for {symbol}: {mt5.last_error()}")
    now = datetime.now(timezone.utc)
    rows: list[dict[str, float | int]] = []
    for row in raw:
        opened = datetime.fromtimestamp(int(row["time"]), timezone.utc)
        # MT5 W1 timestamps are broker-week opens. Do not score the still-open week.
        if opened + timedelta(days=5) > now:
            continue
        rows.append({
            "time": int(row["time"]),
            "open": float(row["open"]),
            "close": float(row["close"]),
        })
    return rows


def maximum_streaks(returns: list[float]) -> tuple[int, int]:
    current_win = current_loss = maximum_win = maximum_loss = 0
    for value in returns:
        if value > 0:
            current_win += 1
            current_loss = 0
            maximum_win = max(maximum_win, current_win)
        elif value < 0:
            current_loss += 1
            current_win = 0
            maximum_loss = max(maximum_loss, current_loss)
        else:
            current_win = current_loss = 0
    return maximum_win, maximum_loss


def backtest(canonical: str, broker_symbol: str, rows: list[dict[str, float | int]]) -> dict:
    gaps = [
        {
            "bar_index": index,
            "gap": math.log(float(rows[index]["open"]) / float(rows[index - 1]["close"])),
        }
        for index in range(1, len(rows))
    ]
    weekly_returns = [0.0] * len(rows)
    trades: list[Trade] = []
    for gap_index in range(ROLLING_WEEKS, len(gaps)):
        history = [float(item["gap"]) for item in gaps[gap_index - ROLLING_WEEKS:gap_index]]
        lower = percentile(history, TAIL_QUANTILE)
        upper = percentile(history, 1.0 - TAIL_QUANTILE)
        current = gaps[gap_index]
        gap = float(current["gap"])
        if lower < gap < upper:
            continue
        bar_index = int(current["bar_index"])
        bar = rows[bar_index]
        bar_time = datetime.fromtimestamp(int(bar["time"]), timezone.utc)
        if bar_time < COMMON_TEST_START:
            continue
        side = -1.0 if gap > 0 else 1.0
        gross_return = side * (float(bar["close"]) / float(bar["open"]) - 1.0)
        net_return = gross_return - ROUND_TRIP_COST
        weekly_returns[bar_index] = net_return
        trades.append(Trade(
            week=datetime.fromtimestamp(int(bar["time"]), timezone.utc).date().isoformat(),
            symbol=canonical,
            side="Long" if side > 0 else "Short",
            gap_pct=round(gap * 100.0, 6),
            gross_return_pct=round(gross_return * 100.0, 6),
            net_return_pct=round(net_return * 100.0, 6),
        ))

    outcomes = [trade.net_return_pct / 100.0 for trade in trades]
    wins = [value for value in outcomes if value > 0]
    losses = [value for value in outcomes if value < 0]
    equity = peak = 1.0
    maximum_drawdown = 0.0
    for value in weekly_returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, 1.0 - equity / peak)
    test_start_index = next(
        index for index, row in enumerate(rows)
        if index >= ROLLING_WEEKS + 1
        and datetime.fromtimestamp(int(row["time"]), timezone.utc) >= COMMON_TEST_START
    )
    test_start = datetime.fromtimestamp(int(rows[test_start_index]["time"]), timezone.utc)
    test_end = datetime.fromtimestamp(int(rows[-1]["time"]), timezone.utc) + timedelta(days=5)
    years = (test_end - test_start).days / 365.2425
    test_weekly_returns = weekly_returns[test_start_index:]
    mean_week = statistics.mean(test_weekly_returns)
    deviation_week = statistics.stdev(test_weekly_returns)
    max_wins, max_losses = maximum_streaks(outcomes)
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    return {
        "symbol": canonical,
        "broker_symbol": broker_symbol,
        "history_from": datetime.fromtimestamp(int(rows[0]["time"]), timezone.utc).date().isoformat(),
        "test_from": test_start.date().isoformat(),
        "test_to": test_end.date().isoformat(),
        "round_trip_cost_pct": ROUND_TRIP_COST * 100.0,
        "trades": len(outcomes),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(outcomes) * 100.0, 2),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "total_return_pct": round((equity - 1.0) * 100.0, 2),
        "cagr_pct": round((equity ** (1.0 / years) - 1.0) * 100.0, 2),
        "max_drawdown_pct": round(maximum_drawdown * 100.0, 2),
        "sharpe_ratio": round(mean_week / deviation_week * math.sqrt(52.0), 2),
        "average_trade_pct": round(statistics.mean(outcomes) * 100.0, 2),
        "average_win_pct": round(statistics.mean(wins) * 100.0, 2),
        "average_loss_pct": round(statistics.mean(losses) * 100.0, 2),
        "best_trade_pct": round(max(outcomes) * 100.0, 2),
        "worst_trade_pct": round(min(outcomes) * 100.0, 2),
        "max_win_streak": max_wins,
        "max_loss_streak": max_losses,
        "long_trades": sum(trade.side == "Long" for trade in trades),
        "short_trades": sum(trade.side == "Short" for trade in trades),
        "trades_detail": [asdict(trade) for trade in trades],
    }


def markdown_report(payload: dict) -> str:
    lines = [
        "# Weekend Gap Reversal — Raw Paper Backtest",
        "",
        "Research only. Not added to the recommended BAT or website catalogue.",
        "",
        "## Fixed rules",
        "",
        "- W1 broker bars; current incomplete week excluded.",
        "- Five-year (260-week) rolling gap distribution with no look-ahead.",
        "- Trade against gaps in the bottom/top 5% and exit at the weekly close.",
        "- 0.08% round-trip cost deducted from every trade.",
        "- Raw paper rule has no stop-loss. Returns below use 1x notional exposure and are not a 1%-risk EA simulation.",
        "",
        "## Results",
        "",
        "| Pair | Test period | Trades | Win rate | PF | Return | CAGR | Max DD | Sharpe | Avg trade | Max W/L streak |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["results"]:
        lines.append(
            f"| {row['symbol']} | {row['test_from']} to {row['test_to']} | {row['trades']} | "
            f"{row['win_rate_pct']:.2f}% | {row['profit_factor']:.2f} | {row['total_return_pct']:+.2f}% | "
            f"{row['cagr_pct']:+.2f}% | {row['max_drawdown_pct']:.2f}% | {row['sharpe_ratio']:.2f} | "
            f"{row['average_trade_pct']:+.2f}% | {row['max_win_streak']}/{row['max_loss_streak']} |"
        )
    lines += [
        "",
        "## Decision",
        "",
        "The raw rule is not deployment-ready because it has no stop-defined 1% risk model and the sample is small. "
        "Pairs with PF above 1 may proceed to a separate MT5 EA engineering and walk-forward stage only after review; failing pairs stay excluded.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        results = []
        for canonical in SYMBOLS:
            broker_symbol = resolve_symbol(canonical)
            mt5.symbol_select(broker_symbol, True)
            results.append(backtest(canonical, broker_symbol, closed_weekly_bars(broker_symbol)))
        payload = {
            "strategy": "Weekend Gap Overreaction Reversal — raw paper rules",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "settings": {
                "rolling_weeks": ROLLING_WEEKS,
                "tail_quantile": TAIL_QUANTILE,
                "round_trip_cost_pct": ROUND_TRIP_COST * 100.0,
                "timeframe": "W1",
                "entry": "broker weekly open, opposite an extreme weekend gap",
                "exit": "broker weekly close",
            },
            "results": results,
        }
        (ROOT / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (ROOT / "FULL REPORT.md").write_text(markdown_report(payload), encoding="utf-8")
        print(markdown_report(payload))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
