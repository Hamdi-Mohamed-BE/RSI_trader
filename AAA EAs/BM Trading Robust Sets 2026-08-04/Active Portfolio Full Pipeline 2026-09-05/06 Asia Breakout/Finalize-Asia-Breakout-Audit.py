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

LABELS = {
    "final-current-safe": "Current: midpoint, 3R, native + Dynamic 50/20, Safe",
    "final-current-standard": "Current rules, Safe off",
    "combo-opposite003-safe": "Opposite edge + 3% buffer, Safe",
    "combo-opposite010-buffer000-safe": "Opposite edge + 10%, zero breakout buffer, Safe",
    "combo-opposite010-window0812-safe": "Opposite edge + 10%, 08:00–12:00, Safe",
}
CORE = list(LABELS)
COLORS = {
    "final-current-safe": "#6ee7b7",
    "final-current-standard": "#94a3b8",
    "combo-opposite003-safe": "#38bdf8",
    "combo-opposite010-buffer000-safe": "#a78bfa",
    "combo-opposite010-window0812-safe": "#fbbf24",
}


def load(stage: str) -> list[dict]:
    return json.loads((REPORTS / stage / "results.json").read_text(encoding="utf-8"))


def indexed(rows: list[dict]) -> dict[str, dict]:
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
        day = start + timedelta(days=offset)
        prior = balances[offset]
        delta = events[day]
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


def table(rows: dict[str, dict], cases: list[str], labels: dict[str, str] | None = None) -> str:
    labels = labels or LABELS
    lines = [
        "| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case in cases:
        if case not in rows:
            continue
        row = rows[case]
        lines.append(
            f"| {labels.get(case, case)} | {float(row['return_pct']):+.2f}% | "
            f"{float(row['profit_factor']):.2f} | {float(row['win_rate_pct']):.2f}% | "
            f"{float(row['max_drawdown_pct']):.2f}% | {int(row['trades'])} | "
            f"{float(row['sharpe_ratio']):.2f} | {float(row['recovery_factor']):.2f} |"
        )
    return "\n".join(lines)


def make_chart(three: dict[str, dict], balances: dict[str, np.ndarray], monte: dict[str, dict], fans: dict[str, np.ndarray]) -> Path:
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), dpi=170)
    fig.patch.set_facecolor("#07110f")
    for axis in axes.flat:
        axis.set_facecolor("#0b1714")
        axis.grid(color="#94a3b8", alpha=0.14)
        axis.spines[["top", "right"]].set_visible(False)

    ax = axes[0, 0]
    for case in CORE:
        ax.plot(balances[case], color=COLORS[case], linewidth=1.5, label=LABELS[case])
    ax.set_title("Exact three-year MT5 balance", loc="left", fontweight="bold")
    ax.set_ylabel("USD")
    ax.set_xlabel("Calendar days")
    ax.legend(fontsize=7, frameon=False)

    ax = axes[0, 1]
    x = np.arange(len(CORE))
    width = 0.36
    ax.bar(x - width / 2, [three[c]["return_pct"] for c in CORE], width,
           color=[COLORS[c] for c in CORE], label="Return")
    ax.bar(x + width / 2, [three[c]["max_drawdown_pct"] for c in CORE], width,
           color="#ef4444", alpha=0.78, label="Max DD")
    ax.set_xticks(x, ["Current\nSafe", "Current\nStandard", "Opp. 3%\nSafe", "Opp. 10%\n0 buffer", "Opp. 10%\n08–12"])
    ax.set_ylabel("Percent")
    ax.set_title("Return versus drawdown", loc="left", fontweight="bold")
    ax.legend(frameon=False)

    recommended = "final-current-safe"
    ax = axes[1, 0]
    fan = fans[recommended]
    fx = np.arange(1, fan.shape[1] + 1)
    ax.fill_between(fx, fan[0], fan[4], color=COLORS[recommended], alpha=0.15, label="5–95%")
    ax.fill_between(fx, fan[1], fan[3], color=COLORS[recommended], alpha=0.28, label="25–75%")
    ax.plot(fx, fan[2], color=COLORS[recommended], linewidth=1.8, label="Median")
    ax.plot(balances[recommended], color="#f8fafc", linewidth=1.0, label="Observed")
    ax.set_title("Recommended current Safe — 10,000 paths", loc="left", fontweight="bold")
    ax.set_ylabel("USD")
    ax.set_xlabel("Calendar days")
    ax.legend(fontsize=8, frameon=False)

    ax = axes[1, 1]
    width = 0.25
    ax.bar(x - width, [monte[c]["return_p05_pct"] for c in CORE], width, color="#94a3b8", label="Return P5")
    ax.bar(x, [monte[c]["return_p50_pct"] for c in CORE], width,
           color=[COLORS[c] for c in CORE], label="Median return")
    ax.bar(x + width, [monte[c]["max_dd_p95_pct"] for c in CORE], width, color="#ef4444", label="P95 max DD")
    ax.axhline(0, color="#cbd5e1", linewidth=0.7)
    ax.set_xticks(x, ["Current\nSafe", "Current\nStandard", "Opp. 3%\nSafe", "Opp. 10%\n0 buffer", "Opp. 10%\n08–12"])
    ax.set_ylabel("Percent")
    ax.set_title("Monte Carlo downside and median", loc="left", fontweight="bold")
    ax.legend(fontsize=8, frameon=False)

    fig.suptitle("Asia Breakout XAU — Step 9.6 decision", fontsize=18, fontweight="bold", y=0.99)
    fig.text(0.5, 0.955, "MT5 Every Tick · Exness XAUUSD · $10,000 · fixed 1% risk · broker costs + random delay",
             ha="center", color="#94a3b8", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    output = ROOT / "ASIA BREAKOUT XAU - FINAL DECISION AND MONTE CARLO.png"
    fig.savefig(output, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output


def main() -> None:
    development = indexed(load("Development"))
    locked = indexed(load("Locked"))
    three = indexed(load("ThreeYear"))
    start, end = date(2023, 9, 1), date(2026, 9, 1)
    monte: dict[str, dict] = {}
    balances: dict[str, np.ndarray] = {}
    fans: dict[str, np.ndarray] = {}
    output_rows: list[dict] = []
    for offset, case in enumerate(CORE):
        returns, balance = daily_returns(three[case], start, end)
        result, fan = bootstrap(returns, offset)
        monte[case], balances[case], fans[case] = result, balance, fan
        output_rows.append({"case": case, "label": LABELS[case], **result})

    with (ROOT / "monte-carlo-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    (ROOT / "monte-carlo-results.json").write_text(json.dumps(output_rows, indent=2), encoding="utf-8")
    chart = make_chart(three, balances, monte, fans)

    mc_lines = [
        "| Configuration | P(profit) | Return P5 / median / P95 | Median / P95 DD | P(DD ≥10%) | P(DD ≥20%) | Ruin |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in CORE:
        row = monte[case]
        mc_lines.append(
            f"| {LABELS[case]} | {row['probability_profit_pct']:.2f}% | "
            f"{row['return_p05_pct']:+.2f}% / {row['return_p50_pct']:+.2f}% / {row['return_p95_pct']:+.2f}% | "
            f"{row['max_dd_p50_pct']:.2f}% / {row['max_dd_p95_pct']:.2f}% | "
            f"{row['probability_10pct_dd_pct']:.2f}% | {row['probability_20pct_dd_pct']:.2f}% | "
            f"{row['probability_ruin_pct']:.2f}% |"
        )

    groups = [
        ("Reward-risk sweep", "reward-risk"),
        ("Stop placement", "stop"),
        ("Trade management", "management"),
        ("Session filter", "session"),
        ("Signal timeframe", "timeframe"),
        ("Entry window", "entry-window"),
        ("Safe filter", "safe-filter"),
        ("Focused combinations", "combined-finalist"),
    ]
    sections = []
    dev_rows = list(development.values())
    for title, group in groups:
        cases = [str(row["case"]) for row in dev_rows if row["group"] == group]
        sections.append(f"## Development — {title}\n\n{table(development, cases, {})}")

    report = f"""# Step 9.6 — Asia Breakout XAU Re-audit

## Goal and controls

Re-test the active XAUUSD Asia-session breakout at fixed 1% risk using its actual MT5 logic, broker costs and random execution delay. Development used 2023-09-01 through 2025-08-31. The untouched locked year used 2025-09-01 through 2026-09-01. Final validation used exact three-year Every Tick history. Monte Carlo uses 10,000 five-calendar-day block-bootstrap paths.

## Decision

**Keep the currently deployed optimized Safe configuration unchanged:** XAUUSD H1, 3R, Asia range 00:00–08:00 UTC, entries 08:00–13:00 UTC, 3% breakout buffer, midpoint stop, native 2R/0.5R trail plus Dynamic 50/20, all-day wrapper, completed-D1 no-lookahead Markov Safe gate, and fixed 1% risk.

It led the untouched year (+32.07%, PF 1.76, 5.67% DD, 73 trades) and the full three years (+44.57%, PF 1.56, 6.27% DD, 130 trades). The alternative opposite-edge stops improved development and slightly improved full-period PF, but failed to beat the current setup on the locked year. Signal-candle stops were clearly harmful. H1 remained preferable to M30/M15. The London wrapper produced only 35 development trades and is not adopted.

No BAT, selected preset, live EA binary, or website record was changed. The existing installed selection already matches the recommendation.

## Untouched locked-year MT5 results

{table(locked, CORE)}

## Exact three-year Every Tick results

{table(three, CORE)}

## Monte Carlo

{chr(10).join(mc_lines)}

{chr(10).join(sections)}

## Interpretation

- Safe mode is essential for this EA in the tested history; disabling it raised trade count but sharply degraded PF and drawdown.
- The apparent development gain from moving the stop to the opposite Asia edge did not persist in the locked year.
- Dynamic 50/20 should remain combined with the EA's native 2R/0.5R trailing behavior because that exact installed combination won the independent validation.
- Results are historical and do not guarantee future performance. The Safe filter is a completed-D1 gate and does not use future bars.

## Artifacts

- Final chart: `{chart.name}`
- Development comparison: `ASIA BREAKOUT XAU - DEVELOPMENT CONFIG COMPARISON.png`
- Locked comparison: `ASIA BREAKOUT XAU - LOCKED CONFIG COMPARISON.png`
- Three-year comparison: `ASIA BREAKOUT XAU - THREEYEAR CONFIG COMPARISON.png`
- Monte Carlo data: `monte-carlo-results.csv` and `monte-carlo-results.json`
"""
    (ROOT / "STEP 9.6 - ASIA BREAKOUT XAU REAUDIT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"chart": str(chart), "report": str(ROOT / 'STEP 9.6 - ASIA BREAKOUT XAU REAUDIT.md'), "monte_carlo": output_rows}, indent=2))


if __name__ == "__main__":
    main()
