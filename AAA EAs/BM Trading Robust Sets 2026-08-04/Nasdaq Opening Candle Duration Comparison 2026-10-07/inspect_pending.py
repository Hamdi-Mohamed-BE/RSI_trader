"""Read-only audit of the completed M1 native report and initial stop slippage."""
import json
import run
from app.mt5_evidence_jobs import _number
report=run.T/'reports/opening-duration-20261007/3m-M1.htm'
trades=run.h._native_trades(report,'M1')
orders=run.orders(report)
rows=[]
for t in trades:
    for o in orders:
        if o[0]==t['open_time'].replace('-','.').replace('T',' ') and o[10]==t['entry_comment']:
            stop=_number(o[6]); pct=abs(t['open_price']-stop)/t['open_price']*100
            planned=stop/(.994 if t['side']=='Long' else 1.006)
            rows.append(dict(open=t['open_time'],side=t['side'],fill=t['open_price'],initial_sl=stop,initial_pct_from_fill=pct,planned_quote=planned,fill_minus_quote=t['open_price']-planned))
print(json.dumps(sorted(rows,key=lambda x:abs(x['initial_pct_from_fill']-.60),reverse=True)[:8],indent=2))
print(json.dumps(run.h._native_metrics(report),indent=2))
import pandas as pd
for folder in (run.R/'native').iterdir():
    if not (folder/'checks.json').exists() or not (folder/'trades.json').exists(): continue
    checks=json.loads((folder/'checks.json').read_text()); ledger=json.loads((folder/'trades.json').read_text())
    if not checks: continue
    for t in ledger:
        matched=[c for c in checks if pd.Timestamp(c['at'])<=pd.Timestamp(t['open_time'])<=pd.Timestamp(c['at'])+pd.Timedelta(seconds=5)]
        if len(matched)!=1 or not matched[0]['di_pass']:
            print(json.dumps(dict(folder=folder.name,open=t['open_time'],matches=matched),indent=2))
            break
