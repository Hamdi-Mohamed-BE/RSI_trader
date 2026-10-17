"""Independent offline receipts. Never fetches data or computes a trading strategy."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict, Counter
from bisect import bisect_left, bisect_right
import argparse, csv, hashlib, json, math

R = Path(__file__).resolve().parent
OLD = R.parent/"FTMO Core3 vs Core4 Phase Timing 2026-10-16"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def near(a, b, eps=1e-7):
    return abs(float(a)-float(b)) <= eps*max(1, abs(float(a)), abs(float(b)))


def preflight():
    plan, inputs, coverage, frozen = [read(R/name) for name in (
        "PLAN.json", "INPUTS.json", "SOURCE-COVERAGE.json", "FROZEN.json")]
    checks = []

    def check(name, ok, detail=None):
        checks.append(dict(name=name, passed=bool(ok), detail=detail))
        if not ok:
            raise AssertionError((name, detail))

    for group in ("files", "source_files"):
        for path, expected in frozen[group].items():
            check("frozen_sha256", sha(path) == expected, path)
    check("no_outcomes_at_initial_freeze", frozen["no_outcomes_computed"] is True)
    check("no_live_or_optimization", plan["live_changes"] is False and
          plan["optimization"] is False and plan["native_simultaneous"] is False)
    old_plan, old_inputs = read(OLD/"PLAN.json"), read(OLD/"INPUTS.json")
    check("fixed_twelve_baskets", len(plan["baskets"]) == 12 and plan["baskets"]["CORE4"] == old_plan["baskets"]["CORE4"] and plan["baskets"]["CORE3"] == old_plan["baskets"]["CORE3"])
    for key in ("history", "scenarios", "risk", "guard", "float_model", "costs", "ordering", "phases"):
        check("same_registered_account_model", plan[key] == old_plan[key], key)
    check("same_paired_starts", inputs["starts"] == old_inputs["starts"] and inputs["excluded_starts"] == old_inputs["excluded_starts"])
    check("byte_identical_core_engine", sha(R/"core_engine.py") == sha(OLD/"run.py") == "83c09daf588cc46206e32eb2950e5c09977ef352065e143feb4e39141a1bf63c")
    old_rows = {x["id"]: x for x in old_inputs["candidates"]}
    check("baseline_four_source_payloads_unchanged", {x["id"]:x for x in inputs["candidates"] if x["ea"] in plan["baskets"]["CORE4"]} == old_rows)
    package_path = next(p for p in frozen["source_files"] if p.endswith("FTMO\\PACKAGE.json"))
    package = read(package_path)
    current = {v["slug"]: v for v in package["entries"]}
    check("manifest_candidate_priority", plan["candidate_priority"] ==
          [v["slug"] for v in package["entries"] if v["slug"] in {x["ea"] for x in inputs["candidates"]}])
    candidates = inputs["candidates"]
    check("unique_source_position_ids", len({v["id"] for v in candidates}) == len(candidates))
    grouped = defaultdict(list)
    for row in candidates:
        grouped[row["ea"]].append(row)
    summary = []
    all_marks = 0
    source_trade_count = 0
    for receipt in coverage["coverage"]:
        slug = receipt["ea"]
        source = Path(receipt["source_result"])
        native = read(source)
        trades = {v["position_id"]: v for v in native["trades"]}
        ordered_trades = sorted(native["trades"], key=lambda v: (v["open_epoch"], v["position_id"]))
        check("no_partial_source_lifecycles", all(not v["partial"] for v in ordered_trades), slug)
        check("unique_source_position_float_ownership", all(a["close_epoch"] <= b["open_epoch"]
              for a, b in zip(ordered_trades, ordered_trades[1:])), slug)
        native_params = receipt["source_parameters"]
        param_diff = {k: [native_params.get(k), current[slug]["inputs"].get(k)]
                      for k in set(native_params) | set(current[slug]["inputs"])
                      if native_params.get(k) != current[slug]["inputs"].get(k)}
        expected_diff = {"InpRiskPercent": ["1.0", "0.5"]}
        if slug == "ema3": expected_diff["InpGridRiskPercent"] = ["1.0", "0.5"]  # inactive strategy-ID8 grid input; EMA3 is ID1
        check("current_variant_only_risk_normalization_diff", param_diff == expected_diff, slug)
        rows = list(csv.DictReader((source.parent/"deals.csv").open(encoding="utf-8-sig")))
        by_pid = defaultdict(list)
        for row in rows:
            by_pid[int(row["position_id"])].append(row)
        marks = {}
        with (source.parent/"equity.csv").open(encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                ep = int(row["epoch"])
                if ep not in marks:
                    marks[ep] = (float(row["balance"]), float(row["equity"]))
        check("source_covers_prague_year", min(marks) <= inputs["year_begin_epoch"] and
              max(marks) >= inputs["year_end_exclusive_epoch"], slug)
        eligible_mark_epochs = sorted(ep for ep in marks if inputs["year_begin_epoch"]-900 <= ep < inputs["year_end_exclusive_epoch"])
        for row in grouped[slug]:
            source_trade_count += 1
            t = trades[row["position_id"]]
            check("candidate_entry_identity", row["op"] == t["open_epoch"] and
                  near(row["source_volume"], t["volume"]) and near(row["sl"], t["sl"]), row["id"])
            contract = {"USTEC": 1., "XAUUSD": 100., "USDJPY": 100000.}[row["symbol"]]
            native_unit_risk = abs(t["open_price"]-t["sl"])*contract/(t["sl"] if row["symbol"] == "USDJPY" else 1.)
            check("stop_risk_from_own_native_initial_sl", near(row["unit_risk"], native_unit_risk) and native_unit_risk > 0, row["id"])
            check("candidate_within_registered_year", inputs["year_begin_epoch"] <= row["op"] <
                  inputs["year_end_exclusive_epoch"], row["id"])
            legs = by_pid[row["position_id"]]
            entries = [d for d in legs if int(d["entry"]) == 0]
            check("one_exact_opening_deal", len(entries) == 1, row["id"])
            check("entry_cost_causal", near(row["entry_unit_cost"],
                  sum(float(entries[0][k]) for k in ("gross", "commission", "swap", "fee"))/t["volume"]), row["id"])
            for field, native_key in (("unit_gross", "gross"), ("unit_swap", "swap")):
                check("native_lifecycle_cash", near(row[field], t[native_key]/t["volume"]), [row["id"], field])
            check("all_fees_preserved", near(row["unit_commission"], (t["commission"]+t["fee"])/t["volume"]), row["id"])
            check("source_forced_close_not_natural", (row["cl"] is None and row["end_censored"] and
                  row["source_forced_close_epoch"] == t["close_epoch"]) if any("end of test" in s.lower() for s in t["exit_comments"])
                  else row["cl"] == t["close_epoch"] and not row["end_censored"], row["id"])
            expected_epochs = eligible_mark_epochs[bisect_right(eligible_mark_epochs, t["open_epoch"]):
                                                  bisect_left(eligible_mark_epochs, t["close_epoch"])]
            check("all_owned_marks_retained_without_selection", [v[0] for v in row["marks"]] == expected_epochs, row["id"])
            previous = -math.inf
            for ep, unit_float, volume, balance, equity in row["marks"]:
                all_marks += 1
                check("owned_mark_strictly_interior", t["open_epoch"] < ep < t["close_epoch"] and ep > previous, row["id"])
                check("owned_mark_exact_source", marks[ep] == (balance, equity) and near(volume, t["volume"]) and
                      near(unit_float, (equity-balance)/volume), [row["id"], ep])
                previous = ep
        check("source_candidate_count", len(grouped[slug]) == receipt["candidates"], slug)
        check("source_mark_count", sum(len(v["marks"]) for v in grouped[slug]) == receipt["owned_marks"], slug)
        summary.append(dict(ea=slug, candidates=len(grouped[slug]), owned_marks=receipt["owned_marks"],
                            no_owned_mark=receipt["positions_without_owned_interior_mark"],
                            history_quality=receipt["history_quality"],
                            tick_notes=receipt["tick_notes"], parameter_differences=param_diff))
    ties = defaultdict(list)
    for row in candidates:
        ties[row["op"]].append(row["ea"])
    entry_ties = [{"epoch": ep, "eas": rows} for ep, rows in sorted(ties.items()) if len(set(rows)) > 1]
    ustec_pair = [v for v in entry_ties if {"nasdaq-5m-candle-momentum", "us100-month-end-flow"}.issubset(v["eas"])]
    check("registered_requested_risk", plan["risk"]["source_requested_risk_percent"] == .5 and
          plan["risk"]["fixed_guard_allocation"] == 50 and plan["risk"]["initial_balance"] == 10000)
    check("registered_guard_caps", all(plan["guard"][k] == v for k, v in {
          "persistent_daily_entry_stop_loss": 300, "permanent_static_equity_floor": 9000,
          "permanent_daily_equity_loss": 500, "admission_equity_buffer": 9200,
          "aggregate_initial_risk_cap": 225, "same_symbol_initial_risk_cap": 150,
          "daily_entry_cap": 7, "daily_completed_losses_cap": 3, "entry_cooldown_seconds": 3}.items()))
    result = dict(status="PREFLIGHT_PASS", checked_utc=datetime.now(timezone.utc).isoformat(),
                  no_portfolio_outcomes_computed_by_this_script=True, plan_sha256=sha(R/"PLAN.json"),
                  inputs_sha256=sha(R/"INPUTS.json"), frozen_sha256=sha(R/"FROZEN.json"),
                  checks=len(checks), failed_checks=0, source_trade_count=source_trade_count,
                  owned_marks_checked=all_marks, sources=summary,
                  same_second_cross_ea_entries=entry_ties, same_second_ustec_pair_ties=ustec_pair,
                  limitations=["Estimated ledger replay, not a simultaneous native FTMO-server test.",
                      "First mark at opening second excluded because source observes before strategy callback.",
                      "Initial floating zero and stale owned mark carry are declared model approximations.",
                      "Only five-minute sampled equity; between-mark breaches can be missed.",
                      "Filled initial SL risk approximates requested quote geometry; current SL and extra swap reserve unavailable.",
                      "Immutable source exits omit counterfactual signals after a rejected source trade.",
                      "Source whole-history quality15% real ticks; real ticks begin2026Jan1.",
                      "Market-time3second wait/manifest order is not historical live cross-chart fill-race evidence."],
                  guard_implementation_audit=("See INDEPENDENT-FIXTURE-TESTS.json and INDEPENDENT-VERIFICATION.json for implementation/final checks."
                      if (R/"run.py").exists() else "PENDING run.py creation; source/plan/data preflight only"))
    (R/"INDEPENDENT-PREFLIGHT.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("sources", "same_second_cross_ea_entries", "limitations")}, indent=2))
    return result


def final_verify():
    pre = preflight()
    plan, data, outputs, summary = [read(R/n) for n in ("PLAN.json", "INPUTS.json", "OUTCOMES.json", "SUMMARY.json")]
    candidates = {v["id"]: v for v in data["candidates"]}
    mark_epochs = {k: [m[0] for m in v["marks"]] for k, v in candidates.items()}
    priority = {v: i for i, v in enumerate(plan["candidate_priority"])}
    prague = ZoneInfo("Europe/Prague")
    checks = Counter()

    def check(name, condition, detail=None):
        checks[name] += 1
        assert condition, (name, detail)

    def local_day(epoch):
        return datetime.fromtimestamp(epoch, prague).date()

    def unit_float(row, epoch):
        index = bisect_right(mark_epochs[row["id"]], epoch)-1
        return row["marks"][index][1] if index >= 0 else 0.

    def side_cost(row, side):
        price = row["open_price"] if side == "entry" else row["close_price"]
        return 1. if row["symbol"] == "USTEC" else 10. if row["symbol"] == "XAUUSD" else 1000./price

    for field, name in (("plan_sha256", "PLAN.json"), ("inputs_sha256", "INPUTS.json"),
                        ("engine_sha256", "core_engine.py"), ("orchestrator_sha256", "run.py"), ("frozen_sha256", "FROZEN.json")):
        check("output_binding", outputs[field] == sha(R/name), field)
    check("summary_output_binding", summary["outcomes_sha256"] == sha(R/"OUTCOMES.json"))
    starts = {(v["date"], v["epoch"], v["horizon_epoch"]) for v in data["starts"]}
    prior = {(t["portfolio"], t["start_date"], t["cost"], t["handover"]): t
             for t in read(OLD/"OUTCOMES.json")["trials"]}
    trial_keys = set()
    closed_positions = open_positions = 0
    sizing_max_diff = 0.
    for trial in outputs["trials"]:
        key = (trial["portfolio"], trial["start_date"], trial["cost"], trial["handover"])
        check("unique_paired_trial", key not in trial_keys, key); trial_keys.add(key)
        if trial["portfolio"] in ("CORE3", "CORE4"):
            check("full_original_baseline_trial_parity", trial == prior[key], key)
        check("registered_start_and_horizon", (trial["start_date"], trial["start_epoch"], trial["horizon_epoch"]) in starts, key)
        check("trial_fixed_basket", trial["portfolio"] in plan["baskets"], key)
        records = []
        seen = set()
        for trade in trial["trades"]:
            check("unique_closed_source_position", trade["id"] not in seen, [key, trade["id"]]); seen.add(trade["id"])
            row = candidates[trade["id"]]
            check("closed_source_identity", row["op"] == trade["op"] and row["cl"] == trade["cl"] and
                  row["ea"] == trade["ea"] and not row["end_censored"], [key, trade["id"]])
            check("filled_source_inside_horizon", trial["start_epoch"] <= trade["op"] <= trade["cl"] < trial["horizon_epoch"], [key, trade["id"]])
            check("entry_cash_full_cost", near(trade["entry_cash"], round(row["entry_unit_cost"]*trade["lots"] -
                  (side_cost(row, "entry")*trade["lots"] if trial["cost"] == "fixed_cost_stress" else 0), 2)), trade["id"])
            swap = row["unit_swap"]*(2 if trial["cost"] == "fixed_cost_stress" and row["unit_swap"] < 0 else 1)
            exit_cash = round((row["unit_gross"]+row["unit_commission"]+swap-row["entry_unit_cost"])*trade["lots"] -
                              (side_cost(row, "exit")*trade["lots"] if trial["cost"] == "fixed_cost_stress" else 0), 2)
            check("exit_cash_full_cost", near(trade["exit_cash"], exit_cash), trade["id"])
            check("whole_position_cash_conservation", near(trade["net"], round(trade["entry_cash"]+trade["exit_cash"], 2)), trade["id"])
            check("filled_stop_risk", near(trade["initial_stop_risk"], row["unit_risk"]*trade["lots"]) and trade["initial_stop_risk"] <= 50+1e-7, trade["id"])
            records.append(dict(row=row, lots=trade["lots"], phase=trade["phase"],
                                entry_cash=trade["entry_cash"], exit_cash=trade["exit_cash"], trade=trade))
            closed_positions += 1
        current_phase = 2 if trial["phase2"]["activation_epoch"] is not None else 1
        for position in trial["open_positions_at_horizon"]:
            check("open_not_duplicated_in_closed", position["id"] not in seen, [key, position["id"]]); seen.add(position["id"])
            row = candidates[position["id"]]
            check("open_end_censored_or_future_natural_close", row["cl"] is None or row["cl"] >= trial["horizon_epoch"], row["id"])
            check("open_stop_risk", near(position["initial_risk"], row["unit_risk"]*position["lots"]) and position["initial_risk"] <= 50+1e-7, row["id"])
            fee = round(row["entry_unit_cost"]*position["lots"] -
                        (side_cost(row, "entry")*position["lots"] if trial["cost"] == "fixed_cost_stress" else 0), 2)
            records.append(dict(row=row, lots=position["lots"], phase=current_phase, entry_cash=fee,
                                exit_cash=None, trade=None))
            open_positions += 1
        for record in records:
            check("only_selected_eas", record["row"]["ea"] in plan["baskets"][trial["portfolio"]], key)
            phase = trial["phase"+str(record["phase"])]; terminal_fail = phase["fail_epoch"]
            check("never_enter_after_hard_failure", terminal_fail is None or record["row"]["op"] <= terminal_fail, key)
            check("entry_not_before_phase_activation", record["row"]["op"] >= phase["activation_epoch"], key)
            check("no_source_finalization_pass", not record["row"]["end_censored"] or record["exit_cash"] is None, key)
        events = []
        if current_phase == 2:
            events.append((trial["phase2"]["activation_epoch"], 0, -1, "", "reset", None))
        for record in records:
            row = record["row"]; pri = priority[row["ea"]]
            events.append((row["op"], 3, pri, row["id"], "entry", record))
            if record["exit_cash"] is not None:
                events.append((row["cl"], 4 if row["cl"] == row["op"] else 1, pri, row["id"], "exit", record))
        events.sort(key=lambda e: e[:4])
        balance = anchor = 10000.; today = None; active = {}; last_entry = -math.inf
        phase_entry_days = defaultdict(set); daily_entries = daily_losses = 0
        for epoch, kind, pri, identity, action, record in events:
            d = local_day(epoch)
            if d != today:
                anchor = balance; today = d; daily_entries = daily_losses = 0
            if action == "reset":
                check("fresh_phase2_flat", not active, key)
                balance = anchor = 10000.; last_entry = -math.inf; daily_entries = daily_losses = 0
                continue
            row = record["row"]
            if action == "exit":
                check("exit_has_exact_opening_position", identity in active, [key, identity])
                balance = round(balance+record["exit_cash"], 2)
                active.pop(identity); daily_losses += record["trade"]["net"] < -.005
                check("replay_exit_cash_balance", near(balance, record["trade"]["balance_after_close"]), [key, identity])
                continue
            eq = balance+sum(unit_float(p["row"], epoch)*p["lots"] for p in active.values())
            spec = plan["risk"]["specs"][row["symbol"]]
            request = min(spec["maximum"], max(spec["minimum"],
                          math.ceil((min(eq*.005/row["unit_risk"], spec["maximum"])-1e-12)/spec["step"])*spec["step"]))
            expected_lot = max(0., round(math.floor(min(request, 50/row["unit_risk"], spec["maximum"])/spec["step"]+1e-9)*spec["step"], 8))
            check("causal_dynamic_requested_then_capped_lots", near(expected_lot, record["lots"]) and expected_lot >= spec["minimum"]-1e-9, [key, identity, eq])
            if record["trade"]:
                check("reported_source_requested_lots", near(record["trade"]["source_requested_lots"], request), identity)
            risk = row["unit_risk"]*record["lots"]
            total = sum(p["row"]["unit_risk"]*p["lots"] for p in active.values())
            same = sum(p["row"]["unit_risk"]*p["lots"] for p in active.values() if p["row"]["symbol"] == row["symbol"])
            reserve = sum(1.25*p["row"]["unit_risk"]*p["lots"]+5 for p in active.values())
            projected = min(eq, balance-reserve)-1.25*risk-5
            margin = lambda p: p["lots"]*plan["risk"]["specs"][p["row"]["symbol"]]["contract"]*(1 if p["row"]["symbol"] == "USDJPY" else p["row"]["open_price"])/plan["risk"]["specs"][p["row"]["symbol"]]["leverage"]
            old_margin = sum(margin(p) for p in active.values()); new_margin = margin(record)
            check("admitted_source_guard_caps", total+risk <= 225+1e-7 and same+risk <= 150+1e-7 and
                  projected >= 9200-1e-8 and anchor-projected <= 300+1e-8, [key, identity])
            check("admitted_margin_proxy", old_margin+new_margin <= projected*.8+1e-8 and new_margin <= eq-old_margin+1e-8, [key, identity])
            check("admitted_daily_count_caps", daily_entries < 7 and daily_losses < 3, [key, identity])
            check("admitted_reconciliation_wait", epoch >= last_entry+3, [key, identity])
            check("admitted_no_current_hard_or_soft_breach", eq > 9000-1e-8 and eq > anchor-300-1e-8, [key, identity])
            target = 11000 if record["phase"] == 1 else 10500
            check("admitted_not_target_held", not (balance >= target-1e-8 and len(phase_entry_days[record["phase"]]) >= 4), [key, identity])
            balance = round(balance+record["entry_cash"], 2); active[identity] = record
            daily_entries += 1; last_entry = epoch; phase_entry_days[record["phase"]].add(str(d))
        check("ending_cash_all_costs_and_fresh_reset", near(balance, trial["ending_balance"]), key)
        expected_equity = balance+sum(unit_float(p["row"], trial["horizon_epoch"]-1e-4)*p["lots"] for p in active.values())
        check("ending_owned_past_mark_equity", near(expected_equity, trial["ending_sampled_equity"]), key)
        check("closed_and_open_counts", len(records) == trial["counts"].get("opened", 0) and
              len(trial["trades"]) == trial["counts"].get("closed", 0), key)
        for phase_no in (1, 2):
            phase = trial["phase"+str(phase_no)]
            check("phase_entry_day_count", phase["entry_days"] == len(phase_entry_days[phase_no]) and
                  phase["entry_dates"] == sorted(phase_entry_days[phase_no]), [key, phase_no])
            if phase["status"] == "passed":
                target = 11000 if phase_no == 1 else 10500
                check("phase_pass_flat_cash_target", phase["terminal_balance"] >= target-1e-8 and phase["entry_days"] >= 4 and
                      near(phase["terminal_balance"], 10000+sum(t["net"] for t in trial["trades"] if t["phase"] == phase_no and t["cl"] <= phase["pass_epoch"])), [key, phase_no])
                check("phase_pass_strictly_before_deadline", phase["pass_epoch"] < trial["horizon_epoch"], key)
    check("all_registered_6432_trials", len(trial_keys) == len(data["starts"])*len(plan["scenarios"])*len(plan["baskets"]) == 6432)
    fixtures = read(R/"INDEPENDENT-FIXTURE-TESTS.json")
    check("fixtures_bound_current_engine", fixtures["status"] == "PASS" and fixtures["failed"] == 0 and fixtures["engine_sha256"] == sha(R/"core_engine.py"))
    result = dict(status="FINAL_PASS", checked_utc=datetime.now(timezone.utc).isoformat(),
                  summary_sha256=sha(R/"SUMMARY.json"), outcomes_sha256=sha(R/"OUTCOMES.json"),
                  engine_sha256=sha(R/"core_engine.py"), orchestrator_sha256=sha(R/"run.py"), frozen_sha256=sha(R/"FROZEN.json"),
                  verifier_sha256=sha(Path(__file__)), fixture_script_sha256=sha(R/"test_independent_guard.py"),
                  source_preflight_checks=pre["checks"], assertions=sum(checks.values()),
                  assertion_groups=dict(checks), paired_trials=len(trial_keys),
                  accepted_closed_position_occurrences_checked=closed_positions,
                  open_position_occurrences_checked=open_positions, synthetic_fixtures=fixtures["total"],
                  no_live_changes=True, statistical_denominator_audit="Owned separately by statistical_verify.py",
                  conclusion="All saved replay cash, source risks, accepted sizing/caps/margins, causal source marks and natural phase passes reconcile. This does not validate missing intratick equity or real FTMO execution.")
    (R/"INDEPENDENT-VERIFICATION.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    final_verify() if args.final else preflight()


