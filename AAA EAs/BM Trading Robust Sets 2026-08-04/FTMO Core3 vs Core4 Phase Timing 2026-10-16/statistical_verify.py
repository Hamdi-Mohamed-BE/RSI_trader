"""Independent cohort/phase statistics, not the portfolio or cash replay engine.

The preflight command reads only the proposed protocol. Verification is deliberately
separate and may run only after the parent has approved outcome computation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PRAGUE = ZoneInfo("Europe/Prague")
OUTCOMES = (
    "failed_phase1", "failed_phase2", "pending_phase1", "pending_phase2",
    "phase2_not_started_wait", "horizon_completed_both",
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def midnight_epoch(day):
    day = date.fromisoformat(day) if isinstance(day, str) else day
    return datetime.combine(day, time.min, PRAGUE).timestamp()


def inclusive_days(begin_epoch, end_epoch):
    assert end_epoch >= begin_epoch
    a = datetime.fromtimestamp(begin_epoch, PRAGUE).date()
    b = datetime.fromtimestamp(end_epoch, PRAGUE).date()
    return (b - a).days + 1


def eligible_starts(start, end, horizon=180):
    first, finish = date.fromisoformat(start), date.fromisoformat(end)
    all_weekdays, eligible = [], []
    day = first
    while day < finish:
        if day.weekday() < 5:
            all_weekdays.append(day.isoformat())
            if day + timedelta(days=horizon) <= finish:
                eligible.append(day.isoformat())
        day += timedelta(days=1)
    return all_weekdays, eligible


def weekday_advance(day, count):
    """Illustrative weekdays only; no official holiday/KYC calendar is inferred."""
    day = date.fromisoformat(day) if isinstance(day, str) else day
    for _ in range(count):
        day += timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
    return day


def absent_epoch(value):
    return None if value is None or value == 0 else float(value)


def median(values):
    return statistics.median(values) if values else None


def _phase(phase, begin, horizon, activated=True):
    p, f = absent_epoch(phase.get("pass_epoch")), absent_epoch(phase.get("fail_epoch"))
    assert not (p is not None and f is not None), "A phase cannot both pass and fail"
    first = absent_epoch(phase.get("first_trade_epoch"))
    if not activated:
        assert p is None and f is None and first is None, "Inactive Phase 2 has events"
        return "not_started", None, None
    for event in (p, f, first):
        if event is not None:
            assert begin <= event < horizon, "Phase event outside exclusive total horizon"
    if p is not None:
        assert first is not None and first <= p, "A pass requires an earlier fill"
        return "passed", p, first
    if f is not None:
        return "failed", f, first
    return "pending", None, first


def normalized_trial(trial):
    start, end = float(trial["start_epoch"]), float(trial["horizon_epoch"])
    day = date.fromisoformat(trial["start_date"])
    assert start == midnight_epoch(day), "Cohort must begin at Prague midnight"
    expected_end_day = day + timedelta(days=180)
    assert trial["horizon_date"] == expected_end_day.isoformat()
    assert end == midnight_epoch(expected_end_day), "Horizon must use 180 civil dates, not fixed seconds"
    assert day.weekday() < 5
    p1, e1, first1 = _phase(trial["phase1"], start, end)
    activation = absent_epoch(trial.get("phase2", {}).get("activation_epoch"))
    started = activation is not None and activation < end
    if p1 == "passed":
        local_pass = datetime.fromtimestamp(e1, PRAGUE).date()
        expected_activation = (
            local_pass + timedelta(days=1)
            if trial["handover"] == "next_prague_midnight"
            else weekday_advance(local_pass, 2)
        )
        expected_activation_epoch = midnight_epoch(expected_activation)
        if expected_activation_epoch < end:
            assert activation == expected_activation_epoch, "Eligible Phase 2 activation cannot be omitted from its denominator"
        else:
            assert activation is None or activation == expected_activation_epoch
        if activation is not None:
            assert e1 < activation, "Phase 2 cannot activate before Phase 1 pass"
    else:
        assert activation is None, "No Phase 2 schedule without a Phase 1 pass"
    p2, e2, first2 = _phase(trial.get("phase2", {}), activation or end, end, started)
    if p1 == "failed":
        assert not started
        outcome = "failed_phase1"
    elif p1 == "pending":
        assert not started
        outcome = "pending_phase1"
    elif not started:
        outcome = "phase2_not_started_wait"
    elif p2 == "failed":
        outcome = "failed_phase2"
    elif p2 == "passed":
        outcome = "horizon_completed_both"
    else:
        outcome = "pending_phase2"
    supplied_outcome = "horizon_completed_both" if trial["outcome"] == "completed_both" else trial["outcome"]
    assert outcome == supplied_outcome, ("Incorrect final classification", outcome, trial["outcome"])
    both = absent_epoch(trial.get("both_pass_epoch"))
    assert both == (e2 if outcome == "horizon_completed_both" else None)
    for phase_name, result in (("phase1", p1), ("phase2", p2)):
        days = trial[phase_name].get("entry_days", 0)
        if isinstance(days, list):
            assert len(days) == len(set(days)), "Duplicate trading dates"
            days = len(days)
        if result == "passed":
            assert int(days) >= 4
    illustration = absent_epoch(trial.get("access_5bd_illustration_epoch"))
    if illustration is not None:
        assert both is not None
        local = datetime.fromtimestamp(both, PRAGUE)
        assert datetime.fromtimestamp(illustration, PRAGUE).date() == weekday_advance(local.date(), 5)
    return dict(
        original=trial, start=start, horizon=end, p1=p1, p2=p2,
        phase2_started=started, outcome=outcome,
        phase1_calendar_days=inclusive_days(start, e1) if p1 == "passed" else None,
        phase1_from_first_trade_calendar_days=inclusive_days(first1, e1) if p1 == "passed" else None,
        phase2_calendar_days=inclusive_days(activation, e2) if p2 == "passed" else None,
        phase2_from_first_trade_calendar_days=inclusive_days(first2, e2) if p2 == "passed" else None,
        total_calendar_days=inclusive_days(start, both) if both is not None else None,
        total_from_first_trade_calendar_days=inclusive_days(first1, both) if both is not None else None,
        total_elapsed_24h_days=(both - start) / 86400 if both is not None else None,
    )


def summarize_trials(trials):
    rows = [normalized_trial(t) for t in trials]
    n = len(rows)
    assert n > 0, "An empty group has no completion rate"
    assert len({t["start_date"] for t in trials}) == n, "Duplicate cohort dates within a scenario"
    outcomes = Counter(r["outcome"] for r in rows)
    p1_pass = sum(r["p1"] == "passed" for r in rows)
    p2_started = sum(r["phase2_started"] for r in rows)
    p2_pass = sum(r["p2"] == "passed" for r in rows)
    completion_days = sorted(r["total_calendar_days"] for r in rows if r["total_calendar_days"] is not None)
    threshold = math.ceil(n / 2)
    return dict(
        starts=n, outcomes={k: outcomes[k] for k in OUTCOMES},
        phase1_passed=p1_pass,
        phase1_pass_pct_all_starts=100 * p1_pass / n,
        phase2_started=p2_started, phase2_passed=p2_pass,
        phase2_pass_pct_started=100 * p2_pass / p2_started if p2_started else None,
        phase2_pass_pct_all_starts=100 * p2_pass / n,
        both_completed=p2_pass, both_completed_pct_all_starts=100 * p2_pass / n,
        phase1_median_calendar_days_among_passes=median([r["phase1_calendar_days"] for r in rows if r["p1"] == "passed"]),
        phase2_median_calendar_days_among_passes=median([r["phase2_calendar_days"] for r in rows if r["p2"] == "passed"]),
        total_median_calendar_days_among_both_passes=median(completion_days),
        total_median_elapsed_24h_days_among_both_passes=median([r["total_elapsed_24h_days"] for r in rows if r["total_elapsed_24h_days"] is not None]),
        first_calendar_day_with_50pct_of_all_starts_completed=completion_days[threshold - 1] if len(completion_days) >= threshold else None,
        pending=sum(outcomes[k] for k in ("pending_phase1", "pending_phase2", "phase2_not_started_wait")),
        failed=outcomes["failed_phase1"] + outcomes["failed_phase2"],
        note="Descriptive overlapping-cohort fractions, not independent future pass probabilities.",
    )


def paired_statistics(core3, core4):
    a = {t["start_date"]: normalized_trial(t) for t in core3}
    b = {t["start_date"]: normalized_trial(t) for t in core4}
    assert len(a) == len(core3) and len(b) == len(core4), "Duplicate cohort starts"
    assert a.keys() == b.keys(), "Paired portfolios require identical eligible dates"
    matrix = Counter((a[k]["outcome"], b[k]["outcome"]) for k in a)
    complete = [k for k in a if a[k]["outcome"] == b[k]["outcome"] == "horizon_completed_both"]
    deltas = [b[k]["total_calendar_days"] - a[k]["total_calendar_days"] for k in complete]
    return dict(
        paired_starts=len(a),
        outcome_matrix=[dict(core3=x, core4=y, n=matrix[x, y]) for x in OUTCOMES for y in OUTCOMES],
        both_portfolios_complete=len(complete),
        median_core4_minus_core3_calendar_days_among_paired_completers=median(deltas),
        no_independent_binomial_confidence_interval=True,
    )


def preflight(plan):
    history = plan["history"]
    weekdays, starts = eligible_starts(history["start_prague"], history["end_exclusive_prague"])
    assert len(starts) == history["all_eligible_weekday_starts"] == 134
    assert len(weekdays) - len(starts) == history["excluded_incomplete_followup_starts"] == 127
    assert starts[0] == history["first_start"] and starts[-1] == history["last_start"]
    assert history["total_horizon_prague_civil_days"] == 180
    assert history["holidays_not_removed"]
    assert len([d for d in starts if d >= "2026-01-01"]) == 71
    assert plan["native_simultaneous"] is False
    return dict(
        status="PREFLIGHT_PASS_NO_OUTCOMES_READ", eligible_starts=134,
        late_starts_excluded=127, weekday_dates_total=261,
        real_tick_era_start_sensitivity=71,
        first_start=starts[0], last_start=starts[-1],
        plan_sha256=sha(ROOT / "PLAN.json"), verifier_sha256=sha(Path(__file__)),
        no_portfolio_outcomes_read=True,
    )


def assert_close(actual, expected, label):
    if expected is None:
        assert actual is None, (label, actual, expected)
    elif isinstance(expected, (int, float)):
        assert actual is not None and math.isclose(float(actual), expected, rel_tol=1e-10, abs_tol=1e-8), (label, actual, expected)
    else:
        assert actual == expected, (label, actual, expected)


def verify_aggregate(supplied, independent):
    mapping = {
        "starts": ("starts", 1),
        "phase1_passes": ("phase1_passed", 1),
        "phase1_pass_fraction": ("phase1_pass_pct_all_starts", .01),
        "phase1_median_prague_days_among_passes": ("phase1_median_calendar_days_among_passes", 1),
        "phase2_started": ("phase2_started", 1),
        "phase2_passes": ("phase2_passed", 1),
        "phase2_conditional_pass_fraction": ("phase2_pass_pct_started", .01),
        "phase2_unconditional_pass_fraction": ("phase2_pass_pct_all_starts", .01),
        "phase2_median_prague_days_among_passes": ("phase2_median_calendar_days_among_passes", 1),
        "both_completed": ("both_completed", 1),
        "both_completion_fraction": ("both_completed_pct_all_starts", .01),
        "total_median_prague_days_among_completed": ("total_median_calendar_days_among_both_passes", 1),
        "overall_time_to50pct_prague_days": ("first_calendar_day_with_50pct_of_all_starts_completed", 1),
    }
    for canonical, (key, factor) in mapping.items():
        value = independent[key]
        assert_close(supplied[canonical], value * factor if value is not None else None, canonical)
    for key in OUTCOMES:
        observed = supplied["outcome_counts"].get(key, 0)
        if key == "horizon_completed_both":
            observed += supplied["outcome_counts"].get("completed_both", 0)
        assert observed == independent["outcomes"][key]
    assert sum(supplied["outcome_counts"].values()) == independent["starts"]
    return len(mapping) + len(OUTCOMES) + 1


def verify_outputs(plan, output, summary):
    _, expected = eligible_starts(plan["history"]["start_prague"], plan["history"]["end_exclusive_prague"])
    expected = set(expected)
    trials = output["trials"]
    grouped = defaultdict(list)
    for trial in trials:
        assert trial["portfolio"] in ("CORE3", "CORE4")
        grouped[trial["portfolio"], trial["cost"], trial["handover"]].append(trial)
        normalized = normalized_trial(trial)
        for phase_name in ("phase1", "phase2"):
            phase = trial[phase_name]
            terminal = absent_epoch(phase.get("pass_epoch")) or absent_epoch(phase.get("fail_epoch"))
            if terminal is not None:
                begin = trial["start_epoch"] if phase_name == "phase1" else phase["activation_epoch"]
                assert_close(phase["elapsed_to_terminal"]["inclusive_prague_days"], inclusive_days(begin, terminal), phase_name + " calendar elapsed")
                assert_close(phase["elapsed_to_terminal"]["elapsed_24h_days"], (terminal - begin) / 86400, phase_name + " fractional elapsed")
                first = absent_epoch(phase.get("first_trade_epoch"))
                if first is not None:
                    assert_close(phase["elapsed_first_trade_to_terminal"]["inclusive_prague_days"], inclusive_days(first, terminal), phase_name + " first-fill calendar elapsed")
                    assert_close(phase["elapsed_first_trade_to_terminal"]["elapsed_24h_days"], (terminal - first) / 86400, phase_name + " first-fill fractional elapsed")
        if normalized["total_calendar_days"] is not None:
            assert_close(trial["total_elapsed_to_both"]["inclusive_prague_days"], normalized["total_calendar_days"], "Whole-attempt elapsed")
            assert_close(trial["total_elapsed_to_both"]["elapsed_24h_days"], normalized["total_elapsed_24h_days"], "Whole-attempt fractional elapsed")
    assert len(trials) == 134 * 8
    assert len(grouped) == 8
    supplied = {(x["portfolio"], x["cost"], x["handover"]): x for x in output["summary"]}
    assert output["summary"] == summary["results"], "Canonical summary differs from raw outcome summary"
    groups, comparisons, checks = [], [], 0
    for scenario in plan["scenarios"]:
        for portfolio in ("CORE3", "CORE4"):
            key = portfolio, scenario["cost"], scenario["handover"]
            rows = grouped[key]
            assert {r["start_date"] for r in rows} == expected
            assert len(rows) == len(expected)
            all_stats = summarize_trials(rows)
            recent_rows = [r for r in rows if r["start_date"] >= "2026-01-01"]
            assert len(recent_rows) == 71
            recent_stats = summarize_trials(recent_rows)
            checks += verify_aggregate(supplied[key]["all_starts"], all_stats)
            checks += verify_aggregate(supplied[key]["jan2026_plus"], recent_stats)
            groups.append(dict(portfolio=portfolio, **scenario, all_starts=all_stats, jan2026_plus=recent_stats))
        a = grouped["CORE3", scenario["cost"], scenario["handover"]]
        b = grouped["CORE4", scenario["cost"], scenario["handover"]]
        comparisons.append(dict(**scenario, all_starts=paired_statistics(a, b), jan2026_plus=paired_statistics([r for r in a if r["start_date"] >= "2026-01-01"], [r for r in b if r["start_date"] >= "2026-01-01"])))
    return dict(
        status="STATISTICAL_FINAL_PASS", trials_verified=len(trials), scenario_groups_verified=8,
        canonical_aggregate_fields_compared=checks, groups=groups, paired_comparisons=comparisons,
        summary_sha256=sha(ROOT / "SUMMARY.json"), outcomes_sha256=sha(ROOT / "OUTCOMES.json"),
        plan_sha256=sha(ROOT / "PLAN.json"), verifier_sha256=sha(Path(__file__)),
        source="Independent timestamp/denominator arithmetic; no cash/path replay or future probability inference.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["preflight", "verify"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = read(ROOT / "PLAN.json")
    result = preflight(plan) if args.mode == "preflight" else verify_outputs(plan, read(ROOT / "OUTCOMES.json"), read(ROOT / "SUMMARY.json"))
    if args.output:
        output = args.output.resolve()
        assert output.parent == ROOT, "Receipt must remain inside this study folder"
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))
