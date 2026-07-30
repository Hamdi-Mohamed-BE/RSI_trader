from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import logging
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from .config import Config
from .models import SymbolSpec
from .symbol_discovery import discover_us100

LOG = logging.getLogger("us100.mt5")


@contextmanager
def connection(cfg: Config):
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None or terminal is None:
            raise RuntimeError("MT5 terminal/account information unavailable")
        if cfg.demo_only and int(account.trade_mode) != int(mt5.ACCOUNT_TRADE_MODE_DEMO):
            raise RuntimeError("DEMO_ONLY=true but the connected account is not demo")
        LOG.info(
            "Connected account=%s server=%s balance=%.2f equity=%.2f",
            account.login,
            account.server,
            account.balance,
            account.equity,
        )
        yield account, terminal
    finally:
        mt5.shutdown()


def discover(cfg: Config) -> tuple[SymbolSpec, list]:
    return discover_us100(cfg.aliases, cfg.symbol_override)


def fetch_m1(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start/end must be timezone-aware")
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M1,
        start.astimezone(timezone.utc),
        end.astimezone(timezone.utc),
    )
    if rates is None or not len(rates):
        raise RuntimeError(f"No M1 data for {symbol}: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def cache_file(cfg: Config, symbol: str, start: datetime, end: datetime) -> Path:
    return cfg.data_dir / f"{symbol.replace('.', '_')}_{start:%Y%m%d}_{end:%Y%m%d}_M1.csv.gz"


def load_or_fetch(
    cfg: Config, symbol: str, start: datetime, end: datetime, refresh: bool = False
) -> tuple[pd.DataFrame, Path]:
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    path = cache_file(cfg, symbol, start, end)
    if path.exists() and not refresh:
        df = pd.read_csv(path)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df, path
    df = fetch_m1(symbol, start, end)
    df.to_csv(path, index=False, compression="gzip")
    return df, path
