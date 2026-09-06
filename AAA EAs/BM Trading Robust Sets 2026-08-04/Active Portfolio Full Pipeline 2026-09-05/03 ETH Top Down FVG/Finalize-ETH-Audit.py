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
REPORT_ROOT = ROOT / "Backtest Reports"
STARTING_BALANCE = 10_000.0
PATHS = 10_000
BLOCK_DAYS = 5
SEED = 20_260_905

CASE_LABELS = {
    "manage-current-dynamic5020": "Current: 3R + dynamic 50/20",
    "manage-native": "3R + native exit",
    "rr-400": "4R + native exit",
    "combo-rr4-dynamic5020": "4R + dynamic 50/20",
    "session-asia": "3R + dynamic, Asia only",
    "combo-rr4-dynamic5020-safe": "4R + dynamic 50/20, safe filter",
}

CORE_CASES = [
    "manage-current-dynamic5020",
    "manage-native",
    "rr-400",
    "combo-rr4-dynamic5020",
]

COLORS = {
    "manage-current-dynamic5020": "#10b981",
    "manage-native": "#64748b",
    "rr-400": "#f59e0b",
    "combo-rr4-dynamic5020": "#38bdf8",
    "session-asia": "#a855f7",
    "combo-rr4-dynamic5020-safe": "#ef4444",
}


def load(stage: str) -> list[dict]:
    return json.loads((REPORT_ROOT / stage / "results.json").read_text(encoding="utf-8"))


def by_case(rows: list[dict]) -> dict[str, dict]:
    return {str(row["case"]): row for row in rows}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def daily_returns(row: dict, start: date, end: date) -> tuple[np.ndarray, np.ndarray]:
    events: defaultdict[date, float] = defaultdict(float)
    series = row.get("series") or []
    previous = float(series[0]["balance"]) if series else STARTING_BALANCE
    for point in series[1:]:
        current = float(point["balance"])
        events[parse_time(point["time"]).date()] += current - previous
        previous = current

    count = (end - start).days + 1
    returns = np.zeros(count, dtype=float)
    balances = np.empty(count + 1, dtype=float)
    balances[0] = STARTING_BALANCE
    for index in range(count):
        day = start + timedelta(days=index)
        prior = balances[index]
        delta = events[day]
        returns[index] = delta / prior if prior > 0 else 0.0
        balances[index + 1] = prior + delta
    return returns, balances


def bootstrap(returns: np.ndarray, seed_offset: int) -> tuple[dict, np.ndarray]:
    rng = np.random.default_rng(SEED + seed_offset)
    block = min(BLOCK_DAYS, len(returns))
    blocks_needed = math.ceil(len(returns) / block)
    starts = rng.integers(0, len(returns) - block + 1, size=(PATHS, blocks_needed))
    offsets = np.arange(block)
    indices = (starts[:, :, None] + offsets).reshape(PATHS, -1)[:, : len(returns)]
    sampled = returns[indices]
    paths = STARTING_BALANCE * np.cumprod(1.0 + sampled, axis=1)
    with_initial = np.concatenate([np.full((PATHS, 1), STARTING_BALANCE), paths], axis=1)
    peaks = np.maximum.accumulate(with_initial, axis=1)
    drawdowns = np.divide(peaks - with_initial, peaks, out=np.zeros_like(peaks), where=peaks > 0)
    maximum_drawdowns = np.max(drawdowns, axis=1) * 100.0
    final_returns = (paths[:, -1] / STARTING_BALANCE - 1.0) * 100.0
    summary = {
        "paths": PATHS,
        "block_days": block,
        "probability_profit_pct": float(np.mean(final_returns > 0.0) * 100.0),
        "probability_loss_pct": float(np.mean(final_returns < 0.0) * 100.0),
        "probability_10pct_dd_pct": float(np.mean(maximum_drawdowns >= 10.0) * 100.0),
        "probability_20pct_dd_pct": float(np.mean(maximum_drawdowns >= 20.0) * 100.0),
        "probability_ruin_pct": float(np.mean(np.min(with_initial, axis=1) <= 0.0) * 100.0),
        "return_p05_pct": float(np.percentile(final_returns, 5)),
        "return_p50_pct": float(np.percentile(final_returns, 50)),
        "return_p95_pct": float(np.percentile(final_returns, 95)),
        "max_dd_p50_pct": float(np.percentile(maximum_drawdowns, 50)),
        "max_dd_p95_pct": float(np.percentile(maximum_drawdowns, 95)),
    }
    fan = np.percentile(paths, [5, 25, 50, 75, 95], axis=0)
    return summary, fan


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def stage_table(stage_rows: dict[str, dict], cases: list[str]) -> str:
    lines = [
        "| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case in cases:
        row = stage_rows[case]
        lines.append(
            f"| {CASE_LABELS[case]} | {float(row['return_pct']):+.2f}% | "
            f"{float(row['profit_factor']):.2f} | {float(row['win_rate_pct']):.2f}% | "
            f"{float(row['max_drawdown_pct']):.2f}% | {int(row['trades'])} | "
            f"{float(row['sharpe_ratio']):.2f} | {float(row['recovery_factor']):.2f} |"
        )
    return "\n".join(lines)


def make_decision_chart(
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

    axis = axes[0, 0]
    for case in CORE_CASES:
        curve = balances[case]
        axis.plot(np.arange(len(curve)), curve, color=COLORS[case], linewidth=1.6, label=CASE_LABELS[case])
    axis.set_title("Exact 3-year MT5 equity", loc="left", fontweight="bold")
    axis.set_ylabel("Balance (USD)")
    axis.set_xlabel("Calendar days")
    axis.legend(fontsize=8, frameon=False)

    axis = axes[0, 1]
    cases = CORE_CASES
    x = np.arange(len(cases))
    returns = [float(three[c]["return_pct"]) for c in cases]
    dds = [float(three[c]["max_drawdown_pct"]) for c in cases]
    width = 0.36
    axis.bar(x - width / 2, returns, width, color=[COLORS[c] for c in cases], alpha=0.92, label="Return")
    axis.bar(x + width / 2, dds, width, color="#ef4444", alpha=0.72, label="Max DD")
    axis.set_xticks(x, ["Current\n3R dyn", "3R\nnative", "4R\nnative", "4R\ndyn"])
    axis.set_ylabel("Percent")
    axis.set_title("Return versus drawdown", loc="left", fontweight="bold")
    axis.legend(frameon=False)

    axis = axes[1, 0]
    candidate = "combo-rr4-dynamic5020"
    fan = fans[candidate]
    fx = np.arange(1, fan.shape[1] + 1)
    axis.fill_between(fx, fan[0], fan[4], color=COLORS[candidate], alpha=0.15, label="5–95%")
    axis.fill_between(fx, fan[1], fan[3], color=COLORS[candidate], alpha=0.28, label="25–75%")
    axis.plot(fx, fan[2], color=COLORS[candidate], linewidth=1.8, label="Median")
    axis.plot(np.arange(len(balances[candidate])), balances[candidate], color="#f8fafc", linewidth=1.1, label="Observed")
    axis.set_title("Recommended 4R dynamic — 10,000-path Monte Carlo", loc="left", fontweight="bold")
    axis.set_ylabel("Balance (USD)")
    axis.set_xlabel("Calendar days")
    axis.legend(frameon=False, fontsize=8)

    axis = axes[1, 1]
    p5 = [monte[c]["return_p05_pct"] for c in cases]
    med = [monte[c]["return_p50_pct"] for c in cases]
    p95dd = [monte[c]["max_dd_p95_pct"] for c in cases]
    width = 0.25
    axis.bar(x - width, p5, width, color="#94a3b8", label="Return P5")
    axis.bar(x, med, width, color=[COLORS[c] for c in cases], label="Median return")
    axis.bar(x + width, p95dd, width, color="#ef4444", label="P95 max DD")
    axis.axhline(0.0, color="#cbd5e1", linewidth=0.7)
    axis.set_xticks(x, ["Current\n3R dyn", "3R\nnative", "4R\nnative", "4R\ndyn"])
    axis.set_ylabel("Percent")
    axis.set_title("Monte Carlo downside and median", loc="left", fontweight="bold")
    axis.legend(frameon=False, fontsize=8)

    fig.suptitle("ETH Top Down FVG — Step 9.3 final decision", fontsize=18, fontweight="bold", y=0.99)
    fig.text(
        0.5,
        0.955,
        "MT5 Every Tick · Exness ETHUSD M15 · broker costs + random execution delay · $10,000 · fixed 1% risk",
        ha="center",
        color="#94a3b8",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    output = ROOT / "ETH TOP DOWN FVG - FINAL DECISION AND MONTE CARLO.png"
    fig.savefig(output, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output


def make_report(
    development: dict[str, dict],
    locked: dict[str, dict],
    three: dict[str, dict],
    monte: dict[str, dict],
) -> Path:
    rr_cases = [f"rr-{value}" for value in ["050", "075", "100", "125", "150", "200", "250", "300", "400", "500"]]
    stop_cases = [
        "stop-b002-min020", "stop-b005-min030", "stop-b010-min030", "stop-b010-min050",
        "stop-b015-min050", "stop-b025-min050", "stop-b020-min075",
    ]
    management_cases = [
        "manage-native", "manage-current-dynamic5020", "manage-be050", "manage-be100", "manage-be150",
        "manage-hold48", "manage-hold192", "manage-dynamic6020", "manage-dynamic7525",
    ]
    session_cases = ["session-all", "session-asia", "session-london", "session-new-york", "session-overlap"]
    locked_cases = [
        "manage-current-dynamic5020", "manage-native", "rr-400", "combo-rr4-dynamic5020",
        "stop-b025-min050", "combo-stop025-dynamic5020", "combo-rr4-stop025-native",
        "combo-rr4-stop025-dynamic5020", "combo-rr4-dynamic5020-safe", "combo-rr4-stop025-safe",
        "session-all", "session-asia", "session-london", "session-new-york", "session-overlap",
    ]
    three_cases = [
        "manage-current-dynamic5020", "manage-native", "rr-400", "combo-rr4-dynamic5020", "session-asia", "combo-rr4-dynamic5020-safe",
    ]

    def compact_table(rows: dict[str, dict], cases: list[str], labels: dict[str, str] | None = None) -> str:
        lines = [
            "| Test | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for case in cases:
            row = rows[case]
            label = labels.get(case, case) if labels else case
            lines.append(
                f"| {label} | {float(row['return_pct']):+.2f}% | {float(row['profit_factor']):.2f} | "
                f"{float(row['win_rate_pct']):.2f}% | {float(row['max_drawdown_pct']):.2f}% | "
                f"{int(row['trades'])} | {float(row['sharpe_ratio']):.2f} | {float(row['recovery_factor']):.2f} |"
            )
        return "\n".join(lines)

    rr_labels = {case: f"{float(case.split('-')[1]) / 100:.2f}R" for case in rr_cases}
    stop_labels = {
        "stop-b002-min020": "buffer 0.02 / min 0.20 ATR",
        "stop-b005-min030": "buffer 0.05 / min 0.30 ATR",
        "stop-b010-min030": "current: buffer 0.10 / min 0.30 ATR",
        "stop-b010-min050": "buffer 0.10 / min 0.50 ATR",
        "stop-b015-min050": "buffer 0.15 / min 0.50 ATR",
        "stop-b025-min050": "buffer 0.25 / min 0.50 ATR",
        "stop-b020-min075": "buffer 0.20 / min 0.75 ATR",
    }
    management_labels = {
        "manage-native": "native exit, no dynamic/BE",
        "manage-current-dynamic5020": "current dynamic: 50% close -> 20% SL",
        "manage-be050": "break-even at 0.5R",
        "manage-be100": "break-even at 1.0R",
        "manage-be150": "break-even at 1.5R",
        "manage-hold48": "48-bar maximum hold",
        "manage-hold192": "192-bar maximum hold",
        "manage-dynamic6020": "dynamic 60% -> 20% SL",
        "manage-dynamic7525": "dynamic 75% -> 25% SL",
    }
    session_labels = {
        "session-all": "all day",
        "session-asia": "Asia 00:00–08:00 UTC",
        "session-london": "London 07:00–12:00 UTC",
        "session-new-york": "New York 13:00–21:00 UTC",
        "session-overlap": "London/NY overlap 13:00–16:00 UTC",
    }

    mc_lines = [
        "| Configuration | P(profit) | Return P5 / median / P95 | Median / P95 max DD | P(DD >= 10%) | Ruin |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for case in three_cases:
        row = monte[case]
        mc_lines.append(
            f"| {CASE_LABELS[case]} | {row['probability_profit_pct']:.2f}% | "
            f"{row['return_p05_pct']:+.2f}% / {row['return_p50_pct']:+.2f}% / {row['return_p95_pct']:+.2f}% | "
            f"{row['max_dd_p50_pct']:.2f}% / {row['max_dd_p95_pct']:.2f}% | "
            f"{row['probability_10pct_dd_pct']:.2f}% | {row['probability_ruin_pct']:.2f}% |"
        )

    locked_labels = {**CASE_LABELS, **stop_labels, **session_labels}

    report = f"""# Step 9.3 — ETH Top Down FVG Re-audit

## Goal and test controls

Independently re-test the active ETHUSD M15 strategy at a fixed 1% risk per trade. The audit covers reward/risk from 0.5R to 5R, stop placement, exit management, sessions, the safe regime filter, an untouched locked year, an exact three-year Every Tick validation, and a 10,000-path five-calendar-day block-bootstrap Monte Carlo.

- Broker/tester: Exness MT5, ETHUSD M15.
- Costs: broker spread, commission/swap from the tester and random execution delay.
- Development window: 2023-09-01 through 2025-08-31. This is where alternatives were compared.
- Locked window: 2025-09-01 through 2026-09-01. No further selection was allowed after seeing this window.
- Exact full window: 2023-09-01 through 2026-09-01, MT5 Every Tick.
- Starting balance: $10,000; leverage 1:2000; risk fixed at 1%.

## Decision

**Recommended research upgrade: 4R target, dynamic 50/20 management, all-day entries, current stop (0.10 ATR buffer / 0.30 ATR minimum), safe filter off.**

The raw 4R native exit has the highest exact three-year return (+24.42%), but 4R dynamic is the better consistency choice. It returns +21.77% with PF 1.72, 43.18% wins, 6.68% max drawdown, Sharpe 7.28 and recovery 2.87. It also wins the untouched locked year (+11.41%, PF 1.65) and improves the Monte Carlo 5th-percentile return from -1.06% to -0.57%, while reducing P95 drawdown from 13.67% to 12.05%. The current 3R dynamic setup remains credible and has the highest exact Sharpe (7.44) and win rate (48.89%). The approved 4R upgrade is now deployed, but should still be treated as a demo-forward-test candidate because of the low sample.

The evidence is **cautious**, not strong: only 44–45 trades occur in three years. Tiny session subsets and the very high native Sharpe values must not be treated as precise forecasts.

## Main side-by-side — exact three-year Every Tick

{stage_table(three, CORE_CASES)}

## Monte Carlo — exact three-year daily return blocks

The simulation resamples 5-calendar-day blocks, including inactive days, 10,000 times. It estimates sequence risk from the available history; it cannot prove the strategy will persist.

{chr(10).join(mc_lines)}

## Development: reward/risk sweep

{compact_table(development, rr_cases, rr_labels)}

The development curve favored 4R. At 5R, return and PF weakened and drawdown rose, which is why the search stopped at 4R for the locked finalists.

## Development: stop placement

{compact_table(development, stop_cases, stop_labels)}

The 0.25/0.50 ATR stop appeared superior in development, but failed the locked test: it reduced returns and materially increased drawdown in the 4R native combination. Therefore the current 0.10/0.30 ATR stop is retained.

## Development: exit and trailing management

{compact_table(development, management_cases, management_labels)}

Dynamic 50/20 improves win rate but clips some payoff. Break-even at 0.5R destroys the edge. At the selected 4R target, dynamic 50/20 gives the best balance of locked-year stability and Monte Carlo downside protection.

## Development: sessions

{compact_table(development, session_cases, session_labels)}

London and overlap look attractive only because they contain 2 and 4 trades respectively. Those samples are unusably small. All-day is the only defensible default.

## Locked-year finalists

{compact_table(locked, locked_cases, locked_labels)}

The locked year rejects the wider stop and safe-filter combinations. The 4R dynamic finalist is strongest here at +11.41% with PF 1.65, while 4R native produces +10.31% with PF 1.52. This is why the final choice uses both the exact three-year result and the Monte Carlo downside view rather than selecting the highest historical return alone.

## Exact three-year finalist set

{stage_table(three, three_cases)}

## Safe mode conclusion

Safe mode is kept as an optional user control but is **not recommended as the ETH default**. On the exact three-year run, adding the completed-D1 Markov gate reduces return from +21.77% to +14.37% and trades from 44 to 28, although PF improves from 1.72 to 1.82 and max drawdown falls from 6.68% to 6.19%. On the untouched locked year it reduces return from +11.41% to +6.27%, with PF 1.51 over only 18 trades. The comparison uses the same approved 4R Dynamic 50/20 base on both sides; no older 3R evidence is used.

## Deployment status

The user approved this recommendation. The shared selected preset used by Standard, Full Safe, Best Recommended, 100K, 900 and Dynamic Config BAT flows now uses 4R with Dynamic 50/20. The website default and locked evidence mapping were updated to the same configuration. Full Safe preserves the 4R/Dynamic 50/20 setup and independently enables the completed-D1 Markov gate.
"""
    output = ROOT / "STEP 9.3 - ETH TOP DOWN FVG REAUDIT.md"
    output.write_text(report, encoding="utf-8")
    return output


def main() -> None:
    development = by_case(load("Development"))
    locked = by_case(load("Locked"))
    three = by_case(load("ThreeYear"))

    start = date(2023, 9, 1)
    end = date(2026, 9, 1)
    monte: dict[str, dict] = {}
    balances: dict[str, np.ndarray] = {}
    fans: dict[str, np.ndarray] = {}
    rows: list[dict] = []
    for index, case in enumerate(CASE_LABELS):
        returns, balance = daily_returns(three[case], start, end)
        summary, fan = bootstrap(returns, index)
        monte[case] = summary
        balances[case] = balance
        fans[case] = fan
        rows.append({"case": case, "label": CASE_LABELS[case], **summary})

    write_csv(ROOT / "monte-carlo-results.csv", rows)
    (ROOT / "monte-carlo-results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    chart = make_decision_chart(three, balances, monte, fans)
    report = make_report(development, locked, three, monte)

    print(json.dumps({"report": str(report), "chart": str(chart), "monte_carlo": rows}, indent=2))


if __name__ == "__main__":
    main()
