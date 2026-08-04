from __future__ import annotations

import csv
import html
import itertools
import json
import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np


ROOT = Path(r"C:\Users\hama101\Downloads\BM Trading EAs 2026-08-04\portfolio optimization")
REPORT_DIR = ROOT / "base reports"
OUTPUT_DIR = ROOT / "analysis"
STARTING_BALANCE = 100_000.0
MONTHLY_DD_LIMIT = 4_000.0
STRESS_FACTOR = 1.25

REPORTS = {
    "RB": "PORT_BASE_RB.htm",
    "GL": "PORT_BASE_GL.htm",
    "TT": "PORT_BASE_TT.htm",
    "Ninja": "PORT_BASE_Ninja.htm",
    "Fisher": "PORT_BASE_Fisher.htm",
    "ATR": "PORT_BASE_ATR.htm",
}


def clean_cell(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).replace("\xa0", " ").strip()


def parse_number(value: str) -> float:
    value = value.strip().replace(" ", "").replace("%", "")
    value = re.sub(r"\([^)]*\)$", "", value)
    if not value or value == "-":
        return 0.0
    return float(value)


@dataclass
class ParsedReport:
    code: str
    path: Path
    summary: dict[str, str]
    deals: list[dict]


def parse_report(code: str, path: Path) -> ParsedReport:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8", errors="replace")

    row_html = re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.I | re.S)
    rows: list[list[str]] = []
    for row in row_html:
        cells = re.findall(r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>", row, flags=re.I | re.S)
        rows.append([clean_cell(cell) for cell in cells])

    summary: dict[str, str] = {}
    for cells in rows:
        for index, cell in enumerate(cells[:-1]):
            if cell.endswith(":") and cells[index + 1]:
                summary.setdefault(cell[:-1], cells[index + 1])

    header_index = None
    expected = [
        "Time", "Deal", "Symbol", "Type", "Direction", "Volume", "Price",
        "Order", "Commission", "Swap", "Profit", "Balance", "Comment",
    ]
    for index, cells in enumerate(rows):
        if cells == expected:
            header_index = index
    if header_index is None:
        raise RuntimeError(f"Deals table not found in {path}")

    deals: list[dict] = []
    for cells in rows[header_index + 1:]:
        if len(cells) != 13 or not re.match(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$", cells[0]):
            continue
        if cells[3].lower() == "balance":
            continue
        timestamp = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S")
        commission = parse_number(cells[8])
        swap = parse_number(cells[9])
        profit = parse_number(cells[10])
        deals.append({
            "timestamp": timestamp,
            "commission": commission,
            "swap": swap,
            "profit": profit,
            "net": commission + swap + profit,
            "direction": cells[4],
            "symbol": cells[2],
            "volume": parse_number(cells[5]),
        })

    reported_profit = parse_number(summary.get("Total Net Profit", "0"))
    deal_profit = sum(item["net"] for item in deals)
    if not math.isclose(reported_profit, deal_profit, abs_tol=0.05):
        raise RuntimeError(
            f"Deal sum mismatch for {code}: report={reported_profit:.2f}, deals={deal_profit:.2f}"
        )
    return ParsedReport(code=code, path=path, summary=summary, deals=deals)


def monthly_drawdowns(event_times: list[datetime], event_pnl: np.ndarray) -> dict[str, float]:
    by_month: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for timestamp, amount in zip(event_times, event_pnl, strict=True):
        by_month[timestamp.strftime("%Y-%m")].append((timestamp, float(amount)))

    result: dict[str, float] = {}
    for month, events in by_month.items():
        running = 0.0
        peak = 0.0
        max_dd = 0.0
        for _, amount in events:
            running += amount
            peak = max(peak, running)
            max_dd = max(max_dd, peak - running)
        result[month] = max_dd
    return result


def period_metrics(
    weights: np.ndarray,
    event_times: list[datetime],
    event_matrix: np.ndarray,
    months: list[str],
) -> dict:
    pnl = event_matrix @ weights
    month_profit = {month: 0.0 for month in months}
    for timestamp, amount in zip(event_times, pnl, strict=True):
        month_profit[timestamp.strftime("%Y-%m")] += float(amount)
    drawdowns = monthly_drawdowns(event_times, pnl)

    values = np.asarray([month_profit[month] for month in months], dtype=float)
    dds = np.asarray([drawdowns.get(month, 0.0) for month in months], dtype=float)
    running = np.cumsum(pnl)
    running_with_start = np.concatenate(([0.0], running))
    peak = np.maximum.accumulate(running_with_start)
    total_dd = float(np.max(peak - running_with_start))
    return {
        "total_profit": float(values.sum()),
        "average_monthly_profit": float(values.mean()),
        "median_monthly_profit": float(np.median(values)),
        "profitable_months": int(np.sum(values > 0)),
        "month_count": len(months),
        "worst_month_profit": float(values.min()),
        "best_month_profit": float(values.max()),
        "max_monthly_closed_balance_dd": float(dds.max(initial=0.0)),
        "stressed_max_monthly_dd": float(dds.max(initial=0.0) * STRESS_FACTOR),
        "global_closed_balance_dd": total_dd,
        "monthly_profit": month_profit,
        "monthly_drawdown": {month: drawdowns.get(month, 0.0) for month in months},
    }


def candidate_weight_vectors(count: int, dimensions: int) -> np.ndarray:
    # Quarter-step risk multipliers, with extra density near the practical 0-6x range.
    rng = np.random.default_rng(20260804)
    values = np.arange(0.0, 8.01, 0.25)
    candidates = rng.choice(values, size=(count, dimensions), replace=True)
    candidates[0] = np.ones(dimensions)
    for index in range(dimensions):
        candidates[index + 1] = 0.0
        candidates[index + 1, index] = 1.0
    return candidates


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    missing = [name for name in REPORTS.values() if not (REPORT_DIR / name).exists()]
    if missing:
        raise SystemExit("Missing reports: " + ", ".join(missing))

    parsed = {code: parse_report(code, REPORT_DIR / filename) for code, filename in REPORTS.items()}
    codes = list(REPORTS)

    all_events = sorted({deal["timestamp"] for report in parsed.values() for deal in report.deals})
    event_index = {timestamp: index for index, timestamp in enumerate(all_events)}
    matrix = np.zeros((len(all_events), len(codes)), dtype=float)
    for column, code in enumerate(codes):
        for deal in parsed[code].deals:
            matrix[event_index[deal["timestamp"]], column] += deal["net"]

    train_mask = np.asarray([timestamp < datetime(2025, 1, 1) for timestamp in all_events])
    valid_mask = np.asarray([timestamp >= datetime(2025, 1, 1) for timestamp in all_events])
    train_times = [timestamp for timestamp, keep in zip(all_events, train_mask, strict=True) if keep]
    valid_times = [timestamp for timestamp, keep in zip(all_events, valid_mask, strict=True) if keep]
    train_matrix = matrix[train_mask]
    valid_matrix = matrix[valid_mask]
    train_months = [f"{year}-{month:02d}" for year in (2023, 2024) for month in range(1, 13)]
    valid_months = [f"{year}-{month:02d}" for year in (2025, 2026) for month in range(1, 13)]
    valid_months = [month for month in valid_months if month <= "2026-07"]
    all_months = train_months + valid_months

    # Monthly-profit screen is vectorized; exact event-level drawdown is calculated on finalists.
    month_matrix = np.zeros((len(all_months), len(codes)), dtype=float)
    month_index = {month: index for index, month in enumerate(all_months)}
    for row, timestamp in enumerate(all_events):
        month = timestamp.strftime("%Y-%m")
        if month in month_index:
            month_matrix[month_index[month], :] += matrix[row, :]

    candidates = candidate_weight_vectors(350_000, len(codes))
    # Ninja had a negative prior validation result; only consider it at zero in the deployable search.
    candidates[:, codes.index("Ninja")] = 0.0
    monthly = candidates @ month_matrix.T
    train_avg = monthly[:, :len(train_months)].mean(axis=1)
    valid_avg = monthly[:, len(train_months):].mean(axis=1)
    train_worst = monthly[:, :len(train_months)].min(axis=1)
    valid_worst = monthly[:, len(train_months):].min(axis=1)

    # Build a conservative per-EA drawdown bound. The sum of the individual monthly
    # drawdowns is an upper bound that prevents obviously over-risked mixes from
    # consuming the slower event-by-event finalist evaluation.
    individual_monthly_dd = np.zeros((len(all_months), len(codes)), dtype=float)
    for column, code in enumerate(codes):
        single_weights = np.zeros(len(codes), dtype=float)
        single_weights[column] = 1.0
        single_metrics = period_metrics(single_weights, all_events, matrix, all_months)
        individual_monthly_dd[:, column] = np.asarray(
            [single_metrics["monthly_drawdown"][month] for month in all_months], dtype=float
        )
    conservative_dd = (candidates @ individual_monthly_dd.T).max(axis=1) * STRESS_FACTOR

    # Favor candidates close to the $2k target in both segments, with smaller bad months.
    rough_score = (
        np.abs(train_avg - 2_000.0)
        + 0.30 * np.abs(valid_avg - 2_000.0)
        + 0.10 * np.maximum(0.0, -train_worst)
        + 0.10 * np.maximum(0.0, -valid_worst)
    )
    acceptable = np.where(
        (train_avg > 0.0)
        & (valid_avg > 0.0)
        & (conservative_dd <= MONTHLY_DD_LIMIT)
    )[0]
    if not len(acceptable):
        raise RuntimeError("No positive portfolio candidate passed the conservative drawdown screen")
    finalists = acceptable[np.argsort(rough_score[acceptable])[:600]]

    evaluated: list[dict] = []
    for index in finalists:
        weights = candidates[index]
        train = period_metrics(weights, train_times, train_matrix, train_months)
        if train["stressed_max_monthly_dd"] > MONTHLY_DD_LIMIT:
            continue
        valid = period_metrics(weights, valid_times, valid_matrix, valid_months)
        if valid["stressed_max_monthly_dd"] > MONTHLY_DD_LIMIT:
            continue
        combined = period_metrics(weights, all_events, matrix, all_months)
        # Both segments matter, and the chosen result should be near $2k without needing a lucky segment.
        score = (
            abs(train["average_monthly_profit"] - 2_000.0)
            + abs(valid["average_monthly_profit"] - 2_000.0)
            + 0.35 * abs(combined["average_monthly_profit"] - 2_000.0)
            + 0.10 * max(0.0, -train["worst_month_profit"])
            + 0.10 * max(0.0, -valid["worst_month_profit"])
            + 0.02 * combined["stressed_max_monthly_dd"]
            + 5.0 * np.count_nonzero(weights)
        )
        evaluated.append({
            "score": float(score),
            "weights": {code: float(weights[i]) for i, code in enumerate(codes)},
            "train": train,
            "validation": valid,
            "combined": combined,
        })

    if not evaluated:
        raise RuntimeError("No portfolio candidate passed the stressed 4% monthly drawdown constraint")
    evaluated.sort(key=lambda item: item["score"])
    best = evaluated[0]

    report_summaries = {}
    for code, report in parsed.items():
        report_summaries[code] = {
            "file": str(report.path),
            "total_net_profit": parse_number(report.summary.get("Total Net Profit", "0")),
            "profit_factor": parse_number(report.summary.get("Profit Factor", "0")),
            "balance_drawdown_maximal": report.summary.get("Balance Drawdown Maximal", ""),
            "equity_drawdown_maximal": report.summary.get("Equity Drawdown Maximal", ""),
            "total_trades": int(parse_number(report.summary.get("Total Trades", "0"))),
            "deal_net_check": round(sum(deal["net"] for deal in report.deals), 2),
        }

    payload = {
        "method": {
            "starting_balance": STARTING_BALANCE,
            "test_start": "2023-01-01",
            "test_end": "2026-08-01",
            "calibration_period": "2023-01-01 to 2024-12-31",
            "validation_period": "2025-01-01 to 2026-08-01",
            "monthly_drawdown_limit": MONTHLY_DD_LIMIT,
            "drawdown_measure": "closed-deal balance peak-to-trough inside each calendar month",
            "stress_factor": STRESS_FACTOR,
            "candidate_count": int(len(candidates)),
            "exact_finalists_evaluated": int(len(evaluated)),
        },
        "ea_reports": report_summaries,
        "best": best,
        "top_20": evaluated[:20],
    }
    (OUTPUT_DIR / "portfolio-analysis.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with (OUTPUT_DIR / "best-portfolio-monthly.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Month", "Profit", "Closed balance DD", "Stressed DD (x1.25)", "Segment"])
        for segment_name, metrics in (("calibration", best["train"]), ("validation", best["validation"])):
            for month in metrics["monthly_profit"]:
                dd = metrics["monthly_drawdown"][month]
                writer.writerow([month, round(metrics["monthly_profit"][month], 2), round(dd, 2), round(dd * STRESS_FACTOR, 2), segment_name])

    with (OUTPUT_DIR / "base-ea-summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["EA", "Net profit", "Profit factor", "Balance DD maximal", "Equity DD maximal", "Trades"])
        for code, item in report_summaries.items():
            writer.writerow([code, item["total_net_profit"], item["profit_factor"], item["balance_drawdown_maximal"], item["equity_drawdown_maximal"], item["total_trades"]])

    print(json.dumps({
        "weights": best["weights"],
        "calibration": {k: v for k, v in best["train"].items() if not k.startswith("monthly_")},
        "validation": {k: v for k, v in best["validation"].items() if not k.startswith("monthly_")},
        "combined": {k: v for k, v in best["combined"].items() if not k.startswith("monthly_")},
    }, indent=2))


if __name__ == "__main__":
    main()
