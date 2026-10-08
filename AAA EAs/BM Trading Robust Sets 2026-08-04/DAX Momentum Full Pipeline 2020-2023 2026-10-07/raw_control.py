"""Original production binary, 2020–2023 only; native isolated raw control."""
from pathlib import Path
import importlib.util,json,msvcrt
R=Path(__file__).resolve().parent;B=R.parent
spec=importlib.util.spec_from_file_location('dax_transfer_control',B/'Nasdaq 5M Germany Transfer 2026-10-07/run.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
control.R=R/'Original Control';control.R.mkdir(exist_ok=True)
control.WINDOWS={'2020-2023':('2020-01-01','2024-01-01')}
def main():
 original={str(p):control.sha(p) for p in (control.SRC,control.SRC.with_suffix('.ex5'),control.SET)}
 p=R/'PRODUCTION FINGERPRINTS.json'
 if p.exists():assert json.loads(p.read_text())==original
 else:control.save(p,original)
 lock=(B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b')
 lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 try:
  result=control.case('DE30','2020-2023')
  assert all(control.sha(Path(p))==digest for p,digest in original.items())
  control.save(R/'RAW ORIGINAL 2020-2023.json',result)
 finally:lock.close()
if __name__=='__main__':main()
