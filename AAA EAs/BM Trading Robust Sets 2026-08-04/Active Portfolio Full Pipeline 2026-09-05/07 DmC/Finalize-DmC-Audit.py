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
    "deployed-safe-dynamic-native",
    "combo-h1-asia-fixed-rr170",
    "combo-h1-asia-fixed-rr300",
    "combo-h1-asia-fixed-rr400",
    "combo-h1-asia-fixed-rr500",
]
LABELS = {
    "deployed-safe-dynamic-native": "Current Safe 1.7R all day",
    "combo-h1-asia-fixed-rr170": "Asia 1.7R",
    "combo-h1-asia-fixed-rr300": "Recommended Asia 3R",
    "combo-h1-asia-fixed-rr400": "Asia 4R",
    "combo-h1-asia-fixed-rr500": "Asia 5R",
}
COLORS = {
    "deployed-safe-dynamic-native": "#94a3b8",
    "combo-h1-asia-fixed-rr170": "#38bdf8",
    "combo-h1-asia-fixed-rr300": "#6ee7b7",
    "combo-h1-asia-fixed-rr400": "#fbbf24",
    "combo-h1-asia-fixed-rr500": "#a78bfa",
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
    fan = np.percentile(paths, [5, 25, 50, 75, 95], axis=0)
    return result, fan


def metric_table(rows: dict[str, dict], cases: list[str]) -> str:
    lines = [
        "| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case in cases:
        row = rows[case]
        lines.append(
            f"| {LABELS[case]} | {float(row['return_pct']):+.2f}% | "
            f"{float(row['profit_factor']):.2f} | {float(row['win_rate_pct']):.2f}% | "
            f"{float(row['max_drawdown_pct']):.2f}% | {int(row['trades'])} | "
            f"{float(row['sharpe_ratio']):.2f} | {float(row['recovery_factor']):.2f} |"
        )
    return "\n".join(lines)


def make_chart(
    development: dict[str, dict],
    locked: dict[str, dict],
    three: dict[str, dict],
    balances: dict[str, np.ndarray],
    monte: dict[str, dict],
    fans: dict[str, np.ndarray],
) -> Path:
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), dpi=170)
    fig.patch.set_facecolor("#07110f")
    for axis in axes.flat:
        axis.set_facecolor("#0b1714")
        axis.grid(color="#94a3b8", alpha=0.14)
        axis.spines[["top", "right"]].set_visible(False)

    ax = axes[0, 0]
    for case in CASES:
        ax.plot(balances[case], color=COLORS[case], linewidth=1.45, label=LABELS[case])
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
    ax.set_xticks(x, ["Current\nSafe", "Asia\n1.7R", "Asia\n3R", "Asia\n4R", "Asia\n5R"])
    ax.set_ylabel("Return (%)")
    ax.set_title("Stability across test windows", loc="left", fontweight="bold")
    ax.legend(fontsize=8, frameon=False)

    recommended = "combo-h1-asia-fixed-rr300"
    ax = axes[1, 0]
    fan = fans[recommended]
    fx = np.arange(1, fan.shape[1] + 1)
    ax.fill_between(fx, fan[0], fan[4], color=COLORS[recommended], alpha=0.15, label="5–95%")
    ax.fill_between(fx, fan[1], fan[3], color=COLORS[recommended], alpha=0.28, label="25–75%")
    ax.plot(fx, fan[2], color=COLORS[recommended], linewidth=1.8, label="Median")
    ax.plot(balances[recommended], color="#f8fafc", linewidth=1.0, label="Observed")
    ax.set_title("Recommended Asia 3R — 10,000 paths", loc="left", fontweight="bold")
    ax.set_ylabel("USD")
    ax.set_xlabel("Calendar days")
    ax.legend(fontsize=8, frameon=False)

    ax = axes[1, 1]
    ax.bar(x - width, [monte[c]["return_p05_pct"] for c in CASES], width, color="#94a3b8", label="Return P5")
    ax.bar(x, [monte[c]["return_p50_pct"] for c in CASES], width, color=[COLORS[c] for c in CASES], label="Median return")
    ax.bar(x + width, [monte[c]["max_dd_p95_pct"] for c in CASES], width, color="#ef4444", label="P95 max DD")
    ax.axhline(0, color="#cbd5e1", linewidth=0.7)
    ax.set_xticks(x, ["Current\nSafe", "Asia\n1.7R", "Asia\n3R", "Asia\n4R", "Asia\n5R"])
    ax.set_ylabel("Percent")
    ax.set_title("Monte Carlo downside and median", loc="left", fontweight="bold")
    ax.legend(fontsize=8, frameon=False)

    fig.suptitle("DmC XAUUSD — full optimization decision", fontsize=18, fontweight="bold", y=0.99)
    fig.text(
        0.5,
        0.955,
        "MT5 Every Tick · Exness XAUUSD · $10,000 · fixed 1% risk · broker costs + random delay",
        ha="center",
        color="#94a3b8",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    output = ROOT / "DMC XAU - FINAL DECISION AND MONTE CARLO.png"
    fig.savefig(output, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output


def main() -> None:
    development = load("Development")
    locked = load("Locked")
    three = load("ThreeYear")
    start, end = date(2023, 9, 1), date(2026, 9, 1)
    monte: dict[str, dict] = {}
    balances: dict[str, np.ndarray] = {}
    fans: dict[str, np.ndarray] = {}
    output_rows: list[dict] = []
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

    report = f"""# Step 6 — DmC XAUUSD full optimization

## Decision

Promote **XAUUSD H1, Asia-only, fixed $22.50 price-distance stop, 3R target, Dynamic 50/20, Safe gate off, fixed 1% risk** as the recommended DmC configuration.

The current Safe 1.7R all-day version had the better recent win rate and PF, but it lost money in the two-year development window. Asia 3R was profitable in both independent segments and produced the best three-year balance between return, drawdown and recovery. Asia 4R returned slightly more over three years, but its locked-year drawdown and Monte Carlo downside were worse.

## Development window — 2023-09-01 to 2025-08-31

{metric_table(development, CASES)}

## Untouched locked year — 2025-09-01 to 2026-09-01

{metric_table(locked, CASES)}

## Exact three years — 2023-09-01 to 2026-09-01

{metric_table(three, CASES)}

## Monte Carlo — 10,000 five-day block-bootstrap paths

{chr(10).join(mc_lines)}

## Cross-market conclusion

The portable ATR-stop form did not transfer robustly. Development results were XAU -4.64%, XAG -78.09%, US30 -31.57%, US100 -38.76%, BTC -28.56%, and GBPJPY +19.28%; GBPJPY then failed the locked year (-22.58%). Keep DmC confined to XAUUSD.

## Implementation notes

- Risk remains 1%.
- The selected setup uses Dynamic 50/20. DmC does not call the shared native R-trailing routine, so the generic native trailing input is explicitly disabled to avoid implying otherwise.
- The session wrapper is Asia only, interpreted in UTC using the broker offset input.
- Full Safe preserves the same validated Asia 3R inputs for DmC. The exact Asia 3R + Markov combination is not promoted until a dedicated tester run completes successfully.
- New portable stop/timeframe inputs remain in the EA code for future research, but the installed preset uses the original fixed stop and H1 signal.
- Results are historical and do not guarantee future performance.

## Artifacts

- Final chart: `{chart.name}`
- Development comparison: `DMC - DEVELOPMENT CONFIG COMPARISON.png`
- Locked comparison: `DMC - LOCKED CONFIG COMPARISON.png`
- Three-year comparison: `DMC - THREEYEAR CONFIG COMPARISON.png`
- Monte Carlo data: `monte-carlo-results.csv` and `monte-carlo-results.json`
"""
    report_path = ROOT / "STEP 6 - DMC XAU FULL OPTIMIZATION.md"
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({"chart": str(chart), "report": str(report_path), "monte_carlo": output_rows}, indent=2))


if __name__ == "__main__":
    main()
