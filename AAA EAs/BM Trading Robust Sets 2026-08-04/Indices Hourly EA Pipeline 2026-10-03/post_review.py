"""Additional transparent data-quality flags, without altering performance."""
import json
from pathlib import Path
import pandas as pd
import analyse as a
R=Path(__file__).resolve().parent
def main():
 rows=json.loads((R/'SUMMARY.json').read_text());decisions=json.loads((R/'DECISIONS.json').read_text());quality=[]
 for asset in ['US30','US100','SP500']:
  row=next(r for r in rows if r['asset']==asset and r['window']=='1y' and r['variant']=='baseline')
  f=pd.read_csv(R/'native'/row['tag']/'fills.csv.gz');t=pd.to_datetime(f.utc,format='%Y.%m.%d %H:%M:%S',utc=True);spread=f.ask-f.bid;real=t>=pd.Timestamp('2026-01-01',tz='UTC')
  q={'asset':asset,'year_zero_entry_spread_fraction_pct':100*float((spread.abs()<1e-9).mean()),'real2026_zero_entry_spread_fraction_pct':100*float((spread[real].abs()<1e-9).mean()),'warning':'Many native entry quotes have zero recorded bid/ask spread, including the real-tick section. Native costs are the recorded tester costs, not proof of realistic historical/live spreads or fills. Additional measured-friction stress is supplied, but realistic historical quote coverage remains unverified.'};quality.append(q)
  d=next(x for x in decisions if x['asset']==asset);b=json.loads((R/'MONTE-CARLO.json').read_text())[asset]['1y']['day_blocks'][1]
  d['gates']['closed_pnl_10pct_breach_below5pct']=b['below_initial_minus_10pct_fraction_pct']<5;d['gates']['historical_bid_ask_spread_integrity_verified']=False;d['data_quality']=q
 a.save(R/'DATA-QUALITY.json',quality);a.save(R/'DECISIONS.json',decisions)
 manifest=json.loads((R/'ANALYSIS-MANIFEST.json').read_text());manifest['post_review_sha256']=a.sha(Path(__file__));manifest['decisions_sha256']=a.sha(R/'DECISIONS.json');manifest['data_quality_sha256']=a.sha(R/'DATA-QUALITY.json');a.save(R/'ANALYSIS-MANIFEST.json',manifest)
 print('DATA QUALITY',quality,flush=True)
if __name__=='__main__':main()
