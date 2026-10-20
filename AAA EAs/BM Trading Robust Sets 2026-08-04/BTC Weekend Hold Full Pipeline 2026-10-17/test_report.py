"""Report fixtures use temporary synthetic FINAL.json only; no prices or OOS."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("btc_weekend_report", Path(__file__).with_name("report.py"))
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def fixture():
    metrics = {"trades": 52, "win_rate_pct": 55.5, "profit_factor": 1.234,
               "return_pct": 12.34, "closed_dd_pct": 8.76, "weekly_sharpe": .98,
               "max_win_streak": 5, "max_loss_streak": 3, "cost_basis": "gross synthetic surrogate"}
    return {"study_status": "RESEARCH_ONLY_FAILED_VALIDATION", "research_only": True,
            "date_split": {"development": {"start": "2018-01-01", "end_exclusive": "2023-10-17"},
                           "validation": {"start": "2023-10-17", "end_exclusive": "2024-10-17"},
                           "oos": {"start": "2024-10-17", "end_exclusive": "2026-10-17"}},
            "source_summary": {"status": "partial", "coverage": [{"timeframe": "M5", "rows": 1234, "gaps": 7,
                                "first_utc": "2018-01-01", "last_bar_open_utc": "2026-10-16", "nonpositive_spread_bars": 99,
                                "start_covered": True, "end_covered": True}]},
            "raw_gates": {"three_year": {"passed": False, "reason": "PF below gate"}, "five_year": None},
            "selection": {"selected_config_id": "synthetic-123", "selected_config": {"timeframe_minutes": 5, "entry_mode": 0,
                          "stop_mode": 0, "stop_value": 0, "target_rr": 0, "management_mode": 0, "management_value": 0,
                          "filter_mode": 0, "filter_value": 0, "entry_minute_ny": 1020, "exit_minute_ny": 1020}},
            "periods": [{"label": "Two-year retrospective OOS", "start": "2024-10-17", "end": "2026-10-17",
                         "baseline": {"metrics": metrics}, "selected": {"metrics": dict(metrics, return_pct=-1.25)}}],
            "robustness": {"selected": {"block_bootstrap": {"5": {"paths": 10000, "status": "complete", "probability_profit_pct": 75,
                           "distributions": {"return_pct": {"p05": -1, "p50": 2}, "pf": {"p05": .9},
                           "max_closed_dd_pct": {"p95": 10}, "max_sampled_equity_dd_pct": {"p95": 12}, "max_loss_streak": {"p95": 7}}}},
                           "deflated_sharpe": {"tested_configurations": 9, "dsr_pct": 31}}},
            "native_audit": {"status": "not_run", "reason": "Awaiting native evidence"},
            "cost_scenarios": {"status": "unknown_historical_financing", "current_swap_sensitivity": True},
            "cautions": ["Synthetic test only", "No stop is not a 1% risk rule"],
            "promotion_gates": {"bootstrap": False, "measured_cost_stress": None, "source_check": True}}


class ReportTests(unittest.TestCase):
    def render(self, data=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "FINAL.json"
            source.write_text(json.dumps(fixture() if data is None else data), encoding="utf-8")
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            result = report.build_report(root)
            self.assertEqual(result, root / "Results.html")
            self.assertEqual(before, hashlib.sha256(source.read_bytes()).hexdigest())
            return result.read_text(encoding="utf-8")

    def test_actual_comparison_metrics_render_without_recalculation(self):
        html = self.render()
        for value in ["+12.34%", "-1.25%", "55.50%", "1.23", "8.76%", "0.98"]:
            self.assertIn(value, html)

    def test_research_gross_retrospective_and_no_stop_warnings(self):
        html = self.render()
        for value in ["RESEARCH ONLY", "NO LIVE CHANGES", "not 1% stop risk", "retrospective", "gross", "2024-10-17", "2026-10-17"]:
            self.assertIn(value, html)

    def test_missing_values_do_not_turn_into_zero(self):
        data = fixture(); data["periods"][0]["selected"] = {"metrics": {}}
        html = self.render(data)
        self.assertIn("Unavailable", html)
        self.assertNotIn("+0.00%", html)

    def test_genuine_zero_is_displayed(self):
        data = fixture(); data["periods"][0]["selected"]["metrics"]["return_pct"] = 0
        self.assertIn("+0.00%", self.render(data))

    def test_all_text_and_json_are_html_escaped(self):
        data = fixture(); payload = '<script>alert("unsafe")</script>'
        data["cautions"] = [payload]; data["selection"]["selected_config_id"] = payload
        html = self.render(data)
        self.assertNotIn(payload, html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script", html.lower())

    def test_no_external_asset_or_javascript_dependency(self):
        html = self.render()
        self.assertNotIn('src="http', html)
        self.assertNotIn('<script', html)
        self.assertNotIn('<link', html)

    def test_gate_fail_unavailable_and_pass_are_distinct(self):
        html = self.render()
        self.assertIn('class="pill fail">Fail', html)
        self.assertIn('class="pill unavailable">Unavailable', html)
        self.assertIn('class="pill pass">Pass', html)

    def test_mobile_horizontal_overflow_and_semantic_headers(self):
        html = self.render()
        self.assertIn("overflow-x:auto", html)
        self.assertIn("@media(max-width:700px)", html)
        self.assertIn('<th scope="col">', html)
        self.assertIn('tabindex="0"', html)

    def test_source_and_native_evidence_not_hidden(self):
        html = self.render()
        for value in ["Unknown / nonpositive spreads", "Awaiting native evidence", "PF below gate", "current_swap_sensitivity"]:
            self.assertIn(value, html)

    def test_monte_carlo_primary_and_factual_count(self):
        html = self.render()
        self.assertIn("Block 5 weeks · primary", html)
        self.assertIn("10,000", html)
        self.assertIn("not forecasts", html)

    def test_missing_final_does_not_write_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                report.build_report(tmp)
            self.assertFalse((Path(tmp) / "Results.html").exists())

    def test_empty_payload_is_honest_unavailable(self):
        html = self.render({})
        self.assertIn("Status unavailable", html)
        self.assertIn("No matching evidence supplied", html)
        self.assertIn("RESEARCH ONLY", html)


if __name__ == "__main__":
    unittest.main()
