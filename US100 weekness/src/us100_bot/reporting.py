from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analytics import metrics, monthly, skips_frame, trades_frame
from .config import Config
from .models import Skip, SymbolSpec, Trade
from .normalization import PriceNormalizer


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def _table(mapping: dict[str, Any]) -> str:
    return "<table>" + "".join(
        f"<tr><th>{html.escape(str(k).replace('_',' ').title())}</th><td>{html.escape(_fmt(v))}</td></tr>"
        for k, v in mapping.items()
    ) + "</table>"


def _chart_paths(
    df: pd.DataFrame,
    monthly_df: pd.DataFrame,
    out: Path,
    start_balance: float,
    oos: pd.DataFrame | None = None,
) -> list[Path]:
    paths: list[Path] = []
    if df.empty:
        return paths
    ordered = df.sort_values("exit_time").copy()
    ordered["exit_time"] = pd.to_datetime(ordered["exit_time"], utc=True)
    equity = start_balance + ordered["pnl"].cumsum()
    peak = np.maximum.accumulate(np.r_[start_balance, equity.values])[1:]
    drawdown = peak - equity.values
    charts = [
        ("equity_curve.png", ordered["exit_time"], equity, "Equity", "Account equity"),
        ("drawdown_curve.png", ordered["exit_time"], drawdown, "Drawdown", "Drawdown"),
    ]
    for filename, x, y, ylabel, title in charts:
        fig, ax = plt.subplots(figsize=(11, 4))
        ax.plot(x, y, linewidth=1.2)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(alpha=.25)
        fig.tight_layout()
        path = out / filename
        fig.savefig(path, dpi=140)
        plt.close(fig)
        paths.append(path)
    if not monthly_df.empty:
        fig, ax = plt.subplots(figsize=(11, 4))
        colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in monthly_df["Net Profit"]]
        ax.bar(monthly_df["Month"], monthly_df["Net Profit"], color=colors)
        ax.tick_params(axis="x", rotation=45)
        ax.set_title("Monthly net profit")
        ax.grid(axis="y", alpha=.25)
        fig.tight_layout()
        path = out / "monthly_profit.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        paths.append(path)
    grouped = ordered.groupby("strategy")["pnl"].agg(["sum", "count"])
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(grouped.index, grouped["sum"], color="#3498db")
    ax.set_title("Net profit by strategy")
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    path = out / "strategy_profit.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    paths.append(path)
    strategy_stats = []
    for name, group in ordered.groupby("strategy"):
        met = metrics(group, start_balance)
        strategy_stats.append(
            {
                "strategy": name,
                "pf": 10.0 if met["profit_factor"] == "inf" else float(met["profit_factor"]),
                "win_rate": float(met["win_rate"]),
            }
        )
    compare = pd.DataFrame(strategy_stats)
    for column, filename, title in (
        ("pf", "profit_factor_comparison.png", "Profit factor by strategy"),
        ("win_rate", "win_rate_comparison.png", "Win rate by strategy"),
    ):
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(compare["strategy"], compare[column], color="#9b59b6")
        ax.set_title(title)
        ax.grid(axis="y", alpha=.25)
        fig.tight_layout()
        path = out / filename
        fig.savefig(path, dpi=140)
        plt.close(fig)
        paths.append(path)
    ordered["entry_time"] = pd.to_datetime(ordered["entry_time"], utc=True)
    ordered["weekday"] = ordered["entry_time"].dt.day_name()
    ordered["entry_clock"] = ordered["entry_time"].dt.tz_convert("America/New_York").dt.strftime("%H:%M")
    for field, filename, title in (
        ("weekday", "profit_by_weekday.png", "Profit by weekday"),
        ("entry_clock", "profit_by_entry_time.png", "Profit by New York entry time"),
    ):
        series = ordered.groupby(field)["pnl"].sum()
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.bar(series.index, series.values, color="#16a085")
        ax.tick_params(axis="x", rotation=35)
        ax.set_title(title)
        ax.grid(axis="y", alpha=.25)
        fig.tight_layout()
        path = out / filename
        fig.savefig(path, dpi=140)
        plt.close(fig)
        paths.append(path)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(ordered["mae"].astype(float), bins=30, color="#e74c3c", alpha=.8)
    axes[0].set_title("MAE distribution (price units)")
    axes[1].hist(ordered["mfe"].astype(float), bins=30, color="#2ecc71", alpha=.8)
    axes[1].set_title("MFE distribution (price units)")
    fig.tight_layout()
    path = out / "mae_mfe_distributions.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    paths.append(path)
    if oos is not None and not oos.empty:
        baseline_met = metrics(df, start_balance)
        oos_met = metrics(oos, start_balance)
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        axes[0].bar(
            ["Baseline", "Walk-forward OOS"],
            [float(baseline_met["net_profit"]), float(oos_met["net_profit"])],
            color=["#3498db", "#f39c12"],
        )
        axes[0].set_title("Net profit comparison")
        axes[1].bar(
            ["Baseline", "Walk-forward OOS"],
            [float(baseline_met["max_dd_pct"]), float(oos_met["max_dd_pct"])],
            color=["#3498db", "#f39c12"],
        )
        axes[1].set_title("Maximum drawdown %")
        fig.tight_layout()
        path = out / "baseline_vs_oos.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        paths.append(path)
    return paths


def write_report(
    cfg: Config,
    spec: SymbolSpec,
    norm: PriceNormalizer,
    baseline_trades: list[Trade],
    baseline_skips: list[Skip],
    oos_trades: list[Trade],
    oos_skips: list[Skip],
    wf: pd.DataFrame,
    robust: pd.DataFrame,
    start: str,
    end: str,
    data_path: Path,
    data_bars: int,
) -> dict[str, Path]:
    out = cfg.report_dir
    out.mkdir(parents=True, exist_ok=True)
    base = trades_frame(baseline_trades)
    oos = trades_frame(oos_trades)
    skips = skips_frame(baseline_skips)
    monthly_all = monthly(base, cfg.starting_balance)
    base.to_csv(out / "backtest_trades.csv", index=False)
    oos.to_csv(out / "walk_forward_oos_trades.csv", index=False)
    skips.to_csv(out / "skipped_setups.csv", index=False)
    monthly_all.to_csv(out / "monthly_results.csv", index=False)
    wf.to_csv(out / "walk_forward_selections.csv", index=False)
    robust.to_csv(out / "robustness_results.csv", index=False)
    per_strategy: dict[str, dict[str, Any]] = {}
    per_month: list[pd.DataFrame] = []
    monthly_groups = {
        "A_FIXED": ("A_FIXED",),
        "A_RUNNER": ("A_RUNNER",),
        "A_COMPLETE": ("A_FIXED", "A_RUNNER"),
        "B1": ("B1",),
        "B2": ("B2",),
        "B_COMPLETE": ("B1", "B2"),
        "COMBINED": ("A_FIXED", "A_RUNNER", "B1", "B2"),
    }
    for name, members in monthly_groups.items():
        subset = base[base["strategy"].isin(members)] if not base.empty else base
        per_strategy[name] = metrics(subset, cfg.starting_balance)
        m = monthly(subset, cfg.starting_balance)
        if not m.empty:
            m.insert(0, "Strategy", name)
            per_month.append(m)
    complete = {
        "A_COMPLETE": per_strategy["A_COMPLETE"],
        "B_COMPLETE": per_strategy["B_COMPLETE"],
        "COMBINED": per_strategy["COMBINED"],
        "OOS_COMBINED": metrics(oos, cfg.starting_balance),
    }
    if per_month:
        pd.concat(per_month, ignore_index=True).to_csv(out / "monthly_by_strategy.csv", index=False)
    chart_paths = _chart_paths(base, monthly_all, out, cfg.starting_balance, oos)
    skip_rate = len(skips) / (len(skips) + len(base)) * 100 if len(skips) + len(base) else 0
    assumptions = {
        "symbol": spec.name,
        "description": spec.description,
        "period_utc": f"{start} through {end}",
        "model": "Broker M1 bid OHLC + per-bar historical spread; pessimistic same-bar stop ordering",
        "bars": data_bars,
        "source": str(data_path),
        "commission_per_lot_round_turn": cfg.commission_per_lot,
        "slippage_pips_each_execution": cfg.slippage_pips,
        "skipped_setup_rate_pct": skip_rate,
        **norm.describe(),
    }
    (out / "metrics.json").write_text(
        json.dumps({"assumptions": assumptions, "strategies": per_strategy, **complete}, indent=2, default=str),
        encoding="utf-8",
    )
    style = """
    body{font-family:Segoe UI,Arial;background:#0d1117;color:#e6edf3;margin:30px;line-height:1.4}
    h1,h2{color:#58a6ff} table{border-collapse:collapse;margin:12px 0 28px;min-width:620px}
    th,td{border:1px solid #30363d;padding:7px 10px;text-align:right} th:first-child,td:first-child{text-align:left}
    th{background:#161b22} .warn{background:#3d2b00;padding:12px;border-left:4px solid #d29922}
    img{max-width:100%;background:white;margin:8px 0 24px}
    """
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'><title>US100 strategy report</title>",
        f"<style>{style}</style></head><body>",
        "<h1>US100 New York Session Strategy Report</h1>",
        "<div class='warn'><b>Research report:</b> M1 bar modeling cannot reproduce tick sequence or sub-minute delays. Live trading remains disabled by default.</div>",
        "<h2>Data and broker conversion</h2>", _table(assumptions),
        "<h2>Baseline results</h2>",
    ]
    for name, met in {**per_strategy, **{k:v for k,v in complete.items() if k != "OOS_COMBINED"}}.items():
        parts.extend([f"<h3>{name}</h3>", _table(met)])
    parts.extend(["<h2>Walk-forward unseen results</h2>", _table(complete["OOS_COMBINED"])])
    if not wf.empty:
        parts.append(wf.to_html(index=False, escape=True))
    parts.extend(["<h2>Monthly combined breakdown</h2>", monthly_all.to_html(index=False, escape=True) if not monthly_all.empty else "<p>No trades.</p>"])
    parts.extend(["<h2>Robustness</h2>", robust.to_html(index=False, escape=True)])
    parts.append("<p>Second-level entry delays (1/2/5/10 seconds) are not claimed because the broker history available to this test is M1, not real ticks.</p>")
    for path in chart_paths:
        parts.append(f"<img src='{path.name}' alt='{path.stem}'>")
    parts.append("</body></html>")
    report = out / "US100_report.html"
    report.write_text("".join(parts), encoding="utf-8")
    return {
        "html": report,
        "trades": out / "backtest_trades.csv",
        "monthly": out / "monthly_results.csv",
        "oos": out / "walk_forward_oos_trades.csv",
        "robustness": out / "robustness_results.csv",
        "metrics": out / "metrics.json",
    }
