"""Preserve the superseded execution-audit pass before correcting the quote check."""
from pathlib import Path
import gzip,json,shutil
import run as r

target=r.R/'Execution Audit Baseline - not final'
assert not target.exists(),'Archive already exists; do not replace it'
target.mkdir()
for p in list(r.R.glob('*.mq5'))+list(r.R.glob('*.ex5'))+list(r.R.glob('*.set'))+[r.R/'Golden Trio Engine.mqh',r.R/'build.json',r.R/'PROTOCOL.txt',r.R/'run-config.json']:
    shutil.copy2(p,target/p.name)
for mode,(name,tf,slug) in r.CASES.items():
    src=r.R/slug/'native';dest=target/slug;dest.mkdir()
    for filename in ['report.htm','status.json','trades.json']:
        shutil.copy2(src/filename,dest/filename)
    for filename in ['decisions.csv','equity.csv','bars.csv','sessions.csv']:
        with (src/filename).open('rb') as f,gzip.open(dest/(filename+'.gz'),'wb',compresslevel=1) as out:
            shutil.copyfileobj(f,out)
    for filename in ['results.json','verification.json']:
        shutil.copy2(src.parent/filename,dest/filename)
r.save(target/'AUDIT-ISSUE.json',{'superseded_not_final':True,'parameter_optimisation':False,
  'issue':'50 VWAP entries had structural TP at/below executable buy Ask. Bid-based broker-validity check omitted frozen protocol requirement to reject quote beyond target.',
  'fix':'Check positive reward against executable entry quote in addition to broker Bid/Ask stop constraints. Keep all parameters/indicator/entry rules unchanged.',
  'required_regression':'Rerun all three native tests. Vault and Overnight must match these baseline trade ledgers exactly; VWAP will be corrected, not selected by performance.'})
print('Preserved superseded audit pass; no private tester INI or journals copied.')
