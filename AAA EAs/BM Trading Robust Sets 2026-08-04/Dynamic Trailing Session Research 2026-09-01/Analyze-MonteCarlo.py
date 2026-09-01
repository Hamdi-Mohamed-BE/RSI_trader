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
STARTING_BALANCE = 10_000.0
PATHS = 10_000
BLOCK_DAYS = 5
SEED = 20_260_901
ROLE_ORDER = ["current", "dynamic-only", "best-session", "best-session-dynamic"]
ROLE_COLORS = {
    "current": "#64748b",
    "dynamic-only": "#f59e0b",
    "best-session": "#38bdf8",
    "best-session-dynamic": "#10b981",
}


def role(row: dict) -> str:
    if row["Variant"] == "current":
        return "current"
    if row["Variant"] == "dynamic-only":
        return "dynamic-only"
    return "best-session-dynamic" if row["Dynamic"] else "best-session"


def parse_day(value: str) -> date:
    return datetime.fromisoformat(value).date()


def daily_deltas(rows: list[dict]) -> tuple[list[date], np.ndarray]:
    events: defaultdict[date, float] = defaultdict(float)
    first_day: date | None = None
    last_day: date | None = None
    for row in rows:
        previous = float(row["initial_balance"])
        first_day = min(first_day, parse_day(row["series"][0]["date"])) if first_day else parse_day(row["series"][0]["date"])
        for point in row["series"][1:]:
            current = float(point["balance"])
            when = parse_day(point["date"])
            events[when] += current - previous
            previous = current
            last_day = max(last_day, when) if last_day else when
    if first_day is None:
        first_day = date(2025, 9, 1)
    if last_day is None:
        last_day = first_day + timedelta(days=364)
    count = (last_day - first_day).days + 1
    days = [first_day + timedelta(days=offset) for offset in range(count)]
    return days, np.asarray([events[day] for day in days], dtype=float)


def return_curve(deltas: np.ndarray, start: float = STARTING_BALANCE) -> tuple[np.ndarray, np.ndarray]:
    balances = np.empty(len(deltas) + 1, dtype=float)
    returns = np.zeros(len(deltas), dtype=float)
    balances[0] = start
    for index, delta in enumerate(deltas):
        previous = balances[index]
        returns[index] = delta / previous if previous > 0 else 0.0
        balances[index + 1] = previous + delta
    return returns, balances


def max_drawdown(balances: np.ndarray) -> tuple[float, float]:
    peaks = np.maximum.accumulate(balances)
    amounts = peaks - balances
    percentages = np.divide(amounts, peaks, out=np.zeros_like(amounts), where=peaks > 0)
    index = int(np.argmax(percentages))
    return float(amounts[index]), float(percentages[index] * 100.0)


def sharpe_ratio(returns: np.ndarray) -> float:
    if len(returns) < 2:
        return 0.0
    deviation = float(np.std(returns, ddof=1))
    if deviation <= 0:
        return 0.0
    return float(np.mean(returns) / deviation * math.sqrt(365.0))


def bootstrap(returns: np.ndarray, seed_offset: int) -> tuple[dict, np.ndarray]:
    if not len(returns):
        returns = np.zeros(365, dtype=float)
    rng = np.random.default_rng(SEED + seed_offset)
    block = min(BLOCK_DAYS, len(returns))
    blocks_needed = math.ceil(len(returns) / block)
    maximum_start = len(returns) - block + 1
    starts = rng.integers(0, maximum_start, size=(PATHS, blocks_needed))
    offsets = np.arange(block)
    indices = (starts[:, :, None] + offsets).reshape(PATHS, -1)[:, : len(returns)]
    sampled = returns[indices]
    paths = STARTING_BALANCE * np.cumprod(1.0 + sampled, axis=1)
    initial = np.full((PATHS, 1), STARTING_BALANCE)
    with_initial = np.concatenate([initial, paths], axis=1)
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
    percentiles = np.percentile(paths, [5, 25, 50, 75, 95], axis=0)
    return summary, percentiles


def observed_metrics(rows: list[dict]) -> tuple[dict, np.ndarray, np.ndarray]:
    days, deltas = daily_deltas(rows)
    returns, balances = return_curve(deltas)
    dd_amount, dd_pct = max_drawdown(balances)
    net = float(balances[-1] - balances[0])
    return {
        "start_date": days[0].isoformat(),
        "end_date": days[-1].isoformat(),
        "net_profit": net,
        "return_pct": net / balances[0] * 100.0,
        "realized_dd_amount": dd_amount,
        "realized_dd_pct": dd_pct,
        "sharpe_ratio": sharpe_ratio(returns),
        "recovery_factor": net / dd_amount if dd_amount > 0 else 0.0,
    }, returns, balances


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_fan_chart(portfolio: list[dict], observed: dict[str, np.ndarray], fans: dict[str, np.ndarray]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), dpi=160, sharex=True)
    for axis, target in zip(axes.flat, ROLE_ORDER):
        fan = fans[target]
        actual = observed[target]
        x = np.arange(1, fan.shape[1] + 1)
        axis.fill_between(x, fan[0], fan[4], color=ROLE_COLORS[target], alpha=0.13, label="5–95%")
        axis.fill_between(x, fan[1], fan[3], color=ROLE_COLORS[target], alpha=0.23, label="25–75%")
        axis.plot(x, fan[2], color=ROLE_COLORS[target], linewidth=1.7, label="bootstrap median")
        axis.plot(np.arange(len(actual)), actual, color="#111827", linewidth=1.15, label="observed")
        row = next(item for item in portfolio if item["variant"] == target)
        axis.set_title(
            f"{target}\nP(profit) {row['probability_profit_pct']:.1f}% · "
            f"DD95 {row['max_dd_p95_pct']:.1f}% · Sharpe {row['sharpe_ratio']:.2f}"
        )
        axis.grid(True, alpha=0.18)
        axis.spines[["top", "right"]].set_visible(False)
        axis.set_ylabel("Balance (USD)")
    for axis in axes[-1, :]:
        axis.set_xlabel("Calendar day in one-year resample")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=4, frameon=False)
    fig.suptitle("Dynamic trailing/session audit — 10,000-path 5-day block bootstrap", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.89))
    output = ROOT / "Charts" / "MONTE CARLO - portfolio variants.png"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def update_report(portfolio: list[dict], cases: list[dict]) -> None:
    report_path = ROOT / "FULL REPORT.md"
    text = report_path.read_text(encoding="utf-8")
    marker = "\n## Sharpe, recovery and Monte Carlo\n"
    if marker in text:
        text = text.split(marker, 1)[0].rstrip() + "\n"
    lines = [
        "",
        "## Sharpe, recovery and Monte Carlo",
        "",
        "Monte Carlo uses 10,000 five-calendar-day block-bootstrap paths from the locked daily return sequence. This preserves short clusters better than randomly shuffling individual trades, but it still assumes the locked year is representative of the future.",
        "",
        "| Variant | Sharpe | Recovery | Profit probability | Return P5 / median / P95 | Median / P95 max DD | P(DD >= 10%) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in portfolio:
        lines.append(
            f"| {row['variant']} | {row['sharpe_ratio']:.2f} | {row['recovery_factor']:.2f} | "
            f"{row['probability_profit_pct']:.2f}% | {row['return_p05_pct']:+.2f}% / "
            f"{row['return_p50_pct']:+.2f}% / {row['return_p95_pct']:+.2f}% | "
            f"{row['max_dd_p50_pct']:.2f}% / {row['max_dd_p95_pct']:.2f}% | "
            f"{row['probability_10pct_dd_pct']:.2f}% |"
        )
    lines += [
        "",
        "### Per-EA risk metrics",
        "",
        "| EA | Variant | Sharpe | Recovery | Profit probability | Return P5 | P95 max DD |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in cases:
        lines.append(
            f"| {row['ea']} | {row['variant']} | {row['sharpe_ratio']:.2f} | "
            f"{row['recovery_factor']:.2f} | {row['probability_profit_pct']:.2f}% | "
            f"{row['return_p05_pct']:+.2f}% | {row['max_dd_p95_pct']:.2f}% |"
        )
    lines += [
        "",
        "The current portfolio has the stronger absolute return and recovery factor. Dynamic-only has a slightly higher Sharpe ratio, a lower observed drawdown and a better simulated drawdown tail, but gives up headline return. Session filtering is not recommended portfolio-wide because it materially reduces return and does not improve the Monte Carlo tail enough to compensate. The evidence supports applying dynamic trailing selectively per EA rather than forcing it on every EA.",
    ]
    report_path.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = json.loads((ROOT / "locked-results.json").read_text(encoding="utf-8"))
    combined = {
        item["role"]: item
        for item in json.loads((ROOT / "combined-results.json").read_text(encoding="utf-8"))
    }
    portfolio_rows: list[dict] = []
    observed_curves: dict[str, np.ndarray] = {}
    fan_curves: dict[str, np.ndarray] = {}
    for index, target in enumerate(ROLE_ORDER):
        group = [row for row in rows if role(row) == target]
        metrics, returns, balances = observed_metrics(group)
        locked = combined[target]
        metrics.update(
            {
                "net_profit": float(locked["net_profit"]),
                "return_pct": float(locked["return_pct"]),
                "realized_dd_amount": float(locked["realized_dd_amount"]),
                "realized_dd_pct": float(locked["realized_dd_pct"]),
                "recovery_factor": (
                    float(locked["net_profit"]) / float(locked["realized_dd_amount"])
                    if float(locked["realized_dd_amount"]) > 0
                    else 0.0
                ),
            }
        )
        monte_carlo, fan = bootstrap(returns, index)
        portfolio_rows.append({"variant": target, **metrics, **monte_carlo})
        observed_curves[target] = balances
        fan_curves[target] = fan

    case_rows: list[dict] = []
    ordered = sorted(rows, key=lambda item: (item["EaId"], ROLE_ORDER.index(role(item))))
    for index, row in enumerate(ordered, start=100):
        metrics, returns, _ = observed_metrics([row])
        equity_dd_amount = float(row["equity_dd_amount"])
        metrics.update(
            {
                "net_profit": float(row["net_profit"]),
                "return_pct": float(row["return_pct"]),
                "realized_dd_amount": equity_dd_amount,
                "realized_dd_pct": float(row["equity_dd_pct"]),
                "recovery_factor": float(row["net_profit"]) / equity_dd_amount if equity_dd_amount > 0 else 0.0,
            }
        )
        monte_carlo, _ = bootstrap(returns, index)
        case_rows.append(
            {
                "ea_id": row["EaId"],
                "ea": row["Label"],
                "symbol": row["Symbol"],
                "variant": role(row),
                "trades": row["trades"],
                **metrics,
                **monte_carlo,
            }
        )

    write_csv(ROOT / "monte-carlo-results.csv", portfolio_rows)
    write_csv(ROOT / "monte-carlo-per-ea.csv", case_rows)
    (ROOT / "monte-carlo-results.json").write_text(
        json.dumps({"portfolio": portfolio_rows, "per_ea": case_rows}, indent=2), encoding="utf-8"
    )
    make_fan_chart(portfolio_rows, observed_curves, fan_curves)
    update_report(portfolio_rows, case_rows)
    for row in portfolio_rows:
        print(
            f"{row['variant']:<22} Sharpe={row['sharpe_ratio']:.2f} "
            f"Recovery={row['recovery_factor']:.2f} P(profit)={row['probability_profit_pct']:.2f}% "
            f"P5={row['return_p05_pct']:+.2f}% DD95={row['max_dd_p95_pct']:.2f}%"
        )


if __name__ == "__main__":
    main()
