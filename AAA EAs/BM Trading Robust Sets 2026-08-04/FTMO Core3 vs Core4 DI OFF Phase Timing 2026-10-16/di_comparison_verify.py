"""Independent paired OFF-minus-ON audit; never runs a portfolio replay."""
from collections import Counter, defaultdict
import argparse
import json
from pathlib import Path
import statistics

import statistical_verify as stats

ROOT = Path(__file__).resolve().parent
ON = ROOT.parent / "FTMO Core3 vs Core4 Phase Timing 2026-10-16"
ON_SUMMARY_HASH = "377685dcc5d94261e2bdc0f368df2abe80eaeb93f0621704d03facbca29e66cc"
ON_OUTCOMES_HASH = "12ccb89cc3be808a3855fb87e1353a32f9c2e9298bd2d0e51b97cde2128372ba"
NON_NASDAQ = (
    "usdjpy-london-open-momentum", "us100-month-end-flow", "xau-rsi-vwap",
)


def paired_group(on_rows, off_rows):
    a = {r["start_date"]: stats.normalized_trial(r) for r in on_rows}
    b = {r["start_date"]: stats.normalized_trial(r) for r in off_rows}
    assert len(a) == len(on_rows) and len(b) == len(off_rows), "Duplicate dates"
    assert a.keys() == b.keys(), "DI versions must use identical eligible dates"
    for key in a:
        x, y = a[key]["original"], b[key]["original"]
        for field in ("portfolio", "start_epoch", "horizon_date", "horizon_epoch", "cost", "handover"):
            assert x[field] == y[field], ("Non-DI cohort condition changed", key, field)
    matrix = Counter((a[k]["outcome"], b[k]["outcome"]) for k in a)
    complete = "horizon_completed_both"
    joint = [k for k in a if a[k]["outcome"] == b[k]["outcome"] == complete]
    differences = [b[k]["total_calendar_days"] - a[k]["total_calendar_days"] for k in joint]
    return dict(
        paired_starts=len(a), on_both_completed=sum(r["outcome"] == complete for r in a.values()),
        off_both_completed=sum(r["outcome"] == complete for r in b.values()),
        both_versions_complete=len(joint),
        on_only_complete=sum(a[k]["outcome"] == complete and b[k]["outcome"] != complete for k in a),
        off_only_complete=sum(a[k]["outcome"] != complete and b[k]["outcome"] == complete for k in a),
        neither_complete=sum(a[k]["outcome"] != complete and b[k]["outcome"] != complete for k in a),
        median_off_minus_on_calendar_days_among_joint_completers=statistics.median(differences) if differences else None,
        off_earlier_pairs=sum(x < 0 for x in differences), same_calendar_day_pairs=sum(x == 0 for x in differences),
        on_earlier_pairs=sum(x > 0 for x in differences),
        outcome_matrix=[dict(di_on=x, di_off=y, n=matrix[x, y]) for x in stats.OUTCOMES for y in stats.OUTCOMES],
        interpretation="Descriptive dependent paired cohorts; not a future pass-probability estimate.",
    )


def compare_protocol(on_plan, off_plan):
    fields = ("baskets", "history", "scenarios", "risk", "guard", "float_model", "costs", "phases", "candidate_priority")
    for key in fields:
        assert on_plan[key] == off_plan[key], ("Non-DI replay protocol changed", key)
    return list(fields)


def preflight():
    assert stats.sha(ON / "SUMMARY.json") == ON_SUMMARY_HASH, "DI-ON control changed"
    assert stats.sha(ON / "OUTCOMES.json") == ON_OUTCOMES_HASH, "DI-ON control changed"
    same_fields = compare_protocol(stats.read(ON / "PLAN.json"), stats.read(ROOT / "PLAN.json"))
    assert stats.sha(ON / "run.py") == stats.sha(ROOT / "run.py"), "Replay engine is not byte-identical"
    old_inputs, new_inputs = stats.read(ON / "INPUTS.json"), stats.read(ROOT / "INPUTS.json")
    assert old_inputs["starts"] == new_inputs["starts"], "Eligible starts changed"
    counts = {}
    for ea in NON_NASDAQ:
        old = [r for r in old_inputs["candidates"] if r["ea"] == ea]
        new = [r for r in new_inputs["candidates"] if r["ea"] == ea]
        assert old == new, ("Non-Nasdaq opportunities/marks/costs changed", ea)
        counts[ea] = len(old)
    return dict(
        status="DI_COMPARISON_PREFLIGHT_PASS", unchanged_protocol_fields=same_fields,
        engine_byte_identical=True, same_eligible_starts=True,
        identical_non_nasdaq_candidate_counts=counts,
        on_summary_sha256=ON_SUMMARY_HASH, on_outcomes_sha256=ON_OUTCOMES_HASH,
        off_plan_sha256=stats.sha(ROOT / "PLAN.json"), off_inputs_sha256=stats.sha(ROOT / "INPUTS.json"),
        comparison_verifier_sha256=stats.sha(Path(__file__)), no_new_outcomes_read=True,
    )


def verify():
    provenance = preflight()
    on_receipt, off_receipt = stats.read(ON / "STATISTICAL-VERIFICATION.json"), stats.read(ROOT / "STATISTICAL-VERIFICATION.json")
    for folder, receipt in ((ON, on_receipt), (ROOT, off_receipt)):
        assert receipt["status"] == "STATISTICAL_FINAL_PASS"
        assert receipt["summary_sha256"] == stats.sha(folder / "SUMMARY.json")
        assert receipt["outcomes_sha256"] == stats.sha(folder / "OUTCOMES.json")
    on, off = stats.read(ON / "OUTCOMES.json")["trials"], stats.read(ROOT / "OUTCOMES.json")["trials"]
    by_on, by_off = defaultdict(list), defaultdict(list)
    for rows, grouped in ((on, by_on), (off, by_off)):
        for row in rows:
            grouped[row["portfolio"], row["cost"], row["handover"]].append(row)
    assert by_on.keys() == by_off.keys() and len(by_on) == 8
    comparisons = []
    for (portfolio, cost, handover), rows in by_on.items():
        other = by_off[portfolio, cost, handover]
        assert len(rows) == len(other) == 134
        full = paired_group(rows, other)
        recent = paired_group([r for r in rows if r["start_date"] >= "2026-01-01"], [r for r in other if r["start_date"] >= "2026-01-01"])
        assert recent["paired_starts"] == 71
        comparisons.append(dict(portfolio=portfolio, cost=cost, handover=handover, all_starts=full, jan2026_plus=recent))
    return dict(
        status="PAIRED_DI_COMPARISON_FINAL_PASS", comparisons=comparisons, group_count=8,
        paired_observations_all_groups=1072, raw_trial_rows_compared=2144,
        provenance=provenance, off_summary_sha256=stats.sha(ROOT / "SUMMARY.json"),
        off_outcomes_sha256=stats.sha(ROOT / "OUTCOMES.json"),
        no_independent_binomial_confidence_interval=True,
        no_live_or_production_changes=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["preflight", "verify"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = preflight() if args.mode == "preflight" else verify()
    if args.output:
        target = args.output.resolve()
        assert target.parent == ROOT
        target.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "comparisons"}, indent=2, allow_nan=False))
