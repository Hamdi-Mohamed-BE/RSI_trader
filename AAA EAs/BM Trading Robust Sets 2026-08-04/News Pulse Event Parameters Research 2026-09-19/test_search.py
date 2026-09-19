import json,unittest
import numpy as np
from search import ROOT,BASE,event,load,portfolio,batch
class Checks(unittest.TestCase):
 def test_empty_event_no_fake_trade(self):
  self.assertEqual(event(np.empty((0,7)),0,BASE)[4],0)
 def test_native_baseline_cash_and_net_wins(self):
  ev,data,offsets,epochs=load();result=batch(data,offsets,epochs,np.array([BASE]))[0]
  simulated=portfolio(result,BASE);native=json.loads((ROOT/'native'/'NativeBaseline'/'stats.json').read_text())
  self.assertEqual(simulated['trades'],native['trades']);self.assertAlmostEqual(simulated['win_rate'],native['win_rate_pct'])
  self.assertLess(abs(simulated['balance']-native['final_balance']),1.0)
 def test_both_sides_can_fill(self):
  ev,data,offsets,epochs=load();result=batch(data,offsets,epochs,np.array([BASE]))[0]
  self.assertGreaterEqual(sum(result[:,4]==2),4)
 def test_chronological_selection(self):
  e,*_=load();selected=json.loads((ROOT/'selected.json').read_text())
  for k in ('NFP','CPI','FOMC'):
   self.assertEqual(selected[k]['train']['events'],sum(x['kind']==k and x['release_utc'][:10]<'2026-05-19' for x in e))
 def test_no_future_active_candle_high_low(self):
  _,data,offsets,_=load()
  # Start after the first partial minute in each exported event window.
  for a,b in zip(offsets[:-1],offsets[1:]):
   q=data[a:b]
   if not len(q):continue
   minute=q[:,0]//60000
   for m in np.unique(minute)[1:]:
    r=q[minute==m];hi=np.maximum.accumulate(r[:,1]);lo=np.minimum.accumulate(r[:,1])
    self.assertLess(np.max(np.abs(r[:,3]-hi)),.0011)
    self.assertLess(np.max(np.abs(r[:,4]-lo)),.0011)
if __name__=='__main__':unittest.main()
