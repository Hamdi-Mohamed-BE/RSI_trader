"""Independent offline receipts. Never fetches data or computes a trading strategy."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict, Counter
from bisect import bisect_left, bisect_right
import argparse, csv, hashlib, json, math, configparser

R = Path(__file__).resolve().parent
OLD = R.parent/"FTMO Core3 vs Core4 Phase Timing 2026-10-16"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def near(a, b, eps=1e-7):
    return abs(float(a)-float(b)) <= eps*max(1, abs(float(a)), abs(float(b)))


def native_preflight():
    plan, frozen = read(R/"NATIVE-PLAN.json"), read(R/"NATIVE-FROZEN.json")
    checks = []

    def check(name, condition, detail=None):
        checks.append(dict(name=name, passed=bool(condition), detail=detail))
        assert condition, (name, detail)

    for path, expected in frozen["files"].items():
        check("native_frozen_sha256", sha(path) == expected, path)
    for path, expected in plan["production_hashes"].items():
        check("production_source_closure_sha256", sha(path) == expected, path)
    long_plan = read(R.parent/"Portfolio Long History All ORB05 2026-10-14"/"PLAN.json")
    case_id = long_plan["mappings"]["ftmo"]["nasdaq-5m-candle-momentum"]
    old_row = next(v for v in long_plan["cases"] if v["case_id"] == case_id)
    new_row = plan["row"]
    check("all_row_metadata_identical", {k:v for k,v in new_row.items() if k != "input_settings"} ==
          {k:v for k,v in old_row.items() if k != "input_settings"})
    differences = {k:[old_row["input_settings"].get(k), new_row["input_settings"].get(k)]
                   for k in set(old_row["input_settings"]) | set(new_row["input_settings"])
                   if old_row["input_settings"].get(k) != new_row["input_settings"].get(k)}
    check("nasdaq_only_di_false", differences == {"InpRequireDIAgreement": ["true", "false"]})
    check("same_native_source_period", plan["source_period"] == ["2021.10.06", "2026.10.06"])
    check("same_native_model_delay", plan["model"] == 4 and plan["delay_ms"] == 150)
    check("source_risk_normalization_unchanged", plan["source_risk_percent"] == 1 and new_row["input_settings"]["InpRiskPercent"] == "1.0")
    old_source = Path(read(OLD/"SOURCE-COVERAGE.json")["coverage"][0]["source_result"])
    archive = read(old_source.parent/"manifest.json")
    check("same_native_observer_bytes", sha(R/"ReadOnlyAudit.mqh") == archive["build"]["audit_sha256"])
    check("same_production_source_closure", plan["production_hashes"] == archive["build"]["production_hashes"])
    check("same_replay_engine_bytes", sha(R/"run.py") == sha(OLD/"run.py") ==
          "83c09daf588cc46206e32eb2950e5c09977ef352065e143feb4e39141a1bf63c")
    profile = Path(plan["empty_profile"])
    check("empty_research_chart_profile", profile.is_dir() and not list(profile.glob("*.chr")))
    owned = read(old_source.parent/"owned-process.json")
    check("same_research_terminal_path", Path(owned["executable"]) == Path(plan["tester"])/"terminal64.exe")
    check("not_regular_terminal_path", "Program Files" not in plan["tester"] and plan["agent_port"] == 3010)
    helper_path = R.parent/"ORB and Range Breakout RR05 Comparison 2026-10-08"/"run.py"
    helper = helper_path.read_text(encoding="utf-8-sig")
    for text in ("Enabled=0", "AllowLiveTrading=0", "AllowDllImport=0", "UseRemote=0", "UseCloud=0",
                 "if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED", "/portable /profile:"):
        check("isolated_native_runner_safety_literal", text in helper, text)
    check("native_scope_no_live_changes", plan["isolated"] and plan["no_live_account_api"] and
          not plan["live_changes"] and not plan["optimization"])
    result = dict(status="NATIVE_PREFLIGHT_PASS", checked_utc=datetime.now(timezone.utc).isoformat(),
                  checks=len(checks), failed=0, native_plan_sha256=sha(R/"NATIVE-PLAN.json"),
                  native_frozen_sha256=sha(R/"NATIVE-FROZEN.json"), only_parameter_difference=differences,
                  source_closure_and_observer_identical_to_archived_di_on=True,
                  regular_terminal_api_access_by_verifier=False,
                  price_cache_identity_to_old_run="UNPROVEN: archived manifest has no historical HCC/TKC byte hashes.",
                  details=checks)
    (R/"INDEPENDENT-NATIVE-PREFLIGHT.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "details"}, indent=2))
    return result


def native_completion():
    native_preflight()
    run = read(R/"NATIVE-RUN.json")
    path = Path(run["path"])
    assert sha(path) == run["sha256"]
    actual, manifest = read(path), read(path.parent/"manifest.json")
    old_path = Path(read(OLD/"SOURCE-COVERAGE.json")["coverage"][0]["source_result"])
    old, old_manifest = read(old_path), read(old_path.parent/"manifest.json")
    assert run["complete"] and run["source_only_DI_toggle"] and run["live_processes_preserved"]
    assert manifest["inputs"]["InpRequireDIAgreement"] == "false"
    assert actual["inputs"]["InpRequireDIAgreement"] == "false"
    assert manifest["build"]["source_copy_sha256"] == old_manifest["build"]["source_copy_sha256"]
    assert manifest["build"]["callbacks"] == old_manifest["build"]["callbacks"]
    assert manifest["build"]["patches"] == []
    assert manifest["build"]["compile"] == "0 errors, 0 warnings"
    config, old_config = configparser.ConfigParser(), configparser.ConfigParser()
    config.read(path.parent/"tester.ini", encoding="utf-8-sig")
    old_config.read(old_path.parent/"tester.ini", encoding="utf-8-sig")
    ignored = {"expert", "expertparameters", "report"}
    differences = [(section, key, old_config[section].get(key), value)
                   for section in config.sections() for key, value in config[section].items()
                   if key not in ignored and old_config[section].get(key) != value]
    assert not differences, differences
    before = {v["path"]:v for v in read(R/"NATIVE-CACHE-BEFORE.json")["files"]}
    after = {v["path"]:v for v in read(R/"NATIVE-CACHE-AFTER.json")["files"]}
    changed = [p for p in before if p not in after or before[p]["sha256"] != after[p]["sha256"]]
    old_trades = {(v["open_epoch"], v["side"]):v for v in old["trades"]}
    new_trades = {(v["open_epoch"], v["side"]):v for v in actual["trades"]}
    assert len(old_trades) == len(old["trades"]) and len(new_trades) == len(actual["trades"])
    common = sorted(old_trades.keys() & new_trades.keys())
    entry_fields = ("open_price", "sl", "tp")
    exit_fields = ("close_epoch", "close_price")
    entry_diffs, exit_diffs = [], []
    begin, end = read(R/"INPUTS.json")["year_begin_epoch"], read(R/"INPUTS.json")["year_end_exclusive_epoch"]
    natural = 0
    for key in common:
        a, b = old_trades[key], new_trades[key]
        if any(not near(a[k], b[k], 1e-10) for k in entry_fields):
            entry_diffs.append(dict(epoch=key[0], side=key[1], old={k:a[k] for k in entry_fields},
                                    new={k:b[k] for k in entry_fields}))
        if any("end of test" in s.lower() for s in a["exit_comments"]+b["exit_comments"]):
            continue
        natural += 1
        if any(not near(a[k], b[k], 1e-10) for k in exit_fields):
            exit_diffs.append(dict(epoch=key[0], side=key[1], old={k:a[k] for k in exit_fields},
                                   new={k:b[k] for k in exit_fields}))
    result = dict(status="NATIVE_COMPLETION_PASS", verified_utc=datetime.now(timezone.utc).isoformat(),
                  native_results_sha256=sha(path), source_copy_and_callbacks_identical=True,
                  only_strategy_input_changed="InpRequireDIAgreement=true→false", tester_configuration_differences=differences,
                  history_quality=actual["native"]["history_quality"], tick_notes=actual["tick_notes"],
                  regular_terminal_processes_preserved=run["live_processes_preserved"],
                  cache_files_before=len(before), cache_files_after=len(after), changed_cache_files=changed,
                  added_cache_files=[p for p in after if p not in before],
                  common_entries_full_source=len(common), common_entries_matching_year=sum(begin <= k[0] < end for k in common),
                  entry_geometry_mismatches=entry_diffs, comparable_natural_exits=natural, natural_exit_geometry_mismatches=exit_diffs,
                  inference="Common entry/SL/TP and natural-exit geometry is a limited overlap sanity check, NOT proof of old/fresh market-cache byte identity. Source volumes/P&L intentionally not compared because independent source capital paths differ.",
                  archived_price_cache_identity="UNPROVEN: original DI-on run retained no historical HCC/TKC byte hashes.")
    (R/"INDEPENDENT-NATIVE-COMPLETION.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("entry_geometry_mismatches", "natural_exit_geometry_mismatches")}, indent=2))
    print("ENTRY_GEOMETRY_MISMATCHES", len(entry_diffs), "NATURAL_EXIT_GEOMETRY_MISMATCHES", len(exit_diffs))
    return result


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
    old_plan, old_inputs = read(OLD/"PLAN.json"), read(OLD/"INPUTS.json")
    check("byte_identical_approved_replay_engine", sha(R/"run.py") == sha(OLD/"run.py") ==
          "83c09daf588cc46206e32eb2950e5c09977ef352065e143feb4e39141a1bf63c")
    check("same_paired_starts_and_exclusions", inputs["starts"] == old_inputs["starts"] and
          inputs["excluded_starts"] == old_inputs["excluded_starts"])
    for key in ("baskets", "history", "scenarios", "risk", "guard", "float_model", "costs", "ordering", "phases", "candidate_priority"):
        check("same_registered_method_as_di_on", plan[key] == old_plan[key], key)
    check("no_outcomes_at_initial_freeze", frozen["no_outcomes_computed"] is True)
    check("no_live_or_optimization", plan["live_changes"] is False and
          plan["optimization"] is False and plan["native_simultaneous"] is False)
    check("fixed_baskets", plan["baskets"] == {
        "CORE3": ["nasdaq-5m-candle-momentum", "usdjpy-london-open-momentum", "us100-month-end-flow"],
        "CORE4": ["nasdaq-5m-candle-momentum", "usdjpy-london-open-momentum", "us100-month-end-flow", "xau-rsi-vwap"]})
    package_path = next(p for p in frozen["source_files"] if p.endswith("FTMO\\PACKAGE.json"))
    package = read(package_path)
    current = {v["slug"]: v for v in package["entries"]}
    check("manifest_candidate_priority", plan["candidate_priority"] ==
          [v["slug"] for v in package["entries"] if v["slug"] in plan["baskets"]["CORE4"]])
    candidates = inputs["candidates"]
    old_unchanged = {v["id"]:v for v in old_inputs["candidates"] if v["ea"] != "nasdaq-5m-candle-momentum"}
    new_unchanged = {v["id"]:v for v in candidates if v["ea"] != "nasdaq-5m-candle-momentum"}
    check("other_three_source_payloads_identical", old_unchanged == new_unchanged)
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
        native_params = receipt["source_parameters"]
        param_diff = {k: [native_params.get(k), current[slug]["inputs"].get(k)]
                      for k in set(native_params) | set(current[slug]["inputs"])
                      if native_params.get(k) != current[slug]["inputs"].get(k)}
        expected_param_diff = {"InpRiskPercent": ["1.0", "0.5"]}
        if slug == "nasdaq-5m-candle-momentum":
            expected_param_diff["InpRequireDIAgreement"] = ["false", "true"]
        check("current_variant_only_registered_risk_and_nasdaq_di_diff", param_diff == expected_param_diff, slug)
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
            expected_unit_risk = abs(t["open_price"]-t["sl"])*contract/(t["sl"] if row["symbol"] == "USDJPY" else 1.)
            check("risk_from_this_native_position_not_reused_di_on_id", near(row["unit_risk"], expected_unit_risk) and
                  expected_unit_risk > 0 and math.isfinite(expected_unit_risk), row["id"])
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
                        ("engine_sha256", "run.py"), ("frozen_sha256", "FROZEN.json")):
        check("output_binding", outputs[field] == sha(R/name), field)
    check("summary_output_binding", summary["outcomes_sha256"] == sha(R/"OUTCOMES.json"))
    starts = {(v["date"], v["epoch"], v["horizon_epoch"]) for v in data["starts"]}
    trial_keys = set()
    closed_positions = open_positions = 0
    sizing_max_diff = 0.
    for trial in outputs["trials"]:
        key = (trial["portfolio"], trial["start_date"], trial["cost"], trial["handover"])
        check("unique_paired_trial", key not in trial_keys, key); trial_keys.add(key)
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
    check("all_registered_1072_trials", len(trial_keys) == len(data["starts"])*len(plan["scenarios"])*2 == 1072)
    fixtures = read(R/"INDEPENDENT-FIXTURE-TESTS.json")
    check("fixtures_bound_current_engine", fixtures["status"] == "PASS" and fixtures["failed"] == 0 and fixtures["engine_sha256"] == sha(R/"run.py"))
    native_receipt = read(R/"INDEPENDENT-NATIVE-COMPLETION.json")
    check("genuine_native_di_off_completion", native_receipt["status"] == "NATIVE_COMPLETION_PASS" and
          not native_receipt["entry_geometry_mismatches"] and not native_receipt["natural_exit_geometry_mismatches"] and
          native_receipt["source_copy_and_callbacks_identical"])
    result = dict(status="FINAL_PASS", checked_utc=datetime.now(timezone.utc).isoformat(),
                  summary_sha256=sha(R/"SUMMARY.json"), outcomes_sha256=sha(R/"OUTCOMES.json"),
                  engine_sha256=sha(R/"run.py"), frozen_sha256=sha(R/"FROZEN.json"),
                  verifier_sha256=sha(Path(__file__)), fixture_script_sha256=sha(R/"test_independent_guard.py"),
                  native_completion_receipt_sha256=sha(R/"INDEPENDENT-NATIVE-COMPLETION.json"),
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
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--native-final", action="store_true")
    args = parser.parse_args()
    native_completion() if args.native_final else native_preflight() if args.native else final_verify() if args.final else preflight()


