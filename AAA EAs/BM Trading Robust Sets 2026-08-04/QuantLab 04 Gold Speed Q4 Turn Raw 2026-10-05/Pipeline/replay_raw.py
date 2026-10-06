"""Immutable raw binary replay on current broker history; isolates boundary quote updates."""
from pathlib import Path
import importlib.util,json,shutil
import search as n
s=importlib.util.spec_from_file_location('raw_replay',n.RAW/'run.py');raw=importlib.util.module_from_spec(s);s.loader.exec_module(raw)
original=n.RAW
raw.R=n.ROOT/'Raw Replay';raw.R.mkdir(exist_ok=True)
for name in ['build.json','PROTOCOL.txt','run-config.json']:shutil.copy2(original/name,raw.R/name)
raw.save(raw.R/'native/SMOKE/results.json',dict(reference=str(original/'native/SMOKE/results.json'),reference_sha256=n.sha(original/'native/SMOKE/results.json'),note='Existing verified raw smoke prerequisite, not a new smoke result'))
raw.CFG=dict(warmup_days=180,seed=20261005,windows={'3Y':n.WEB['3y']},cases=[dict(id='PARITY_REPLAY',window='3Y',modules=7,control=False,symbol='XAUUSD')])
r=raw.run('PARITY_REPLAY')
import pandas as pd
old=pd.read_csv(raw.R/'native/PARITY_REPLAY/trades.csv');new=n.read_ledger('parity-shared3y')
keys=['module','open_epoch','close_epoch','side','volume','open_price','close_price','initial_sl','initial_tp','requested_risk','actual_risk','net_profit','commission','swap','fee']
def key(df):return sorted(tuple(v if isinstance(v,str) else round(float(v),6) for v in row) for row in df[keys].itertuples(index=False))
ok=key(old)==key(new)
n.save(n.ROOT/'PARITY.json',dict(exact=ok,old_n=len(old),new_n=len(new),new_net=float(new.net_profit.sum()),old_net=float(old.net_profit.sum()),reference='Immutable raw binary replay on identical current history',raw_source_sha256=n.sha(raw.SOURCE),raw_binary_sha256=n.sha(raw.EXPERT),original_raw_net=4021.72,boundary_data_update_usd=float(old.net_profit.sum())-4021.72))
assert ok,'Raw current-history replay still differs from harness'
opt=n.batch('parity-optimizer-two',[n.RAWCASE['A'],n.RAWCASE['A']],*n.RECENT,model=1)[0]
single=n.batch('parity-single',[n.RAWCASE['A']],*n.RECENT,model=1,optimize=False)[0]
assert key(n.read_ledger('parity-optimizer-two'))==key(n.read_ledger('parity-single'))
n.status('PARITY VERIFIED: all188 raw replay positions and optimizer/single')
