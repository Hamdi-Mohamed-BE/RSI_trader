import json,unittest
import numpy as np
from research import ROOT,ASSETS
from search import event,baseline,load,configs

class ResearchChecks(unittest.TestCase):
 def test_empty_event(self):
  self.assertEqual(event(np.empty((0,7)),1000,baseline('XAG'),.001,.01)[4],0)
 def test_no_late_placement(self):
  q=np.array([[1000,100,100.1,100,100,100,100],[2000,102,102.1,102,100,100,100]],float)
  self.assertEqual(event(q,1000,np.array([1,0,1,1,0,0,1,60.]),.01,0)[4],0)
 def test_opposite_side_not_cancelled(self):
  q=np.array([[0,100,100.1,100,100,100,100],[100,101.2,101.3,101.2,100,100,100],[200,98.8,98.9,101.2,98.8,100,100],[62000,98.5,98.6,98.5,98.5,100,100]],float)
  r=event(q,1000,np.array([1,0,1,1,0,0,1,60.]),.01,0)
  self.assertEqual(r[4],2)
 def test_fees_reduce_pnl(self):
  q=np.array([[0,100,100.1,100,100,100,100],[100,101.2,101.3,101.2,100,100,100],[62000,102,102.1,102,102,100,100]],float)
  p=np.array([1,0,1,1,0,0,1,60.]);a=event(q,1000,p,.01,0);b=event(q,1000,p,.01,.2)
  self.assertAlmostEqual(a[0]-b[0],.2*a[4])
 def test_baseline_cash_trade_and_net_win_parity(self):
  for asset in ASSETS:
   x=json.loads((ROOT/asset/'baseline-parity.json').read_text())
   self.assertEqual(x['trade_count_difference'],0,asset)
   self.assertLess(abs(x['cash_difference']),1,asset)
   self.assertAlmostEqual(x['simulated']['win_rate'],x['native']['win_rate_pct'],places=7,msg=asset)
 def test_causal_current_candle(self):
  for asset in ASSETS:self.assertTrue(json.loads((ROOT/asset/'data-quality.json').read_text())['causal_active_candle_pass'])
 def test_family_selection_train_cutoff(self):
  events=json.loads((ROOT/'calendar.json').read_text())
  for asset in ASSETS:
   selected=json.loads((ROOT/asset/'selected.json').read_text())
   for k in ('NFP','CPI','FOMC'):
    self.assertEqual(selected[k]['train']['events'],sum(e['kind']==k and e['release_utc'][:10]<'2026-05-19' for e in events))
 def test_grid_and_baseline(self):
  for asset in ASSETS:
   p,_=configs(asset)
   self.assertTrue(np.any(np.all(np.isclose(p,baseline(asset)),axis=1)))
   self.assertTrue(np.all(p[:,7]>=60))
   self.assertEqual(set(np.round(p[:,4],2)),set(np.r_[0,np.arange(.5,8.01,.5)]))
 def test_no_production_initialization(self):
  for asset in ASSETS:
   for suffix in ('Baseline','Quotes','Fitted','Train'):
    path=ROOT/(asset+suffix+'.mq5')
    if path.exists():self.assertIn('if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;',path.read_text())
 def test_all_native_ledgers_and_coverage(self):
  for asset in ASSETS:
   for variant in ('Baseline','Fitted','Train','BaselineHoldout','TrainHoldout','BaselineDelay250','FittedDelay250'):
    folder=ROOT/'native'/(asset+variant)
    s=json.loads((folder/'stats.json').read_text());t=json.loads((folder/'trades.json').read_text());run=json.loads((folder/'run.json').read_text())
    self.assertEqual(len(t),s['trades'])
    self.assertAlmostEqual(sum(x['net_profit'] for x in t),s['net_profit'],places=2)
    self.assertEqual(s['calendar']['expected'],11 if 'Holdout' in variant else 30)
    self.assertEqual(run['settings']['InpEnableBuySide'],'true')
    self.assertEqual(run['settings']['InpEnableSellSide'],'true')
    self.assertEqual(run['settings']['InpAdaptivePortfolioControls'],'false')
    self.assertEqual(run['model'],4)
    self.assertEqual(s['history_quality'],'100% real ticks' if 'Holdout' in variant else '71% real ticks')
    self.assertAlmostEqual(sum(x['commission'] for x in t),s['commission'],places=2)
    self.assertTrue(all(x['symbol']==ASSETS[asset]['symbol'] for x in t))

if __name__=='__main__':unittest.main()
