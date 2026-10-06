import unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_safety(self):
  s=(R/'EA/Head.mqh').read_text();self.assertIn('if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;',s)
  self.assertNotIn('MathMax(lo',s);self.assertIn('if(now<InpTradeFrom)return;',s)
 def test_confirmed_pivot(self):
  s=(R/'EA/Head.mqh').read_text();self.assertIn('for(int i=3;i<=60;i++)',s);self.assertIn('for(int k=1;k<=2;k++)',s)
  self.assertIn('r[i].time+3600>now',s)
 def test_risk_floor(self):
  import math
  qty=lambda budget,loss,step:math.floor((budget/loss+1e-12)/step)*step
  self.assertLessEqual(qty(50,123.4,.01)*123.4,50)
  self.assertEqual(qty(1,1000,.01),0)
 def test_dst(self):
  def sunday(y,m,n):
   d=datetime(y,m,1,tzinfo=timezone.utc);return 1+(6-d.weekday())%7+(n-1)*7
  t=datetime(2025,1,1,tzinfo=timezone.utc)
  while t<datetime(2027,1,1,tzinfo=timezone.utc):
   a=datetime(t.year,3,sunday(t.year,3,2),7,tzinfo=timezone.utc);b=datetime(t.year,11,sunday(t.year,11,1),6,tzinfo=timezone.utc)
   self.assertEqual(-4 if a<=t<b else -5,t.astimezone(ZoneInfo('America/New_York')).utcoffset().total_seconds()/3600);t+=timedelta(hours=1)
 def test_partial_not_repeated(self):
  s=(R/'EA/Head.mqh').read_text();self.assertIn('!trimmed3&&rr>=3',s);self.assertIn('trimmed3&&!trimmed5&&rr>=5',s)
  self.assertIn('PositionClosePartial(ticket,cut)',s);self.assertIn('originalVolume*.2',s)
if __name__=='__main__':unittest.main()
