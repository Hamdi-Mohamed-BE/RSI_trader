from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from .config import AppConfig, SymbolConfig, apply_settings_mt5_symbol
from .signal_engine import generate_signals, latest_closed_signal
from .strategy import Signal
from .timeframes import timeframe_seconds

LIVE_SCAN_BARS = 600


def extended_history_start(start: datetime, timeframe: str, window_bars: int = LIVE_SCAN_BARS) -> datetime:
    start_utc = start if start.tzinfo is not None else start.replace(tzinfo=timezone.utc)
    return start_utc - timedelta(seconds=timeframe_seconds(timeframe) * window_bars)


def bar_unix(value) -> int:
    if hasattr(value, "timestamp"):
        return int(value.timestamp())
    return int(pd.Timestamp(value).timestamp())


def poll_times(start_unix: int, end_unix: int, poll_seconds: int) -> list[int]:
    if end_unix < start_unix or poll_seconds <= 0:
        return []
    first = first_poll_after(start_unix, poll_seconds)
    times: list[int] = []
    current = first
    while current <= end_unix:
        times.append(current)
        current += poll_seconds
    return times


def first_poll_after(as_of_unix: int, poll_seconds: int) -> int:
    if poll_seconds <= 0:
        return as_of_unix
    first = as_of_unix + poll_seconds - (as_of_unix % poll_seconds)
    if first < as_of_unix:
        first += poll_seconds
    return first


def _forming_bar_index(df: pd.DataFrame, as_of_unix: int) -> int:
    if df.empty:
        return -1
    opens = df["time"].map(bar_unix).tolist()
    lo = 0
    hi = len(opens) - 1
    result = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if opens[mid] <= as_of_unix:
            result = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return result


def rates_window_at(df: pd.DataFrame, as_of_unix: int, window_bars: int = LIVE_SCAN_BARS) -> pd.DataFrame | None:
    form_idx = _forming_bar_index(df, as_of_unix)
    if form_idx < 1:
        return None
    start_idx = max(0, form_idx - (window_bars - 1))
    chunk = df.iloc[start_idx : form_idx + 1]
    if len(chunk) < 2:
        return None
    return chunk


def scan_signal_at(
    df: pd.DataFrame,
    as_of_unix: int,
    symbol_cfg: SymbolConfig,
    config: AppConfig,
    *,
    window_bars: int = LIVE_SCAN_BARS,
) -> tuple[Signal | None, int | None]:
    chunk = rates_window_at(df, as_of_unix, window_bars)
    if chunk is None:
        return None, None
    signal = latest_closed_signal(config, chunk, symbol_cfg, config.risk)
    if signal is None:
        return None, None
    form_idx = _forming_bar_index(df, as_of_unix)
    row_index = form_idx - 1
    if row_index < 0 or row_index >= len(df):
        return None, None
    if bar_unix(df.iloc[row_index]["time"]) != bar_unix(signal.time):
        return None, None
    return signal, row_index


@dataclass(frozen=True)
class LiveScanOpportunity:
    scan_unix: int
    entry_unix: int
    symbol_cfg: SymbolConfig
    df: pd.DataFrame
    row_index: int
    signal: Signal
    point: float


def _index_signals_by_row(df: pd.DataFrame, symbol_cfg: SymbolConfig, config: AppConfig) -> dict[int, Signal]:
    """Map confirmation bar index -> signal (single generate_signals pass)."""
    signals = generate_signals(config, df, symbol_cfg, config.risk)
    if not signals:
        return {}

    times = df["time"].map(bar_unix).to_numpy()
    indexed: dict[int, Signal] = {}
    for signal in signals:
        signal_unix = bar_unix(signal.time)
        matches = np.nonzero(times == signal_unix)[0]
        if len(matches):
            indexed[int(matches[-1])] = signal
    return indexed


def collect_live_scan_opportunities(
    df: pd.DataFrame,
    symbol_cfg: SymbolConfig,
    config: AppConfig,
    *,
    start_unix: int,
    end_unix: int,
    point: float,
    window_bars: int = LIVE_SCAN_BARS,
    retry_max_setups: bool = False,
) -> tuple[list[LiveScanOpportunity], int]:
    """Mirror live bot signal detection: one scan per closed bar, optional retry polls for max_setups."""
    poll_seconds = max(1, int(config.bot.poll_seconds))
    tf_sec = timeframe_seconds(symbol_cfg.timeframe)
    opportunities: list[LiveScanOpportunity] = []
    signals_by_row = _index_signals_by_row(df, symbol_cfg, config)

    if len(df) < 2 or not signals_by_row:
        return [], 0

    opens = [bar_unix(value) for value in df["time"]]
    min_row_for_window = max(0, window_bars - 2)

    for row_index, signal in signals_by_row.items():
        detect_from = opens[row_index] + tf_sec
        if detect_from > end_unix:
            continue
        if detect_from < start_unix:
            continue

        first_scan = first_poll_after(detect_from, poll_seconds)
        if first_scan > end_unix:
            continue

        if row_index < min_row_for_window:
            verified_signal, verified_row = scan_signal_at(
                df, first_scan, symbol_cfg, config, window_bars=window_bars
            )
            if verified_signal is None or verified_row != row_index:
                continue
            signal = verified_signal

        entry_unix = bar_unix(signal.time)
        if entry_unix < start_unix:
            continue

        scan_times = [first_scan]
        if retry_max_setups:
            retry_until = opens[row_index + 1] + tf_sec if row_index + 1 < len(opens) else end_unix
            scan_unix = first_scan + poll_seconds
            while scan_unix <= min(retry_until, end_unix):
                scan_times.append(scan_unix)
                scan_unix += poll_seconds

        broker_signal = apply_settings_mt5_symbol(signal, symbol_cfg, config)
        for scan_unix in scan_times:
            opportunities.append(
                LiveScanOpportunity(
                    scan_unix=scan_unix,
                    entry_unix=entry_unix,
                    symbol_cfg=symbol_cfg,
                    df=df,
                    row_index=row_index,
                    signal=broker_signal,
                    point=point,
                )
            )

    unique_setups = len({item.signal.setup_id for item in opportunities})
    return opportunities, unique_setups
