"""Mathematical/state invariants; final native-ledger checks are added after runs."""
from pathlib import Path
import hashlib, json, unittest

ROOT=Path(__file__).resolve().parent

def centres(confirm,seed=26100950):
    state=(confirm//3600)^seed;out=[]
    for _ in range(3):
        for attempt in range(10000):
            state=(1664525*state+1013904223)&0xffffffff
            candidate=2+state%31
            if all(abs(candidate-c)>2 for c in out):out.append(candidate);break
    return out

class ReconstructionTests(unittest.TestCase):
    def test_gate_not_before_confirmation(self):
        allowed=lambda age:1<=age<=33 and any(abs(age-c)<=1 for c in [8,16,32])
        self.assertFalse(allowed(-1));self.assertFalse(allowed(0));self.assertFalse(allowed(34))
        self.assertEqual(sum(allowed(a) for a in range(1,34)),9)

    def test_random_controls_equal_gate_exposure(self):
        for confirm in range(1700000000,1701000000,14400):
            values=centres(confirm)
            self.assertEqual(len(values),3)
            self.assertTrue(all(2<=c<=32 for c in values))
            self.assertEqual(len({a for c in values for a in [c-1,c,c+1]}),9)
            self.assertEqual(values,centres(confirm))

    def test_pivot_confirmation_delay(self):
        # centre shift 3, completed neighbours shifts 2/1; confirmation at shift 0
        centre=1700000000
        confirm=centre+3*14400
        self.assertGreater(confirm,centre+2*14400)
        self.assertIn('bars[k-InpPivotNeighbours-1].time',(ROOT/'Gann Research.mq5').read_text())

    def test_fan_scale_freezes_completed_same_type_swing(self):
        previous,current,bar_gap=100,120,10
        slope=(current-previous)/bar_gap
        self.assertEqual(slope,2)
        self.assertEqual(current+slope*8,136)
        source=(ROOT/'Gann Research.mq5').read_text()
        self.assertIn('MathAbs(price-previous_price)/length',source)
        self.assertNotIn('MathTan(',source)

    def test_range_grid_and_long_short_geometry(self):
        low,high,atr=100,180,4
        lower,upper,middle=110,170,140
        self.assertEqual(lower,low+(high-low)/8)
        self.assertEqual(upper,high-(high-low)/8)
        self.assertLess(low-.1*atr,lower);self.assertGreater(high+.1*atr,upper)
        self.assertLess(lower,middle);self.assertGreater(upper,middle)

    def test_safe_source_and_completed_signals(self):
        source=(ROOT/'Gann Research.mq5').read_text()
        for token in ['!MQLInfoInteger(MQL_TESTER)','MathFloor(','CopyBuffer(atr_handle,0,1,1',
                      'current-bars[1].time!=PeriodSeconds','feature_known_epoch','signal_close_epoch']:
            self.assertIn(token,source)
        self.assertNotIn('WebRequest(',source)

    def test_plan_is_complete_and_frozen(self):
        p=json.loads((ROOT/'PLAN.json').read_text())
        self.assertEqual(len(p['cases']),42)
        self.assertEqual(len({c['slug'] for c in p['cases']}),42)
        self.assertEqual(p['risk_percent_current_balance'],.5)
        self.assertFalse(p['live_changes']);self.assertFalse(p['optimized'])
        self.assertEqual(p['final_two_year_validation'],['2024.10.09','2026.10.09'])

    def test_completed_native_ledgers_when_present(self):
        status=ROOT/'RUN_STATUS.json'
        if not status.exists():return
        state=json.loads(status.read_text())
        for case in state['complete'].values():
            r=json.loads(Path(case['path']).read_text())
            self.assertTrue(r['known_at_entry_verified'])
            self.assertFalse(any(r['flags'][k] for k in ['init_failed','runtime','history','stopout','invalid_volume','export_failed']))
            self.assertAlmostEqual(sum(t['net'] for t in r['trades']),r['native']['net_profit'],delta=.031)
            self.assertEqual(len(r['signal_audit']),len(r['trades']))

    def test_frozen_source_and_actual_native_clock_inputs(self):
        p=json.loads((ROOT/'PLAN.json').read_text());source_hash=hashlib.sha256((ROOT/'Gann Research.mq5').read_bytes()).hexdigest()
        state_path=ROOT/'RUN_STATUS.json'
        state=json.loads(state_path.read_text()) if state_path.exists() else {'complete':{}}
        for case in p['cases']:
            self.assertEqual(case['production_hashes'][case['source']],source_hash)
            if case['slug'] not in state['complete']:continue
            r=json.loads(Path(state['complete'][case['slug']]['path']).read_text())
            for key in ['InpIdea','InpSignalTF','InpReferenceTF','InpRiskPercent','InpRandomSeed','InpCloseMinuteUTC']:
                self.assertEqual(float(r['inputs'][key]),float(case['input_settings'][key]))
            for entry in r['signal_audit']:
                s=entry['signal']
                if int(s['idea']) in [4,5]:
                    self.assertEqual([int(s['random'+str(i)]) for i in [1,2,3]],centres(int(s['feature_known_epoch'])))

if __name__=='__main__':unittest.main()
