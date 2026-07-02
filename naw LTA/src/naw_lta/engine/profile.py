from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VolumeProfile:
    poc: float
    vah: float
    val: float
    hvns: list[float]
    lvns: list[float]
    total_volume: float
    source: str


def build_bar_profile(
    frame: pd.DataFrame, bins: int = 48, value_area_percent: float = 0.70
) -> VolumeProfile:
    if frame.empty:
        raise ValueError("Cannot build a volume profile from empty bars.")
    typical = (frame["high"] + frame["low"] + frame["close"]) / 3.0
    volume = frame.get("volume", pd.Series(1.0, index=frame.index)).fillna(0.0).astype(float)
    return _profile(typical.to_numpy(), volume.to_numpy(), bins, value_area_percent, "ohlcv-1m")


def build_trade_profile(
    frame: pd.DataFrame, bins: int = 48, value_area_percent: float = 0.70
) -> VolumeProfile:
    if frame.empty or "price" not in frame.columns:
        raise ValueError("Trade tape must contain price data.")
    size_column = "size" if "size" in frame.columns else "volume"
    sizes = frame.get(size_column, pd.Series(1.0, index=frame.index)).fillna(0.0).astype(float)
    return _profile(
        frame["price"].astype(float).to_numpy(),
        sizes.to_numpy(),
        bins,
        value_area_percent,
        "trades",
    )


def _profile(
    prices: np.ndarray,
    sizes: np.ndarray,
    bins: int,
    value_area_percent: float,
    source: str,
) -> VolumeProfile:
    valid = np.isfinite(prices) & np.isfinite(sizes)
    prices = prices[valid]
    sizes = sizes[valid]
    if not len(prices):
        raise ValueError("Volume profile contains no valid observations.")
    low, high = float(prices.min()), float(prices.max())
    if high <= low:
        high = low + max(abs(low) * 1e-6, 1e-6)
    histogram, edges = np.histogram(prices, bins=bins, range=(low, high), weights=sizes)
    centers = (edges[:-1] + edges[1:]) / 2.0
    poc_index = int(np.argmax(histogram))
    total = float(histogram.sum())

    ranked = np.argsort(histogram)[::-1]
    selected: list[int] = []
    running = 0.0
    target = total * value_area_percent
    for index in ranked:
        selected.append(int(index))
        running += float(histogram[index])
        if running >= target:
            break
    selected_centers = centers[selected] if selected else np.array([centers[poc_index]])
    hvn_indices = ranked[: min(3, len(ranked))]
    nonzero = np.flatnonzero(histogram > 0)
    lvn_indices = nonzero[np.argsort(histogram[nonzero])[: min(3, len(nonzero))]] if len(nonzero) else []
    return VolumeProfile(
        poc=float(centers[poc_index]),
        vah=float(selected_centers.max()),
        val=float(selected_centers.min()),
        hvns=[float(centers[index]) for index in hvn_indices],
        lvns=[float(centers[index]) for index in lvn_indices],
        total_volume=total,
        source=source,
    )


def order_book_metrics(frame: pd.DataFrame | None) -> dict[str, float | None]:
    empty = {"imbalance": None, "microprice": None, "spread": None, "depth": None}
    if frame is None or frame.empty:
        return empty
    row = frame.iloc[-1]
    bid_sizes: list[float] = []
    ask_sizes: list[float] = []
    for level in range(10):
        suffix = f"{level:02d}"
        bid = row.get(f"bid_sz_{suffix}")
        ask = row.get(f"ask_sz_{suffix}")
        if pd.notna(bid):
            bid_sizes.append(float(bid))
        if pd.notna(ask):
            ask_sizes.append(float(ask))
    bid_total, ask_total = sum(bid_sizes), sum(ask_sizes)
    total = bid_total + ask_total
    imbalance = (bid_total - ask_total) / total if total else None
    bid_price = row.get("bid_px_00")
    ask_price = row.get("ask_px_00")
    best_bid_size = float(row.get("bid_sz_00", 0.0) or 0.0)
    best_ask_size = float(row.get("ask_sz_00", 0.0) or 0.0)
    top_total = best_bid_size + best_ask_size
    microprice = None
    spread = None
    if pd.notna(bid_price) and pd.notna(ask_price):
        bid_price, ask_price = float(bid_price), float(ask_price)
        spread = ask_price - bid_price
        if top_total:
            microprice = (ask_price * best_bid_size + bid_price * best_ask_size) / top_total
    return {
        "imbalance": imbalance,
        "microprice": microprice,
        "spread": spread,
        "depth": total,
    }


def trade_flow_metrics(frame: pd.DataFrame | None) -> dict[str, float | None]:
    empty = {"delta_ratio": None, "buy_volume": None, "sell_volume": None, "session_poc": None}
    if frame is None or frame.empty or "price" not in frame.columns:
        return empty
    size_column = "size" if "size" in frame.columns else "volume"
    sizes = frame.get(size_column, pd.Series(1.0, index=frame.index)).fillna(0.0).astype(float)
    if "side" in frame.columns:
        sides = frame["side"].astype(str).str.upper()
        buy_volume = float(sizes[sides.str.startswith("B")].sum())
        sell_volume = float(sizes[sides.str.startswith("A")].sum())
    else:
        buy_volume = sell_volume = 0.0
    classified = buy_volume + sell_volume
    delta_ratio = (buy_volume - sell_volume) / classified if classified else None
    try:
        session_poc = build_trade_profile(frame, bins=32).poc
    except ValueError:
        session_poc = None
    return {
        "delta_ratio": delta_ratio,
        "buy_volume": buy_volume,
        "sell_volume": sell_volume,
        "session_poc": session_poc,
    }
