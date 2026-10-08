"""Independent date/risk-input and native cashflow integrity checks."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import collections, hashlib, json
import pandas as pd

R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def nth_sunday(year,month,n):
 first=datetime(year,month,1,tzinfo=timezone.utc)
 return 1+(6-first.weekday())%7+7*(n-1)
def mql_offset(t):
 start=datetime(t.year,3,nth_sunday(t.year,3,2),7,tzinfo=timezone.utc)
 end=datetime(t.year,11,nth_sunday(t.year,11,1),6,tzinfo=timezone.utc)
 return -4 if start<=t<end else -5
def main():
 # Every hour throughout the research window, including DST-transition boundaries.
 tested=0;t=datetime(2023,10,6,tzinfo=timezone.utc);end=datetime(2026,10,6,tzinfo=timezone.utc)
 while t<end:
  assert mql_offset(t)==t.astimezone(ZoneInfo('America/New_York')).utcoffset().total_seconds()/3600
  tested+=1;t+=timedelta(hours=1)
 build=json.loads((R/'build.json').read_text());status=json.loads((R/'native/status.json').read_text())
 assert build['source']==sha(R/'Roboquant ORB Raw.mq5')==status['source_sha256']
 assert build['protocol']==sha(R/'PROTOCOL.md')==status['protocol_sha256']
 assert build['binary']==sha(R/'Roboquant ORB Raw.ex5')
 assert status['report_sha256']==sha(R/'native/report.htm')
 assert all(v==0 for v in status['flags'].values())
 trades=json.loads((R/'native/trades.json').read_text())
 assert len(trades)==status['native']['trades']
 assert abs(sum(x['net_profit'] for x in trades)-status['native']['net_profit'])<0.02
 for x in trades:
  assert abs(x['gross_profit']+x['commission']+x['swap']-x['net_profit'])<0.011
 holds=[(datetime.fromisoformat(x['close_time'])-datetime.fromisoformat(x['open_time'])).total_seconds() for x in trades]
 assert max(holds)<=481
 decisions=pd.read_csv(R/'native/decisions.csv',encoding='utf-16')
 sent=decisions[decisions.reason=='entry_sent'].copy()
 sent['ny']=pd.to_datetime(sent.epoch,unit='s',utc=True).dt.tz_convert('America/New_York')
 assert len(sent)==len(trades)==sent.ny.dt.date.nunique()
 assert ((sent.atr_ratio>=1)&(sent.atr_ratio<=2.5)&(sent.relative_volume>=0.5)&(sent.relative_volume<=1.5)).all()
 assert sent.ny.dt.strftime('%H%M%S').ge('095955').all()
 assert sent.range_high.gt(sent.range_low).all()
 reason=lambda x:'TP' if x['exit_comment'].startswith('tp') else 'SL' if x['exit_comment'].startswith('sl') else 'time/other'
 result={'dst_hours_checked':tested,'source_binary_protocol_report_hashes_match':True,'native_cashflow_parity':True,'one_entry_per_ny_day':True,'entry_filter_bands_valid':True,'maximum_hold_seconds':max(holds),'exit_reasons':dict(collections.Counter(map(reason,trades))),'gross_after_spread_before_commission':round(sum(x['gross_profit'] for x in trades),2),'commission':round(sum(x['commission'] for x in trades),2),'net':round(sum(x['net_profit'] for x in trades),2),'long_short':dict(collections.Counter(x['side'] for x in trades))}
 (R/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
