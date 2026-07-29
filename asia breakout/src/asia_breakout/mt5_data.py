from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import logging
from pathlib import Path
import time

import MetaTrader5 as mt5
import pandas as pd

from .config import AppConfig
from .observability import log_event


LOGGER = logging.getLogger("asia_breakout.mt5")


class MT5Error(RuntimeError):
    pass


@contextmanager
def mt5_connection(config: AppConfig):
    if not mt5.initialize(path=str(config.terminal_path)):
        log_event(
            LOGGER,
            logging.ERROR,
            "mt5_initialize_failed",
            "MT5 initialization failed",
            error=mt5.last_error(),
            terminal_path=str(config.terminal_path),
        )
        raise MT5Error(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        ensure_account(config)
        account = mt5.account_info()
        log_event(
            LOGGER,
            logging.INFO,
            "mt5_connected",
            "Connected to MT5 account",
            server=getattr(account, "server", None),
            currency=getattr(account, "currency", None),
            balance=getattr(account, "balance", None),
            equity=getattr(account, "equity", None),
            trading_enabled=config.enable_trading,
            dry_run=config.dry_run,
        )
        yield
    finally:
        mt5.shutdown()
        log_event(
            LOGGER,
            logging.INFO,
            "mt5_disconnected",
            "MT5 connection closed",
        )


def ensure_account(config: AppConfig) -> None:
    """Keep a batch on one feed even if the visible terminal account changes."""
    if config.login is None:
        return
    account = mt5.account_info()
    if account is not None and int(account.login) == config.login:
        return
    kwargs: dict[str, object] = {}
    if config.password:
        kwargs["password"] = config.password
    if config.server:
        kwargs["server"] = config.server
    if not mt5.login(config.login, **kwargs):
        log_event(
            LOGGER,
            logging.ERROR,
            "mt5_login_failed",
            "Could not switch to the configured MT5 account",
            server=config.server,
            error=mt5.last_error(),
        )
        raise MT5Error(
            f"Cannot lock MT5 to account {config.login}: {mt5.last_error()}"
        )
    log_event(
        LOGGER,
        logging.INFO,
        "mt5_account_selected",
        "Configured MT5 account selected",
        server=config.server,
    )


def discover_symbols(instruments: tuple[str, ...]) -> dict[str, str]:
    """Resolve canonical instruments to exact symbols offered by this broker."""
    from .symbols import symbol_match_score

    available = mt5.symbols_get()
    if available is None:
        raise MT5Error(f"Cannot read broker symbol catalogue: {mt5.last_error()}")
    resolved: dict[str, str] = {}
    for instrument in instruments:
        choices: list[tuple[tuple[int, int, int, int, int, int], str]] = []
        normalized = instrument.upper()
        expected_base = normalized[:-3]
        expected_profit = normalized[-3:]
        for info in available:
            score = symbol_match_score(instrument, info.name)
            if score is None:
                continue
            if int(info.trade_mode) == int(mt5.SYMBOL_TRADE_MODE_DISABLED):
                continue
            tradeable = 1
            pair_match = int(
                str(info.currency_base).upper() == expected_base
                and str(info.currency_profit).upper() == expected_profit
            )
            profit_match = int(
                str(info.currency_profit).upper() == expected_profit
            )
            visible = int(bool(info.visible))
            shortest = -len(info.name)
            choices.append(
                (
                    (
                        tradeable,
                        pair_match,
                        profit_match,
                        score,
                        visible,
                        shortest,
                    ),
                    info.name,
                )
            )
        if not choices:
            raise MT5Error(
                f"No broker symbol matches canonical instrument {instrument}"
            )
        broker_symbol = max(choices, key=lambda item: item[0])[1]
        if not mt5.symbol_select(broker_symbol, True):
            raise MT5Error(
                f"Cannot select discovered symbol {broker_symbol}: {mt5.last_error()}"
            )
        resolved[instrument] = broker_symbol
        log_event(
            LOGGER,
            logging.INFO,
            "symbol_resolved",
            f"{instrument} resolved to {broker_symbol}",
            instrument=instrument,
            broker_symbol=broker_symbol,
        )
    return resolved


def symbol_metadata(symbol: str) -> dict[str, float | int | str]:
    info = None
    for _ in range(3):
        if mt5.symbol_select(symbol, True):
            info = mt5.symbol_info(symbol)
            if info is not None:
                break
        time.sleep(1)
    if info is None:
        raise MT5Error(f"Cannot select/read {symbol}: {mt5.last_error()}")
    return {
        "symbol": symbol,
        "digits": int(info.digits),
        "point": float(info.point),
        "volume_min": float(info.volume_min),
        "volume_max": float(info.volume_max),
        "volume_step": float(info.volume_step),
        "trade_stops_level": int(info.trade_stops_level),
    }


def fetch_m1(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must be timezone-aware UTC datetimes")
    rates = None
    for _ in range(3):
        if mt5.symbol_select(symbol, True):
            rates = mt5.copy_rates_range(
                symbol,
                mt5.TIMEFRAME_M1,
                start.astimezone(timezone.utc),
                end.astimezone(timezone.utc),
            )
            if rates is not None and len(rates):
                break
        time.sleep(1)
    if rates is None or len(rates) == 0:
        raise MT5Error(f"No M1 data for {symbol}: {mt5.last_error()}")
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    return frame


def cache_path(cache_dir: Path, symbol: str, start: datetime, end: datetime) -> Path:
    safe = symbol.replace(".", "_")
    return cache_dir / f"{safe}_{start:%Y%m%d}_{end:%Y%m%d}_M1.csv.gz"


def load_or_fetch_m1(
    symbol: str,
    start: datetime,
    end: datetime,
    cache_dir: Path,
    refresh: bool = False,
) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache_dir, symbol, start, end)
    if path.exists() and not refresh:
        log_event(
            LOGGER,
            logging.DEBUG,
            "market_data_cache_hit",
            f"Loaded cached M1 data for {symbol}",
            symbol=symbol,
            path=str(path),
        )
        frame = pd.read_csv(path)
        frame["time"] = pd.to_datetime(frame["time"], utc=True)
        return frame
    frame = fetch_m1(symbol, start, end)
    log_event(
        LOGGER,
        logging.INFO,
        "market_data_downloaded",
        f"Downloaded {len(frame)} M1 bars for {symbol}",
        symbol=symbol,
        bars=len(frame),
        start=start,
        end=end,
    )
    frame.to_csv(path, index=False, compression="gzip")
    return frame


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
