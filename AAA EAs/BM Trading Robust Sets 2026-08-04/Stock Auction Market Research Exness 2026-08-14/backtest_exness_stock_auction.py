from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
RESULTS = ROOT / "Results Spread Slippage"
SHARED_PATH = ROOT.parent / "Stock Auction Market Research 2026-08-14" / "backtest_stock_auction.py"
SPEC = importlib.util.spec_from_file_location("shared_stock_auction", SHARED_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load shared stock research engine: {SHARED_PATH}")
SHARED = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SHARED
SPEC.loader.exec_module(SHARED)
BASE = SHARED.BASE


# Filled only when the Exness raw feed shows a mechanical split discontinuity.
SPLIT_ADJUSTMENTS: dict[str, list[tuple[str, float]]] = {}


def read_manifest() -> dict:
    return json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))


def ready_map() -> dict:
    manifest = read_manifest()
    output = {}
    for label, details in manifest["instruments"].items():
        if details.get("status") != "READY":
            continue
        output[label] = (DATA, label, f"Exness-{label}-*-M1-*.csv.gz")
    return output


def load_stock(label: str):
    manifest = read_manifest()
    details = manifest["instruments"][label]
    files = sorted(DATA.glob(f"Exness-{label}-*-M1-*.csv.gz"))
    if not files:
        raise FileNotFoundError(f"No Exness M1 files for {label}")
    columns = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
    frames = [pd.read_csv(path, compression="gzip", usecols=columns, parse_dates=["time"]) for path in files]
    frame = pd.concat(frames, ignore_index=True)
    frame["time"] = pd.to_datetime(frame.time, utc=True)
    frame = frame.loc[(frame.time >= "2022-01-01") & (frame.time < "2027-01-01")]
    frame = frame.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    frame["spread"] = frame["spread"].astype(float)
    for split_date, factor in SPLIT_ADJUSTMENTS.get(label, []):
        pre_split = frame.time < pd.Timestamp(split_date, tz="UTC")
        frame.loc[pre_split, ["open", "high", "low", "close", "spread"]] /= factor
    details = dict(details)
    details["split_adjustments"] = [
        {"first_adjusted_trading_date": split_date, "forward_split_factor": factor}
        for split_date, factor in SPLIT_ADJUSTMENTS.get(label, [])
    ]
    return frame, details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", nargs="*")
    parser.add_argument("--combine-existing", action="store_true")
    args = parser.parse_args()
    source_map = ready_map()
    if not source_map:
        raise RuntimeError("No Exness broker symbols have usable history")

    BASE.ROOT = ROOT
    BASE.RESULTS = RESULTS
    BASE.SOURCE_MAP = source_map
    BASE.load_asset = load_stock
    BASE.INDEX_LONG_ONLY = set(source_map)
    SHARED.RESULTS = RESULTS
    RESULTS.mkdir(parents=True, exist_ok=True)

    assets = args.assets or list(source_map)
    unknown = [asset for asset in assets if asset not in source_map]
    if unknown:
        raise SystemExit(f"Unavailable Exness history: {', '.join(unknown)}")
    if args.combine_existing:
        outputs = {}
        for label in source_map:
            result = json.loads((RESULTS / f"{label}-selected-result.json").read_text(encoding="utf-8"))
            result["asset_class"] = "US equity/index CFD"
            result["broker"] = "Exness-MT5Trial16 Zero demo"
            result["direction_rule"] = "long only"
            trades = pd.read_csv(
                RESULTS / f"{label}-selected-trades.csv",
                parse_dates=["entry_time_utc", "exit_time_utc"],
            )
            outputs[label] = {"result": result, "trades": trades}
    else:
        outputs = {}
        for label in assets:
            output = BASE.analyze_asset(label)
            output["result"]["asset_class"] = "US equity/index CFD"
            output["result"]["broker"] = "Exness-MT5Trial16 Zero demo"
            output["result"]["data"]["server"] = "Exness-MT5Trial16"
            output["result"]["direction_rule"] = "long only"
            (RESULTS / f"{label}-selected-result.json").write_text(
                json.dumps(output["result"], indent=2), encoding="utf-8"
            )
            outputs[label] = output
    SHARED.write_outputs(outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
