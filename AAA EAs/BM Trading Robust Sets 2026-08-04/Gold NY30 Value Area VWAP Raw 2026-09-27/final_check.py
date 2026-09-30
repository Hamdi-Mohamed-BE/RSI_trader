"""Lightweight final cross-report review independent of chart/report generation."""
from pathlib import Path
import gzip,json,re,hashlib
import audit
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def main():
 build=load(ROOT/"BUILD.json");completed=list((ROOT/"native").glob("*/run.json"))
 assert len(completed)==28
 exits=0;rounding=0;flags={}
 for p in completed:
  meta=load(p);a=load(p.parent/"AUDIT.json");trades=load(p.parent/"trades.json")
  assert a["ok"] and a["report_sha256"]==meta["report_sha256"]
  for key in ("source_sha256","binary_sha256","config_sha256","rules_sha256"):assert meta[key]==build[key]
  journal=gzip.decompress((p.parent/"journal.txt.gz").read_bytes()).decode()
  signals=[z.split("|") for z in dict.fromkeys(re.findall(r"NY30_SIGNAL\|[^\r\n]+",journal))]
  step=float(re.search(r"lot_step=([\d.]+)",journal)[1]);minlot=float(re.search(r"min_lot=([\d.]+)",journal)[1])
  tick=float(re.search(r"tick_size=([\d.]+)",journal)[1]);contract=float(re.search(r"contract=([\d.]+)",journal)[1])
  for s in signals:
   entry,stop,tp,lot,risk,equity=map(float,s[5:11]);one=abs(entry-stop)*contract
   assert risk<=max(equity*.01,minlot*one)+step*one+.02,(p.parent.name,s)
   assert abs(lot/step-round(lot/step))<1e-5
   rounding+=1
  for t in trades:
   near=[s for s in signals if 0<=(audit.dt(t["open_time"])-audit.dt(s[1])).total_seconds()<=5]
   assert len(near)==1
   s=near[0];reason=t["exit_comment"]
   if reason.startswith("tp "):
    assert abs(float(reason[3:])-float(s[7]))<tick*.51
    exits+=1
   elif reason.startswith("sl "):
    sl=float(reason[3:]);orig=float(s[6])
    assert abs(sl-orig)<tick*.51 or (t["entry_comment"]=="NY30 R" and abs(sl-t["open_price"])<tick*.51)
    exits+=1
  assert meta["flags"]["entry_fail"]==meta["flags"]["close_fail"]==meta["flags"]["be_fail"]==0,(p.parent.name,meta["flags"])
  flags[p.parent.name]=meta["flags"]
 result={"ok":True,"reports":len(completed),"native_exit_level_checks":exits,"lot_step_and_risk_bound_checks":rounding,"execution_flags":flags}
 audit.save(ROOT/"FINAL_REVIEW.json",result)
 print(json.dumps({k:v for k,v in result.items() if k!="execution_flags"},indent=2),flush=True)
if __name__=="__main__":main()

