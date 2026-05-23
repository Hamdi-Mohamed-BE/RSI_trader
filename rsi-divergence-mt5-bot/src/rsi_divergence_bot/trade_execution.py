from __future__ import annotations

import pandas as pd

from .mt5_client import MT5Client
from .strategy import Signal


def normalized_split_lot(client: MT5Client, symbol: str, lot_per_leg: float) -> float:
    return client.normalize_volume(symbol, lot_per_leg)


def normalized_partial_volumes(client: MT5Client, symbol: str, lot_per_leg: float, num_tps: int) -> tuple[float, float]:
    total_volume = client.normalize_volume(symbol, lot_per_leg * num_tps)
    per_slice = client.normalize_volume(symbol, total_volume / num_tps)
    return total_volume, per_slice


def simulate_single_trade(client: MT5Client, signal: Signal, rows, tp_protection: bool = False) -> dict:
    return simulate_split_trade(client, signal, rows, tp_protection=False)


def simulate_split_trade(client: MT5Client, signal: Signal, rows, tp_protection: bool) -> dict:
    lot_per_leg = normalized_split_lot(client, signal.symbol, signal.lot_per_leg)
    active = [True for _ in signal.tps]
    stops = [signal.sl for _ in signal.tps]
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

    for row in rows:
        high = float(row.high)
        low = float(row.low)
        close = float(row.close)
        bar_time = row_unix(row)
        last_bar_time = bar_time
        if signal.side == "buy":
            for index, is_active in enumerate(active):
                if is_active and low <= stops[index]:
                    pnl += client.money_for_distance(signal.symbol, lot_per_leg, stops[index] - signal.entry)
                    active[index] = False
                    exit_kind = "sl"
            for index, tp in enumerate(signal.tps):
                if active[index] and high >= tp:
                    pnl += client.money_for_distance(signal.symbol, lot_per_leg, tp - signal.entry)
                    active[index] = False
                    exit_kind = f"tp{index + 1}"
                    if tp_protection:
                        for move_index, still_active in enumerate(active):
                            if still_active and stops[move_index] < tp:
                                stops[move_index] = tp
        else:
            for index, is_active in enumerate(active):
                if is_active and high >= stops[index]:
                    pnl += client.money_for_distance(signal.symbol, lot_per_leg, signal.entry - stops[index])
                    active[index] = False
                    exit_kind = "sl"
            for index, tp in enumerate(signal.tps):
                if active[index] and low <= tp:
                    pnl += client.money_for_distance(signal.symbol, lot_per_leg, signal.entry - tp)
                    active[index] = False
                    exit_kind = f"tp{index + 1}"
                    if tp_protection:
                        for move_index, still_active in enumerate(active):
                            if still_active and stops[move_index] > tp:
                                stops[move_index] = tp
        if not any(active):
            exit_time = bar_time
            return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}

    exit_time = last_bar_time
    for index, is_active in enumerate(active):
        if not is_active:
            continue
        if signal.side == "buy":
            pnl += client.money_for_distance(signal.symbol, lot_per_leg, close - signal.entry)
        else:
            pnl += client.money_for_distance(signal.symbol, lot_per_leg, signal.entry - close)
    return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}


def simulate_partial_trade(client: MT5Client, signal: Signal, rows, tp_protection: bool) -> dict:
    tps = list(signal.tps)
    if not tps:
        return {"pnl": 0.0, "exit_time": None, "exit_kind": "close"}

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
