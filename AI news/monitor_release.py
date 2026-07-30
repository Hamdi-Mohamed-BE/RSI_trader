from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

from news_core import ROOT
from predict_news import discover_gold, load_env


def tick_mid(tick: object) -> float:
    return (float(tick["bid"]) + float(tick["ask"])) / 2


def wait_until(moment: datetime) -> None:
    while True:
        remaining = (moment - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(5.0, max(0.1, remaining)))


def monitor(path: Path) -> dict:
    load_env()
    prediction = json.loads(path.read_text(encoding="utf-8"))
    release = datetime.fromisoformat(prediction["release_time_utc"]).astimezone(timezone.utc)
    terminal = (
        prediction.get("mt5_path")
        or os.getenv("MT5_PATH")
        or r"C:\Program Files\MetaTrader 5\terminal64.exe"
    )
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        symbol = prediction.get("symbol") or discover_gold()
        mt5.symbol_select(symbol, True)
        wait_until(release + timedelta(seconds=31))
        ticks = mt5.copy_ticks_range(
            symbol,
            release - timedelta(seconds=5),
            release + timedelta(seconds=30),
            mt5.COPY_TICKS_ALL,
        )
        if ticks is None or len(ticks) < 2:
            raise RuntimeError(f"No release-window ticks available: {mt5.last_error()}")
        before = [tick for tick in ticks if int(tick["time_msc"]) < int(release.timestamp() * 1000)]
        baseline_tick = before[-1] if before else ticks[0]
        baseline = tick_mid(baseline_tick)
        expected = prediction.get("expected_impulse_range_usd", {}).get("median") or 1.0
        baseline_spread = float(baseline_tick["ask"] - baseline_tick["bid"])
        threshold = max(2 * baseline_spread, 0.10 * float(expected), 0.10)

        release_ticks = [
            tick for tick in ticks if int(tick["time_msc"]) >= int(release.timestamp() * 1000)
        ]
        crossing = None
        mids = []
        spreads = []
        for tick in release_ticks:
            mid = tick_mid(tick)
            mids.append(mid)
            spreads.append(float(tick["ask"] - tick["bid"]))
            move = mid - baseline
            if crossing is None and abs(move) >= threshold:
                crossing = {
                    "direction": "UP" if move > 0 else "DOWN",
                    "timestamp_utc": datetime.fromtimestamp(
                        int(tick["time_msc"]) / 1000,
                        timezone.utc,
                    ).isoformat(),
                    "milliseconds_after_release": int(tick["time_msc"]) - int(release.timestamp() * 1000),
                    "move_usd": round(move, 3),
                }

        wait_until(release + timedelta(minutes=15, seconds=2))
        rates = mt5.copy_rates_range(
            symbol,
            mt5.TIMEFRAME_M1,
            release,
            release + timedelta(minutes=16),
        )
        sustained = {}
        if rates is not None:
            for horizon in (1, 5, 15):
                index = min(horizon - 1, len(rates) - 1)
                move = float(rates[index]["close"]) - baseline
                sustained[str(horizon)] = {
                    "direction": "UP" if move >= threshold else "DOWN" if move <= -threshold else "NO CLEAR MOVE",
                    "move_usd": round(move, 3),
                }
        observed = "NO CLEAR MOVE" if crossing is None else crossing["direction"]
        predicted = prediction.get("prediction")
        predicted_observed = "UP" if predicted == "BUY" else "DOWN" if predicted == "SELL" else None
        result = {
            "prediction_file": str(path),
            "release_time_utc": release.isoformat(),
            "symbol": symbol,
            "impulse_threshold_usd": round(threshold, 3),
            "observed_first_impulse": observed,
            "first_impulse": crossing,
            "first_30_seconds": {
                "maximum_up_usd": round(max(mids) - baseline, 3) if mids else None,
                "maximum_down_usd": round(min(mids) - baseline, 3) if mids else None,
                "maximum_spread_usd": round(max(spreads), 3) if spreads else None,
            },
            "sustained": sustained,
            "prediction_result": (
                "UNCLEAR"
                if predicted_observed is None or crossing is None
                else "CORRECT" if predicted_observed == observed else "INCORRECT"
            ),
            "reversal_detected": (
                bool(
                    crossing
                    and sustained.get("15", {}).get("direction") in {"UP", "DOWN"}
                    and sustained["15"]["direction"] != crossing["direction"]
                )
            ),
            "trade_execution": False,
        }
    finally:
        mt5.shutdown()
    output = path.with_suffix(".observed.json")
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["saved_to"] = str(output)
    return result


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Observe and score a saved news prediction.")
    parser.add_argument("prediction", type=Path, help="Path to a saved predictions/*.json file")
    args = parser.parse_args()
    print(json.dumps(monitor(args.prediction.resolve()), indent=2))


if __name__ == "__main__":
    main()
