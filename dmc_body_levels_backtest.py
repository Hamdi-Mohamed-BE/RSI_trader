from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

import MetaTrader5 as mt5


START = datetime(2026, 6, 12, tzinfo=timezone.utc)
END = datetime(2026, 7, 12, tzinfo=timezone.utc)
START_BALANCE = 300.0
FIXED_LOT = 0.01
LOOKBACK = 36
MIN_CONFLUENCE = 1
STOP_BUFFER_POINTS = 50
MAX_TRADES_PER_DAY = 3
REWARD_RISK = 2.0

TERMINAL_PATHS = [
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files\JustMarkets MetaTrader 5\terminal64.exe",
]

TF_SEC = {
    mt5.TIMEFRAME_M15: 15 * 60,
    mt5.TIMEFRAME_H1: 60 * 60,
    mt5.TIMEFRAME_H4: 4 * 60 * 60,
    mt5.TIMEFRAME_D1: 24 * 60 * 60,
    mt5.TIMEFRAME_W1: 7 * 24 * 60 * 60,
    mt5.TIMEFRAME_MN1: 31 * 24 * 60 * 60,
}

SOURCES = [
    (mt5.TIMEFRAME_MN1, "M"),
    (mt5.TIMEFRAME_W1, "W"),
    (mt5.TIMEFRAME_D1, "D"),
    (mt5.TIMEFRAME_H4, "4H"),
    (mt5.TIMEFRAME_H1, "1H"),
]

ALIASES = {
    "XAUUSD": ["XAUUSD", "XAUUSDm", "XAUUSD.raw", "GOLD", "XAUUSD-STD"],
    "BTCUSD": ["BTCUSD", "BTCUSDm", "BTCUSD.raw", "BTCUSD-STD", "BTC"],
    "US30": ["US30", "US30m", "US30.cash", "DJ30", "DJI", "US30-STD", "US30.x10"],
    "US100": ["US100", "US100m", "US100.cash", "NAS100", "USTEC", "NAS100.cash", "NAS100m", "US100-STD"],
}


def initialize_mt5() -> None:
    if mt5.initialize():
        return
    for path in TERMINAL_PATHS:
        if mt5.initialize(path=path):
            return
    raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")


def as_dt(timestamp: int) -> datetime:
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)


def canonical(symbol: str) -> str:
    value = "".join(ch for ch in symbol.upper() if ch.isalnum())
    for suffix in ("RAW", "PRO", "MICRO", "MINI", "CASH", "STD", "M", "C"):
        if value.endswith(suffix) and len(value) > len(suffix) + 3:
            value = value[: -len(suffix)]
            break
    if value in {"GOLD", "XAU", "XAAUSD"}:
        return "XAUUSD"
    if value == "BTC":
        return "BTCUSD"
    if value in {"DJ30", "DJI", "DOW"}:
        return "US30"
    if value in {"NAS100", "USTEC", "USTEC100", "NDX"}:
        return "US100"
    return value


def resolve_symbol(target: str, broker_symbols: list[str]) -> str | None:
    for candidate in ALIASES[target]:
        for symbol in broker_symbols:
            if symbol.upper() == candidate.upper():
                mt5.symbol_select(symbol, True)
                return symbol
    for symbol in broker_symbols:
        if canonical(symbol) == target:
            mt5.symbol_select(symbol, True)
            return symbol
    return None


def get_rates(symbol: str, timeframe: int, start: datetime, end: datetime) -> list[dict]:
    raw = mt5.copy_rates_range(symbol, timeframe, start, end)
    if raw is None:
        return []
    return [
        {
            "time": as_dt(row["time"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        for row in raw
    ]


def completed_bars(all_rates: list[dict], timeframe: int, close_time: datetime) -> list[dict]:
    seconds = TF_SEC[timeframe]
    completed = [row for row in all_rates if row["time"] + timedelta(seconds=seconds) <= close_time]
    return list(reversed(completed[-LOOKBACK:]))


def body_top(bar: dict) -> float:
    return max(bar["open"], bar["close"])


def body_bottom(bar: dict) -> float:
    return min(bar["open"], bar["close"])


def classify(series_newest: list[dict], idx: int, level: float) -> int:
    touched = False
    body_through = False
    fully_above = False
    fully_below = False
    for newer in series_newest[:idx]:
        if newer["low"] <= level <= newer["high"]:
            touched = True
        if newer["low"] > level:
            fully_above = True
        if newer["high"] < level:
            fully_below = True
        if body_bottom(newer) < level < body_top(newer):
            body_through = True
    if body_through or (fully_above and fully_below and not touched):
        return 2
    return 1 if touched else 0


def add_level(levels: list[dict], price: float, state: int, tag: str, tick_size: float) -> None:
    if not price or math.isnan(price):
        return
    for level in levels:
        if abs(level["price"] - price) <= tick_size:
            tags = level["tags"].split("/")
            if tag not in tags:
                level["tags"] += "/" + tag
                level["conf"] += 1
            level["state"] = min(level["state"], state)
            return
    levels.append({"price": price, "state": state, "tags": tag, "conf": 1})


def build_levels(htf_data: dict[int, list[dict]], close_time: datetime, tick_size: float) -> list[dict]:
    levels: list[dict] = []
    for timeframe, tag in SOURCES:
        series = completed_bars(htf_data[timeframe], timeframe, close_time)
        for idx, bar in enumerate(series):
            top = body_top(bar)
            bottom = body_bottom(bar)
            add_level(levels, top, classify(series, idx, top), tag, tick_size)
            add_level(levels, bottom, classify(series, idx, bottom), tag, tick_size)
    return levels


def level_cache_key(close_time: datetime) -> datetime:
    return close_time.replace(minute=0, second=0, microsecond=0)


def active_pocket(levels: list[dict], reference: float) -> tuple[float | None, float | None, str, str]:
    floor = None
    target = None
    floor_tag = ""
    target_tag = ""
    for level in levels:
        if level["state"] != 0 or level["conf"] < MIN_CONFLUENCE:
            continue
        price = level["price"]
        if price < reference and (floor is None or price > floor):
            floor = price
            floor_tag = level["tags"]
        if price > reference and (target is None or price < target):
            target = price
            target_tag = level["tags"]
    return floor, target, floor_tag, target_tag


def nearest_above(levels: list[dict], reference: float) -> float | None:
    values = [level["price"] for level in levels if level["state"] == 0 and level["conf"] >= MIN_CONFLUENCE and level["price"] > reference]
    return min(values) if values else None


def nearest_below(levels: list[dict], reference: float) -> float | None:
    values = [level["price"] for level in levels if level["state"] == 0 and level["conf"] >= MIN_CONFLUENCE and level["price"] < reference]
    return max(values) if values else None


def calc_profit(symbol: str, side: str, lot: float, entry: float, exit_price: float) -> float:
    order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    value = mt5.order_calc_profit(order_type, symbol, lot, entry, exit_price)
    return float(value or 0.0)


def backtest_symbol(label: str, symbol: str) -> dict:
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return {"label": label, "symbol": symbol, "error": "missing symbol info"}

    point = float(symbol_info.point)
    tick_size = float(symbol_info.trade_tick_size or point)
    buffer = STOP_BUFFER_POINTS * point
    warmup = START - timedelta(days=1250)
    m15 = get_rates(symbol, mt5.TIMEFRAME_M15, START - timedelta(days=3), END + timedelta(days=1))
    htf_data = {timeframe: get_rates(symbol, timeframe, warmup, END + timedelta(days=1)) for timeframe, _ in SOURCES}
    if len(m15) < 100:
        return {"label": label, "symbol": symbol, "error": f"not enough M15 data ({len(m15)})"}
    for timeframe, data in htf_data.items():
        if len(data) < 5:
            return {"label": label, "symbol": symbol, "error": f"not enough TF {timeframe} data ({len(data)})"}

    levels_by_hour: dict[datetime, list[dict]] = {}
    balance = START_BALANCE
    equity_curve = [balance]
    trades: list[dict] = []
    open_trade = None
    day_counts: dict[str, int] = {}

    for idx in range(2, len(m15) - 1):
        bar = m15[idx]
        next_bar = m15[idx + 1]
        close_time = bar["time"] + timedelta(minutes=15)
        if close_time < START or close_time >= END:
            continue

        if open_trade is not None:
            side = open_trade["side"]
            exit_price = None
            outcome = None
            if side == "buy":
                if bar["low"] <= open_trade["sl"]:
                    exit_price = open_trade["sl"]
                    outcome = "SL"
                elif bar["high"] >= open_trade["tp"]:
                    exit_price = open_trade["tp"]
                    outcome = "TP"
            else:
                if bar["high"] >= open_trade["sl"]:
                    exit_price = open_trade["sl"]
                    outcome = "SL"
                elif bar["low"] <= open_trade["tp"]:
                    exit_price = open_trade["tp"]
                    outcome = "TP"
            if exit_price is not None:
                pnl = calc_profit(symbol, side, FIXED_LOT, open_trade["entry"], exit_price)
                balance += pnl
                open_trade.update(exit_time=bar["time"], exit=exit_price, outcome=outcome, pnl=pnl, balance=balance)
                trades.append(open_trade)
                equity_curve.append(balance)
                open_trade = None

        if open_trade is not None:
            continue

        day = close_time.date().isoformat()
        if MAX_TRADES_PER_DAY > 0 and day_counts.get(day, 0) >= MAX_TRADES_PER_DAY:
            continue

        key = level_cache_key(close_time)
        if key not in levels_by_hour:
            levels_by_hour[key] = build_levels(htf_data, close_time, tick_size)
        levels = levels_by_hour[key]

        prior = m15[idx - 1]
        floor, target, floor_tag, target_tag = active_pocket(levels, prior["close"])
        if floor is None and target is None:
            continue

        top = body_top(bar)
        bottom = body_bottom(bar)
        gain = target is not None and bottom < target < top and bar["close"] > target
        lose = floor is not None and bottom < floor < top and bar["close"] < floor
        fail_hi = target is not None and bar["high"] >= target and top <= target and bar["close"] < target
        fail_lo = floor is not None and bar["low"] <= floor and bottom >= floor and bar["close"] > floor

        entry = next_bar["open"]
        side = None
        setup = ""
        sl = 0.0
        tp = 0.0

        if fail_lo:
            side, setup, sl = "buy", "FAIL_LOW " + floor_tag, floor - buffer
            nxt = nearest_above(levels, entry)
            tp = nxt if nxt and nxt > entry else entry + abs(entry - sl) * REWARD_RISK
        elif fail_hi:
            side, setup, sl = "sell", "FAIL_HIGH " + target_tag, target + buffer
            nxt = nearest_below(levels, entry)
            tp = nxt if nxt and nxt < entry else entry - abs(entry - sl) * REWARD_RISK
        elif gain:
            side, setup, sl = "buy", "GAIN " + target_tag, target - buffer
            nxt = nearest_above(levels, entry)
            tp = nxt if nxt and nxt > entry else entry + abs(entry - sl) * REWARD_RISK
        elif lose:
            side, setup, sl = "sell", "LOSE " + floor_tag, floor + buffer
            nxt = nearest_below(levels, entry)
            tp = nxt if nxt and nxt < entry else entry - abs(entry - sl) * REWARD_RISK

        if side is None:
            continue
        if side == "buy" and not (sl < entry < tp):
            continue
        if side == "sell" and not (tp < entry < sl):
            continue

        day_counts[day] = day_counts.get(day, 0) + 1
        open_trade = {
            "symbol": label,
            "broker_symbol": symbol,
            "side": side,
            "setup": setup,
            "signal_time": close_time,
            "entry_time": next_bar["time"],
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "lot": FIXED_LOT,
        }

    if open_trade is not None:
        last = m15[-1]
        pnl = calc_profit(symbol, open_trade["side"], FIXED_LOT, open_trade["entry"], last["close"])
        balance += pnl
        open_trade.update(exit_time=last["time"], exit=last["close"], outcome="EOD", pnl=pnl, balance=balance)
        trades.append(open_trade)
        equity_curve.append(balance)

    wins = [trade for trade in trades if trade["pnl"] > 0]
    losses = [trade for trade in trades if trade["pnl"] < 0]
    gross_win = sum(trade["pnl"] for trade in wins)
    gross_loss = -sum(trade["pnl"] for trade in losses)
    peak = START_BALANCE
    max_dd = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak * 100.0 if peak else 0.0)

    by_setup: dict[str, dict] = {}
    for trade in trades:
        key = trade["setup"].split()[0]
        row = by_setup.setdefault(key, {"trades": 0, "pnl": 0.0, "wins": 0})
        row["trades"] += 1
        row["pnl"] += trade["pnl"]
        row["wins"] += 1 if trade["pnl"] > 0 else 0

    return {
        "label": label,
        "symbol": symbol,
        "trades": trades,
        "final": balance,
        "profit": balance - START_BALANCE,
        "return_pct": (balance / START_BALANCE - 1.0) * 100.0,
        "win_rate": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "max_dd_pct": max_dd,
        "profit_factor": gross_win / gross_loss if gross_loss else None,
        "by_setup": by_setup,
    }


def main() -> None:
    initialize_mt5()
    account = mt5.account_info()
    print(f"MT5 account: {account.login if account else 'unknown'} server={account.server if account else 'unknown'}")

    broker_symbols = [symbol.name for symbol in mt5.symbols_get() or []]
    resolved = {target: resolve_symbol(target, broker_symbols) for target in ("XAUUSD", "BTCUSD", "US30", "US100")}
    print(f"Resolved: {resolved}")
    print()
    print("DMC BODY LEVELS EA BACKTEST")
    print(f"Window UTC: {START:%Y-%m-%d} -> {END:%Y-%m-%d}, start=${START_BALANCE:.2f}, lot={FIXED_LOT}")
    print("Assumptions: M15 next-open entry, conservative same-bar SL-first, max 3 trades/day/symbol, target next virgin level else 2R.")
    print()

    combined = START_BALANCE
    for label, symbol in resolved.items():
        if symbol is None:
            print(f"{label}: ERROR could not resolve broker symbol")
            continue
        result = backtest_symbol(label, symbol)
        if "error" in result:
            print(f"{label} ({symbol}): ERROR {result['error']}")
            continue
        combined += result["profit"]
        pf = "inf" if result["profit_factor"] is None else f"{result['profit_factor']:.2f}"
        print(
            f"{label} -> {symbol}: trades={len(result['trades'])}, final=${result['final']:.2f}, "
            f"PnL=${result['profit']:.2f}, return={result['return_pct']:.2f}%, "
            f"win={result['win_rate']:.2f}%, maxDD={result['max_dd_pct']:.2f}%, PF={pf}"
        )
        for setup, row in sorted(result["by_setup"].items()):
            win_rate = row["wins"] / row["trades"] * 100.0 if row["trades"] else 0.0
            print(f"  {setup}: trades={row['trades']}, pnl=${row['pnl']:.2f}, win={win_rate:.1f}%")
        print("  Last 5 trades:")
        for trade in result["trades"][-5:]:
            print(
                f"    {trade['signal_time']:%m-%d %H:%M} {trade['side'].upper()} {trade['setup']} "
                f"entry={trade['entry']:.5f} sl={trade['sl']:.5f} tp={trade['tp']:.5f} "
                f"{trade['outcome']} pnl=${trade['pnl']:.2f}"
            )
        print()

    print(
        f"Combined independent-symbol estimate: ${START_BALANCE:.2f} -> ${combined:.2f}, "
        f"PnL=${combined - START_BALANCE:.2f}, return={(combined / START_BALANCE - 1.0) * 100.0:.2f}%"
    )
    mt5.shutdown()


if __name__ == "__main__":
    main()
