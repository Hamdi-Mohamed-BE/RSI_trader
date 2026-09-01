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
CHARTS = ROOT / "Charts"
STARTING_BALANCE = 10_000.0
PATHS = 10_000
BLOCK_DAYS = 5
SEED = 20_260_901

# The exact per-EA choices promoted into the active BAT portfolio.
SELECTED = {
    "lta-xau": "current",
    "topdown-btc": "current",
    "topdown-eth": "dynamic-only",
    "engineered-xau": "dynamic-only",
    "orb-volume-xau": "dynamic-only",
    "asia-xau": "dynamic-only",
    "dmc-xau": "dynamic-only",
    "ema3-xau": "dynamic-only",
    "weakness-xau": "dynamic-only",
    "overnight-ustec": "current",
    "momentum-ustec": "dynamic-only",
    "news-xau": "dynamic-only",
}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def event_curve(rows: list[dict]) -> tuple[list[datetime], np.ndarray]:
    events: defaultdict[datetime, float] = defaultdict(float)
    first = min(parse_time(row["series"][0]["date"]) for row in rows)
    for row in rows:
        previous = float(row["initial_balance"])
        for point in row["series"][1:]:
            current = float(point["balance"])
            events[parse_time(point["date"])] += current - previous
            previous = current
    timestamps = [first, *sorted(events)]
    balances = [STARTING_BALANCE]
    for when in timestamps[1:]:
        balances.append(balances[-1] + events[when])
    return timestamps, np.asarray(balances, dtype=float)


def daily_returns(rows: list[dict]) -> tuple[list[date], np.ndarray, np.ndarray]:
    events: defaultdict[date, float] = defaultdict(float)
    first = min(parse_time(row["series"][0]["date"]).date() for row in rows)
    last = first
    for row in rows:
        previous = float(row["initial_balance"])
        for point in row["series"][1:]:
            current = float(point["balance"])
            when = parse_time(point["date"]).date()
            events[when] += current - previous
            previous = current
            last = max(last, when)
    days = [first + timedelta(days=index) for index in range((last - first).days + 1)]
    balances = np.empty(len(days) + 1, dtype=float)
    returns = np.zeros(len(days), dtype=float)
    balances[0] = STARTING_BALANCE
    for index, day in enumerate(days):
        previous = balances[index]
        delta = events[day]
        returns[index] = delta / previous if previous > 0 else 0.0
        balances[index + 1] = previous + delta
    return days, returns, balances


def max_drawdown(balances: np.ndarray) -> tuple[float, float]:
    peaks = np.maximum.accumulate(balances)
    amounts = peaks - balances
    percentages = np.divide(amounts, peaks, out=np.zeros_like(amounts), where=peaks > 0)
    index = int(np.argmax(percentages))
    return float(amounts[index]), float(percentages[index] * 100.0)


def sharpe(returns: np.ndarray) -> float:
    if len(returns) < 2:
        return 0.0
    deviation = float(np.std(returns, ddof=1))
    return float(np.mean(returns) / deviation * math.sqrt(365.0)) if deviation > 0 else 0.0


def aggregate(rows: list[dict]) -> tuple[dict, np.ndarray, list[datetime], np.ndarray]:
    timestamps, events = event_curve(rows)
    days, returns, daily_balances = daily_returns(rows)
    dd_amount, dd_pct = max_drawdown(events)
    net = float(sum(float(row["net_profit"]) for row in rows))
    gross_profit = float(sum(float(row["gross_profit"]) for row in rows))
    gross_loss = float(sum(float(row["gross_loss"]) for row in rows))
    trades = int(sum(int(row["trades"]) for row in rows))
    wins = int(sum(int(row["wins"]) for row in rows))
    metrics = {
        "start_date": days[0].isoformat(),
        "end_date": days[-1].isoformat(),
        "starting_balance": STARTING_BALANCE,
        "final_balance": STARTING_BALANCE + net,
        "net_profit": net,
        "return_pct": net / STARTING_BALANCE * 100.0,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": gross_profit / abs(gross_loss) if gross_loss else 999.0,
        "trades": trades,
        "wins": wins,
        "losses": trades - wins,
        "win_rate_pct": wins / trades * 100.0 if trades else 0.0,
        "realized_dd_amount": dd_amount,
        "realized_dd_pct": dd_pct,
        "sharpe_ratio": sharpe(returns),
        "recovery_factor": net / dd_amount if dd_amount else 0.0,
        "commission": float(sum(float(row.get("commission", 0.0)) for row in rows)),
        "swap": float(sum(float(row.get("swap", 0.0)) for row in rows)),
    }
    return metrics, returns, timestamps, events


def bootstrap(returns: np.ndarray) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED)
    block = min(BLOCK_DAYS, len(returns))
    blocks_needed = math.ceil(len(returns) / block)
    starts = rng.integers(0, len(returns) - block + 1, size=(PATHS, blocks_needed))
    indices = (starts[:, :, None] + np.arange(block)).reshape(PATHS, -1)[:, : len(returns)]
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
        "return_mean_pct": float(np.mean(final_returns)),
        "return_p05_pct": float(np.percentile(final_returns, 5)),
        "return_p50_pct": float(np.percentile(final_returns, 50)),
        "return_p95_pct": float(np.percentile(final_returns, 95)),
        "max_dd_p50_pct": float(np.percentile(maximum_drawdowns, 50)),
        "max_dd_p95_pct": float(np.percentile(maximum_drawdowns, 95)),
    }
    fan = np.percentile(paths, [5, 25, 50, 75, 95], axis=0)
    return summary, fan, final_returns, maximum_drawdowns


def per_ea_rows(selected: list[dict], current_by_id: dict[str, dict]) -> list[dict]:
    result = []
    for row in sorted(selected, key=lambda item: item["Label"]):
        current = current_by_id[row["EaId"]]
        dd_amount = float(row["equity_dd_amount"])
        result.append(
            {
                "ea_id": row["EaId"],
                "ea": row["Label"],
                "symbol": row["Symbol"],
                "timeframe": row["Period"],
                "setup": "dynamic 50/20" if row["Variant"] == "dynamic-only" else "current exit",
                "return_pct": float(row["return_pct"]),
                "profit_factor": float(row["profit_factor"]),
                "win_rate_pct": float(row["win_rate"]),
                "max_dd_pct": float(row["equity_dd_pct"]),
                "trades": int(row["trades"]),
                "recovery_factor": float(row["net_profit"]) / dd_amount if dd_amount else 0.0,
                "current_return_pct": float(current["return_pct"]),
                "current_profit_factor": float(current["profit_factor"]),
                "return_delta_pct_points": float(row["return_pct"]) - float(current["return_pct"]),
                "pf_delta": float(row["profit_factor"]) - float(current["profit_factor"]),
            }
        )
    return result


def chart_equity(
    selected_times: list[datetime], selected_curve: np.ndarray,
    current_times: list[datetime], current_curve: np.ndarray,
    selected_metrics: dict, current_metrics: dict,
) -> None:
    fig, axis = plt.subplots(figsize=(13, 6.6), dpi=170)
    axis.plot(current_times, current_curve, color="#64748b", linewidth=1.5, label="Retained EAs — all current exits")
    axis.plot(selected_times, selected_curve, color="#0f9d76", linewidth=2.0, label="Applied per-EA selections")
    axis.axhline(STARTING_BALANCE, color="#111827", linewidth=0.8, alpha=0.45)
    axis.set_title("Applied 12-EA portfolio — locked one-year arithmetic equity overlay")
    axis.set_ylabel("Balance (USD)")
    axis.set_xlabel("Date")
    axis.grid(True, alpha=0.18)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(loc="upper left", frameon=False)
    axis.text(
        0.01, 0.02,
        f"Applied: {selected_metrics['return_pct']:+.2f}% return · PF {selected_metrics['profit_factor']:.2f} · "
        f"DD {selected_metrics['realized_dd_pct']:.2f}%\n"
        f"All current: {current_metrics['return_pct']:+.2f}% return · PF {current_metrics['profit_factor']:.2f} · "
        f"DD {current_metrics['realized_dd_pct']:.2f}%",
        transform=axis.transAxes,
        fontsize=9,
        va="bottom",
    )
    fig.tight_layout()
    fig.savefig(CHARTS / "SELECTED PORTFOLIO - equity comparison.png", bbox_inches="tight")
    plt.close(fig)


def chart_monte_carlo(observed: np.ndarray, fan: np.ndarray, final_returns: np.ndarray, drawdowns: np.ndarray, summary: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.7), dpi=170)
    x = np.arange(1, fan.shape[1] + 1)
    axes[0].fill_between(x, fan[0], fan[4], color="#0f9d76", alpha=0.14, label="5–95%")
    axes[0].fill_between(x, fan[1], fan[3], color="#0f9d76", alpha=0.26, label="25–75%")
    axes[0].plot(x, fan[2], color="#0f9d76", linewidth=1.8, label="Median path")
    axes[0].plot(np.arange(len(observed)), observed, color="#111827", linewidth=1.25, label="Observed")
    axes[0].set_title("10,000 block-bootstrap paths")
    axes[0].set_xlabel("Calendar day")
    axes[0].set_ylabel("Balance (USD)")
    axes[0].grid(True, alpha=0.18)
    axes[0].spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False, loc="upper left")

    axes[1].scatter(final_returns, drawdowns, s=7, alpha=0.17, color="#2563eb", edgecolors="none")
    axes[1].axvline(0, color="#111827", linewidth=0.8, alpha=0.5)
    axes[1].axhline(10, color="#b91c1c", linewidth=0.8, alpha=0.5)
    axes[1].set_title("Terminal return vs maximum drawdown")
    axes[1].set_xlabel("One-year return (%)")
    axes[1].set_ylabel("Maximum drawdown (%)")
    axes[1].grid(True, alpha=0.18)
    axes[1].spines[["top", "right"]].set_visible(False)
    axes[1].text(
        0.98, 0.98,
        f"P(profit) {summary['probability_profit_pct']:.1f}%\n"
        f"Return P5/P50/P95 {summary['return_p05_pct']:+.1f}% / {summary['return_p50_pct']:+.1f}% / {summary['return_p95_pct']:+.1f}%\n"
        f"DD median/P95 {summary['max_dd_p50_pct']:.1f}% / {summary['max_dd_p95_pct']:.1f}%",
        transform=axes[1].transAxes,
        ha="right", va="top", fontsize=9,
    )
    fig.suptitle("Applied 12-EA portfolio — Monte Carlo risk audit")
    fig.tight_layout()
    fig.savefig(CHARTS / "SELECTED PORTFOLIO - monte carlo.png", bbox_inches="tight")
    plt.close(fig)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(selected_metrics: dict, current_metrics: dict, monte_carlo: dict, cases: list[dict]) -> None:
    lines = [
        "# Applied 12-EA portfolio audit — 2026-09-01",
        "",
        "The BAT portfolio now uses the individually selected exit mode for each retained EA. All new session filters are disabled. Engineered Liquidity BTC, US100 Fabio ORB 1R and the standalone XAU Markov Regime EA were removed.",
        "",
        "## Locked one-year portfolio comparison",
        "",
        "| Portfolio | Return | PF | Win rate | Max realized DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| Applied per-EA selections | {selected_metrics['return_pct']:+.2f}% | {selected_metrics['profit_factor']:.2f} | {selected_metrics['win_rate_pct']:.2f}% | {selected_metrics['realized_dd_pct']:.2f}% | {selected_metrics['trades']} | {selected_metrics['sharpe_ratio']:.2f} | {selected_metrics['recovery_factor']:.2f} |",
        f"| Same 12 EAs, all current exits | {current_metrics['return_pct']:+.2f}% | {current_metrics['profit_factor']:.2f} | {current_metrics['win_rate_pct']:.2f}% | {current_metrics['realized_dd_pct']:.2f}% | {current_metrics['trades']} | {current_metrics['sharpe_ratio']:.2f} | {current_metrics['recovery_factor']:.2f} |",
        "",
        "## Monte Carlo — applied selections",
        "",
        f"10,000 five-calendar-day block-bootstrap paths, using the locked portfolio daily return sequence from {selected_metrics['start_date']} through {selected_metrics['end_date']}.",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Probability of profit | {monte_carlo['probability_profit_pct']:.2f}% |",
        f"| Probability of loss | {monte_carlo['probability_loss_pct']:.2f}% |",
        f"| Return P5 / median / P95 | {monte_carlo['return_p05_pct']:+.2f}% / {monte_carlo['return_p50_pct']:+.2f}% / {monte_carlo['return_p95_pct']:+.2f}% |",
        f"| Mean simulated return | {monte_carlo['return_mean_pct']:+.2f}% |",
        f"| Median / P95 maximum DD | {monte_carlo['max_dd_p50_pct']:.2f}% / {monte_carlo['max_dd_p95_pct']:.2f}% |",
        f"| Probability DD >= 10% | {monte_carlo['probability_10pct_dd_pct']:.2f}% |",
        f"| Probability DD >= 20% | {monte_carlo['probability_20pct_dd_pct']:.2f}% |",
        f"| Simulated ruin | {monte_carlo['probability_ruin_pct']:.2f}% |",
        "",
        "## Applied per-EA setups",
        "",
        "| EA | Symbol / TF | Exit setup | Return | PF | Win rate | DD | Trades | Recovery | vs current return |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cases:
        lines.append(
            f"| {row['ea']} | {row['symbol']} {row['timeframe']} | {row['setup']} | "
            f"{row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | "
            f"{row['max_dd_pct']:.2f}% | {row['trades']} | {row['recovery_factor']:.2f} | "
            f"{row['return_delta_pct_points']:+.2f} pp |"
        )
    lines += [
        "",
        "## Important limitation",
        "",
        "This is a chronological arithmetic cash-flow overlay of separate, locked MT5 every-tick EA tests. It preserves the observed timing of closed-trade balance changes, costs and short return clusters, but it is not a simultaneous shared-margin MT5 portfolio test. Monte Carlo measures sequence uncertainty from this one locked year; it cannot prove future profitability or capture future spread, slippage, correlation or regime changes.",
    ]
    (ROOT / "SELECTED PORTFOLIO REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    CHARTS.mkdir(exist_ok=True)
    rows = json.loads((ROOT / "locked-results.json").read_text(encoding="utf-8"))
    selected = [row for row in rows if SELECTED.get(row["EaId"]) == row["Variant"]]
    current = [row for row in rows if row["EaId"] in SELECTED and row["Variant"] == "current"]
    if len(selected) != len(SELECTED) or len(current) != len(SELECTED):
        raise RuntimeError(f"Expected {len(SELECTED)} selected and current cases; got {len(selected)} and {len(current)}")

    selected_metrics, returns, selected_times, selected_curve = aggregate(selected)
    _, _, selected_daily_curve = daily_returns(selected)
    current_metrics, _, current_times, current_curve = aggregate(current)
    monte_carlo, fan, final_returns, drawdowns = bootstrap(returns)
    cases = per_ea_rows(selected, {row["EaId"]: row for row in current})

    output = {
        "selected_setup": SELECTED,
        "selected_portfolio": selected_metrics,
        "same_12_all_current": current_metrics,
        "monte_carlo": monte_carlo,
        "per_ea": cases,
        "methodology": "Chronological arithmetic overlay of separate locked MT5 tests; 10,000-path five-day block bootstrap.",
    }
    (ROOT / "selected-portfolio-results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    write_csv(ROOT / "selected-portfolio-per-ea.csv", cases)
    write_csv(ROOT / "selected-portfolio-summary.csv", [
        {"portfolio": "applied per-EA selections", **selected_metrics},
        {"portfolio": "same 12 all current", **current_metrics},
    ])
    chart_equity(selected_times, selected_curve, current_times, current_curve, selected_metrics, current_metrics)
    chart_monte_carlo(selected_daily_curve, fan, final_returns, drawdowns, monte_carlo)
    write_report(selected_metrics, current_metrics, monte_carlo, cases)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
