from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np


ROOT = Path(r"C:\Users\hama101\Downloads\BM Trading EAs 2026-08-04\portfolio optimization")
REPORT_DIR = ROOT / "scaled validation reports"
OUTPUT_DIR = ROOT / "analysis" / "prop firm simulation"
START_BALANCE = 100_000.0
LOSS_STRESS = 1.25
DEADLINE_BUSINESS_DAYS = 42  # 2026-08-04 through 2026-09-30 inclusive
MONTE_CARLO_TRIALS = 50_000

spec = importlib.util.spec_from_file_location("portfolio_analyzer", ROOT / "analyze_portfolio.py")
pa = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pa
spec.loader.exec_module(pa)

REPORTS = {
    "Range Breakout": "PORT_SCALED_RB.htm",
    "Go Long": "PORT_SCALED_GL.htm",
    "Turnaround Tuesday": "PORT_SCALED_TT.htm",
    "ATR Candle Breakout": "PORT_SCALED_ATR.htm",
}


@dataclass(frozen=True)
class DayResult:
    day: date
    pnl: float
    min_intraday: float
    traded: bool


@dataclass(frozen=True)
class Rules:
    name: str
    target: float
    daily_loss: float
    max_loss: float
    min_trading_days: int
    trailing_eod: bool = False
    best_day_ratio: float | None = None


def business_dates(start: date, end: date) -> list[date]:
    result = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            result.append(current)
        current += timedelta(days=1)
    return result


def load_days(loss_stress: float = LOSS_STRESS) -> list[DayResult]:
    parsed = {
        name: pa.parse_report(name, REPORT_DIR / filename)
        for name, filename in REPORTS.items()
    }
    events_by_day: dict[date, list[tuple[object, float, float]]] = {}
    traded_days: set[date] = set()
    for report in parsed.values():
        for deal in report.deals:
            event_day = deal["timestamp"].date()
            raw_net = deal["net"]
            stressed_net = raw_net * (loss_stress if raw_net < 0 else 1.0)
            events_by_day.setdefault(event_day, []).append((deal["timestamp"], raw_net, stressed_net))
            if deal["direction"] == "in":
                traded_days.add(event_day)

    first = min(events_by_day)
    last = max(events_by_day)
    results = []
    for event_day in business_dates(first, last):
        events = sorted(events_by_day.get(event_day, []), key=lambda item: item[0])
        running_raw = 0.0
        running_stressed = 0.0
        minimum_stressed = 0.0
        for _, raw_amount, stressed_amount in events:
            running_raw += raw_amount
            running_stressed += stressed_amount
            minimum_stressed = min(minimum_stressed, running_stressed)
        results.append(DayResult(event_day, running_raw, minimum_stressed, event_day in traded_days))
    return results


def consistency_ok(daily_pnl: list[float], ratio: float | None) -> bool:
    if ratio is None:
        return True
    positives = [amount for amount in daily_pnl if amount > 0]
    if not positives:
        return False
    return max(positives) <= ratio * sum(positives) + 1e-9


def run_phase(path: list[DayResult], start: int, stop: int, rules: Rules) -> dict:
    balance = 0.0
    highest_eod = 0.0
    trading_days = 0
    daily_pnl: list[float] = []
    for index in range(start, min(stop, len(path))):
        item = path[index]
        if item.min_intraday < -rules.daily_loss - 1e-9:
            return {"status": "daily_breach", "index": index, "balance": balance + item.pnl}
        loss_floor = (highest_eod if rules.trailing_eod else 0.0) - rules.max_loss
        if balance + item.min_intraday < loss_floor - 1e-9:
            return {"status": "max_loss_breach", "index": index, "balance": balance + item.pnl}
        balance += item.pnl
        daily_pnl.append(item.pnl)
        if item.traded:
            trading_days += 1
        highest_eod = max(highest_eod, balance)
        if (
            balance >= rules.target
            and trading_days >= rules.min_trading_days
            and consistency_ok(daily_pnl, rules.best_day_ratio)
        ):
            return {"status": "passed", "index": index, "balance": balance, "daily_pnl": daily_pnl}
    return {"status": "unfinished", "index": min(stop, len(path)) - 1, "balance": balance, "daily_pnl": daily_pnl}


def run_funded_cycle(
    path: list[DayResult],
    start: int,
    stop: int,
    rules: Rules,
    minimum_days: int,
    best_day_ratio: float | None = None,
    eligibility_interval: int | None = None,
) -> dict:
    balance = 0.0
    highest_eod = 0.0
    daily_pnl: list[float] = []
    first_trade = None
    for index in range(start, min(stop, len(path))):
        item = path[index]
        if item.traded and first_trade is None:
            first_trade = index
        if item.min_intraday < -rules.daily_loss - 1e-9:
            return {"status": "daily_breach", "index": index, "balance": balance + item.pnl}
        loss_floor = (highest_eod if rules.trailing_eod else 0.0) - rules.max_loss
        if balance + item.min_intraday < loss_floor - 1e-9:
            return {"status": "max_loss_breach", "index": index, "balance": balance + item.pnl}
        balance += item.pnl
        daily_pnl.append(item.pnl)
        highest_eod = max(highest_eod, balance)
        elapsed = 0 if first_trade is None else index - first_trade + 1
        on_eligible_day = elapsed >= minimum_days and (
            eligibility_interval is None or elapsed % eligibility_interval == 0
        )
        if on_eligible_day and balance >= 20.0 and consistency_ok(daily_pnl, best_day_ratio):
            return {"status": "payout_eligible", "index": index, "balance": balance, "daily_pnl": daily_pnl}
    return {"status": "unfinished", "index": min(stop, len(path)) - 1, "balance": balance, "daily_pnl": daily_pnl}


FN_RULES = Rules("FundedNext Stellar 1-Step", 10_000.0, 3_000.0, 6_000.0, 2)
FTMO_1_RULES = Rules("FTMO 1-Step", 10_000.0, 3_000.0, 10_000.0, 1, trailing_eod=True, best_day_ratio=0.50)
FTMO_2_RULES = Rules("FTMO 2-Step Swing phase 1", 10_000.0, 5_000.0, 10_000.0, 4)
FTMO_VERIFY_RULES = Rules("FTMO 2-Step Swing verification", 5_000.0, 5_000.0, 10_000.0, 4)


def journey_fundednext(path: list[DayResult], deadline: int) -> dict:
    # Two business days for review/activation, five business days for the first cycle,
    # and one business day for the advertised payout processing.
    phase = run_phase(path, 0, max(0, deadline - 8), FN_RULES)
    if phase["status"] != "passed":
        return {"status": phase["status"], "stage": "challenge", "payout": 0.0}
    funded_start = phase["index"] + 3
    funded_stop = deadline - 1
    funded = run_funded_cycle(
        path,
        funded_start,
        funded_stop,
        FN_RULES,
        minimum_days=5,
        eligibility_interval=5,
    )
    if funded["status"] != "payout_eligible":
        return {"status": funded["status"], "stage": "funded", "payout": 0.0, "challenge_day": phase["index"]}
    net_payout = funded["balance"] * 0.80 * 0.965  # 80% base split and maximum published 3.5% processor fee
    return {
        "status": "payout",
        "stage": "complete",
        "payout": max(0.0, net_payout),
        "challenge_day": phase["index"],
        "payout_day": funded["index"] + 1,
    }


def journey_ftmo_1step(path: list[DayResult], deadline: int) -> dict:
    # Two business days for account review/activation and roughly ten business days
    # for the 14-calendar-day reward wait, followed by three processing days.
    phase = run_phase(path, 0, max(0, deadline - 15), FTMO_1_RULES)
    if phase["status"] != "passed":
        return {"status": phase["status"], "stage": "challenge", "payout": 0.0}
    funded_start = phase["index"] + 3
    funded = run_funded_cycle(
        path,
        funded_start,
        max(funded_start, deadline - 3),
        FTMO_1_RULES,
        minimum_days=10,
        best_day_ratio=0.50,
    )
    if funded["status"] != "payout_eligible":
        return {"status": funded["status"], "stage": "funded", "payout": 0.0, "challenge_day": phase["index"]}
    return {
        "status": "payout",
        "stage": "complete",
        "payout": max(0.0, funded["balance"] * 0.90),
        "challenge_day": phase["index"],
        "payout_day": funded["index"] + 3,
    }


def journey_ftmo_2step(path: list[DayResult], deadline: int) -> dict:
    phase1 = run_phase(path, 0, deadline, FTMO_2_RULES)
    if phase1["status"] != "passed":
        return {"status": phase1["status"], "stage": "phase1", "payout": 0.0}
    phase2_start = phase1["index"] + 2
    phase2 = run_phase(path, phase2_start, deadline, FTMO_VERIFY_RULES)
    if phase2["status"] != "passed":
        return {"status": phase2["status"], "stage": "phase2", "payout": 0.0}
    funded_start = phase2["index"] + 3
    funded = run_funded_cycle(path, funded_start, max(funded_start, deadline - 3), FTMO_2_RULES, minimum_days=10)
    if funded["status"] != "payout_eligible":
        return {"status": funded["status"], "stage": "funded", "payout": 0.0}
    return {"status": "payout", "stage": "complete", "payout": max(0.0, funded["balance"] * 0.80)}


JOURNEYS = {
    "FundedNext Stellar 1-Step": journey_fundednext,
    "FTMO 1-Step Standard": journey_ftmo_1step,
    "FTMO 2-Step Swing": journey_ftmo_2step,
}


def historical_windows(days: list[DayResult], deadline: int, journey) -> dict:
    outcomes = []
    for start in range(0, len(days) - deadline + 1):
        path = days[start:start + deadline]
        outcome = journey(path, deadline)
        outcomes.append(outcome)
    payouts = [item["payout"] for item in outcomes if item["status"] == "payout"]
    challenge_passes = sum(item.get("stage") in {"funded", "complete"} for item in outcomes)
    return {
        "windows": len(outcomes),
        "payouts": len(payouts),
        "payout_probability_percent": 100.0 * len(payouts) / len(outcomes) if outcomes else 0.0,
        "challenge_pass_probability_percent": 100.0 * challenge_passes / len(outcomes) if outcomes else 0.0,
        "average_net_payout_when_successful": float(np.mean(payouts)) if payouts else 0.0,
        "status_counts": {status: sum(item["status"] == status for item in outcomes) for status in sorted({item["status"] for item in outcomes})},
    }


def bootstrap_paths(days: list[DayResult], length: int, trials: int, seed: int = 20260804):
    rng = np.random.default_rng(seed)
    max_start = len(days) - 5
    blocks_needed = math.ceil(length / 5)
    starts = rng.integers(0, max_start + 1, size=(trials, blocks_needed), dtype=np.int32)
    for trial in range(trials):
        indices = []
        for block_start in starts[trial]:
            indices.extend(range(int(block_start), int(block_start) + 5))
        yield [days[index] for index in indices[:length]]


def monte_carlo(days: list[DayResult], deadline: int, journey, trials: int, seed: int) -> dict:
    payouts = []
    status_counts: dict[str, int] = {}
    challenge_days = []
    challenge_passes = 0
    for path in bootstrap_paths(days, deadline, trials, seed):
        outcome = journey(path, deadline)
        if outcome.get("stage") in {"funded", "complete"}:
            challenge_passes += 1
        status_counts[outcome["status"]] = status_counts.get(outcome["status"], 0) + 1
        if outcome["status"] == "payout":
            payouts.append(outcome["payout"])
            if "challenge_day" in outcome:
                challenge_days.append(outcome["challenge_day"] + 1)
    probability = len(payouts) / trials
    standard_error = math.sqrt(probability * (1.0 - probability) / trials) if trials else 0.0
    return {
        "trials": trials,
        "payouts": len(payouts),
        "payout_probability_percent": 100.0 * probability,
        "challenge_pass_probability_percent": 100.0 * challenge_passes / trials,
        "monte_carlo_95pct_interval_percent": [
            max(0.0, 100.0 * (probability - 1.96 * standard_error)),
            min(100.0, 100.0 * (probability + 1.96 * standard_error)),
        ],
        "average_net_payout_when_successful": float(np.mean(payouts)) if payouts else 0.0,
        "median_challenge_business_days_when_successful": float(np.median(challenge_days)) if challenge_days else None,
        "status_counts": status_counts,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    days = load_days()
    raw_days = load_days(loss_stress=1.0)
    pnl = np.asarray([item.pnl for item in days])
    raw_pnl = np.asarray([item.pnl for item in raw_days])
    rolling_42 = np.convolve(raw_pnl, np.ones(DEADLINE_BUSINESS_DAYS), mode="valid")
    dataset = {
        "start": str(days[0].day),
        "end": str(days[-1].day),
        "business_days": len(days),
        "raw_net_profit": float(raw_pnl.sum()),
        "net_profit_used_for_return_simulation": float(pnl.sum()),
        "all_losing_deals_25pct_worse_net_profit_warning_scenario": -6819.1875,
        "loss_stress_factor": LOSS_STRESS,
        "worst_closed_day": float(pnl.min()),
        "best_closed_day": float(pnl.max()),
        "maximum_stressed_intraday_closed_loss": float(-min(item.min_intraday for item in days)),
        "best_actual_42_business_day_profit": float(rolling_42.max()),
        "median_actual_42_business_day_profit": float(np.median(rolling_42)),
        "deadline": "2026-09-30",
        "deadline_business_days": DEADLINE_BUSINESS_DAYS,
    }

    results = {}
    for index, (name, journey) in enumerate(JOURNEYS.items()):
        results[name] = {
            "historical_rolling_42_business_days": historical_windows(days, DEADLINE_BUSINESS_DAYS, journey),
            "historical_rolling_260_business_days": historical_windows(days, 260, journey),
            "bootstrap_42_business_days": monte_carlo(days, DEADLINE_BUSINESS_DAYS, journey, MONTE_CARLO_TRIALS, 20260804 + index),
            "bootstrap_260_business_days": monte_carlo(days, 260, journey, MONTE_CARLO_TRIALS, 20270804 + index),
        }

    payload = {
        "important_limitations": [
            "Simulation uses closed-deal events from the exact final MT5 reports; prop rules use floating equity too.",
            "Negative closed events are multiplied by 1.25; positive events are not increased.",
            "Weekly block bootstrap reuses a 19-month historical sample and is not a true forecast.",
            "News, weekend, symbol mapping, spreads, swaps, slippage, EA licensing and compliance reviews can reduce eligibility.",
            "Monte Carlo confidence intervals measure sampling error only, not model uncertainty.",
        ],
        "dataset": dataset,
        "results": results,
    }
    (OUTPUT_DIR / "prop-firm-simulation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with (OUTPUT_DIR / "prop-firm-comparison.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Firm/program", "Window", "Trials/windows", "Payouts", "Payout probability %", "Average net payout if successful"])
        for name, sections in results.items():
            for window, item in sections.items():
                writer.writerow([
                    name, window, item.get("trials", item.get("windows")), item["payouts"],
                    round(item["payout_probability_percent"], 4), round(item["average_net_payout_when_successful"], 2),
                ])
    print(json.dumps({"dataset": dataset, "results": results}, indent=2))


if __name__ == "__main__":
    main()
