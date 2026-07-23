from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5


SYMBOLS = ["XAUUSD..", "BTCUSD", "US30", "EURUSD.."]
LOTS = [0.01, 0.02, 0.05, 0.10]
TP_MONEY = [25, 50, 100, 150, 200]
SL_MONEY = [100, 250, 500, 1000]
MAX_DAILY_WINS = [0, 1, 2, 3]
START_BALANCE = 300.0
OUT_DIR = Path(__file__).resolve().parent
RATE_CACHE = {}
SYMBOL_INFO_CACHE = {}


def symbol_specs(symbol: str) -> dict | None:
    if symbol in SYMBOL_INFO_CACHE:
        return SYMBOL_INFO_CACHE[symbol]

    info = mt5.symbol_info(symbol)
    if info is None:
        SYMBOL_INFO_CACHE[symbol] = None
        return None

    specs = {
        "tick_size": float(info.trade_tick_size or info.point or 0),
        "tick_value": float(info.trade_tick_value or 0),
        "point": float(info.point or 0),
    }
    SYMBOL_INFO_CACHE[symbol] = specs
    return specs


@dataclass
class Config:
    symbol: str
    lot: float
    tp_money: float
    sl_money: float
    max_daily_wins: int


@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str
    entry: float
    exit: float
    profit: float
    reason: str


def money_to_price_distance(symbol: str, lot: float, money: float) -> float:
    specs = symbol_specs(symbol)
    if specs is None or lot <= 0 or money <= 0:
        return 0.0
    tick_size = specs["tick_size"]
    tick_value = specs["tick_value"]
    if tick_size <= 0 or tick_value <= 0:
        return 0.0
    return (money / (tick_value * lot)) * tick_size


def price_profit(symbol: str, side: str, lot: float, entry: float, exit_price: float) -> float:
    specs = symbol_specs(symbol)
    if specs is None:
        return 0.0
    tick_size = specs["tick_size"]
    tick_value = specs["tick_value"]
    direction = 1.0 if side == "buy" else -1.0
    return ((exit_price - entry) * direction / tick_size) * tick_value * lot


def fetch_rates(symbol: str, timeframe: int, start: datetime, end: datetime):
    cache_key = (symbol, timeframe, int(start.timestamp()), int(end.timestamp()))
    if cache_key in RATE_CACHE:
        return RATE_CACHE[cache_key]

    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_range(symbol, timeframe, start, end)
    if rates is None:
        RATE_CACHE[cache_key] = []
        return RATE_CACHE[cache_key]

    RATE_CACHE[cache_key] = list(rates)
    return RATE_CACHE[cache_key]


def bar_time(row) -> datetime:
    return datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)


def simulate(config: Config, start: datetime, end: datetime) -> list[Trade]:
    h1 = fetch_rates(config.symbol, mt5.TIMEFRAME_H1, start - timedelta(hours=3), end)
    if len(h1) < 3:
        return []

    trades: list[Trade] = []
    open_pos: dict | None = None
    daily_wins: dict[str, int] = {}
    tp_dist = money_to_price_distance(config.symbol, config.lot, config.tp_money)
    sl_dist = money_to_price_distance(config.symbol, config.lot, config.sl_money)
    if tp_dist <= 0 or sl_dist <= 0:
        return []

    def close_position(exit_time: datetime, exit_price: float, reason: str):
        nonlocal open_pos
        if open_pos is None:
            return
        profit = price_profit(config.symbol, open_pos["side"], config.lot, open_pos["entry"], exit_price)
        trade = Trade(
            entry_time=open_pos["time"],
            exit_time=exit_time,
            symbol=config.symbol,
            side=open_pos["side"],
            entry=open_pos["entry"],
            exit=exit_price,
            profit=profit,
            reason=reason,
        )
        trades.append(trade)
        if profit > 0:
            key = exit_time.date().isoformat()
            daily_wins[key] = daily_wins.get(key, 0) + 1
        open_pos = None

    h1_sorted = sorted(h1, key=lambda row: row["time"])
    for idx in range(1, len(h1_sorted)):
        prev = h1_sorted[idx - 1]
        current = h1_sorted[idx]
        hour = bar_time(current).replace(minute=0, second=0, microsecond=0)
        if hour < start or hour >= end:
            continue

        direction = None
        if float(prev["close"]) > float(prev["open"]):
            direction = "buy"
        elif float(prev["close"]) < float(prev["open"]):
            direction = "sell"

        entry_price = float(current["open"])

        if open_pos and direction and open_pos["side"] != direction:
            close_position(hour, entry_price, "opposite_h1")

        if open_pos is None and direction:
            key = hour.date().isoformat()
            wins = daily_wins.get(key, 0)
            if config.max_daily_wins <= 0 or wins < config.max_daily_wins:
                open_pos = {"side": direction, "entry": entry_price, "time": hour}

        if open_pos is None:
            continue

        side = open_pos["side"]
        entry = open_pos["entry"]
        if side == "buy":
            tp = entry + tp_dist
            sl = entry - sl_dist
        else:
            tp = entry - tp_dist
            sl = entry + sl_dist

        high = float(current["high"])
        low = float(current["low"])
        exit_time = hour + timedelta(hours=1)
        if side == "buy":
            hit_sl = low <= sl
            hit_tp = high >= tp
            if hit_sl and hit_tp:
                close_position(exit_time, sl, "sl_same_bar")
            elif hit_sl:
                close_position(exit_time, sl, "sl")
            elif hit_tp:
                close_position(exit_time, tp, "tp")
        else:
            hit_sl = high >= sl
            hit_tp = low <= tp
            if hit_sl and hit_tp:
                close_position(exit_time, sl, "sl_same_bar")
            elif hit_sl:
                close_position(exit_time, sl, "sl")
            elif hit_tp:
                close_position(exit_time, tp, "tp")

    if open_pos is not None:
        last_price = float(h1_sorted[-1]["close"])
        close_position(min(end, bar_time(h1_sorted[-1])), last_price, "period_end")

    return trades


def summarize(trades: list[Trade]) -> dict:
    wins = [t.profit for t in trades if t.profit > 0]
    losses = [t.profit for t in trades if t.profit < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    net = gross_win - gross_loss
    balance = START_BALANCE
    peak = balance
    max_dd = 0.0
    for t in trades:
        balance += t.profit
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, (peak - balance) / peak * 100.0)
    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / len(trades) * 100.0) if trades else 0.0,
        "gross_win": gross_win,
        "gross_loss": gross_loss,
        "net": net,
        "end_balance": START_BALANCE + net,
        "return_pct": (net / START_BALANCE * 100.0) if START_BALANCE else 0.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else (math.inf if gross_win > 0 else 0.0),
        "max_dd_pct": max_dd,
    }


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    rows = []
    best_by_symbol = {}

    try:
        for symbol in SYMBOLS:
            if mt5.symbol_info(symbol) is None:
                continue
            for lot in LOTS:
                for tp in TP_MONEY:
                    for sl in SL_MONEY:
                        for max_wins in MAX_DAILY_WINS:
                            config = Config(symbol, lot, tp, sl, max_wins)
                            trades = simulate(config, start, end)
                            stats = summarize(trades)
                            if stats["trades"] == 0:
                                continue
                            row = {
                                "symbol": symbol,
                                "lot": lot,
                                "tp_money": tp,
                                "sl_money": sl,
                                "max_daily_wins": max_wins,
                                **stats,
                            }
                            rows.append(row)
                            current_best = best_by_symbol.get(symbol)
                            if current_best is None or (row["net"], row["profit_factor"]) > (
                                current_best["net"],
                                current_best["profit_factor"],
                            ):
                                best_by_symbol[symbol] = row

        rows.sort(key=lambda row: (row["net"], row["profit_factor"], row["win_rate"]), reverse=True)
        out_csv = OUT_DIR / "rami_backtest_last_30_days_optimization.csv"
        with out_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)

        print(f"Period UTC: {start:%Y-%m-%d %H:%M} -> {end:%Y-%m-%d %H:%M}")
        print(f"Start balance model: ${START_BALANCE:.2f}; spread/commission not included; H1 OHLC same-bar SL-first approximation.")
        print(f"CSV: {out_csv}")
        print("\nTop 10 optimized configs:")
        for row in rows[:10]:
            print(
                f"{row['symbol']} lot={row['lot']} TP=${row['tp_money']} SL=${row['sl_money']} "
                f"maxWins={row['max_daily_wins']} trades={row['trades']} win%={row['win_rate']:.2f} "
                f"PF={row['profit_factor']:.2f} net=${row['net']:.2f} ret={row['return_pct']:.2f}% "
                f"DD={row['max_dd_pct']:.2f}%"
            )

        print("\nBest per symbol:")
        for symbol, row in best_by_symbol.items():
            print(
                f"{symbol}: lot={row['lot']} TP=${row['tp_money']} SL=${row['sl_money']} "
                f"maxWins={row['max_daily_wins']} trades={row['trades']} win%={row['win_rate']:.2f} "
                f"PF={row['profit_factor']:.2f} net=${row['net']:.2f} ret={row['return_pct']:.2f}% "
                f"DD={row['max_dd_pct']:.2f}%"
            )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
