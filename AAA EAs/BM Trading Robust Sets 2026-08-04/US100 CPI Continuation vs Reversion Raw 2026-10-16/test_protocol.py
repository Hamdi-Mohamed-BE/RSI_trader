"""Structural/raw-protocol checks; no broker connection or parameter search."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib, json, unittest
import build_engine

R = Path(__file__).resolve().parent

class ProtocolTests(unittest.TestCase):
    def test_scope(self):
        c = json.loads((R / 'config.json').read_text())
        self.assertEqual(c['symbol'], 'USTEC')
        self.assertEqual(c['event_types'], ['CPI'])
        self.assertEqual(c['risk_percent'], 0.25)
        self.assertFalse(c['live_changes'])
        self.assertFalse(c['installers_changed'])
        self.assertFalse(c['website_changed'])
        self.assertTrue(c['next_asset_requires_review'])
        self.assertEqual(c['oos_start'], '2024-10-16')
        self.assertEqual(c['end_exclusive'], '2026-10-16')

    def test_calendar(self):
        if not (R / 'calendar.json').exists():
            self.skipTest('Calendar not prepared yet')
        events = json.loads((R / 'calendar.json').read_text())['events']
        epochs = [e['epoch'] for e in events]
        self.assertEqual(epochs, sorted(set(epochs)))
        ny = ZoneInfo('America/New_York')
        for e in events:
            d = datetime.fromtimestamp(e['epoch'], timezone.utc).astimezone(ny)
            self.assertEqual((d.hour, d.minute, d.second), (8, 30, 0))
            self.assertEqual(e['kind'], 'CPI')
            self.assertTrue(e['source'].startswith('https://www.bls.gov/'))
        self.assertEqual(datetime.fromtimestamp(epochs[-1], timezone.utc).isoformat(), '2026-10-14T12:30:00+00:00')

    def test_causal_mechanics_and_safety(self):
        s = (R / 'engine.mq5').read_text()
        for fragment in ['!MQLInfoInteger(MQL_TESTER)', 'event-900,event-1',
                         'before[i].time!=event-900+i*60', 'CopyRates(_Symbol,PERIOD_M1,event,event+59',
                         'now<event+60', 'strategy_mode==0?300:600', 'filled+(strategy_mode==0?900:1800)',
                         'Events[event_index]+3600', 'MathFloor(MathMin(budget/-loss,max_lot)/step',
                         'reward/distance<1.5', 'quote.ask-quote.bid>0.1*distance',
                         'positive_spread && quote.ask<=quote.bid']:
            self.assertIn(fragment, s)
        self.assertNotIn('trade.PositionModify', s)
        self.assertNotIn('BuyStop(', s)
        self.assertNotIn('SellStop(', s)

    def test_case_enumeration(self):
        if not (R / 'CASES.json').exists():
            self.skipTest('Cases not prepared yet')
        cases = json.loads((R / 'CASES.json').read_text())
        self.assertEqual(cases, [dict(mode=m, require_positive_spread=p) for p in [0, 1] for m in [0, 1, 2]])
        self.assertIn('double Cases[][2]', build_engine.build(cases))
        with self.assertRaises(AssertionError):
            build_engine.build([dict(mode=3, require_positive_spread=0)])

    def test_geometry_is_not_an_edge_test(self):
        # Upward spike begins at anchor=low. After a midpoint crossing,
        # reward to anchor cannot exceed risk to the spike extreme.
        anchor, low, high, buffer = 100., 100., 110., 0.1
        midpoint = (low + high) / 2
        for entry in [104.99, 104., 101.]:
            self.assertLess(entry, midpoint)
            rr = (entry - anchor) / (high + buffer - entry)
            self.assertLess(rr, 1.0)
        # Initial jump persistence is distinct from incremental follow-on.
        self.assertGreater(108. - anchor, 0)
        self.assertLess(108. - 110., 0)

    def test_freeze(self):
        if not (R / 'FROZEN.json').exists():
            self.skipTest('Not frozen yet')
        f = json.loads((R / 'FROZEN.json').read_text())['locked']
        for filename, key in [('config.json', 'config_sha256'), ('calendar.json', 'calendar_sha256'),
                              ('CASES.json', 'cases_sha256'), ('engine.mq5', 'engine_sha256'), ('build_engine.py', 'build_sha256')]:
            self.assertEqual(hashlib.sha256((R / filename).read_bytes()).hexdigest(), f[key])
        self.assertEqual(f['parameters_searched'], 0)
        self.assertEqual(f['enumerated_cases'], 6)

if __name__ == '__main__':
    unittest.main()
