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
SYMBOLS = {
    "EURUSD": "EURUSD..",
    "US100": "UT100",
    "US30": "US30",
    "XAU": "XAUUSD..",
}
STARTS = {
    "EURUSD": 2019,
    "US100": 2022,
    "US30": 2022,
    "XAU": 2019,
}
END = datetime(2026, 8, 10, tzinfo=timezone.utc)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def server_epoch_to_utc(values: pd.Series) -> pd.Series:
    naive = pd.to_datetime(values, unit="s")
    local = naive.dt.tz_localize("Europe/Helsinki", ambiguous="infer", nonexistent="shift_forward")
    return local.dt.tz_convert("UTC")


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize(path=str(TERMINAL), timeout=60_000):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None or account.server != "MEXAtlantic-Demo":
            raise RuntimeError(f"Expected MEXAtlantic-Demo, received {account}")
        manifest: dict[str, object] = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "server": account.server,
            "timezone_conversion": "Europe/Helsinki broker clock to UTC (UTC+2 winter / UTC+3 summer)",
            "instruments": {},
        }
        for label, symbol in SYMBOLS.items():
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Cannot select {symbol}: {mt5.last_error()}")
            info = mt5.symbol_info(symbol)
            if info is None:
                raise RuntimeError(f"No specification for {symbol}")
            files: list[dict[str, object]] = []
            rows = 0
            first = None
            last = None
            spread_values: list[pd.Series] = []
            tick_volume_sum = 0
            real_volume_sum = 0
            for year in range(STARTS[label], END.year + 1):
                destination = DATA / f"MEXAtlantic-{label}-{symbol}-M1-{year}.csv.gz"
                if not destination.exists():
                    print(f"Downloading {label} / {symbol} M1 {year}...", flush=True)
                    start = datetime(year, 1, 1, tzinfo=timezone.utc)
                    stop = min(END, datetime(year + 1, 1, 1, tzinfo=timezone.utc))
                    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, stop)
                    if rates is None or len(rates) == 0:
                        raise RuntimeError(f"No {symbol} rates for {year}: {mt5.last_error()}")
                    frame = pd.DataFrame(rates)
                    frame["time"] = server_epoch_to_utc(frame["time"])
                    frame.to_csv(destination, index=False, compression={"method": "gzip", "compresslevel": 6})
                frame = pd.read_csv(destination, compression="gzip", parse_dates=["time"])
                frame["time"] = pd.to_datetime(frame["time"], utc=True)
                rows += len(frame)
                tick_volume_sum += int(frame["tick_volume"].sum())
                real_volume_sum += int(frame["real_volume"].sum())
                positive = frame.loc[frame["spread"] > 0, "spread"]
                if len(positive):
                    spread_values.append(positive)
                year_first = frame["time"].min()
                year_last = frame["time"].max()
                first = year_first if first is None else min(first, year_first)
                last = year_last if last is None else max(last, year_last)
                files.append({"file": destination.name, "rows": len(frame), "sha256": sha256(destination)})
                print(f"  {destination.name}: {len(frame):,} rows", flush=True)
            spreads = pd.concat(spread_values, ignore_index=True) if spread_values else pd.Series(dtype=float)
            manifest["instruments"][label] = {
                "symbol": symbol,
                "digits": int(info.digits),
                "point": float(info.point),
                "tick_size": float(info.trade_tick_size),
                "tick_value": float(info.trade_tick_value),
                "contract_size": float(info.trade_contract_size),
                "minimum_volume": float(info.volume_min),
                "volume_step": float(info.volume_step),
                "rows": rows,
                "first_utc": first.isoformat() if first is not None else None,
                "last_utc": last.isoformat() if last is not None else None,
                "median_positive_spread_points": float(spreads.median()) if len(spreads) else 0.0,
                "median_spread_price": float(spreads.median() * info.point) if len(spreads) else 0.0,
                "tick_volume_sum": tick_volume_sum,
                "real_volume_sum": real_volume_sum,
                "volume_note": "Broker quote-tick activity; real exchange volume is unavailable" if real_volume_sum == 0 else "Real volume present",
                "files": files,
            }
        (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2), flush=True)
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
