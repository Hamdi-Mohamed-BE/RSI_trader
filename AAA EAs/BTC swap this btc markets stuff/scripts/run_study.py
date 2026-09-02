from __future__ import annotations

import itertools
import json
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from btc_basis.analysis import choose_locked_config, evaluate_grid, monte_carlo
from btc_basis.data import load_or_download
from btc_basis.strategy import StrategyConfig, backtest, detect_reopen_events, performance_metrics


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data"
RESULTS = ROOT / "Results"
DEV_START = pd.Timestamp("2024-09-03", tz="UTC")
LOCK_DATE = pd.Timestamp("2025-11-01", tz="UTC")
LEGACY_END = pd.Timestamp("2026-05-29", tz="UTC")


def parameter_grid() -> list[dict]:
    keys = [
        "lookback_hours",
        "minimum_spot_move",
        "entry_z",
        "exit_z",
        "stop_z_extension",
        "maximum_hold_hours",
    ]
    values = [
        [168, 336, 720],
        [0.005, 0.01, 0.015],
        [0.5, 1.0, 1.5],
        [0.0, 0.25],
        [1.0, 1.5],
        [6, 12, 24, 48],
    ]
    return [dict(zip(keys, combination)) for combination in itertools.product(*values)]


def export_trades(trades: pd.DataFrame, path: Path) -> None:
    output = trades.copy()
    for column in ["entry_time", "exit_time", "previous_time"]:
        if column in output:
            output[column] = pd.to_datetime(output[column], utc=True).astype(str)
    output.to_csv(path, index=False)


def summarize_segment(trades: pd.DataFrame) -> dict:
    summary = performance_metrics(trades)
    summary["average_holding_hours"] = float(trades["holding_hours"].mean()) if not trades.empty else 0.0
    summary["long_trades"] = int((trades["side"] == "long").sum()) if not trades.empty else 0
    summary["short_trades"] = int((trades["side"] == "short").sum()) if not trades.empty else 0
    return summary


def plot_equity(series: dict[str, pd.DataFrame]) -> None:
    plt.style.use("dark_background")
    figure, axis = plt.subplots(figsize=(12, 6.5))
    colors = {"Directional": "#55e6b1", "Hedged": "#71b7ff"}
    for name, trades in series.items():
        if trades.empty:
            continue
        x = pd.to_datetime(trades["exit_time"], utc=True)
        y = 10_000.0 * trades["equity"]
        axis.step(x, y, where="post", label=name, color=colors[name], linewidth=2.2)
    axis.axhline(10_000, color="#82929a", linestyle="--", linewidth=1)
    axis.set_title("BTC spot–CME futures basis: locked legacy-period results")
    axis.set_ylabel("Equity from $10,000")
    axis.grid(alpha=0.15)
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(RESULTS / "equity-comparison.png", dpi=170)
    plt.close(figure)


def plot_events(events: pd.DataFrame) -> None:
    plt.style.use("dark_background")
    figure, axis = plt.subplots(figsize=(12, 5.5))
    colors = np.where(events["direction"] > 0, "#55e6b1", np.where(events["direction"] < 0, "#ff7782", "#718087"))
    axis.scatter(events.index, events["basis_z"], c=colors, s=38, alpha=0.9)
    axis.axhline(0, color="#82929a", linewidth=1)
    axis.set_title("Eligible legacy reopen events: standardized futures basis")
    axis.set_ylabel("Basis z-score at reopen")
    axis.grid(alpha=0.15)
    figure.tight_layout()
    figure.savefig(RESULTS / "basis-events.png", dpi=170)
    plt.close(figure)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    spot, futures = load_or_download(DATA)
    grids = parameter_grid()
    summary: dict = {
        "data": {
            "spot_rows": len(spot),
            "futures_rows": len(futures),
            "spot_start": str(spot.index.min()),
            "spot_end": str(spot.index.max()),
            "futures_start": str(futures.index.min()),
            "futures_end": str(futures.index.max()),
            "development": [str(DEV_START), str(LOCK_DATE)],
            "locked_validation": [str(LOCK_DATE), str(LEGACY_END)],
        },
        "market_structure": {
            "legacy_cutoff": str(LEGACY_END),
            "current_version_status": "not validated: CME moved crypto futures to 24/7 on 2026-05-29; Yahoo continuous data is not sufficient for the short maintenance-pause variant",
        },
    }
    full_trades: dict[str, pd.DataFrame] = {}
    representative_events = pd.DataFrame()
    for mode, costs in [("directional", 12.0), ("hedged", 32.0)]:
        base = StrategyConfig(mode=mode, round_trip_cost_bps=costs)
        grid = evaluate_grid(spot, futures, base, grids, DEV_START, LOCK_DATE)
        grid.to_csv(RESULTS / f"grid-{mode}.csv", index=False)
        locked = choose_locked_config(grid)
        config = replace(base, **locked)
        development = backtest(spot, futures, config, DEV_START, LOCK_DATE)
        validation = backtest(spot, futures, config, LOCK_DATE, LEGACY_END)
        full = backtest(spot, futures, config, DEV_START, LEGACY_END)
        export_trades(development, RESULTS / f"trades-{mode}-development.csv")
        export_trades(validation, RESULTS / f"trades-{mode}-validation.csv")
        export_trades(full, RESULTS / f"trades-{mode}-full.csv")
        full_trades[mode.title()] = full
        if representative_events.empty:
            representative_events = detect_reopen_events(spot, futures, config)
        summary[mode] = {
            "cost_bps_round_trip": costs,
            "locked_config": config.serializable(),
            "development": summarize_segment(development),
            "validation": summarize_segment(validation),
            "full_legacy": summarize_segment(full),
            "monte_carlo_full": monte_carlo(full),
            "monte_carlo_validation": monte_carlo(validation, seed=20260903),
        }

    if not representative_events.empty:
        representative_events.reset_index().to_csv(RESULTS / "eligible-reopen-events.csv", index=False)
        plot_events(representative_events)
    plot_equity(full_trades)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# BTC spot–CME futures basis validation",
        "",
        "The model was selected only on the development period and then frozen for the locked validation period.",
        "The Yahoo continuous futures series is a screening proxy, not institutional execution evidence.",
        "",
        "| Version | Period | Trades | Return | PF | Win rate | Max DD | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for mode in ["directional", "hedged"]:
        for segment, label in [("development", "Development"), ("validation", "Locked validation"), ("full_legacy", "Full legacy")]:
            metrics = summary[mode][segment]
            lines.append(
                f"| {mode.title()} | {label} | {metrics['trades']} | {metrics['return_pct']:+.2f}% | "
                f"{metrics['profit_factor']:.2f} | {metrics['win_rate_pct']:.2f}% | {metrics['max_drawdown_pct']:.2f}% | "
                f"{metrics['sharpe']:.2f} | {metrics['recovery_factor']:.2f} |"
            )
    lines.extend(
        [
            "",
            "## Important limitation",
            "",
            "CME launched 24/7 crypto futures trading on 2026-05-29. The historical weekend-reopen premise therefore no longer exists in the same form.",
            "The present-day maintenance-pause variant needs licensed, contract-level CME and spot data before it can be judged.",
        ]
    )
    (RESULTS / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
