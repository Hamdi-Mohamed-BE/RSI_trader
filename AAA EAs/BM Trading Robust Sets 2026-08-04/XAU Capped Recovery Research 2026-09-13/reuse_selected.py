"""Reuse exact existing native runs when the frozen selection equals baseline."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
selected=json.loads((ROOT/'selection.json').read_text())['selected']['parameters']
baseline=json.loads((ROOT/'baseline.json').read_text())
source_hash=hashlib.sha256((ROOT/'EA'/'XAU Capped Recovery.mq5').read_bytes()).hexdigest()
for r in baseline:
    if r['parameters']!=selected:continue
    assert r['source_sha256']==source_hash
    old=r['tag'];new=old.replace('baseline-','selected-',1)
    assert not (ROOT/'Runs'/f'{new}.json').exists()
    for p in (ROOT/'Audit').glob(old+'-*'):
        shutil.copy2(p,p.with_name(p.name.replace(old,new,1)))
    shutil.copy2(ROOT/'Backtest Reports'/f'{old}.htm',ROOT/'Backtest Reports'/f'{new}.htm')
    # The native HTML retains its original title and graph paths intentionally.
    alias={**r,'tag':new,'reused_from':old,'reuse_reason':'Frozen settings, window, source and execution delay exactly equal existing baseline run; not a new test.'}
    (ROOT/'Runs'/f'{new}.json').write_text(json.dumps(alias,indent=2),encoding='utf-8')
    print(f'{new}: reuses {old}')
