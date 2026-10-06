"""Pre-search time-exit input guard; no strategy or threshold retuning."""
from pathlib import Path
import hashlib,importlib.util,json,msvcrt
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('frozen_slow_plan',R/'plan.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
original=p.canonical
def canonical(values):
 values=dict(values)
 if values['InpExitMode']==3 and values['InpMaximumHoldDays']==0:values['InpMaximumHoldDays']=5
 return original(values)
if __name__=='__main__':
 signature={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in ['search.py','PRESEARCH AMENDMENT.md']}
 frozen=R/'PRESEARCH FROZEN.json'
 if frozen.exists():assert json.loads(frozen.read_text())==signature
 else:p.save(frozen.name,signature)
 assert p.n.freeze()==json.loads((R/'build.json').read_text())['frozen']
 p.canonical=canonical
 with (p.n.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  p.search();p.plateau();p.choose();p.confirm()
