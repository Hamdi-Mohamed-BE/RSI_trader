"""Signal parity verifier for native NQ M5 exports, not fabricated delta data.
CSV: close_timestamp_utc,open,high,low,close,upticks,downticks.
Up/down fields MUST come from the chart or independently documented tick feed.
No trade P&L is manufactured from OHLCV. Intrabar fills require separate tick replay.
"""
from dataclasses import dataclass
import pandas as pd
@dataclass
class IVB:
 day:object=None
 high:float|None=None
 low:float|None=None
 used:bool=False
 cumdelta:float=0.
 def step(self,time,high,low,close,upticks,downticks,flat=True):
  ny=pd.Timestamp(time).tz_convert('America/New_York');minute=ny.hour*60+ny.minute
  if self.day!=ny.date():self.day=ny.date();self.high=self.low=None;self.used=False;self.cumdelta=0.
  delta=upticks-downticks
  if 510<minute<=840:self.cumdelta+=delta
  if 510<minute<=540:
   self.high=high if self.high is None else max(self.high,high);self.low=low if self.low is None else min(self.low,low)
  if not (self.high is not None and 540<minute<=840 and flat and not self.used and close>self.high and close>self.low and delta>=200):return None
  self.used=True
  return {'signal_time':str(pd.Timestamp(time)),'side':'BUY','contracts':1,'entry_reference':close,'initial_sl':self.low,'initial_tp':close+(close-self.low),'delta':delta,'cumdelta':self.cumdelta,'source_close_timing_optimistic':True,'entry_at_eod_hazard':minute==840}
def validate_export(d):
 required=['close_timestamp_utc','open','high','low','close','upticks','downticks'];assert set(required)<=set(d)
 d=d.copy();d['close_timestamp_utc']=pd.to_datetime(d.close_timestamp_utc,utc=True)
 assert d.close_timestamp_utc.is_monotonic_increasing and d.close_timestamp_utc.is_unique
 assert not d[required].isna().any().any();assert (d[['upticks','downticks']]>=0).all().all()
 assert ((d.high>=d[['open','close','low']].max(axis=1))&(d.low<=d[['open','close','high']].min(axis=1))).all()
 assert (d.close_timestamp_utc.dt.minute%5==0).all() and (d.close_timestamp_utc.dt.second==0).all()
 return d
