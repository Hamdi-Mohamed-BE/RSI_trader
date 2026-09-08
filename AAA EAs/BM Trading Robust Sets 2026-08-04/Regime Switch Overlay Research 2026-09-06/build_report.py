"""Build final charts, Monte Carlo comparisons and the human-readable report."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import research


ROOT = Path(__file__).resolve().parent
CHARTS = ROOT / "Charts"


def fmt(value, digits=2):
    return f"{float(value):.{digits}f}"


def main() -> int:
    results = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    screen = pd.read_csv(ROOT / "all-screen-results.csv")
    CHARTS.mkdir(exist_ok=True)

    modes = ("directional-signal", "directional-state", "flat-sideways", "regime-switch")
    colors = {"directional-signal": "#34d399", "directional-state": "#60a5fa", "flat-sideways": "#fbbf24", "regime-switch": "#a78bfa"}
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    for ax, symbol in zip(axes.flat, research.SYMBOLS):
        frame = screen[screen.symbol == symbol]
        for mode in modes:
            subset = frame[frame["config"].str.contains(f'"mode": "{mode}"', regex=False)]
            if len(subset):
                ax.scatter(subset.validation_max_dd_pct, subset.validation_return_pct, s=9, alpha=.25, color=colors[mode], label=mode)
        ax.axhline(0, color="#64748b", lw=.8); ax.set_title(symbol)
        ax.set_xlabel("Pre-lock validation DD (%)"); ax.set_ylabel("Pre-lock validation return (%)"); ax.grid(alpha=.2)
    axes[0, 0].legend(markerscale=2)
    fig.suptitle("All 5,380 causal regime configurations — selection evidence only")
    fig.tight_layout(); fig.savefig(CHARTS / "configuration-screen.png", dpi=180); plt.close(fig)

    switch_symbols = [s for s in research.SYMBOLS if "regime-switch" in results[s]["best_by_mode"]]
    fig, axes = plt.subplots(2, 2, figsize=(15, 9)); x = np.arange(len(switch_symbols)); width=.36
    fields = (("return_pct", "Locked return (%)"), ("profit_factor", "Locked profit factor"), ("win_rate", "Locked win rate (%)"), ("max_dd_pct", "Locked max drawdown (%)"))
    for ax, (field, title) in zip(axes.flat, fields):
        baseline = [results[s]["baseline_locked"][field] for s in switch_symbols]
        switched = [results[s]["best_by_mode"]["regime-switch"]["locked"][field] for s in switch_symbols]
        ax.bar(x-width/2, baseline, width, color="#64748b", label="Momentum baseline")
        ax.bar(x+width/2, switched, width, color="#a78bfa", label="True regime switch")
        ax.set_xticks(x, switch_symbols); ax.set_title(title); ax.grid(axis="y", alpha=.2)
    axes[0,0].legend(); fig.suptitle("Best pre-lock regime-switch rule — untouched locked year")
    fig.tight_layout(); fig.savefig(CHARTS / "true-switch-locked.png", dpi=180); plt.close(fig)

    mode_mc = {}
    mode_trades = {}
    for symbol in switch_symbols:
        cfg = research.Config(**results[symbol]["best_by_mode"]["regime-switch"]["config"])
        close = research.load_prices(symbol); forecast = research.forecasts(close, cfg)
        momentum, snapback = research.ledgers(symbol, "locked")
        trades = research.select_non_overlapping(research.attach_forecast(momentum + snapback, forecast), cfg, research.LOCKED)
        mode_mc[symbol] = research.monte_carlo(trades)
        full_momentum, full_snapback = research.ledgers(symbol, "full")
        full_trades = research.select_non_overlapping(research.attach_forecast(full_momentum + full_snapback, forecast), cfg, research.FULL)
        mode_trades[symbol] = {
            "locked": [research.public_trade(row) for row in trades],
            "full": [research.public_trade(row) for row in full_trades],
        }
    (ROOT / "true-switch-monte-carlo.json").write_text(json.dumps(mode_mc, indent=2), encoding="utf-8")
    (ROOT / "true-switch-trades.json").write_text(json.dumps(mode_trades, indent=2), encoding="utf-8")

    lines = [
        "# Step 1 — Volatility-Regime Switch: Final Report", "",
        "## Decision", "",
        "**Do not replace the live portfolio defaults. XAUUSD qualifies only for a demo-forward test of the true switch; XAGUSD, BTCUSD and USTEC are rejected for deployment.**", "",
        "The overlay was selected without reading the latest year. It used completed UTC daily bars only, fixed 1% risk, native MT5 component ledgers, and 10,000 Monte Carlo paths.", "",
        "## Primary selection: best rule across all regime modes", "",
        "| Asset | Locked return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | MC P5 | Decision |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for symbol in research.SYMBOLS:
        r = results[symbol]; locked=r["selected_locked"]; mc=r["monte_carlo"]
        decision = "Research only" if symbol == "XAUUSD" else "Reject"
        lines.append(f"| {symbol} | {fmt(locked['return_pct'])}% | {fmt(locked['profit_factor'])} | {fmt(locked['win_rate'])}% | {fmt(locked['max_dd_pct'])}% | {locked['trades']} | {fmt(locked['sharpe'])} | {fmt(locked['recovery'])} | {fmt(mc['return_p5'])}% | {decision} |")
    lines += ["", "## Frozen baseline versus selected overlay", "", "| Asset | Baseline return | Baseline PF | Baseline DD | Baseline trades | Overlay return | Overlay PF | Overlay DD | Overlay trades |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for symbol in research.SYMBOLS:
        b=results[symbol]["baseline_locked"]; s=results[symbol]["selected_locked"]
        lines.append(f"| {symbol} | {fmt(b['return_pct'])}% | {fmt(b['profit_factor'])} | {fmt(b['max_dd_pct'])}% | {b['trades']} | {fmt(s['return_pct'])}% | {fmt(s['profit_factor'])} | {fmt(s['max_dd_pct'])}% | {s['trades']} |")
    lines += ["", "## The actual momentum / mean-reversion switch", "", "| Asset | Train return / PF / trades | Validation return / PF / trades | Locked return | PF | Win rate | DD | Trades (Mom/MR) | Sharpe | Recovery | MC P5 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for symbol in switch_symbols:
        v=results[symbol]["best_by_mode"]["regime-switch"]; t=v["train"]; a=v["validation"]; l=v["locked"]; mc=mode_mc[symbol]
        lines.append(f"| {symbol} | {fmt(t['return_pct'])}% / {fmt(t['profit_factor'])} / {t['trades']} | {fmt(a['return_pct'])}% / {fmt(a['profit_factor'])} / {a['trades']} | {fmt(l['return_pct'])}% | {fmt(l['profit_factor'])} | {fmt(l['win_rate'])}% | {fmt(l['max_dd_pct'])}% | {l['trades']} ({l['momentum_trades']}/{l['mean_reversion_trades']}) | {fmt(l['sharpe'])} | {fmt(l['recovery'])} | {fmt(mc['return_p5'])}% |")
    lines += [
        "", "## Recommendation", "",
        "- **XAUUSD:** demo-forward test the true switch only. Its frozen rule used a 40-day return, ±2% state threshold, 126-transition history, no directional signal buffer, and a 50% Sideways-probability requirement. Locked evidence was +34.74%, PF 2.85, 37.93% wins, 4.68% DD, 29 trades; Monte Carlo P5 was +5.98% and DD P95 was 8.30%.",
        "- **XAGUSD:** reject. The locked result is based on only three trades and its pre-lock train and validation returns were both negative.",
        "- **BTCUSD:** reject. The filtered locked result has only three trades and no separately validated BTC mean-reversion leg exists.",
        "- **USTEC:** reject. The globally selected overlay remained negative. The true switch became +2.53% in the locked year, but its pre-lock validation was slightly negative and its Monte Carlo P5 was negative; selecting it now would be post-lock cherry-picking.",
        "", "## Important limitation", "",
        "This stage is an overlay on already validated native-MT5 trade ledgers, not a fresh tick-by-tick rerun of a newly coded combined EA. It is strong enough to choose a demo candidate, not strong enough for live capital. The next valid action for XAU is to implement the frozen switch in an experimental EA, run native MT5 Every Tick/random-delay validation, then forward-test it without changing the current live portfolio.",
        "", "## Files", "",
        "- `results.json`: complete selected, baseline, per-mode and trade-level results.",
        "- `all-screen-results.csv`: all 5,380 tested configurations.",
        "- `true-switch-monte-carlo.json`: 10,000-path robustness results.",
        "- `Charts/`: locked comparison, equity, full configuration screen and true-switch charts.",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
