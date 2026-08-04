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


HERE = Path(__file__).resolve().parent
PRIOR_SCRIPT = HERE.parent / "Prop Firm Simulation 2026-08-04" / "simulate_prop_firms.py"
START_DATE = date(2026, 8, 5)
END_DATE = date(2027, 2, 4)
TRIALS = 50_000
BLOCK_DAYS = 5

spec = importlib.util.spec_from_file_location("prior_prop_sim", PRIOR_SCRIPT)
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)


@dataclass(frozen=True)
class DayResult:
    pnl: float
    min_intraday: float
    traded: bool


@dataclass(frozen=True)
class PhaseRules:
    target: float
    daily_loss: float
    max_loss: float
    min_trading_days: int


FUTURE_DATES = prior.business_dates(START_DATE, END_DATE)
HORIZON = len(FUTURE_DATES)


def next_business_day(value: date) -> date:
    current = value + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current


def load_days(win_factor: float, loss_factor: float) -> list[DayResult]:
    parsed = {
        name: prior.pa.parse_report(name, prior.REPORT_DIR / filename)
        for name, filename in prior.REPORTS.items()
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
    results = []
    for event_day in prior.business_dates(first, last):
        running = 0.0
        minimum = 0.0
        for _, amount in sorted(events_by_day.get(event_day, []), key=lambda item: item[0]):
            running += amount
            minimum = min(minimum, running)
        results.append(DayResult(running, minimum, event_day in traded_days))
    return results


def run_phase(path: list[DayResult], start: int, rules: PhaseRules) -> dict:
    balance = 0.0
    trading_days = 0
    for index in range(start, len(path)):
        item = path[index]
        if item.min_intraday <= -rules.daily_loss + 1e-9:
            return {"status": "daily_breach", "index": index, "balance": balance + item.pnl}
        if balance + item.min_intraday <= -rules.max_loss + 1e-9:
            return {"status": "max_loss_breach", "index": index, "balance": balance + item.pnl}
        balance += item.pnl
        if item.traded:
            trading_days += 1
        if balance >= rules.target and trading_days >= rules.min_trading_days:
            return {"status": "passed", "index": index, "balance": balance}
    return {"status": "unfinished", "index": len(path) - 1, "balance": balance}


def run_funded(
    path: list[DayResult],
    start: int,
    rules: PhaseRules,
    program: str,
    payout_share: float,
    payout_fee_factor: float,
) -> dict:
    balance = 0.0
    first_trade: int | None = None
    for index in range(start, len(path)):
        item = path[index]
        if item.traded and first_trade is None:
            first_trade = index
        if item.min_intraday <= -rules.daily_loss + 1e-9:
            return {"status": "funded_daily_breach", "index": index, "balance": balance + item.pnl}
        if balance + item.min_intraday <= -rules.max_loss + 1e-9:
            return {"status": "funded_max_loss_breach", "index": index, "balance": balance + item.pnl}
        balance += item.pnl
        if first_trade is None or index + 1 >= len(path):
            continue

        if program == "FundedNext Stellar 1-Step":
            elapsed_business_days = index - first_trade + 1
            eligible = elapsed_business_days >= 5 and elapsed_business_days % 5 == 0
        else:
            eligible = FUTURE_DATES[index] >= FUTURE_DATES[first_trade] + timedelta(days=30)

        if eligible and balance > 0:
            request_date = FUTURE_DATES[index]
            payout_date = next_business_day(request_date)
            if payout_date <= END_DATE:
                return {
                    "status": "payout",
                    "index": index,
                    "payout_index": index + 1,
                    "payout_date": str(payout_date),
                    "balance": balance,
                    "payout": balance * payout_share * payout_fee_factor,
                }
    return {"status": "funded_unfinished", "index": len(path) - 1, "balance": balance}


def journey_fundednext(path: list[DayResult]) -> dict:
    rules = PhaseRules(10_000.0, 3_000.0, 6_000.0, 2)
    phase1 = run_phase(path, 0, rules)
    if phase1["status"] != "passed":
        return {
            "status": f"phase1_{phase1['status']}",
            "phase1_passed": False,
            "all_phases_passed": False,
            "payout": 0.0,
        }
    funded_start = phase1["index"] + 3  # two complete business days for review/activation
    if funded_start >= len(path):
        return {
            "status": "funded_unfinished",
            "phase1_passed": True,
            "all_phases_passed": True,
            "payout": 0.0,
            "phase1_day": phase1["index"] + 1,
        }
    funded = run_funded(path, funded_start, rules, "FundedNext Stellar 1-Step", 0.80, 0.965)
    return {
        **funded,
        "phase1_passed": True,
        "all_phases_passed": True,
        "phase1_day": phase1["index"] + 1,
    }


def journey_bright(path: list[DayResult]) -> dict:
    phase1_rules = PhaseRules(8_000.0, 4_000.0, 8_000.0, 5)
    phase2_rules = PhaseRules(5_000.0, 4_000.0, 8_000.0, 5)
    phase1 = run_phase(path, 0, phase1_rules)
    if phase1["status"] != "passed":
        return {
            "status": f"phase1_{phase1['status']}",
            "phase1_passed": False,
            "all_phases_passed": False,
            "payout": 0.0,
        }
    phase2_start = phase1["index"] + 2  # one complete business day between phases
    if phase2_start >= len(path):
        return {
            "status": "phase2_unfinished",
            "phase1_passed": True,
            "all_phases_passed": False,
            "payout": 0.0,
        }
    phase2 = run_phase(path, phase2_start, phase2_rules)
    if phase2["status"] != "passed":
        return {
            "status": f"phase2_{phase2['status']}",
            "phase1_passed": True,
            "all_phases_passed": False,
            "payout": 0.0,
            "phase1_day": phase1["index"] + 1,
        }
    funded_start = phase2["index"] + 3  # two complete business days for risk review/KYC activation
    if funded_start >= len(path):
        return {
            "status": "funded_unfinished",
            "phase1_passed": True,
            "all_phases_passed": True,
            "payout": 0.0,
            "phase1_day": phase1["index"] + 1,
            "phase2_day": phase2["index"] + 1,
        }
    funded = run_funded(path, funded_start, phase1_rules, "BrightFunded 2-Step Bright", 0.80, 1.0)
    return {
        **funded,
        "phase1_passed": True,
        "all_phases_passed": True,
        "phase1_day": phase1["index"] + 1,
        "phase2_day": phase2["index"] + 1,
    }


JOURNEYS = {
    "FundedNext Stellar 1-Step": journey_fundednext,
    "BrightFunded 2-Step Bright": journey_bright,
}


def bootstrap_paths(days: list[DayResult], trials: int, seed: int):
    rng = np.random.default_rng(seed)
    blocks_needed = math.ceil(HORIZON / BLOCK_DAYS)
    max_start = len(days) - BLOCK_DAYS
    starts = rng.integers(0, max_start + 1, size=(trials, blocks_needed), dtype=np.int32)
    for trial in range(trials):
        indices: list[int] = []
        for block_start in starts[trial]:
            indices.extend(range(int(block_start), int(block_start) + BLOCK_DAYS))
        yield [days[index] for index in indices[:HORIZON]]


def summarize_outcomes(outcomes: list[dict]) -> dict:
    payouts = np.asarray([item["payout"] for item in outcomes if item["status"] == "payout"], dtype=float)
    payout_days = np.asarray([item["payout_index"] + 1 for item in outcomes if item["status"] == "payout"], dtype=float)
    payout_probability = len(payouts) / len(outcomes)
    standard_error = math.sqrt(payout_probability * (1.0 - payout_probability) / len(outcomes))
    status_counts = {
        status: sum(item["status"] == status for item in outcomes)
        for status in sorted({item["status"] for item in outcomes})
    }

    def quantiles(values: np.ndarray) -> dict | None:
        if not len(values):
            return None
        q = np.quantile(values, [0.10, 0.50, 0.90])
        return {"p10": float(q[0]), "median": float(q[1]), "p90": float(q[2])}

    date_quantiles = None
    if len(payout_days):
        day_q = np.quantile(payout_days, [0.10, 0.50, 0.90])
        date_quantiles = {
            label: str(FUTURE_DATES[min(HORIZON - 1, max(0, int(round(value)) - 1))])
            for label, value in zip(("p10", "median", "p90"), day_q)
        }

    return {
        "paths": len(outcomes),
        "phase1_pass_probability_percent": 100.0 * sum(item["phase1_passed"] for item in outcomes) / len(outcomes),
        "all_evaluation_phases_pass_probability_percent": 100.0 * sum(item["all_phases_passed"] for item in outcomes) / len(outcomes),
        "first_payout_probability_percent": 100.0 * payout_probability,
        "monte_carlo_sampling_95pct_interval_percent": [
            100.0 * max(0.0, payout_probability - 1.96 * standard_error),
            100.0 * min(1.0, payout_probability + 1.96 * standard_error),
        ],
        "first_payout_per_account_when_successful": {
            "mean": float(np.mean(payouts)) if len(payouts) else 0.0,
            **(quantiles(payouts) or {}),
        },
        "unconditional_expected_first_payout_per_account": float(np.mean([item.get("payout", 0.0) for item in outcomes])),
        "first_payout_date_when_successful": date_quantiles,
        "status_counts": status_counts,
    }


def monte_carlo(days: list[DayResult], journey, seed: int) -> dict:
    outcomes = [journey(path) for path in bootstrap_paths(days, TRIALS, seed)]
    return summarize_outcomes(outcomes)


def historical_windows(days: list[DayResult], journey) -> dict:
    outcomes = [journey(days[start:start + HORIZON]) for start in range(len(days) - HORIZON + 1)]
    return summarize_outcomes(outcomes)


def main() -> None:
    scenarios = {
        "tested_execution": {
            "description": "Exact closed-deal net P/L from the final MT5 reports.",
            "win_factor": 1.0,
            "loss_factor": 1.0,
        },
        "moderate_execution_and_news_stress": {
            "description": "Every winning deal reduced 5% and every losing deal enlarged 5%.",
            "win_factor": 0.95,
            "loss_factor": 1.05,
        },
        "severe_execution_and_news_stress": {
            "description": "Every winning deal reduced 10% and every losing deal enlarged 10%; this makes the tested 19-month sample net-negative.",
            "win_factor": 0.90,
            "loss_factor": 1.10,
        },
    }
    payload = {
        "prepared": "2026-08-04",
        "forecast_start": str(START_DATE),
        "forecast_end": str(END_DATE),
        "business_days": HORIZON,
        "trials_per_program_scenario": TRIALS,
        "portfolio_test_source": {
            "start": "2025-01-02",
            "end": "2026-07-31",
            "starting_balance": 100_000.0,
            "net_profit": 17_844.91,
            "note": "Only closed-deal combined history is available; prop firms enforce floating equity.",
        },
        "correlation": {
            "assumption": "All copied accounts receive the same return path and are fully correlated.",
            "implication": "Account count multiplies payout dollars, not the probability of passing or receiving a payout.",
        },
        "program_limits": {
            "FundedNext Stellar 1-Step": "One cloned account modeled as compliant; identical EA trades across FundedNext accounts are prohibited.",
            "BrightFunded 2-Step Bright": "Up to four copied $100K funded accounts ($400K allocation) modeled as compliant.",
            "Ten copied $100K accounts": "Hypothetical only; exceeds the reviewed firms' identical-strategy allocation rules.",
        },
        "important_limitations": [
            "A block bootstrap reorders five-day chunks from only 19 months of history; it is not a forecast guarantee.",
            "Floating equity, future spreads, swaps, symbol mapping, slippage, outages, EA licensing and firm reviews are not observable in the combined reports.",
            "The moderate stress is a sensitivity test, not an empirically measured broker adjustment.",
            "Stage transitions approximate one business day between evaluation phases and two business days before funded activation.",
            "The model assumes a phase can restart from the sampled daily P/L stream; positions spanning a stage transition cannot be reconstructed from combined daily data.",
            "BrightFunded funded-news profits inside its restricted window may be removed; the stress case is not an exact news-calendar replay.",
            "Payout reputation and published rules cannot guarantee that any private simulated-account firm will remain solvent or approve a future payout.",
        ],
        "results": {},
    }

    for scenario_index, (scenario_name, scenario) in enumerate(scenarios.items()):
        days = load_days(scenario["win_factor"], scenario["loss_factor"])
        scenario_result = {
            "description": scenario["description"],
            "historical_sample_net_profit_after_adjustment": float(sum(item.pnl for item in days)),
            "programs": {},
        }
        for program_index, (program_name, journey) in enumerate(JOURNEYS.items()):
            result = monte_carlo(days, journey, 20260804 + scenario_index * 100 + program_index)
            result["historical_rolling_132_business_day_windows"] = historical_windows(days, journey)
            multipliers = {"one_account": 1, "four_correlated_accounts": 4, "ten_correlated_accounts_hypothetical": 10}
            result["correlated_account_payouts_when_successful"] = {
                name: {
                    key: value * multiplier
                    for key, value in result["first_payout_per_account_when_successful"].items()
                }
                for name, multiplier in multipliers.items()
            }
            scenario_result["programs"][program_name] = result
        payload["results"][scenario_name] = scenario_result

    (HERE / "six-month-simulation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with (HERE / "six-month-summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "Scenario", "Program", "Phase 1 pass %", "All evaluation phases pass %", "First payout by 2027-02-04 %",
            "Mean first payout/account if successful", "Median first payout/account if successful", "Median first payout date",
            "Mean first payout x4 correlated", "Mean first payout x10 correlated hypothetical",
        ])
        for scenario_name, scenario in payload["results"].items():
            for program_name, result in scenario["programs"].items():
                per_account = result["first_payout_per_account_when_successful"]
                dates = result["first_payout_date_when_successful"] or {}
                writer.writerow([
                    scenario_name,
                    program_name,
                    round(result["phase1_pass_probability_percent"], 4),
                    round(result["all_evaluation_phases_pass_probability_percent"], 4),
                    round(result["first_payout_probability_percent"], 4),
                    round(per_account.get("mean", 0.0), 2),
                    round(per_account.get("median", 0.0), 2),
                    dates.get("median"),
                    round(result["correlated_account_payouts_when_successful"]["four_correlated_accounts"]["mean"], 2),
                    round(result["correlated_account_payouts_when_successful"]["ten_correlated_accounts_hypothetical"]["mean"], 2),
                ])
    print(json.dumps(payload["results"], indent=2))


if __name__ == "__main__":
    main()
