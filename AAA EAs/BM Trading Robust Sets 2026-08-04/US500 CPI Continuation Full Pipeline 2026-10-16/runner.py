"""Isolated native tester adapter; small batches, immutable manifests, safe retries."""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, importlib.util, json, os, sys, time
R=Path(__file__).resolve().parent; B=R.parent
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path.insert(0,str(R))
import build_engine
spec=importlib.util.spec_from_file_location('cpi_continuation_native_helpers',B/'US100 News Reversion Pipeline 2020-2024 2026-10-08/runner.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
legacy.R=R;legacy.B=B;legacy.build_engine=build_engine;legacy.CONFIG=json.loads((R/'config.json').read_text())
CONFIG=legacy.CONFIG
save=legacy.save;load=legacy.load;sha=legacy.sha;status=legacy.status;lease=legacy.lease

def native(label,cases,start,end,delay=150,model=4):
    assert CONFIG['symbol']=='US500'
    if (R/'RUNS.json').exists():
        existing=load(R/'RUNS.json').get(label)
        if existing is not None:
            assert [x['parameters'] for x in existing]==cases and all(x['start']==start and x['end']==end and x['model']==model for x in existing)
            return existing
    result=[]
    # Two generated/real tick caches at most, avoiding the six-way cache
    # contention observed in the prior raw experiment.
    for chunk_index,offset in enumerate(range(0,len(cases),2)):
        subset=cases[offset:offset+2]
        base=f'{label}-b{chunk_index}'
        for attempt in range(3):
            name=base+(f'-r{attempt}' if attempt else '')
            journal=R/'native'/name/'journal.txt.gz'
            if journal.exists() and not (journal.parent/'results.json').exists():
                old=gzip.decompress(journal.read_bytes()).decode()
                if 'tester agent authorization error' in old:
                    status('RETRY KNOWN PRE-TEST AGENT HANDSHAKE',stage=name);continue
            try:
                rows=legacy.batch(name,subset,start,end,model=model,optimize=len(subset)>1,verbose=True,
                                  risk=CONFIG['risk_percent'],delay=delay,symbol='US500')
                break
            except AssertionError:
                text=gzip.decompress(journal.read_bytes()).decode() if journal.exists() else ''
                if 'tester agent authorization error' not in text or attempt==2: raise
                status('RETRY PRE-TEST AGENT HANDSHAKE',stage=name);time.sleep(2)
        else: raise RuntimeError('Three local tester-agent handshake failures; no failed case presented as result')
        for row in rows:
            row['phase']=label
            row['phase_index']=offset+row['index']
        result.extend(rows)
    allruns=load(R/'RUNS.json') if (R/'RUNS.json').exists() else {}
    allruns[label]=result;save(R/'RUNS.json',allruns)
    return result
