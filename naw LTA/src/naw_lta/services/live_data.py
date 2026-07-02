from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from ..providers import DatabentoProvider
from ..settings import DATA_DIR


LIVE_DIR = DATA_DIR / "live"


class LiveDataStore:
    def __init__(self, provider: DatabentoProvider):
        self.provider = provider
        LIVE_DIR.mkdir(parents=True, exist_ok=True)

    def bars(self, provider_symbol: str, lookback_days: int) -> pd.DataFrame:
        path = self._path(provider_symbol, "bars")
        existing = self._read(path)
        end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        if existing.empty:
            start = end - timedelta(days=lookback_days + 3)
        else:
            last = existing.index[-1].to_pydatetime()
            start = last + timedelta(minutes=1)
        if start < end:
            fresh = self.provider.bars(provider_symbol, start, end)
            existing = pd.concat([existing, fresh]) if not existing.empty else fresh
        existing = existing[~existing.index.duplicated(keep="last")].sort_index()
        existing = existing.loc[existing.index >= end - timedelta(days=lookback_days + 3)]
        self._write(existing, path)
        return existing

    def recent_trades(self, provider_symbol: str, minutes: int = 180) -> pd.DataFrame:
        end = datetime.now(timezone.utc)
        return self.provider.trades(provider_symbol, end - timedelta(minutes=minutes), end)

    def recent_depth(self, provider_symbol: str, minutes: int = 2) -> pd.DataFrame:
        end = datetime.now(timezone.utc)
        return self.provider.depth(provider_symbol, end - timedelta(minutes=minutes), end)

    @staticmethod
    def _path(symbol: str, suffix: str) -> Path:
        return LIVE_DIR / f"{symbol.replace('.', '_')}_{suffix}.pkl"

    @staticmethod
    def _read(path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()
        try:
            return pd.read_pickle(path)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def _write(frame: pd.DataFrame, path: Path) -> None:
        temporary = path.with_suffix(".tmp")
        frame.to_pickle(temporary)
        temporary.replace(path)

