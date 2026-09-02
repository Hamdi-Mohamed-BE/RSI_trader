from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf


def _normalize_download(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.rename(columns={column: column.lower().replace(" ", "_") for column in frame.columns})
    required = ["open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Downloaded data is missing columns: {missing}")
    frame = frame[required].copy()
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    return frame.dropna(subset=["open", "close"])


def download_proxy_history(period: str = "730d", interval: str = "1h") -> tuple[pd.DataFrame, pd.DataFrame]:
    spot = yf.download(
        "BTC-USD",
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    futures = yf.download(
        "BTC=F",
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    spot = _normalize_download(spot)
    futures = _normalize_download(futures)
    if spot.empty or futures.empty:
        raise RuntimeError("Yahoo did not return synchronized BTC spot and futures history.")
    return spot, futures


def load_or_download(data_dir: Path, refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    data_dir.mkdir(parents=True, exist_ok=True)
    spot_path = data_dir / "btc-usd-spot-1h.parquet"
    futures_path = data_dir / "btc-cme-continuous-1h.parquet"
    if not refresh and spot_path.exists() and futures_path.exists():
        spot = pd.read_parquet(spot_path)
        futures = pd.read_parquet(futures_path)
        spot.index = pd.to_datetime(spot.index, utc=True)
        futures.index = pd.to_datetime(futures.index, utc=True)
        return spot.sort_index(), futures.sort_index()
    spot, futures = download_proxy_history()
    spot.to_parquet(spot_path)
    futures.to_parquet(futures_path)
    return spot, futures

