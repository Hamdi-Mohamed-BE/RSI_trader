"""Rebuild derived exit-delay diagnostics from actual native closes, no reruns or strategy edits."""
from pathlib import Path
import gzip,json
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent
def main():
 for p in (R/'native').glob('*/result.json'):
  z=json.loads(p.read_text())
  if z.get('export'):continue
  trades=json.loads(gzip.decompress((p.parent/'trades.json.gz').read_bytes()));a=pd.read_csv(p.parent/'audit.csv.gz');e=a[(a.event=='entry')&(a.retcode==10009)]
  close=pd.to_datetime([t['close_time'] for t in trades],utc=True).to_numpy(dtype='datetime64[ns]').astype('int64')/1e9
  assert len(close)==len(e);late=np.maximum(0,close-e.end_epoch.to_numpy())
  z['audit'].update(late_exits_over_60s=int((late>60).sum()),max_exit_delay_hours=float(late.max()/3600) if len(late) else 0,invalid_stop_entries=int(((a.event=='entry')&(a.retcode==10016)).sum()),insufficient_funds_entries=int(((a.event=='entry')&(a.retcode==10019)).sum()))
  p.write_text(json.dumps(z,indent=2,allow_nan=False),encoding='utf-8')
 rows=[json.loads((R/'native'/f'{tf}-{version}/result.json').read_text()) for tf in ('H1','H4','D1') for version in ('model','control')]
 (R/'SUMMARY.json').write_text(json.dumps(rows,indent=2,allow_nan=False),encoding='utf-8');print('Exit delays corrected using explicit nanosecond datetime conversion; prices, trades, P&L and strategy unchanged.')
if __name__=='__main__':main()
