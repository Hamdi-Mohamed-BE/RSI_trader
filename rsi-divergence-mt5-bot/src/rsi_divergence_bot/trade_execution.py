from __future__ import annotations

import pandas as pd

from .indicators import ema
from .mt5_client import MT5Client
from .strategy import Signal
from .trade_geometry import invalid_market_geometry


def normalized_split_lot(client: MT5Client, symbol: str, lot_per_leg: float) -> float:
    return client.normalize_volume(symbol, lot_per_leg)


def normalized_full_volume(client: MT5Client, symbol: str, lot_per_leg: float) -> float:
    return client.normalize_volume(symbol, lot_per_leg)


def normalized_partial_volumes(client: MT5Client, symbol: str, lot_per_leg: float, num_tps: int) -> tuple[float, float]:
    total_volume = client.normalize_volume(symbol, lot_per_leg * num_tps)
    per_slice = client.normalize_volume(symbol, total_volume / num_tps)
    return total_volume, per_slice


def simulate_single_trade(client: MT5Client, signal: Signal, rows, tp_protection: bool = False) -> dict:
    return simulate_split_trade(client, signal, rows, tp_protection=False)


def simulate_full_trade(client: MT5Client, signal: Signal, rows, tp_protection: bool) -> dict:
    tps = list(signal.tps)
    if not tps:
        return {"pnl": 0.0, "exit_time": None, "exit_kind": "close", "legs": []}
    if invalid_market_geometry(signal.side, signal.entry, signal.sl, tps):
        return {"pnl": 0.0, "exit_time": None, "exit_kind": "invalid_geometry", "legs": []}

    total_volume = normalized_full_volume(client, signal.symbol, signal.lot_per_leg)
    sl = float(signal.sl)
    final_tp = float(tps[-1])
    moved_to_tp = 0
    pnl = 0.0
    exit_time: int | None = None
    exit_kind = "close"
    exit_price = float(signal.entry)
    last_bar_time: int | None = None
    open_position = True

    def row_unix(row) -> int:
        ts = getattr(row, "time", None)
        if hasattr(ts, "timestamp"):
            return int(ts.timestamp())
        return int(pd.Timestamp(ts).timestamp())

    def pnl_for_volume(volume: float, exit_price: float) -> float:
        if signal.side == "buy":
            return client.money_for_distance(signal.symbol, volume, exit_price - signal.entry)
        return client.money_for_distance(signal.symbol, volume, signal.entry - exit_price)

    for row in rows:
        high = float(row.high)
        low = float(row.low)
        close = float(row.close)
        bar_time = row_unix(row)
        last_bar_time = bar_time

        if not open_position:
            break

        if signal.side == "buy":
            if low <= sl:
                exit_price = sl
                pnl = pnl_for_volume(total_volume, exit_price)
                exit_kind = "sl"
                exit_time = bar_time
                open_position = False
                break
            if high >= final_tp:
                exit_price = final_tp
                pnl = pnl_for_volume(total_volume, exit_price)
                exit_kind = f"tp{len(tps)}"
                exit_time = bar_time
                open_position = False
                break
            if tp_protection:
                for index, tp in enumerate(tps[:-1], start=1):
                    if index <= moved_to_tp:
                        continue
                    if high >= tp:
                        sl = max(sl, float(tp))
                        moved_to_tp = index
        else:
            if high >= sl:
                exit_price = sl
                pnl = pnl_for_volume(total_volume, exit_price)
                exit_kind = "sl"
                exit_time = bar_time
                open_position = False
                break
            if low <= final_tp:
                exit_price = final_tp
                pnl = pnl_for_volume(total_volume, exit_price)
                exit_kind = f"tp{len(tps)}"
                exit_time = bar_time
                open_position = False
                break
            if tp_protection:
                for index, tp in enumerate(tps[:-1], start=1):
                    if index <= moved_to_tp:
                        continue
                    if low <= tp:
                        sl = min(sl, float(tp))
                        moved_to_tp = index

    if open_position:
        exit_time = last_bar_time
        if exit_time is not None:
            exit_price = close
            pnl = pnl_for_volume(total_volume, exit_price)
            exit_kind = "close"

    leg_results = [
        {
            "leg": 1,
            "entry": round(float(signal.entry), 5),
            "sl": round(float(sl), 5),
            "exit_sl": round(float(sl), 5),
            "initial_sl": round(float(signal.sl), 5),
            "tp": round(float(final_tp), 5),
            "lot": total_volume,
            "exit_price": round(float(exit_price), 5),
            "exit_time": exit_time,
            "exit_kind": exit_kind,
            "pnl": round(float(pnl), 2),
        }
    ]
    return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind, "legs": leg_results}


def simulate_silver_optimized_trade(client: MT5Client, signal: Signal, rows) -> dict:
    tps = list(signal.tps)
    if not tps or signal.algorithm != "silver_optimized":
        return {"pnl": 0.0, "exit_time": None, "exit_kind": "invalid_geometry", "legs": []}
    if invalid_market_geometry(signal.side, signal.entry, signal.sl, tps):
        return {"pnl": 0.0, "exit_time": None, "exit_kind": "invalid_geometry", "legs": []}

    frame = pd.DataFrame(rows)
    if frame.empty:
        return {"pnl": 0.0, "exit_time": None, "exit_kind": "close", "legs": []}

    fast_len = int(signal.ema_fast_len or 21)
    slow_len = int(signal.ema_slow_len or 55)
    frame["ema_fast"] = ema(frame["close"], fast_len)
    frame["ema_slow"] = ema(frame["close"], slow_len)

    total_volume = normalized_full_volume(client, signal.symbol, signal.lot_per_leg)
    sl = float(signal.sl)
    tp = float(tps[0])
    trail_offset = float(signal.atr_at_entry or abs(signal.entry - signal.sl)) * float(signal.trail_atr_mult or 1.5)
    pnl = 0.0
    exit_time: int | None = None
    exit_kind = "close"
    exit_price = float(signal.entry)
    last_bar_time: int | None = None
    open_position = True
    peak = float(signal.entry)
    trough = float(signal.entry)

    def row_unix(row) -> int:
        ts = getattr(row, "time", None)
        if hasattr(ts, "timestamp"):
            return int(ts.timestamp())
        return int(pd.Timestamp(ts).timestamp())

    def pnl_for_volume(volume: float, price: float) -> float:
        if signal.side == "buy":
            return client.money_for_distance(signal.symbol, volume, price - signal.entry)
        return client.money_for_distance(signal.symbol, volume, signal.entry - price)

    for row in frame.itertuples(index=False):
        high = float(row.high)
        low = float(row.low)
        close = float(row.close)
        ema_fast = float(row.ema_fast)
        ema_slow = float(row.ema_slow)
        bar_time = row_unix(row)
        last_bar_time = bar_time

        if signal.side == "buy":
            peak = max(peak, high)
            trail_stop = max(sl, peak - trail_offset)
            if close < ema_slow and ema_fast < ema_slow:
                exit_price = close
                pnl = pnl_for_volume(total_volume, exit_price)
                exit_kind = "regime"
                exit_time = bar_time
                open_position = False
                break
            if low <= trail_stop:
                exit_price = trail_stop
                pnl = pnl_for_volume(total_volume, exit_price)
                exit_kind = "sl" if trail_stop <= sl else "trail"
                exit_time = bar_time
                open_position = False
                break
            if high >= tp:
                exit_price = tp
                pnl = pnl_for_volume(total_volume, exit_price)
                exit_kind = "tp1"
                exit_time = bar_time
                open_position = False
                break
        else:
            trough = min(trough, low)
            trail_stop = min(sl, trough + trail_offset)
            if close > ema_slow and ema_fast > ema_slow:
                exit_price = close
                pnl = pnl_for_volume(total_volume, exit_price)
                exit_kind = "regime"
                exit_time = bar_time
                open_position = False
                break
            if high >= trail_stop:
                exit_price = trail_stop
                pnl = pnl_for_volume(total_volume, exit_price)
                exit_kind = "sl" if trail_stop >= sl else "trail"
                exit_time = bar_time
                open_position = False
                break
            if low <= tp:
                exit_price = tp
                pnl = pnl_for_volume(total_volume, exit_price)
                exit_kind = "tp1"
                exit_time = bar_time
                open_position = False
                break

    if open_position and last_bar_time is not None:
        exit_time = last_bar_time
        exit_price = float(frame.iloc[-1]["close"])
        pnl = pnl_for_volume(total_volume, exit_price)
        exit_kind = "close"

    leg_results = [
        {
            "leg": 1,
            "entry": round(float(signal.entry), 5),
            "sl": round(float(signal.sl), 5),
            "exit_sl": round(float(sl), 5),
            "initial_sl": round(float(signal.sl), 5),
            "tp": round(float(tp), 5),
            "lot": total_volume,
            "exit_price": round(float(exit_price), 5),
            "exit_time": exit_time,
            "exit_kind": exit_kind,
            "pnl": round(float(pnl), 2),
        }
    ]
    return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind, "legs": leg_results}


def simulate_split_trade(client: MT5Client, signal: Signal, rows, tp_protection: bool) -> dict:
    if invalid_market_geometry(signal.side, signal.entry, signal.sl, signal.tps):
        return {"pnl": 0.0, "exit_time": None, "exit_kind": "invalid_geometry", "legs": []}
    lot_per_leg = normalized_split_lot(client, signal.symbol, signal.lot_per_leg)
    active = [True for _ in signal.tps]
    stops = [signal.sl for _ in signal.tps]
    leg_results: list[dict] = []
    pnl = 0.0
    close = signal.entry
    exit_time: int | None = None
    exit_kind = "close"
    last_bar_time: int | None = None

    def row_unix(row) -> int:
        ts = getattr(row, "time", None)
        if hasattr(ts, "timestamp"):
            return int(ts.timestamp())
        return int(pd.Timestamp(ts).timestamp())

    def close_leg(index: int, exit_price: float, bar_time: int, kind: str) -> None:
        nonlocal pnl, exit_kind
        if signal.side == "buy":
            leg_pnl = client.money_for_distance(signal.symbol, lot_per_leg, exit_price - signal.entry)
        else:
            leg_pnl = client.money_for_distance(signal.symbol, lot_per_leg, signal.entry - exit_price)
        pnl += leg_pnl
        active[index] = False
        exit_kind = kind
        leg_results.append(
            {
                "leg": index + 1,
                "entry": round(float(signal.entry), 5),
                "sl": round(float(signal.sl), 5),
                "exit_sl": round(float(stops[index]), 5),
                "tp": round(float(signal.tps[index]), 5),
                "lot": lot_per_leg,
                "exit_price": round(float(exit_price), 5),
                "exit_time": bar_time,
                "exit_kind": kind,
                "pnl": round(float(leg_pnl), 2),
            }
        )

    for row in rows:
        high = float(row.high)
        low = float(row.low)
        close = float(row.close)
        bar_time = row_unix(row)
        last_bar_time = bar_time
        if signal.side == "buy":
            for index, is_active in enumerate(active):
                if is_active and low <= stops[index]:
                    close_leg(index, stops[index], bar_time, "sl")
            for index, tp in enumerate(signal.tps):
                if active[index] and high >= tp:
                    close_leg(index, tp, bar_time, f"tp{index + 1}")
                    if tp_protection:
                        for move_index, still_active in enumerate(active):
                            if still_active and stops[move_index] < tp:
                                stops[move_index] = tp
        else:
            for index, is_active in enumerate(active):
                if is_active and high >= stops[index]:
                    close_leg(index, stops[index], bar_time, "sl")
            for index, tp in enumerate(signal.tps):
                if active[index] and low <= tp:
                    close_leg(index, tp, bar_time, f"tp{index + 1}")
                    if tp_protection:
                        for move_index, still_active in enumerate(active):
                            if still_active and stops[move_index] > tp:
                                stops[move_index] = tp
        if not any(active):
            exit_time = bar_time
            return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind, "legs": leg_results}

    exit_time = last_bar_time
    if exit_time is None:
        return {"pnl": pnl, "exit_time": None, "exit_kind": exit_kind, "legs": leg_results}
    for index, is_active in enumerate(active):
        if not is_active:
            continue
        close_leg(index, close, int(exit_time), "close")
    return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind, "legs": leg_results}


def simulate_partial_trade(client: MT5Client, signal: Signal, rows, tp_protection: bool) -> dict:
    tps = list(signal.tps)
    if not tps:
        return {"pnl": 0.0, "exit_time": None, "exit_kind": "close"}
    if invalid_market_geometry(signal.side, signal.entry, signal.sl, tps):
        return {"pnl": 0.0, "exit_time": None, "exit_kind": "invalid_geometry"}

    total_volume, slice_volume = normalized_partial_volumes(client, signal.symbol, signal.lot_per_leg, len(tps))
    remaining_volume = total_volume
    sl = float(signal.sl)
    partial_closed = 0
    pnl = 0.0
    exit_time: int | None = None
    exit_kind = "close"
    last_bar_time: int | None = None

    def row_unix(row) -> int:
        ts = getattr(row, "time", None)
        if hasattr(ts, "timestamp"):
            return int(ts.timestamp())
        return int(pd.Timestamp(ts).timestamp())

    def pnl_for_slice(volume: float, exit_price: float) -> float:
        if signal.side == "buy":
            return client.money_for_distance(signal.symbol, volume, exit_price - signal.entry)
        return client.money_for_distance(signal.symbol, volume, signal.entry - exit_price)

    for row in rows:
        high = float(row.high)
        low = float(row.low)
        close = float(row.close)
        bar_time = row_unix(row)
        last_bar_time = bar_time

        if remaining_volume <= 0:
            exit_time = bar_time
            return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}

        if signal.side == "buy":
            if low <= sl:
                pnl += pnl_for_slice(remaining_volume, sl)
                exit_kind = "sl"
                exit_time = bar_time
                return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}

            while partial_closed < len(tps) - 1 and high >= tps[partial_closed]:
                close_volume = slice_volume if partial_closed < len(tps) - 2 else remaining_volume - slice_volume
                close_volume = min(client.normalize_volume(signal.symbol, close_volume), remaining_volume)
                if close_volume <= 0:
                    break
                pnl += pnl_for_slice(close_volume, tps[partial_closed])
                remaining_volume -= close_volume
                partial_closed += 1
                exit_kind = f"tp{partial_closed}"
                if tp_protection:
                    sl = max(sl, tps[partial_closed - 1])

            if remaining_volume > 0 and high >= tps[-1]:
                pnl += pnl_for_slice(remaining_volume, tps[-1])
                exit_kind = f"tp{len(tps)}"
                exit_time = bar_time
                return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}
        else:
            if high >= sl:
                pnl += pnl_for_slice(remaining_volume, sl)
                exit_kind = "sl"
                exit_time = bar_time
                return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}

            while partial_closed < len(tps) - 1 and low <= tps[partial_closed]:
                close_volume = slice_volume if partial_closed < len(tps) - 2 else remaining_volume - slice_volume
                close_volume = min(client.normalize_volume(signal.symbol, close_volume), remaining_volume)
                if close_volume <= 0:
                    break
                pnl += pnl_for_slice(close_volume, tps[partial_closed])
                remaining_volume -= close_volume
                partial_closed += 1
                exit_kind = f"tp{partial_closed}"
                if tp_protection:
                    sl = min(sl, tps[partial_closed - 1])

            if remaining_volume > 0 and low <= tps[-1]:
                pnl += pnl_for_slice(remaining_volume, tps[-1])
                exit_kind = f"tp{len(tps)}"
                exit_time = bar_time
                return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}

    exit_time = last_bar_time
    if remaining_volume > 0:
        pnl += pnl_for_slice(remaining_volume, close)
    return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}
