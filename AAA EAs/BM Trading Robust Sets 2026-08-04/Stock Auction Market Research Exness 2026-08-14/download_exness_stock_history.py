from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
TERMINAL = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
SERVER = "Exness-MT5Trial16"
LOGIN = 472334559
START_YEAR = 2022
END = datetime(2026, 8, 14, 23, 59, tzinfo=timezone.utc)
CANDIDATES = {
    "SP500": ("US500", "SPX500", "SP500", "S&P500"),
    "NVDA": ("NVDA", "NVIDIA"),
    "AAPL": ("AAPL", "APPLE"),
    "MSFT": ("MSFT", "MICROSOFT"),
    "AMZN": ("AMZN", "AMAZON"),
    "GOOGL": ("GOOGL", "GOOG", "ALPHABET"),
    "META": ("META", "FACEBOOK"),
    "AVGO": ("AVGO", "BROADCOM"),
    "AMD": ("AMD",),
    "INTC": ("INTC", "INTEL"),
    "TSLA": ("TSLA", "TESLA"),
    "JPM": ("JPM", "JPMORGAN"),
}


def normalize(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def resolve_symbol(catalog, aliases: tuple[str, ...]):
    best = None
    best_score = 10**12
    for item in catalog:
        if int(item.trade_mode) == mt5.SYMBOL_TRADE_MODE_DISABLED:
            continue
        normalized = normalize(item.name)
        for alias_index, original_alias in enumerate(aliases):
            alias = normalize(original_alias)
            if normalized == alias:
                match = 0
            elif normalized.startswith(alias) or normalized.endswith(alias):
                match = 100
            elif alias in normalized:
                match = 200
            else:
                continue
            path_text = item.path.lower()
            asset_penalty = 0 if ("stock" in path_text or "indice" in path_text or "idx" in path_text) else 100
            amplified_penalty = 50_000 if "_x" in item.name.lower() else 0
            futures_penalty = 100_000 if "future" in path_text else 0
            score = (
                match * 1_000 + alias_index * 10 + len(normalized) - len(alias)
                + asset_penalty + amplified_penalty + futures_penalty
            )
            if score < best_score:
                best, best_score = item, score
    return best


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def safe_symbol(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def commission_terms(label: str) -> dict:
    if label == "SP500":
        return {
            "commission_usd_per_lot_per_side": 0.50,
            "commission_source": "Exness US500 Zero-account published specification",
            "commission_confidence": "published exact value",
        }
    return {
        "commission_usd_per_lot_per_side": 0.50,
        "commission_source": "Exness stock Zero-account published minimum",
        "commission_confidence": "lower-bound estimate; instrument-specific PA table unavailable",
    }


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize(path=str(TERMINAL), timeout=60_000):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        # Use the password already stored by the user's terminal; do not persist credentials in research files.
        if not mt5.login(LOGIN, server=SERVER, timeout=60_000):
            raise RuntimeError(f"Exness saved-credential login failed: {mt5.last_error()}")
        account = mt5.account_info()
        if account is None or account.server != SERVER:
            raise RuntimeError(f"Expected {SERVER}, received {account}")
        catalog = mt5.symbols_get()
        if catalog is None:
            raise RuntimeError(f"Could not read broker symbols: {mt5.last_error()}")

        manifest: dict[str, object] = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "server": account.server,
            "account_group": "Zero (inferred from broker symbol paths)",
            "terminal": str(TERMINAL),
            "timezone": "MetaTrader5 Python epoch interpreted as UTC",
            "missing_symbols_do_not_abort": True,
            "commission_warning": (
                "US500 commission is published exact. Stock commission uses Exness's published $0.50/lot/side "
                "minimum because the instrument-specific Personal Area contract table was unavailable."
            ),
            "instruments": {},
        }
        for label, aliases in CANDIDATES.items():
            catalog_item = resolve_symbol(catalog, aliases)
            if catalog_item is None:
                manifest["instruments"][label] = {
                    "status": "MISSING", "aliases": list(aliases),
                    "message": "No enabled Exness symbol matched; skipped without aborting.",
                }
                print(f"MISSING {label}: {', '.join(aliases)}", flush=True)
                continue
            symbol = catalog_item.name
            if not mt5.symbol_select(symbol, True):
                manifest["instruments"][label] = {
                    "status": "UNAVAILABLE", "symbol": symbol, "aliases": list(aliases),
                    "message": f"Symbol exists but could not be selected: {mt5.last_error()}",
                }
                print(f"UNAVAILABLE {label}: {symbol}", flush=True)
                continue
            info = mt5.symbol_info(symbol)
            if info is None:
                manifest["instruments"][label] = {
                    "status": "UNAVAILABLE", "symbol": symbol, "aliases": list(aliases),
                    "message": "Symbol specification unavailable.",
                }
                continue

            files: list[dict[str, object]] = []
            spreads: list[pd.Series] = []
            missing_years: list[int] = []
            total_rows = 0
            tick_volume_sum = 0
            real_volume_sum = 0
            first = None
            last = None
            for year in range(START_YEAR, END.year + 1):
                destination = DATA / f"Exness-{label}-{safe_symbol(symbol)}-M1-{year}.csv.gz"
                if not destination.exists():
                    start = datetime(year, 1, 1, tzinfo=timezone.utc)
                    stop = min(END, datetime(year + 1, 1, 1, tzinfo=timezone.utc))
                    print(f"Downloading {label} / {symbol} M1 {year}...", flush=True)
                    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, stop)
                    if rates is None or len(rates) == 0:
                        missing_years.append(year)
                        print(f"  no rates: {mt5.last_error()}", flush=True)
                        continue
                    frame = pd.DataFrame(rates)
                    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
                    frame.to_csv(destination, index=False, compression={"method": "gzip", "compresslevel": 6})

                frame = pd.read_csv(destination, compression="gzip", parse_dates=["time"])
                frame["time"] = pd.to_datetime(frame["time"], utc=True)
                total_rows += len(frame)
                tick_volume_sum += int(frame["tick_volume"].sum())
                real_volume_sum += int(frame["real_volume"].sum())
                positive = frame.loc[frame["spread"] > 0, "spread"]
                if len(positive):
                    spreads.append(positive)
                year_first, year_last = frame.time.min(), frame.time.max()
                first = year_first if first is None else min(first, year_first)
                last = year_last if last is None else max(last, year_last)
                files.append({"file": destination.name, "rows": len(frame), "sha256": digest(destination)})
                print(f"  {destination.name}: {len(frame):,} rows", flush=True)

            spread_values = pd.concat(spreads, ignore_index=True) if spreads else pd.Series(dtype=float)
            # A symbol is usable even if the broker did not retain every requested year. The
            # downstream stage enforces the minimum period needed for development/validation.
            complete = len(files) > 0
            manifest["instruments"][label] = {
                "status": "READY" if complete else "INCOMPLETE",
                "symbol": symbol, "path": info.path, "aliases": list(aliases),
                "digits": int(info.digits), "point": float(info.point),
                "tick_size": float(info.trade_tick_size or info.point),
                "tick_value": float(info.trade_tick_value),
                "contract_size": float(info.trade_contract_size),
                "minimum_volume": float(info.volume_min), "volume_step": float(info.volume_step),
                "swap_mode": int(info.swap_mode), "swap_long": float(info.swap_long),
                "swap_short": float(info.swap_short),
                "swap_rollover_three_day": int(info.swap_rollover3days),
                **commission_terms(label),
                "rows": total_rows, "first_utc": first.isoformat() if first is not None else None,
                "last_utc": last.isoformat() if last is not None else None,
                "median_positive_spread_points": float(spread_values.median()) if len(spread_values) else 0.0,
                "median_spread_price": (
                    float(spread_values.median()) * float(info.point) if len(spread_values) else 0.0
                ),
                "tick_volume_sum": tick_volume_sum, "real_volume_sum": real_volume_sum,
                "missing_years": missing_years, "files": files,
            }
        (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        ready = [key for key, value in manifest["instruments"].items() if value.get("status") == "READY"]
        skipped = [key for key, value in manifest["instruments"].items() if value.get("status") != "READY"]
        print(json.dumps({"ready": ready, "skipped": skipped}, indent=2), flush=True)
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
