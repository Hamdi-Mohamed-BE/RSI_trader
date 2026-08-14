from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
RESULTS = ROOT / "Results"
BASE_PATH = ROOT.parent / "Global Macro Auction Market Research 2026-08-14" / "backtest_auction_market.py"
SPEC = importlib.util.spec_from_file_location("stock_auction_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load base auction-market research: {BASE_PATH}")
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)


# MEXAtlantic supplies these histories on the raw price scale that existed on each date.
# Convert the pre-split OHLC and spread to today's share basis so a corporate action is
# not mistaken for a tradable crash. Dates are the first split-adjusted trading sessions.
SPLIT_ADJUSTMENTS = {
    "AMZN": [("2022-06-06", 20.0)],
    "GOOGL": [("2022-07-18", 20.0)],
    "TSLA": [("2022-08-25", 3.0)],
    "NVDA": [("2024-06-10", 10.0)],
    "AVGO": [("2024-07-15", 10.0)],
}


def read_manifest() -> dict:
    return json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))


def ready_map() -> dict:
    manifest = read_manifest()
    output = {}
    for label, details in manifest["instruments"].items():
        if details.get("status") != "READY":
            continue
        output[label] = (DATA, label, f"MEXAtlantic-{label}-*-M1-*.csv.gz")
    return output


def load_stock(label: str):
    manifest = read_manifest()
    details = manifest["instruments"][label]
    files = sorted(DATA.glob(f"MEXAtlantic-{label}-*-M1-*.csv.gz"))
    if not files:
        raise FileNotFoundError(f"No M1 files for {label}")
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


def write_outputs(outputs: dict[str, dict]) -> None:
    """Write every stock result; the original six-panel writer truncates larger universes."""
    rows = []
    columns = 3
    row_count = max(1, math.ceil(len(outputs) / columns))
    figure, axes = BASE.plt.subplots(row_count, columns, figsize=(18, 4.8 * row_count), constrained_layout=True)
    flat_axes = BASE.np.asarray(axes).reshape(-1)
    for axis in flat_axes:
        axis.set_visible(False)
    for axis, (label, output) in zip(flat_axes, outputs.items()):
        axis.set_visible(True)
        result = output["result"]
        trades = output["trades"]
        pattern = result["selected_pattern"]
        execution = result["selected_execution"]
        full = result["full_2022_2026"]
        confirm = result["confirmation_2026"]
        rows.append({
            "status": result["final_status"], "research_status": result["research_status"],
            "instrument": label, "symbol": result["broker_symbol"],
            "timeframe": "H4" if pattern["timeframe_minutes"] == 240 else "D1",
            **pattern, **execution, "full_trades": full["trades"],
            "full_win_rate_pct": full["win_rate_pct"], "full_pf": full["profit_factor"],
            "full_return_pct": full["return_pct"], "full_cagr_pct": result["full_cagr_pct"],
            "full_max_dd_pct": full["max_drawdown_pct"], "confirm_trades": confirm["trades"],
            "confirm_win_rate_pct": confirm["win_rate_pct"], "confirm_pf": confirm["profit_factor"],
            "confirm_return_pct": confirm["return_pct"], "confirm_max_dd_pct": confirm["max_drawdown_pct"],
        })
        if trades.empty:
            axis.text(0.5, 0.5, "No trades", ha="center", va="center")
            axis.set_title(label)
            continue
        time = pd.to_datetime(trades.entry_time_utc, utc=True)
        equity = BASE.STARTING_BALANCE * BASE.np.cumprod(
            1.0 + BASE.RISK_FRACTION * trades.r_multiple.to_numpy(float)
        )
        title = (
            f"{label} - {result['final_status']} | Full {full['return_pct']:+.1f}% "
            f"PF {full['profit_factor']:.2f} | 2026 {confirm['return_pct']:+.1f}%"
        )
        axis.step(time, equity, where="post", linewidth=1.2)
        axis.axhline(BASE.STARTING_BALANCE, color="gray", linestyle="--", linewidth=0.8)
        axis.axvline(pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--", linewidth=1.0)
        axis.set_title(title)
        axis.set_ylabel("Closed equity ($)")
        axis.grid(alpha=0.25)
        individual, individual_axis = BASE.plt.subplots(figsize=(12, 6), constrained_layout=True)
        individual_axis.step(time, equity, where="post")
        individual_axis.axhline(BASE.STARTING_BALANCE, color="gray", linestyle="--")
        individual_axis.axvline(
            pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--",
            label="Locked 2026 confirmation",
        )
        individual_axis.set_title(title)
        individual_axis.set_xlabel("Date (UTC)")
        individual_axis.set_ylabel("Closed equity ($)")
        individual_axis.grid(alpha=0.25)
        individual_axis.legend()
        individual.savefig(RESULTS / f"{label}-equity.png", dpi=170)
        BASE.plt.close(individual)
    figure.suptitle(
        "US stock/index auction-market models - 1% risk, recorded CFD spreads + slippage",
        fontsize=16,
    )
    figure.savefig(RESULTS / "all-markets-equity.png", dpi=180)
    BASE.plt.close(figure)
    pd.DataFrame(rows).to_csv(RESULTS / "summary.csv", index=False)
    (RESULTS / "all-results.json").write_text(
        json.dumps({label: output["result"] for label, output in outputs.items()}, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", nargs="*")
    parser.add_argument("--combine-existing", action="store_true")
    args = parser.parse_args()
    source_map = ready_map()
    if not source_map:
        raise RuntimeError("No broker symbols have complete 2022-2026 history")
    BASE.ROOT = ROOT
    BASE.RESULTS = RESULTS
    BASE.SOURCE_MAP = source_map
    BASE.load_asset = load_stock
    BASE.INDEX_LONG_ONLY = set(source_map)  # The video's equity rule is long only.
    RESULTS.mkdir(parents=True, exist_ok=True)

    assets = args.assets or list(source_map)
    unknown = [asset for asset in assets if asset not in source_map]
    if unknown:
        raise SystemExit(f"Unavailable or incomplete broker history: {', '.join(unknown)}")
    if args.combine_existing:
        outputs = {}
        for label in source_map:
            result = json.loads((RESULTS / f"{label}-selected-result.json").read_text(encoding="utf-8"))
            result["asset_class"] = "US equity/index CFD"
            result["direction_rule"] = "long only, as specified by the video for US equities"
            trades = pd.read_csv(
                RESULTS / f"{label}-selected-trades.csv", parse_dates=["entry_time_utc", "exit_time_utc"]
            )
            outputs[label] = {"result": result, "trades": trades}
    else:
        outputs = {}
        for label in assets:
            output = BASE.analyze_asset(label)
            output["result"]["asset_class"] = "US equity/index CFD"
            output["result"]["direction_rule"] = "long only, as specified by the video for US equities"
            result_path = RESULTS / f"{label}-selected-result.json"
            result_path.write_text(json.dumps(output["result"], indent=2), encoding="utf-8")
            outputs[label] = output
    write_outputs(outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
