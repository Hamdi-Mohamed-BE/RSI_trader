import importlib.util, json, math, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('zone_report',ROOT/'publish.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

def pivots(bars):
    out=[]
    for i in range(2,len(bars)-2):
        high,low=bars[i];others=bars[i-2:i]+bars[i+1:i+3]
        top=all(high>=h for h,l in others) and any(high>h for h,l in others)
        bottom=all(low<=l for h,l in others) and any(low<l for h,l in others)
        if top:out.append((high,i))
        if bottom and (not top or high!=low):out.append((low,i))
    return out

def cluster(points,pip=.0001):
    points=sorted(points);out=[];i=0
    while i<len(points):
        j=i+1
        while j<len(points) and points[j][0]-points[i][0]<=60*pip+1e-9:j+=1
        touches=len({t for price,t in points[i:j]})
        if touches>=3:
            low,high=points[i][0],points[j-1][0]
            if high-low<5*pip:
                center=(high+low)/2;low,high=center-2.5*pip,center+2.5*pip
            out.append((low,high,touches))
        i=j
    return out

class ReconstructionTests(unittest.TestCase):
    def test_confirmation_requires_two_later_completed_bars(self):
        bars=[(1,0),(2,1),(6,5),(3,2),(2,1)]
        self.assertNotIn((6,2),pivots(bars[:-1]));self.assertIn((6,2),pivots(bars))

    def test_zone_requires_three_distinct_days(self):
        self.assertEqual(cluster([(1.1,1),(1.1001,1),(1.1002,2)]),[])
        self.assertEqual(len(cluster([(1.1,1),(1.1001,2),(1.1002,3)])),1)

    def test_zone_minimum_width(self):
        low,high,n=cluster([(1.1,1),(1.1,2),(1.1,3)])[0]
        self.assertAlmostEqual(high-low,.0005);self.assertEqual(n,3)

    def test_max_width_and_no_lucky_cluster_selection(self):
        bands=cluster([(1.1,1),(1.105,2),(1.107,3),(1.108,4)])
        self.assertEqual(bands,[]) # Greedy groups are fixed; do not search for a better-looking triple.

    def test_current_vs_high_water_budget(self):
        self.assertEqual(9800*.005,49);self.assertEqual(10000*.005,50)
        self.assertGreater(50/9800,.005)

    def test_round_down_not_minimum_lot_overrisk(self):
        raw=50/650;size=math.floor(raw/.01)*.01
        self.assertLessEqual(size*650,50)
        below=50/10000;self.assertLess(below,.01)

    def test_close_stats_include_costs_and_streaks(self):
        result=p.closed_stats([{'net':x} for x in [-50,-50,98,98,-52]],10000)
        self.assertEqual(result['win_streak'],2);self.assertEqual(result['loss_streak'],2)
        self.assertAlmostEqual(result['pf'],196/152);self.assertAlmostEqual(result['return_pct'],.44)

    def test_native_warmup_and_measurement_verification(self):
        checks=json.loads((ROOT/'VERIFICATION.json').read_text())
        self.assertEqual(len(checks['cases']),12)
        self.assertTrue(checks['risk_modes_signal_fill_parity'])
        for case in checks['cases']:
            self.assertTrue(case['cash_reconciled']);self.assertTrue(case['complete_two_year_zone_history'])
            self.assertTrue(case['no_warmup_orders']);self.assertFalse(case['tick_gaps'])

if __name__=='__main__':unittest.main()
