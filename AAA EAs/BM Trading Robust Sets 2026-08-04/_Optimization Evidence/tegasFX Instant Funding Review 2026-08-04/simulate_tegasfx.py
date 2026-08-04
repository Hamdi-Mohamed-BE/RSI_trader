from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SOURCE_SCRIPT = HERE.parent / "10 Account Prop Simulation 2026-08-04" / "simulate_six_months.py"
START_DATE = date(2026, 8, 5)
END_DATE = date(2026, 12, 31)
LATEST_CONSERVATIVE_REQUEST_DATE = date(2026, 12, 28)
TRIALS = 50_000
BLOCK_DAYS = 5
MAX_LOSS = 10_000.0
DAILY_LOSS = 10_000.0
PROFIT_SPLIT = 0.50

spec = importlib.util.spec_from_file_location("six_month_source", SOURCE_SCRIPT)
source = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = source
spec.loader.exec_module(source)

FUTURE_DATES = source.prior.business_dates(START_DATE, END_DATE)


@dataclass(frozen=True)
class RichDay:
    pnl: float
    minimum_from_open: float
    max_closed_equity_drawdown: float
    traded: bool


def load_days(win_factor: float, loss_factor: float) -> list[RichDay]:
    parsed = {
        name: source.prior.pa.parse_report(name, source.prior.REPORT_DIR / filename)
        for name, filename in source.prior.REPORTS.items()
    }
    events_by_day: dict[date, list[tuple[object, float]]] = {}
    traded_days: set[date] = set()
    for report in parsed.values():
        for deal in report.deals:
            event_day = deal["timestamp"].date()
            amount = deal["net"]
            adjusted = amount * (win_factor if amount > 0 else loss_factor)
            events_by_day.setdefault(event_day, []).append((deal["timestamp"], adjusted))
            if deal["direction"] == "in":
                traded_days.add(event_day)

    first = min(events_by_day)
    last = max(events_by_day)
    results: list[RichDay] = []
    for event_day in source.prior.business_dates(first, last):
        running = 0.0
        minimum = 0.0
        peak = 0.0
        peak_to_trough = 0.0
        for _, amount in sorted(events_by_day.get(event_day, []), key=lambda item: item[0]):
            running += amount
            peak = max(peak, running)
            minimum = min(minimum, running)
            peak_to_trough = min(peak_to_trough, running - peak)
        results.append(RichDay(running, minimum, peak_to_trough, event_day in traded_days))
    return results


def run_path(path: list[RichDay]) -> dict:
    balance = 0.0
    trading_days = 0
    any_profit_index: int | None = None
    any_profit_cash = 0.0
    thousand_cash_index: int | None = None
    thousand_cash_amount = 0.0

    for index, day in enumerate(path):
        if day.max_closed_equity_drawdown <= -DAILY_LOSS + 1e-9:
            return {
                "status": "daily_breach",
                "any_profit_index": any_profit_index,
                "any_profit_cash": any_profit_cash,
                "thousand_cash_index": thousand_cash_index,
                "thousand_cash_amount": thousand_cash_amount,
            }
        if balance + day.minimum_from_open <= -MAX_LOSS + 1e-9:
            return {
                "status": "static_breach",
                "any_profit_index": any_profit_index,
                "any_profit_cash": any_profit_cash,
                "thousand_cash_index": thousand_cash_index,
                "thousand_cash_amount": thousand_cash_amount,
            }

        balance += day.pnl
        if day.traded:
            trading_days += 1

        if trading_days >= 10 and FUTURE_DATES[index] <= LATEST_CONSERVATIVE_REQUEST_DATE:
            if any_profit_index is None and balance > 0:
                any_profit_index = index
                any_profit_cash = balance * PROFIT_SPLIT
            if thousand_cash_index is None and balance >= 2_000.0:
                thousand_cash_index = index
                thousand_cash_amount = balance * PROFIT_SPLIT

    return {
        "status": "survived",
        "ending_balance_change": balance,
        "any_profit_index": any_profit_index,
        "any_profit_cash": any_profit_cash,
        "thousand_cash_index": thousand_cash_index,
        "thousand_cash_amount": thousand_cash_amount,
    }


def bootstrap_paths(days: list[RichDay], seed: int):
    rng = np.random.default_rng(seed)
    horizon = len(FUTURE_DATES)
    blocks_needed = math.ceil(horizon / BLOCK_DAYS)
    max_start = len(days) - BLOCK_DAYS
    starts = rng.integers(0, max_start + 1, size=(TRIALS, blocks_needed), dtype=np.int32)
    for trial in range(TRIALS):
        indices: list[int] = []
        for block_start in starts[trial]:
            indices.extend(range(int(block_start), int(block_start) + BLOCK_DAYS))
        yield [days[index] for index in indices[:horizon]]


def summarize(outcomes: list[dict]) -> dict:
    any_profit = [item for item in outcomes if item["any_profit_index"] is not None]
    thousand = [item for item in outcomes if item["thousand_cash_index"] is not None]
    ending = np.asarray([item.get("ending_balance_change", np.nan) for item in outcomes], dtype=float)
    ending = ending[~np.isnan(ending)]

    def probability_interval(count: int) -> list[float]:
        probability = count / len(outcomes)
        standard_error = math.sqrt(probability * (1.0 - probability) / len(outcomes))
        return [
            100.0 * max(0.0, probability - 1.96 * standard_error),
            100.0 * min(1.0, probability + 1.96 * standard_error),
        ]

    def date_quantiles(items: list[dict], key: str) -> dict | None:
        if not items:
            return None
        indices = np.asarray([item[key] for item in items], dtype=float)
        values = np.quantile(indices, [0.10, 0.50, 0.90])
        return {
            label: str(FUTURE_DATES[min(len(FUTURE_DATES) - 1, max(0, int(round(value))))])
            for label, value in zip(("p10", "median", "p90"), values)
        }

    def cash_quantiles(items: list[dict], key: str) -> dict | None:
        if not items:
            return None
        values = np.asarray([item[key] for item in items], dtype=float)
        p10, median, p90 = np.quantile(values, [0.10, 0.50, 0.90])
        return {
            "mean": float(np.mean(values)),
            "p10": float(p10),
            "median": float(median),
            "p90": float(p90),
        }

    status_counts = {
        status: sum(item["status"] == status for item in outcomes)
        for status in sorted({item["status"] for item in outcomes})
    }
    return {
        "paths": len(outcomes),
        "survival_probability_percent": 100.0 * status_counts.get("survived", 0) / len(outcomes),
        "any_positive_payout_request_probability_percent": 100.0 * len(any_profit) / len(outcomes),
        "any_positive_payout_request_sampling_95pct_interval_percent": probability_interval(len(any_profit)),
        "at_least_1000_cash_request_probability_percent": 100.0 * len(thousand) / len(outcomes),
        "at_least_1000_cash_request_sampling_95pct_interval_percent": probability_interval(len(thousand)),
        "any_positive_request_date": date_quantiles(any_profit, "any_profit_index"),
        "at_least_1000_request_date": date_quantiles(thousand, "thousand_cash_index"),
        "cash_at_first_positive_request": cash_quantiles(any_profit, "any_profit_cash"),
        "cash_at_first_1000_request": cash_quantiles(thousand, "thousand_cash_amount"),
        "ending_account_profit_if_survived": {
            "mean": float(np.mean(ending)) if len(ending) else 0.0,
            "median": float(np.median(ending)) if len(ending) else 0.0,
        },
        "status_counts": status_counts,
    }


def rolling_history(days: list[RichDay]) -> dict:
    horizon = len(FUTURE_DATES)
    outcomes = [run_path(days[start : start + horizon]) for start in range(len(days) - horizon + 1)]
    return summarize(outcomes)


def main() -> None:
    scenarios = {
        "tested_execution": (1.0, 1.0),
        "moderate_execution_and_news_stress": (0.95, 1.05),
        "severe_execution_and_news_stress": (0.90, 1.10),
    }
    payload = {
        "prepared": "2026-08-04",
        "program": "tegasFX $100K Instant Funding, Bronze 50% profit split",
        "forecast_start": str(START_DATE),
        "forecast_end": str(END_DATE),
        "business_days": len(FUTURE_DATES),
        "latest_conservative_request_date_for_year_end_processing": str(LATEST_CONSERVATIVE_REQUEST_DATE),
        "source_history": {
            "start": "2025-01-02",
            "end": "2026-07-31",
            "business_days": 412,
            "starting_balance": 100_000.0,
            "net_profit": 17_844.91,
        },
        "modeled_rules": {
            "overall_static_loss_floor": -MAX_LOSS,
            "daily_closed_equity_high_watermark_loss": -DAILY_LOSS,
            "minimum_trading_days_before_request": 10,
            "starting_profit_split": PROFIT_SPLIT,
            "cash_target": 1_000.0,
            "account_profit_needed_for_cash_target": 2_000.0,
            "current_listed_security_deposit": 9_999.0,
            "refund_formula": "90% of security deposit minus realized losses, after review",
        },
        "limitations": [
            "The official page displays selectable drawdown tiers; this model uses the narrowest 10% tier conservatively.",
            "Only closed deals are available, so floating-equity daily and overall breaches are understated.",
            "Payout eligibility is not payout approval or cash receipt.",
            "The $9,999 security deposit and its refund are counterparty exposures; they are not included as investment return.",
            "Future spreads, commissions, swaps, slippage, symbol mapping, outages and compliance reviews are unknown.",
        ],
        "results": {},
    }

    for index, (name, (win_factor, loss_factor)) in enumerate(scenarios.items()):
        days = load_days(win_factor, loss_factor)
        outcomes = [run_path(path) for path in bootstrap_paths(days, 20260804 + index)]
        payload["results"][name] = summarize(outcomes)
        payload["results"][name]["historical_rolling_windows"] = rolling_history(days)

    (HERE / "tegasfx-year-end-simulation.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    with (HERE / "tegasfx-year-end-summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Scenario",
                "Survival %",
                "Any positive payout request %",
                "$1,000+ cash request %",
                "Median date any request",
                "Median date $1,000+ request",
                "Median cash at first positive request",
                "Median cash at first $1,000+ request",
            ]
        )
        for name, result in payload["results"].items():
            any_dates = result["any_positive_request_date"] or {}
            thousand_dates = result["at_least_1000_request_date"] or {}
            any_cash = result["cash_at_first_positive_request"] or {}
            thousand_cash = result["cash_at_first_1000_request"] or {}
            writer.writerow(
                [
                    name,
                    round(result["survival_probability_percent"], 4),
                    round(result["any_positive_payout_request_probability_percent"], 4),
                    round(result["at_least_1000_cash_request_probability_percent"], 4),
                    any_dates.get("median"),
                    thousand_dates.get("median"),
                    round(any_cash.get("median", 0.0), 2),
                    round(thousand_cash.get("median", 0.0), 2),
                ]
            )

    print(json.dumps(payload["results"], indent=2))


if __name__ == "__main__":
    main()
