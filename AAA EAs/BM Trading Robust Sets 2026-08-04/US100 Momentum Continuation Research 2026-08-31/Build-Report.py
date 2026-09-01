from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter


ROOT = Path(__file__).resolve().parent
SELECTED = ["baseline-active", "ny-long-only", "ny-gate-exact", "h1-exact"]
LABELS = {
    "baseline-active": "Current BAT EA",
    "ny-long-only": "Current entry, long only",
    "ny-gate-exact": "Current entry + screenshot H1 gate",
    "h1-exact": "Literal screenshot H1 strategy",
}
COLORS = {
    "baseline-active": "#70e1f5",
    "ny-long-only": "#ffd166",
    "ny-gate-exact": "#62f6a8",
    "h1-exact": "#c69cff",
}


def load(stage: str) -> dict[str, dict]:
    rows = json.loads((ROOT / f"{stage}-results.json").read_text(encoding="utf-8"))
    return {row["case"]: row for row in rows}


def curve(row: dict) -> tuple[np.ndarray, np.ndarray]:
    dates = np.array([np.datetime64(point["date"]) for point in row["series"]])
    balances = np.array([float(point["balance"]) for point in row["series"]])
    return dates, (balances / balances[0] - 1.0) * 100.0


def trade_returns(row: dict) -> np.ndarray:
    balances = np.array([float(point["balance"]) for point in row["series"]])
    returns = balances[1:] / balances[:-1] - 1.0
    return returns[np.isfinite(returns)]


def bootstrap(row: dict, seed: int = 20260831, paths: int = 4000) -> dict:
    outcomes = trade_returns(row)
    rng = np.random.default_rng(seed)
    samples = rng.choice(outcomes, size=(paths, len(outcomes)), replace=True)
    equity = np.cumprod(1.0 + samples, axis=1)
    equity = np.column_stack([np.ones(paths), equity])
    peaks = np.maximum.accumulate(equity, axis=1)
    drawdowns = 1.0 - equity / peaks
    end = (equity[:, -1] - 1.0) * 100.0
    max_dd = np.max(drawdowns, axis=1) * 100.0
    return {
        "end": end,
        "max_dd": max_dd,
        "median_return": float(np.median(end)),
        "p05_return": float(np.percentile(end, 5)),
        "p95_return": float(np.percentile(end, 95)),
        "median_dd": float(np.median(max_dd)),
        "p95_dd": float(np.percentile(max_dd, 95)),
        "chance_profit": float(np.mean(end > 0.0) * 100.0),
    }


def fmt(row: dict, key: str, decimals: int = 2) -> str:
    return f"{float(row[key]):.{decimals}f}"


def main() -> None:
    development = load("development")
    locked = load("locked")
    lastyear = load("lastyear")
    monte = {case: bootstrap(locked[case]) for case in ("baseline-active", "ny-gate-exact")}

    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), constrained_layout=True)
    fig.patch.set_facecolor("#071116")
    for ax in axes.flat:
        ax.set_facecolor("#0c1920")
        ax.grid(color="#29404a", alpha=0.35, linewidth=0.7)
        for spine in ax.spines.values():
            spine.set_color("#29404a")

    for ax, stage, title in (
        (axes[0, 0], development, "Development: 2019-07-16 to 2024-12-31 (98% quality)"),
        (axes[0, 1], locked, "Locked holdout: 2025-01-01 to 2026-08-27 (100% quality)"),
        (axes[1, 0], lastyear, "Last year: 2025-08-28 to 2026-08-27 (100% quality)"),
    ):
        for case in SELECTED:
            dates, returns = curve(stage[case])
            ax.plot(dates, returns, label=LABELS[case], color=COLORS[case], linewidth=2.0)
        ax.axhline(0, color="#8ca0aa", linewidth=0.9, alpha=0.7)
        ax.set_title(title, fontsize=12, fontweight="bold", loc="left")
        ax.set_ylabel("Return on $10,000 (%)")
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))

    ax = axes[1, 1]
    bins = np.linspace(0, max(monte["baseline-active"]["p95_dd"], monte["ny-gate-exact"]["p95_dd"]) * 1.25, 45)
    for case in ("baseline-active", "ny-gate-exact"):
        ax.hist(monte[case]["max_dd"], bins=bins, density=True, alpha=0.45,
                color=COLORS[case], label=LABELS[case])
        ax.axvline(monte[case]["p95_dd"], color=COLORS[case], linestyle="--", linewidth=1.8)
    ax.set_title("Locked-trade bootstrap: 4,000 resamples", fontsize=12, fontweight="bold", loc="left")
    ax.set_xlabel("Maximum drawdown (%) — dashed line is 95th percentile")
    ax.set_ylabel("Density")

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.02), frameon=False)
    fig.suptitle("US100 Momentum — Screenshot Continuation Test", fontsize=20, fontweight="bold", y=1.065)
    graph = ROOT / "US100 MOMENTUM IMPROVEMENT COMPARISON.png"
    fig.savefig(graph, dpi=180, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)

    summary_rows = []
    for stage_name, stage in (("Development", development), ("Locked", locked), ("Last year", lastyear)):
        for case in SELECTED:
            row = stage[case]
            summary_rows.append({
                "stage": stage_name,
                "variant": LABELS[case],
                "return_pct": row["return_pct"],
                "profit_factor": row["profit_factor"],
                "win_rate_pct": row["win_rate"],
                "max_equity_dd_pct": row["equity_dd_pct"],
                "trades": row["trades"],
                "commission": row["commission"],
                "history_quality_pct": row["history_quality_pct"],
            })
    with (ROOT / "SUMMARY.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_rows[0].keys())
        writer.writeheader()
        writer.writerows(summary_rows)

    def table(stage: dict) -> str:
        lines = [
            "| Variant | Return | PF | Win rate | Max equity DD | Trades |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for case in SELECTED:
            row = stage[case]
            lines.append(
                f"| {LABELS[case]} | {float(row['return_pct']):+.2f}% | {fmt(row, 'profit_factor')} | "
                f"{fmt(row, 'win_rate')}% | {fmt(row, 'equity_dd_pct')}% | {int(row['trades'])} |"
            )
        return "\n".join(lines)

    base = locked["baseline-active"]
    gate = locked["ny-gate-exact"]
    report = f"""# US100 Momentum Continuation Improvement Test

## Decision

**Do not replace the active BAT EA.** The screenshot-derived H1 gate looked attractive in development but failed the untouched 2025–2026 holdout. The literal H1 strategy also failed. The current NY-open EA remains the strongest tested version.

## What was reconstructed

1. **Long-only:** exploit the positive long-run drift of the Nasdaq.
2. **24-hour momentum:** completed H1 close minus the close 24 bars earlier must exceed 0.5 ATR.
3. **Range leadership:** the completed close must be in the top 25% of its trailing 48-bar high-low range.
4. **Trend:** EMA(100) must be rising.
5. **Ride and trail:** enter the next H1 bar, use a 2.5 ATR initial/trailing stop and close after at most 120 H1 bars.

Two implementations were tested: the literal standalone H1 system and the same filters used only as a gate for the existing 09:30–09:35 New York M5 signal.

## Development screen — 2019-07-16 to 2024-12-31

{table(development)}

The exact gate appeared to improve PF from {base['profit_factor'] if False else development['baseline-active']['profit_factor']:.2f} to {development['ny-gate-exact']['profit_factor']:.2f} and reduce drawdown from {development['baseline-active']['equity_dd_pct']:.2f}% to {development['ny-gate-exact']['equity_dd_pct']:.2f}%. These results were used only to decide what to carry forward.

## Locked holdout — 2025-01-01 to 2026-08-27

{table(locked)}

On untouched data, the exact H1 gate changed return from {base['return_pct']:+.2f}% to {gate['return_pct']:+.2f}%, PF from {base['profit_factor']:.2f} to {gate['profit_factor']:.2f}, and trades from {base['trades']} to {gate['trades']}. This is a failed robustness test, not an improvement.

## Last year — 2025-08-28 to 2026-08-27

{table(lastyear)}

The gate reduced last-year drawdown, but it discarded too many profitable signals: return fell from {lastyear['baseline-active']['return_pct']:+.2f}% to {lastyear['ny-gate-exact']['return_pct']:+.2f}%.

## Bootstrap diagnostic — locked trades, 4,000 resamples

| Variant | Chance profitable | Median return | 5–95% return | Median max DD | 95th-percentile DD |
|---|---:|---:|---:|---:|---:|
| Current BAT EA | {monte['baseline-active']['chance_profit']:.1f}% | {monte['baseline-active']['median_return']:+.1f}% | {monte['baseline-active']['p05_return']:+.1f}% to {monte['baseline-active']['p95_return']:+.1f}% | {monte['baseline-active']['median_dd']:.1f}% | {monte['baseline-active']['p95_dd']:.1f}% |
| Screenshot H1 gate | {monte['ny-gate-exact']['chance_profit']:.1f}% | {monte['ny-gate-exact']['median_return']:+.1f}% | {monte['ny-gate-exact']['p05_return']:+.1f}% to {monte['ny-gate-exact']['p95_return']:+.1f}% | {monte['ny-gate-exact']['median_dd']:.1f}% | {monte['ny-gate-exact']['p95_dd']:.1f}% |

Bootstrap paths resample the same locked trade returns and therefore measure sequencing uncertainty, not future market-regime uncertainty.

## Test integrity

- Broker: Exness, USTEC CFD.
- Initial balance: $10,000.
- Risk: 1% of current equity per trade for apples-to-apples comparison.
- Development: MT5 1-minute OHLC screen, 98% broker history quality.
- Locked and last year: MT5 Every Tick, 100% history quality.
- Broker spread, commission, swap and random execution delay were included.
- Rules were frozen before the locked test.
- Active BAT, active preset and website were not changed.
"""
    (ROOT / "FULL REPORT.md").write_text(report, encoding="utf-8")
    print(graph)
    print(ROOT / "FULL REPORT.md")


if __name__ == "__main__":
    main()
