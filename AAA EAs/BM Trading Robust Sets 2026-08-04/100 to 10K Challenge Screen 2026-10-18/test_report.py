"""Synthetic report tests; no historical challenge outcomes are computed."""
import copy
import json
from pathlib import Path
import pytest
import report


def put(root, name, value):
    (root / name).write_text(json.dumps(value), encoding="utf-8")


def bind(root, name):
    return report.sha(root / name)


@pytest.fixture
def saved(tmp_path):
    plan = dict(initial_balance=100, target_balance=10000, development=["2020-01-01", "2022-01-01"],
                evaluation=["2022-01-01", "2024-01-01"], horizon_days=365, risk_percentages=[5],
                limitations=["Synthetic test only; not untouched OOS."])
    for key in ("sizing", "cash", "success", "failure", "exposure", "daily_pause", "margin", "stress"):
        plan[key] = "Synthetic " + key + " rule"
    source = dict(metadata=dict(labels={"a": "EA <A>", "b": "EA B"},
                                excluded={"excluded" + str(i): "reason" for i in range(7)}),
                  symbols={}, source_hashes={})
    audit = dict(eligible_current_eas=30, alternatives=1, source_file_count=211,
                 counts=dict(positions=12, partial_positions=1, end_censored_positions=1),
                 source_warnings=[dict(key="a", native_flags={"invalid_stops": 12}, note="Log diagnostic, not unique rejects.")],
                 limitations=["15% real ticks. ETH uses stale quotes."])
    broker = dict(account=dict(company="Exness", server="Trial15", currency="USD", leverage=2000))
    for name, value in [("PLAN.json", plan), ("INPUTS.json", source), ("SOURCE AUDIT.json", audit), ("BROKER.json", broker)]:
        put(tmp_path, name, value)
    frozen = dict(before_challenge_outcomes=True,
                  files={str(tmp_path / name): bind(tmp_path, name) for name in ("PLAN.json", "INPUTS.json")})
    put(tmp_path, "FROZEN.json", frozen)

    def attempts(starts):
        return [dict(start=t, end_exclusive=t + 365 * report.DAY, status="timeout", hit_epoch=None,
                     hit_days=None, floor_epoch=None, ending_closed_cash=100, open_positions=0,
                     max_closed_dd_pct=0, no_admitted_positions=True, counts={}) for t in starts]

    def summary(aa):
        return dict(starts=len(aa), hits=0, hit_pct=0, floor_pct=0, timeout_pct=100, no_trade_pct=100,
                    median_hit_days=None, all_start_median_days=None, mean_capped_days=365,
                    ending_cash_p10=100, ending_cash_median=100, ending_cash_p90=100,
                    median_closed_dd_pct=0, worst_closed_dd_pct=0, fastest=None, total_counts={})

    starts = report.expected_starts(plan["development"], 365)
    single = dict(id="a@5", keys=["a"], risk_pct=5, attempts=attempts(starts))
    single["summary"] = summary(single["attempts"])
    combo = copy.deepcopy(single)
    combo.update(id="a+b@5", keys=["a", "b"])
    development = dict(starts=starts, singles=[single], combos=[combo], configuration_count=2,
                       shortlist=["a", "b"], frozen_sha256=bind(tmp_path, "FROZEN.json"))
    put(tmp_path, "DEVELOPMENT.json", development)
    locked = []
    for kind, c in (("single", single), ("combo", combo)):
        for role in ("primary", "highest_hit_rate", "fastest_observed"):
            locked.append(dict(kind=kind, role=role, qualified=False, id=c["id"], keys=c["keys"], risk_pct=5,
                               development=c["summary"]))
    selection = dict(status="LOCKED before evaluation", locked=locked,
                     frozen_sha256=bind(tmp_path, "FROZEN.json"), development_sha256=bind(tmp_path, "DEVELOPMENT.json"))
    put(tmp_path, "SELECTION.json", selection)
    results = dict(historical_fraction_not_future_probability=True, no_live_changes=True,
                   plan_sha256=bind(tmp_path, "PLAN.json"), inputs_sha256=bind(tmp_path, "INPUTS.json"),
                   selection_sha256=bind(tmp_path, "SELECTION.json"), frozen_sha256=bind(tmp_path, "FROZEN.json"), results=[])
    for c in (single, combo):
        for cost in ("recorded", "stress"):
            aa = attempts(report.expected_starts(plan["evaluation"], 365))
            results["results"].append(dict(id=c["id"], keys=c["keys"], risk_pct=5, cost=cost,
                                           attempts=aa, summary=summary(aa), details=[]))
    put(tmp_path, "RESULTS.json", results)
    return tmp_path


def data(root):
    return [report.read(root, n) for n in ("PLAN.json", "INPUTS.json", "DEVELOPMENT.json", "SELECTION.json", "RESULTS.json")]


def test_missing_receipt_is_pending(saved):
    assert report.receipt(saved)[0] == "PENDING"


def test_exact_receipt_passes(saved):
    put(saved, "VERIFICATION.json", dict(status="PASS", checks=123,
        results_sha256=bind(saved, "RESULTS.json"), selection_sha256=bind(saved, "SELECTION.json"), frozen_sha256=bind(saved, "FROZEN.json")))
    assert report.receipt(saved) == ("PASS", "Hash-bound independent verification · 123 checks")


@pytest.mark.parametrize("binding", ["results_sha256", "selection_sha256", "frozen_sha256"])
def test_stale_or_missing_binding_never_passes(saved, binding):
    receipt = dict(status="PASS", results_sha256=bind(saved, "RESULTS.json"),
                   selection_sha256=bind(saved, "SELECTION.json"), frozen_sha256=bind(saved, "FROZEN.json"))
    receipt[binding] = "wrong"
    put(saved, "VERIFICATION.json", receipt)
    assert report.receipt(saved)[0] == "NOT VERIFIED"
    del receipt[binding]
    put(saved, "VERIFICATION.json", receipt)
    assert report.receipt(saved)[0] == "NOT VERIFIED"


def test_failed_receipt_never_passes(saved):
    put(saved, "VERIFICATION.json", dict(status="FAIL", results_sha256=bind(saved, "RESULTS.json"),
        selection_sha256=bind(saved, "SELECTION.json"), frozen_sha256=bind(saved, "FROZEN.json")))
    assert report.receipt(saved)[0] == "NOT VERIFIED"


def test_render_self_contained_safely_escaped(saved):
    out = report.render(saved)
    assert "EA &lt;A&gt;" in out and "EA <A>" not in out
    assert "not future probabilities" in out
    assert "floating drawdown or broker stopout" in out
    assert "NONE QUALIFIED — fallback" in out
    assert "PENDING" in out
    assert "<script" not in out and "<svg" not in out
    assert "Every tested single-EA / risk configuration" in out
    assert "Every tested basket / risk configuration" in out
    assert (saved / "Results.html").read_text(encoding="utf-8") == out


def test_reject_missing_cost(saved):
    values = data(saved)
    values[-1]["results"].pop()
    with pytest.raises(AssertionError):
        report.validate(saved, *values)


def test_reject_duplicate_result(saved):
    values = data(saved)
    values[-1]["results"].append(copy.deepcopy(values[-1]["results"][0]))
    with pytest.raises(AssertionError):
        report.validate(saved, *values)


def test_reject_missing_start(saved):
    values = data(saved)
    values[-1]["results"][0]["attempts"].pop()
    with pytest.raises(AssertionError):
        report.validate(saved, *values)


def test_reject_development_selection_mismatch(saved):
    values = data(saved)
    values[-2]["locked"][0]["development"]["hit_pct"] = 90
    with pytest.raises(AssertionError):
        report.validate(saved, *values)


def test_reject_stale_results_binding(saved):
    values = data(saved)
    values[-1]["selection_sha256"] = "wrong"
    with pytest.raises(AssertionError):
        report.validate(saved, *values)


def test_reject_frozen_file_change(saved):
    (saved / "PLAN.json").write_text("{}", encoding="utf-8")
    with pytest.raises(AssertionError, match="Frozen input changed"):
        report.validate(saved, *data(saved))


def test_expected_starts_all_full_horizon():
    starts = report.expected_starts(["2024-10-06", "2026-10-06"], 365)
    assert len(starts) == 53
    assert report.utc(starts[0]) == "2024-10-07 00:00:00 UTC"
    assert report.utc(starts[-1]) == "2025-10-06 00:00:00 UTC"


def test_nulls_do_not_display_as_zero():
    assert report.number(None) == report.money(None) == report.pct(None) == "—"


def test_attempt_dates_and_skips():
    attempt = dict(start=0, end_exclusive=31536000, status="timeout", hit_epoch=None, hit_days=None,
                   floor_epoch=None, ending_closed_cash=20, open_positions=1, max_closed_dd_pct=80,
                   counts=dict(candidates=7, opened=1, minimum_lot=2, margin_proxy=3, daily_pause=1))
    out = report.attempts_table([attempt])
    assert "1970-01-01 00:00:00 UTC" in out and "1971-01-01 00:00:00 UTC" in out
    assert "daily_pause: 1" in out


def test_details_keep_cash_curve_and_rejection_decisions():
    detail = dict(start=0, ending_closed_cash=101, max_closed_dd_pct=1,
                  trade_stats=dict(trades=1, win_rate_pct=100, profit_factor=None, max_win_streak=1, max_loss_streak=0),
                  closed_positions=[dict(id="a|2", key="a", op=0, cl=5, lots=.01, net=1, risk=2)],
                  decisions=[dict(epoch=0, id="a|2", key="a", decision="opened", budget=2, volume=.01,
                                  planned_stop_risk=2, margin_proxy=1)],
                  curve=[dict(epoch=0, balance=100, open_positions=1), dict(epoch=5, balance=101, open_positions=0)])
    result = dict(summary=dict(fastest=dict(start=0)), attempts=[detail])
    out = report.detail_html(result, detail, {"a": "EA A"})
    assert "retrospectively fastest hit" in out and "middle-ranked ending cash start" in out
    assert "Every completed position" in out and "Every entry admission or rejection decision" in out
    assert "Every saved event-level closed-cash observation" in out
    assert "not measured subsecond execution precision" in out


@pytest.fixture
def recent(saved):
    plan, source, dev, selection, results = data(saved)
    put(saved, "RECENT-PLAN.json", dict(window=plan["evaluation"]))
    put(saved, "RECENT-FROZEN.json", dict(before_full_recent_ranking=True,
        files={str(saved / "RESULTS.json"): bind(saved, "RESULTS.json")}))
    configurations = []
    selected = []
    for kind, cc in (("single", dev["singles"]), ("combo", dev["combos"])):
        for original in cc:
            candidate = next(c for c in results["results"] if c["id"] == original["id"] and c["cost"] == "recorded")
            candidate = copy.deepcopy(candidate)
            del candidate["cost"]
            del candidate["details"]
            configurations.append(candidate)
            for role in ("primary", "fastest_observed"):
                selected.append(dict(kind=kind, role=role, id=candidate["id"], keys=candidate["keys"], risk_pct=candidate["risk_pct"]))
    recent = dict(status="RETROSPECTIVE, NOT VALIDATION", configurations=configurations, selected=selected,
                  sensitivity=copy.deepcopy(results["results"]), recent_frozen_sha256=bind(saved, "RECENT-FROZEN.json"),
                  original_results_sha256=bind(saved, "RESULTS.json"))
    put(saved, "RECENT.json", recent)
    return saved


def test_recent_receipt_is_separate_and_pending(recent):
    assert report.recent_receipt(recent)[0] == "PENDING"
    put(recent, "VERIFICATION.json", dict(status="PASS", results_sha256=bind(recent, "RESULTS.json"),
        selection_sha256=bind(recent, "SELECTION.json"), frozen_sha256=bind(recent, "FROZEN.json")))
    assert report.receipt(recent)[0] == "PASS" and report.recent_receipt(recent)[0] == "PENDING"


def test_recent_matching_hashes_pass(recent):
    put(recent, "RECENT-VERIFICATION.json", dict(status="PASS", checks=1234,
        recent_sha256=bind(recent, "RECENT.json"), recent_frozen_sha256=bind(recent, "RECENT-FROZEN.json"),
        original_results_sha256=bind(recent, "RESULTS.json")))
    assert report.recent_receipt(recent) == ("PASS", "Hash-bound supplemental verification · 1,234 checks")


@pytest.mark.parametrize("field", ["recent_sha256", "recent_frozen_sha256", "original_results_sha256"])
def test_recent_receipt_stale_binding_does_not_pass(recent, field):
    receipt = dict(status="PASS", recent_sha256=bind(recent, "RECENT.json"),
        recent_frozen_sha256=bind(recent, "RECENT-FROZEN.json"), original_results_sha256=bind(recent, "RESULTS.json"))
    receipt[field] = "wrong"
    put(recent, "RECENT-VERIFICATION.json", receipt)
    assert report.recent_receipt(recent)[0] == "NOT VERIFIED"


def test_recent_render_preserves_original_failure_and_evidence(recent):
    protected = ["RESULTS.json", "FROZEN.json", "SELECTION.json", "DEVELOPMENT.json", "RECENT.json", "RECENT-FROZEN.json"]
    before = {name: bind(recent, name) for name in protected}
    out = report.render(recent)
    assert "Both locked primary choices had zero later-evaluation target hits" in out
    assert "Later-period retrospective scoreboard — NOT validation" in out
    assert "not a newly validated recommendation" in out
    assert "Arithmetic verification does not remove retrospective selection bias" in out
    assert "No new forward evidence exists" in out
    assert out.index("Both locked primary choices had zero") < out.index("Later-period retrospective scoreboard — NOT validation")
    assert {name: bind(recent, name) for name in protected} == before


@pytest.mark.parametrize("change", ["extra_config", "missing_cost", "missing_start", "wrong_original", "base_mismatch"])
def test_recent_rejects_incomplete_or_changed_evidence(recent, change):
    values = data(recent)
    scoreboard = report.read(recent, "RECENT.json")
    if change == "extra_config":
        extra = copy.deepcopy(scoreboard["configurations"][0])
        extra["id"] = "newspace@5"
        scoreboard["configurations"].append(extra)
    elif change == "missing_cost":
        scoreboard["sensitivity"].pop()
    elif change == "missing_start":
        scoreboard["configurations"][0]["attempts"].pop()
    elif change == "wrong_original":
        scoreboard["original_results_sha256"] = "wrong"
    else:
        scoreboard["sensitivity"][0]["summary"]["ending_cash_median"] = 999
    with pytest.raises(AssertionError):
        report.validate_recent(recent, values[0], values[2], scoreboard)


@pytest.fixture
def risk(recent):
    plan = report.read(recent, "PLAN.json")
    scoreboard = report.read(recent, "RECENT.json")
    (recent / "risk_sensitivity.py").write_text("# synthetic fixture, not executed", encoding="utf-8")
    protocol = dict(status="RETROSPECTIVE SAME-PERIOD SENSITIVITY, NOT VALIDATION",
                    families=[c for c in scoreboard["selected"] if c["role"] == "primary"],
                    risks=plan["risk_percentages"], window=plan["evaluation"], before_ladder_stress_outcomes=True,
                    script_sha256=bind(recent, "risk_sensitivity.py"), recent_sha256=bind(recent, "RECENT.json"),
                    original_frozen_sha256=bind(recent, "FROZEN.json"))
    put(recent, "RISK-SENSITIVITY-PLAN.json", protocol)
    results = []
    for c in scoreboard["sensitivity"]:
        c = copy.deepcopy(c)
        c["kind"] = "single" if len(c["keys"]) == 1 else "combo"
        del c["id"]
        del c["details"]
        results.append(c)
    put(recent, "RISK-SENSITIVITY.json", dict(status=protocol["status"], results=results,
        protocol_sha256=bind(recent, "RISK-SENSITIVITY-PLAN.json")))
    return recent


def test_risk_receipt_is_separate_pending(risk):
    assert report.risk_receipt(risk)[0] == "PENDING"


def test_risk_receipt_matching_hashes_pass(risk):
    put(risk, "RISK-VERIFICATION.json", dict(status="PASS", checks=321,
        risk_sha256=bind(risk, "RISK-SENSITIVITY.json"), protocol_sha256=bind(risk, "RISK-SENSITIVITY-PLAN.json"),
        recent_sha256=bind(risk, "RECENT.json")))
    assert report.risk_receipt(risk) == ("PASS", "Hash-bound risk-ladder verification · 321 checks")


@pytest.mark.parametrize("field", ["risk_sha256", "protocol_sha256", "recent_sha256"])
def test_risk_receipt_stale_hash_never_passes(risk, field):
    receipt = dict(status="PASS", risk_sha256=bind(risk, "RISK-SENSITIVITY.json"),
                   protocol_sha256=bind(risk, "RISK-SENSITIVITY-PLAN.json"), recent_sha256=bind(risk, "RECENT.json"))
    receipt[field] = "wrong"
    put(risk, "RISK-VERIFICATION.json", receipt)
    assert report.risk_receipt(risk)[0] == "NOT VERIFIED"


def test_risk_table_labels_data_mining_and_lot_limits(risk):
    out = report.render(risk)
    assert "Risk ladder for the two retrospectively selected families" in out
    assert "Same-period sensitivity — NOT new validation" in out
    assert "Zero closed DD in a zero-trade start" in out
    assert "Risk-ladder verification: <strong>PENDING" in out


@pytest.mark.parametrize("change", ["missing_cost", "missing_start", "base_mismatch", "protocol_hash"])
def test_risk_validation_rejects_incomplete_or_stale(risk, change):
    plan = report.read(risk, "PLAN.json")
    recent = report.read(risk, "RECENT.json")
    r = report.read(risk, "RISK-SENSITIVITY.json")
    if change == "missing_cost":
        r["results"].pop()
    elif change == "missing_start":
        r["results"][0]["attempts"].pop()
    elif change == "base_mismatch":
        r["results"][0]["summary"]["ending_cash_median"] = 999
    else:
        r["protocol_sha256"] = "wrong"
    with pytest.raises(AssertionError):
        report.validate_risk(risk, plan, recent, r)
