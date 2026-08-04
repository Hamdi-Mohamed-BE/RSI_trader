from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SOURCE_SCRIPT = HERE.parent / "10 Account Prop Simulation 2026-08-04" / "simulate_six_months.py"
START_DATE = date(2026, 8, 5)
TRIALS = 50_000
BLOCK_DAYS = 5

spec = importlib.util.spec_from_file_location("six_month_source", SOURCE_SCRIPT)
source = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = source
spec.loader.exec_module(source)


def capped_pnl(value: float) -> float:
    """E8 Pro removes daily closed profit above 2% of the initial balance."""
    return min(value, 2_000.0)


def run_phase(path: list, start: int, target: float) -> dict:
    balance = 0.0
    for index in range(start, len(path)):
        day = path[index]
        if day.min_intraday <= -2_500.0 + 1e-9:
            return {"status": "daily_breach", "index": index, "balance": balance + day.pnl}
        if balance + day.min_intraday <= -8_000.0 + 1e-9:
            return {"status": "static_breach", "index": index, "balance": balance + day.pnl}
        balance += capped_pnl(day.pnl)
        if balance >= target:
            return {"status": "passed", "index": index, "balance": balance}
    return {"status": "unfinished", "index": len(path) - 1, "balance": balance}


def run_journey(path: list) -> dict:
    challenge = run_phase(path, 0, 8_000.0)
    if challenge["status"] != "passed":
        return {
            "status": f"challenge_{challenge['status']}",
            "challenge_passed": False,
            "challenge_index": None,
            "eligible_index": None,
            "requestable_cash": 0.0,
        }

    # Conservative operational assumption: two complete business days are left
    # for review/KYC/account activation after the challenge is passed.
    funded_start = challenge["index"] + 3
    if funded_start >= len(path):
        return {
            "status": "funded_not_started",
            "challenge_passed": True,
            "challenge_index": challenge["index"],
            "eligible_index": None,
            "requestable_cash": 0.0,
        }

    balance = 0.0
    for index in range(funded_start, len(path)):
        day = path[index]
        if day.min_intraday <= -2_500.0 + 1e-9:
            return {
                "status": "funded_daily_breach",
                "challenge_passed": True,
                "challenge_index": challenge["index"],
                "eligible_index": None,
                "requestable_cash": 0.0,
            }
        if balance + day.min_intraday <= -8_000.0 + 1e-9:
            return {
                "status": "funded_static_breach",
                "challenge_passed": True,
                "challenge_index": challenge["index"],
                "eligible_index": None,
                "requestable_cash": 0.0,
            }
        balance += capped_pnl(day.pnl)
        if balance >= 1_000.0:
            # Standard plan: half the performance is requestable, then the
            # 80% payout share applies. This is eligibility, not approval.
            return {
                "status": "payout_request_eligible",
                "challenge_passed": True,
                "challenge_index": challenge["index"],
                "eligible_index": index,
                "funded_profit": balance,
                "requestable_cash": balance * 0.50 * 0.80,
            }

    return {
        "status": "funded_unfinished",
        "challenge_passed": True,
        "challenge_index": challenge["index"],
        "eligible_index": None,
        "requestable_cash": 0.0,
    }


def bootstrap_paths(days: list, horizon: int, seed: int):
    rng = np.random.default_rng(seed)
    blocks_needed = math.ceil(horizon / BLOCK_DAYS)
    max_start = len(days) - BLOCK_DAYS
    starts = rng.integers(0, max_start + 1, size=(TRIALS, blocks_needed), dtype=np.int32)
    for trial in range(TRIALS):
        indices: list[int] = []
        for block_start in starts[trial]:
            indices.extend(range(int(block_start), int(block_start) + BLOCK_DAYS))
        yield [days[index] for index in indices[:horizon]]


def summarize(outcomes: list[dict], future_dates: list[date]) -> dict:
    challenge_indices = np.asarray(
        [item["challenge_index"] for item in outcomes if item["challenge_passed"]], dtype=float
    )
    eligible = [item for item in outcomes if item["status"] == "payout_request_eligible"]
    eligible_indices = np.asarray([item["eligible_index"] for item in eligible], dtype=float)
    cash = np.asarray([item["requestable_cash"] for item in eligible], dtype=float)
    challenge_probability = len(challenge_indices) / len(outcomes)
    eligible_probability = len(eligible) / len(outcomes)
    standard_error = math.sqrt(eligible_probability * (1.0 - eligible_probability) / len(outcomes))

    def quantiles(values: np.ndarray) -> dict | None:
        if not len(values):
            return None
        p10, median, p90 = np.quantile(values, [0.10, 0.50, 0.90])
        return {"p10": float(p10), "median": float(median), "p90": float(p90)}

    def date_quantiles(indices: np.ndarray) -> dict | None:
        if not len(indices):
            return None
        values = np.quantile(indices, [0.10, 0.50, 0.90])
        return {
            label: str(future_dates[min(len(future_dates) - 1, max(0, int(round(value))))])
            for label, value in zip(("p10", "median", "p90"), values)
        }

    status_counts = {
        status: sum(item["status"] == status for item in outcomes)
        for status in sorted({item["status"] for item in outcomes})
    }
    return {
        "paths": len(outcomes),
        "challenge_pass_probability_percent": 100.0 * challenge_probability,
        "payout_request_eligibility_probability_percent": 100.0 * eligible_probability,
        "monte_carlo_sampling_95pct_interval_percent": [
            100.0 * max(0.0, eligible_probability - 1.96 * standard_error),
            100.0 * min(1.0, eligible_probability + 1.96 * standard_error),
        ],
        "challenge_pass_date_when_passed": date_quantiles(challenge_indices),
        "payout_request_date_when_eligible": date_quantiles(eligible_indices),
        "first_request_cash_on_standard_80pct_plan_when_eligible": {
            "mean": float(np.mean(cash)) if len(cash) else 0.0,
            **(quantiles(cash) or {}),
        },
        "unconditional_expected_requestable_cash": float(
            np.mean([item["requestable_cash"] for item in outcomes])
        ),
        "status_counts": status_counts,
    }


def simulate(days: list, future_dates: list[date], seed: int) -> dict:
    outcomes = [run_journey(path) for path in bootstrap_paths(days, len(future_dates), seed)]
    return summarize(outcomes, future_dates)


def rolling_history(days: list, future_dates: list[date]) -> dict:
    horizon = len(future_dates)
    outcomes = [run_journey(days[start : start + horizon]) for start in range(len(days) - horizon + 1)]
    return summarize(outcomes, future_dates)


def main() -> None:
    horizons = {
        "by_end_of_next_month": source.prior.business_dates(START_DATE, date(2026, 9, 30)),
        "by_end_of_2026": source.prior.business_dates(START_DATE, date(2026, 12, 31)),
        "six_months": source.prior.business_dates(START_DATE, date(2027, 2, 4)),
    }
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
            "description": "Every winning deal reduced 10% and every losing deal enlarged 10%; the source history becomes net-negative.",
            "win_factor": 0.90,
            "loss_factor": 1.10,
        },
    }

    payload = {
        "prepared": "2026-08-04",
        "program": "E8 Pro Forex $100K, standard 80% plan",
        "source_history": {
            "start": "2025-01-02",
            "end": "2026-07-31",
            "business_days": 412,
            "starting_balance": 100_000.0,
            "net_profit": 17_844.91,
            "data_available": "Closed-deal combined MT5 history only; floating equity is unavailable.",
        },
        "modeled_rules": {
            "challenge_target": 8_000.0,
            "static_max_loss": 8_000.0,
            "daily_loss": 2_500.0,
            "daily_profit_cap": 2_000.0,
            "minimum_funded_profit_for_request": 1_000.0,
            "standard_plan_cash_formula": "funded profit x 50% requestable portion x 80% payout share",
            "stage_transition_assumption": "Two complete business days after challenge pass for review/KYC/activation.",
        },
        "interpretation": {
            "payout_request_eligibility": "The simulated account meets the published numerical threshold. It is not a prediction that E8 accepts or sends cash.",
            "cash_received_probability": "Not estimable from MT5 returns. E8 states payouts are discretionary and not guaranteed.",
        },
        "important_limitations": [
            "The five-day block bootstrap reorders only 19 months of history and is not a forecast guarantee.",
            "The MT5 reports contain closed deals, not floating intraday equity; real rule-breach risk is therefore understated.",
            "Future spreads, swaps, slippage, news gaps, outages, symbol mapping, EA licensing and E8 compliance reviews are not observable.",
            "The public third-party EAs may be used by other E8 customers; E8 says matching EA strategies across users can cause termination.",
            "Positions spanning a challenge-to-funded transition cannot be reconstructed from the combined daily data.",
            "No probability of payout approval is claimed because there is no auditable denominator for E8 requests and approvals.",
        ],
        "results": {},
    }

    for scenario_index, (scenario_name, scenario) in enumerate(scenarios.items()):
        days = source.load_days(scenario["win_factor"], scenario["loss_factor"])
        payload["results"][scenario_name] = {
            "description": scenario["description"],
            "historical_sample_net_profit_after_adjustment": float(sum(item.pnl for item in days)),
            "horizons": {},
        }
        for horizon_index, (horizon_name, future_dates) in enumerate(horizons.items()):
            result = simulate(days, future_dates, 20260804 + scenario_index * 100 + horizon_index)
            result["forecast_start"] = str(future_dates[0])
            result["forecast_end"] = str(future_dates[-1])
            result["business_days"] = len(future_dates)
            result["historical_rolling_windows"] = rolling_history(days, future_dates)
            payload["results"][scenario_name]["horizons"][horizon_name] = result

    (HERE / "e8-pro-fast-payout-simulation.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    with (HERE / "e8-pro-fast-payout-summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Scenario",
                "Horizon",
                "Business days",
                "Challenge pass %",
                "Payout request eligible %",
                "Median challenge pass date",
                "Median request eligibility date",
                "Median first request cash if eligible",
                "Unconditional expected requestable cash",
            ]
        )
        for scenario_name, scenario_result in payload["results"].items():
            for horizon_name, result in scenario_result["horizons"].items():
                pass_dates = result["challenge_pass_date_when_passed"] or {}
                payout_dates = result["payout_request_date_when_eligible"] or {}
                cash = result["first_request_cash_on_standard_80pct_plan_when_eligible"]
                writer.writerow(
                    [
                        scenario_name,
                        horizon_name,
                        result["business_days"],
                        round(result["challenge_pass_probability_percent"], 4),
                        round(result["payout_request_eligibility_probability_percent"], 4),
                        pass_dates.get("median"),
                        payout_dates.get("median"),
                        round(cash.get("median", 0.0), 2),
                        round(result["unconditional_expected_requestable_cash"], 2),
                    ]
                )

    print(json.dumps(payload["results"], indent=2))


if __name__ == "__main__":
    main()
