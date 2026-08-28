from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .config import ARTIFACT_ROOT, INITIAL_BALANCE, TEST_END, TEST_START


COLORS = {
    "xau": "#d4a72c",
    "us100": "#268bd2",
    "btc": "#f7931a",
    "eth": "#7c83fd",
    "us30": "#2aa198",
}


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Cannot JSON-encode {type(value).__name__}")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, default=_json_default, allow_nan=False),
        encoding="utf-8",
    )


def plot_standalone(results: dict[str, Any], path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=False)
    for axis, (key, result) in zip(axes.flat, results.items(), strict=False):
        equity = result["optimized"]["equity"]
        literal = result["literal"]["equity"]
        axis.plot(literal.index, literal.values, color="#8b949e", linewidth=1.1, label="Repo literal")
        axis.plot(equity.index, equity.values, color=COLORS[key], linewidth=1.7, label="Train-selected")
        axis.axhline(INITIAL_BALANCE, color="#555", linestyle="--", linewidth=0.8)
        metrics = result["optimized"]["metrics"]
        axis.set_title(
            f"{result['label']}  |  {metrics['return_pct']:+.2f}%  PF {metrics['profit_factor']:.2f}  "
            f"DD {metrics['max_equity_dd_pct']:.2f}%"
        )
        axis.set_ylabel("Equity (USD)")
        axis.grid(alpha=0.20)
        axis.legend(loc="best", fontsize=8)
    fig.suptitle("Markov Regime EA — locked one-year out-of-sample equity", fontsize=15)
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def plot_active_filter(result: dict[str, Any], path: Path) -> None:
    baseline = result["baseline"]["equity"]
    filtered = result["filtered"]["equity"]
    fig, axis = plt.subplots(figsize=(13, 6.5))
    axis.plot(baseline.index, baseline.values, label="Active BAT — unchanged", color="#8892a0", linewidth=1.3)
    axis.plot(filtered.index, filtered.values, label="Markov-filtered research overlay", color="#00c896", linewidth=1.8)
    axis.axhline(INITIAL_BALANCE, color="#555", linestyle="--", linewidth=0.8)
    axis.set_title("Existing active EAs — historical MT5 cash-flow overlay")
    axis.set_ylabel("Realized balance (USD)")
    axis.grid(alpha=0.20)
    axis.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def write_equity_csv(results: dict[str, Any], path: Path) -> None:
    columns: dict[str, pd.Series] = {}
    for key, result in results.items():
        columns[f"{key}_literal"] = result["literal"]["equity"]
        columns[f"{key}_optimized"] = result["optimized"]["equity"]
    pd.DataFrame(columns).sort_index().to_csv(path, index_label="Date")


def write_active_csv(result: dict[str, Any], path: Path) -> None:
    baseline = result["baseline"]["equity"].groupby(level=0).last()
    filtered = result["filtered"]["equity"].groupby(level=0).last()
    frame = pd.concat(
        [
            baseline.rename("baseline"),
            filtered.rename("filtered"),
        ],
        axis=1,
    ).sort_index().ffill()
    frame.to_csv(path, index_label="Time")


def write_standalone_summary_csv(results: dict[str, Any], path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for key, result in results.items():
        for variant in ("literal", "optimized"):
            rows.append(
                {
                    "asset": result["label"],
                    "proxy": result["ticker"],
                    "variant": variant,
                    **result[variant]["metrics"],
                    **{f"param_{name}": value for name, value in result[variant]["config"].items()},
                }
            )
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _metric_row(label: str, result: dict[str, Any]) -> str:
    metric = result["metrics"]
    return (
        f"| {label} | {metric['return_pct']:+.2f}% | {metric['profit_factor']:.2f} | "
        f"{metric['win_rate_pct']:.2f}% | {metric['max_equity_dd_pct']:.2f}% | "
        f"{metric['trades']} | ${metric['final_balance']:,.2f} |"
    )


def write_full_report(
    standalone: dict[str, Any],
    active: dict[str, Any],
    snapshots: dict[str, Any],
    path: Path,
) -> None:
    lines = [
        "# Markov Regime EA — research and validation report",
        "",
        f"**Locked test:** {TEST_START} to {TEST_END}  ",
        "**Initial balance:** $10,000 per standalone asset  ",
        "**Risk:** 1% of current balance per standalone trade  ",
        "**Selection rule:** parameters were selected only on the training period ending 2025-08-10.",
        "",
        "## Standalone out-of-sample results",
        "",
        "| Asset | Return | PF | Win rate | Max equity DD | Trades | Final |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in standalone.values():
        lines.append(_metric_row(result["label"], result["optimized"]))
    lines += [
        "",
        "![Standalone equity](standalone-equity.png)",
        "",
        "### Repository-literal comparison",
        "",
        "The supplied repository defines the regime forecast, but not a complete execution model. "
        "For a fair comparison, the literal version uses its default 20-day / 5% labels with the "
        "same 1% ATR execution shell.",
        "",
        "| Asset | Return | PF | Win rate | Max equity DD | Trades | Final |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in standalone.values():
        lines.append(_metric_row(result["label"], result["literal"]))
    lines += [
        "",
        "## Existing active EAs: regime-filter experiment",
        "",
        "This experiment does **not** rewrite or enable anything in the active installer. It replays "
        "the existing MT5 reports and vetoes entries whose direction disagreed with the prior daily regime.",
        "",
        "| Version | Return | PF | Win rate | Max realized DD | Trades | Final |",
        "|---|---:|---:|---:|---:|---:|---:|",
        _metric_row("Current active BAT", active["baseline"]),
        _metric_row("Markov-filtered overlay", active["filtered"]),
        "",
        "![Active filter equity](active-ea-filter-equity.png)",
        "",
        "### Effect by EA",
        "",
        "| EA | Symbol | Base return | Filtered return | Base PF | Filtered PF | Kept |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in active["by_ea"]:
        lines.append(
            f"| {item['ea']} | {item['symbol']} | {item['baseline']['return_pct']:+.2f}% | "
            f"{item['filtered']['return_pct']:+.2f}% | {item['baseline']['profit_factor']:.2f} | "
            f"{item['filtered']['profit_factor']:.2f} | {item['accepted_pct']:.1f}% |"
        )
    lines += [
        "",
        "## Current regime snapshots",
        "",
        "| Asset | State | Signal | Bull next | Sideways next | Bear next |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for key, snapshot in snapshots.items():
        probs = snapshot["next_probabilities"]
        lines.append(
            f"| {standalone.get(key, {'label': key.upper()})['label']} | {snapshot['current_regime']} | "
            f"{snapshot['signal']:+.4f} | {probs['bull']:.2%} | {probs['sideways']:.2%} | {probs['bear']:.2%} |"
        )
    lines += [
        "",
        "## Evidence limits",
        "",
        "- Standalone tests use fresh Yahoo daily continuous-futures/spot proxies: GC=F, NQ=F, BTC-USD and ETH-USD.",
        "- These are not MT5 tick tests and do not reproduce Exness symbol specifications, intraday spread spikes or slippage.",
        "- Explicit conservative round-trip cost assumptions are included: XAU 5 bps, US100 3 bps, BTC 12 bps, ETH 15 bps.",
        "- Existing-EA filtering uses the actual net trade cash flows in the saved MT5 reports, so their commission and swap remain included.",
        "- A profitable backtest does not establish live profitability. Keep this research overlay out of the active BAT until it passes MT5 tick and forward validation.",
        "",
        "## Reproducibility",
        "",
        "Run `INSTALL.bat`, then `RUN BACKTEST.bat`. Exact downloaded bars, selected parameters, trades, CSVs and PNG graphs are retained in this folder.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_paths() -> dict[str, Path]:
    return {
        "standalone_json": ARTIFACT_ROOT / "standalone-results.json",
        "standalone_csv": ARTIFACT_ROOT / "standalone-results.csv",
        "standalone_equity_csv": ARTIFACT_ROOT / "standalone-equity.csv",
        "standalone_graph": ARTIFACT_ROOT / "standalone-equity.png",
        "active_json": ARTIFACT_ROOT / "active-ea-regime-filter.json",
        "active_csv": ARTIFACT_ROOT / "active-ea-filter-equity.csv",
        "active_graph": ARTIFACT_ROOT / "active-ea-filter-equity.png",
        "signals": ARTIFACT_ROOT / "current-signals.json",
        "locked_settings": ARTIFACT_ROOT / "LOCKED SETTINGS.json",
        "report": ARTIFACT_ROOT / "FULL REPORT.md",
    }
