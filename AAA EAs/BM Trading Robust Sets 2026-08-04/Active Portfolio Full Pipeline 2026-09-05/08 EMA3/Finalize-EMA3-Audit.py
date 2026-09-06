from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "Backtest Reports"
STARTING_BALANCE = 10_000.0
PATHS = 10_000
BLOCK_DAYS = 5
SEED = 20_260_905

CASES = [
    "deployed-standard-dynamic-native",
    "manage-dynamic6020-only",
    "manage-dynamic6020-only-safe",
    "combo-all-atr150-rr250",
    "stop-fixed-1500",
]
LABELS = {
    "deployed-standard-dynamic-native": "Previous Dynamic 50/20 + native trail",
    "manage-dynamic6020-only": "Recommended Dynamic 60/20 only",
    "manage-dynamic6020-only-safe": "Full Safe Dynamic 60/20 only",
    "combo-all-atr150-rr250": "Higher-return ATR 1.5 / 2.5R",
    "stop-fixed-1500": "Highest-return fixed 15 stop",
}
COLORS = {
    "deployed-standard-dynamic-native": "#94a3b8",
    "manage-dynamic6020-only": "#6ee7b7",
    "manage-dynamic6020-only-safe": "#38bdf8",
    "combo-all-atr150-rr250": "#fbbf24",
    "stop-fixed-1500": "#f97316",
}


def load(stage: str) -> dict[str, dict]:
    rows = json.loads((REPORTS / stage / "results.json").read_text(encoding="utf-8"))
    return {str(row["case"]): row for row in rows}


def daily_returns(row: dict, start: date, end: date) -> tuple[np.ndarray, np.ndarray]:
    events: defaultdict[date, float] = defaultdict(float)
    series = row.get("series") or []
    previous = float(series[0]["balance"]) if series else STARTING_BALANCE
    for point in series[1:]:
        current = float(point["balance"])
        events[datetime.fromisoformat(point["time"]).date()] += current - previous
        previous = current
    days = (end - start).days + 1
    returns = np.zeros(days, dtype=float)
    balances = np.empty(days + 1, dtype=float)
    balances[0] = STARTING_BALANCE
    for offset in range(days):
        prior = balances[offset]
        delta = events[start + timedelta(days=offset)]
        returns[offset] = delta / prior if prior > 0 else 0.0
        balances[offset + 1] = prior + delta
    return returns, balances


def bootstrap(returns: np.ndarray, offset: int) -> tuple[dict, np.ndarray]:
    rng = np.random.default_rng(SEED + offset)
    block = min(BLOCK_DAYS, len(returns))
    blocks = math.ceil(len(returns) / block)
    starts = rng.integers(0, len(returns) - block + 1, size=(PATHS, blocks))
    indices = (starts[:, :, None] + np.arange(block)).reshape(PATHS, -1)[:, : len(returns)]
    sampled = returns[indices]
    paths = STARTING_BALANCE * np.cumprod(1.0 + sampled, axis=1)
    full = np.concatenate([np.full((PATHS, 1), STARTING_BALANCE), paths], axis=1)
    peaks = np.maximum.accumulate(full, axis=1)
    max_dd = np.max((peaks - full) / peaks, axis=1) * 100.0
    final_return = (paths[:, -1] / STARTING_BALANCE - 1.0) * 100.0
    result = {
        "paths": PATHS,
        "block_days": block,
        "probability_profit_pct": float(np.mean(final_return > 0) * 100),
        "probability_loss_pct": float(np.mean(final_return < 0) * 100),
        "probability_10pct_dd_pct": float(np.mean(max_dd >= 10) * 100),
        "probability_20pct_dd_pct": float(np.mean(max_dd >= 20) * 100),
        "probability_ruin_pct": float(np.mean(np.min(full, axis=1) <= 0) * 100),
        "return_p05_pct": float(np.percentile(final_return, 5)),
        "return_p50_pct": float(np.percentile(final_return, 50)),
        "return_p95_pct": float(np.percentile(final_return, 95)),
        "max_dd_p50_pct": float(np.percentile(max_dd, 50)),
        "max_dd_p95_pct": float(np.percentile(max_dd, 95)),
    }
    return result, np.percentile(paths, [5, 25, 50, 75, 95], axis=0)


def metric_table(rows: dict[str, dict]) -> str:
    lines = [
        "| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case in CASES:
        row = rows[case]
        lines.append(
            f"| {LABELS[case]} | {float(row['return_pct']):+.2f}% | "
            f"{float(row['profit_factor']):.2f} | {float(row['win_rate_pct']):.2f}% | "
            f"{float(row['max_drawdown_pct']):.2f}% | {int(row['trades'])} | "
            f"{float(row['sharpe_ratio']):.2f} | {float(row['recovery_factor']):.2f} |"
        )
    return "\n".join(lines)


def make_chart(development, locked, three, balances, monte, fans) -> Path:
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), dpi=170)
    fig.patch.set_facecolor("#07110f")
    for axis in axes.flat:
        axis.set_facecolor("#0b1714")
        axis.grid(color="#94a3b8", alpha=0.14)
        axis.spines[["top", "right"]].set_visible(False)

    ax = axes[0, 0]
    for case in CASES:
        ax.plot(balances[case], color=COLORS[case], linewidth=1.35, label=LABELS[case])
    ax.set_title("Exact three-year MT5 balance", loc="left", fontweight="bold")
    ax.set_ylabel("USD")
    ax.set_xlabel("Calendar days")
    ax.legend(fontsize=7, frameon=False)

    ax = axes[0, 1]
    x = np.arange(len(CASES))
    width = 0.25
    ax.bar(x - width, [development[c]["return_pct"] for c in CASES], width, color="#38bdf8", label="Development")
    ax.bar(x, [locked[c]["return_pct"] for c in CASES], width, color="#6ee7b7", label="Locked year")
    ax.bar(x + width, [three[c]["return_pct"] for c in CASES], width, color="#fbbf24", label="Three years")
    ax.axhline(0, color="#cbd5e1", linewidth=0.7)
    ax.set_xticks(x, ["Previous", "Recommended", "Full Safe", "ATR 2.5R", "Fixed 15"])
    ax.set_ylabel("Return (%)")
    ax.set_title("Stability across test windows", loc="left", fontweight="bold")
    ax.legend(fontsize=8, frameon=False)

    recommended = "manage-dynamic6020-only"
    ax = axes[1, 0]
    fan = fans[recommended]
    fx = np.arange(1, fan.shape[1] + 1)
    ax.fill_between(fx, fan[0], fan[4], color=COLORS[recommended], alpha=0.15, label="5–95%")
    ax.fill_between(fx, fan[1], fan[3], color=COLORS[recommended], alpha=0.28, label="25–75%")
    ax.plot(fx, fan[2], color=COLORS[recommended], linewidth=1.8, label="Median")
    ax.plot(balances[recommended], color="#f8fafc", linewidth=1.0, label="Observed")
    ax.set_title("Recommended Dynamic 60/20 — 10,000 paths", loc="left", fontweight="bold")
    ax.set_ylabel("USD")
    ax.set_xlabel("Calendar days")
    ax.legend(fontsize=8, frameon=False)

    ax = axes[1, 1]
    ax.bar(x - width, [monte[c]["return_p05_pct"] for c in CASES], width, color="#94a3b8", label="Return P5")
    ax.bar(x, [monte[c]["return_p50_pct"] for c in CASES], width, color=[COLORS[c] for c in CASES], label="Median return")
    ax.bar(x + width, [monte[c]["max_dd_p95_pct"] for c in CASES], width, color="#ef4444", label="P95 max DD")
    ax.axhline(0, color="#cbd5e1", linewidth=0.7)
    ax.set_xticks(x, ["Previous", "Recommended", "Full Safe", "ATR 2.5R", "Fixed 15"])
    ax.set_ylabel("Percent")
    ax.set_title("Monte Carlo downside and median", loc="left", fontweight="bold")
    ax.legend(fontsize=8, frameon=False)

    fig.suptitle("EMA3 XAUUSD — final optimization decision", fontsize=18, fontweight="bold", y=0.99)
    fig.text(
        0.5,
        0.955,
        "MT5 Every Tick · Exness XAUUSD · $10,000 · fixed 1% risk · broker costs + random delay",
        ha="center",
        color="#94a3b8",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    output = ROOT / "EMA3 XAU - FINAL DECISION AND MONTE CARLO.png"
    fig.savefig(output, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output


def main() -> None:
    development = load("Development")
    locked = load("Locked")
    three = load("ThreeYear")
    start, end = date(2023, 9, 1), date(2026, 9, 1)
    monte, balances, fans = {}, {}, {}
    output_rows = []
    for offset, case in enumerate(CASES):
        returns, balance = daily_returns(three[case], start, end)
        result, fan = bootstrap(returns, offset)
        monte[case], balances[case], fans[case] = result, balance, fan
        output_rows.append({"case": case, "label": LABELS[case], **result})

    with (ROOT / "monte-carlo-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    (ROOT / "monte-carlo-results.json").write_text(json.dumps(output_rows, indent=2), encoding="utf-8")
    chart = make_chart(development, locked, three, balances, monte, fans)

    mc_lines = [
        "| Configuration | P(profit) | Return P5 / median / P95 | Median / P95 DD | P(DD >= 20%) | Ruin |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for case in CASES:
        row = monte[case]
        mc_lines.append(
            f"| {LABELS[case]} | {row['probability_profit_pct']:.2f}% | "
            f"{row['return_p05_pct']:+.2f}% / {row['return_p50_pct']:+.2f}% / {row['return_p95_pct']:+.2f}% | "
            f"{row['max_dd_p50_pct']:.2f}% / {row['max_dd_p95_pct']:.2f}% | "
            f"{row['probability_20pct_dd_pct']:.2f}% | {row['probability_ruin_pct']:.2f}% |"
        )

    markets = []
    for case in ("market-xau", "market-xag", "market-us30", "market-us100", "market-btc", "market-gbpjpy"):
        row = development.get(case)
        if row:
            markets.append(
                f"| {row['symbol']} | {float(row['return_pct']):+.2f}% | {float(row['profit_factor']):.2f} | "
                f"{float(row['win_rate_pct']):.2f}% | {float(row['max_drawdown_pct']):.2f}% | {int(row['trades'])} |"
            )

    report = f"""# Step 7 — EMA3 XAUUSD full optimization

## Decision

Promote **XAUUSD H4, original five-bar pivot stop, 1.7R target, Dynamic 60/20 only, native trailing off, all-day entries, fixed 1% risk** as the Standard configuration.

Keep **the same exact setup plus the completed-D1 Markov gate** as Full Safe. Safe materially reduces three-year drawdown and increases PF, but it also reduces return and trade count, so it remains optional rather than the default.

The fixed-15 and ATR-1.5/2.5R variants made more historical money, but their PF and drawdown were worse. They are retained as research evidence, not deployed as the core preset.

## Development window — 2023-09-01 to 2025-08-31

{metric_table(development)}

## Untouched locked year — 2025-09-01 to 2026-09-01

{metric_table(locked)}

## Exact three years — 2023-09-01 to 2026-09-01

{metric_table(three)}

## Monte Carlo — 10,000 five-day block-bootstrap paths

{chr(10).join(mc_lines)}

## Cross-market development screen — ATR-normalized research form

| Symbol | Return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|
{chr(10).join(markets)}

EMA3 stays confined to XAUUSD. BTC was positive, but its untouched-year PF fell to 1.25 with 10.21% drawdown; XAG and GBPJPY failed, while US30 and US100 were weak.

## Implementation notes

- Risk remains 1%.
- Dynamic 60/20 moves the stop after a newly completed M15 candle closes at least 60% of the original entry-to-target path; it locks 20% of that path.
- Native R-trailing is disabled. Running both mechanisms reduced robustness.
- The signal remains H4 with the original EMA 20/50 alignment, EMA 200 six-bar slope, five-bar closing breakout and opposite five-bar extreme stop.
- Standard has the Markov gate off. Full Safe applies the separately tested gate to the same selected configuration.
- Results are historical and do not guarantee future performance.

## Artifacts

- Final chart: `{chart.name}`
- Development comparison: `EMA3 - DEVELOPMENT CONFIG COMPARISON.png`
- Locked comparison: `EMA3 - LOCKED CONFIG COMPARISON.png`
- Three-year comparison: `EMA3 - THREEYEAR CONFIG COMPARISON.png`
- Monte Carlo data: `monte-carlo-results.csv` and `monte-carlo-results.json`
"""
    report_path = ROOT / "STEP 7 - EMA3 XAU FULL OPTIMIZATION.md"
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({"chart": str(chart), "report": str(report_path), "monte_carlo": output_rows}, indent=2))


if __name__ == "__main__":
    main()
