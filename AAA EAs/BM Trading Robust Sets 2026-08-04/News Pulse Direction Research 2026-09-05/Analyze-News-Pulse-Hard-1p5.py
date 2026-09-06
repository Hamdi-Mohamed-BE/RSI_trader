from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
CORE_PATH = ROOT / "Analyze-News-Pulse-Multi.py"
SPEC = importlib.util.spec_from_file_location("news_pulse_core", CORE_PATH)
assert SPEC and SPEC.loader
CORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORE)
ASSETS = ("xauusd", "xagusd", "eurusd")


def save_rows(stage: str, rows: list[dict]) -> None:
    prefix = f"HARD 1P5 {stage.upper()} RESULTS"
    (ROOT / f"{prefix}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    flat = [{key: value for key, value in row.items() if key not in {"series", "trade_returns"}} for row in rows]
    with (ROOT / f"{prefix}.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)


def plot_equity(stage: str, rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(11, 5.6), dpi=160)
    colors = {"xauusd": "#38bdf8", "xagusd": "#a78bfa", "eurusd": "#f59e0b"}
    for row in rows:
        dates = [datetime.fromisoformat(point["date"]) for point in row["series"]]
        balances = [point["balance"] for point in row["series"]]
        label = f"{row['symbol']}: {row['return_pct']:+.2f}% / PF {row['profit_factor']:.2f} / DD {row['max_drawdown_pct']:.2f}% / n={row['trades']}"
        ax.plot(dates, balances, linewidth=2, color=colors[row["asset"]], label=label)
    ax.axhline(10000, color="#94a3b8", linestyle="--", linewidth=0.8)
    ax.grid(True, alpha=0.18)
    ax.spines[["top", "right"]].set_visible(False)
    locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.set_title(f"News Pulse — hard 1.50% total event risk — {stage}")
    ax.set_ylabel("Balance (USD)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    chart_root = ROOT / "Charts"
    chart_root.mkdir(exist_ok=True)
    fig.savefig(chart_root / f"HARD 1P5 {stage.upper()} EQUITY.png", bbox_inches="tight")
    plt.close(fig)


def finalize() -> None:
    full_path = ROOT / "HARD 1P5 FULL RESULTS.json"
    stress_path = ROOT / "HARD 1P5 STRESS RESULTS.json"
    if not full_path.exists() or not stress_path.exists():
        return
    full = json.loads(full_path.read_text(encoding="utf-8"))
    stress = json.loads(stress_path.read_text(encoding="utf-8"))
    monte_carlo = {row["asset"]: CORE.monte_carlo(row) for row in full}
    payload = {
        "events": ["NFP", "CPI", "FOMC statement / Federal Reserve rate decision"],
        "risk": {"per_pending_stop_pct": 0.75, "maximum_planned_event_pct": 1.50, "source_locked": True},
        "period": "2025-09-01 to 2026-09-01",
        "full": full,
        "random_delay": stress,
        "monte_carlo": monte_carlo,
    }
    (ROOT / "HARD 1P5 FINAL AUDIT.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# News Pulse — deployed hard 1.50% total-risk audit", "",
        "The EA watches NFP, CPI, and FOMC statements/rate decisions. Both pending directions are enabled. The compiled v2.12 source hard-locks 0.75% risk per stop, for at most 1.50% planned event exposure.", "",
        "| Market | Entry / stop | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Random-delay return / PF | MC P5 return | MC P95 DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for asset in ASSETS:
        row = next(item for item in full if item["asset"] == asset)
        stressed = next(item for item in stress if item["asset"] == asset)
        mc = monte_carlo[asset]
        lines.append(
            f"| {row['symbol']} | {row['entry_offset']:g} / {row['stop_distance']:g} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe_ratio']:.2f} | {row['recovery_factor']:.2f} | {stressed['return_pct']:+.2f}% / {stressed['profit_factor']:.2f} | {mc['return_p5_pct']:+.2f}% | {mc['max_dd_p95_pct']:.2f}% |"
        )
    lines.extend([
        "", "MT5 Sharpe is shown for completeness but is mechanically inflated by sparse positions held for roughly one minute. News gaps, spread expansion, slippage and order rejection can exceed the planned 1.50% exposure.",
    ])
    (ROOT / "HARD 1P5 FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("Full", "Stress"))
    args = parser.parse_args()
    manifest_path = ROOT / "Backtest Reports" / f"Hard 1.5 {args.stage}" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if isinstance(manifest, dict):
        manifest = [manifest]
    rows = [CORE.parse_report(Path(item["report"]), item) for item in manifest]
    if any(row["trades"] <= 0 or row["history_quality_pct"] < 90 for row in rows):
        raise RuntimeError("A hard-1.5 deployment test has missing trades or inadequate history quality.")
    save_rows(args.stage, rows)
    plot_equity(args.stage, rows)
    finalize()
    for row in rows:
        print(f"{row['symbol']:7} ret={row['return_pct']:+8.2f}% PF={row['profit_factor']:6.2f} win={row['win_rate_pct']:6.2f}% DD={row['max_drawdown_pct']:5.2f}% n={row['trades']:2}")


if __name__ == "__main__":
    main()
