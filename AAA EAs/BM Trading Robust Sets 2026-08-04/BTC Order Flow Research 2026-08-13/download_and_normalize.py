from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
BASE = "https://data.binance.vision/data/futures/um/daily"


def dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def get_bytes(url: str, attempts: int = 5) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.content
        except Exception as exc:  # network retry boundary
            last_error = exc
            time.sleep(min(8, 2**attempt))
    raise RuntimeError(f"Download failed after {attempts} attempts: {url}: {last_error}")


def read_zip_csv(content: bytes, expected_fragment: str) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"Corrupt member {bad}")
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(names) != 1 or expected_fragment not in names[0]:
            raise RuntimeError(f"Unexpected ZIP members: {names}")
        with archive.open(names[0]) as handle:
            return pd.read_csv(handle)


def parse_open_time(values: pd.Series) -> pd.Series:
    sample = float(values.iloc[0])
    unit = "us" if sample > 1e14 else "ms"
    return pd.to_datetime(values, unit=unit, utc=True)


def normalize_day(day: date) -> tuple[str, pd.DataFrame, dict]:
    stamp = day.isoformat()
    depth_name = f"BTCUSDT-bookDepth-{stamp}"
    kline_name = f"BTCUSDT-1m-{stamp}"
    depth_url = f"{BASE}/bookDepth/BTCUSDT/{depth_name}.zip"
    kline_url = f"{BASE}/klines/BTCUSDT/1m/{kline_name}.zip"
    depth_bytes = get_bytes(depth_url)
    kline_bytes = get_bytes(kline_url)
    depth = read_zip_csv(depth_bytes, depth_name)
    bars = read_zip_csv(kline_bytes, kline_name)

    depth["timestamp"] = pd.to_datetime(depth["timestamp"], utc=True)
    depth["minute"] = depth["timestamp"].dt.floor("min")
    depth["percentage"] = pd.to_numeric(depth["percentage"], errors="raise").round(2)
    depth["depth"] = pd.to_numeric(depth["depth"], errors="raise")
    pivot = depth.pivot_table(index=["minute", "timestamp"], columns="percentage", values="depth", aggfunc="last")
    # ±1% and ±5% exist across the entire requested archive. Binance added the
    # ±0.2% bands later, so they are deliberately excluded from strategy
    # features to avoid a mid-sample schema/regime leak.
    required = [-5.0, -1.0, 1.0, 5.0]
    missing = [value for value in required if value not in pivot.columns]
    if missing:
        raise RuntimeError(f"{stamp}: missing depth bands {missing}")

    snapshots = pd.DataFrame(index=pivot.index)
    snapshots["bid_1"] = pivot[-1.0]
    snapshots["ask_1"] = pivot[1.0]
    snapshots["bid_5"] = pivot[-5.0]
    snapshots["ask_5"] = pivot[5.0]
    snapshots = snapshots.reset_index()
    denominator = lambda bid, ask: (bid + ask).replace(0, np.nan)
    for suffix in ("1", "5"):
        bid = snapshots[f"bid_{suffix}"]
        ask = snapshots[f"ask_{suffix}"]
        snapshots[f"imb_{suffix}"] = (bid - ask) / denominator(bid, ask)

    grouped = snapshots.groupby("minute", sort=True)
    minute = grouped[[
        "bid_1", "ask_1", "bid_5", "ask_5", "imb_1", "imb_5",
    ]].mean()
    first = grouped[["bid_1", "ask_1"]].first()
    last = grouped[["bid_1", "ask_1"]].last()
    minute["bid_replenishment"] = last["bid_1"] / first["bid_1"].replace(0, np.nan) - 1.0
    minute["ask_replenishment"] = last["ask_1"] / first["ask_1"].replace(0, np.nan) - 1.0
    minute["replenishment_edge"] = minute["bid_replenishment"] - minute["ask_replenishment"]
    minute["depth_snapshots"] = grouped.size()
    minute = minute.reset_index().rename(columns={"minute": "time"})

    bars["time"] = parse_open_time(bars["open_time"])
    numeric = [
        "open", "high", "low", "close", "volume", "quote_volume", "count",
        "taker_buy_volume", "taker_buy_quote_volume",
    ]
    for column in numeric:
        bars[column] = pd.to_numeric(bars[column], errors="raise")
    bars["signed_volume"] = 2.0 * bars["taker_buy_volume"] - bars["volume"]
    bars["delta_ratio"] = bars["signed_volume"] / bars["volume"].replace(0, np.nan)
    bars["taker_buy_ratio"] = bars["taker_buy_volume"] / bars["volume"].replace(0, np.nan)
    keep = [
        "time", "open", "high", "low", "close", "volume", "quote_volume", "count",
        "taker_buy_volume", "taker_buy_quote_volume", "signed_volume", "delta_ratio",
        "taker_buy_ratio",
    ]
    result = bars[keep].merge(minute, on="time", how="inner", validate="one_to_one")
    result["source_day"] = stamp
    result = result.replace([np.inf, -np.inf], np.nan).dropna().sort_values("time")
    metadata = {
        "day": stamp,
        "rows": int(len(result)),
        "depth_snapshots": int(len(snapshots)),
        "depth_zip_bytes": len(depth_bytes),
        "kline_zip_bytes": len(kline_bytes),
        "depth_sha256": hashlib.sha256(depth_bytes).hexdigest(),
        "kline_sha256": hashlib.sha256(kline_bytes).hexdigest(),
    }
    return stamp, result, metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2025-08-11")
    parser.add_argument("--end", default="2026-08-10")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if end < start:
        raise SystemExit("end must be on or after start")
    DATA.mkdir(parents=True, exist_ok=True)
    requested = list(dates(start, end))
    frames: dict[str, pd.DataFrame] = {}
    metadata: dict[str, dict] = {}
    failures: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(normalize_day, day): day for day in requested}
        completed = 0
        for future in as_completed(futures):
            day = futures[future]
            try:
                stamp, frame, details = future.result()
                frames[stamp] = frame
                metadata[stamp] = details
            except Exception as exc:
                failures[day.isoformat()] = str(exc)
            completed += 1
            if completed % 20 == 0 or completed == len(requested):
                print(f"processed {completed}/{len(requested)}; failures={len(failures)}", flush=True)

    if not frames:
        raise SystemExit(f"No data normalized. Failures: {failures}")
    combined = pd.concat([frames[key] for key in sorted(frames)], ignore_index=True).sort_values("time")
    if combined["time"].duplicated().any():
        raise SystemExit("Duplicate normalized timestamps detected")
    output = DATA / f"btcusdt-orderflow-{args.start}_{args.end}.parquet"
    connection = duckdb.connect()
    connection.register("normalized", combined)
    connection.execute(
        f"COPY normalized TO '{output.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    connection.close()
    summary = {
        "market": "Binance USD-M BTCUSDT perpetual",
        "start": args.start,
        "end": args.end,
        "requested_days": len(requested),
        "successful_days": len(frames),
        "failed_days": failures,
        "rows": int(len(combined)),
        "first_time": combined["time"].min().isoformat(),
        "last_time": combined["time"].max().isoformat(),
        "output": str(output),
        "daily_integrity": metadata,
    }
    (DATA / "dataset-metadata.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "daily_integrity"}, indent=2))


if __name__ == "__main__":
    main()
