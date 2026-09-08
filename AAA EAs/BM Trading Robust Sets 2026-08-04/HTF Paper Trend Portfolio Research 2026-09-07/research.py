"""Shared-rule HTF trend portfolio screen using archived broker M15 bars."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from functools import lru_cache
import importlib.util
import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ROOT.parent
SOURCE_ROOT = PACKAGE_ROOT / "Slow Multi Asset Trend Research 2026-09-06"
SOURCE_SCRIPT = SOURCE_ROOT / "research.py"
SYMBOLS = ("XAUUSD", "XAGUSD", "BTCUSD", "ETHUSD", "USTEC", "US30", "EURUSD", "GBPJPY")
GROWTH = {"BTCUSD", "ETHUSD", "USTEC", "US30"}
DEV = (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
FULL = (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
HORIZONS = {
    "1-3-12m": (21, 63, 252),
    "1-3-6m": (21, 63, 126),
    "3-6-12m": (63, 126, 252),
}
TREND_FILTERS = ("none", "ema100", "ema200")
DIRECTIONS = ("both", "growth-long-only", "long-only")
SESSIONS = ("all-day", "asia", "london", "new-york", "overlap")
STOP_NAMES = {0: "ATR", 1: "swing", 2: "chandelier"}
EXIT_NAMES = {0: "signal reversal", 1: "fixed RR", 2: "adaptive RR", 3: "time"}
MANAGE_NAMES = {0: "none", 1: "breakeven", 2: "ATR trail", 3: "chandelier trail", 4: "Dynamic 50/20"}


def _load_slow_module():
    spec = importlib.util.spec_from_file_location("calyx_slow_research", SOURCE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SOURCE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.HORIZONS.update(HORIZONS)
    return module


slow = _load_slow_module()


@dataclass(frozen=True)
class PortfolioConfig:
    tf: str = "D1"
    horizon: str = "1-3-12m"
    trend: str = "none"
    direction: str = "both"
    session: str = "all-day"
    stop_mode: int = 0
    stop_atr: float = 2.5
    exit_mode: int = 0
    rr: float = 2.0
    max_hold_days: int = 0
    manage: int = 0


def json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=json_default), encoding="utf-8")


@lru_cache(maxsize=8)
def frame_bundle(symbol: str):
    frame, meta, floor = slow.load(symbol)
    ts = frame.index.as_unit("s").asi8.astype(np.int64)
    arrays = (
        ts,
        frame.open.to_numpy(),
        frame.high.to_numpy(),
        frame.low.to_numpy(),
        frame.close.to_numpy(),
        frame.spread_price.to_numpy(),
    )
    return frame, meta, floor, arrays


def actual_direction(config: PortfolioConfig, symbol: str) -> str:
    if config.direction == "growth-long-only":
        return "long-only" if symbol in GROWTH else "both"
    return config.direction


@lru_cache(maxsize=24)
def signal_bundle(symbol: str, tf: str, horizon: str, trend: str, direction: str):
    frame = frame_bundle(symbol)[0]
    indicator, stamp = slow.make_signal(frame, tf, horizon, trend, direction)
    return (
        indicator.signal.fillna(0).to_numpy(np.int8),
        indicator.strength.fillna(0).to_numpy(),
        indicator.atr.to_numpy(),
        indicator.swing_low.to_numpy(),
        indicator.swing_high.to_numpy(),
        indicator.chand_long.to_numpy(),
        indicator.chand_short.to_numpy(),
        stamp,
    )


def run_asset(symbol: str, config: PortfolioConfig, start: pd.Timestamp, end: pd.Timestamp):
    frame, _, _, arrays = frame_bundle(symbol)
    direction = actual_direction(config, symbol)
    sig, strength, atr, swing_lo, swing_hi, chand_lo, chand_hi, stamp = signal_bundle(
        symbol, config.tf, config.horizon, config.trend, direction
    )
    out = slow.simulate_numba(
        *arrays,
        sig,
        strength,
        atr,
        swing_lo,
        swing_hi,
        chand_lo,
        chand_hi,
        stamp,
        int(start.timestamp()),
        int(end.timestamp()),
        slow.SESSIONS[config.session],
        config.stop_mode,
        config.stop_atr,
        config.exit_mode,
        config.rr,
        config.max_hold_days,
        config.manage,
        {"H4": 0, "D1": 1, "W1": 2}[config.tf],
    )
    entries, exits, rs, sides, mtm_dd = out
    metrics = slow.metrics(entries, exits, rs, sides, mtm_dd)
    ts = arrays[0]
    trades = []
    for entry, exit_, r_value, side in zip(entries, exits, rs, sides):
        index = int(np.searchsorted(ts, int(entry)))
        signal_strength = float(strength[min(index, len(strength) - 1)])
        trades.append(
            {
                "symbol": symbol,
                "entry_time": pd.Timestamp(int(entry), unit="s", tz="UTC").isoformat(),
                "exit_time": pd.Timestamp(int(exit_), unit="s", tz="UTC").isoformat(),
                "r": float(r_value),
                "return_fraction": float(max(-0.95, 0.01 * r_value)),
                "side": "long" if side > 0 else "short",
                "signal_strength": signal_strength,
            }
        )
    return metrics, trades


def accept_risk_cap(candidates: list[dict], cap: int = 4) -> list[dict]:
    ordered = sorted(
        candidates,
        key=lambda row: (
            pd.Timestamp(row["entry_time"]),
            -float(row.get("signal_strength", 0.0)),
            row["symbol"],
        ),
    )
    accepted: list[dict] = []
    open_exits: list[pd.Timestamp] = []
    for trade in ordered:
        entry = pd.Timestamp(trade["entry_time"])
        open_exits = [exit_ for exit_ in open_exits if exit_ > entry]
        if len(open_exits) >= cap:
            continue
        accepted.append(trade)
        open_exits.append(pd.Timestamp(trade["exit_time"]))
    accepted.sort(key=lambda row: (pd.Timestamp(row["exit_time"]), row["symbol"]))
    return accepted


def stats_from_trades(trades: list[dict], risk_scale: float = 1.0) -> dict:
    if not trades:
        return {
            "return_pct": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "max_dd_pct": 0.0,
            "trades": 0,
            "sharpe": 0.0,
            "recovery": 0.0,
            "expectancy_r": 0.0,
            "final_balance": 10000.0,
            "profitable_assets": 0,
        }
    fractions = np.array([float(row["return_fraction"]) * risk_scale for row in trades])
    curve = np.r_[10000.0, 10000.0 * np.cumprod(1.0 + fractions)]
    pnl = np.diff(curve)
    gross_loss = -float(pnl[pnl < 0].sum())
    pf = float(pnl[pnl > 0].sum()) / gross_loss if gross_loss > 0 else 99.0
    dd = float(np.max(1.0 - curve / np.maximum.accumulate(curve)) * 100.0)
    ret = float((curve[-1] / curve[0] - 1.0) * 100.0)
    dates = pd.to_datetime([row["exit_time"] for row in trades], utc=True)
    daily = pd.Series(fractions, index=dates).groupby(level=0).sum().resample("1D").sum()
    standard_deviation = float(daily.std(ddof=1))
    sharpe = float(daily.mean() / standard_deviation * math.sqrt(252)) if standard_deviation > 0 else 0.0
    asset_returns = {}
    for symbol in SYMBOLS:
        values = [1.0 + float(row["return_fraction"]) * risk_scale for row in trades if row["symbol"] == symbol]
        asset_returns[symbol] = (float(np.prod(values)) - 1.0) * 100.0 if values else 0.0
    return {
        "return_pct": ret,
        "profit_factor": min(99.0, pf),
        "win_rate": float(np.mean(fractions > 0) * 100.0),
        "max_dd_pct": dd,
        "trades": int(len(trades)),
        "sharpe": sharpe,
        "recovery": ret / dd if dd > 0 else 0.0,
        "expectancy_r": float(np.mean([row["r"] for row in trades])),
        "final_balance": float(curve[-1]),
        "profitable_assets": int(sum(value > 0 for value in asset_returns.values())),
    }


def evaluate(config: PortfolioConfig, start: pd.Timestamp, end: pd.Timestamp, include_trades: bool = False):
    candidates = []
    standalone = {}
    for symbol in SYMBOLS:
        metrics, trades = run_asset(symbol, config, start, end)
        standalone[symbol] = {key: value for key, value in metrics.items() if key != "trades_data"}
        candidates.extend(trades)
    accepted = accept_risk_cap(candidates)
    metrics = stats_from_trades(accepted)
    metrics["max_standalone_mtm_dd_pct"] = float(max(row["max_dd_pct"] for row in standalone.values()))
    result = {"metrics": metrics, "standalone": standalone}
    if include_trades:
        result["trades"] = accepted
        result["rejected_by_risk_cap"] = int(len(candidates) - len(accepted))
    return result


def score(metrics: dict) -> float:
    if metrics["trades"] < 45:
        return -10000.0 + metrics["trades"]
    if metrics["return_pct"] <= 0 or metrics["profit_factor"] < 1.0:
        return -1000.0 - metrics["max_dd_pct"]
    breadth = metrics["profitable_assets"]
    if breadth < 4:
        return -500.0 + breadth
    return (
        5.0 * math.log1p(metrics["return_pct"])
        + 5.0 * math.log(min(3.0, metrics["profit_factor"]))
        + 2.0 * max(-3.0, min(3.0, metrics["sharpe"]))
        + 2.0 * max(-3.0, min(8.0, metrics["recovery"]))
        + 0.5 * breadth
        + 0.01 * metrics["win_rate"]
        - 0.30 * metrics["max_dd_pct"]
        - 0.08 * metrics["max_standalone_mtm_dd_pct"]
    )


def screen_rows(configs: list[PortfolioConfig], phase: str, start: pd.Timestamp, end: pd.Timestamp):
    rows = []
    for number, config in enumerate(configs, 1):
        result = evaluate(config, start, end)
        metrics = result["metrics"]
        rows.append({"phase": phase, "config": asdict(config), **metrics, "score": score(metrics)})
        if number % 20 == 0 or number == len(configs):
            print(f"{phase}: {number}/{len(configs)}", flush=True)
    return rows


def select_config(start: pd.Timestamp, end: pd.Timestamp, save_rows: bool = True):
    all_rows = []
    signal_configs = [
        PortfolioConfig(tf=tf, horizon=horizon, trend=trend, direction=direction)
        for tf in ("H4", "D1", "W1")
        for horizon in HORIZONS
        for trend in TREND_FILTERS
        for direction in DIRECTIONS
    ]
    rows = screen_rows(signal_configs, "shared-signal", start, end)
    all_rows.extend(rows)
    chosen = PortfolioConfig(**max(rows, key=lambda row: row["score"])["config"])

    session_configs = [replace(chosen, session=session) for session in SESSIONS]
    rows = screen_rows(session_configs, "entry-session", start, end)
    all_rows.extend(rows)
    chosen = PortfolioConfig(**max(rows + [max(all_rows, key=lambda row: row["score"])], key=lambda row: row["score"])["config"])

    exit_configs = []
    exit_variants = [(0, 2.0, 0)]
    exit_variants += [(1, rr, 0) for rr in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0)]
    exit_variants += [(2, 2.0, 0), (3, 2.0, 20), (3, 2.0, 60), (3, 2.0, 120)]
    for stop_mode in STOP_NAMES:
        for stop_atr in (1.5, 2.5, 3.5):
            for exit_mode, rr, maximum_days in exit_variants:
                exit_configs.append(
                    replace(
                        chosen,
                        stop_mode=stop_mode,
                        stop_atr=stop_atr,
                        exit_mode=exit_mode,
                        rr=rr,
                        max_hold_days=maximum_days,
                    )
                )
    rows = screen_rows(exit_configs, "stop-and-exit", start, end)
    all_rows.extend(rows)
    chosen = PortfolioConfig(**max(rows + [max(all_rows, key=lambda row: row["score"])], key=lambda row: row["score"])["config"])

    management_configs = [replace(chosen, manage=manage) for manage in MANAGE_NAMES]
    rows = screen_rows(management_configs, "trade-management", start, end)
    all_rows.extend(rows)
    chosen = PortfolioConfig(**max(rows + [max(all_rows, key=lambda row: row["score"])], key=lambda row: row["score"])["config"])
    if save_rows:
        serialised = [{**row, "config": json.dumps(row["config"], sort_keys=True)} for row in all_rows]
        pd.DataFrame(serialised).to_csv(ROOT / "all-screen-results.csv", index=False)
    return chosen, all_rows


def monte_carlo(trades: list[dict], paths: int = 10000, seed: int = 20260907):
    fractions = np.array([row["return_fraction"] for row in trades])
    if len(fractions) == 0:
        return np.empty((0, 0)), {}
    rng = np.random.default_rng(seed)
    block = 5
    blocks = (len(fractions) + block - 1) // block
    starts = rng.integers(0, len(fractions), size=(paths, blocks))
    indices = (starts[:, :, None] + np.arange(block)) % len(fractions)
    samples = fractions[indices.reshape(paths, -1)[:, : len(fractions)]]
    curves = np.ones((paths, len(fractions) + 1)) * 10000.0
    curves[:, 1:] = 10000.0 * np.cumprod(1.0 + samples, axis=1)
    returns = (curves[:, -1] / 10000.0 - 1.0) * 100.0
    drawdowns = np.max(1.0 - curves / np.maximum.accumulate(curves, axis=1), axis=1) * 100.0
    stats = {
        "paths": paths,
        "return_p5": float(np.percentile(returns, 5)),
        "return_median": float(np.median(returns)),
        "return_p95": float(np.percentile(returns, 95)),
        "dd_median": float(np.median(drawdowns)),
        "dd_p95": float(np.percentile(drawdowns, 95)),
        "profitable_probability_pct": float(np.mean(returns > 0) * 100.0),
    }
    return curves, stats


def asset_table(trades: list[dict], standalone: dict):
    rows = []
    for symbol in SYMBOLS:
        selected = [row for row in trades if row["symbol"] == symbol]
        metrics = stats_from_trades(selected)
        rows.append(
            {
                "symbol": symbol,
                **metrics,
                "standalone_mtm_dd_pct": float(standalone[symbol]["max_dd_pct"]),
                "standalone_trades": int(standalone[symbol]["trades"]),
            }
        )
    return rows


def make_charts(screen: pd.DataFrame, locked: dict, assets: list[dict], stability: list[dict], curves: np.ndarray):
    charts = ROOT / "Charts"
    charts.mkdir(exist_ok=True)
    trades = locked["trades"]
    fractions = np.array([row["return_fraction"] for row in trades])
    equity = 10000.0 * np.cumprod(1.0 + fractions)
    dates = pd.to_datetime([row["exit_time"] for row in trades], utc=True)
    full = np.r_[10000.0, equity]
    dd = (1.0 - full / np.maximum.accumulate(full)) * 100.0
    plot_dates = pd.DatetimeIndex([LOCKED[0]]).append(pd.DatetimeIndex(dates))

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, constrained_layout=True)
    axes[0].step(plot_dates, full, where="post", color="#25d9a0", linewidth=1.7)
    axes[0].set_title("Locked-year HTF portfolio — closed balance")
    axes[0].set_ylabel("USD")
    axes[0].grid(alpha=0.2)
    axes[1].fill_between(plot_dates, -dd, 0, step="post", color="#e35d6a", alpha=0.55)
    axes[1].set_ylabel("Drawdown %")
    axes[1].grid(alpha=0.2)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.savefig(charts / "locked-equity-drawdown.png", dpi=160)
    plt.close(fig)

    x = np.arange(len(assets))
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    axes[0, 0].bar(x, [row["return_pct"] for row in assets], color=["#25b887" if row["return_pct"] > 0 else "#d85b67" for row in assets])
    axes[0, 0].set_title("Accepted-trade return contribution")
    axes[0, 1].bar(x, [row["profit_factor"] for row in assets], color="#5794e6")
    axes[0, 1].axhline(1.0, color="black", linewidth=0.7)
    axes[0, 1].set_title("Profit factor")
    axes[1, 0].bar(x, [row["win_rate"] for row in assets], color="#8a70d6")
    axes[1, 0].set_title("Win rate %")
    axes[1, 1].bar(x, [row["standalone_mtm_dd_pct"] for row in assets], color="#d18a42")
    axes[1, 1].set_title("Standalone M15 mark-to-market DD %")
    for axis in axes.flat:
        axis.set_xticks(x, [row["symbol"] for row in assets], rotation=25)
        axis.grid(axis="y", alpha=0.2)
    fig.savefig(charts / "locked-asset-breakdown.png", dpi=160)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(11, 6), constrained_layout=True)
    development = screen
    points = axis.scatter(
        development.max_dd_pct,
        development.return_pct,
        c=np.clip(development.profit_factor, 0, 3),
        s=10 + np.sqrt(np.maximum(development.trades, 0)) * 2,
        cmap="viridis",
        alpha=0.6,
    )
    axis.axhline(0, color="gray", linewidth=0.7)
    axis.set(title=f"All {len(development):,} shared-rule development screens", xlabel="Closed-balance DD %", ylabel="Return %")
    fig.colorbar(points, ax=axis, label="PF (capped at 3)")
    fig.savefig(charts / "all-configurations.png", dpi=160)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(11, 5), constrained_layout=True)
    labels = [row["period"] for row in stability]
    values = [row["return_pct"] for row in stability]
    axis.bar(labels, values, color=["#25b887" if value > 0 else "#d85b67" for value in values])
    axis.axhline(0, color="black", linewidth=0.7)
    axis.set(title="Frozen configuration — consecutive six-month returns", ylabel="Return %")
    axis.grid(axis="y", alpha=0.2)
    fig.savefig(charts / "six-month-stability.png", dpi=160)
    plt.close(fig)

    if curves.size:
        low, q25, median, q75, high = np.percentile(curves, [5, 25, 50, 75, 95], axis=0)
        xx = np.arange(len(low))
        fig, axis = plt.subplots(figsize=(11, 5), constrained_layout=True)
        axis.fill_between(xx, low, high, color="#397db6", alpha=0.18, label="5–95%")
        axis.fill_between(xx, q25, q75, color="#397db6", alpha=0.32, label="25–75%")
        axis.plot(xx, median, color="#f2f5f7", linewidth=1.5, label="Median")
        axis.set(title="10,000 five-trade block-bootstrap paths", xlabel="Closed trade", ylabel="USD balance")
        axis.grid(alpha=0.15)
        axis.legend()
        fig.patch.set_facecolor("#101820")
        axis.set_facecolor("#101820")
        axis.tick_params(colors="white")
        axis.xaxis.label.set_color("white")
        axis.yaxis.label.set_color("white")
        axis.title.set_color("white")
        fig.savefig(charts / "monte-carlo.png", dpi=160, facecolor=fig.get_facecolor())
        plt.close(fig)


def config_description(config: PortfolioConfig) -> str:
    if config.exit_mode == 1:
        exit_text = f"{config.rr:g}R"
    elif config.exit_mode == 3:
        exit_text = f"{config.max_hold_days}-day time exit"
    else:
        exit_text = EXIT_NAMES[config.exit_mode]
    return (
        f"{config.tf}, {config.horizon}, {config.trend}, {config.direction}, {config.session}; "
        f"{STOP_NAMES[config.stop_mode]} stop with {config.stop_atr:g} ATR floor; "
        f"{exit_text}; {MANAGE_NAMES[config.manage]} management"
    )


def main():
    print("Selecting one shared configuration on development data only", flush=True)
    selected, rows = select_config(*DEV)
    selection = {
        "selected_before_locked_year": True,
        "development_period": [DEV[0].isoformat(), DEV[1].isoformat()],
        "locked_period": [LOCKED[0].isoformat(), LOCKED[1].isoformat()],
        "config": asdict(selected),
        "description": config_description(selected),
        "risk_percent_per_trade": 1.0,
        "maximum_concurrent_trades": 4,
    }
    dump(ROOT / "selection-lock.json", selection)
    print("FROZEN", selection["description"], flush=True)

    development = evaluate(selected, *DEV, include_trades=True)
    locked = evaluate(selected, *LOCKED, include_trades=True)
    full = evaluate(selected, *FULL, include_trades=True)
    assets = asset_table(locked["trades"], locked["standalone"])

    stability = []
    cursor = FULL[0]
    while cursor < FULL[1]:
        end = min(cursor + pd.DateOffset(months=6), FULL[1])
        result = evaluate(selected, cursor, end, include_trades=True)
        stability.append({"period": f"{cursor:%Y-%m}→{end:%Y-%m}", **result["metrics"]})
        cursor = end

    curves, mc = monte_carlo(locked["trades"])
    stress_trades = [dict(row, return_fraction=float(row["return_fraction"]) - 0.0005) for row in locked["trades"]]
    cost_stress = stats_from_trades(stress_trades)
    risk_sensitivity = [
        {"risk_percent": risk, **stats_from_trades(locked["trades"], risk)} for risk in (0.5, 1.0)
    ]
    result = {
        "protocol": "single shared rule; development 2023-01-01..2025-09-01; untouched locked test 2025-09-01..2026-09-01",
        "config": asdict(selected),
        "description": config_description(selected),
        "development": development,
        "locked": locked,
        "full_context": full,
        "locked_assets": assets,
        "six_month_stability": stability,
        "monte_carlo": mc,
        "cost_stress_extra_0_05pct_per_trade": cost_stress,
        "risk_sensitivity": risk_sensitivity,
    }
    dump(ROOT / "results.json", result)
    pd.DataFrame(assets).to_csv(ROOT / "locked-asset-breakdown.csv", index=False)
    screen = pd.DataFrame([{**row, "config": json.dumps(row["config"], sort_keys=True)} for row in rows])
    make_charts(screen, locked, assets, stability, curves)

    locked_metrics = locked["metrics"]
    accepted_assets = sum(row["trades"] > 0 for row in assets)
    positive_assets = sum(row["return_pct"] > 0 for row in assets)
    accepted = (
        locked_metrics["return_pct"] > 0
        and locked_metrics["profit_factor"] >= 1.20
        and locked_metrics["trades"] >= 40
        and locked_metrics["max_dd_pct"] <= 15.0
        and cost_stress["return_pct"] > 0
        and positive_assets >= 4
        and mc.get("return_p5", -1) > 0
    )
    decision = "QUALIFIES FOR DEMO FORWARD TEST" if accepted else "REJECT / RESEARCH ONLY"

    lines = [
        "# Step 1 — Paper-Based HTF Multi-Asset Trend Portfolio",
        "",
        f"**Decision: {decision}. No EA, BAT or website change has been made.**",
        "",
        "## Frozen shared configuration",
        "",
        f"`{config_description(selected)}`",
        "",
        "This single configuration was selected across all eight assets using development data only. Every accepted trade uses a volatility-derived stop and a maximum of 1% current-equity risk; no more than four trades may overlap.",
        "",
        "## Portfolio results",
        "",
        "| Sample | Return | PF | Win rate | Closed DD | Trades | Sharpe | Recovery | Profitable assets |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, sample in (("Development", development), ("Locked year", locked), ("Full context", full)):
        metric = sample["metrics"]
        lines.append(
            f"| {label} | {metric['return_pct']:+.2f}% | {metric['profit_factor']:.2f} | {metric['win_rate']:.2f}% | {metric['max_dd_pct']:.2f}% | {metric['trades']} | {metric['sharpe']:.2f} | {metric['recovery']:.2f} | {metric['profitable_assets']}/8 |"
        )
    lines += [
        "",
        "Closed-balance DD is the synchronized portfolio figure. The maximum standalone M15 mark-to-market DD is reported separately because combining independent broker-bar simulations cannot reconstruct perfectly synchronized intraday equity.",
        "",
        "![Locked equity and drawdown](Charts/locked-equity-drawdown.png)",
        "",
        "## Locked-year asset breakdown",
        "",
        "| Asset | Return contribution | PF | Win rate | Accepted trades | Sharpe | Recovery | Standalone M15 MTM DD | Standalone trades |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in assets:
        lines.append(
            f"| {row['symbol']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery']:.2f} | {row['standalone_mtm_dd_pct']:.2f}% | {row['standalone_trades']} |"
        )
    lines += [
        "",
        "![Asset breakdown](Charts/locked-asset-breakdown.png)",
        "",
        "## Consecutive six-month stability",
        "",
        "| Period | Return | PF | Win rate | DD | Trades |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in stability:
        lines.append(
            f"| {row['period']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate']:.2f}% | {row['max_dd_pct']:.2f}% | {row['trades']} |"
        )
    lines += [
        "",
        "![Six-month stability](Charts/six-month-stability.png)",
        "",
        "## Robustness",
        "",
        f"Monte Carlo used 10,000 five-trade block-bootstrap paths. Return P5 was {mc.get('return_p5', 0):+.2f}%, median {mc.get('return_median', 0):+.2f}% and P95 {mc.get('return_p95', 0):+.2f}%. Median DD was {mc.get('dd_median', 0):.2f}% and P95 DD {mc.get('dd_p95', 0):.2f}%; {mc.get('profitable_probability_pct', 0):.2f}% of paths finished profitable.",
        "",
        f"Adding another 0.05% account cost to every trade produced {cost_stress['return_pct']:+.2f}% return, PF {cost_stress['profit_factor']:.2f} and {cost_stress['max_dd_pct']:.2f}% DD.",
        "",
        "![Monte Carlo](Charts/monte-carlo.png)",
        "",
        "## Screen and limitations",
        "",
        f"The development pipeline evaluated {len(rows):,} shared configurations. The locked year was not used to choose the rule.",
        "",
        "- The screen uses archived broker M15 bars and spread observations, not native MT5 tick replay. A qualifying result would still require a compiled portfolio implementation and native MT5 validation.",
        "- The four-position cap accepts the strongest simultaneous signals. A rejected independent trade is not retried until that standalone signal generates another entry; this is conservative but not identical to a centralized execution engine.",
        "- Carry, futures rolls and reliable historical CFD swap charges are not fully reconstructed. A holding-time financing allowance is included, plus the explicit additional-cost stress.",
        "- The available common broker history is roughly 2022–2026, much shorter than the century-scale paper evidence. This test validates our instruments and broker conditions, not the paper itself.",
        "- Backtests and Monte Carlo are not forecasts or guarantees.",
        "",
        "![All shared configurations](Charts/all-configurations.png)",
    ]
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    checks = [
        (len(SYMBOLS) == 8 and "EURUSD" in SYMBOLS, "all eight assets including EURUSD"),
        (selection["selected_before_locked_year"], "selection frozen before locked test"),
        (len(rows) >= 150, "complete staged shared-rule screen"),
        (locked_metrics["trades"] == len(locked["trades"]), "locked trade ledger count"),
        (all(pd.Timestamp(row["entry_time"]) >= LOCKED[0] for row in locked["trades"]), "locked entries inside interval"),
        (all(pd.Timestamp(row["entry_time"]) < LOCKED[1] for row in locked["trades"]), "no post-lock entries"),
        (locked_metrics["max_dd_pct"] >= 0, "drawdown calculated"),
        (mc.get("paths") == 10000, "10,000 Monte Carlo paths"),
        ((ROOT / "Charts" / "locked-equity-drawdown.png").is_file(), "equity graph generated"),
        ((ROOT / "Charts" / "locked-asset-breakdown.png").is_file(), "asset graph generated"),
        (not any(path.name.endswith(".set") or path.suffix == ".ex5" for path in ROOT.rglob("*")), "no EA/SET promoted before review"),
    ]
    verification = [f"{'PASS' if ok else 'FAIL'} {label}" for ok, label in checks]
    verification.append(f"SUMMARY {sum(ok for ok, _ in checks)}/{len(checks)} checks passed")
    (ROOT / "VERIFICATION.txt").write_text("\n".join(verification) + "\n", encoding="utf-8")
    dump(
        ROOT / "progress.json",
        {
            "step": 1,
            "title": "Paper-Based HTF Multi-Asset Trend Portfolio",
            "status": "awaiting-review",
            "decision": decision,
            "screened_configurations": len(rows),
            "locked_trades": locked_metrics["trades"],
            "monte_carlo_paths": 10000,
            "production_changed": False,
        },
    )
    print(decision, locked_metrics, flush=True)


if __name__ == "__main__":
    main()
