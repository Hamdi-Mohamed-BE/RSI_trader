"""Serial research driver. Never controls the live terminal."""
from pathlib import Path
import importlib.util,json,sys,subprocess
from concurrent.futures import ProcessPoolExecutor
BASE=Path(__file__).resolve().parent.parent
GOLD=BASE/"Gold NY30 Value Area VWAP Raw 2026-09-27"
sys.path.insert(0,str(GOLD))
import audit
VARIANTS=("reversal","continuation","combined","control")
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 mode=sys.argv[1]
 runners=[]
 for asset,symbol in (("US100","USTEC"),("US500","US500")):
  root=BASE/(asset+" NY30 Value Area VWAP Raw 2026-09-27")
  r=module(root/"run_native.py",asset)
  if not (root/"BUILD.json").exists():r.compile_ea()
  r.frozen();runners.append((asset,symbol,root,r))
 schedule=[("smoke",4)] if mode=="smoke" else [(p,1) for p in ("3y","5y")]+[(p,4) for p in ("6m","1y","3y","5y")]
 # Native terminals remain strictly serial. Only independent, read-only
 # ledger/profile checks use two workers alongside the native tester.
 with ProcessPoolExecutor(max_workers=2) as pool:
  futures=[]
  for period,model in schedule:
   for asset,symbol,root,r in runners:
    for version in VARIANTS:
     for job in futures:
      if job.done():job.result()
     r.run_case(period,version,model)
     case=root/"native"/f"{symbol}-{period}-{version}-m{model}"
     if not (case/"AUDIT.json").exists():futures.append(pool.submit(audit.audit,case))
  for job in futures:job.result()
 if mode=="grid":
  for asset,symbol,root,r in runners:
   checker=module(GOLD/"final_check.py",asset+"_final");checker.ROOT=root;checker.main()
 print("COMPLETE "+mode,flush=True)
if __name__=="__main__":main()
