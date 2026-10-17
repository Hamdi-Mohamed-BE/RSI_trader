"""Independent, predeclared screen ranking; does not run portfolio trials.

Only use after the underlying phase counts/timestamps have been independently
verified. Selection is descriptive on overlapping selected history, not a
calibrated future pass probability.
"""
from __future__ import annotations

from collections import defaultdict
import math


SCENARIOS = frozenset(
    (cost, handover)
    for cost in ("recorded_exness", "fixed_cost_stress")
    for handover in ("next_prague_midnight", "two_business_day_wait")
)


def rank_screen(groups, baskets):
    """Return the frozen dual-gate/minimax ranking from verified group metrics.

    groups retain the canonical prior-study aggregate field names. The baskets
    mapping supplies exact predeclared member lists, never post-result mixes.
    """
    by_id = defaultdict(list)
    for group in groups:
        assert group["portfolio"] in baskets, "Unregistered basket"
        by_id[group["portfolio"]].append(group)
    assert by_id.keys() == baskets.keys(), "Every frozen basket needs results"
    candidates = []
    for candidate_id, members in baskets.items():
        assert members and len(members) == len(set(members)), "Empty/duplicate roster"
        rows = by_id[candidate_id]
        keys = [(r["cost"], r["handover"]) for r in rows]
        assert len(keys) == 4 and set(keys) == SCENARIOS, "Exactly four unique scenarios required"
        main_counts, recent_counts, t50, medians = [], [], [], []
        for row in rows:
            main, recent = row["all_starts"], row["jan2026_plus"]
            assert main["starts"] == 134 and recent["starts"] == 71
            for metrics in (main, recent):
                count = metrics["both_completed"]
                assert isinstance(count, int) and 0 <= count <= metrics["starts"]
            main_counts.append(main["both_completed"])
            recent_counts.append(recent["both_completed"])
            t50.append(main["overall_time_to50pct_prague_days"])
            medians.append(main["total_median_prague_days_among_completed"])
        main_ok = all(count >= 101 for count in main_counts)
        recent_ok = all(count >= 54 for count in recent_counts)
        eligible = main_ok and recent_ok
        if eligible:
            assert all(v is not None and math.isfinite(v) and 1 <= v <= 180 for v in t50 + medians)
        candidate = dict(
            portfolio=candidate_id, members=list(members), ea_count=len(members),
            main_four_scenarios_gate=main_ok,
            jan2026_four_scenarios_gate=recent_ok, eligible=eligible,
            minimum_main_completions=min(main_counts),
            minimum_jan2026_completions=min(recent_counts),
            worst_all_start_time_to50_days=max(t50) if all(v is not None for v in t50) else None,
            worst_conditional_total_median_days=max(medians) if all(v is not None for v in medians) else None,
        )
        candidate["selection_key"] = (
            [candidate["worst_all_start_time_to50_days"],
             candidate["worst_conditional_total_median_days"],
             candidate["ea_count"], candidate_id]
            if eligible else None
        )
        candidates.append(candidate)
    eligible_rows = sorted((c for c in candidates if c["eligible"]), key=lambda c: tuple(c["selection_key"]))
    ranks = {c["portfolio"]: i + 1 for i, c in enumerate(eligible_rows)}
    for candidate in candidates:
        candidate["eligible_rank"] = ranks.get(candidate["portfolio"])
    return dict(
        candidate_count=len(candidates), candidates=candidates,
        eligible_count=len(eligible_rows),
        selected_portfolio=eligible_rows[0]["portfolio"] if eligible_rows else None,
        selection_order=[c["portfolio"] for c in eligible_rows],
        thresholds=dict(main=101, main_denominator=134, jan2026=54, jan2026_denominator=71),
        criterion="Both gates in each of four scenarios; minimax all-start T50, then minimax conditional total median, fewer EAs, deterministic ID.",
        interpretation="Retrospective dependent-cohort historical screen; not a future pass-probability estimate.",
    )
