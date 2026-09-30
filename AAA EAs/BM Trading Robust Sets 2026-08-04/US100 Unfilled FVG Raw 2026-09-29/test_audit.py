"""Negative controls for the independent native-entry oracle."""
import unittest
import pandas as pd
from audit import R,oracle

class OracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=R/'native/M1-IFVG-raw-smoke-m4'
        cls.sig=next(pd.read_csv(p/'signals.csv.gz').itertuples(index=False))
        a=pd.read_csv(p/'audit.csv.gz');cls.bars=a[a.position_id==cls.sig.position_id].copy()
    def test_valid_native_entry(self):oracle(self.sig,self.bars,False)
    def test_no_future_confirmation(self):
        with self.assertRaises(AssertionError):oracle(self.sig._replace(ready=self.sig.fill_time+60),self.bars,False)
    def test_target_already_touched_rejected(self):
        a=self.bars.copy();idx=a[(a.kind=='m1')&(a.time>=self.sig.ready)].index[-1]
        a.loc[idx,'low' if self.sig.raw_side<0 else 'high']=self.sig.midpoint
        with self.assertRaises(AssertionError):oracle(self.sig,a,False)
    def test_wrong_trigger_level_rejected(self):
        with self.assertRaises(AssertionError):oracle(self.sig._replace(reference=self.sig.reference+100),self.bars,False)
    def test_missing_exhaustion_rejected(self):
        a=self.bars.copy();p=a[a.kind=='parent'];c=p.index[-1];b=p.iloc[-2]
        a.loc[c,'close']=b.high+1 if self.sig.raw_side<0 else b.low-1
        with self.assertRaises(AssertionError):oracle(self.sig,a,False)

if __name__=='__main__':unittest.main()
