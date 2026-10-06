"""Extend unchanged raw evidence; preserve the original evidence folder."""
from pathlib import Path
import importlib.util,json,sys,shutil,inspect
R=Path(__file__).resolve().parent;RAW=R.parent
s=importlib.util.spec_from_file_location('ukt_raw',RAW/'run.py');raw=importlib.util.module_from_spec(s);s.loader.exec_module(raw)
raw.R=R;raw.SOURCE=RAW/'EA/Calyx UK100 Three Module Research.mq5';raw.EXPERT=raw.SOURCE.with_suffix('.ex5')
raw.PERIODS.update({'6M':('2026.04.04','2026.10.04'),'3Y':('2023.10.04','2026.10.04'),'5Y':('2021.10.04','2026.10.04')})
raw.PERIODS['XAG1Y']=('2025.10.04','2026.10.04')
# Reuse the exact raw runner with a symbol variable; never alter the raw EA or its inputs.
raw.SYMBOL='UK100'
run_source=inspect.getsource(raw.run).replace("symbol='UK100'","symbol=SYMBOL").replace('Symbol=UK100','Symbol={SYMBOL}').replace("[start,end,'UK100','H1']","[start,end,SYMBOL,'H1']")
exec(run_source,raw.__dict__)
# Older broker history has a 14:01 first quote after a gap. Accept only an
# entry inside the immediately following H1 bar, never a stale/future signal.
audit_source=inspect.getsource(raw.audit).replace('3600<=','3600<=').replace('.total_seconds()<3610','.total_seconds()<7200')
exec(audit_source,raw.__dict__)
R.mkdir(exist_ok=True)
for name in ['RAW.set','PROTOCOL.txt']:shutil.copy2(RAW/name,R/name)
for window in ['SMOKE','1Y','3M']:
    target=R/'native'/window
    if not target.exists():shutil.copytree(RAW/'native'/window,target)
if __name__=='__main__':
    for w in sys.argv[1:]:
        raw.SYMBOL='XAGUSD' if w.startswith('XAG') else 'UK100'
        raw.run(w)
    raw.save(R/'BASELINE RESULTS.json',[json.loads(p.read_text()) for p in sorted((R/'native').glob('*/results.json'))])
