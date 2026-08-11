from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

import research_optimize as base
import research_optimize_v2 as v2


TERMINAL = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
SYMBOL = "UT100"
START = datetime(2022, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 10, tzinfo=timezone.utc)
DATA = base.RESEARCH / "data-mexatlantic"
REPORTS = base.RESEARCH / "reports-cross-broker-mexatlantic"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def server_epoch_to_utc(values: pd.Series) -> pd.Series:
    # MEXAtlantic stores bar labels in its New-York-close server clock:
    # UTC+2 in northern-hemisphere winter and UTC+3 in summer.
    naive = pd.to_datetime(values, unit="s")
    localized = naive.dt.tz_localize("Europe/Helsinki", ambiguous="infer", nonexistent="shift_forward")
    return localized.dt.tz_convert("UTC")


def history() -> tuple[pd.DataFrame, dict]:
    DATA.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize(path=str(TERMINAL), timeout=60_000):
        raise RuntimeError(f"MEXAtlantic terminal initialization failed: {mt5.last_error()}")
    try:
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(f"Cannot select {SYMBOL}: {mt5.last_error()}")
        info = mt5.symbol_info(SYMBOL)
        if info is None:
            raise RuntimeError("Missing UT100 specification")
        files = []
        frames = []
        for year in range(START.year, END.year + 1):
            path = DATA / f"MEXAtlantic-{SYMBOL}-M1-{year}.csv.gz"
            start = max(START, datetime(year, 1, 1, tzinfo=timezone.utc))
            end = min(END, datetime(year + 1, 1, 1, tzinfo=timezone.utc))
            if not path.exists():
                print(f"Downloading MEXAtlantic {SYMBOL} {year}...", flush=True)
                rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, start, end)
                if rates is None or len(rates) == 0:
                    raise RuntimeError(f"No {SYMBOL} M1 rates in {year}: {mt5.last_error()}")
                frame = pd.DataFrame(rates)
                frame["time"] = server_epoch_to_utc(frame["time"])
                frame.to_csv(path, index=False, compression={"method": "gzip", "compresslevel": 6})
            frame = pd.read_csv(path, compression="gzip", parse_dates=["time"])
            frame["time"] = pd.to_datetime(frame["time"], utc=True)
            frames.append(frame)
            files.append({"file": path.name, "rows": len(frame), "sha256": sha256(path)})
        combined = pd.concat(frames, ignore_index=True).drop_duplicates("time", keep="last").sort_values("time")
        positive = combined.loc[combined.spread > 0, "spread"]
        median_spread = float(positive.median()) if len(positive) else 0.0
        manifest = {
            "server": mt5.account_info().server if mt5.account_info() else "unknown",
            "symbol": SYMBOL,
            "digits": int(info.digits),
            "point": float(info.point),
            "tick_size": float(info.trade_tick_size),
            "rows": len(combined),
            "first_utc": combined.time.iloc[0].isoformat(),
            "last_utc": combined.time.iloc[-1].isoformat(),
            "median_spread_points": median_spread,
            "median_spread_index_points": median_spread * float(info.point),
            "timezone_conversion": "Europe/Helsinki broker clock to UTC (UTC+2 winter / UTC+3 summer)",
            "files": files,
        }
        return combined.reset_index(drop=True), manifest
    finally:
        mt5.shutdown()


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    raw, manifest = history()
    sessions, quality = v2.build_sessions(raw, manifest["median_spread_points"])
    signal = v2.Signal(20.0, 0.0, "asia_and_london_aligned", "absolute", "both", 400.0)
    outcome = v2.Outcome("opening_range_breakout", 10 * 60 + 30, 1.25, 20.0, 2.0, "none", 16 * 60)
    trades = v2.make_trades(sessions, signal, outcome)
    metrics = base.scalar_metrics(trades.result_r)
    yearly = {
        str(year): base.scalar_metrics(group.result_r)
        for year, group in trades.groupby(pd.to_datetime(trades.date).dt.year)
    }
    result = {
        "manifest": manifest,
        "quality": quality,
        "locked_signal": signal.__dict__,
        "locked_execution": outcome.__dict__,
        "metrics": metrics,
        "yearly": yearly,
        "note": "No MEXAtlantic parameter optimization was performed.",
    }
    (REPORTS / "results.json").write_text(json.dumps(base.json_safe(result), indent=2), encoding="utf-8")
    trades.to_csv(REPORTS / "trades.csv", index=False)
    lines = [
        "# MEXAtlantic Cross-Broker Validation",
        "",
        "The exact 20-point Exness-selected configuration was replayed unchanged. No MEXAtlantic optimization was performed.",
        "",
        f"- Period: {manifest['first_utc']} through {manifest['last_utc']}",
        f"- M1 bars: {manifest['rows']:,}",
        f"- Median recorded spread: {manifest['median_spread_index_points']:.2f} index points",
        f"- Trades: {metrics['trades']}",
        f"- Return at 1% risk: {metrics['return_pct']:.2f}%",
        f"- PF: {metrics['profit_factor']:.2f}",
        f"- Win rate: {metrics['win_rate_pct']:.2f}%",
        f"- Closed-balance DD: {metrics['max_closed_balance_dd_pct']:.2f}%",
        "",
    ]
    (REPORTS / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(base.json_safe(result), indent=2))
    print(f"Cross-broker report: {REPORTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
