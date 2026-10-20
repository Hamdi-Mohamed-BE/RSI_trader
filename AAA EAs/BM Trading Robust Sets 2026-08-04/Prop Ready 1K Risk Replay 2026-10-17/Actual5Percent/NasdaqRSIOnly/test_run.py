"""Subset-only fixtures; no risk-outcome inspection or account connection."""
from pathlib import Path
import importlib.util
import unittest


ROOT = Path(__file__).resolve().parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


r = module('nasdaq_rsi_subset', ROOT/'run.py')
engine = module('frozen_true_five_engine', ROOT.parent/'run.py')
fixtures = module('frozen_true_five_fixtures', ROOT.parent/'test_run.py')
EXPECTED = {'xau-rsi-vwap', 'nasdaq-5m-candle-momentum'}


class SubsetProtocolFixtures(unittest.TestCase):
    def setUp(self):
        self.original = engine.base.read(ROOT.parent.parent/'INPUTS.json')
        self.before = engine.base.sha(ROOT.parent.parent/'INPUTS.json')
        self.data = r.filtered_inputs(self.original)

    def test_exact_requested_membership(self):
        self.assertEqual(set(r.SELECTED), EXPECTED)
        self.assertEqual({q['ea'] for q in self.data['candidates']}, EXPECTED)
        self.assertEqual({q['ea'] for q in self.data['coverage']}, EXPECTED)

    def test_42_observed_standalone_candidates_only(self):
        self.assertEqual(len(self.data['candidates']), 42)
        self.assertEqual(sum(q['ea'] == 'xau-rsi-vwap' for q in self.data['candidates']), 12)
        self.assertEqual(sum(q['ea'] == 'nasdaq-5m-candle-momentum' for q in self.data['candidates']), 30)

    def test_source_entries_exits_costs_and_marks_unchanged(self):
        expected = [q for q in self.original['candidates'] if q['ea'] in EXPECTED]
        self.assertEqual(self.data['candidates'], expected)
        self.assertEqual(self.data['coverage'], [q for q in self.original['coverage'] if q['ea'] in EXPECTED])

    def test_filter_never_mutates_original_input(self):
        self.assertEqual(engine.base.sha(ROOT.parent.parent/'INPUTS.json'), self.before)
        self.assertEqual(len(self.original['candidates']), 93)

    def test_no_source_position_closed_early_for_subset(self):
        censored = [q for q in self.data['candidates'] if q['end_censored']]
        self.assertEqual(len(censored), 1)
        self.assertEqual(censored[0]['ea'], 'nasdaq-5m-candle-momentum')
        self.assertIsNone(censored[0]['cl'])

    def test_relative_priority_remains_rsi_then_nasdaq(self):
        plan = engine.base.read(ROOT.parent.parent/'PLAN.json')
        priority = [q for q in plan['priority'] if q in EXPECTED]
        self.assertEqual(priority, ['xau-rsi-vwap', 'nasdaq-5m-candle-momentum'])
        events = engine.base.events_for(dict(priority=priority), self.data)
        for _, kind, order, _, q, _ in events:
            if kind != 0:
                self.assertEqual(order, priority.index(q['ea']))

    def test_fixed50_and_compound5_scenarios_without_old_controls(self):
        self.assertEqual(len(r.SCENARIOS), 2)
        self.assertEqual({(s['mode'], s['value']) for s in r.SCENARIOS}, {('fixed', 50.), ('percent', 5.)})
        self.assertTrue(all(s['guard_policy'] == 'research_10daily_20total' for s in r.SCENARIOS))

    def test_two_risk_modes_times_two_cost_cases(self):
        pairs = {(s['id'], stress) for s in r.SCENARIOS for stress in (False, True)}
        self.assertEqual(len(pairs), 4)

    def test_all_earlier_source_freezes_still_unchanged(self):
        for folder in (ROOT.parent, ROOT.parent.parent):
            frozen = engine.base.read(folder/'FROZEN.json')
            for path, expected in {**frozen['files'], **frozen.get('source_files', {})}.items():
                with self.subTest(path=path):
                    self.assertEqual(engine.base.sha(path), expected)


class InheritedAccountingFixtures(unittest.TestCase):
    def test_true_compounding_without_initial_five_dollar_ceiling(self):
        spec = fixtures.broker()['symbols']['USTEC']
        scenario = next(s for s in r.SCENARIOS if s['mode'] == 'percent')
        self.assertEqual(engine.true_lots(1200., 100., spec, scenario), (.6, 60.))
        self.assertEqual(engine.true_lots(800., 100., spec, scenario), (.4, 40.))

    def test_censored_fee_paid_but_no_forced_profit(self):
        scenario = next(s for s in r.SCENARIOS if s['mode'] == 'percent')
        model = engine.ResearchReplay(scenario, fixtures.broker())
        q = fixtures.row(duration=None, entry_cost=-3.)
        model.opening(q, q['op'])
        model.mark(q, [q['op']+1, 20., None], q['op']+1)
        result = model.result()
        self.assertEqual(result['metrics']['trades'], 0)
        self.assertEqual(result['metrics']['ending_balance'], 998.5)
        self.assertEqual(result['metrics']['ending_sampled_equity'], 1008.5)
        self.assertEqual(len(result['open_positions']), 1)
        self.assertEqual(sum(q['net_profit'] for q in result['daily']), -1.5)

    def test_original_signal_sizing_ceilings_bypassed_only_in_hypothetical(self):
        scenario = next(s for s in r.SCENARIOS if s['mode'] == 'percent')
        model = engine.ResearchReplay(scenario, fixtures.broker())
        q = fixtures.row()
        model.opening(q, q['op'])
        self.assertEqual(q['source_volume'], .01)
        self.assertEqual(model.active[q['id']]['lots'], .5)
        self.assertEqual(model.active[q['id']]['risk'], 50.)

    def test_future_marks_still_fail(self):
        scenario = next(s for s in r.SCENARIOS if s['mode'] == 'percent')
        model = engine.ResearchReplay(scenario, fixtures.broker())
        q = fixtures.row()
        model.opening(q, q['op'])
        with self.assertRaises(AssertionError):
            model.mark(q, [q['op']+10, 10., None], q['op']+1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
