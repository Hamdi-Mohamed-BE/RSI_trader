from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from .config import DATA_ROOT, AssetSpec, ensure_directories


REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def _normalise_download(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        raise RuntimeError("Market-data download returned no rows.")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise RuntimeError(f"Downloaded data is missing columns: {missing}")
    result = frame[REQUIRED_COLUMNS].copy()
    index = pd.DatetimeIndex(pd.to_datetime(result.index, utc=True)).tz_convert(None)
    result.index = index.normalize()
    result = result[~result.index.duplicated(keep="last")].sort_index()
    for column in REQUIRED_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result.dropna(subset=["Open", "High", "Low", "Close"])


def fetch_yahoo(
    asset: AssetSpec,
    *,
    start: str = "2017-01-01",
    end: str | None = None,
    refresh: bool = True,
) -> pd.DataFrame:
    """Download fresh daily OHLCV and retain the exact evidence CSV.

    Yahoo continuous futures/spot series are a preliminary research proxy. They
    are not presented as an MT5 or Databento execution-quality backtest.
    """
    ensure_directories()
    path = DATA_ROOT / f"{asset.key}-daily.csv"
    if path.is_file() and not refresh:
        cached = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
        return _normalise_download(cached)

    end_date = end or (date.today() + timedelta(days=1)).isoformat()
    frame = yf.download(
        asset.ticker,
        start=start,
        end=end_date,
        progress=False,
        auto_adjust=True,
        actions=False,
        threads=False,
    )
    result = _normalise_download(frame)
    output = result.copy()
    output.index.name = "Date"
    output.to_csv(path)
    return result


def read_market_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    return _normalise_download(frame)

