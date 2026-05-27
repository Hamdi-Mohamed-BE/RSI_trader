from __future__ import annotations

import math


def invalid_market_geometry(side: str, entry: float, sl: float, tps: list[float], *, label: str = "entry") -> str | None:
    side = side.lower()
    prices = [entry, sl, *tps]
    if side not in {"buy", "sell"}:
        return f"unsupported side {side}"
    if not tps:
        return "missing TP levels"
    if any(not math.isfinite(float(price)) for price in prices):
        return "entry, SL, and TPs must be finite prices"
    if entry <= 0:
        return f"{label} must be greater than zero"

    if side == "buy":
        if sl >= entry:
            return f"BUY SL must be below {label} {entry:.5f}: sl={sl:.5f}"
        bad_tps = [tp for tp in tps if tp <= entry]
        if bad_tps:
            return f"BUY TPs must be above {label} {entry:.5f}: {bad_tps}"
        return None

    if sl <= entry:
        return f"SELL SL must be above {label} {entry:.5f}: sl={sl:.5f}"
    bad_tps = [tp for tp in tps if tp >= entry]
    if bad_tps:
        return f"SELL TPs must be below {label} {entry:.5f}: {bad_tps}"
    return None


def default_stop_loss_one_to_one(side: str, entry: float, reference_tp: float) -> float:
    """Risk distance from entry to a reference TP, mirrored on the SL side (1:1 RR)."""
    side = side.lower()
    distance = abs(float(reference_tp) - float(entry))
    if side == "buy":
        return float(entry) - distance
    if side == "sell":
        return float(entry) + distance
    raise ValueError(f"unsupported side {side}")


def synthetic_stop_loss_reference_tp(tps: list[float]) -> float:
    """Use second TP for default 1:1 SL when available; otherwise first TP."""
    if len(tps) >= 2:
        return float(tps[1])
    return float(tps[0])


def invalid_pending_geometry(order_kind: str, current_bid: float, current_ask: float, entry: float) -> str | None:
    if order_kind == "buy_limit" and entry >= current_ask:
        return f"BUY LIMIT entry must be below current ask {current_ask:.5f}: entry={entry:.5f}"
    if order_kind == "sell_limit" and entry <= current_bid:
        return f"SELL LIMIT entry must be above current bid {current_bid:.5f}: entry={entry:.5f}"
    if order_kind == "buy_stop" and entry <= current_ask:
        return f"BUY STOP entry must be above current ask {current_ask:.5f}: entry={entry:.5f}"
    if order_kind == "sell_stop" and entry >= current_bid:
        return f"SELL STOP entry must be below current bid {current_bid:.5f}: entry={entry:.5f}"
    return None
