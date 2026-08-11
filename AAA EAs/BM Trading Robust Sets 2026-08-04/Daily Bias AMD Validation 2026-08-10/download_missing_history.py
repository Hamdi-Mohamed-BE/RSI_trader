from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
TERMINAL = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
SYMBOLS = {"BTC": "BTCUSD", "GBPJPY": "GBPJPY.."}
START_YEAR = 2022
END = datetime(2026, 8, 10, tzinfo=timezone.utc)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def server_epoch_to_utc(values: pd.Series) -> pd.Series:
    naive = pd.to_datetime(values, unit="s")
    try:
        local = naive.dt.tz_localize("Europe/Helsinki", ambiguous="infer", nonexistent="shift_forward")
    except ValueError:
        # Some continuously traded BTC years contain only one copy of the
        # autumn clock-change hour, so pandas cannot infer its DST side.
        local = naive.dt.tz_localize("Europe/Helsinki", ambiguous=True, nonexistent="shift_forward")
    return local.dt.tz_convert("UTC")


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize(path=str(TERMINAL), timeout=60_000):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None or account.server != "MEXAtlantic-Demo":
            raise RuntimeError(f"Expected MEXAtlantic-Demo, received {account}")
        output: dict[str, object] = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "server": account.server,
            "timezone_conversion": "Europe/Helsinki broker clock to UTC",
            "instruments": {},
        }
        for label, symbol in SYMBOLS.items():
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Cannot select {symbol}: {mt5.last_error()}")
            info = mt5.symbol_info(symbol)
            if info is None:
                raise RuntimeError(f"No symbol specification for {symbol}")
            files = []
            spreads = []
            first = None
            last = None
            total_rows = 0
            for year in range(START_YEAR, END.year + 1):
                path = DATA / f"MEXAtlantic-{label}-{symbol}-M1-{year}.csv.gz"
                if not path.exists():
                    start = datetime(year, 1, 1, tzinfo=timezone.utc)
                    stop = min(END, datetime(year + 1, 1, 1, tzinfo=timezone.utc))
                    print(f"Downloading {label} {symbol} M1 {year}...", flush=True)
                    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, stop)
                    if rates is None or len(rates) == 0:
                        raise RuntimeError(f"No {symbol} M1 rates for {year}: {mt5.last_error()}")
                    frame = pd.DataFrame(rates)
                    frame["time"] = server_epoch_to_utc(frame["time"])
                    frame.to_csv(path, index=False, compression={"method": "gzip", "compresslevel": 6})
                frame = pd.read_csv(path, compression="gzip", parse_dates=["time"])
                frame["time"] = pd.to_datetime(frame["time"], utc=True)
                total_rows += len(frame)
                positive = frame.loc[frame.spread > 0, "spread"]
                if len(positive):
                    spreads.append(positive)
                year_first, year_last = frame.time.min(), frame.time.max()
                first = year_first if first is None else min(first, year_first)
                last = year_last if last is None else max(last, year_last)
                files.append({"file": path.name, "rows": len(frame), "sha256": digest(path)})
                print(f"  {path.name}: {len(frame):,} rows", flush=True)
            spread = pd.concat(spreads, ignore_index=True) if spreads else pd.Series(dtype=float)
            output["instruments"][label] = {
                "symbol": symbol,
                "digits": int(info.digits),
                "point": float(info.point),
                "tick_size": float(info.trade_tick_size),
                "tick_value": float(info.trade_tick_value),
                "contract_size": float(info.trade_contract_size),
                "minimum_volume": float(info.volume_min),
                "volume_step": float(info.volume_step),
                "rows": total_rows,
                "first_utc": first.isoformat(),
                "last_utc": last.isoformat(),
                "median_positive_spread_points": float(spread.median()),
                "median_spread_price": float(spread.median() * info.point),
                "files": files,
            }
        (DATA / "manifest.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(json.dumps(output, indent=2), flush=True)
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
