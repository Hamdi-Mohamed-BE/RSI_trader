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
    "current-dynamic5020": "Deployed: 2.0 gate, 0.08 buffer, dynamic 50/20, both",
    "current-native": "Current rules, native exit",
    "safe-on": "Deployed base + Safe D1 regime gate",
    "combo-rr25-stop000-dyn6020-long": "2.5 gate, 0.00 buffer, dynamic 60/20, long",
    "combo-rr25-stop003-dyn6020": "2.5 gate, 0.03 buffer, dynamic 60/20, both",
    "combo-rr25-stop003-dyn6020-safe": "2.5 gate, 0.03 buffer, dynamic 60/20, both + Safe",
    "combo-rr25-stop003-dyn6020-long": "2.5 gate, 0.03 buffer, dynamic 60/20, long",
    "combo-rr25-stop003-dyn6020-long-safe": "2.5 gate, 0.03 buffer, dynamic 60/20, long + Safe",
}

CORE = [
    "current-dynamic5020",
    "combo-rr25-stop003-dyn6020",
    "combo-rr25-stop003-dyn6020-long",
    "combo-rr25-stop003-dyn6020-long-safe",
]

COLORS = {
    "current-dynamic5020": "#94a3b8",
    "combo-rr25-stop003-dyn6020": "#38bdf8",
    "combo-rr25-stop003-dyn6020-long": "#34d399",
    "combo-rr25-stop003-dyn6020-long-safe": "#a78bfa",
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


def table(rows: dict[str, dict], cases: list[str]) -> str:
    lines = [
        "| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case in cases:
        row = rows[case]
        lines.append(
            f"| {LABELS.get(case, case)} | {float(row['return_pct']):+.2f}% | "
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
        ax.plot(balances[case], color=COLORS[case], linewidth=1.55, label=LABELS[case])
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
           color="#ef4444", alpha=0.75, label="Max DD")
    ax.set_xticks(x, ["Current", "New both", "New long", "New long\nSafe"])
    ax.set_ylabel("Percent")
    ax.set_title("Return versus drawdown", loc="left", fontweight="bold")
    ax.legend(frameon=False)

    recommended = "combo-rr25-stop003-dyn6020-long"
    ax = axes[1, 0]
    fan = fans[recommended]
    fx = np.arange(1, fan.shape[1] + 1)
    ax.fill_between(fx, fan[0], fan[4], color=COLORS[recommended], alpha=0.15, label="5–95%")
    ax.fill_between(fx, fan[1], fan[3], color=COLORS[recommended], alpha=0.28, label="25–75%")
    ax.plot(fx, fan[2], color=COLORS[recommended], linewidth=1.8, label="Median")
    ax.plot(balances[recommended], color="#f8fafc", linewidth=1.0, label="Observed")
    ax.set_title("Recommended long — 10,000-path block Monte Carlo", loc="left", fontweight="bold")
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
    ax.set_xticks(x, ["Current", "New both", "New long", "New long\nSafe"])
    ax.set_ylabel("Percent")
    ax.set_title("Monte Carlo downside and median", loc="left", fontweight="bold")
    ax.legend(fontsize=8, frameon=False)

    fig.suptitle("Engineered Liquidity XAU — Step 9.4 decision", fontsize=18, fontweight="bold", y=0.99)
    fig.text(0.5, 0.955, "MT5 Every Tick · Exness XAUUSD H1 · real broker costs and random delay · $10,000 · fixed 1% risk",
             ha="center", color="#94a3b8", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    output = ROOT / "ENGINEERED LIQUIDITY XAU - FINAL DECISION AND MONTE CARLO.png"
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
    for offset, case in enumerate(LABELS):
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

    locked_cases = [case for case in LABELS if case in locked]
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

    rr = [f"rr-{value}" for value in ["050", "075", "100", "125", "150", "200", "250", "300", "400", "500"]]
    stops = [f"stop-buffer-{value}" for value in ["000", "003", "005", "008", "012", "020", "030"]]
    management = ["manage-native", "manage-dynamic5020", "manage-dynamic5010", "manage-dynamic5030", "manage-dynamic6020", "manage-dynamic7525"]
    sessions = ["session-all", "session-asia", "session-london", "session-new-york", "session-overlap"]
    directions = ["direction-both", "direction-long-only", "direction-short-only"]

    report = f"""# Step 9.4 — Engineered Liquidity XAU Re-audit

## Goal and controls

Re-test the active XAUUSD H1 strategy at a fixed 1% risk using broker-cost-inclusive MT5 evidence. Development used 2023-09-01 through 2025-08-31; the untouched locked year used 2025-09-01 through 2026-09-01; final validation used exact three-year Every Tick history. Monte Carlo uses 10,000 five-calendar-day block-bootstrap paths.

## Recommendation

**Research recommendation: 2.5 minimum setup-RR gate, 0.03 ATR structural-stop buffer, Dynamic 60/20, long-only, all day, 24-bar maximum hold, two trades/day, fixed 1% risk.** Keep Safe as an optional per-EA switch, off by default.

This is not a literal 2.5R take-profit: the EA targets opposing liquidity and rejects entries whose projected target is below 2.5R. The 0.03 buffer is preferred to the zero-buffer development winner because it held up better in the untouched year. Long-only materially improves three-year PF and drawdown, but it remains exposed to a change in gold's long-term regime; Safe improves PF further while cutting trades and return.

No BAT, selected preset, EA binary, or website record was changed during this audit. Deployment remains pending user approval.

## Untouched locked-year MT5 results

{table(locked, locked_cases)}

## Exact three-year Every Tick results

{table(three, list(LABELS))}

## Monte Carlo

{chr(10).join(mc_lines)}

## Development — minimum projected RR gate

{table(development, rr)}

## Development — stop buffer

{table(development, stops)}

## Development — management

{table(development, management)}

## Development — sessions

{table(development, sessions)}

## Development — direction

{table(development, directions)}

## Interpretation

- All day is retained. London-only raised PF but left only 38 development trades and much less return; New York and overlap failed.
- Dynamic 60/20 means that after a completed M15 candle reaches 60% of the original path to target, the stop locks 20% of that path. It beat native and Dynamic 50/20 in development.
- Safe is a completed-D1 Markov regime gate layered onto this EA alone, with no look-ahead. It is useful as a cautious option, not the Standard default.
- The short side was negative in development; the long-only recommendation is evidence-driven, but requires demo forward monitoring because directional edges can be regime-dependent.
- Historical and simulated results are not a promise of future profit.
"""
    report_path = ROOT / "STEP 9.4 - ENGINEERED LIQUIDITY XAU REAUDIT.md"
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({"report": str(report_path), "chart": str(chart), "monte_carlo": output_rows}, indent=2))


if __name__ == "__main__":
    main()
