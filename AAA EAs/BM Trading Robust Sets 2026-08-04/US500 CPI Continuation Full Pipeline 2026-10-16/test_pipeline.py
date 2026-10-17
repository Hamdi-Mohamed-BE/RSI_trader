"""Read-only protocol tests: no MT5 API, compiler, tester or research launch."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import ast
import copy
import hashlib
import inspect
import itertools
import json
import math
import sys
import unittest

sys.dont_write_bytecode = True
R = Path(__file__).resolve().parent
sys.path.insert(0, str(R))
import build_engine
import search_plan


def read(name):
    return (R / name).read_text(encoding="utf-8")


def load(name):
    return json.loads(read(name))


def sha(name):
    return hashlib.sha256((R / name).read_bytes()).hexdigest()


BASE = dict(hold_minutes=15, target_r=1.5, entry_window_minutes=5,
            impulse_mult=1.0, close_fraction=0.25)
SEARCH_AXES = {"target_r", "hold_minutes", "impulse_mult"}


class PipelineProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load("config.json")
        cls.split = load("DATA-SPLIT.json")
        cls.plan = load("SEARCH-PLAN.json")
        cls.engine = read("engine.mq5")
        cls.orchestrator = read("run_pipeline.py")

    def test_scope_and_fixed_risk(self):
        cfg = self.config
        self.assertEqual(cfg["symbol"], "US500")
        self.assertEqual(cfg["event_types"], ["CPI"])
        self.assertEqual(cfg["deposit"], 10000)
        self.assertEqual(cfg["risk_percent"], 0.25)
        self.assertEqual(cfg["execution_delay_ms"], 150)
        self.assertEqual(cfg["baseline"], BASE)
        self.assertEqual(search_plan.BASE, BASE)
        self.assertEqual(self.plan["baseline"], BASE)
        self.assertTrue(cfg["research_only"])
        self.assertTrue(cfg["exploratory_optimization_authorized"])
        for name in ("live_changes", "installers_changed", "website_changed", "push_authorized"):
            self.assertIs(cfg[name], False)
        rules = cfg["fixed_rules"]
        self.assertIn("First release-aligned M1", rules["signal"])
        self.assertIn("15 strictly pre-release", rules["atr"])
        self.assertIn("0.1 pre-news ATR and one tick", rules["stop"])
        self.assertTrue(rules["positive_entry_spread_required"])
        self.assertTrue(rules["one_attempt_per_event"])
        self.assertEqual(rules["maximum_spread_fraction_of_stop"], 0.1)
        self.assertEqual(rules["quote_freshness_seconds"], 2)
        self.assertEqual(rules["hard_flat_minutes_after_release"], 60)
        for name in ("trailing", "break_even", "partials", "reentry", "forced_market_fallback"):
            self.assertIs(rules[name], False)

    def test_exact_two_year_split_and_preceding_validation(self):
        expected = {
            "development": {"start": "2020-01-01", "end_exclusive": "2023-10-16"},
            "validation": {"start": "2023-10-16", "end_exclusive": "2024-10-16"},
            "oos": {"start": "2024-10-16", "end_exclusive": "2026-10-16", "calendar_years": 2},
        }
        for name, value in expected.items():
            self.assertEqual(self.split[name], value)
        self.assertTrue(self.split["selection_must_end_before_oos"])
        self.assertTrue(self.split["recent_subwindows_are_diagnostic_only"])
        self.assertIn("not asserted", self.split["untouched_status"])
        self.assertIn("Retrospective", self.config["oos_status"])
        self.assertEqual(self.config["oos_start"], expected["oos"]["start"])
        self.assertEqual(self.config["end_exclusive"], expected["oos"]["end_exclusive"])
        self.assertEqual(self.config["development_end_exclusive"], expected["validation"]["start"])
        self.assertEqual(self.config["validation_end_exclusive"], expected["oos"]["start"])

    def test_raw_gates_cannot_consume_validation_or_oos(self):
        gate = self.config["raw_gate"]
        self.assertEqual(gate["three_year_start"], "2020-10-16")
        self.assertEqual(gate["end_exclusive"], "2023-10-16")
        self.assertEqual(gate["five_year_required_start"], "2018-10-16")
        self.assertIn("Unavailable", gate["five_year_status"])
        self.assertEqual(gate["minimum_trades"], 30)
        self.assertEqual(gate["minimum_pf"], 1.15)
        self.assertEqual(self.config["promotion_rules_unchanged"]["minimum_oos_trades"], 30)
        events = load("calendar.json")["events"]
        lo = int(datetime.fromisoformat(self.config["oos_start"]).replace(tzinfo=timezone.utc).timestamp())
        hi = int(datetime.fromisoformat(self.config["end_exclusive"]).replace(tzinfo=timezone.utc).timestamp())
        sample = [event for event in events if lo <= event["epoch"] < hi]
        self.assertEqual(len(sample), 23)
        self.assertLess(len(sample), self.config["promotion_rules_unchanged"]["minimum_oos_trades"])

    def test_calendar_exact_unique_cpi_new_york_clock(self):
        events = load("calendar.json")["events"]
        self.assertEqual(len(events), 81)
        epochs = [event["epoch"] for event in events]
        self.assertEqual(epochs, sorted(set(epochs)))
        ny = ZoneInfo("America/New_York")
        for event in events:
            with self.subTest(epoch=event["epoch"]):
                self.assertEqual(event["kind"], "CPI")
                self.assertEqual(event["epoch"] % 60, 0)
                local = datetime.fromtimestamp(event["epoch"], timezone.utc).astimezone(ny)
                self.assertEqual((local.hour, local.minute, local.second), (8, 30, 0))
                self.assertTrue(event.get("source", "").startswith("https://"))
        self.assertTrue(all(b - a > 3600 for a, b in zip(epochs, epochs[1:])))

    def test_search_only_three_axes_and_fixed_signal_details(self):
        expected_stages = [
            ["target", "target_r", [0.5, 1.0, 1.5, 2.0]],
            ["hold", "hold_minutes", [5, 15, 30]],
            ["impulse", "impulse_mult", [0.75, 1.0, 1.25]],
        ]
        self.assertEqual(self.plan["stages"], expected_stages)
        self.assertEqual(json.loads(json.dumps(search_plan.STAGES)), expected_stages)
        self.assertEqual(self.plan["beam_width"], 1)
        self.assertEqual({stage[1] for stage in self.plan["stages"]}, SEARCH_AXES)
        self.assertEqual(set(self.plan["neighbours"]), SEARCH_AXES)
        self.assertEqual(set(self.plan["bounds"]), SEARCH_AXES)
        self.assertEqual(self.plan["max_main_unique_configurations"], 20)
        for case in search_plan.neighbours(BASE):
            self.assertEqual(case["entry_window_minutes"], 5)
            self.assertEqual(case["close_fraction"], 0.25)
            changes = [field for field in BASE if case[field] != BASE[field]]
            self.assertLessEqual(len(changes), 1)
            self.assertTrue(set(changes).issubset(SEARCH_AXES))

    def test_every_hypothetical_ofaat_path_respects_main_search_cap(self):
        stages = self.plan["stages"]
        for tp, hold, impulse in itertools.product(stages[0][2], stages[1][2], stages[2][2]):
            centre = dict(BASE)
            seen = {search_plan.key(centre)}
            for (_, field, values), winner in zip(stages, (tp, hold, impulse)):
                for value in values:
                    seen.add(search_plan.key(dict(centre, **{field: value})))
                centre[field] = winner
            for point in (BASE, centre):
                for case in search_plan.neighbours(point):
                    seen.add(search_plan.key(case))
                    self.assertEqual(case["entry_window_minutes"], 5)
                    self.assertEqual(case["close_fraction"], 0.25)
            with self.subTest(target=tp, hold=hold, impulse=impulse):
                self.assertLessEqual(len(seen), self.plan["max_main_unique_configurations"])

    def test_walk_forward_nine_case_grid_and_honest_chronology(self):
        wf = self.plan["walk_forward"]
        self.assertEqual(wf["grid_target_r"], [0.5, 1.5, 2.0])
        self.assertEqual(wf["grid_hold_minutes"], [5, 15, 30])
        self.assertEqual(wf["fixed_other_fields"], BASE)
        self.assertEqual(len(wf["grid_target_r"]) * len(wf["grid_hold_minutes"]), 9)
        self.assertEqual(len(wf["folds"]), 2)
        for fold in wf["folds"]:
            self.assertLess(fold["train_start"], fold["train_end"])
            self.assertEqual(fold["train_end"], fold["test_start"])
            self.assertLess(fold["test_start"], fold["test_end"])
            self.assertLessEqual(fold["test_end"], self.config["development_end_exclusive"])
        self.assertIn("chosen=rank(training)[0]['parameters']", self.orchestrator)
        self.assertNotIn("rank(tested)", self.orchestrator)
        self.assertIn("selection_used_for_final=False", self.orchestrator)

    def test_score_has_no_holdout_or_file_access(self):
        score_source = inspect.getsource(search_plan.score)
        tree = ast.parse(score_source)
        forbidden = {"open", "load", "read", "read_text", "read_bytes", "native", "batch"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                self.assertNotIn(name, forbidden)
        self.assertNotIn("oos", score_source.lower())
        self.assertNotIn("holdout", score_source.lower())
        sample = {"parameters": BASE, "metrics": {"trades": 16, "net": 10.0, "pf": 1.2,
                   "yearly": [{"year": 2020, "net": 5.0}, {"year": 2021, "net": 5.0}],
                   "win_rate_pct": 60.0, "equity_dd": 1.0}}
        contaminated = copy.deepcopy(sample)
        contaminated["oos"] = {"net": 1e20, "pf": 1e20}
        contaminated["holdout"] = {"net": -1e20, "pf": 0}
        self.assertEqual(search_plan.score(sample), search_plan.score(contaminated))

    def test_persisted_selection_lock_precedes_all_final_evaluation(self):
        marker = "# NO selection, scoring or new parameters below this persisted lock."
        self.assertEqual(self.orchestrator.count(marker), 1)
        before, after = self.orchestrator.split(marker)
        self.assertIn("r.save(R/'SELECTION.json',selection)", before)
        self.assertIn("fp=R/'FROZEN.json'", before)
        self.assertIn("else:r.save(fp,frozen)", before)
        self.assertIn("r.load(fp)['locked']==frozen['locked']", before)
        self.assertIn("r.native('holdout',[BASE,selected],C['oos_start'],C['end_exclusive'])", after)
        self.assertIn("r.native('full',[BASE,selected]", after)
        self.assertNotIn("rank(", after)
        self.assertNotIn("score(", after)
        self.assertNotIn("selected=", after)
        self.assertNotIn("trials_add(", after)
        self.assertNotIn("SELECTION.json", after)

    def test_engine_is_tester_only_causal_and_matches_baseline_mechanics(self):
        source = self.engine
        self.assertIn("!MQLInfoInteger(MQL_TESTER)", source)
        self.assertIn("const int MAGIC=26101683;", source)
        self.assertIn("input double InpRiskPct=0.25;", source)
        self.assertIn("strategy_mode=0;positive_spread=true;", source)
        self.assertIn("CopyRates(_Symbol,PERIOD_M1,event-900,event-1,before)!=15", source)
        self.assertIn("before[i].time!=event-900+i*60", source)
        self.assertIn("for(int i=1;i<15;i++)", source)
        self.assertIn("pre_atr+=tr/14.0", source)
        impulse = source.split("void ConfirmImpulse(){", 1)[1].split("void Signal(", 1)[0]
        self.assertLess(impulse.index("if(now<event+60)return;"), impulse.index("CopyRates("))
        self.assertIn("event,event+59,bar", impulse)
        self.assertIn("MathAbs(first_close-fair)<pre_atr*impulse_mult", impulse)
        self.assertIn("double buffer=0.1*pre_atr+TickSize();", source)
        self.assertIn("quote.ask-quote.bid>0.1*distance", source)
        self.assertIn("positive_spread && quote.ask<=quote.bid", source)
        self.assertIn("MathFloor(MathMin(budget/-loss,max_lot)/step+1e-9)*step", source)
        self.assertIn("datetime deadline=filled+hold_minutes*60;", source)
        self.assertIn("datetime deadline=event+entry_window_minutes*60;", source)
        self.assertIn("double tp=Price(ep+direction*target_r*distance,direction);", source)
        self.assertIn('"entry_"+signal', source)
        self.assertIn('Enter(first[0],quote,spike,"continuation")', source)
        self.assertNotIn("fade_confirmation", source)
        self.assertNotIn("strategy_mode==1", source)

    def test_builder_baseline_order_and_parameter_bounds(self):
        self.assertEqual(build_engine.FIELDS, tuple(BASE))
        self.assertEqual(set(build_engine.BOUNDS), set(BASE))
        built = build_engine.build([BASE])
        self.assertTrue(built.startswith("double Cases[][5]={{15,1.5,5,1.0,0.25}};"))
        self.assertIn("long Events[]={", built)
        self.assertIn('string Kinds[]={"CPI"', built)
        for field, (lo, hi) in build_engine.BOUNDS.items():
            for value in (lo, hi):
                with self.subTest(field=field, valid=value):
                    self.assertIsInstance(build_engine.build([dict(BASE, **{field: value})]), str)
            for value in (lo - 0.01, hi + 0.01):
                with self.subTest(field=field, invalid=value):
                    with self.assertRaises(AssertionError):
                        build_engine.build([dict(BASE, **{field: value})])
        invalid = [dict(BASE, target_r=math.nan), dict(BASE, target_r=math.inf),
                   dict(BASE, target_r=True), dict(BASE, hold_minutes=2.5),
                   dict(BASE, entry_window_minutes=3.5), dict(BASE, mode=0)]
        missing = dict(BASE)
        del missing["target_r"]
        invalid.append(missing)
        for case in invalid:
            with self.subTest(invalid=case):
                with self.assertRaises(AssertionError):
                    build_engine.build([case])
        with self.assertRaises(AssertionError):
            build_engine.build([])

    def test_preregistration_file_hashes_are_unchanged(self):
        registration = load("PREREGISTRATION.json")
        required = {"config.json", "calendar.json", "DATA-SPLIT.json", "SEARCH-PLAN.json",
                    "engine.mq5", "build_engine.py", "search_plan.py"}
        self.assertEqual(set(registration["locked"]), required)
        for name, expected in registration["locked"].items():
            with self.subTest(registered_file=name):
                self.assertEqual(sha(name), expected)
        self.assertTrue(registration["prior_raw_results_viewed"])
        self.assertFalse(registration["genuinely_untouched_oos"])
        self.assertFalse(registration["live_changes"])

    def test_final_freeze_files_and_holdout_start_when_available(self):
        if not (R / "FROZEN.json").exists():
            self.skipTest("Final selection not frozen yet; this test becomes mandatory after selection")
        frozen = load("FROZEN.json")
        files = frozen["locked"]["files"]
        self.assertTrue({"engine.mq5", "build_engine.py", "config.json", "calendar.json",
                         "DATA-SPLIT.json", "SEARCH-PLAN.json", "SELECTION.json", "trials.json"}.issubset(files))
        for name, expected in files.items():
            with self.subTest(final_frozen_file=name):
                self.assertEqual(sha(name), expected)
        self.assertEqual(frozen["locked"]["baseline"], BASE)
        self.assertEqual(frozen["locked"]["selected"], load("SELECTION.json")["selected"])
        self.assertTrue(frozen["research_only"])
        self.assertFalse(frozen["live_changes"])
        frozen_epoch = datetime.fromisoformat(frozen["frozen_at_utc"]).timestamp()
        runs = load("RUNS.json") if (R / "RUNS.json").exists() else {}
        for row in runs.get("holdout", []):
            metadata = load("native/" + row["stage"] + "/owned-process.json")
            self.assertGreaterEqual(metadata["started"], frozen_epoch)
            self.assertEqual(row["start"], self.config["oos_start"])
            self.assertEqual(row["end"], self.config["end_exclusive"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
