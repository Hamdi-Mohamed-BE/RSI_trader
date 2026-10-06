"""Frozen search, with bounded non-mutating tester shutdown wait."""
from pathlib import Path
import hashlib,importlib.util,json,msvcrt,time
R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('frozen_trend_plan',R/'plan.py')
p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
original_free=p.n.h.free
def wait_free():
 deadline=time.monotonic()+50
 while True:
  try:return original_free()
  except AssertionError as e:
   if not any(s in str(e) for s in ['Tester port occupied','Isolated terminal occupied']):raise
   if time.monotonic()>=deadline:raise
   time.sleep(2)
if __name__=='__main__':
 signature={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in ['resume.py','EXECUTION WAIT AMENDMENT.md']}
 frozen=R/'EXECUTION WAIT FROZEN.json'
 if frozen.exists():assert json.loads(frozen.read_text())==signature
 else:p.save(frozen.name,signature)
 assert p.n.freeze()==json.loads((R/'build.json').read_text())['frozen']
 p.n.h.free=wait_free
 with (p.n.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
  lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
  p.search();p.plateau();p.choose();p.confirm()
