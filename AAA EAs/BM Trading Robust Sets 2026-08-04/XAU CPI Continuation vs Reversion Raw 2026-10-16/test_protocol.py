"""Gold raw-study protocol checks; never connects to or launches MT5."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib
import json
import re
import sys
import unittest

sys.dont_write_bytecode = True
R = Path(__file__).resolve().parent
US500 = R.parent / "US500 CPI Continuation vs Reversion Raw 2026-10-16"
sys.path.insert(0, str(R))
import build_engine


def load(name):
    return json.loads((R / name).read_text(encoding="utf-8"))


def metadata_block(source):
    marker = " // Research metadata only; no signal or sizing rule is changed by this receipt.\n"
    start = source.index(marker)
    end = source.index(" trade.SetExpertMagicNumber", start)
    return source[start:end]


def canonical(source, gold=False):
    if gold:
        source = source.replace(metadata_block(source), "", 1)
    source = re.sub(r'(?m)^input string InpTag="[^"]*";\n', "", source)
    source = re.sub(r'(?m)^const int MAGIC=\d+;\n', "", source)
    return source.strip()


class ProtocolTests(unittest.TestCase):
    def test_scope_risk_and_no_optimization(self):
        cfg = load("config.json")
        self.assertEqual(cfg["symbol"], "XAUUSD")
        self.assertEqual(cfg["event_types"], ["CPI"])
        self.assertEqual(cfg["deposit"], 10000)
        self.assertEqual(cfg["risk_percent"], 0.25)
        self.assertEqual(cfg["execution_delay_ms"], 150)
        self.assertTrue(cfg["raw_only"])
        self.assertTrue(cfg["research_only"])
        self.assertFalse(cfg["optimization"])
        for name in ("live_changes", "installers_changed", "website_changed", "push_authorized"):
            self.assertFalse(cfg[name])
        self.assertTrue(cfg["next_asset_requires_review"])
        self.assertEqual(cfg["oos_start"], "2024-10-16")
        self.assertEqual(cfg["end_exclusive"], "2026-10-16")

    def test_explicit_native_gold_symbol(self):
        runner = (R / "run_study.py").read_text(encoding="utf-8")
        self.assertIn("cfg['symbol'] == 'XAUUSD'", runner)
        self.assertIn("symbol=cfg['symbol']", runner)
        self.assertIn("cpi-xau-raw-20261016", runner)
        self.assertIn("optimize=False", runner)
        self.assertIn("0-contract.csv.gz", runner)
        self.assertIn("contract_source.stat().st_mtime >= owned['started']-2", runner)

    def test_calendar_and_cases_match_prior_study(self):
        events = load("calendar.json")["events"]
        old = json.loads((US500 / "calendar.json").read_text(encoding="utf-8"))["events"]
        self.assertEqual(events, old)
        self.assertEqual(len(events), 81)
        epochs = [event["epoch"] for event in events]
        self.assertEqual(epochs, sorted(set(epochs)))
        ny = ZoneInfo("America/New_York")
        for event in events:
            local = datetime.fromtimestamp(event["epoch"], timezone.utc).astimezone(ny)
            self.assertEqual((local.hour, local.minute, local.second), (8, 30, 0))
            self.assertEqual(event["kind"], "CPI")
            self.assertTrue(event["source"].startswith("https://www.bls.gov/"))
        self.assertEqual(datetime.fromtimestamp(epochs[-1], timezone.utc).isoformat(), "2026-10-14T12:30:00+00:00")
        cases = load("CASES.json")
        self.assertEqual(cases, [dict(mode=mode, require_positive_spread=policy) for policy in (0, 1) for mode in (0, 1, 2)])
        self.assertIn("double Cases[][2]", build_engine.build(cases))

    def test_core_engine_preserved_except_identifiers_and_metadata(self):
        source = (R / "engine.mq5").read_text(encoding="utf-8")
        prior = (US500 / "engine.mq5").read_text(encoding="utf-8")
        self.assertEqual(canonical(source, gold=True), canonical(prior))
        self.assertEqual((R / "build_engine.py").read_bytes(), (US500 / "build_engine.py").read_bytes())
        self.assertIn('input string InpTag="xau-cpi-raw";', source)
        self.assertIn("const int MAGIC=26101684;", source)
        block = metadata_block(source)
        assignments = re.findall(r"\b([A-Za-z_]\w*)\s*=(?!=)", block)
        self.assertEqual(assignments, ["cf"])
        self.assertNotIn("trade.", block)
        self.assertIn("SYMBOL_TRADE_CONTRACT_SIZE", block)
        self.assertIn("SYMBOL_TRADE_TICK_SIZE", source)
        self.assertIn("SYMBOL_TRADE_TICK_VALUE_LOSS", block)
        self.assertIn("SYMBOL_VOLUME_MIN", block)
        self.assertIn("SYMBOL_VOLUME_STEP", block)

    def test_hold_cap_matches_frozen_configuration(self):
        cfg = load("config.json")
        continuation = cfg["continuation"]["maximum_hold_minutes_from_fill"]
        reversion = cfg["reversion"]["maximum_hold_minutes_from_fill"]
        self.assertEqual(continuation, 15)
        self.assertEqual(reversion, 30)
        source = (R / "engine.mq5").read_text(encoding="utf-8")
        if continuation == reversion:
            self.assertIn(f"datetime deadline=filled+{int(continuation * 60)};", source)
        else:
            self.assertIn(f"filled+(strategy_mode==0?{int(continuation * 60)}:{int(reversion * 60)})", source)
        cap = cfg.get("gold_holding_cap", {})
        if cap.get("applies_to_all_models"):
            self.assertEqual(continuation, cap["minutes_from_fill"])
            self.assertEqual(reversion, cap["minutes_from_fill"])

    def test_causal_safety_and_dynamic_gold_units(self):
        source = (R / "engine.mq5").read_text(encoding="utf-8")
        for fragment in ("!MQLInfoInteger(MQL_TESTER)", "event-900,event-1", "before[i].time!=event-900+i*60",
                         "CopyRates(_Symbol,PERIOD_M1,event,event+59", "now<event+60", "strategy_mode==0?300:600",
                         "Events[event_index]+3600", "MathFloor(MathMin(budget/-loss,max_lot)/step",
                         "reward/distance<1.5", "quote.ask-quote.bid>0.1*distance", "positive_spread && quote.ask<=quote.bid",
                         "OrderCalcProfit(", "SYMBOL_TRADE_TICK_SIZE", "SYMBOL_VOLUME_STEP"):
            self.assertIn(fragment, source)
        self.assertNotIn("trade.PositionModify", source)
        self.assertNotIn("BuyStop(", source)
        self.assertNotIn("SellStop(", source)
        self.assertNotIn("SYMBOL_VOLUME_MIN)*", source)

    def test_builder_rejects_undeclared_or_invalid_cases(self):
        invalid = [dict(mode=3, require_positive_spread=0), dict(mode=0, require_positive_spread=2),
                   dict(mode=True, require_positive_spread=0), dict(mode=0, require_positive_spread=False),
                   dict(mode=0, require_positive_spread=0, target_r=2), dict(mode=0)]
        for case in invalid:
            with self.subTest(case=case):
                with self.assertRaises(AssertionError):
                    build_engine.build([case])
        with self.assertRaises(AssertionError):
            build_engine.build([])

    def test_geometry_and_impulse_persistence_are_separate(self):
        anchor, low, high, buffer = 3000., 3000., 3010., .1
        midpoint = (low + high) / 2
        for entry in (3004.99, 3004., 3001.):
            self.assertLess(entry, midpoint)
            self.assertLess((entry - anchor) / (high + buffer - entry), 1.0)
        self.assertGreater(3008. - anchor, 0)
        self.assertLess(3008. - high, 0)

    def test_freeze_including_runner(self):
        frozen = load("FROZEN.json")["locked"]
        mapping = [("config.json", "config_sha256"), ("calendar.json", "calendar_sha256"),
                   ("CASES.json", "cases_sha256"), ("engine.mq5", "engine_sha256"),
                   ("build_engine.py", "build_sha256"), ("run_study.py", "run_sha256")]
        for name, field in mapping:
            self.assertEqual(hashlib.sha256((R / name).read_bytes()).hexdigest(), frozen[field])
        self.assertEqual(frozen["parameters_searched"], 0)
        self.assertEqual(frozen["enumerated_cases"], 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
