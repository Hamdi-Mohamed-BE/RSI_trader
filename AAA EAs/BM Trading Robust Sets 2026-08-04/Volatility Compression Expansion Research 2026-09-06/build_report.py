from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
SYMBOLS = ("XAUUSD", "XAGUSD", "BTCUSD", "US30", "USTEC", "GBPJPY")
LABELS = {"USTEC": "US100", "US30": "US30"}
LOCKED_START = "2025-09-01"
LOCKED_END = "2026-09-01"
FULL_START = "2023-09-01"
FULL_END = "2026-09-01"
RNG = np.random.default_rng(9690606)
COLORS = {
    "XAUUSD": "#f3c969", "XAGUSD": "#b7c2d0", "BTCUSD": "#ff9b46",
    "US30": "#70a1ff", "USTEC": "#55efc4", "GBPJPY": "#d6a2e8",
}


def name(symbol: str) -> str:
    return LABELS.get(symbol, symbol)


def money(value: float) -> str:
    return f"${value:,.2f}"


def fmt(value: float, digits: int = 2) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def pct(value: float) -> str:
    return f"{value:+.2f}%"


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    def clean(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
    output = ["| " + " | ".join(map(clean, headers)) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    output.extend("| " + " | ".join(map(clean, row)) + " |" for row in rows)
    return "\n".join(output)


def bootstrap(returns: np.ndarray, paths: int = 10_000, block: int = 5) -> dict:
    n = len(returns)
    if n == 0:
        return {"paths": paths, "trades": 0, "profit_probability_pct": 0.0, "ending_p5_pct": 0.0,
                "ending_median_pct": 0.0, "ending_p95_pct": 0.0, "dd_median_pct": 0.0, "dd_p95_pct": 0.0}
    endings = np.empty(paths); dds = np.empty(paths)
    blocks_needed = int(np.ceil(n / block))
    starts = np.arange(n)
    for p in range(paths):
        chosen = RNG.choice(starts, blocks_needed, replace=True)
        sample = np.concatenate([np.take(returns, np.arange(s, s + block) % n) for s in chosen])[:n]
        equity = np.concatenate(([1.0], np.cumprod(1.0 + sample)))
        peak = np.maximum.accumulate(equity)
        endings[p] = (equity[-1] - 1.0) * 100.0
        dds[p] = np.max((peak - equity) / peak) * 100.0
    return {
        "paths": paths, "block_size": block, "trades": n,
        "profit_probability_pct": float(np.mean(endings > 0) * 100.0),
        "ending_p5_pct": float(np.percentile(endings, 5)),
        "ending_median_pct": float(np.percentile(endings, 50)),
        "ending_p95_pct": float(np.percentile(endings, 95)),
        "dd_median_pct": float(np.percentile(dds, 50)),
        "dd_p95_pct": float(np.percentile(dds, 95)),
        "endings": endings.tolist(), "dds": dds.tolist(),
    }


def decision(row: dict, full: dict, mc: dict) -> tuple[str, str]:
    symbol = row["symbol"]
    if symbol == "XAUUSD" and row["profit_factor"] >= 1.30 and row["trades"] >= 75 and full["profit_factor"] >= 1.25:
        return "DEMO ONLY", "Only asset with repeatable PF across both native horizons; 3-year DD still too high for live promotion."
    if symbol == "BTCUSD":
        return "WATCH", "Excellent locked year, but 3-year PF is only 1.08 and DD is 17.79%; likely regime-dependent."
    if symbol == "US30":
        return "WATCH", "Low DD and positive 3-year result, but the locked PF/trade count are too weak."
    if symbol == "USTEC":
        return "REJECT", "Three-year PF is near breakeven with 24.86% DD."
    if symbol == "XAGUSD":
        return "REJECT", "Native PF and drawdown fail the gate despite the proxy result."
    return "REJECT", "Negative locked and three-year native evidence."


def equity_frame(row: dict) -> pd.DataFrame:
    frame = pd.DataFrame(row["series"])
    frame["date"] = pd.to_datetime(frame["date"], format="mixed")
    return frame.sort_values("date")


def main() -> None:
    charts = ROOT / "Charts"; charts.mkdir(exist_ok=True)
    native = json.loads((ROOT / "native-results.json").read_text(encoding="utf-8"))
    locks = json.loads((ROOT / "selection-lock.json").read_text(encoding="utf-8"))
    locked = {row["symbol"]: row for row in native if row["stage"] == "locked"}
    full = {row["symbol"]: row for row in native if row["stage"] == "full"}

    mc_rows = []
    mc_raw = {}
    for symbol in SYMBOLS:
        trades_path = ROOT / "Native" / f"{symbol.lower()}-frozen-locked-model0" / "trades.json"
        trades = json.loads(trades_path.read_text(encoding="utf-8"))
        result = bootstrap(np.array([item["return_fraction"] for item in trades], dtype=float))
        mc_raw[symbol] = result
        mc_rows.append({"symbol": symbol, **{k: v for k, v in result.items() if k not in ("endings", "dds")}})
    pd.DataFrame(mc_rows).to_csv(ROOT / "native-monte-carlo-summary.csv", index=False)
    (ROOT / "native-monte-carlo.json").write_text(json.dumps(mc_raw, indent=2), encoding="utf-8")

    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), constrained_layout=True)
    fig.patch.set_facecolor("#06110f")
    for ax, symbol in zip(axes.flat, SYMBOLS):
        frame = equity_frame(locked[symbol])
        ax.plot(frame["date"], frame["balance"], color=COLORS[symbol], lw=1.8)
        ax.axhline(10_000, color="#7f8c8d", lw=.8, alpha=.6)
        ax.set_title(f"{name(symbol)} — locked year", loc="left", fontsize=12, weight="bold")
        ax.set_facecolor("#081916"); ax.grid(color="#28433e", alpha=.35)
        ax.tick_params(axis="x", rotation=25)
        ax.text(.02, .95, f"{pct(locked[symbol]['return_pct'])} | PF {locked[symbol]['profit_factor']:.2f} | DD {locked[symbol]['equity_dd_pct']:.2f}%",
                transform=ax.transAxes, va="top", color="#88f7cf", fontsize=9)
    fig.suptitle("Calyx Volatility Compression → Expansion — untouched native MT5 year", fontsize=19, weight="bold", color="#88f7cf")
    fig.savefig(charts / "native-locked-equity-curves.png", dpi=160, facecolor=fig.get_facecolor()); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), constrained_layout=True)
    fig.patch.set_facecolor("#06110f")
    xs = np.arange(len(SYMBOLS)); labels = [name(s) for s in SYMBOLS]
    metrics = [
        ("Locked return (%)", [locked[s]["return_pct"] for s in SYMBOLS], 0),
        ("Profit factor", [locked[s]["profit_factor"] for s in SYMBOLS], 1),
        ("Maximum equity DD (%)", [locked[s]["equity_dd_pct"] for s in SYMBOLS], 0),
    ]
    for ax, (title, values, baseline) in zip(axes, metrics):
        colors = ["#55efc4" if (v > baseline if title != "Maximum equity DD (%)" else v <= 12) else "#ff7675" for v in values]
        ax.bar(xs, values, color=colors, alpha=.9); ax.axhline(baseline, color="#dfe6e9", lw=.8)
        ax.set_xticks(xs, labels, rotation=30); ax.set_title(title, loc="left", weight="bold")
        ax.set_facecolor("#081916"); ax.grid(axis="y", color="#28433e", alpha=.35)
        for x, v in zip(xs, values): ax.text(x, v, f" {v:.2f}", ha="center", va="bottom", fontsize=8)
    fig.suptitle("Native locked-year decision metrics", fontsize=18, weight="bold", color="#88f7cf")
    fig.savefig(charts / "native-locked-comparison.png", dpi=160, facecolor=fig.get_facecolor()); plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(18, 10), constrained_layout=True)
    fig.patch.set_facecolor("#06110f")
    for ax, symbol in zip(axes.flat, SYMBOLS):
        data = np.asarray(mc_raw[symbol]["endings"])
        ax.hist(data, bins=55, color=COLORS[symbol], alpha=.8); ax.axvline(0, color="#ff7675", lw=1)
        ax.axvline(np.median(data), color="#ffffff", lw=1.2, ls="--")
        ax.set_title(f"{name(symbol)} — 10,000 paths", loc="left", weight="bold")
        ax.set_facecolor("#081916"); ax.grid(color="#28433e", alpha=.25)
        ax.text(.02, .95, f"Profit chance {mc_raw[symbol]['profit_probability_pct']:.1f}%\nP5 {mc_raw[symbol]['ending_p5_pct']:+.1f}% | DD95 {mc_raw[symbol]['dd_p95_pct']:.1f}%",
                transform=ax.transAxes, va="top", fontsize=9)
    fig.suptitle("Locked-year block-bootstrap Monte Carlo — same trades, different sequence luck", fontsize=18, weight="bold", color="#88f7cf")
    fig.savefig(charts / "native-monte-carlo.png", dpi=160, facecolor=fig.get_facecolor()); plt.close(fig)

    summary_rows = []
    decisions = {}
    for symbol in SYMBOLS:
        verdict, why = decision(locked[symbol], full[symbol], mc_raw[symbol]); decisions[symbol] = {"decision": verdict, "reason": why}
        r, f = locked[symbol], full[symbol]
        summary_rows.append([name(symbol), verdict, pct(r["return_pct"]), fmt(r["profit_factor"]), f"{r['win_rate']:.2f}%",
                             f"{r['equity_dd_pct']:.2f}%", r["trades"], fmt(r["sharpe_ratio"]), fmt(r["recovery_factor"]),
                             pct(f["return_pct"]), fmt(f["profit_factor"]), f"{f['equity_dd_pct']:.2f}%", f["trades"]])

    config_rows = []
    for symbol in SYMBOLS:
        c = locks[symbol]["config"]
        config_rows.append([name(symbol), c["timeframe"], c["session"], f"{c['compression']} {c['compression_value']}",
                            f"{c['range_bars']}/{c['arm_bars']}", c["confirmation"], c["trend"], c["direction"],
                            f"{c['stop_mode']} {c['stop_value']}", f"{c['rr']}R", c["management"], c["maximum_hold_bars"]])

    mc_table = []
    for symbol in SYMBOLS:
        m = mc_raw[symbol]
        mc_table.append([name(symbol), f"{m['profit_probability_pct']:.1f}%", pct(m["ending_p5_pct"]), pct(m["ending_median_pct"]),
                         pct(m["ending_p95_pct"]), f"{m['dd_median_pct']:.2f}%", f"{m['dd_p95_pct']:.2f}%"])

    proxy_screen = json.loads((ROOT / "screen-final.json").read_text(encoding="utf-8"))
    proxy_map = ({symbol: value["locked"] for symbol, value in proxy_screen.items()}
                 if isinstance(proxy_screen, dict) else
                 {row["symbol"]: row for row in proxy_screen if row.get("period") == "locked"})
    proxy_rows = []
    for symbol in SYMBOLS:
        p = proxy_map.get(symbol, {})
        n = locked[symbol]
        proxy_rows.append([name(symbol), pct(p.get("return_pct", float("nan"))), fmt(p.get("profit_factor", float("nan"))),
                           p.get("trades", "n/a"), pct(n["return_pct"]), fmt(n["profit_factor"]), n["trades"]])

    management = pd.read_csv(ROOT / "management-sensitivity.csv")
    management_rows = []
    for symbol in SYMBOLS:
        subset = management[management.symbol == symbol]
        for _, row in subset.iterrows():
            c = json.loads(row.config)
            management_rows.append([name(symbol), c["management"], pct(row.validation_return_pct), fmt(row.validation_profit_factor),
                                    f"{row.validation_win_rate:.2f}%", f"{row.validation_max_dd_pct:.2f}%", int(row.validation_trades)])

    rr = pd.read_csv(ROOT / "rr-sensitivity.csv")
    rr_rows = []
    for symbol in SYMBOLS:
        subset = rr[rr.symbol == symbol].sort_values("score", ascending=False).head(3)
        for _, row in subset.iterrows():
            c = json.loads(row.config)
            rr_rows.append([name(symbol), f"{c['rr']}R", pct(row.train_return_pct), fmt(row.train_profit_factor),
                            pct(row.validation_return_pct), fmt(row.validation_profit_factor), f"{row.validation_max_dd_pct:.2f}%", int(row.validation_trades)])

    report = f"""# Step 6 — Volatility Compression → Expansion

## Goal and outcome

Build a no-look-ahead compression-breakout EA and run the agreed pipeline on XAU, XAG, BTC, US30, US100 and GBPJPY at a fixed **1.00% current-equity risk per trade**. The six configurations were selected using the development and pre-lock validation windows, frozen, and only then read on the untouched year.

**Outcome: do not add this EA to the live/recommended system yet.** XAU is the only version worth forward-demo testing. BTC is a useful watch candidate but its three-year native evidence is not stable. The other four fail the promotion gate.

## Native MT5 results — decisive evidence

{markdown_table(['Asset','Decision','Locked return','PF','Win rate','DD','Trades','Sharpe','Recovery','3y return','3y PF','3y DD','3y trades'], summary_rows)}

Locked year: {LOCKED_START} to {LOCKED_END}. Three-year context: {FULL_START} to {FULL_END}. Initial balance $10,000. Native MetaTrader 5, broker history, Every Tick model, recorded spread, 1% dynamic equity risk. Sharpe and recovery are MT5 report values. History quality is 98–100%.

### Decision notes

"""
    for symbol in SYMBOLS:
        report += f"- **{name(symbol)} — {decisions[symbol]['decision']}:** {decisions[symbol]['reason']}\n"
    report += f"""

## Frozen configuration per asset

{markdown_table(['Asset','TF','Session','Compression','Range/arm','Confirm','Trend','Direction','Stop','RR','Management','Max bars'], config_rows)}

All session hours are UTC with automatic DST handling for London and New York. No locked-period values were used to select these configurations.

## Monte Carlo — locked native trades

{markdown_table(['Asset','Profit chance','End P5','End median','End P95','Median DD','DD P95'], mc_table)}

Method: 10,000 stationary five-trade block-bootstrap paths per asset. This reshuffles actual locked-year native trade returns while retaining some local clustering. It estimates sequencing risk; it cannot forecast a new market regime.

## Management comparison before the lock was opened

{markdown_table(['Asset','Management','Validation return','PF','Win rate','DD','Trades'], management_rows)}

The “dynamic-m15-50-20” option moves the stop to +0.20R after a completed M15 candle has reached at least +0.50R. The optimizer was allowed to reject it. It did: no management was selected for XAU, BTC, US30, US100 and GBPJPY; XAG selected simple break-even. This is important evidence that trailing logic can reduce this system's expectancy.

## Best three RR candidates in pre-lock research

{markdown_table(['Asset','RR','Train return','Train PF','Validation return','Validation PF','Validation DD','Validation trades'], rr_rows)}

RR was searched from 0.5R through 6R. The table is a staged, pre-lock sensitivity view around the then-current candidate—not a second optimization on the untouched year.

## Proxy-to-native reality check

{markdown_table(['Asset','Proxy locked return','Proxy PF','Proxy trades','Native locked return','Native PF','Native trades'], proxy_rows)}

The proxy was used only to screen configurations quickly. Native execution is authoritative. The large XAG divergence is the clearest warning against publishing proxy-only statistics.

## Pipeline completed

- Five signal timeframes: M5, M15, M30, H1 and H4.
- Six session modes: all day, Asia, London, New York, London–New York overlap, and London-or-New-York.
- Four compression definitions: ATR contraction, Bollinger bandwidth percentile, narrow range and Bollinger-inside-Keltner approximation.
- Confirmation, trend, direction, stop placement, holding time, RR 0.5R–6R, break-even, ATR trail and Dynamic M15 50–20 management.
- Development year, separate validation year, untouched locked year and exact three-year native MT5 context.
- Rolling six-month proxy stability and 10,000-path native Monte Carlo.
- Compilation: **0 errors, 0 warnings**. Native trade ledger reconciles to each MT5 report.

## Honest recommendation

1. **XAU:** forward-demo only for at least 8–12 weeks and 30+ new trades. Keep risk at 1% only in demo; its 17.01% three-year DD is too high for immediate real/prop deployment.
2. **BTC:** keep as research/watch, not portfolio. Recent PF 1.73 is attractive, but three-year PF 1.08 shows regime dependence.
3. **US30:** archive as an alternate research preset. It has controlled DD, but only 21 locked trades and PF 1.14.
4. **XAG, US100 and GBPJPY:** reject this strategy/configuration.

No BAT, recommended portfolio, website catalogue, cache or live MT5 profile was changed. The EA remains tester-only until you review and explicitly choose a next action.

## Research rationale

Compression-breakout logic is a testable volatility-scaling hypothesis rather than a guaranteed edge. The build used volatility-normalized thresholds because price changes show non-trivial scaling behaviour, Bollinger bandwidth as a standard relative-volatility measure, and session filters because intraday continuation/predictability varies across the day. These ideas justified the search space; they did not determine the verdict—the native locked evidence did.
"""
    (ROOT / "REPORT.md").write_text(report, encoding="utf-8")

    readme = """# Calyx Volatility Compression Expansion Research

Research-only MT5 EA and full pipeline evidence for XAUUSD, XAGUSD, BTCUSD, US30, USTEC (US100) and GBPJPY.

- `REPORT.md` — concise decision report and all core tables.
- `selection-lock.json` — configuration freeze made before locked-year inspection.
- `native-results.json/csv` — authoritative MT5 Every Tick evidence.
- `native-monte-carlo.json/csv` — 10,000-path locked-trade block bootstrap.
- `all-screen-results.csv` and sensitivity CSVs — proxy research surface.
- `Native/` — original MT5 HTML reports, graphs and reconciled trade ledgers.
- `EA/` — tester-only MQL5 source; fixed 1% risk.
- `Charts/` — report figures.

Nothing in this folder is installed by the production portfolio BAT files.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    (ROOT / "decisions.json").write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    print("REPORT BUILT", ROOT / "REPORT.md")


if __name__ == "__main__":
    main()
